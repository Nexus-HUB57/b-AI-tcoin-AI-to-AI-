r"""MobileWallet — Wallet operations for mobile SDK.

Provides wallet lifecycle management optimized for mobile:
    - Create new wallets with Schnorr key pairs
    - Import existing wallets from private key or mnemonic
    - Export wallet data (encrypted)
    - Sign transactions offline (no server round-trip)
    - Address derivation and validation

Security Model:
    The mobile SDK NEVER transmits private keys. All signing
    happens locally. The server only receives signatures and
    public keys. The key material can be further protected by
    the device's secure enclave (iOS) or Keystore (Android).

Key Storage:
    Keys are held in memory only during the SDK session.
    The calling application is responsible for persisting
    encrypted key bundles to device storage.

Usage::

    sdk = BaitcoinMobileSDK()
    result = sdk.wallet.create("agent_alice")
    # Store result["key_bundle"] in device secure storage
    # result contains: address, pubkey_hex, key_bundle
"""

import hashlib
import json
import os
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class WalletInfo:
    r"""Mobile wallet information."""
    agent_id: str
    address: str
    pubkey_hex: str
    privkey_hex: str
    created_at: float = field(default_factory=time.time)
    wallet_id: str = ""

    def to_dict(self, include_private: bool = False) -> dict:
        r"""Serialize wallet info. Private key excluded by default."""
        d = {
            "wallet_id": self.wallet_id,
            "agent_id": self.agent_id,
            "address": self.address,
            "pubkey_hex": self.pubkey_hex,
            "created_at": self.created_at,
        }
        if include_private:
            d["privkey_hex"] = self.privkey_hex
        return d

    def to_key_bundle(self, passphrase: str = "", security=None) -> dict:
        r"""Export as encrypted key bundle for device storage.

        New bundles are encrypted with the SDK AES-256-GCM provider.
        """
        if security is None:
            raise ValueError("security provider required for encrypted key bundle")
        key_data = {
            "agent_id": self.agent_id,
            "pubkey_hex": self.pubkey_hex,
            "privkey_hex": self.privkey_hex,
            "created_at": self.created_at,
        }
        encrypted = security.encrypt_key_bundle(key_data, passphrase)
        return {
            "key_bundle": encrypted,
            "wallet_id": self.wallet_id,
            "agent_id": self.agent_id,
            "address": self.address,
        }


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


class MobileWallet:
    r"""Mobile wallet operations.

    Wraps wallet creation, import, export, and signing for
    mobile-optimized workflows.
    """

    def __init__(self, sdk: 'BaitcoinMobileSDK'):
        r"""Initialize with parent SDK reference."""
        self._sdk = sdk
        self._wallets: Dict[str, WalletInfo] = {}

    def create(self, agent_id: str) -> dict:
        r"""Create a new wallet with Schnorr key pair.

        Generates a new secp256k1 key pair, derives the b'AI'tcoin
        address, and returns the wallet info.

        Parameters
        ----------
        agent_id : str
            Unique agent identifier

        Returns
        -------
        dict
            Wallet creation result with address, pubkey, and key bundle.
        """
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair

        kp = SchnorrKeyPair()
        pubkey_hex = kp.public_key_hex
        privkey_hex = kp.private_key_hex

        # Derive b'AI'tcoin address
        address = self._derive_address(pubkey_hex)
        wallet_id = uuid.uuid4().hex[:12]

        wallet = WalletInfo(
            agent_id=agent_id,
            address=address,
            pubkey_hex=pubkey_hex,
            privkey_hex=privkey_hex,
            wallet_id=wallet_id,
        )

        self._wallets[agent_id] = wallet
        return wallet.to_dict(include_private=True)

    def import_wallet(self, agent_id: str, privkey_hex: str) -> dict:
        r"""Import an existing wallet from private key.

        Parameters
        ----------
        agent_id : str
            Unique agent identifier
        privkey_hex : str
            Hex-encoded private key

        Returns
        -------
        dict
            Imported wallet info
        """
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair

        if not isinstance(privkey_hex, str) or len(privkey_hex) != 64:
            raise ValueError("private key must be a 32-byte hex string")
        try:
            private_key = int(privkey_hex, 16)
        except ValueError as exc:
            raise ValueError("private key must be hexadecimal") from exc
        kp = SchnorrKeyPair(private_key=private_key)
        pubkey_hex = kp.public_key_hex
        address = self._derive_address(pubkey_hex)
        wallet_id = uuid.uuid4().hex[:12]

        wallet = WalletInfo(
            agent_id=agent_id,
            address=address,
            pubkey_hex=pubkey_hex,
            privkey_hex=privkey_hex,
            wallet_id=wallet_id,
        )

        self._wallets[agent_id] = wallet
        return wallet.to_dict(include_private=True)

    def export_key_bundle(self, agent_id: str, passphrase: str = "") -> dict:
        r"""Export wallet as encrypted key bundle for device storage.

        Parameters
        ----------
        agent_id : str
            Agent ID to export
        passphrase : str
            Encryption passphrase (in production, used for AES-256-GCM)

        Returns
        -------
        dict
            Key bundle with encrypted private key material
        """
        wallet = self._wallets.get(agent_id)
        if not wallet:
            return {"error": "wallet_not_found"}
        security = getattr(self._sdk, "security", None)
        return wallet.to_key_bundle(passphrase, security=security)

    def get_address(self, agent_id: str) -> str:
        r"""Get the b'AI'tcoin address for an agent."""
        wallet = self._wallets.get(agent_id)
        if not wallet:
            return ""
        return wallet.address

    def get_pubkey(self, agent_id: str) -> str:
        r"""Get the public key for an agent."""
        wallet = self._wallets.get(agent_id)
        if not wallet:
            return ""
        return wallet.pubkey_hex

    def sign_message(self, agent_id: str, message: str) -> dict:
        r"""Sign a message using the agent's private key.

        Parameters
        ----------
        agent_id : str
            Signing agent
        message : str
            Message to sign

        Returns
        -------
        dict
            Signature data including r, s values and public key
        """
        from baitcoin_core.cryptography.schnorr import SchnorrKeyPair

        wallet = self._wallets.get(agent_id)
        if not wallet:
            return {"error": "wallet_not_found"}

        kp = SchnorrKeyPair(private_key=int(wallet.privkey_hex, 16))
        msg_hash = hashlib.sha256(message.encode()).digest()
        sig = kp.sign(msg_hash)

        return {
            "signature_hex": sig.hex,
            "pubkey_hex": wallet.pubkey_hex,
            "message_hash": msg_hash.hex(),
            "agent_id": agent_id,
        }

    def sign_transaction(self, agent_id: str, tx_data: dict) -> dict:
        r"""Sign a transaction offline.

        Constructs the transaction hash from the provided fields,
        signs it with the agent's private key, and returns the
        signed transaction ready for broadcast.

        Parameters
        ----------
        agent_id : str
            Signing agent
        tx_data : dict
            Transaction fields: inputs, outputs, nonce, etc.

        Returns
        -------
        dict
            Signed transaction with signature field populated
        """
        wallet = self._wallets.get(agent_id)
        if not wallet:
            return {"error": "wallet_not_found"}

        # Build deterministic tx hash
        tx_for_signing = {
            "inputs": tx_data.get("inputs", []),
            "outputs": tx_data.get("outputs", []),
            "nonce": tx_data.get("nonce", int(time.time())),
            "agent_id": agent_id,
        }
        tx_str = json.dumps(tx_for_signing, sort_keys=True)
        tx_hash = hashlib.sha256(tx_str.encode()).digest()

        # Sign
        sign_result = self.sign_message(agent_id, tx_str)
        if "error" in sign_result:
            return sign_result

        signed_tx = dict(tx_data)
        signed_tx["signature"] = sign_result["signature_hex"]
        signed_tx["signer_pubkey"] = sign_result["pubkey_hex"]
        signed_tx["tx_id"] = hashlib.sha256(
            (tx_str + sign_result["signature_hex"]).encode()
        ).hexdigest()

        return {"success": True, "signed_tx": signed_tx}

    def list_wallets(self) -> List[dict]:
        r"""List all loaded wallets (public info only)."""
        return [w.to_dict(include_private=False) for w in self._wallets.values()]

    def validate_address(self, address: str) -> dict:
        r"""Validate a b'AI'tcoin address format.

        Checks:
        1. Starts with 'bait' prefix
        2. Valid Base58Check encoding
        3. Correct checksum
        """
        is_valid = True
        reason = ""

        if not address.startswith("b'"):
            is_valid = False
            reason = "missing_bait_prefix"
        elif len(address) < 10:
            is_valid = False
            reason = "too_short"
        else:
            try:
                # Base58 decode validation
                alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
                n = 0
                for char in address[2:]:  # Skip "b'"
                    n = n * 58 + alphabet.index(char)
                # Convert to bytes for checksum
                data = n.to_bytes(25, byteorder='big')
                payload = data[:-4]
                checksum = data[-4:]
                computed = hashlib.sha256(
                    hashlib.sha256(payload).digest()
                ).digest()[:4]
                if checksum != computed:
                    is_valid = False
                    reason = "invalid_checksum"
            except (ValueError, OverflowError):
                is_valid = False
                reason = "invalid_base58"

        return {
            "address": address,
            "is_valid": is_valid,
            "reason": reason if not is_valid else "ok",
        }

    @staticmethod
    def _derive_address(pubkey_hex: str) -> str:
        r"""Derive b'AI'tcoin address from public key.

        Format: 'bait' + Base58Check(0x00 + RIPEMD160(SHA256(pubkey_bytes)))
        """
        pubkey_bytes = bytes.fromhex(pubkey_hex)
        sha_hash = hashlib.sha256(pubkey_bytes).digest()
        try:
            ripemd = hashlib.new('ripemd160', sha_hash).digest()
        except (ValueError, Exception):
            ripemd = _ripemd160_py(sha_hash)
        payload = b'\x00' + ripemd
        checksum = hashlib.sha256(
            hashlib.sha256(payload).digest()
        ).digest()[:4]
        address_bytes = payload + checksum

        # Base58 encode
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        n = int.from_bytes(address_bytes, 'big')
        result = ""
        while n > 0:
            n, r = divmod(n, 58)
            result = alphabet[r] + result
        # Leading zeros
        for byte in address_bytes:
            if byte == 0:
                result = '1' + result
            else:
                break
        return "b'" + result
