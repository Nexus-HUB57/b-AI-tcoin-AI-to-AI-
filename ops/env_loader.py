#!/usr/bin/env python3
"""env_loader.py — Centralized environment & secrets loader for GO LIVE.

All secrets are loaded from env vars (never hardcoded). Supports:
  - Production: env vars injected via GitHub Actions → SSH → .env.production
  - Development: .env file in project root
  - Fallback: /etc/custody-sweep.env (legacy VPS)

SECURITY MODEL:
  - CUSTODY_SWAP_BTC: P2PKH address from env (was hardcoded before S1.4)
  - MYLINK_MASTER_KEY: 64-char hex key for vault encryption + signing
  - ANTHROPIC_API_KEY: Claude API key for activity engine
  - OPENAI_API_KEY: GPT API key for activity engine
  - All keys support rotation via env var update (no code change)
"""

import os
import json
import hashlib
import hmac
from pathlib import Path

# ── Project root detection ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("BAITCOIN_DATA", "/home/baitcoin/.baitcoin"))
ENV_PRODUCTION = DATA_DIR / ".env.production"
ENV_LOCAL = PROJECT_ROOT / ".env"
ENV_LEGACY = "/etc/custody-sweep.env"

_loaded = False

def _parse_env_file(path):
    """Parse a simple KEY=VALUE env file (no interpolation)."""
    env = {}
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    env[key.strip()] = val.strip()
    except (FileNotFoundError, PermissionError):
        pass
    return env

def load_env():
    """Load env vars from file hierarchy (does NOT override existing os.environ)."""
    global _loaded
    if _loaded:
        return
    
    # Priority: os.environ > .env.production > .env > /etc/custody-sweep.env
    sources = [ENV_PRODUCTION, ENV_LOCAL, ENV_LEGACY]
    for path in sources:
        parsed = _parse_env_file(path)
        for key, val in parsed.items():
            if key not in os.environ or not os.environ[key]:
                os.environ[key] = val
    
    _loaded = True

# ── Required secrets (will raise if missing in production) ──
CRITICAL_SECRETS = [
    "CUSTODY_SWAP_BTC",
    "MYLINK_MASTER_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
]

def require(key: str) -> str:
    """Get a required env var. Raises if missing."""
    load_env()
    val = os.environ.get(key, "")
    if not val:
        raise EnvironmentError(
            f"CRITICAL: Secret {key} is not set. "
            f"Set it in GitHub Secrets → .env.production or os.environ."
        )
    return val

def get(key: str, default: str = "") -> str:
    """Get an optional env var with default."""
    load_env()
    return os.environ.get(key, default)

# ── Typed accessors ──
def custody_btc_address() -> str:
    """Get the custody BTC address (P2PKH). Was hardcoded ADDRESSES[0] before S1.4."""
    addr = require("CUSTODY_SWAP_BTC")
    # Basic P2PKH validation (starts with 1 or 3, 25-34 chars)
    if not (len(addr) >= 25 and addr[0] in "13"):
        raise ValueError(f"CUSTODY_SWAP_BTC is not a valid P2PKH address: {addr[:8]}...")
    return addr

def custody_addresses() -> list:
    """Get all custody addresses (primary from env + extras from config)."""
    primary = custody_btc_address()
    extras = get("CUSTODY_ADDITIONAL_ADDRESSES", "")
    addrs = [primary]
    if extras:
        addrs.extend(a.strip() for a in extras.split(",") if a.strip())
    return addrs

def master_key() -> bytes:
    """Get the master encryption/signing key as bytes."""
    key_hex = require("MYLINK_MASTER_KEY")
    if len(key_hex) != 64:
        raise ValueError(f"MYLINK_MASTER_KEY must be 64 hex chars, got {len(key_hex)}")
    return bytes.fromhex(key_hex)

def anthropic_key() -> str:
    """Get Anthropic API key for Claude."""
    return require("ANTHROPIC_API_KEY")

def openai_key() -> str:
    """Get OpenAI API key for GPT."""
    return require("OPENAI_API_KEY")

def daemon_url() -> str:
    """Get daemon API URL."""
    return get("DAEMON_API_URL", "http://127.0.0.1:18445")

def staking_apy() -> float:
    """Get staking APY rate."""
    return float(get("STAKING_APY_RATE", "0.07"))

def is_armed() -> bool:
    """Check if custody sweep is ARMED for real broadcast."""
    return get("CUSTODY_ARMED", "false").lower() == "true"

# ── Session token rotation ──
def derive_session_key(purpose: str, rotation_epoch: int = 0) -> bytes:
    """Derive a purpose-specific session key from the master key.
    
    This enables key rotation: change rotation_epoch to invalidate
    all tokens signed with previous epochs, without changing the
    master key itself.
    
    Args:
        purpose: e.g. "session", "csrf", "api-token"
        rotation_epoch: increment to rotate (default 0 = no rotation)
    
    Returns:
        32-byte derived key
    """
    mk = master_key()
    ctx = f"{purpose}:{rotation_epoch}".encode()
    return hashlib.sha256(mk + ctx).digest()

def sign_token(payload: str, purpose: str = "session") -> str:
    """Sign a token payload with the current session key."""
    key = derive_session_key(purpose)
    return hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()

def verify_token(payload: str, signature: str, purpose: str = "session") -> bool:
    """Verify a token signature (constant-time comparison)."""
    expected = sign_token(payload, purpose)
    return hmac.compare_digest(expected, signature)

# ── Health check ──
def health_check():
    """Check all critical secrets are available. Returns (ok, missing)."""
    load_env()
    missing = [s for s in CRITICAL_SECRETS if not os.environ.get(s)]
    return len(missing) == 0, missing

# ── CLI ──
if __name__ == "__main__":
    import sys
    load_env()
    
    if "--check" in sys.argv:
        ok, missing = health_check()
        if ok:
            print("ALL SECRETS OK")
            for s in CRITICAL_SECRETS:
                val = os.environ.get(s, "")
                print(f"  {s}: {'*' * 8}{val[-4:] if len(val) > 4 else '(short)'}")
        else:
            print(f"MISSING SECRETS: {', '.join(missing)}")
            print("Set them in GitHub repo Settings > Secrets and run the GO LIVE workflow.")
        sys.exit(0 if ok else 1)
    
    elif "--addresses" in sys.argv:
        try:
            for a in custody_addresses():
                print(a)
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)
    
    else:
        print("Usage:")
        print("  env_loader.py --check       Validate all secrets are set")
        print("  env_loader.py --addresses   Print custody BTC addresses")
