# Wiring Python ↔ FROST / ParityGate

## 1. Multi-sig concatenada (v1 — produção staging atual)

```python
from native_processing.parity_gate_factory import load_parity_gate
from native_processing.parity_attestation_builder import build_signed_attestation
from native_processing.schnorr_keypair import SchnorrKeyPair

# Config com oracle-a/b/c pubkeys
gate = load_parity_gate("secrets/oracles-staging/parity_gate_config.staging.json")

# Signers = keys descriptografadas
att = build_signed_attestation(signers, bait_usdt=1.0)
gate.validate(att)  # OK
```

Bootstrap one-shot:
```bash
python3 scripts/bootstrap_parity_oracles.py \
  --keys-dir secrets/oracles-staging \
  --config secrets/oracles-staging/parity_gate_config.staging.json \
  --password-file /path/to/pw
```

## 2. FROST group key (v2)

### Config JSON
```json
{
  "scheme": "frost-pedersen-dkg",
  "min_quorum": 1,
  "tolerance_bps": 50,
  "max_age_seconds": 60,
  "authorized_pubkeys": {
    "frost-group": "<64 hex x-only from Rust DKG>"
  }
}
```

### Python
```python
from native_processing.parity_gate_factory import load_parity_gate
from native_processing.frost_verifier import make_frost_verify_proof
from native_processing.parity_gate import ParityGate, ParityAttestation

gate = load_parity_gate("parity_gate_config.frost.json")
# ou:
verify = make_frost_verify_proof(group_pubkey_hex)
gate = ParityGate(verify, min_quorum=1)

att = ParityAttestation(
    pair="BAIT/USDT",
    bait_usdt_ppm=1_000_000,
    usdt_usd_ppm=1_000_000,
    usd_brl_ppm=5_000_000,
    observed_at=...,
    expires_at=...,
    round_id="...",
    source_ids=("frost-group",),
    quorum=1,
    proof_b64="<base64 of 64-byte FROST sig from Rust>",
)
gate.validate(att)
```

### Rust → Python handoff
1. `dkg_3of5()` → `group_xonly_hex` → write `parity_gate_config.frost.json`
2. `frost_sign(message)` → 64 bytes → `proof_b64 = base64(sig)`
3. `message` MUST be `SHA256(b"bait.swap.parity.v1\\n" + canonical_json)` (same as Python `attestation_message_bytes`)

## 3. load_parity_gate scheme auto-detect

| authorized_pubkeys | scheme | verifier |
|--------------------|--------|----------|
| oracle-a,b,c | concat / auto | ConcatSchnorr (N×64) |
| frost-group only | frost / auto | FrostVerifier (64) |

