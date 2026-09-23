"""Read-only xpub/address/UTXO reconciliation primitives for MyLink custody."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Mapping

from embit.bip32 import HDKey


class ReconciliationError(ValueError):
    pass


def _hash160(data: bytes) -> bytes:
    return hashlib.new("ripemd160", hashlib.sha256(data).digest()).digest()


def _bech32_encode(hrp: str, version: int, program: bytes) -> str:
    alphabet = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    def convert(data, frombits=8, tobits=5):
        acc = bits = 0; out = []
        for value in data:
            acc = (acc << frombits) | value; bits += frombits
            while bits >= tobits:
                bits -= tobits; out.append((acc >> bits) & 31)
        if bits: out.append((acc << (tobits - bits)) & 31)
        return out
    values = [version] + convert(program)
    const = 1 if version == 0 else 0x2bc830a3
    expanded = [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]
    chk = 1
    for v in expanded + values + [0] * 6:
        top = chk >> 25; chk = ((chk & 0x1ffffff) << 5) ^ v
        for i, g in enumerate((0x3b6a57b2,0x26508e6d,0x1ea119fa,0x3d4233dd,0x2a1462b3)):
            if (top >> i) & 1: chk ^= g
    return hrp + "1" + "".join(alphabet[x] for x in values + [(chk ^ const) >> (5 * (5-i)) & 31 for i in range(6)])


def derive_address(xpub: str, branch: int, index: int, script_type: str = "p2wpkh") -> str:
    if type(branch) is not int or type(index) is not int or branch not in (0, 1) or not 0 <= index < 2**31:
        raise ReconciliationError("invalid BIP32 child")
    key = HDKey.from_base58(xpub).child(branch).child(index)
    pub = key.sec()
    if script_type == "p2wpkh":
        return _bech32_encode("bc", 0, _hash160(pub))
    if script_type == "p2tr":
        return _bech32_encode("bc", 1, key.xonly())
    raise ReconciliationError("supported script types: p2wpkh, p2tr")


@dataclass(frozen=True)
class UTXO:
    txid: str
    vout: int
    value_sats: int
    address: str
    confirmed: bool
    block_height: int | None = None

    @property
    def outpoint(self) -> str:
        return f"{self.txid}:{self.vout}"


def reconcile_utxos(*, derived_addresses: Iterable[str], observed: Iterable[UTXO]) -> dict:
    allowed = frozenset(derived_addresses)
    rows = list(observed)
    invalid = [u.outpoint for u in rows if u.address not in allowed]
    duplicate = len({u.outpoint for u in rows}) != len(rows)
    if invalid or duplicate:
        return {"status": "BLOCKED", "invalid_addresses": invalid, "duplicate_outpoints": duplicate,
                "utxo_count": len(rows), "total_sats": 0}
    total = sum(u.value_sats for u in rows if u.confirmed)
    return {"status": "PASS", "invalid_addresses": [], "duplicate_outpoints": False,
            "utxo_count": len(rows), "confirmed_utxo_count": sum(u.confirmed for u in rows),
            "total_sats": total, "addresses": len({u.address for u in rows})}
