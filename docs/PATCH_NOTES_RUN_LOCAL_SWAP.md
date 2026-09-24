# Optional patches for run_local_swap_*.py

These changes replace `ParityGate(lambda _: True)` with real Schnorr test keys.
Apply manually or in a follow-up PR after review — not included as hard overwrites.

## Pattern

```python
from native_processing.test_parity_gate import make_test_parity_gate
from native_processing.parity_attestation_builder import build_signed_attestation

parity_gate, test_oracles = make_test_parity_gate(clock=time.time)
signed_att = build_signed_attestation(test_oracles, bait_usdt=1.0, ttl_seconds=120, now=now)
parity_attestation = { ... from signed_att ... }
# then: parity_gate=parity_gate  instead of lambda _: True
```

See local copies under artifacts if needed for diff review.
