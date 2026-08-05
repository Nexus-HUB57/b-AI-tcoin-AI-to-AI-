r"""
b'AI'tcoin Address System — Unified address derivation.

Addresses are derived from Schnorr public keys using Hash160 (RIPEMD160(SHA256(pubkey))
with a 1-byte version prefix and 4-byte checksum, producing a Base58Check-encoded string.

Format: version (1B) || hash160 (20B) || checksum (4B)
  - Mainnet: version = 0x00 -> prefix 'b'
  - Testnet: version = 0x01 -> prefix 't'

Example: b'1a2b3c4d5e6f7890abcdef1234567890abcdef12

This unifies how agents, wallets, and the explorer reference entities on-chain.
Previously, balances were looked up by raw pubkey bytes, which is fragile and
non-standard. Now every entity has a human-readable address.
"""

import hashlib
import struct
from typing import Optional, Tuple


# Base58 alphabet (no 0, O, I, l to avoid ambiguity)
_B58_ALPHABET_STR = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
_B58_ALPHABET = _B58_ALPHABET_STR.encode('ascii')
_B58_MAP = {c: i for i, c in enumerate(_B58_ALPHABET_STR)}

# Network version bytes
_VERSION_MAINNET = 0x00
_VERSION_TESTNET = 0x01

# Address prefix chars for display
_PREFIX_MAINNET = 'b'
_PREFIX_TESTNET = 't'


def sha256d(data: bytes) -> bytes:
    r"""Double SHA-256."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def hash160(data: bytes) -> bytes:
    r"""RIPEMD160(SHA256(data)) — standard Bitcoin address hash."""
    sha = hashlib.sha256(data).digest()
    ripemd = hashlib.new('ripemd160', sha).digest()
    return ripemd

def base58_encode(payload: bytes) -> str:
    r"""Encode bytes to Base58 string."""
    n = int.from_bytes(payload, byteorder='big')
    if n == 0:
        return '1' * len(payload)  # All-zero payload
    result = []
    while n > 0:
        n, remainder = divmod(n, 58)
        result.append(_B58_ALPHABET_STR[remainder])
    # Preserve leading zeros as '1' characters
    for byte in payload:
        if byte == 0:
            result.append('1')
        else:
            break
    return ''.join(reversed(result))

def base58_decode(s: str) -> bytes:
    r"""Decode Base58 string to bytes."""
    n = 0
    for char in s:
        if char not in _B58_MAP:
            raise ValueError(f"Invalid Base58 character: {char}")
        n = n * 58 + _B58_MAP[char]
    # Count leading '1's (zeros)
    leading_zeros = 0
    for char in s:
        if char == '1':
            leading_zeros += 1
        else:
            break
    result = n.to_bytes(max((n.bit_length() + 7) // 8, 1), byteorder='big')
    return b'\x00' * leading_zeros + result


class BAITAddress:
    r"""Unified b'AI'tcoin address.

    Encodes a Schnorr x-only public key into a human-readable address
    using Hash160 + Base58Check encoding.

    Usage::
        addr = BAITAddress.from_pubkey(pubkey_bytes)
        print(addr)  # b'1a2b3c...
        print(addr.network)  # 'mainnet'

        addr2 = BAITAddress.parse("b'1a2b3c...")
        assert addr2.pubkey_hash == addr.pubkey_hash
    """

    def __init__(self, version: int, pubkey_hash: bytes):
        if version not in (_VERSION_MAINNET, _VERSION_TESTNET):
            raise ValueError(f"Unknown version: {version:#x}")
        if len(pubkey_hash) != 20:
            raise ValueError(f"pubkey_hash must be 20 bytes, got {len(pubkey_hash)}")
        self.version = version
        self.pubkey_hash = pubkey_hash

    @classmethod
    def from_pubkey(cls, pubkey_bytes: bytes, network: str = 'mainnet') -> 'BAITAddress':
        r"""Derive address from Schnorr x-only public key (32 bytes)."""
        if len(pubkey_bytes) != 32:
            raise ValueError(f"Schnorr pubkey must be 32 bytes, got {len(pubkey_bytes)}")
        version = _VERSION_MAINNET if network == 'mainnet' else _VERSION_TESTNET
        h = hash160(pubkey_bytes)
        return cls(version, h)

    @classmethod
    def from_agent_id(cls, agent_id: str, network: str = 'mainnet') -> 'BAITAddress':
        r"""Derive deterministic address from agent ID string."""
        pubkey_bytes = hashlib.sha256(agent_id.encode()).digest()[:32]
        return cls.from_pubkey(pubkey_bytes, network)

    @classmethod
    def parse(cls, address_str: str) -> 'BAITAddress':
        r"""Parse a b'AI'tcoin address string."""
        if not address_str.startswith("b'"):
            raise ValueError("Address must start with b'")
        raw = address_str[2:]
        try:
            decoded = base58_decode(raw)
        except Exception as e:
            raise ValueError(f"Invalid Base58: {e}") from e
        if len(decoded) != 25:
            raise ValueError(f"Decoded address must be 25 bytes, got {len(decoded)}")
        version = decoded[0]
        pubkey_hash = decoded[1:21]
        checksum = decoded[21:25]
        expected_checksum = sha256d(decoded[:21])[:4]
        if checksum != expected_checksum:
            raise ValueError("Address checksum mismatch")
        return cls(version, pubkey_hash)

    @property
    def network(self) -> str:
        return 'mainnet' if self.version == _VERSION_MAINNET else 'testnet'

    @property
    def prefix(self) -> str:
        return _PREFIX_MAINNET if self.version == _VERSION_MAINNET else _PREFIX_TESTNET

    @property
    def checksum(self) -> bytes:
        return sha256d(bytes([self.version]) + self.pubkey_hash)[:4]

    def to_bytes(self) -> bytes:
        r"""Full 25-byte serialized address (version + hash160 + checksum)."""
        return bytes([self.version]) + self.pubkey_hash + self.checksum
    def __str__(self) -> str:
        return f"{self.prefix}'{base58_encode(self.to_bytes())}"

    def __repr__(self) -> str:
        return f"BAITAddress({str(self)})"

    def __eq__(self, other) -> object:
        if not isinstance(other, BAITAddress):
            return NotImplemented
        return self.version == other.version and self.pubkey_hash == other.pubkey_hash

    def __hash__(self) -> int:
        return hash((self.version, self.pubkey_hash))


def pubkey_to_address(pubkey_bytes: bytes, network: str = 'mainnet') -> str:
    r"""Quick helper: pubkey bytes -> address string."""
    return str(BAITAddress.from_pubkey(pubkey_bytes, network))

def agent_to_address(agent_id: str, network: str = 'mainnet') -> str:
    r"""Quick helper: agent ID string -> address string."""
    return str(BAITAddress.from_agent_id(agent_id, network))

def validate_address(address_str: str) -> bool:
    r"""Check if a string is a valid b'AI'tcoin address."""
    try:
        BAITAddress.parse(address_str)
        return True
    except (ValueError, Exception):
        return False
