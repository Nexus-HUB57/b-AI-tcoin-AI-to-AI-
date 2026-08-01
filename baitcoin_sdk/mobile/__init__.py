r"""b'AI'tcoin Mobile SDK — Cross-platform mobile SDK (iOS/Android).

Provides a unified API for mobile applications to interact with
the b'AI'tcoin network. The SDK is designed as a REST API contract
that native mobile clients (Swift/Kotlin) or cross-platform frameworks
(React Native, Flutter) can consume via HTTP.

Architecture:
    Mobile Device -> HTTPS -> b'AI'tcoin Mobile API Gateway
                                        |
                                    +---+---+
                                    |       |
                                Wallet  Blockchain
                                Ops     Queries

The mobile SDK provides:
    - BaitcoinMobileSDK: Main SDK client class
    - MobileWallet: Secure key management and signing
    - MobileStaking: Staking operations
    - MobileMarketplace: AI service discovery and purchase
    - MobileNotifications: Push notification preferences
    - MobileSecurity: Biometric auth, key encryption

Design Principles:
    1. REST-first: All operations via HTTPS, no direct P2P on mobile
    2. Minimal payload: Compressed responses, pagination
    3. Offline-first: Local transaction signing, queued broadcasts
    4. Secure: Biometric key encryption, secure enclave integration
    5. Battery-aware: No background mining, pull-based sync

Usage (conceptual — consumed via HTTP by native clients)::

    # Client sends POST /api/v1/mobile/wallet/create
    # Response contains encrypted_key_bundle

    # Client sends POST /api/v1/mobile/transfer
    #   {"from": "agent_1", "to": "agent_2", "amount_bait": 10.0,
    #    "signature": "..."}
"""

from baitcoin_sdk.mobile.client import BaitcoinMobileSDK
from baitcoin_sdk.mobile.wallet import MobileWallet
from baitcoin_sdk.mobile.staking import MobileStaking
from baitcoin_sdk.mobile.marketplace import MobileMarketplace
from baitcoin_sdk.mobile.notifications import MobileNotificationManager
from baitcoin_sdk.mobile.security import MobileSecurity

__all__ = [
    "BaitcoinMobileSDK",
    "MobileWallet",
    "MobileStaking",
    "MobileMarketplace",
    "MobileNotificationManager",
    "MobileSecurity",
]
