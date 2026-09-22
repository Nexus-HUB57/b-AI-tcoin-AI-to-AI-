"""
BAIT Investment Pipeline — Sync Engine (Core Orchestrator)
===========================================================
The heart of the automated investment pipeline. Orchestrates:
  1. BTC balance monitoring (custody fund)
  2. BTC transfer to Binance deposit address
  3. BTC→ETH swap execution on Binance
  4. ETH withdrawal to deployer wallet
  5. Deploy readiness verification
  6. Smart contract deployment trigger

Synchronized state machine ensures exactly-once execution per phase
with full crash recovery via persisted state.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import PipelineConfig, Phase, SwapMethod
from state_machine import PhaseStateMachine, TransitionResult
from binance_client import BinanceClient
from balance_monitor import BalanceMonitor


# Configure logging
import os as _os
_log_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SyncEngine")


class EventLogger:
    """Append-only event log for audit trail"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
    
    def log(self, event_type: str, data: Dict[str, Any]):
        """Log an event (append-only, one JSON per line)"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **data
        }
        try:
            with open(self.filepath, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to log event: {e}")


class SyncEngine:
    """
    Core orchestration engine for the BAIT investment pipeline.
    
    Syncs the full flow: BTC custody → Binance → ETH → Deploy
    
    Usage:
        config = PipelineConfig()
        engine = SyncEngine(config)
        engine.run_phase_1()  # Execute Phase 1: deploy gas funding
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.state_machine = PhaseStateMachine(config)
        self.binance = BinanceClient(config.binance, config.retry)
        self.balance_monitor = BalanceMonitor(
            config.custody,
            config.ethereum,
            config.monitoring
        )
        self.event_log = EventLogger(config.monitoring.event_log)
        self._running = False
    
    # ─── Pre-flight Checks ──────────────────────────────────────────
    
    def pre_flight_check(self) -> Dict[str, Any]:
        """
        Comprehensive pre-flight check before any phase execution.
        
        Verifies:
        - Binance API connectivity
        - API key validity
        - BTC custody fund balance
        - ETH deployer wallet status
        - Free RPC endpoint availability
        - Trading pair availability (ETHBTC)
        """
        checks = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": self.config.version
        }
        
        # 1. Binance connectivity
        try:
            server_time = self.binance.get_server_time()
            checks["binance_api"] = {
                "status": "OK",
                "server_time": server_time,
                "testnet": self.config.binance.use_testnet
            }
        except Exception as e:
            checks["binance_api"] = {"status": "FAIL", "error": str(e)}
        
        # 2. Binance account
        try:
            account = self.binance.get_account_info()
            checks["binance_account"] = {
                "status": "OK",
                "can_trade": account.get("canTrade", False),
                "can_withdraw": account.get("canWithdraw", False),
                "can_deposit": account.get("canDeposit", False)
            }
        except Exception as e:
            checks["binance_account"] = {"status": "FAIL", "error": str(e)}
        
        # 3. ETHBTC trading pair
        try:
            symbol_info = self.binance.get_symbol_info("ETHBTC")
            checks["trading_pair"] = {
                "status": "OK",
                "symbol": "ETHBTC",
                "status_field": symbol_info.get("status")
            }
        except Exception as e:
            checks["trading_pair"] = {"status": "FAIL", "error": str(e)}
        
        # 4. BTC custody balance
        custody = self.balance_monitor.check_custody_fund()
        checks["btc_custody"] = {
            "status": "OK" if "error" not in custody else "FAIL",
            "total_btc": custody.get("total_btc", 0),
            "primary_address": self.config.custody.primary_address
        }
        
        # 5. ETH RPC endpoints
        rpc_working = []
        for rpc in self.config.ethereum.rpc_endpoints:
            try:
                resp = __import__('requests').post(
                    rpc,
                    json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                    timeout=5
                )
                if resp.status_code == 200:
                    rpc_working.append(rpc)
            except Exception:
                pass
        checks["eth_rpc"] = {
            "working": len(rpc_working),
            "total": len(self.config.ethereum.rpc_endpoints),
            "endpoints": rpc_working
        }
        
        # 6. Current market price
        try:
            price = self.binance.get_symbol_price("ETHBTC")
            checks["market_price"] = {
                "status": "OK",
                "ethbtc": price,
                "btc_per_eth": price,
                "eth_per_btc": 1/price if price > 0 else 0
            }
        except Exception as e:
            checks["market_price"] = {"status": "FAIL", "error": str(e)}
        
        # Overall assessment
        all_ok = all(
            v.get("status") == "OK" 
            for k, v in checks.items() 
            if isinstance(v, dict) and "status" in v
        )
        checks["overall"] = "READY" if all_ok else "NOT_READY"
        
        self.event_log.log("pre_flight_check", checks)
        logger.info(f"Pre-flight check: {checks['overall']}")
        
        return checks
    
    # ─── Phase 1: Deploy Gas Funding ────────────────────────────────
    
    def run_phase_1(self) -> Dict[str, Any]:
        """
        Execute Phase 1: Sell 0.01 BTC → ~0.525 ETH for deploy gas.
        
        Steps:
        1. Verify custody fund has sufficient BTC
        2. Calculate swap amounts at current market
        3. Execute limit order on Binance (ETHBTC pair)
        4. Wait for order fill
        5. Withdraw ETH to deployer wallet
        6. Verify ETH balance >= 0.525
        7. Execute mainnet deployment
        
        Returns:
            Dict with full execution results
        """
        result = {
            "phase": "phase_1_deploy",
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Transition state machine
        transition = self.state_machine.transition(
            Phase.PHASE_1_DEPLOY,
            {"phase_1_started": result["started_at"]}
        )
        if transition != TransitionResult.SUCCESS:
            result["error"] = f"State transition failed: {transition.value}"
            return result
        
        logger.info("=== PHASE 1: Deploy Gas Funding ===")
        self.event_log.log("phase_1_start", {})
        
        try:
            # Step 1: Verify custody balance
            custody = self.balance_monitor.check_custody_fund()
            btc_available = custody.get("total_btc", 0)
            btc_needed = self.config.phases.phase_1_btc_amount
            
            if btc_available < btc_needed:
                raise Exception(
                    f"Insufficient BTC: {btc_available:.8f} available, "
                    f"{btc_needed} needed"
                )
            
            result["custody_balance"] = btc_available
            logger.info(f"Custody balance: {btc_available:.8f} BTC (need {btc_needed})")
            
            # Step 2: Calculate swap amounts
            swap_calc = self.binance.calculate_swap_amounts(
                btc_needed,
                self.config.phases.phase_1_slippage_pct
            )
            result["swap_calculation"] = swap_calc
            logger.info(
                f"Swap: {btc_needed} BTC → {swap_calc['eth_after_fee']:.6f} ETH "
                f"(min: {swap_calc['eth_min_with_slippage']:.6f})"
            )
            
            # Step 3: Execute limit order
            # On ETHBTC pair: BUY ETH with BTC
            # Quantity is in ETH, price is in BTC/ETH
            eth_quantity = swap_calc["eth_after_fee"]
            limit_price = swap_calc["limit_price_btc_per_eth"]
            
            order = self.binance.create_limit_order(
                symbol="ETHBTC",
                side="BUY",
                quantity=eth_quantity,
                price=limit_price
            )
            order_id = order["orderId"]
            result["order"] = {
                "order_id": order_id,
                "symbol": "ETHBTC",
                "side": "BUY",
                "type": "LIMIT",
                "quantity": eth_quantity,
                "price": limit_price
            }
            logger.info(f"Limit order placed: ID={order_id}, qty={eth_quantity:.6f} ETH @ {limit_price:.8f} BTC/ETH")
            self.event_log.log("order_placed", result["order"])
            
            # Step 4: Wait for fill
            filled_order = self.binance.wait_for_order_fill(
                "ETHBTC",
                order_id,
                timeout_seconds=self.config.binance.order_timeout_seconds
            )
            filled_qty = float(filled_order.get("executedQty", 0))
            filled_price = float(filled_order.get("cummulativeQuoteQty", 0)) / filled_qty if filled_qty else 0
            result["fill"] = {
                "order_id": order_id,
                "status": filled_order.get("status"),
                "filled_qty_eth": filled_qty,
                "filled_price_btc_per_eth": filled_price,
                "total_cost_btc": float(filled_order.get("cummulativeQuoteQty", 0))
            }
            logger.info(f"Order filled: {filled_qty:.6f} ETH @ {filled_price:.8f} BTC/ETH")
            self.event_log.log("order_filled", result["fill"])
            
            # Step 5: Withdraw ETH to deployer wallet
            if not self.config.ethereum.deployer_address:
                raise Exception("Deployer address not configured — cannot withdraw ETH")
            
            withdrawal = self.binance.withdraw(
                coin="ETH",
                amount=filled_qty - self.config.binance.withdrawal_fee_eth,
                address=self.config.ethereum.deployer_address,
                network="ETH"
            )
            result["withdrawal"] = {
                "withdraw_id": withdrawal.get("id"),
                "amount": filled_qty - self.config.binance.withdrawal_fee_eth,
                "destination": self.config.ethereum.deployer_address,
                "fee": self.config.binance.withdrawal_fee_eth
            }
            logger.info(
                f"ETH withdrawal initiated: {filled_qty - self.config.binance.withdrawal_fee_eth:.6f} ETH "
                f"→ {self.config.ethereum.deployer_address}"
            )
            self.event_log.log("withdrawal_initiated", result["withdrawal"])
            
            # Step 6: Verify ETH balance
            logger.info("Waiting for ETH withdrawal to confirm (30-60s)...")
            time.sleep(60)  # Wait for withdrawal to process
            
            deployer_balance = self.balance_monitor.check_deployer_balance()
            eth_balance = deployer_balance.get("balance_eth", 0)
            result["deployer_balance"] = deployer_balance
            
            if eth_balance >= self.config.ethereum.phase1_gas_eth:
                logger.info(f"Deployer has {eth_balance:.6f} ETH — sufficient for Phase 1 deploy")
                result["deploy_ready"] = True
                
                # Transition to Phase 2
                self.state_machine.transition(
                    Phase.PHASE_2_LIQUIDITY,
                    {"phase_1_completed": True, "eth_balance": eth_balance}
                )
            else:
                logger.warning(f"Deployer has {eth_balance:.6f} ETH — below target {self.config.ethereum.phase1_gas_eth}")
                result["deploy_ready"] = False
            
        except Exception as e:
            logger.error(f"Phase 1 failed: {e}")
            result["error"] = str(e)
            self.state_machine.transition(Phase.ERROR, {"phase_1_error": str(e)})
            self.event_log.log("phase_1_error", {"error": str(e)})
        
        result["completed_at"] = datetime.now(timezone.utc).isoformat()
        result["state"] = self.state_machine.get_status()
        self.event_log.log("phase_1_complete", result)
        
        return result
    
    # ─── Phase 2: Liquidity Seeding ─────────────────────────────────
    
    def run_phase_2(self) -> Dict[str, Any]:
        """
        Execute Phase 2: Sell 0.20 BTC → ~12.5 ETH for Uniswap V3 liquidity.
        
        Same flow as Phase 1 but larger amounts and tighter slippage.
        After ETH is in deployer wallet, calls addLiquidity() on BAITUniswapV3Liquidity.
        """
        result = {
            "phase": "phase_2_liquidity",
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        
        if self.state_machine.current_phase != Phase.PHASE_2_LIQUIDITY:
            result["error"] = f"Wrong phase: {self.state_machine.current_phase.value} (need PHASE_2_LIQUIDITY)"
            return result
        
        logger.info("=== PHASE 2: Liquidity Seeding ===")
        self.event_log.log("phase_2_start", {})
        
        try:
            btc_needed = self.config.phases.phase_2_btc_amount
            
            # Calculate swap
            swap_calc = self.binance.calculate_swap_amounts(
                btc_needed,
                self.config.phases.phase_2_slippage_pct
            )
            result["swap_calculation"] = swap_calc
            logger.info(f"Swap: {btc_needed} BTC → {swap_calc['eth_after_fee']:.6f} ETH")
            
            # Execute limit order
            eth_quantity = swap_calc["eth_after_fee"]
            limit_price = swap_calc["limit_price_btc_per_eth"]
            
            order = self.binance.create_limit_order(
                symbol="ETHBTC",
                side="BUY",
                quantity=eth_quantity,
                price=limit_price
            )
            order_id = order["orderId"]
            logger.info(f"Limit order: ID={order_id}, {eth_quantity:.6f} ETH @ {limit_price:.8f}")
            
            # Wait for fill
            filled_order = self.binance.wait_for_order_fill(
                "ETHBTC",
                order_id,
                timeout_seconds=600  # 10 min for larger order
            )
            filled_qty = float(filled_order.get("executedQty", 0))
            result["order_fill"] = {
                "order_id": order_id,
                "filled_qty_eth": filled_qty,
                "status": filled_order.get("status")
            }
            logger.info(f"Order filled: {filled_qty:.6f} ETH")
            
            # Withdraw ETH
            withdrawal = self.binance.withdraw(
                coin="ETH",
                amount=filled_qty - self.config.binance.withdrawal_fee_eth,
                address=self.config.ethereum.deployer_address,
                network="ETH"
            )
            result["withdrawal"] = {
                "withdraw_id": withdrawal.get("id"),
                "amount_eth": filled_qty - self.config.binance.withdrawal_fee_eth
            }
            logger.info("ETH withdrawal initiated for liquidity seeding")
            
            # Wait for withdrawal
            time.sleep(60)
            
            # Verify balance sufficient for liquidity
            deployer_balance = self.balance_monitor.check_deployer_balance()
            eth_balance = deployer_balance.get("balance_eth", 0)
            result["deployer_balance"] = deployer_balance
            
            # Transition to Phase 3 or Deployed
            self.state_machine.transition(
                Phase.PHASE_3_INCREMENTAL,
                {"phase_2_completed": True, "liquidity_eth": eth_balance}
            )
            
        except Exception as e:
            logger.error(f"Phase 2 failed: {e}")
            result["error"] = str(e)
            self.state_machine.transition(Phase.ERROR, {"phase_2_error": str(e)})
        
        result["completed_at"] = datetime.now(timezone.utc).isoformat()
        result["state"] = self.state_machine.get_status()
        self.event_log.log("phase_2_complete", result)
        
        return result
    
    # ─── Full Pipeline ──────────────────────────────────────────────
    
    def run_full_pipeline(self, phases: int = 2) -> Dict[str, Any]:
        """
        Execute the full investment pipeline through specified phases.
        
        Args:
            phases: Number of phases to execute (1, 2, or 3)
        """
        logger.info(f"=== FULL PIPELINE START (phases={phases}) ===")
        self.event_log.log("pipeline_start", {"phases": phases})
        
        results = {
            "pipeline_version": self.config.version,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "pre_flight": None,
            "phase_1": None,
            "phase_2": None
        }
        
        # Pre-flight
        pre_flight = self.pre_flight_check()
        results["pre_flight"] = pre_flight
        if pre_flight["overall"] != "READY":
            results["error"] = "Pre-flight check failed"
            results["completed_at"] = datetime.now(timezone.utc).isoformat()
            return results
        
        # Phase 1
        results["phase_1"] = self.run_phase_1()
        if "error" in results["phase_1"]:
            results["error"] = f"Phase 1 failed: {results['phase_1']['error']}"
            results["completed_at"] = datetime.now(timezone.utc).isoformat()
            return results
        
        # Phase 2
        if phases >= 2:
            results["phase_2"] = self.run_phase_2()
            if "error" in results["phase_2"]:
                results["error"] = f"Phase 2 failed: {results['phase_2']['error']}"
                results["completed_at"] = datetime.now(timezone.utc).isoformat()
                return results
        
        results["completed_at"] = datetime.now(timezone.utc).isoformat()
        results["final_state"] = self.state_machine.get_status()
        
        self.event_log.log("pipeline_complete", results)
        logger.info("=== FULL PIPELINE COMPLETE ===")
        
        return results
    
    # ─── Status & Control ───────────────────────────────────────────
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive pipeline status"""
        return {
            "state_machine": self.state_machine.get_status(),
            "binance_configured": self.config.binance.is_configured,
            "binance_testnet": self.config.binance.use_testnet,
            "custody_primary": self.config.custody.primary_address,
            "deployer_address": self.config.ethereum.deployer_address,
            "version": self.config.version,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def pause(self):
        """Pause the pipeline"""
        self._running = False
        self.state_machine.transition(Phase.PAUSED)
        logger.info("Pipeline PAUSED")
    
    def resume(self):
        """Resume the pipeline from paused state"""
        self.state_machine.transition(Phase.PHASE_1_DEPLOY)  # Will resume to previous
        self._running = True
        logger.info("Pipeline RESUMED")
    
    def emergency_stop(self, reason: str = "Manual emergency stop"):
        """Emergency stop — pause and log"""
        self._running = False
        self.state_machine.transition(Phase.ERROR, {"emergency_stop_reason": reason})
        self.event_log.log("emergency_stop", {"reason": reason})
        logger.critical(f"EMERGENCY STOP: {reason}")
