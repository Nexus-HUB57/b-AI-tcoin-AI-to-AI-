//! BIP-340 Schnorr verification + quorum check for BAIT parity oracles.
//!
//! Compatible with Python `native_processing.schnorr_parity_verifier`.
//!
//! Message format (must match Python):
//!   SHA256( "bait.swap.parity.v1\n" || canonical_json )
//!
//! Proof format:
//!   Base64( sig_0 || sig_1 || ... || sig_n-1 )  where each sig is 64 bytes (r||s)

use secp256k1::{Message, XOnlyPublicKey, schnorr::Signature, Secp256k1};
use sha2::{Digest, Sha256};
use std::collections::HashMap;

/// Tagged hash as defined in BIP-340.
pub fn tagged_hash(tag: &str, msg: &[u8]) -> [u8; 32] {
    let tag_hash = Sha256::digest(tag.as_bytes());
    let mut hasher = Sha256::new();
    hasher.update(&tag_hash);
    hasher.update(&tag_hash);
    hasher.update(msg);
    hasher.finalize().into()
}

/// Build the attestation message bytes (32-byte digest).
/// `canonical_json` must already be the sorted, compact JSON of the unsigned attestation.
pub fn attestation_message(canonical_json: &[u8]) -> [u8; 32] {
    let mut data = Vec::with_capacity(20 + canonical_json.len());
    data.extend_from_slice(b"bait.swap.parity.v1\n");
    data.extend_from_slice(canonical_json);
    Sha256::digest(&data).into()
}

/// Verify a single BIP-340 signature.
pub fn verify_bip340(pubkey_xonly: &[u8; 32], message: &[u8; 32], sig64: &[u8; 64]) -> bool {
    let secp = Secp256k1::verification_only();
    let pk = match XOnlyPublicKey::from_slice(pubkey_xonly) {
        Ok(p) => p,
        Err(_) => return false,
    };
    let sig = match Signature::from_slice(sig64) {
        Ok(s) => s,
        Err(_) => return false,
    };
    // secp256k1 crate expects the 32-byte message hash directly for schnorr
    let msg = Message::from_digest_slice(message).expect("32 bytes");
    secp.verify_schnorr(&sig, &msg, &pk).is_ok()
}

/// Quorum verification over a multi-sig proof.
///
/// * `source_ids` — ordered list of oracle IDs (same order as signatures in proof)
/// * `authorized` — map source_id → 32-byte x-only pubkey
/// * `message` — 32-byte attestation digest
/// * `proof` — raw bytes = concat of 64-byte signatures
/// * `quorum` — minimum valid signatures required
pub fn verify_quorum(
    source_ids: &[&str],
    authorized: &HashMap<&str, [u8; 32]>,
    message: &[u8; 32],
    proof: &[u8],
    quorum: usize,
) -> bool {
    let n = source_ids.len();
    if n == 0 || quorum == 0 || proof.len() != n * 64 {
        return false;
    }
    let mut valid = 0usize;
    for (i, sid) in source_ids.iter().enumerate() {
        let Some(pk) = authorized.get(sid) else {
            continue;
        };
        let mut sig = [0u8; 64];
        sig.copy_from_slice(&proof[i * 64..(i + 1) * 64]);
        if verify_bip340(pk, message, &sig) {
            valid += 1;
        }
    }
    valid >= quorum
}

/// Decode base64 proof into raw signature bytes.
pub fn decode_proof_b64(proof_b64: &str) -> Result<Vec<u8>, base64::DecodeError> {
    use base64::{engine::general_purpose::STANDARD, Engine};
    STANDARD.decode(proof_b64)
}

#[cfg(test)]
mod tests {
    use super::*;
    use secp256k1::{Keypair, SecretKey};

    #[test]
    fn roundtrip_sign_verify() {
        let secp = Secp256k1::new();
        let sk = SecretKey::from_slice(&[1u8; 32]).unwrap();
        let keypair = Keypair::from_secret_key(&secp, &sk);
        let (xonly, _parity) = keypair.x_only_public_key();

        let msg_bytes = attestation_message(b"{\"pair\":\"BAIT/USDT\"}");
        let msg = Message::from_digest_slice(&msg_bytes).unwrap();
        let sig = secp.sign_schnorr_no_aux_rand(&msg, &keypair);

        let mut pk = [0u8; 32];
        pk.copy_from_slice(&xonly.serialize());
        let mut sig_arr = [0u8; 64];
        sig_arr.copy_from_slice(sig.as_ref());

        assert!(verify_bip340(&pk, &msg_bytes, &sig_arr));
    }

    #[test]
    fn quorum_2_of_3() {
        let secp = Secp256k1::new();
        let mut authorized = HashMap::new();
        let mut sigs = Vec::new();
        let msg_bytes = attestation_message(b"{\"test\":1}");

        for i in 1..=3u8 {
            let mut seed = [0u8; 32];
            seed[31] = i;
            let sk = SecretKey::from_slice(&seed).unwrap();
            let keypair = Keypair::from_secret_key(&secp, &sk);
            let (xonly, _) = keypair.x_only_public_key();
            let mut pk = [0u8; 32];
            pk.copy_from_slice(&xonly.serialize());
            let sid = match i {
                1 => "oracle-a",
                2 => "oracle-b",
                _ => "oracle-c",
            };
            authorized.insert(sid, pk);

            let msg = Message::from_digest_slice(&msg_bytes).unwrap();
            let sig = secp.sign_schnorr_no_aux_rand(&msg, &keypair);
            sigs.extend_from_slice(sig.as_ref());
        }

        let ids = ["oracle-a", "oracle-b", "oracle-c"];
        assert!(verify_quorum(&ids, &authorized, &msg_bytes, &sigs, 3));
        assert!(verify_quorum(&ids, &authorized, &msg_bytes, &sigs, 2));

        // Only 2 authorized → quorum 3 fails
        let mut auth2 = authorized.clone();
        auth2.remove("oracle-c");
        assert!(!verify_quorum(&ids, &auth2, &msg_bytes, &sigs, 3));
    }
}
