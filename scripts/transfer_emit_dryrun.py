#!/usr/bin/env python3
"""Build a BAIT L1 transfer payload (dry-run by default).

Does NOT broadcast. Use on full-node host with real UTXO + keys.

  python3 scripts/transfer_emit_dryrun.py --from-coinbase-txid <txid> --vout 0 \\
      --to b'/t... --amount-bait 1 --agent-id chimera7-defi

G-03 PASS requires this tx type=transfer to appear in explorer after mining.
"""
from __future__ import annotations
import argparse, hashlib, json, time, sys
from typing import Any

def sha256d(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

def build_transfer(
    *,
    prev_txid: str,
    vout: int,
    to_address: str,
    amount_bait: float,
    agent_id: str,
    change_address: str | None = None,
    change_bait: float = 0.0,
) -> dict[str, Any]:
    amount_sats = int(round(amount_bait * 1e8))
    outs = [{"amount_sats": amount_sats, "address": to_address, "output_index": 0}]
    if change_address and change_bait > 0:
        outs.append({
            "amount_sats": int(round(change_bait * 1e8)),
            "address": change_address,
            "output_index": 1,
        })
    raw = {
        "tx_type": "transfer",
        "agent_id": agent_id,
        "timestamp": time.time(),
        "inputs": [{
            "prev_tx_hash": prev_txid,
            "output_index": vout,
            "pubkey_hex": None,
            "signature_hex": None,
        }],
        "outputs": outs,
    }
    canon = json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()
    raw["tx_id"] = sha256d(canon).hex()
    raw["status"] = "UNSIGNED_DRY_RUN"
    raw["note"] = (
        "Sign inputs with BIP-340 over canonical body, submit to full-node mempool, "
        "mine 1 block. Explorer must show tx_type=transfer for G-03 PASS."
    )
    return raw

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--from-coinbase-txid", required=True)
    p.add_argument("--vout", type=int, default=0)
    p.add_argument("--to", required=True, help="destination b'/t address")
    p.add_argument("--amount-bait", type=float, required=True)
    p.add_argument("--agent-id", default="baithex-g03-emitter")
    p.add_argument("--change-address", default="")
    p.add_argument("--change-bait", type=float, default=0.0)
    p.add_argument("--broadcast", action="store_true",
                   help="reserved; refused in sandbox (always dry-run)")
    args = p.parse_args()
    if args.broadcast:
        print(json.dumps({"ok": False, "error": "broadcast_refused_in_sandbox_use_host_full_node"}))
        return 2
    tx = build_transfer(
        prev_txid=args.from_coinbase_txid,
        vout=args.vout,
        to_address=args.to,
        amount_bait=args.amount_bait,
        agent_id=args.agent_id,
        change_address=args.change_address or None,
        change_bait=args.change_bait,
    )
    print(json.dumps(tx, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
