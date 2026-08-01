r"""BaitcoinMobileSDK — Main mobile SDK client.

Provides the primary entry point for mobile applications
to interact with the b'AI'tcoin ecosystem. Every operation
is available via the unified SDK interface.

The SDK communicates with a b'AI'tcoin API server over HTTPS.
It handles request signing, response parsing, error handling,
and offline transaction queuing.

Connection Modes:
    - **Remote**: Connects to a b'AI'tcoin API endpoint (production)
    - **Local**: Uses in-process Python objects (testing)

Supported Operations:
    - Wallet: create, import, export, balance, transfer
    - Staking: stake, unstake, claim rewards, view positions
    - Marketplace: search, purchase, list services
    - Blockchain: block queries, transaction lookup, network status
    - Agents: register, update capabilities, view reputation
    - Notifications: register push tokens, set preferences

Threading Model:
    All operations are synchronous from the caller's perspective.
    The underlying HTTP client handles connection pooling.
    Mobile frameworks should call SDK methods from background threads.

Usage (Python testing)::

    sdk = BaitcoinMobileSDK(endpoint="https://api.baitcoin.net")

    # Create wallet
    wallet = sdk.wallet.create("my_agent")
    print(wallet["address"])  # bait1q...

    # Check balance
    balance = sdk.get_balance("my_agent")
    print(balance)  # 100.5

    # Transfer
    tx = sdk.transfer("my_agent", "recipient", 10.0)
    print(tx["tx_hash"])
"""

import hashlib
import json
import time
import uuid
from typing import Dict, List, Optional, Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from baitcoin_sdk.mobile.wallet import MobileWallet
from baitcoin_sdk.mobile.staking import MobileStaking
from baitcoin_sdk.mobile.marketplace import MobileMarketplace
from baitcoin_sdk.mobile.notifications import MobileNotificationManager
from baitcoin_sdk.mobile.security import MobileSecurity


class BaitcoinMobileSDK:
    r"""b'AI'tcoin Mobile SDK — unified client for mobile applications.

    Parameters
    ----------
    endpoint : str
        API server URL (default: https://api.baitcoin.net)
    api_key : str
        Optional API key for authenticated endpoints
    device_id : str
        Unique device identifier for push notifications
    timeout : int
        HTTP request timeout in seconds (default: 15)
    """

    DEFAULT_ENDPOINT = "https://api.baitcoin.net"
    SDK_VERSION = "1.0.0-mobile"
    PLATFORM_IOS = "ios"
    PLATFORM_ANDROID = "android"
    PLATFORM_CROSSPLATFORM = "crossplatform"

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: str = "",
        device_id: str = "",
        timeout: int = 15,
    ):
        self.endpoint = endpoint or self.DEFAULT_ENDPOINT
        self.api_key = api_key
        self.device_id = device_id or uuid.uuid4().hex[:12]
        self.timeout = timeout
        self._session_id = uuid.uuid4().hex

        # Sub-SDKs
        self.wallet = MobileWallet(self)
        self.staking = MobileStaking(self)
        self.marketplace = MobileMarketplace(self)
        self.notifications = MobileNotificationManager(self)
        self.security = MobileSecurity(self)

        # Local mode (for testing)
        self._local_mode = False
        self._local_node = None

    def _request(
        self,
        method: str,
        path: str,
        body: dict = None,
        headers: dict = None,
    ) -> dict:
        r"""Execute an HTTP request against the API server.

        Automatically adds SDK identification headers and handles errors.
        """
        url = f"{self.endpoint}{path}"
        data = json.dumps(body).encode() if body else None
        req_headers = {
            "Content-Type": "application/json",
            "X-SDK-Version": self.SDK_VERSION,
            "X-Device-ID": self.device_id,
            "X-Session-ID": self._session_id,
        }
        if self.api_key:
            req_headers["Authorization"] = f"Bearer {self.api_key}"
        if headers:
            req_headers.update(headers)

        req = Request(url, data=data, headers=req_headers, method=method)
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            body = e.read().decode()
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return {"error": "http_error", "status": e.code}
        except URLError:
            return {"error": "connection_failed"}
        except Exception as e:
            return {"error": str(e)}

    # --- Core operations ---

    def get_balance(self, agent_id: str) -> float:
        r"""Get BAIT balance for an agent (mobile-optimized)."""
        if self._local_mode and self._local_node:
            return self._local_node.token.balance_bait(agent_id)
        resp = self._request("GET", f"/api/v1/balance/{agent_id}")
        return resp.get("balance_bait", 0.0)

    def transfer(
        self,
        from_agent: str,
        to_agent: str,
        amount_bait: float,
        memo: str = "",
    ) -> dict:
        r"""Transfer BAIT between agents."""
        if self._local_mode and self._local_node:
            success = self._local_node.token.transfer(
                from_agent, to_agent,
                int(amount_bait * 100_000_000), memo,
            )
            return {"success": success, "amount_bait": amount_bait}
        return self._request("POST", "/api/v1/transfer", {
            "from": from_agent,
            "to": to_agent,
            "amount_bait": amount_bait,
            "memo": memo,
        })

    def get_blockchain_info(self) -> dict:
        r"""Get blockchain summary."""
        return self._request("GET", "/api/v1/blockchain")

    def get_block(self, height: int = None, block_hash: str = None) -> dict:
        r"""Get a specific block by height or hash."""
        if block_hash:
            return self._request(
                "GET", f"/api/v1/explorer/blocks/hash/{block_hash}"
            )
        return self._request(
            "GET", f"/api/v1/explorer/blocks/height/{height}"
        )

    def get_transaction(self, tx_hash: str) -> dict:
        r"""Get transaction details by hash."""
        return self._request("GET", f"/api/v1/explorer/tx/{tx_hash}")

    def get_network_status(self) -> dict:
        r"""Get comprehensive network status for mobile dashboard."""
        return self._request("GET", "/api/v1/analytics/dashboard")

    def faucet_claim(self, agent_id: str, pubkey_hex: str) -> dict:
        r"""Claim BAIT from the testnet/mainnet faucet."""
        return self._request("POST", "/api/v1/faucet/claim", {
            "agent_id": agent_id,
            "pubkey_hex": pubkey_hex,
        })

    def get_price(self, symbol: str) -> Optional[float]:
        r"""Get price from oracle."""
        resp = self._request("GET", f"/api/v1/oracle/{symbol}")
        return resp.get("price")

    def search_on_chain(self, query: str) -> dict:
        r"""Universal on-chain search (blocks, txs, addresses)."""
        return self._request(
            "GET", f"/api/v1/explorer/search?q={query}"
        )

    def get_sdk_info(self) -> dict:
        r"""Get SDK version and device information."""
        return {
            "sdk_version": self.SDK_VERSION,
            "device_id": self.device_id,
            "session_id": self._session_id,
            "endpoint": self.endpoint,
            "local_mode": self._local_mode,
        }
