#!/usr/bin/env python3
r"""
mylink_fund_eth_burn.py — Workflow "Fundo MyLink" de queima de gas ETH
====================================================================

Valida o Motor Swap Sweep BAITHex enviando uma transação EIP-155 da
carteira operacional do Fundo MyLink para o endereço de queima
(configurável, default `0x000000000000000000000000000000000000dEaD`).

Gates:
  • ARM gate (MYLINK_FUND_ETH_BURN_ARMED=true) — sem isso, dry-run
  • Saldo mínimo (ETH_MIN_BALANCE_WEI) — aborta se pós-queima ficar abaixo
  • Limite de gas (ETH_MAX_GAS_WEI) — aborta se gas cost estimado passar
  • Chain-id mismatch (ETH_EXPECTED_CHAIN_ID) — aborta se chain não bater

Segurança (linha com `docs/AGENT_PRIVATE_KEY_SECURITY_SPEC.md`):
  • Keystore lido de KEYSTORE_ETH_FUNDO_MYLINK (path ou JSON inline)
  • Passphrase lida de KEYSTORE_ETH_FUNDO_MYLINK_PASSWORD
  • Chave privada descriptografada existe APENAS em memória
  • Sobrescrita com 0x00 antes de sair
  • Nenhum log imprime keystore, passphrase, raw tx, ou chave privada

Uso local (simulação):
    MYLINK_FUND_ETH_BURN_ARMED=false \\
    ETH_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/xxx \\
    python3 ops/mylink_fund_eth_burn.py

Produção (com secrets no GitHub Actions Secrets):
    KEYSTORE_ETH_FUNDO_MYLINK          conteúdo JSON do keystore
    KEYSTORE_ETH_FUNDO_MYLINK_PASSWORD passphrase do keystore
    ETH_RPC_URL                        endpoint JSON-RPC
    MYLINK_FUND_ETH_BURN_ARMED         "true" para execução real
    ETH_BURN_AMOUNT_WEI                opcional (default 0)
    ETH_BURN_ADDRESS                   opcional (default 0x...dead)
    ETH_MIN_BALANCE_WEI                opcional (default 0)
    ETH_MAX_GAS_WEI                    opcional
    ETH_EXPECTED_CHAIN_ID              opcional (default 1 = mainnet)
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

# --------------------------------------------------------------------- logging

logging.basicConfig(
    level=os.environ.get("MYLINK_LOG_LEVEL", "INFO"),
    format="%(asctime)sZ [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("mylink_fund_eth_burn")

BURN_ADDRESS_DEFAULT = "0x000000000000000000000000000000000000dEaD"


# ----------------------------------------------------------------- env helpers

def _env_required(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        log.error("missing required env var: %s", name)
        sys.exit(2)
    return val


def _env_optional(name: str, default: str) -> str:
    return os.environ.get(name, "").strip() or default


def _env_int_optional(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        log.error("env var %s must be an integer, got %r", name, raw)
        sys.exit(2)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "armed", "on")


# ---------------------------------------------------------------- keystore

@dataclass
class Keystore:
    address: str          # lowercase
    crypto: dict
    raw_bytes: bytes      # raw JSON, NEVER logged


def _load_keystore_from_inline_json(raw: str) -> Keystore:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error("KEYSTORE_ETH_FUNDO_MYLINK is not valid JSON: %s", e)
        sys.exit(2)
    if "address" not in data and "crypto" not in data and "Crypto" in data:
        data = {"address": "", "crypto": data["Crypto"]}
    if "crypto" not in data:
        log.error("keystore missing 'crypto' field")
        sys.exit(2)
    addr = data.get("address", "")
    if addr and not addr.startswith("0x"):
        addr = "0x" + addr
    return Keystore(address=addr.lower(), crypto=data["crypto"],
                    raw_bytes=raw.encode("utf-8"))


def _load_keystore_from_path(path: str) -> Keystore:
    if not os.path.isfile(path):
        log.error("keystore file not found: %s", path)
        sys.exit(2)
    with open(path, "rb") as f:
        return _load_keystore_from_inline_json(f.read().decode("utf-8"))


def load_keystore(env_value: str) -> Keystore:
    s = env_value.strip()
    if s.startswith("{") and s.endswith("}"):
        return _load_keystore_from_inline_json(s)
    return _load_keystore_from_path(s)


def decrypt_keystore(keystore: Keystore, password: str) -> bytes:
    """Decrypt a Web3 Secret Storage keystore (scrypt + AES-128-CTR + MAC).

    Returns the 32-byte raw private key. Raises SystemExit on any failure.
    """
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    from Crypto.Hash import keccak  # type: ignore  # pycryptodome

    crypto = keystore.crypto
    kdf = crypto.get("kdf", "scrypt")
    if kdf != "scrypt":
        log.error("unsupported keystore KDF: %s (only scrypt is supported)", kdf)
        sys.exit(2)
    p = crypto["kdfparams"]
    dklen = int(p["dklen"])
    salt = bytes.fromhex(p["salt"])
    n, r, pp = int(p["n"]), int(p["r"]), int(p["p"])

    derived = Scrypt(salt=salt, length=dklen, n=n, r=r, p=pp,
                     backend=default_backend()).derive(password.encode("utf-8"))

    ciphertext = bytes.fromhex(crypto["ciphertext"])
    iv = bytes.fromhex(crypto["cipherparams"]["iv"])
    cipher = Cipher(algorithms.AES(derived[:16]), modes.CTR(iv), backend=default_backend())
    plaintext = cipher.decryptor().update(ciphertext) + cipher.decryptor().finalize()

    mac_expected = bytes.fromhex(crypto["mac"])
    mac_computed = keccak.new(digest_bits=256, data=derived[16:32] + ciphertext).digest()
    if not secrets.compare_digest(mac_expected, mac_computed):
        log.error("keystore MAC mismatch — wrong passphrase or corrupted keystore")
        sys.exit(2)
    if len(plaintext) != 32:
        log.error("decrypted key length %d (expected 32)", len(plaintext))
        sys.exit(2)
    log.info("keystore decrypted (scrypt n=%d r=%d p=%d); address=%s",
             n, r, pp, keystore.address)
    return plaintext


# ----------------------------------------------------------------- JSON-RPC

class JsonRpcError(RuntimeError):
    pass


def _rpc(rpc_url: str, method: str, params: list, *, timeout: int = 30) -> Any:
    payload = {"jsonrpc": "2.0", "id": int(time.time() * 1000) % (10**9),
               "method": method, "params": params}
    req = urllib.request.Request(
        rpc_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    except urllib.error.URLError as e:
        raise JsonRpcError(f"RPC unreachable: {e}") from e
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as e:
        raise JsonRpcError(f"RPC returned non-JSON: {body[:200]!r}") from e
    if "error" in parsed:
        raise JsonRpcError(f"RPC error: {parsed['error']}")
    return parsed.get("result")


def get_chain_id(rpc_url: str) -> int:
    return int(_rpc(rpc_url, "eth_chainId", []), 16)


def get_balance(rpc_url: str, address: str) -> int:
    return int(_rpc(rpc_url, "eth_getBalance", [address, "latest"]), 16)


def get_nonce(rpc_url: str, address: str) -> int:
    return int(_rpc(rpc_url, "eth_getTransactionCount", [address, "pending"]), 16)


def get_gas_price(rpc_url: str) -> int:
    return int(_rpc(rpc_url, "eth_gasPrice", []), 16)


def send_raw_tx(rpc_url: str, raw_hex: str) -> str:
    return _rpc(rpc_url, "eth_sendRawTransaction", [raw_hex])


def get_tx_receipt(rpc_url: str, txhash: str, *, timeout_s: int = 180) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = _rpc(rpc_url, "eth_getTransactionReceipt", [txhash])
        if r is not None:
            return r
        time.sleep(3)
    raise JsonRpcError(f"timed out waiting for receipt of {txhash}")


# ----------------------------------------------------------------- main

def main() -> int:
    log.info("=== MyLink Fund — ETH Gas Burn workflow starting ===")

    armed = _env_bool("MYLINK_FUND_ETH_BURN_ARMED", default=False)
    rpc_url = _env_required("ETH_RPC_URL")
    burn_address = _env_optional("ETH_BURN_ADDRESS", BURN_ADDRESS_DEFAULT).lower()
    if not (burn_address.startswith("0x") and len(burn_address) == 42):
        log.error("ETH_BURN_ADDRESS invalid: %r (expected 0x + 40 hex)", burn_address)
        return 2
    burn_amount_wei = _env_int_optional("ETH_BURN_AMOUNT_WEI", 0)
    min_balance_wei = _env_int_optional("ETH_MIN_BALANCE_WEI", 0)
    max_gas_wei = _env_int_optional("ETH_MAX_GAS_WEI", 100 * 10**9 * 21000)
    expected_chain_id = _env_int_optional("ETH_EXPECTED_CHAIN_ID", 1)

    log.info(
        "config: armed=%s burn=%s amount_wei=%d min_balance_wei=%d "
        "max_gas_wei=%d expected_chain_id=%d",
        armed, burn_address, burn_amount_wei, min_balance_wei, max_gas_wei,
        expected_chain_id,
    )

    # --- Chain ID sanity ---
    chain_id = get_chain_id(rpc_url)
    log.info("eth_chainId: %d", chain_id)
    if chain_id != expected_chain_id:
        log.error("chain_id mismatch (got %d, expected %d) — refusing to sign",
                  chain_id, expected_chain_id)
        return 3

    # --- Keystore ---
    keystore_env = _env_required("KEYSTORE_ETH_FUNDO_MYLINK")
    passphrase = _env_required("KEYSTORE_ETH_FUNDO_MYLINK_PASSWORD")
    keystore = load_keystore(keystore_env)

    privkey_buf = bytearray(decrypt_keystore(keystore, passphrase))
    del passphrase  # wipe local ref

    try:
        # --- Pre-flight ---
        balance_wei = get_balance(rpc_url, keystore.address)
        log.info("balance: %s wei (%s ETH)",
                 balance_wei, Decimal(balance_wei) / Decimal(10**18))

        nonce = get_nonce(rpc_url, keystore.address)
        log.info("nonce: %d", nonce)

        gas_price = get_gas_price(rpc_url)
        log.info("gas_price: %d wei (%s gwei)",
                 gas_price, Decimal(gas_price) / Decimal(10**9))

        est_gas_cost = gas_price * 21000
        log.info("est_gas_cost: %d wei", est_gas_cost)
        if est_gas_cost > max_gas_wei:
            log.error("gas cost %d exceeds max_gas_wei=%d — aborting",
                      est_gas_cost, max_gas_wei)
            return 4

        total_outflow = burn_amount_wei + est_gas_cost
        if balance_wei < total_outflow:
            log.error("insufficient balance: have %d, need %d (burn + gas)",
                      balance_wei, total_outflow)
            return 5

        post_balance = balance_wei - total_outflow
        if post_balance < min_balance_wei:
            log.error("post-burn balance %d below min_balance_wei=%d",
                      post_balance, min_balance_wei)
            return 6

        # --- Sign + broadcast (delegates to eth-account if installed) ---
        try:
            from eth_account import Account  # type: ignore
            from eth_account._utils.legacy_transactions import Transaction, encode_transaction  # type: ignore
        except ImportError:
            log.error(
                "eth-account not installed. Run `pip install eth-account` to enable signing."
                " In dry-run mode (armed=false) the script exits 0 without signing.",
            )
            return 0 if not armed else 9

        # Build legacy EIP-155 tx
        tx = Transaction(
            nonce=nonce,
            gasPrice=gas_price,
            gas=21000,
            to=bytes.fromhex(burn_address[2:]),
            value=burn_amount_wei,
            data=b"",
            chainId=chain_id,
        )
        signed = Account.sign_transaction(tx, bytes(privkey_buf))
        raw_hex = "0x" + signed.raw_transaction.hex()

        log.info(
            "tx ready: nonce=%d gas_price=%d value=%d to=%s gas=21000",
            nonce, gas_price, burn_amount_wei, burn_address,
        )
        log.info("raw tx length: %d bytes", len(signed.raw_transaction))

        if not armed:
            log.warning("=== ARMED=FALSE: simulation mode — not broadcasting ===")
            log.info("would broadcast tx from %s", keystore.address)
            return 0

        log.info("=== ARMED=TRUE: broadcasting tx ===")
        txhash = send_raw_tx(rpc_url, raw_hex)
        log.info("tx sent: %s", txhash)

        log.info("waiting for receipt (timeout 180s)…")
        receipt = get_tx_receipt(rpc_url, txhash, timeout_s=180)
        status = int(receipt.get("status", "0x0"), 16)
        block = int(receipt.get("blockNumber", "0x0"), 16)
        gas_used = int(receipt.get("gasUsed", "0x0"), 16)

        log.info("receipt: block=%d status=%d gas_used=%d", block, status, gas_used)
        if status != 1:
            log.error("tx reverted (status=0) — block=%d txhash=%s", block, txhash)
            return 8

        log.info("=== MyLink Fund — ETH Gas Burn SUCCESS ===")
        log.info("txhash: %s", txhash)
        log.info("block:  %d", block)
        log.info("gas:    %d wei (%s ETH)",
                 gas_used * gas_price,
                 Decimal(gas_used * gas_price) / Decimal(10**18))
        return 0
    finally:
        # Zero the privkey buffer
        for i in range(len(privkey_buf)):
            privkey_buf[i] = 0


if __name__ == "__main__":
    sys.exit(main())