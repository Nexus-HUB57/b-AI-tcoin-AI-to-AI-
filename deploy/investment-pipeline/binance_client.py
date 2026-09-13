"""
BAIT Investment Pipeline — Binance API Client
==============================================
Synchronous Binance API client for BTC→ETH swap automation.

Features:
- HMAC-SHA256 signed requests
- Exponential backoff with jitter
- Circuit breaker pattern
- Rate limit handling (429 responses)
- Testnet support

Security: API keys loaded from environment variables ONLY.
"""

import hashlib
import hmac
import json
import math
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests

from config import BinanceConfig, OrderStatus, RetryConfig


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures"""
    
    def __init__(self, threshold: int = 5, reset_seconds: int = 300):
        self.threshold = threshold
        self.reset_seconds = reset_seconds
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "closed"  # closed, open, half-open
    
    @property
    def is_open(self) -> bool:
        if self._state == "open":
            if self._last_failure_time and \
               time.time() - self._last_failure_time > self.reset_seconds:
                self._state = "half-open"
                return False
            return True
        return False
    
    def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.threshold:
            self._state = "open"
    
    def record_success(self):
        self._failure_count = 0
        self._state = "closed"


class BinanceClient:
    """
    Binance API client with retry, circuit breaker, and rate limiting.
    
    Usage:
        client = BinanceClient(config.binance, config.retry)
        price = client.get_symbol_price("ETHBTC")
        order = client.create_limit_order("ETHBTC", "BUY", quantity, price)
    """
    
    def __init__(self, config: BinanceConfig, retry: RetryConfig):
        self.config = config
        self.retry = retry
        self.circuit_breaker = CircuitBreaker(
            threshold=retry.circuit_breaker_threshold,
            reset_seconds=retry.circuit_breaker_reset_seconds
        )
        self._session = requests.Session()
        self._session.headers.update({
            "X-MBX-APIKEY": self.config.api_key,
            "Content-Type": "application/json"
        })
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms between requests (10 req/s)
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate HMAC-SHA256 signature for authenticated request"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.config.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _calculate_backoff(self, attempt: int) -> float:
        """Exponential backoff with jitter"""
        delay = min(
            self.retry.base_delay_seconds * (self.retry.exponential_base ** attempt),
            self.retry.max_delay_seconds
        )
        if self.retry.jitter:
            delay *= (0.5 + random.random() * 0.5)
        return delay
    
    def _rate_limit_wait(self):
        """Ensure minimum interval between requests"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        signed: bool = False,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Make an API request with retry logic and circuit breaker.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., /api/v3/order)
            params: Request parameters
            signed: Whether to sign the request
            timeout: Request timeout in seconds
            
        Returns:
            Response JSON as dict
            
        Raises:
            Exception: On persistent failure after retries
        """
        if self.circuit_breaker.is_open:
            raise Exception("Circuit breaker is OPEN — too many recent failures. Wait before retrying.")
        
        params = params or {}
        url = f"{self.config.effective_base_url}{endpoint}"
        
        last_exception = None
        for attempt in range(self.retry.max_retries):
            try:
                self._rate_limit_wait()
                
                request_params = dict(params)
                if signed:
                    request_params["timestamp"] = int(time.time() * 1000)
                    request_params["recvWindow"] = self.config.recv_window
                    request_params["signature"] = self._generate_signature(request_params)
                
                response = self._session.request(
                    method=method,
                    url=url,
                    params=request_params if method == "GET" else None,
                    data=request_params if method != "GET" else None,
                    timeout=timeout
                )
                
                # Rate limit handling
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    time.sleep(retry_after)
                    continue
                
                if response.status_code == 418:
                    # IP banned
                    raise Exception(f"IP banned by Binance. Response: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                self.circuit_breaker.record_success()
                return result
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                backoff = self._calculate_backoff(attempt)
                time.sleep(backoff)
                
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                backoff = self._calculate_backoff(attempt)
                time.sleep(backoff)
                
            except requests.exceptions.HTTPError as e:
                if response.status_code >= 500:
                    # Server error — retry
                    last_exception = e
                    backoff = self._calculate_backoff(attempt)
                    time.sleep(backoff)
                else:
                    # Client error — don't retry
                    self.circuit_breaker.record_failure()
                    raise Exception(f"Binance API error {response.status_code}: {response.text}")
                    
            except Exception as e:
                last_exception = e
                backoff = self._calculate_backoff(attempt)
                time.sleep(backoff)
        
        self.circuit_breaker.record_failure()
        raise Exception(f"Binance API request failed after {self.retry.max_retries} retries: {last_exception}")
    
    # ─── Market Data ────────────────────────────────────────────────
    
    def get_server_time(self) -> int:
        """Get Binance server time (ms epoch)"""
        resp = self._request("GET", "/api/v3/time")
        return resp["serverTime"]
    
    def get_symbol_price(self, symbol: str = "ETHBTC") -> float:
        """Get current price for a symbol"""
        resp = self._request("GET", "/api/v3/ticker/price", {"symbol": symbol})
        return float(resp["price"])
    
    def get_symbol_info(self, symbol: str = "ETHBTC") -> Dict:
        """Get trading pair info (filters, precision, etc.)"""
        resp = self._request("GET", "/api/v3/exchangeInfo")
        for s in resp["symbols"]:
            if s["symbol"] == symbol:
                return s
        raise Exception(f"Symbol {symbol} not found")
    
    def get_order_book(self, symbol: str = "ETHBTC", limit: int = 5) -> Dict:
        """Get order book (bids/asks)"""
        return self._request("GET", "/api/v3/depth", {"symbol": symbol, "limit": limit})
    
    def get_24h_ticker(self, symbol: str = "ETHBTC") -> Dict:
        """Get 24-hour price change statistics"""
        return self._request("GET", "/api/v3/ticker/24hr", {"symbol": symbol})
    
    # ─── Account ────────────────────────────────────────────────────
    
    def get_account_info(self) -> Dict:
        """Get account information (balances, trading rules)"""
        return self._request("GET", "/api/v3/account", signed=True)
    
    def get_balance(self, asset: str) -> Optional[float]:
        """Get balance for a specific asset"""
        account = self.get_account_info()
        for balance in account["balances"]:
            if balance["asset"] == asset:
                return float(balance["free"])
        return 0.0
    
    def get_deposit_address(self, coin: str, network: Optional[str] = None) -> Dict:
        """Get deposit address for a coin"""
        params = {"coin": coin}
        if network:
            params["network"] = network
        return self._request("GET", "/sapi/v1/capital/deposit/address", params, signed=True)
    
    # ─── Orders ─────────────────────────────────────────────────────
    
    def create_market_order(
        self,
        symbol: str,
        side: str,  # BUY or SELL
        quantity: float
    ) -> Dict:
        """Create a market order (immediate execution)"""
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": self._format_quantity(symbol, quantity)
        }
        return self._request("POST", "/api/v3/order", params, signed=True)
    
    def create_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = "GTC"  # GTC, IOC, FOK
    ) -> Dict:
        """Create a limit order"""
        params = {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "timeInForce": time_in_force,
            "quantity": self._format_quantity(symbol, quantity),
            "price": self._format_price(symbol, price)
        }
        return self._request("POST", "/api/v3/order", params, signed=True)
    
    def create_oco_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_price: float,
        stop_limit_price: float
    ) -> Dict:
        """Create an OCO (One-Cancels-Other) order pair"""
        params = {
            "symbol": symbol,
            "side": side,
            "quantity": self._format_quantity(symbol, quantity),
            "type": "TAKE_PROFIT_LIMIT",
            "price": self._format_price(symbol, price),
            "stopPrice": self._format_price(symbol, stop_price),
            "stopLimitPrice": self._format_price(symbol, stop_limit_price),
            "stopLimitTimeInForce": "GTC",
            "listOrderType": "OCO"
        }
        return self._request("POST", "/api/v3/order/oco", params, signed=True)
    
    def get_order(self, symbol: str, order_id: int) -> Dict:
        """Get order status by ID"""
        return self._request("GET", "/api/v3/order", {
            "symbol": symbol,
            "orderId": order_id
        }, signed=True)
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """Cancel an active order"""
        return self._request("DELETE", "/api/v3/order", {
            "symbol": symbol,
            "orderId": order_id
        }, signed=True)
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get all open orders"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/api/v3/openOrders", params, signed=True)
    
    def wait_for_order_fill(
        self,
        symbol: str,
        order_id: int,
        timeout_seconds: int = 300,
        poll_interval: int = 5
    ) -> Dict:
        """
        Wait for an order to be filled.
        
        Returns the final order dict when filled, or raises on timeout.
        """
        start = time.time()
        while time.time() - start < timeout_seconds:
            order = self.get_order(symbol, order_id)
            status = order.get("status", "")
            if status == "FILLED":
                return order
            elif status in ("CANCELLED", "EXPIRED", "REJECTED"):
                raise Exception(f"Order {order_id} ended with status: {status}")
            time.sleep(poll_interval)
        raise Exception(f"Order {order_id} not filled within {timeout_seconds}s")
    
    # ─── Withdrawals ────────────────────────────────────────────────
    
    def withdraw(
        self,
        coin: str,
        amount: float,
        address: str,
        network: Optional[str] = None,
        address_tag: Optional[str] = None
    ) -> Dict:
        """
        Submit a withdrawal request.
        
        Args:
            coin: Asset (e.g., "ETH")
            amount: Amount to withdraw
            address: Destination address
            network: Network (e.g., "ETH" for ERC-20)
            address_tag: Memo/tag if required
        """
        params = {
            "coin": coin,
            "amount": str(amount),
            "address": address
        }
        if network:
            params["network"] = network
        if address_tag:
            params["addressTag"] = address_tag
        return self._request("POST", "/sapi/v1/capital/withdraw/apply", params, signed=True)
    
    def get_withdrawal_history(self, coin: Optional[str] = None) -> List[Dict]:
        """Get withdrawal history"""
        params = {}
        if coin:
            params["coin"] = coin
        return self._request("GET", "/sapi/v1/capital/withdraw/history", params, signed=True)
    
    def get_deposit_history(self, coin: Optional[str] = None) -> List[Dict]:
        """Get deposit history"""
        params = {}
        if coin:
            params["coin"] = coin
        return self._request("GET", "/sapi/v1/capital/deposit/hisRec", params, signed=True)
    
    # ─── Helpers ────────────────────────────────────────────────────
    
    def _format_quantity(self, symbol: str, quantity: float) -> str:
        """Format quantity to proper precision (simplified)"""
        return f"{quantity:.6f}".rstrip('0').rstrip('.')
    
    def _format_price(self, symbol: str, price: float) -> str:
        """Format price to proper precision (simplified)"""
        return f"{price:.8f}".rstrip('0').rstrip('.')
    
    def calculate_swap_amounts(
        self,
        btc_amount: float,
        slippage_pct: float = 2.0
    ) -> Dict[str, float]:
        """
        Calculate expected ETH from BTC swap.
        
        For the ETHBTC pair on Binance:
        - Price is in BTC per ETH (e.g., 0.05 means 1 ETH = 0.05 BTC)
        - To sell BTC for ETH: we BUY ETH using BTC
        
        Args:
            btc_amount: Amount of BTC to sell
            slippage_pct: Maximum acceptable slippage
            
        Returns:
            Dict with expected amounts
        """
        price = self.get_symbol_price("ETHBTC")
        # price = BTC per 1 ETH
        # ETH obtained = btc_amount / price
        eth_expected = btc_amount / price
        
        # Account for fees
        fee = eth_expected * self.config.taker_fee
        eth_after_fee = eth_expected - fee
        
        # Slippage
        eth_min = eth_after_fee * (1 - slippage_pct / 100)
        
        # Limit price (better than market)
        limit_price = price * (1 + slippage_pct / 100 / 2)  # Split slippage
        
        return {
            "ethbtc_price": price,
            "eth_expected_gross": eth_expected,
            "fee_eth": fee,
            "eth_after_fee": eth_after_fee,
            "eth_min_with_slippage": eth_min,
            "limit_price_btc_per_eth": limit_price,
            "btc_input": btc_amount,
            "slippage_pct": slippage_pct
        }
