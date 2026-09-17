#!/usr/bin/env python3
"""
BAIT Uniswap V3 Liquidity Bootstrapping — Simulation & Deployment Script

Calculates optimal liquidity distribution across price ranges for the wBAIT/WETH pool,
generates forge script commands, and simulates impermanent loss and fee scenarios.

NO ACTUAL ETH/BAIT REQUIRED — simulation only.

Usage:
  python3 liquidity-bootstrapping.py [--capital USD] [--price BAIT_USD] [--eth ETH_USD]
  python3 liquidity-bootstrapping.py --capital 100000 --price 0.00111071 --eth 2000
  python3 liquidity-bootstrapping.py --report-only   # Skip interactive output, just JSON

Requirements: pip install web3 (optional, for on-chain verification)
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ─── Constants ────────────────────────────────────────────────────────────────

# Uniswap V3 constants
Q96 = 2 ** 96  # 2^96 for sqrtPriceX96 encoding
FEE_TIER = 3000  # 0.3%
TICK_SPACING = 60
MIN_TICK = -887272
MAX_TICK = 887272

# BAIT token constants
BAIT_DECIMALS = 8
WETH_DECIMALS = 18
BAIT_MAX_SUPPLY = 21_000_000  # 21M wBAIT

# Default market parameters
DEFAULT_BAIT_PRICE_USD = 0.00111071
DEFAULT_ETH_PRICE_USD = 2000.0
DEFAULT_CAPITAL_USD = 100_000.0

# Slippage protection (basis points)
DEFAULT_SLIPPAGE_BPS = 50  # 0.5%

# Deployment config path (for loading/saving checkpoint data)
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOYMENT_CONFIG_PATH = os.path.join(CONFIG_DIR, "uniswap-v3-deployment.json")
CHECKPOINT_PATH = os.path.join(CONFIG_DIR, ".liquidity-checkpoint.json")


# ─── Math Helpers ─────────────────────────────────────────────────────────────

def price_to_tick(price: float) -> int:
    """Convert price to nearest Uniswap V3 tick."""
    if price <= 0:
        return MIN_TICK
    tick = math.floor(math.log(price) / math.log(1.0001))
    return max(MIN_TICK, min(MAX_TICK, tick))

def tick_to_price(tick: int) -> float:
    """Convert tick to price."""
    return 1.0001 ** tick

def align_tick(tick: int, tick_spacing: int = TICK_SPACING) -> int:
    """Align tick to nearest valid tick for given tick spacing."""
    aligned = round(tick / tick_spacing) * tick_spacing
    return max(MIN_TICK, min(MAX_TICK, aligned))

def price_to_sqrt_price_x96(price: float) -> int:
    """Convert price ratio to sqrtPriceX96 format."""
    if price <= 0:
        return 0
    return int(math.sqrt(price) * Q96)

def sqrt_price_x96_to_price(sqrt_price_x96: int) -> float:
    """Convert sqrtPriceX96 back to price ratio."""
    return (sqrt_price_x96 / Q96) ** 2

def validate_tick_range(tick_lower: int, tick_upper: int, tick_spacing: int = TICK_SPACING) -> Tuple[bool, str]:
    """Validate a tick range for Uniswap V3 compatibility."""
    if tick_lower >= tick_upper:
        return False, f"tickLower ({tick_lower}) must be < tickUpper ({tick_upper})"
    if tick_lower % tick_spacing != 0:
        return False, f"tickLower ({tick_lower}) not aligned to tickSpacing ({tick_spacing})"
    if tick_upper % tick_spacing != 0:
        return False, f"tickUpper ({tick_upper}) not aligned to tickSpacing ({tick_spacing})"
    if tick_lower < MIN_TICK:
        return False, f"tickLower ({tick_lower}) below MIN_TICK ({MIN_TICK})"
    if tick_upper > MAX_TICK:
        return False, f"tickUpper ({tick_upper}) above MAX_TICK ({MAX_TICK})"
    return True, "Valid"

def calculate_liquidity_amount(
    sqrt_price_x96: int,
    sqrt_lower_x96: int,
    sqrt_upper_x96: int,
    amount0: int,
    amount1: int
) -> float:
    """Calculate liquidity amount for a concentrated position (simplified)."""
    if sqrt_price_x96 <= sqrt_lower_x96:
        # Price below range — only token0
        return amount0 * sqrt_lower_x96 * sqrt_upper_x96 / (Q96 * (sqrt_upper_x96 - sqrt_lower_x96))
    elif sqrt_price_x96 >= sqrt_upper_x96:
        # Price above range — only token1
        return amount1 * Q96 / (sqrt_upper_x96 - sqrt_lower_x96)
    else:
        # Price in range — both tokens contribute
        liq0 = amount0 * sqrt_price_x96 * sqrt_upper_x96 / (Q96 * (sqrt_upper_x96 - sqrt_price_x96))
        liq1 = amount1 * Q96 / (sqrt_price_x96 - sqrt_lower_x96)
        return min(liq0, liq1)

def format_wbait(amount: float) -> str:
    """Format amount in wBAIT (8 decimals)."""
    return f"{amount:,.2f}"

def format_eth(amount: float) -> str:
    """Format amount in ETH (18 decimals)."""
    return f"{amount:,.6f}"

def wbait_to_wei(amount: float) -> int:
    """Convert wBAIT to wei (8 decimals)."""
    return int(amount * 10 ** BAIT_DECIMALS)

def eth_to_wei(amount: float) -> int:
    """Convert ETH to wei (18 decimals)."""
    return int(amount * 10 ** WETH_DECIMALS)

def apply_slippage(amount: int, slippage_bps: int = DEFAULT_SLIPPAGE_BPS) -> int:
    """Apply slippage protection to get minimum amount."""
    return amount * (10000 - slippage_bps) // 10000


# ─── Liquidity Position ──────────────────────────────────────────────────────

@dataclass
class LiquidityPosition:
    name: str
    tick_lower: int
    tick_upper: int
    price_lower: float
    price_upper: float
    capital_pct: float  # % of total capital
    wbait_amount: float
    weth_amount: float
    capital_usd: float
    slippage_bps: int = DEFAULT_SLIPPAGE_BPS

    def validate(self) -> Tuple[bool, str]:
        """Validate tick range."""
        return validate_tick_range(self.tick_lower, self.tick_upper)

    @property
    def wbait_wei(self) -> int:
        return wbait_to_wei(self.wbait_amount)

    @property
    def weth_wei(self) -> int:
        return eth_to_wei(self.weth_amount)

    @property
    def wbait_min_wei(self) -> int:
        """wBAIT amount with slippage protection."""
        return apply_slippage(self.wbait_wei, self.slippage_bps)

    @property
    def weth_min_wei(self) -> int:
        """WETH amount with slippage protection."""
        return apply_slippage(self.weth_wei, self.slippage_bps)

    @property
    def range_width_pct(self) -> float:
        """Width of range as % of current price."""
        if self.price_lower == 0:
            return 0.0
        return (self.price_upper - self.price_lower) / ((self.price_upper + self.price_lower) / 2) * 100

    def to_dict(self) -> dict:
        valid, msg = self.validate()
        return {
            "name": self.name,
            "tickLower": self.tick_lower,
            "tickUpper": self.tick_upper,
            "priceLower": self.price_lower,
            "priceUpper": self.price_upper,
            "capitalPct": f"{self.capital_pct:.0%}",
            "wbaitAmount": format_wbait(self.wbait_amount),
            "wbaitAmountWei": str(self.wbait_wei),
            "wbaitAmountMinWei": str(self.wbait_min_wei),
            "wethAmount": format_eth(self.weth_amount),
            "wethAmountWei": str(self.weth_wei),
            "wethAmountMinWei": str(self.weth_min_wei),
            "capitalUSD": f"${self.capital_usd:,.0f}",
            "rangeWidthPct": f"{self.range_width_pct:.1f}%",
            "slippageBps": self.slippage_bps,
            "valid": valid,
            "validationMsg": msg if not valid else "OK",
        }


# ─── Liquidity Distribution Calculator ────────────────────────────────────────

class LiquidityBootstrapper:
    def __init__(self, bait_price_usd: float, eth_price_usd: float, capital_usd: float,
                 slippage_bps: int = DEFAULT_SLIPPAGE_BPS):
        self.bait_price_usd = bait_price_usd
        self.eth_price_usd = eth_price_usd
        self.capital_usd = capital_usd
        self.bait_price_eth = bait_price_usd / eth_price_usd
        self.slippage_bps = slippage_bps

        print(f"\n{'='*70}")
        print(f"BAIT Uniswap V3 Liquidity Bootstrapping — SIMULATION")
        print(f"{'='*70}")
        print(f"BAIT price:  ${bait_price_usd:.8f}")
        print(f"ETH price:   ${eth_price_usd:,.2f}")
        print(f"BAIT/ETH:    {self.bait_price_eth:.12f}")
        print(f"Capital:     ${capital_usd:,.0f}")
        print(f"Slippage:    {slippage_bps/100:.2f}%")
        print(f"{'='*70}\n")

    def calculate_sqrt_price_x96(self) -> int:
        """Calculate sqrtPriceX96 for the initial pool price."""
        sqrt_price_x96 = price_to_sqrt_price_x96(self.bait_price_eth)
        current_tick = price_to_tick(self.bait_price_eth)
        aligned_tick = align_tick(current_tick)

        print("Initial Price Calculation:")
        print(f"  Price (WETH/BAIT):    {self.bait_price_eth:.12f}")
        print(f"  sqrtPriceX96:         {sqrt_price_x96}")
        print(f"  Contract constant:    2190640149935016301856")
        print(f"  Current tick:         {current_tick}")
        print(f"  Aligned tick:         {aligned_tick}")
        print(f"  Aligned price:        {tick_to_price(aligned_tick):.12f}")

        # Verify against contract constant
        contract_sqrt = 2190640149935016301856
        contract_price = sqrt_price_x96_to_price(contract_sqrt)
        print(f"  Contract price:       {contract_price:.12f}")
        diff_pct = abs(contract_price - self.bait_price_eth) / self.bait_price_eth * 100
        print(f"  Difference:           {diff_pct:.4f}%")
        if diff_pct > 1.0:
            print(f"  ⚠ WARNING: sqrtPriceX96 differs from contract by >1%")
        print()

        return sqrt_price_x96

    def calculate_optimal_distribution(self) -> List[LiquidityPosition]:
        """Calculate optimal liquidity distribution across price ranges."""
        current_tick = align_tick(price_to_tick(self.bait_price_eth))

        # Define range multipliers relative to current price
        # Ranges are designed to balance fee capture vs IL risk
        ranges = [
            {
                "name": "Core (Tight)",
                "lower_mult": 0.70,
                "upper_mult": 1.40,
                "capital_pct": 0.50,
                "description": "±30-40% from current price — max fee capture"
            },
            {
                "name": "Mid (Wide)",
                "lower_mult": 0.35,
                "upper_mult": 2.80,
                "capital_pct": 0.30,
                "description": "Broader range — price stability buffer"
            },
            {
                "name": "Outer (Safety)",
                "lower_mult": 0.10,
                "upper_mult": 9.00,
                "capital_pct": 0.20,
                "description": "Very wide — liquidity in extreme moves"
            },
        ]

        positions = []
        print("Optimal Liquidity Distribution:\n")

        for r in ranges:
            price_lower = self.bait_price_eth * r["lower_mult"]
            price_upper = self.bait_price_eth * r["upper_mult"]

            tick_lower = align_tick(price_to_tick(price_lower))
            tick_upper = align_tick(price_to_tick(price_upper))

            # Recalculate exact prices from aligned ticks
            price_lower = tick_to_price(tick_lower)
            price_upper = tick_to_price(tick_upper)

            # Validate tick range
            valid, msg = validate_tick_range(tick_lower, tick_upper)
            if not valid:
                print(f"  ⚠ INVALID RANGE for {r['name']}: {msg}")
                continue

            # Capital allocation: split 50/50 between BAIT and ETH by USD value
            capital = self.capital_usd * r["capital_pct"]
            wbait_usd = capital / 2
            weth_usd = capital / 2

            wbait_amount = wbait_usd / self.bait_price_usd
            weth_amount = weth_usd / self.eth_price_usd

            # Check against max supply
            if wbait_amount > BAIT_MAX_SUPPLY:
                print(f"  ⚠ WARNING: {r['name']} requires {format_wbait(wbait_amount)} wBAIT, "
                      f"exceeding max supply of {BAIT_MAX_SUPPLY:,}")

            pos = LiquidityPosition(
                name=r["name"],
                tick_lower=tick_lower,
                tick_upper=tick_upper,
                price_lower=price_lower,
                price_upper=price_upper,
                capital_pct=r["capital_pct"],
                wbait_amount=wbait_amount,
                weth_amount=weth_amount,
                capital_usd=capital,
                slippage_bps=self.slippage_bps,
            )
            positions.append(pos)

            print(f"  {r['name']} ({r['description']}):")
            print(f"    Ticks:      [{tick_lower}, {tick_upper}]")
            print(f"    Price:      [{price_lower:.12f}, {price_upper:.12f}] BAIT/ETH")
            print(f"    Range width: {pos.range_width_pct:.1f}%")
            print(f"    Capital:    ${capital:,.0f} ({r['capital_pct']:.0%})")
            print(f"    wBAIT:      {format_wbait(wbait_amount)}")
            print(f"    WETH:       {format_eth(weth_amount)}")
            print(f"    Slippage:   {self.slippage_bps/100:.2f}% (min amounts calculated)")
            print(f"    Valid:      ✓ {msg}")
            print()

        return positions

    def generate_forge_commands(self, positions: List[LiquidityPosition],
                                liquidity_address: str = "$LIQUIDITY_ADDRESS",
                                rpc_url: str = "$RPC_URL",
                                owner_key: str = "$OWNER_KEY") -> List[str]:
        """Generate forge/cast commands for pool creation and liquidity addition."""
        sqrt_price_x96 = self.calculate_sqrt_price_x96()

        commands = []
        commands.append("#!/bin/bash")
        commands.append("# ─── BAIT Uniswap V3 Pool Deployment Commands ───")
        commands.append(f"# Generated: {datetime.now(timezone.utc).isoformat()}")
        commands.append(f"# Capital: ${self.capital_usd:,.0f} | BAIT: ${self.bait_price_usd:.8f} | ETH: ${self.eth_price_usd:,.2f}")
        commands.append(f"# Fee tier: {FEE_TIER} (0.3%) | Tick spacing: {TICK_SPACING}")
        commands.append("")

        # Step 1: Create pool
        commands.append("# Step 1: Create the wBAIT/WETH pool")
        commands.append(f"cast send {liquidity_address} 'createPool()' --rpc-url {rpc_url} --private-key {owner_key}")
        commands.append("")

        # Step 2: Verify pool was created
        commands.append("# Step 1b: Verify pool exists")
        commands.append(f"cast call $FACTORY_ADDRESS 'getPool(address,address,uint24)(address)' $WBAIT_ADDRESS $WETH_ADDRESS {FEE_TIER} --rpc-url {rpc_url}")
        commands.append("")

        # Step 3: Add liquidity for each position
        for i, pos in enumerate(positions):
            valid, msg = pos.validate()
            if not valid:
                commands.append(f"# Step {i+2}: SKIPPED — {pos.name} ({msg})")
                continue

            commands.append(f"# Step {i+2}: Add {pos.name} liquidity ({pos.capital_pct:.0%} of capital)")
            commands.append(
                f"cast send {liquidity_address} 'addLiquidity(uint256,uint256,int24,int24)' "
                f"{pos.wbait_wei} {pos.weth_wei} {pos.tick_lower} {pos.tick_upper} "
                f"--rpc-url {rpc_url} --private-key {owner_key}"
            )
            commands.append("")

        # Add verification commands
        commands.append("# ─── Post-Deployment Verification ───")
        commands.append(f"cast call $POOL_ADDRESS 'slot0()(uint160,int24,uint16,uint16,uint16,uint8,bool)' --rpc-url {rpc_url}")
        commands.append(f"cast call $POOL_ADDRESS 'liquidity()(uint128)' --rpc-url {rpc_url}")
        commands.append("")

        # Forge script variant
        commands.append("# ─── Alternative: Single Forge Script ───")
        commands.append("forge script script/DeployBAIT.s.sol --rpc-url $RPC_URL --broadcast --verify")

        print("Generated Forge Commands:")
        for cmd in commands:
            print(f"  {cmd}")
        print()

        return commands

    def simulate_impermanent_loss(self, positions: List[LiquidityPosition],
                                   price_changes: List[float] = None) -> dict:
        """Simulate impermanent loss for various price change scenarios."""
        if price_changes is None:
            price_changes = [0.5, 0.7, 0.8, 0.9, 1.1, 1.25, 1.5, 2.0, 3.0, 5.0]

        print("Impermanent Loss Simulation:")
        print(f"{'Price Change':>12} | {'IL %':>10} | {'HODL Value':>12} | {'LP Value':>12} | {'Diff':>10} | {'In Range?':>10}")
        print("-" * 78)

        results = []
        initial_capital = self.capital_usd
        current_tick = align_tick(price_to_tick(self.bait_price_eth))

        for mult in price_changes:
            new_price = self.bait_price_eth * mult
            new_tick = price_to_tick(new_price)

            # For concentrated liquidity, IL depends on whether price stays in range
            # Simplified IL formula for Uniswap V3: IL = 2*sqrt(p)/(1+p) - 1
            # where p = price_ratio (new/old)
            p = mult
            if p > 0:
                il_fraction = 2 * math.sqrt(p) / (1 + p) - 1
                il_pct = il_fraction * 100
            else:
                il_pct = -100.0

            # Check if price is still in each position's range
            in_range_positions = []
            for pos in positions:
                in_range = pos.tick_lower <= new_tick <= pos.tick_upper
                in_range_positions.append(in_range)
            any_in_range = any(in_range_positions)

            # HODL value
            bait_hodl_value = (initial_capital / 2) * mult
            eth_hodl_value = initial_capital / 2
            hodl_total = bait_hodl_value + eth_hodl_value

            # LP value = HODL * (1 + IL)
            # If out of range, IL is worse (position becomes single-sided)
            if not any_in_range:
                # Out of range: position is single-sided, worse IL
                lp_value = hodl_total * (1 + il_fraction) * 0.85  # Approximate penalty
            else:
                lp_value = hodl_total * (1 + il_fraction)

            diff = lp_value - hodl_total
            range_status = "YES" if any_in_range else "NO ⚠"

            print(f"{'×' + str(mult):>12} | {il_pct:>9.2f}% | ${hodl_total:>10,.0f} | ${lp_value:>10,.0f} | ${diff:>9,.0f} | {range_status:>10}")

            results.append({
                "priceMultiplier": mult,
                "impermanentLossPct": round(il_pct, 4),
                "hodlValue": round(hodl_total, 2),
                "lpValue": round(lp_value, 2),
                "difference": round(diff, 2),
                "inRange": any_in_range,
                "newTick": new_tick,
                "newPriceETH": new_price,
            })

        print()
        return results

    def estimate_fee_earnings(self, positions: List[LiquidityPosition],
                               daily_volume_usd: float = 50_000) -> dict:
        """Estimate fee earnings based on projected daily volume."""
        fee_rate = FEE_TIER / 1_000_000  # 0.003 for 0.3%

        print("Fee Earning Estimates:")
        print(f"  Fee tier:        {FEE_TIER/10000:.2%}")
        print(f"  Daily volume:    ${daily_volume_usd:,.0f}")
        print(f"  Fee rate:        {fee_rate:.4f}")
        print()

        total_daily_fees = daily_volume_usd * fee_rate

        results = []
        for pos in positions:
            # Estimate share of fees proportional to capital allocation
            # Concentration factor: tighter ranges capture more fees per unit of capital
            concentration_factor = 1.0
            if "Core" in pos.name:
                concentration_factor = 1.5
            elif "Mid" in pos.name:
                concentration_factor = 1.0
            elif "Outer" in pos.name:
                concentration_factor = 0.3

            daily_fees = total_daily_fees * pos.capital_pct * concentration_factor
            monthly_fees = daily_fees * 30
            yearly_fees = daily_fees * 365
            apr = (yearly_fees / pos.capital_usd) * 100 if pos.capital_usd > 0 else 0

            # Net APY (fees - IL estimate)
            # Assume moderate IL of ~2-5% annually for the core position
            il_estimate_pct = 2.0
            if "Mid" in pos.name:
                il_estimate_pct = 1.0
            elif "Outer" in pos.name:
                il_estimate_pct = 0.5
            net_apy = apr - il_estimate_pct

            print(f"  {pos.name}:")
            print(f"    Daily fees:   ${daily_fees:,.2f}")
            print(f"    Monthly fees: ${monthly_fees:,.2f}")
            print(f"    Yearly fees:  ${yearly_fees:,.2f}")
            print(f"    Gross APR:    {apr:.1f}%")
            print(f"    Est. IL:      ~{il_estimate_pct:.1f}% annually")
            print(f"    Net APY:      ~{net_apy:.1f}%")
            print()

            results.append({
                "position": pos.name,
                "dailyFeesUSD": round(daily_fees, 2),
                "monthlyFeesUSD": round(monthly_fees, 2),
                "yearlyFeesUSD": round(yearly_fees, 2),
                "grossAPR": round(apr, 2),
                "estimatedILPct": il_estimate_pct,
                "netAPY": round(net_apy, 2),
                "concentrationFactor": concentration_factor
            })

        return results

    def simulate_price_impact(self, swap_sizes_usd: List[float] = None) -> List[dict]:
        """Simulate price impact for various swap sizes."""
        if swap_sizes_usd is None:
            swap_sizes_usd = [100, 500, 1000, 5000, 10000, 25000, 50000]

        print("Price Impact Simulation (simplified constant-product model):")
        print(f"{'Swap Size':>12} | {'Price Impact':>12} | {'Effective Price':>14}")
        print("-" * 45)

        results = []
        # TVL approximation (total capital / 2 for each side)
        tvl_usd = self.capital_usd

        for size in swap_sizes_usd:
            # Simplified price impact: impact ≈ (size / tvl) for small swaps
            # For constant product: impact = size / (tvl + size)
            impact = size / (tvl_usd + size)
            effective_price = self.bait_price_usd * (1 + impact)

            print(f"${size:>10,.0f} | {impact:>11.2%} | ${effective_price:>12.8f}")

            results.append({
                "swapSizeUSD": size,
                "priceImpactPct": round(impact * 100, 4),
                "effectivePrice": round(effective_price, 8),
            })

        print()
        return results

    def save_checkpoint(self, report: dict):
        """Save checkpoint data for resumable deployments."""
        checkpoint = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "parameters": report["parameters"],
            "positions": report["liquidityPositions"],
            "forgeCommands": report["forgeCommands"],
        }
        with open(CHECKPOINT_PATH, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        print(f"Checkpoint saved to: {CHECKPOINT_PATH}")

    def load_checkpoint(self) -> Optional[dict]:
        """Load checkpoint data if available."""
        if os.path.exists(CHECKPOINT_PATH):
            with open(CHECKPOINT_PATH, 'r') as f:
                return json.load(f)
        return None

    def generate_full_report(self, daily_volume: float = 50_000) -> dict:
        """Generate complete bootstrapping report with all calculations."""
        sqrt_price_x96 = self.calculate_sqrt_price_x96()
        positions = self.calculate_optimal_distribution()
        forge_commands = self.generate_forge_commands(positions)
        il_simulation = self.simulate_impermanent_loss(positions)
        fee_estimates = self.estimate_fee_earnings(positions, daily_volume_usd=daily_volume)
        price_impacts = self.simulate_price_impact()

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "parameters": {
                "baitPriceUSD": self.bait_price_usd,
                "ethPriceUSD": self.eth_price_usd,
                "baitPriceETH": self.bait_price_eth,
                "capitalUSD": self.capital_usd,
                "feeTier": FEE_TIER,
                "tickSpacing": TICK_SPACING,
                "slippageBps": self.slippage_bps,
            },
            "initialPrice": {
                "sqrtPriceX96": sqrt_price_x96,
                "contractConstant": 2190640149935016301856,
                "currentTick": align_tick(price_to_tick(self.bait_price_eth)),
            },
            "liquidityPositions": [p.to_dict() for p in positions],
            "impermanentLoss": il_simulation,
            "feeEstimates": fee_estimates,
            "priceImpactSimulation": price_impacts,
            "forgeCommands": forge_commands,
            "summary": {
                "totalWBait": format_wbait(sum(p.wbait_amount for p in positions)),
                "totalWETH": format_eth(sum(p.weth_amount for p in positions)),
                "totalCapitalUSD": f"${self.capital_usd:,.0f}",
                "positionCount": len(positions),
                "allPositionsValid": all(p.validate()[0] for p in positions),
                "maxSupplyCheck": sum(p.wbait_amount for p in positions) <= BAIT_MAX_SUPPLY,
            }
        }

        # Save report
        report_path = os.path.join(CONFIG_DIR, 'liquidity-bootstrapping-report.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {report_path}")

        # Save checkpoint
        self.save_checkpoint(report)

        return report


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BAIT Uniswap V3 Liquidity Bootstrapping Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 liquidity-bootstrapping.py
  python3 liquidity-bootstrapping.py --capital 250000
  python3 liquidity-bootstrapping.py --price 0.002 --eth 3000 --capital 50000
  python3 liquidity-bootstrapping.py --report-only
        """
    )
    parser.add_argument("--capital", type=float, default=DEFAULT_CAPITAL_USD,
                       help=f"Total capital in USD (default: ${DEFAULT_CAPITAL_USD:,.0f})")
    parser.add_argument("--price", type=float, default=DEFAULT_BAIT_PRICE_USD,
                       help=f"BAIT price in USD (default: ${DEFAULT_BAIT_PRICE_USD})")
    parser.add_argument("--eth", type=float, default=DEFAULT_ETH_PRICE_USD,
                       help=f"ETH price in USD (default: ${DEFAULT_ETH_PRICE_USD:,.0f})")
    parser.add_argument("--volume", type=float, default=50_000,
                       help="Projected daily volume in USD (default: $50,000)")
    parser.add_argument("--slippage", type=int, default=DEFAULT_SLIPPAGE_BPS,
                       help=f"Slippage tolerance in basis points (default: {DEFAULT_SLIPPAGE_BPS})")
    parser.add_argument("--report-only", action="store_true",
                       help="Only generate JSON report, minimize stdout output")
    args = parser.parse_args()

    bootstrapper = LiquidityBootstrapper(
        bait_price_usd=args.price,
        eth_price_usd=args.eth,
        capital_usd=args.capital,
        slippage_bps=args.slippage,
    )

    report = bootstrapper.generate_full_report(daily_volume=args.volume)

    # Print summary
    print("\n" + "=" * 70)
    print("BOOTSTRAPPING SUMMARY")
    print("=" * 70)
    print(f"  Total wBAIT needed:    {report['summary']['totalWBait']}")
    print(f"  Total WETH needed:     {report['summary']['totalWETH']}")
    print(f"  Total capital:         {report['summary']['totalCapitalUSD']}")
    print(f"  Liquidity positions:   {report['summary']['positionCount']}")
    print(f"  All positions valid:   {'✓' if report['summary']['allPositionsValid'] else '✗'}")
    print(f"  Max supply check:      {'✓' if report['summary']['maxSupplyCheck'] else '✗ NEEDS REVIEW'}")
    print(f"  sqrtPriceX96:          {report['initialPrice']['sqrtPriceX96']}")
    print(f"  Slippage protection:   {args.slippage/100:.2f}%")
    print()
    print("  NOTE: This is a SIMULATION only. No actual ETH/BAIT required.")
    print("  Use the generated forge commands for actual deployment.")
    print("  Minimum amounts include slippage protection for sandwich attack mitigation.")
    print("=" * 70)


if __name__ == "__main__":
    main()
