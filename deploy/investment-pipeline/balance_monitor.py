"""
BAIT Investment Pipeline — Balance Monitor
===========================================
Monitors BTC custody balances and ETH deployer wallet balance.
Uses Blockstream API for BTC and Ethereum RPC for ETH.

Provides real-time balance feeds for the sync engine.
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import requests

from config import CustodyConfig, EthereumConfig, MonitoringConfig


class BalanceMonitor:
    """
    Monitors balances across BTC custody and ETH deployer wallet.
    
    BTC: Uses Blockstream.info API (free, no key required)
    ETH: Uses Ethereum JSON-RPC (free community endpoints)
    """
    
    def __init__(
        self,
        custody: CustodyConfig,
        ethereum: EthereumConfig,
        monitoring: MonitoringConfig
    ):
        self.custody = custody
        self.ethereum = ethereum
        self.monitoring = monitoring
        self._last_btc_check: Dict[str, Any] = {}
        self._last_eth_check: Dict[str, Any] = {}
        self._btc_callbacks: List[Callable] = []
        self._eth_callbacks: List[Callable] = []
    
    # ─── BTC Balance ────────────────────────────────────────────────
    
    def get_btc_balance(self, address: str) -> Dict[str, Any]:
        """
        Get BTC balance for an address via Blockstream API.
        
        Returns dict with funded_txsum, spent_txsum, balance (satoshi + BTC).
        """
        url = self.custody.balance_api.format(address=address)
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            # Blockstream returns chain_stats with funded/sent sums in satoshis
            chain_stats = data.get("chain_stats", {})
            funded = int(chain_stats.get("funded_txo_sum", 0))
            spent = int(chain_stats.get("spent_txo_sum", 0))
            balance_sats = funded - spent
            balance_btc = balance_sats / 100_000_000
            
            result = {
                "address": address,
                "balance_sats": balance_sats,
                "balance_btc": balance_btc,
                "funded_txo_sum_sats": funded,
                "spent_txo_sum_sats": spent,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "source": "blockstream.info"
            }
            
            self._last_btc_check = result
            self._notify_btc_callbacks(result)
            return result
            
        except Exception as e:
            return {
                "address": address,
                "error": str(e),
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
    
    def check_custody_fund(self) -> Dict[str, Any]:
        """Check all custody addresses and return aggregate balance"""
        all_balances = []
        total_btc = 0.0
        total_sats = 0
        
        # Primary address
        primary = self.get_btc_balance(self.custody.primary_address)
        if "error" not in primary:
            total_btc += primary["balance_btc"]
            total_sats += primary["balance_sats"]
        all_balances.append(primary)
        
        # Secondary addresses
        for addr in self.custody.secondary_addresses:
            bal = self.get_btc_balance(addr)
            if "error" not in bal:
                total_btc += bal["balance_btc"]
                total_sats += bal["balance_sats"]
            all_balances.append(bal)
        
        return {
            "total_btc": total_btc,
            "total_sats": total_sats,
            "addresses": all_balances,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    
    # ─── ETH Balance ────────────────────────────────────────────────
    
    def get_eth_balance(self, address: str, rpc_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Get ETH balance for an address via JSON-RPC.
        
        Tries multiple RPC endpoints with failover.
        """
        rpc_urls = [rpc_url] if rpc_url else self.ethereum.rpc_endpoints
        
        for url in rpc_urls:
            try:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_getBalance",
                    "params": [address, "latest"],
                    "id": 1
                }
                resp = requests.post(url, json=payload, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                
                if "result" in data:
                    balance_wei = int(data["result"], 16)
                    balance_eth = balance_wei / 1e18
                    
                    result = {
                        "address": address,
                        "balance_wei": balance_wei,
                        "balance_eth": balance_eth,
                        "rpc_url": url,
                        "checked_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    self._last_eth_check = result
                    self._notify_eth_callbacks(result)
                    return result
                    
            except Exception:
                continue
        
        return {
            "address": address,
            "error": "All RPC endpoints failed",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    
    def check_deployer_balance(self) -> Dict[str, Any]:
        """Check ETH balance of the deployer wallet"""
        if not self.ethereum.deployer_address:
            return {
                "error": "Deployer address not configured",
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        return self.get_eth_balance(self.ethereum.deployer_address)
    
    # ─── Binance Balance ────────────────────────────────────────────
    
    def get_binance_balances(self, binance_client) -> Dict[str, Any]:
        """Get BTC and ETH balances on Binance"""
        try:
            btc = binance_client.get_balance("BTC")
            eth = binance_client.get_balance("ETH")
            return {
                "binance_btc": btc or 0.0,
                "binance_eth": eth or 0.0,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "error": str(e),
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
    
    # ─── Continuous Monitoring ──────────────────────────────────────
    
    def register_btc_callback(self, callback: Callable):
        """Register callback for BTC balance updates"""
        self._btc_callbacks.append(callback)
    
    def register_eth_callback(self, callback: Callable):
        """Register callback for ETH balance updates"""
        self._eth_callbacks.append(callback)
    
    def _notify_btc_callbacks(self, data: Dict):
        for cb in self._btc_callbacks:
            try:
                cb(data)
            except Exception:
                pass
    
    def _notify_eth_callbacks(self, data: Dict):
        for cb in self._eth_callbacks:
            try:
                cb(data)
            except Exception:
                pass
    
    def run_continuous(
        self,
        interval_btc: int = 60,
        interval_eth: int = 30,
        duration_seconds: Optional[int] = None
    ):
        """
        Run continuous balance monitoring.
        
        Args:
            interval_btc: Seconds between BTC checks
            interval_eth: Seconds between ETH checks
            duration_seconds: Total duration (None = forever)
        """
        start = time.time()
        last_btc = 0
        last_eth = 0
        
        while True:
            now = time.time()
            if duration_seconds and now - start > duration_seconds:
                break
            
            # BTC check
            if now - last_btc >= interval_btc:
                custody = self.check_custody_fund()
                last_btc = now
            
            # ETH check (only if deployer address is set)
            if self.ethereum.deployer_address and now - last_eth >= interval_eth:
                deployer = self.check_deployer_balance()
                last_eth = now
            
            time.sleep(1)
    
    def get_full_status(self, binance_client=None) -> Dict[str, Any]:
        """Get comprehensive balance status across all addresses"""
        custody = self.check_custody_fund()
        deployer = self.check_deployer_balance() if self.ethereum.deployer_address else {}
        binance = self.get_binance_balances(binance_client) if binance_client else {}
        
        return {
            "custody_fund": custody,
            "deployer_wallet": deployer,
            "binance": binance,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
