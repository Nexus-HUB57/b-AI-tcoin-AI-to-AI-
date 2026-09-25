# bait_frost_dkg — Pedersen DKG for BAIT ParityGate

## Status

| Layer | Status |
|-------|--------|
| Educational DKG (scalar shares + Lagrange) | Implemented in `src/lib.rs` |
| Feldman EC commitments (C_k = a_k·G) | Requires `k256` / `frost-secp256k1` |
| Production FROST DKG | Use `frost-secp256k1` on **Rust ≥ 1.80** |

This sandbox runs Rust 1.75 and blocks Cargo build-scripts (`Permission denied`).
Compile outside:

```bash
cd rust_frost_dkg
rustup default 1.80   # or newer
cargo test
cargo run --example dkg_3of5
```

## Protocol (what is implemented)

1. **dealer_round1** — sample degree-(t-1) polynomial, publish hash commitment  
2. **dealer_round2** — evaluate f(i) for each participant → private SharePackage  
3. **participant_finalize** — sum received shares → secret share + group key handle  
4. **run_dkg_simulated** — full n-party in-process DKG  
5. **reconstruct_secret** — Lagrange (TEST ONLY — never in production)  
6. **to_parity_gate_config** — JSON for `parity_gate_factory.py`

## Production path (frost-secp256k1)

```toml
# Cargo.toml — requires Rust >= 1.80
frost-secp256k1 = "2.1"
```

```rust
use frost_secp256k1 as frost;
use frost::keys::dkg;

// part1 → broadcast
// part2 → P2P encrypted shares  
// part3 → KeyPackage + PubKeyPackage
// group x-only pubkey → authorized_pubkeys["frost-group"]
```

See `docs/FROST_MUSIG2_E2E_PLAN.md` and the FROST threshold write-up.

## Security warnings (educational build)

- Scalar arithmetic uses truncated u128 for demo — **not** full 256-bit mod n.
- Commitments are SHA256 of coefficients, **not** EC points — no Feldman verify.
- `reconstruct_secret` exists only to prove Lagrange correctness in tests.
- Do **not** use this crate’s secret shares for real BTC/BAIT custody.
