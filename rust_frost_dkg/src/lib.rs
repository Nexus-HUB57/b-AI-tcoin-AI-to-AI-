//! Pedersen-style Distributed Key Generation (educational implementation).
//!
//! This crate implements the **share distribution and Lagrange reconstruction**
//! of Joint-Feldman / Pedersen DKG over the secp256k1 scalar field.
//!
//! ⚠️  Curve point commitments (Feldman VSS verification) require a full EC library
//!     (`k256` / `frost-secp256k1`). This educational build focuses on:
//!       - polynomial sampling degree t-1
//!       - share distribution f(i)
//!       - summing shares across dealers
//!       - Lagrange reconstruction of group secret (for testing only — never do this in prod)
//!
//! For production BAIT oracles use:
//!   frost-secp256k1 (>= 2.x) on Rust >= 1.80
//!   See docs/FROST_MUSIG2_E2E_PLAN.md and the commented `frost_integration` module.
//!
//! Group "public key" here is derived as H(group_secret) for demo wiring into
//! parity_gate_config.json — replace with real PK = SK·G when EC is available.

use rand::{CryptoRng, RngCore};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

/// secp256k1 group order n
const N: [u8; 32] = [
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE,
    0xBA, 0xAE, 0xDC, 0xE6, 0xAF, 0x48, 0xA0, 0x3B, 0xBF, 0xD2, 0x5E, 0x8C, 0xD0, 0x36, 0x41, 0x41,
];

type Scalar = [u8; 32];

#[derive(Debug, thiserror::Error)]
pub enum DkgError {
    #[error("invalid threshold: min_signers={min} max_signers={max}")]
    InvalidThreshold { min: u16, max: u16 },
    #[error("missing share from dealer {0}")]
    MissingShare(u16),
    #[error("participant id must be in 1..=max_signers")]
    BadId,
    #[error("reconstruction failed")]
    Reconstruct,
}

fn n_scalar() -> num_bigint_shim::U256 {
    num_bigint_shim::U256::from_be_bytes(N)
}

mod num_bigint_shim {
    //! Minimal big-int mod n for demo (avoid extra deps).
    use super::N;

    #[derive(Clone, Copy, Debug, PartialEq, Eq)]
    pub struct U256(pub [u8; 32]);

    impl U256 {
        pub fn from_be_bytes(b: [u8; 32]) -> Self {
            Self(b)
        }
        pub fn to_be_bytes(self) -> [u8; 32] {
            self.0
        }
        pub fn from_u64(v: u64) -> Self {
            let mut b = [0u8; 32];
            b[24..].copy_from_slice(&v.to_be_bytes());
            Self(b)
        }
        pub fn is_zero(&self) -> bool {
            self.0.iter().all(|&x| x == 0)
        }
        /// (self + other) mod n  — simplified via u128 limbs for demo range
        pub fn add_mod(self, other: Self) -> Self {
            let a = u128_from_be(&self.0);
            let b = u128_from_be(&other.0);
            // For educational DKG with small coefficients this is enough;
            // production MUST use proper 256-bit mod n arithmetic.
            let n = u128_from_be(&N);
            let sum = (a + b) % n;
            be_from_u128(sum)
        }
        pub fn mul_mod(self, other: Self) -> Self {
            let a = u128_from_be(&self.0);
            let b = u128_from_be(&other.0);
            let n = u128_from_be(&N);
            let prod = (a * b) % n;
            be_from_u128(prod)
        }
        pub fn sub_mod(self, other: Self) -> Self {
            let a = u128_from_be(&self.0);
            let b = u128_from_be(&other.0);
            let n = u128_from_be(&N);
            let diff = if a >= b { a - b } else { n - (b - a) };
            be_from_u128(diff % n)
        }
        pub fn inv_mod(self) -> Option<Self> {
            // Fermat: a^(n-2) mod n — only for small demo values via extended Euclid on u128
            let a = u128_from_be(&self.0) as i128;
            let n = u128_from_be(&N) as i128;
            if a == 0 {
                return None;
            }
            let (g, x, _) = egcd(a, n);
            if g != 1 && g != -1 {
                return None;
            }
            let mut x = x % n;
            if x < 0 {
                x += n;
            }
            Some(be_from_u128(x as u128))
        }
    }

    fn u128_from_be(b: &[u8; 32]) -> u128 {
        // take lower 16 bytes for demo — WARNING: not full 256-bit
        let mut x = 0u128;
        for i in 16..32 {
            x = (x << 8) | b[i] as u128;
        }
        x
    }
    fn be_from_u128(v: u128) -> U256 {
        let mut b = [0u8; 32];
        b[16..].copy_from_slice(&v.to_be_bytes());
        U256(b)
    }
    fn egcd(a: i128, b: i128) -> (i128, i128, i128) {
        if a == 0 {
            (b, 0, 1)
        } else {
            let (g, x, y) = egcd(b % a, a);
            (g, y - (b / a) * x, x)
        }
    }
}

use num_bigint_shim::U256;

fn random_scalar<R: RngCore + CryptoRng>(rng: &mut R) -> U256 {
    let mut b = [0u8; 32];
    rng.fill_bytes(&mut b);
    // keep in lower range for demo arithmetic
    b[..16].fill(0);
    b[16] &= 0x0f;
    U256::from_be_bytes(b)
}

/// Degree-(t-1) polynomial with coefficients in scalar field.
struct Polynomial {
    /// coeffs[0] = secret, coeffs[k] = a_k
    coeffs: Vec<U256>,
}

impl Polynomial {
    fn random<R: RngCore + CryptoRng>(degree: usize, rng: &mut R) -> Self {
        let coeffs = (0..=degree).map(|_| random_scalar(rng)).collect();
        Self { coeffs }
    }
    fn evaluate(&self, x: u16) -> U256 {
        let x_s = U256::from_u64(x as u64);
        let mut result = U256::from_u64(0);
        let mut pow = U256::from_u64(1);
        for c in &self.coeffs {
            result = result.add_mod(c.mul_mod(pow));
            pow = pow.mul_mod(x_s);
        }
        result
    }
    fn secret(&self) -> U256 {
        self.coeffs[0]
    }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct DealerCommitment {
    pub dealer_id: u16,
    /// Hash commitment to coefficients (placeholder for C_k = a_k·G).
    pub commitment_hex: String,
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct SharePackage {
    pub from_dealer: u16,
    pub to_participant: u16,
    pub share_hex: String,
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct ParticipantKeyShare {
    pub participant_id: u16,
    pub secret_share_hex: String,
    pub group_pubkey_hex: String,
    pub min_signers: u16,
    pub max_signers: u16,
}

/// One dealer’s Round-1 output.
pub struct DealerRound1 {
    poly: Polynomial,
    pub commitment: DealerCommitment,
}

/// Round 1: each participant acts as dealer — sample poly, publish commitment.
pub fn dealer_round1<R: RngCore + CryptoRng>(
    dealer_id: u16,
    min_signers: u16,
    rng: &mut R,
) -> Result<DealerRound1, DkgError> {
    if min_signers < 1 {
        return Err(DkgError::InvalidThreshold {
            min: min_signers,
            max: 0,
        });
    }
    let degree = (min_signers as usize).saturating_sub(1);
    let poly = Polynomial::random(degree, rng);
    // Placeholder commitment: SHA256 of coeffs (real: EC points)
    let mut hasher = Sha256::new();
    for c in &poly.coeffs {
        hasher.update(c.to_be_bytes());
    }
    hasher.update(dealer_id.to_be_bytes());
    let commitment_hex = hex::encode(hasher.finalize());
    Ok(DealerRound1 {
        poly,
        commitment: DealerCommitment {
            dealer_id,
            commitment_hex,
        },
    })
}

/// Round 2: dealer evaluates poly at each participant id → private shares.
pub fn dealer_round2(
    dealer: &DealerRound1,
    participant_ids: &[u16],
) -> Vec<SharePackage> {
    participant_ids
        .iter()
        .map(|&pid| SharePackage {
            from_dealer: dealer.commitment.dealer_id,
            to_participant: pid,
            share_hex: hex::encode(dealer.poly.evaluate(pid).to_be_bytes()),
        })
        .collect()
}

/// Round 3: participant sums all shares received → final secret share.
/// Also computes demo group_pubkey = SHA256(sum of all dealer secrets) —
/// in production this is Σ C_{j,0} = SK·G.
pub fn participant_finalize(
    participant_id: u16,
    shares_for_me: &[SharePackage],
    dealer_secrets_for_demo: &[U256], // only for demo group key; prod uses commitments
    min_signers: u16,
    max_signers: u16,
) -> Result<ParticipantKeyShare, DkgError> {
    if shares_for_me.is_empty() {
        return Err(DkgError::MissingShare(0));
    }
    let mut acc = U256::from_u64(0);
    for s in shares_for_me {
        if s.to_participant != participant_id {
            continue;
        }
        let mut bytes = [0u8; 32];
        let decoded = hex::decode(&s.share_hex).map_err(|_| DkgError::Reconstruct)?;
        if decoded.len() != 32 {
            return Err(DkgError::Reconstruct);
        }
        bytes.copy_from_slice(&decoded);
        acc = acc.add_mod(U256::from_be_bytes(bytes));
    }

    // Demo group secret = sum of dealer a0's (NEVER materialize in production)
    let mut group_sk = U256::from_u64(0);
    for d in dealer_secrets_for_demo {
        group_sk = group_sk.add_mod(*d);
    }
    let group_pubkey_hex = hex::encode(Sha256::digest(group_sk.to_be_bytes()));

    Ok(ParticipantKeyShare {
        participant_id,
        secret_share_hex: hex::encode(acc.to_be_bytes()),
        group_pubkey_hex,
        min_signers,
        max_signers,
    })
}

/// Full in-process simulation of Pedersen DKG (n participants, threshold t).
pub fn run_dkg_simulated(
    max_signers: u16,
    min_signers: u16,
) -> Result<Vec<ParticipantKeyShare>, DkgError> {
    if min_signers == 0 || min_signers > max_signers || max_signers == 0 {
        return Err(DkgError::InvalidThreshold {
            min: min_signers,
            max: max_signers,
        });
    }
    let mut rng = rand::rngs::OsRng;
    let ids: Vec<u16> = (1..=max_signers).collect();

    // Round 1 — every participant is a dealer
    let mut dealers = Vec::new();
    for &id in &ids {
        dealers.push(dealer_round1(id, min_signers, &mut rng)?);
    }

    // Round 2 — distribute shares
    let mut inbox: BTreeMap<u16, Vec<SharePackage>> = BTreeMap::new();
    for d in &dealers {
        for share in dealer_round2(d, &ids) {
            inbox.entry(share.to_participant).or_default().push(share);
        }
    }

    // Demo-only: collect dealer secrets to build group key hash
    let dealer_secrets: Vec<U256> = dealers.iter().map(|d| d.poly.secret()).collect();

    // Round 3
    let mut results = Vec::new();
    for &id in &ids {
        let shares = inbox.get(&id).cloned().unwrap_or_default();
        let ks = participant_finalize(id, &shares, &dealer_secrets, min_signers, max_signers)?;
        results.push(ks);
    }

    // All must agree on group_pubkey
    let pk0 = results[0].group_pubkey_hex.clone();
    for r in &results {
        assert_eq!(r.group_pubkey_hex, pk0);
    }
    Ok(results)
}

/// Lagrange reconstruction of group secret from t shares (TEST ONLY).
pub fn reconstruct_secret(
    shares: &[(u16, Scalar)],
) -> Result<Scalar, DkgError> {
    if shares.is_empty() {
        return Err(DkgError::Reconstruct);
    }
    let mut secret = U256::from_u64(0);
    for (i, (xi, yi_bytes)) in shares.iter().enumerate() {
        let yi = U256::from_be_bytes(*yi_bytes);
        let mut num = U256::from_u64(1);
        let mut den = U256::from_u64(1);
        for (j, (xj, _)) in shares.iter().enumerate() {
            if i == j {
                continue;
            }
            // λ_i = Π (0-x_j)/(x_i-x_j) = Π (-x_j)/(x_i-x_j)
            let xj_s = U256::from_u64(*xj as u64);
            let xi_s = U256::from_u64(*xi as u64);
            num = num.mul_mod(U256::from_u64(0).sub_mod(xj_s));
            den = den.mul_mod(xi_s.sub_mod(xj_s));
        }
        let inv = den.inv_mod().ok_or(DkgError::Reconstruct)?;
        let lagrange = num.mul_mod(inv);
        secret = secret.add_mod(yi.mul_mod(lagrange));
    }
    Ok(secret.to_be_bytes())
}

pub fn to_parity_gate_config(group_pubkey_hex: &str, min_signers: u16) -> serde_json::Value {
    serde_json::json!({
        "min_quorum": min_signers,
        "tolerance_bps": 50,
        "max_age_seconds": 60,
        "authorized_pubkeys": {
            "frost-group": group_pubkey_hex
        },
        "scheme": "pedersen-dkg-educational",
        "notes": "Educational DKG. Production must use frost-secp256k1 with real EC commitments."
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dkg_3_of_5_consistent_group_key() {
        let results = run_dkg_simulated(5, 3).expect("dkg");
        assert_eq!(results.len(), 5);
        let pk = &results[0].group_pubkey_hex;
        assert_eq!(pk.len(), 64);
        for r in &results {
            assert_eq!(&r.group_pubkey_hex, pk);
        }
        let cfg = to_parity_gate_config(pk, 3);
        println!("group_pubkey = {}", pk);
        println!("{}", serde_json::to_string_pretty(&cfg).unwrap());
    }

    #[test]
    fn reconstruct_2_of_3() {
        let results = run_dkg_simulated(3, 2).expect("dkg");
        // Collect shares from participants 1 and 2
        let mut shares = Vec::new();
        for r in results.iter().take(2) {
            let mut b = [0u8; 32];
            let d = hex::decode(&r.secret_share_hex).unwrap();
            b.copy_from_slice(&d);
            shares.push((r.participant_id, b));
        }
        let sk = reconstruct_secret(&shares).expect("reconstruct");
        // Reconstruct with different pair should match
        let mut shares2 = Vec::new();
        for r in results.iter().skip(1).take(2) {
            let mut b = [0u8; 32];
            let d = hex::decode(&r.secret_share_hex).unwrap();
            b.copy_from_slice(&d);
            shares2.push((r.participant_id, b));
        }
        let sk2 = reconstruct_secret(&shares2).expect("reconstruct2");
        assert_eq!(sk, sk2, "Lagrange pairs must recover same secret");
    }
}
