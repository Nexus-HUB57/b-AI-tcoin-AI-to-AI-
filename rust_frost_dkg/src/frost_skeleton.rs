//! FROST skeleton: DKG 3-of-5 + sign + verify → proof_b64 (64 bytes) for Python ParityGate.
//!
//! Requires: Rust >= 1.80, frost-secp256k1 = "2.1"
//!
//! Enable with:
//!   // in lib.rs:  #[cfg(feature = "frost-prod")] mod frost_skeleton;
//!   cargo test --features frost-prod
//!
//! This file is the reference implementation to port when the toolchain allows.

#![allow(dead_code, unused_imports)]

/*
use frost_secp256k1 as frost;
use frost::keys::{self, dkg, KeyPackage, PublicKeyPackage};
use frost::{Identifier, SigningPackage, aggregate};
use rand::rngs::OsRng;
use std::collections::BTreeMap;

pub type Hex = String;

/// Run Pedersen DKG (FROST) 3-of-5 in-process. Returns (key_packages, pubkey_package, group_xonly_hex).
pub fn dkg_3of5() -> Result<(BTreeMap<Identifier, KeyPackage>, PublicKeyPackage, Hex), frost::Error> {
    let max_signers: u16 = 5;
    let min_signers: u16 = 3;
    let mut rng = OsRng;

    // --- Round 1 ---
    let mut r1_secrets = BTreeMap::new();
    let mut r1_packages = BTreeMap::new();
    for i in 1..=max_signers {
        let id = Identifier::try_from(i).unwrap();
        let (sec, pkg) = dkg::part1(id, max_signers, min_signers, &mut rng)?;
        r1_secrets.insert(id, sec);
        r1_packages.insert(id, pkg);
    }

    // --- Round 2 ---
    let mut r2_secrets = BTreeMap::new();
    let mut r2_packages_map: BTreeMap<Identifier, BTreeMap<Identifier, _>> = BTreeMap::new();
    for i in 1..=max_signers {
        let id = Identifier::try_from(i).unwrap();
        let sec = r1_secrets.remove(&id).unwrap();
        // packages from everyone except self
        let mut received = r1_packages.clone();
        received.remove(&id);
        let (r2_sec, pkgs_out) = dkg::part2(sec, &received)?;
        r2_secrets.insert(id, r2_sec);
        for (to, pkg) in pkgs_out {
            r2_packages_map.entry(to).or_default().insert(id, pkg);
        }
    }

    // --- Round 3 ---
    let mut key_packages = BTreeMap::new();
    let mut pubkey_package = None;
    for i in 1..=max_signers {
        let id = Identifier::try_from(i).unwrap();
        let mut r1_recv = r1_packages.clone();
        r1_recv.remove(&id);
        let r2_recv = r2_packages_map.remove(&id).unwrap_or_default();
        let (kp, pp) = dkg::part3(r2_secrets.get(&id).unwrap(), &r1_recv, &r2_recv)?;
        key_packages.insert(id, kp);
        pubkey_package = Some(pp);
    }
    let pubkey_package = pubkey_package.unwrap();

    // Group verifying key → x-only hex (32 bytes)
    let vk = pubkey_package.verifying_key();
    let serialized = vk.serialize()?;
    let xonly = if serialized.len() == 33 {
        serialized[1..].to_vec()
    } else {
        serialized.to_vec()
    };
    let group_hex = hex::encode(xonly);
    Ok((key_packages, pubkey_package, group_hex))
}

/// Sign message with first `min_signers` participants; return 64-byte signature.
pub fn frost_sign(
    key_packages: &BTreeMap<Identifier, KeyPackage>,
    pubkey_package: &PublicKeyPackage,
    message: &[u8],
    min_signers: u16,
) -> Result<[u8; 64], frost::Error> {
    let mut rng = OsRng;
    let mut nonces = BTreeMap::new();
    let mut commitments = BTreeMap::new();

    // Round 1: nonces from first min_signers
    for (i, (id, kp)) in key_packages.iter().enumerate() {
        if i as u16 >= min_signers {
            break;
        }
        let (nonce, commit) = frost::round1::commit(kp.signing_share(), &mut rng);
        nonces.insert(*id, nonce);
        commitments.insert(*id, commit);
    }

    let signing_package = SigningPackage::new(commitments, message);

    // Round 2: signature shares
    let mut sig_shares = BTreeMap::new();
    for (id, nonce) in &nonces {
        let kp = &key_packages[id];
        let share = frost::round2::sign(&signing_package, nonce, kp)?;
        sig_shares.insert(*id, share);
    }

    let group_sig = aggregate(&signing_package, &sig_shares, pubkey_package)?;
    let bytes = group_sig.serialize()?;
    let mut out = [0u8; 64];
    out.copy_from_slice(&bytes[..64]);
    Ok(out)
}

pub fn to_parity_config(group_xonly_hex: &str, min_signers: u16) -> serde_json::Value {
    serde_json::json!({
        "min_quorum": 1,
        "tolerance_bps": 50,
        "max_age_seconds": 60,
        "scheme": "frost-pedersen-dkg",
        "authorized_pubkeys": {
            "frost-group": group_xonly_hex
        },
        "notes": "Group key from FROST Pedersen DKG 3-of-5. proof_b64 = single 64-byte Schnorr."
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use base64::{engine::general_purpose::STANDARD, Engine};
    use sha2::{Digest, Sha256};

    #[test]
    fn dkg_sign_verify_proof_b64() {
        let (kps, pp, group_hex) = dkg_3of5().expect("dkg");
        assert_eq!(group_hex.len(), 64);

        // Message = same domain as Python attestation_message_bytes
        let canonical = br#"{"bait_usdt_ppm":1000000,"expires_at":1.0,"observed_at":0.0,"pair":"BAIT/USDT","quorum":1,"round_id":"test","source_ids":["frost-group"],"usd_brl_ppm":5000000,"usdt_usd_ppm":1000000,"version":1}"#;
        let mut data = Vec::new();
        data.extend_from_slice(b"bait.swap.parity.v1\n");
        data.extend_from_slice(canonical);
        let msg = Sha256::digest(&data);

        let sig = frost_sign(&kps, &pp, &msg, 3).expect("sign");
        let proof_b64 = STANDARD.encode(sig);
        assert_eq!(sig.len(), 64);
        println!("group_pubkey={}", group_hex);
        println!("proof_b64={}", proof_b64);
        println!("config={}", serde_json::to_string_pretty(&to_parity_config(&group_hex, 3)).unwrap());

        // Verify with frost
        let sig_obj = frost::Signature::deserialize(sig.as_slice()).expect("sig deser");
        pp.verifying_key().verify(&msg, &sig_obj).expect("verify");
    }
}
*/

/// Placeholder so the module always parses without frost-prod feature.
pub fn skeleton_docs() -> &'static str {
    "Enable feature frost-prod + Rust >= 1.80; see commented code in frost_skeleton.rs"
}
