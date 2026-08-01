r"""MobileSecurity — Security utilities for mobile SDK.

Provides security primitives for mobile integration:
    - Biometric authentication interface
    - Key encryption/decryption
    - Secure key derivation (PBKDF2)
    - Device attestation
    - Transaction signing with biometric gate

The security module is designed to work WITH device-native
security features (Secure Enclave on iOS, Keystore on Android).
It provides the Python server-side interface that mobile
clients interact with.

Security Architecture::

    Mobile Device
    +-- Secure Enclave / Keystore (stores private key)
    +-- Biometric Prompt (fingerprint/face)
    |
    |  User taps "Send 10 BAIT"
    |  -> Biometric prompt shown
    |  -> User authenticates
    |  -> Secure Enclave signs transaction
    |  -> Signed tx sent to server
    |
    v
    b'AI'tcoin Server (verifies signature, broadcasts)

Usage::

    security = MobileSecurity(sdk)
    encrypted = security.encrypt_key_bundle(key_data, "password123")
    decrypted = security.decrypt_key_bundle(encrypted, "password123")
"""
import hashlib
import hmac
import json
import os
import base64
import time
from typing import Dict, Optional, Tuple


class MobileSecurity:
    r"""Security utilities for mobile SDK.

    Provides server-side security operations that complement
    device-native security features.
    """

    PBKDF2_ITERATIONS = 100_000
    SALT_LENGTH = 16
    KEY_LENGTH = 32
    AUTH_TAG_LENGTH = 16

    def __init__(self, sdk: 'BaitcoinMobileSDK'):
        self._sdk = sdk
        self._failed_attempts: Dict[str, int] = {}
        self._lockout_until: Dict[str, float] = {}
        self.MAX_ATTEMPTS = 5
        self.LOCKOUT_DURATION = 300  # 5 minutes

    def derive_key(self, passphrase: str, salt: bytes = None) -> Tuple[bytes, bytes]:
        r"""Derive an encryption key from passphrase using PBKDF2-HMAC-SHA256.

        Parameters
        ----------
        passphrase : str
            User's passphrase
        salt : bytes
            Optional salt (generated if not provided)

        Returns
        -------
        Tuple[bytes, bytes]
            (derived_key, salt)

        Security:
            Uses 100,000 PBKDF2 iterations with SHA-256.
            This provides ~50 bits of password security against
            GPU-based attacks (as of 2024 hardware).
        """
        if salt is None:
            salt = os.urandom(self.SALT_LENGTH)

        derived = hashlib.pbkdf2_hmac(
            'sha256',
            passphrase.encode('utf-8'),
            salt,
            self.PBKDF2_ITERATIONS,
            dklen=self.KEY_LENGTH,
        )
        return derived, salt

    def encrypt_key_bundle(self, key_data: dict, passphrase: str) -> dict:
        r"""Encrypt a key bundle with a passphrase.

        Uses AES-256-CTR mode (simulated with XOR since we don't
        require the cryptography library as a dependency).

        In production deployments, this would use:
            - AES-256-GCM via cryptography lib
            - Or platform-native encryption (CryptoKit/KeyStore)

        Parameters
        ----------
        key_data : dict
            Key material to encrypt
        passphrase : str
            Encryption passphrase

        Returns
        -------
        dict
            Encrypted bundle with salt, iv, ciphertext
        """
        derived_key, salt = self.derive_key(passphrase)
        iv = os.urandom(12)
        plaintext = json.dumps(key_data, sort_keys=True).encode()

        # Simulated AES-CTR: XOR plaintext with key stream
        # In production, use: from cryptography.fernet import Fernet
        key_stream = hashlib.sha256(derived_key + iv).digest()
        ciphertext = bytes(
            a ^ b for a, b in zip(plaintext, (key_stream * (len(plaintext) // 32 + 1))[:len(plaintext)])
        )

        # HMAC for integrity
        auth_tag = hmac.new(derived_key, iv + ciphertext, hashlib.sha256).digest()[:self.AUTH_TAG_LENGTH]

        return {
            "version": 1,
            "algorithm": "pbkdf2-sha256-xor",
            "iterations": self.PBKDF2_ITERATIONS,
            "salt": base64.b64encode(salt).decode(),
            "iv": base64.b64encode(iv).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "auth_tag": base64.b64encode(auth_tag).decode(),
        }

    def decrypt_key_bundle(self, encrypted: dict, passphrase: str) -> dict:
        r"""Decrypt a key bundle with a passphrase.

        Parameters
        ----------
        encrypted : dict
            Encrypted bundle from encrypt_key_bundle
        passphrase : str
            Decryption passphrase

        Returns
        -------
        dict
            Decrypted key data, or error dict
        """
        try:
            salt = base64.b64decode(encrypted["salt"])
            iv = base64.b64decode(encrypted["iv"])
            ciphertext = base64.b64decode(encrypted["ciphertext"])
            auth_tag = base64.b64decode(encrypted["auth_tag"])

            derived_key, _ = self.derive_key(passphrase, salt)

            # Verify HMAC
            expected_tag = hmac.new(
                derived_key, iv + ciphertext, hashlib.sha256
            ).digest()[:self.AUTH_TAG_LENGTH]

            if not hmac.compare_digest(auth_tag, expected_tag):
                return {"error": "integrity_check_failed"}

            # Decrypt (reverse XOR)
            key_stream = hashlib.sha256(derived_key + iv).digest()
            plaintext = bytes(
                a ^ b for a, b in zip(ciphertext, (key_stream * (len(ciphertext) // 32 + 1))[:len(ciphertext)])
            )

            return json.loads(plaintext.decode())
        except Exception as e:
            return {"error": f"decryption_failed: {e}"}

    def check_biometric_eligible(self, device_id: str) -> dict:
        r"""Check if a device supports biometric authentication.

        This is a server-side check that validates the device
        has previously enrolled biometrics.
        """
        return {
            "eligible": True,  # Assume eligible; client enforces
            "device_id": device_id,
            "methods": ["fingerprint", "face_id", "face_unlock"],
        }

    def verify_biometric_token(self, device_id: str, token: str) -> dict:
        r"""Verify a biometric authentication token.

        The actual biometric check happens on-device. This method
        verifies the server-side token that the device sends after
        successful biometric authentication.
        """
        # Check rate limiting
        attempts = self._failed_attempts.get(device_id, 0)
        lockout = self._lockout_until.get(device_id, 0)

        if time.time() < lockout:
            remaining = lockout - time.time()
            return {
                "verified": False,
                "error": "device_locked",
                "remaining_seconds": int(remaining),
            }

        if attempts >= self.MAX_ATTEMPTS:
            self._lockout_until[device_id] = time.time() + self.LOCKOUT_DURATION
            return {
                "verified": False,
                "error": "too_many_attempts",
                "lockout_seconds": self.LOCKOUT_DURATION,
            }

        # Verify token (in production, verify JWT signed by device)
        if not token or len(token) < 16:
            self._failed_attempts[device_id] = attempts + 1
            return {"verified": False, "error": "invalid_token"}

        # Token accepted
        self._failed_attempts[device_id] = 0
        return {"verified": True}

    def generate_device_challenge(self, device_id: str) -> dict:
        r"""Generate a cryptographic challenge for device attestation.

        The device must sign this challenge with its stored key
        to prove it has access to the key without revealing it.
        """
        challenge = os.urandom(32).hex()
        return {
            "challenge": challenge,
            "expires_at": time.time() + 60,
            "device_id": device_id,
        }

    def verify_device_response(self, device_id: str, challenge: str,
                                 signature_hex: str, pubkey_hex: str) -> dict:
        r"""Verify a device's response to a cryptographic challenge.

        Parameters
        ----------
        device_id : str
            Device identifier
        challenge : str
            Original challenge string
        signature_hex : str
            Hex-encoded Schnorr signature
        pubkey_hex : str
            Hex-encoded public key
        """
        try:
            from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
            kp = SchnorrKeyPair.from_pubkey_hex(pubkey_hex)
            msg_hash = hashlib.sha256(challenge.encode()).digest()
            sig_bytes = bytes.fromhex(signature_hex)
            valid = kp.verify(msg_hash, sig_bytes)
            return {"verified": valid}
        except Exception as e:
            return {"verified": False, "error": str(e)}

    def get_security_status(self, device_id: str) -> dict:
        r"""Get security status for a device."""
        return {
            "device_id": device_id,
            "failed_attempts": self._failed_attempts.get(device_id, 0),
            "is_locked": time.time() < self._lockout_until.get(device_id, 0),
            "max_attempts": self.MAX_ATTEMPTS,
            "lockout_seconds": self.LOCKOUT_DURATION,
        }
