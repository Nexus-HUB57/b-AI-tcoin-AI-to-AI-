#!/usr/bin/env python3
"""mempool_broadcast.py — On-chain TX broadcast via mempool.space API.

Provides a single entry point for broadcasting raw hex transactions to
the Bitcoin network via mempool.space/tx/push. Used by:
  - custody_sweep.py (sweep settlements)
  - swap_executor settlement (BTC/BAIT swaps)
  - A2A x402 settlement (agent-to-agent payments)

Usage:
    python3 mempool_broadcast.py --hex <raw_tx_hex> [--testnet]
    python3 mempool_broadcast.py --check <txid>

Environment:
    MEMPOOL_API_URL: override default (https://mempool.space/api)
    MEMPOOL_TESTNET: set to "true" for testnet3 (mempool.space/testnet/api)
"""

import json, os, sys, time, urllib.request, urllib.error

# ── Config ──
DEFAULT_MEMPOOL = "https://mempool.space/api"
DEFAULT_TESTNET = "https://mempool.space/testnet/api"

def get_api_base():
    """Resolve mempool API base URL from env."""
    if os.environ.get("MEMPOOL_API_URL"):
        return os.environ["MEMPOOL_API_URL"].rstrip("/")
    if os.environ.get("MEMPOOL_TESTNET", "").lower() == "true":
        return DEFAULT_TESTNET
    return DEFAULT_MEMPOOL

def broadcast_tx(raw_hex: str, api_base: str = None) -> dict:
    """Broadcast a raw transaction hex to mempool.space.
    
    Returns:
        dict with keys: ok (bool), txid (str), error (str|None), elapsed_ms (int)
    """
    if not raw_hex or not all(c in "0123456789abcdefABCDEF" for c in raw_hex):
        return {"ok": False, "txid": None, "error": "invalid hex string", "elapsed_ms": 0}
    
    api = api_base or get_api_base()
    url = f"{api}/tx"
    t0 = time.time()
    
    try:
        req = urllib.request.Request(
            url,
            data=raw_hex.encode("utf-8"),
            headers={"Content-Type": "text/plain"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8").strip()
        elapsed = int((time.time() - t0) * 1000)
        
        # mempool.space returns the txid on success
        is_valid_txid = len(body) == 64 and all(c in "0123456789abcdef" for c in body)
        if is_valid_txid:
            return {"ok": True, "txid": body, "error": None, "elapsed_ms": elapsed}
        else:
            return {"ok": False, "txid": body, "error": "unexpected response (not a txid)", "elapsed_ms": elapsed}
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")[:200]
        except Exception:
            pass
        elapsed = int((time.time() - t0) * 1000)
        # Common errors: "txn-already-in-mempool", "txn-mempool-conflict", "missing-inputs"
        return {"ok": False, "txid": None, "error": f"HTTP {e.code}: {body}", "elapsed_ms": elapsed}
    except Exception as e:
        elapsed = int((time.time() - t0) * 1000)
        return {"ok": False, "txid": None, "error": str(e)[:200], "elapsed_ms": elapsed}

def check_tx(txid: str, api_base: str = None) -> dict:
    """Check transaction status on mempool.space.
    
    Returns:
        dict with: found (bool), confirmations (int), status (str)
    """
    api = api_base or get_api_base()
    
    # First try /api/tx/{txid} (returns full tx if exists)
    try:
        url = f"{api}/tx/{txid}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            tx = json.loads(resp.read().decode())
        status = tx.get("status", {})
        confirmed = status.get("confirmed", False)
        block_height = status.get("block_height", 0)
        return {
            "found": True,
            "confirmed": confirmed,
            "block_height": block_height,
            "confirmations": status.get("confirmations", 0),
            "fee": tx.get("fee", 0),
        }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"found": False, "confirmed": False, "confirmations": 0}
        return {"found": False, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"found": False, "error": str(e)[:200]}

def get_fee_recommendation(api_base: str = None) -> dict:
    """Get recommended fee rates from mempool.space."""
    api = api_base or get_api_base()
    try:
        url = f"{api}/v1/fees/recommended"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)[:200], "halfHourFee": 10, "hourFee": 8, "minimumFee": 5}

# ── CLI ──
def main():
    args = sys.argv[1:]
    
    if "--hex" in args:
        idx = args.index("--hex")
        if idx + 1 >= len(args):
            print("Usage: mempool_broadcast.py --hex <raw_tx_hex>")
            sys.exit(1)
        raw_hex = args[idx + 1]
        result = broadcast_tx(raw_hex)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["ok"] else 1)
    
    elif "--check" in args:
        idx = args.index("--check")
        if idx + 1 >= len(args):
            print("Usage: mempool_broadcast.py --check <txid>")
            sys.exit(1)
        txid = args[idx + 1]
        result = check_tx(txid)
        print(json.dumps(result, indent=2))
        sys.exit(0)
    
    elif "--fees" in args:
        result = get_fee_recommendation()
        print(json.dumps(result, indent=2))
        sys.exit(0)
    
    else:
        print("Usage:")
        print("  mempool_broadcast.py --hex <raw_tx_hex>  Broadcast transaction")
        print("  mempool_broadcast.py --check <txid>      Check tx status")
        print("  mempool_broadcast.py --fees              Get fee recommendation")
        print("\nEnvironment:")
        print("  MEMPOOL_API_URL   Override API base URL")
        print("  MEMPOOL_TESTNET   Set to 'true' for testnet3")
        sys.exit(1)

if __name__ == "__main__":
    main()
