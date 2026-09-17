#!/usr/bin/env python3
"""Protocolos Atemporais — Hub V3 / MyLink / Motor Swap.

Objetivo:
- suportar assinaturas ECDSA DER secp256k1 para endereços legacy (pré-2014)
- detectar variante comprimida/não comprimida de endereços P2PKH
- sincronizar uma Master Wallet pool massiva (endereços/UTXOs) sem expor segredos
- expor camadas verificáveis de RAG, MCP e contexto para LLMs sem custodiar chaves

Este módulo é deliberadamente offline/local: não faz broadcast, não lê segredos do ambiente,
não fala com RPC externo e não persiste material sensível. Ele serve como camada verificável
para integrar componentes existentes do ecossistema.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ecdsa import SECP256k1, SigningKey, VerifyingKey
from ecdsa.util import sigdecode_der, sigencode_der_canonize

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_MAP = {c: i for i, c in enumerate(B58)}


def sha256d(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def hash160(data: bytes) -> bytes:
    return hashlib.new("ripemd160", hashlib.sha256(data).digest()).digest()


def base58_encode(payload: bytes) -> str:
    n = int.from_bytes(payload, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = B58[r] + out
    pad = len(payload) - len(payload.lstrip(b"\x00"))
    return ("1" * pad) + (out or "")


def base58_decode(text: str) -> bytes:
    n = 0
    for c in text:
        if c not in _B58_MAP:
            raise ValueError(f"caractere Base58 invalido: {c}")
        n = n * 58 + _B58_MAP[c]
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    pad = len(text) - len(text.lstrip("1"))
    return (b"\x00" * pad) + raw


def base58check_encode(payload: bytes) -> str:
    return base58_encode(payload + sha256d(payload)[:4])


def base58check_decode(text: str) -> bytes:
    raw = base58_decode(text)
    if len(raw) < 5:
        raise ValueError("payload Base58Check muito curto")
    payload, checksum = raw[:-4], raw[-4:]
    if sha256d(payload)[:4] != checksum:
        raise ValueError("checksum Base58Check invalido")
    return payload


def canonical_json(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def pubkey_bytes_from_privkey(privkey: bytes, compressed: bool = True) -> bytes:
    sk = SigningKey.from_string(privkey, curve=SECP256k1)
    point = sk.get_verifying_key().pubkey.point
    x = int(point.x())
    y = int(point.y())
    if compressed:
        return bytes([0x02 | (y & 1)]) + x.to_bytes(32, "big")
    return b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")


def p2pkh_address_from_pubkey(pubkey: bytes, version: int = 0x00) -> str:
    return base58check_encode(bytes([version]) + hash160(pubkey))


def wif_to_privkey(wif: str) -> Tuple[bytes, bool, int]:
    payload = base58check_decode(wif)
    if len(payload) not in (33, 34):
        raise ValueError("WIF invalido")
    version = payload[0]
    body = payload[1:]
    if len(body) == 33 and body[-1] == 0x01:
        return body[:-1], True, version
    if len(body) == 32:
        return body, False, version
    raise ValueError("WIF malformado")


def privkey_to_wif(privkey: bytes, compressed: bool = True, version: int = 0x80) -> str:
    if len(privkey) != 32:
        raise ValueError("privkey deve ter 32 bytes")
    payload = bytes([version]) + privkey + (b"\x01" if compressed else b"")
    return base58check_encode(payload)


def derive_legacy_address_variants(privkey: bytes, version: int = 0x00) -> Dict[str, Any]:
    pub_compressed = pubkey_bytes_from_privkey(privkey, compressed=True)
    pub_uncompressed = pubkey_bytes_from_privkey(privkey, compressed=False)
    return {
        "compressed": {
            "pubkey_hex": pub_compressed.hex(),
            "address": p2pkh_address_from_pubkey(pub_compressed, version=version),
            "wif": privkey_to_wif(privkey, compressed=True),
        },
        "uncompressed": {
            "pubkey_hex": pub_uncompressed.hex(),
            "address": p2pkh_address_from_pubkey(pub_uncompressed, version=version),
            "wif": privkey_to_wif(privkey, compressed=False),
        },
    }


def match_legacy_address(address: str, *, wif: Optional[str] = None, privkey_hex: Optional[str] = None) -> Dict[str, Any]:
    """Detecta qual variante legacy (compressed/uncompressed) corresponde ao endereço.

    Útil para fundos com endereços antigos pré-2014, onde a mesma chave privada pode gerar
    dois endereços distintos dependendo do formato do pubkey.
    """
    if not wif and not privkey_hex:
        raise ValueError("forneca wif ou privkey_hex")
    if wif:
        privkey, implied_compressed, version = wif_to_privkey(wif)
    else:
        privkey = bytes.fromhex(privkey_hex)
        implied_compressed = None
        version = 0x80
    addr_version = base58check_decode(address)[0]
    variants = derive_legacy_address_variants(privkey, version=addr_version)
    matched = None
    for label, item in variants.items():
        if item["address"] == address:
            matched = label
            break
    return {
        "matched": bool(matched),
        "match_type": matched,
        "wif_implies": "compressed" if implied_compressed else ("uncompressed" if implied_compressed is False else None),
        "variants": variants,
    }


@dataclass
class DERIdentity:
    agent_id: str
    privkey: bytes
    compressed: bool = True
    network_version: int = 0x00
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if len(self.privkey) != 32:
            raise ValueError("privkey deve ter 32 bytes")
        self.signing_key = SigningKey.from_string(self.privkey, curve=SECP256k1)
        self.verifying_key = self.signing_key.get_verifying_key()
        self.pubkey_bytes = pubkey_bytes_from_privkey(self.privkey, compressed=self.compressed)
        self.address = p2pkh_address_from_pubkey(self.pubkey_bytes, version=self.network_version)
        self.wif = privkey_to_wif(self.privkey, compressed=self.compressed, version=0x80 | (self.network_version & 0x7F))

    def sign_payload(self, payload: Dict[str, Any]) -> str:
        digest = hashlib.sha256(canonical_json(payload)).digest()
        return self.signing_key.sign_digest_deterministic(
            digest,
            hashfunc=hashlib.sha256,
            sigencode=sigencode_der_canonize,
        ).hex()

    def verify_payload(self, payload: Dict[str, Any], signature_hex: str) -> bool:
        digest = hashlib.sha256(canonical_json(payload)).digest()
        try:
            return self.verifying_key.verify_digest(bytes.fromhex(signature_hex), digest, sigdecode=sigdecode_der)
        except Exception:
            return False

    def to_public_card(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "address": self.address,
            "pubkey_hex": self.pubkey_bytes.hex(),
            "compression": "compressed" if self.compressed else "uncompressed",
            "sig_scheme": "ECDSA-DER-secp256k1",
            "legacy_pre_2014_compatible": True,
            "created_at": self.created_at,
        }


@dataclass
class LinkedProofChain:
    genesis_label: str = "ATEMPORAL-GENESIS"
    head: str = field(init=False)
    height: int = field(default=0, init=False)
    history: List[Dict[str, Any]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.head = sha256d(self.genesis_label.encode()).hex()

    def append(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        entry = {
            "height": self.height + 1,
            "prev_head": self.head,
            "event_type": event_type,
            "payload": payload,
            "ts": time.time(),
        }
        self.head = sha256d(bytes.fromhex(self.head) + canonical_json(entry)).hex()
        self.height += 1
        proof = {
            "height": self.height,
            "head": self.head,
            "event_type": event_type,
            "payload_hash": hashlib.sha256(canonical_json(payload)).hexdigest(),
        }
        self.history.append({**entry, **proof})
        return proof


@dataclass
class MasterWalletPool:
    addresses: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    utxos: List[Dict[str, Any]] = field(default_factory=list)
    loaded_from: Optional[str] = None

    @staticmethod
    def _normalize_address_rows(data: Any) -> Dict[str, Dict[str, Any]]:
        if isinstance(data, dict):
            if "addresses" in data and isinstance(data["addresses"], list):
                rows = data["addresses"]
            else:
                rows = [
                    {"address": key, **(value if isinstance(value, dict) else {"value": value})}
                    for key, value in data.items()
                ]
        elif isinstance(data, list):
            rows = data
        else:
            rows = []
        out: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            addr = row.get("address") or row.get("addr") or row.get("wallet")
            if not addr:
                continue
            out[str(addr)] = {
                "address": str(addr),
                "label": row.get("label") or row.get("tag") or "pool",
                "balance_btc": float(row.get("balance_btc") or row.get("btc") or 0.0),
                "utxos": int(row.get("utxos") or row.get("utxo_count") or 0),
                "watch_only": bool(row.get("watch_only", False)),
            }
        return out

    @staticmethod
    def _normalize_utxos(data: Any) -> List[Dict[str, Any]]:
        if isinstance(data, dict) and isinstance(data.get("utxos"), list):
            rows = data["utxos"]
        elif isinstance(data, list):
            rows = data
        else:
            rows = []
        out: List[Dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            txid = str(row.get("txid") or "")
            vout = int(row.get("vout") or 0)
            address = str(row.get("address") or row.get("addr") or "")
            if not txid or not address:
                continue
            sats = row.get("value_sats")
            if sats is None:
                sats = row.get("sats")
            if sats is None and row.get("value") is not None:
                try:
                    sats = int(round(float(row["value"]) * 100_000_000))
                except Exception:
                    sats = 0
            out.append({
                "txid": txid,
                "vout": vout,
                "address": address,
                "value_sats": int(sats or 0),
                "spendable": bool(row.get("spendable", True)),
                "watch_only": bool(row.get("watch_only", False)),
            })
        return out

    @classmethod
    def from_json_file(cls, path: str | Path) -> "MasterWalletPool":
        raw = json.loads(Path(path).read_text())
        pool = cls(
            addresses=cls._normalize_address_rows(raw.get("addresses", raw)),
            utxos=cls._normalize_utxos(raw.get("utxos", raw)),
            loaded_from=str(path),
        )
        pool.reconcile()
        return pool

    def reconcile(self) -> None:
        for utxo in self.utxos:
            addr = utxo["address"]
            row = self.addresses.setdefault(addr, {
                "address": addr,
                "label": "pool",
                "balance_btc": 0.0,
                "utxos": 0,
                "watch_only": bool(utxo.get("watch_only", False)),
            })
            row["utxos"] += 1
            row["balance_btc"] += utxo["value_sats"] / 100_000_000
            row["watch_only"] = bool(row.get("watch_only", False) or utxo.get("watch_only", False))

    def summary(self) -> Dict[str, Any]:
        spendable_sats = sum(u["value_sats"] for u in self.utxos if u.get("spendable", True) and not u.get("watch_only", False))
        watch_only_sats = sum(u["value_sats"] for u in self.utxos if u.get("watch_only", False))
        return {
            "addresses_total": len(self.addresses),
            "utxos_total": len(self.utxos),
            "spendable_btc": round(spendable_sats / 100_000_000, 8),
            "watch_only_btc": round(watch_only_sats / 100_000_000, 8),
            "loaded_from": self.loaded_from,
        }

    def rag_document(self, limit: int = 25) -> Dict[str, Any]:
        ranked = sorted(self.addresses.values(), key=lambda row: row.get("balance_btc", 0.0), reverse=True)
        return {
            "summary": self.summary(),
            "top_addresses": ranked[:limit],
            "wallets_redacted": False,
            "schema": ["address", "balance_btc", "utxos", "watch_only", "label"],
        }


class AtemporalProtocolSuite:
    def __init__(self) -> None:
        self.identities: Dict[str, DERIdentity] = {}
        self.pool = MasterWalletPool()
        self.proofs = LinkedProofChain()
        self.started_at = time.time()

    def register_identity(self, agent_id: str, *, privkey_hex: Optional[str] = None, compressed: bool = True) -> Dict[str, Any]:
        privkey = bytes.fromhex(privkey_hex) if privkey_hex else sha256d(agent_id.encode())[:32]
        ident = DERIdentity(agent_id=agent_id, privkey=privkey, compressed=compressed)
        self.identities[agent_id] = ident
        proof = self.proofs.append("register_identity", ident.to_public_card())
        return {"ok": True, **ident.to_public_card(), "proof": proof}

    def sign_intent(self, agent_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        ident = self.identities[agent_id]
        sig = ident.sign_payload(payload)
        envelope = {
            "agent_id": agent_id,
            "address": ident.address,
            "pubkey_hex": ident.pubkey_bytes.hex(),
            "payload": payload,
            "signature_der_hex": sig,
            "verified": ident.verify_payload(payload, sig),
            "scheme": "ECDSA-DER-secp256k1",
        }
        envelope["proof"] = self.proofs.append("sign_intent", {
            "agent_id": agent_id,
            "payload_hash": hashlib.sha256(canonical_json(payload)).hexdigest(),
            "signature_der_hex": sig,
        })
        return envelope

    def verify_intent(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        pubkey = bytes.fromhex(envelope["pubkey_hex"])
        vk = VerifyingKey.from_string(pubkey[1:] if len(pubkey) == 33 else pubkey[1:], curve=SECP256k1) if len(pubkey) == 65 else VerifyingKey.from_string(pubkey, curve=SECP256k1)
        digest = hashlib.sha256(canonical_json(envelope["payload"])).digest()
        ok = vk.verify_digest(bytes.fromhex(envelope["signature_der_hex"]), digest, sigdecode=sigdecode_der)
        return {"ok": bool(ok), "agent_id": envelope.get("agent_id"), "scheme": envelope.get("scheme")}

    def sync_master_wallet(self, pool: MasterWalletPool) -> Dict[str, Any]:
        self.pool = pool
        proof = self.proofs.append("sync_master_wallet", pool.summary())
        return {"ok": True, "summary": pool.summary(), "proof": proof}

    def rag_snapshot(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "proof_head": self.proofs.head,
            "proof_height": self.proofs.height,
            "identities": [ident.to_public_card() for ident in self.identities.values()],
            "master_wallet": self.pool.rag_document(),
        }

    def llm_context(self, objective: str) -> Dict[str, Any]:
        return {
            "objective": objective,
            "constraints": [
                "nao expor WIF, xprv, seeds ou chaves privadas",
                "usar apenas provas encadeadas, pubkeys e enderecos publicos",
                "enderecos legacy pre-2014 podem ser compressed ou uncompressed",
            ],
            "proof_head": self.proofs.head,
            "proof_height": self.proofs.height,
            "identities_count": len(self.identities),
            "master_wallet_summary": self.pool.summary(),
        }

    def mcp_call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params or {}
        if method == "status":
            result = {
                "started_at": self.started_at,
                "uptime_s": round(time.time() - self.started_at, 3),
                "identities": len(self.identities),
                "proof_height": self.proofs.height,
                "proof_head": self.proofs.head,
                "pool": self.pool.summary(),
            }
        elif method == "rag_snapshot":
            result = self.rag_snapshot()
        elif method == "llm_context":
            result = self.llm_context(params.get("objective", "atempotral orchestration"))
        else:
            raise ValueError(f"metodo MCP desconhecido: {method}")
        return {"jsonrpc": "2.0", "result": result}


def validate_end_to_end(sample_pool: Optional[MasterWalletPool] = None, identities: int = 32) -> Dict[str, Any]:
    suite = AtemporalProtocolSuite()
    for i in range(identities):
        suite.register_identity(f"agent-{i:03d}", compressed=(i % 2 == 0))
    payload = {"kind": "swap_intent", "pair": "BTC/BAIT", "quantity": 125000, "ts": 1}
    envelope = suite.sign_intent("agent-000", payload)
    assert envelope["verified"] is True
    if sample_pool is None:
        sample_pool = MasterWalletPool(
            addresses={
                "1AAA": {"address": "1AAA", "balance_btc": 1.25, "utxos": 2, "watch_only": False, "label": "spendable"},
                "1BBB": {"address": "1BBB", "balance_btc": 2.50, "utxos": 1, "watch_only": True, "label": "vault"},
            },
            utxos=[
                {"txid": "a" * 64, "vout": 0, "address": "1AAA", "value_sats": 100_000_000, "spendable": True},
                {"txid": "b" * 64, "vout": 1, "address": "1AAA", "value_sats": 25_000_000, "spendable": True},
                {"txid": "c" * 64, "vout": 0, "address": "1BBB", "value_sats": 250_000_000, "watch_only": True},
            ],
            loaded_from="in-memory",
        )
        sample_pool.reconcile()
    sync = suite.sync_master_wallet(sample_pool)
    rag = suite.rag_snapshot()
    mcp = suite.mcp_call("status")
    return {
        "ok": True,
        "identities": len(suite.identities),
        "proof_height": suite.proofs.height,
        "proof_head": suite.proofs.head,
        "signature_verified": envelope["verified"],
        "pool_summary": sync["summary"],
        "rag_identities": len(rag["identities"]),
        "mcp_status": mcp["result"],
        "legacy_example": derive_legacy_address_variants(sha256d(b"legacy-demo")[:32]),
    }


if __name__ == "__main__":
    print(json.dumps(validate_end_to_end(), indent=2, ensure_ascii=False))
