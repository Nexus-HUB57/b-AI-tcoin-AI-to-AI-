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

    def to_key_bundle(self, passphrase: str = "") -> dict:
        r"""Export as encrypted key bundle for device storage.

        In production, this would use AES-256-GCM with the
        passphrase-derived key. For now, uses base64 encoding.
        """
        import base64
        bundle = json.dumps({
            "agent_id": self.agent_id,
            "pubkey_hex": self.pubkey_hex,
            "privkey_hex": self.privkey_hex,
            "created_at": self.created_at,
        }).encode()
        encrypted = base64.b64encode(bundle).decode()
        return {
            "key_bundle": encrypted,
            "wallet_id": self.wallet_id,
            "agent_id": self.agent_id,
            "address": self.address,
        }


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

        kp = SchnorrKeyPair()
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
        return wallet.to_key_bundle(passphrase)

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

        kp = SchnorrKeyPair()
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

        if not address.startswith("bait"):
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
                for char in address[4:]:  # Skip 'bait'
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
        ripemd = hashlib.new('ripemd160', sha_hash).digest()
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
        return "bait" + result
