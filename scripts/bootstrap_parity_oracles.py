#!/usr/bin/env python3
"""Bootstrap de produção/staging: carrega keys criptografadas, assina attestation ao vivo, valida no gate.

Uso no host de staging:

  export ORACLE_KEY_PASSWORD='...'          # ou --password-file
  python3 scripts/bootstrap_parity_oracles.py \\
      --keys-dir secrets/oracles-staging \\
      --config secrets/oracles-staging/parity_gate_config.staging.json

Saídas:
  - Carrega oracle-{a,b,c}.key
  - Constrói ParityAttestation assinada (proof_b64 multi-sig)
  - Valida com ParityGate (load_parity_gate)
  - Imprime digest + attestation JSON (sem material secreto)

Exit 0 = PASS, 1 = FAIL.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from native_processing.parity_gate_factory import load_parity_gate  # noqa: E402
from native_processing.parity_attestation_builder import build_signed_attestation  # noqa: E402
from native_processing.schnorr_keypair import SchnorrKeyPair  # noqa: E402


ORACLE_IDS = ("oracle-a", "oracle-b", "oracle-c")


def _password(args: argparse.Namespace) -> bytes:
    if args.password_env:
        pw = os.environ.get(args.password_env, "").encode()
        if not pw:
            raise SystemExit(f"env {args.password_env} empty")
        return pw
    if args.password_file:
        return Path(args.password_file).read_bytes().strip()
    raise SystemExit("provide --password-env or --password-file")


def load_signers(keys_dir: Path, password: bytes) -> dict:
    signers = {}
    for oid in ORACLE_IDS:
        key_path = keys_dir / f"{oid}.key"
        if not key_path.exists():
            raise SystemExit(f"missing key file: {key_path}")
        kp = SchnorrKeyPair.load_encrypted(key_path, password)
        # Optional: check against .pub
        pub_path = keys_dir / f"{oid}.pub"
        if pub_path.exists():
            expected = pub_path.read_text().strip()
            if kp.public_key_hex != expected:
                raise SystemExit(f"pubkey mismatch for {oid}")
        signers[oid] = kp
        print(f"  loaded {oid}: pubkey={kp.public_key_hex[:16]}…")
    return signers


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap parity oracles (sign + gate validate)")
    parser.add_argument("--keys-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True, help="parity_gate_config JSON")
    parser.add_argument("--password-env", default=None)
    parser.add_argument("--password-file", type=Path, default=None)
    parser.add_argument("--bait-usdt", type=float, default=1.0)
    parser.add_argument("--ttl", type=float, default=90.0)
    parser.add_argument("--json-out", type=Path, default=None, help="write attestation JSON")
    args = parser.parse_args()

    print("=== Bootstrap Parity Oracles ===")
    print(f"keys-dir: {args.keys_dir}")
    print(f"config:   {args.config}")

    password = _password(args)
    print("\n[1] Loading encrypted Schnorr keys…")
    signers = load_signers(args.keys_dir, password)

    print("\n[2] Building signed ParityAttestation…")
    now = time.time()
    att = build_signed_attestation(
        signers,
        bait_usdt=args.bait_usdt,
        usdt_usd=1.0,
        usd_brl=5.0,
        ttl_seconds=args.ttl,
        now=now,
    )
    att_dict = {
        "version": 1,
        "pair": att.pair,
        "bait_usdt_ppm": att.bait_usdt_ppm,
        "usdt_usd_ppm": att.usdt_usd_ppm,
        "usd_brl_ppm": att.usd_brl_ppm,
        "observed_at": att.observed_at,
        "expires_at": att.expires_at,
        "round_id": att.round_id,
        "source_ids": list(att.source_ids),
        "quorum": att.quorum,
        "proof_b64": att.proof_b64,
        "digest": att.digest(),
    }
    print(f"  round_id={att.round_id}")
    print(f"  digest={att.digest()}")
    print(f"  proof_b64 length={len(att.proof_b64)} (expect ~256 for 3×64)")

    print("\n[3] Loading ParityGate from config…")
    gate = load_parity_gate(args.config, clock=time.time)
    print(f"  gate min_quorum={gate.min_quorum} tolerance_bps={gate.tolerance_bps}")

    print("\n[4] Validating attestation…")
    try:
        digest = gate.validate(att, now=now + 1)
        print(f"  VALIDATE OK digest={digest}")
        status = "PASS"
    except Exception as exc:
        print(f"  VALIDATE FAIL: {exc}")
        status = "FAIL"

    if args.json_out:
        args.json_out.write_text(json.dumps(att_dict, indent=2) + "\n")
        print(f"\nWrote attestation → {args.json_out}")

    print(f"\n=== {status} ===")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
