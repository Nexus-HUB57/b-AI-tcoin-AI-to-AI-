#!/usr/bin/env python3
"""
BAIT Investment Pipeline — CLI Runner
=====================================
Command-line interface to the automated investment pipeline.

Usage:
    # Pre-flight check (dry run)
    python pipeline_cli.py preflight
    
    # Check all balances
    python pipeline_cli.py balances
    
    # Run Phase 1 only (deploy gas, ~0.01 BTC)
    python pipeline_cli.py phase1
    
    # Run Phase 2 (liquidity, ~0.20 BTC)
    python pipeline_cli.py phase2
    
    # Run full pipeline (Phase 1 + 2)
    python pipeline_cli.py full
    
    # Check pipeline status
    python pipeline_cli.py status
    
    # Emergency stop
    python pipeline_cli.py stop "reason"
    
    # Simulate (testnet) full pipeline
    python pipeline_cli.py simulate

Environment Variables Required:
    BINANCE_API_KEY     — Binance API key
    BINANCE_API_SECRET  — Binance API secret
    BINANCE_USE_TESTNET — "true" or "false" (default: "true")
    DEPLOYER_KEYSTORE_PASSWORD — Password for deployer keystore
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Add pipeline directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PipelineConfig, Phase
from sync_engine import SyncEngine
from balance_monitor import BalanceMonitor


def setup_logging():
    """Setup logging for CLI output"""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def cmd_preflight(engine: SyncEngine, args):
    """Run pre-flight check"""
    print("\n" + "=" * 60)
    print("BAIT INVESTMENT PIPELINE — PRE-FLIGHT CHECK")
    print("=" * 60)
    
    result = engine.pre_flight_check()
    
    # Print results
    for key, value in result.items():
        if key == "overall":
            continue
        if isinstance(value, dict):
            status = value.get("status", "N/A")
            icon = "✓" if status == "OK" else "✗" if status == "FAIL" else "○"
            print(f"\n  {icon} {key}:")
            for k, v in value.items():
                if k != "status":
                    print(f"      {k}: {v}")
    
    print(f"\n{'=' * 60}")
    overall = result.get("overall", "UNKNOWN")
    icon = "✓" if overall == "READY" else "✗"
    print(f"  {icon} OVERALL: {overall}")
    print(f"{'=' * 60}\n")
    
    # Save results
    output_path = "deploy/investment-pipeline/preflight-results.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"Results saved to: {output_path}")
    
    return 0 if overall == "READY" else 1


def cmd_balances(engine: SyncEngine, args):
    """Check all balances"""
    print("\n" + "=" * 60)
    print("BAIT INVESTMENT PIPELINE — BALANCE CHECK")
    print("=" * 60)
    
    config = engine.config
    monitor = engine.balance_monitor
    
    # BTC custody
    print("\n  BTC CUSTODY FUND:")
    custody = monitor.check_custody_fund()
    for addr_data in custody.get("addresses", []):
        addr = addr_data.get("address", "unknown")[:20] + "..."
        bal = addr_data.get("balance_btc", 0)
        print(f"    {addr}: {bal:.8f} BTC")
    print(f"    TOTAL: {custody.get('total_btc', 0):.8f} BTC")
    
    # ETH deployer (if configured)
    if config.ethereum.deployer_address:
        print(f"\n  ETH DEPLOYER WALLET:")
        deployer = monitor.check_deployer_balance()
        addr = config.ethereum.deployer_address[:20] + "..."
        bal = deployer.get("balance_eth", 0)
        print(f"    {addr}: {bal:.6f} ETH")
    else:
        print(f"\n  ETH DEPLOYER: Not configured")
    
    # Binance (if API configured)
    if config.binance.is_configured:
        print(f"\n  BINANCE:")
        try:
            binance_bal = monitor.get_binance_balances(engine.binance)
            print(f"    BTC: {binance_bal.get('binance_btc', 0):.8f}")
            print(f"    ETH: {binance_bal.get('binance_eth', 0):.6f}")
        except Exception as e:
            print(f"    Error: {e}")
    else:
        print(f"\n  BINANCE: API not configured")
    
    # Binance custody addresses
    print(f"\n  BINANCE CUSTODY ADDRESSES:")
    print(f"    BTC deposit: {config.binance.btc_deposit_address}")
    print(f"    ETH deposit: {config.binance.eth_deposit_address}")
    
    print(f"\n{'=' * 60}\n")
    
    return 0


def cmd_phase1(engine: SyncEngine, args):
    """Execute Phase 1 (deploy gas funding)"""
    print("\n" + "=" * 60)
    print("BAIT INVESTMENT PIPELINE — PHASE 1: DEPLOY GAS")
    print("=" * 60)
    print(f"  Target: Sell 0.01 BTC → ~0.525 ETH for deploy gas")
    print(f"  Testnet: {engine.config.binance.use_testnet}")
    print(f"{'=' * 60}\n")
    
    if not engine.config.binance.is_configured:
        print("ERROR: Binance API not configured. Set BINANCE_API_KEY and BINANCE_API_SECRET.")
        return 1
    
    result = engine.run_phase_1()
    
    # Save results
    output_path = "deploy/investment-pipeline/phase1-results.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nResults saved to: {output_path}")
    
    return 0 if "error" not in result else 1


def cmd_phase2(engine: SyncEngine, args):
    """Execute Phase 2 (liquidity seeding)"""
    print("\n" + "=" * 60)
    print("BAIT INVESTMENT PIPELINE — PHASE 2: LIQUIDITY")
    print("=" * 60)
    print(f"  Target: Sell 0.20 BTC → ~12.5 ETH for Uniswap V3 liquidity")
    print(f"{'=' * 60}\n")
    
    result = engine.run_phase_2()
    
    output_path = "deploy/investment-pipeline/phase2-results.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nResults saved to: {output_path}")
    
    return 0 if "error" not in result else 1


def cmd_full(engine: SyncEngine, args):
    """Execute full pipeline (Phase 1 + 2)"""
    print("\n" + "=" * 60)
    print("BAIT INVESTMENT PIPELINE — FULL EXECUTION")
    print("=" * 60 + "\n")
    
    result = engine.run_full_pipeline(phases=2)
    
    output_path = "deploy/investment-pipeline/full-pipeline-results.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nResults saved to: {output_path}")
    
    return 0 if "error" not in result else 1


def cmd_status(engine: SyncEngine, args):
    """Show pipeline status"""
    status = engine.get_status()
    
    print("\n" + "=" * 60)
    print("BAIT INVESTMENT PIPELINE — STATUS")
    print("=" * 60)
    
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print(f"{'=' * 60}\n")
    return 0


def cmd_stop(engine: SyncEngine, args):
    """Emergency stop"""
    reason = args.reason if hasattr(args, 'reason') and args.reason else "Manual stop via CLI"
    engine.emergency_stop(reason)
    print(f"\nEMERGENCY STOP executed: {reason}")
    return 0


def cmd_simulate(engine: SyncEngine, args):
    """Simulate full pipeline on Binance testnet"""
    # Force testnet
    engine.config.binance.use_testnet = True
    
    print("\n" + "=" * 60)
    print("BAIT INVESTMENT PIPELINE — SIMULATION (TESTNET)")
    print("=" * 60)
    print(f"  Using Binance Testnet: {engine.config.binance.testnet_url}")
    print(f"  No real funds will be used!")
    print(f"{'=' * 60}\n")
    
    # Pre-flight on testnet
    pre_flight = engine.pre_flight_check()
    print(f"  Pre-flight: {pre_flight.get('overall', 'UNKNOWN')}")
    
    if pre_flight["overall"] != "READY":
        print("\n  Testnet pre-flight failed. Check testnet API keys.")
        print("  Get testnet keys at: https://testnet.binance.vision/")
        return 1
    
    # Simulate Phase 1
    print("\n  Simulating Phase 1...")
    swap_calc = engine.binance.calculate_swap_amounts(0.01)
    print(f"    Input: 0.01 BTC")
    print(f"    Expected ETH: {swap_calc['eth_after_fee']:.6f}")
    print(f"    Min ETH (with slippage): {swap_calc['eth_min_with_slippage']:.6f}")
    print(f"    Market price: {swap_calc['ethbtc_price']:.8f} BTC/ETH")
    
    result = {
        "simulation": True,
        "testnet": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase_1_simulated": {
            "btc_input": 0.01,
            "swap_calculation": swap_calc,
            "deployer_eth_target": engine.config.ethereum.phase1_gas_eth,
            "sufficient": swap_calc['eth_after_fee'] >= engine.config.ethereum.phase1_gas_eth
        }
    }
    
    # Simulate Phase 2
    print("\n  Simulating Phase 2...")
    swap_calc_2 = engine.binance.calculate_swap_amounts(0.20)
    print(f"    Input: 0.20 BTC")
    print(f"    Expected ETH: {swap_calc_2['eth_after_fee']:.6f}")
    print(f"    Min ETH (with slippage): {swap_calc_2['eth_min_with_slippage']:.6f}")
    
    result["phase_2_simulated"] = {
        "btc_input": 0.20,
        "swap_calculation": swap_calc_2,
        "liquidity_eth_target": engine.config.ethereum.phase2_liquidity_eth,
        "sufficient": swap_calc_2['eth_after_fee'] >= engine.config.ethereum.phase2_liquidity_eth
    }
    
    # Save simulation results
    output_path = "deploy/investment-pipeline/simulation-results.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  Simulation results saved to: {output_path}")
    print(f"\n{'=' * 60}\n")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="BAIT Investment Pipeline — Automated BTC→ETH→Deploy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Pipeline command")
    
    subparsers.add_parser("preflight", help="Run pre-flight check (dry run)")
    subparsers.add_parser("balances", help="Check all balances")
    subparsers.add_parser("phase1", help="Execute Phase 1 (deploy gas)")
    subparsers.add_parser("phase2", help="Execute Phase 2 (liquidity)")
    subparsers.add_parser("full", help="Execute full pipeline (Phase 1+2)")
    subparsers.add_parser("status", help="Show pipeline status")
    subparsers.add_parser("simulate", help="Simulate on testnet (no real funds)")
    
    stop_parser = subparsers.add_parser("stop", help="Emergency stop")
    stop_parser.add_argument("reason", nargs="?", default="Manual stop", help="Reason for stop")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    setup_logging()
    
    # Initialize pipeline
    config = PipelineConfig()
    engine = SyncEngine(config)
    
    # Dispatch command
    commands = {
        "preflight": cmd_preflight,
        "balances": cmd_balances,
        "phase1": cmd_phase1,
        "phase2": cmd_phase2,
        "full": cmd_full,
        "status": cmd_status,
        "stop": cmd_stop,
        "simulate": cmd_simulate
    }
    
    handler = commands.get(args.command)
    if handler:
        return handler(engine, args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
