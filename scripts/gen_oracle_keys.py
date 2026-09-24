#!/usr/bin/env python3
"""Gera 3 keypairs Schnorr BIP-340 para oráculos de parity (produção / staging).

Uso:
  python3 scripts/gen_oracle_keys.py --out-dir ./secrets/oracles --password-env ORACLE_KEY_PASSWORD
  python3 scripts/gen_oracle_keys.py --out-dir ./secrets/oracles --password-file ./secrets/.oracle_pw

Saídas (por oráculo):
  oracle-{a,b,c}.key          — chave privada criptografada (scrypt + AES-GCM, mode 0600)
  oracle-{a,b,c}.pub          — pubkey x-only hex (32 bytes) — pode ser pública
  authorized_pubkeys.json     — mapa source_id → pubkey hex (para ParityGate)

NUNCA commitar os arquivos .key nem a senha.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from native_processing.schnorr_keypair import SchnorrKeyPair  # noqa: E402


ORACLE_IDS = ("oracle-a", "oracle-b", "oracle-c")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 3 Schnorr BIP-340 oracle keypairs")
    parser.add_argument("--out-dir", type=Path, required=True, help="Directory for key files")
    parser.add_argument("--password-env", type=str, default=None, help="Env var holding password")
    parser.add_argument("--password-file", type=Path, default=None, help="File containing password")
    parser.add_argument("--force", action="store_true", help="Overwrite existing keys")
    args = parser.parse_args()

    if args.password_env:
        password = os.environ.get(args.password_env, "").encode()
        if not password:
            print(f"ERROR: env var {args.password_env} is empty", file=sys.stderr)
            return 2
    elif args.password_file:
        password = args.password_file.read_bytes().strip()
        if not password:
            print("ERROR: password file is empty", file=sys.stderr)
            return 2
    else:
        print("ERROR: provide --password-env or --password-file", file=sys.stderr)
        return 2

    if len(password) < 16:
        print("WARNING: password shorter than 16 bytes — consider a stronger secret", file=sys.stderr)

    out: Path = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    out.chmod(0o700)

    authorized: dict[str, str] = {}
    for oid in ORACLE_IDS:
        key_path = out / f"{oid}.key"
        pub_path = out / f"{oid}.pub"

        if key_path.exists() and not args.force:
            print(f"SKIP {oid}: {key_path} already exists (use --force)")
            # still collect pubkey if .pub exists
            if pub_path.exists():
                authorized[oid] = pub_path.read_text().strip()
            continue

        kp = SchnorrKeyPair.generate()
        kp.save_encrypted(key_path, password)
        pub_path.write_text(kp.public_key_hex + "\n")
        pub_path.chmod(0o644)
        authorized[oid] = kp.public_key_hex
        print(f"OK  {oid}: pubkey={kp.public_key_hex}")
        # zero sensitive material in this scope
        del kp

    auth_path = out / "authorized_pubkeys.json"
    auth_path.write_text(json.dumps(authorized, indent=2, sort_keys=True) + "\n")
    auth_path.chmod(0o644)
    print(f"\nWrote {auth_path}")
    print("Remember: never commit *.key files or the password.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
