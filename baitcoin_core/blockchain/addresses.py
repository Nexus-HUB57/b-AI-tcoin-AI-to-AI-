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


def _ripemd160_py(msg):
    import struct as _s
    rl=[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,7,4,13,1,10,6,15,3,12,0,9,5,2,14,11,8,3,10,14,4,9,15,8,1,2,7,0,6,13,11,5,12,1,9,11,10,0,8,12,4,13,3,7,15,14,5,6,2,4,0,5,9,7,12,2,10,14,1,3,8,11,6,15,13]
    rr=[5,14,7,0,9,2,11,4,13,6,15,8,1,10,3,12,6,11,3,7,0,13,5,10,14,15,8,12,4,9,1,2,15,5,1,3,7,14,6,9,11,8,12,2,10,0,4,13,8,6,4,1,3,11,15,0,5,12,2,13,9,7,10,14,12,15,10,4,1,5,8,7,6,2,13,14,0,3,9,11]
    sl=[11,14,15,12,5,8,7,9,11,13,14,15,6,7,9,8,7,6,8,13,11,9,7,15,7,12,15,9,11,7,13,12,11,13,6,7,14,9,13,15,14,8,13,6,5,12,7,5,11,12,14,15,14,15,9,8,9,14,5,6,8,6,5,12,9,15,5,11,6,8,13,12,5,12,13,14,11,8,5,6]
    sr=[8,9,9,11,13,15,15,5,7,7,8,11,14,14,12,6,9,13,15,7,12,8,9,11,7,7,12,7,6,15,13,11,9,7,15,11,8,6,6,14,12,13,5,14,13,13,7,5,15,5,8,11,14,14,6,14,6,9,12,9,12,5,15,8,8,5,12,9,12,5,14,6,8,13,6,5,15,13,11,11]
    kl=[0x00000000,0x5A827999,0x6ED9EBA1,0x8F1BBCDC,0xA953FD4E]
    kr=[0x50A28BE6,0x5C4DD124,0x6D703EF3,0x7A6D76E9,0x00000000]
    def rol(x,n): return ((x<<n)|(x>>(32-n)))&0xFFFFFFFF
    def f(j,x,y,z):
        if j<16: return x^y^z
        if j<32: return (x&y)|(~x&z)
        if j<48: return (x|~y)^z
        if j<64: return (x&z)|(y&~z)
        return x^(y|~z)
    ml=len(msg)*8
    msg+=b"\x80"
    while len(msg)%64!=56: msg+=b"\x00"
    msg+=_s.pack("<Q",ml)
    h0,h1,h2,h3,h4=0x67452301,0xEFCDAB89,0x98BADCFE,0x10325476,0xC3D2E1F0
    for off in range(0,len(msg),64):
        X=list(_s.unpack("<16I",msg[off:off+64]))
        al,bl,cl,dl,el=h0,h1,h2,h3,h4
        ar,br,cr,dr,er=h0,h1,h2,h3,h4
        for j in range(80):
            t=(rol((al+f(j,bl,cl,dl)+X[rl[j]]+kl[j//16])&0xFFFFFFFF,sl[j])+el)&0xFFFFFFFF
            al,el,dl,cl,bl=el,dl,rol(cl,10),bl,t
            t=(rol((ar+f(79-j,br,cr,dr)+X[rr[j]]+kr[j//16])&0xFFFFFFFF,sr[j])+er)&0xFFFFFFFF
            ar,er,dr,cr,br=er,dr,rol(cr,10),br,t
        t=(h1+cl+dr)&0xFFFFFFFF
        h1=(h2+dl+er)&0xFFFFFFFF
        h2=(h3+el+ar)&0xFFFFFFFF
        h3=(h4+al+br)&0xFFFFFFFF
        h4=(h0+bl+cr)&0xFFFFFFFF
        h0=t
    return _s.pack("<5I",h0,h1,h2,h3,h4)

def hash160(data: bytes) -> bytes:
    r"""RIPEMD160(SHA256(data)) — standard Bitcoin address hash."""
    sha = hashlib.sha256(data).digest()
    try:
        ripemd = hashlib.new('ripemd160', sha).digest()
    except (ValueError, Exception):
        ripemd = _ripemd160_py(sha)
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
