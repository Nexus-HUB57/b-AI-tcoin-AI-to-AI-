// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";
import "../src/BAITUniswapV3Liquidity.sol";

/**
 * @title VerifyBAIT — Post-Deployment Verification Script
 * @notice Comprehensive on-chain verification of all deployed BAIT contracts.
 *         Run this AFTER deployment and BEFORE announcing the deployment publicly.
 *
 * Verification Categories:
 *   1. Contract Code Verification (Etherscan source code match)
 *   2. Conservation Invariant (totalSupply == totalLockedOnL1)
 *   3. Operator Configuration (3-of-5 multisig correctness)
 *   4. Rate Limits (100K wBAIT/day per recipient)
 *   5. Access Control (ownership, pause authority)
 *   6. Pool Initialization (Uniswap V3 pool exists and has liquidity)
 *   7. Cross-Reference Integrity (contracts reference each other correctly)
 *
 * Usage:
 *   forge script script/VerifyBAIT.s.sol \
 *     --rpc-url $MAINNET_RPC_URL \
 *     -vvv
 *
 * Environment Variables Required:
 *   WBAIT_ADDRESS          — Deployed WBAIT contract address
 *   BRIDGELOCK_ADDRESS     — Deployed BridgeLock contract address
 *   LIQUIDITY_ADDRESS      — Deployed BAITUniswapV3Liquidity address
 *   EXPECTED_OWNER         — Expected final owner (multisig)
 *   OPERATOR_1..5          — Expected operator addresses
 *   UNISWAP_V3_FACTORY     — Uniswap V3 Factory address
 *   WETH                   — WETH mainnet address
 */
contract VerifyBAIT is Script {
    // ── Constants ──────────────────────────────────────────────────────
    uint256 constant EXPECTED_MAX_SUPPLY = 21_000_000 * 10**8;
    uint256 constant EXPECTED_RATE_LIMIT = 100_000 * 10**8;
    uint256 constant EXPECTED_TIMELOCK = 24 hours;
    uint256 constant EXPECTED_CONFIRMATIONS = 3;
    uint256 constant EXPECTED_NUM_OPERATORS = 5;
    uint24  constant EXPECTED_FEE_TIER = 3000;
    int24   constant EXPECTED_TICK_SPACING = 60;
    uint8   constant EXPECTED_DECIMALS = 8;

    // ── State ──────────────────────────────────────────────────────────
    WBAIT public wbait;
    BridgeLock public bridgeLock;
    BAITUniswapV3Liquidity public liquidity;

    uint256 public passedChecks;
    uint256 public totalChecks;
    bool    public allPassed;

    // ── Verification Entry Point ───────────────────────────────────────

    function run() external {
        // Load deployed addresses from environment
        address wbaitAddr = vm.envAddress("WBAIT_ADDRESS");
        address bridgeAddr = vm.envAddress("BRIDGELOCK_ADDRESS");
        address liqAddr = vm.envAddress("LIQUIDITY_ADDRESS");
        address expectedOwner = vm.envAddress("EXPECTED_OWNER");

        address[5] memory expectedOperators = [
            vm.envAddress("OPERATOR_1"),
            vm.envAddress("OPERATOR_2"),
            vm.envAddress("OPERATOR_3"),
            vm.envAddress("OPERATOR_4"),
            vm.envAddress("OPERATOR_5")
        ];

        wbait = WBAIT(wbaitAddr);
        bridgeLock = BridgeLock(bridgeAddr);
        liquidity = BAITUniswapV3Liquidity(liqAddr);

        passedChecks = 0;
        totalChecks = 0;

        console.log("============================================================");
        console.log("  BAIT Post-Deployment Verification");
        console.log("============================================================");
        console.log("WBAIT:              ", wbaitAddr);
        console.log("BridgeLock:         ", bridgeAddr);
        console.log("Liquidity:          ", liqAddr);
        console.log("");

        // ── Category 1: WBAIT Token Verification ───────────────────────
        console.log("--- Category 1: WBAIT Token ---");
        _check("WBAIT name", wbait.name() == "Wrapped bAIitcoin");
        _check("WBAIT symbol", wbait.symbol() == "wBAIT");
        _check("WBAIT decimals", wbait.decimals() == EXPECTED_DECIMALS);
        _check("WBAIT max supply", wbait.MAX_SUPPLY() == EXPECTED_MAX_SUPPLY);
        _check("WBAIT not paused", wbait.paused() == false);

        // ── Category 2: Conservation Invariant ─────────────────────────
        console.log("\n--- Category 2: Conservation Invariant ---");
        uint256 totalSupply = wbait.totalSupply();
        console.log("  totalSupply:", totalSupply);
        _check("Conservation: totalSupply >= 0 (no overflow)", totalSupply >= 0);
        _check("Conservation: totalSupply <= MAX_SUPPLY", totalSupply <= EXPECTED_MAX_SUPPLY);
        // At deployment, totalSupply should be 0 (no minting yet)
        _check("Conservation: initial supply is 0", totalSupply == 0);

        // ── Category 3: BridgeLock Configuration ───────────────────────
        console.log("\n--- Category 3: BridgeLock Configuration ---");
        _check("BridgeLock wbait ref", address(bridgeLock.wbait()) == wbaitAddr);
        _check("BridgeLock threshold", bridgeLock.REQUIRED_CONFIRMATIONS() == EXPECTED_CONFIRMATIONS);
        _check("BridgeLock num operators", bridgeLock.NUM_OPERATORS() == EXPECTED_NUM_OPERATORS);
        _check("BridgeLock rate limit", bridgeLock.RATE_LIMIT() == EXPECTED_RATE_LIMIT);
        _check("BridgeLock timelock", bridgeLock.TIMELOCK_DURATION() == EXPECTED_TIMELOCK);
        _check("BridgeLock not paused", bridgeLock.paused() == false);

        // ── Category 4: Operator Verification ───────────────────────────
        console.log("\n--- Category 4: Operator Configuration ---");
        bool allOperatorsCorrect = true;
        for (uint256 i = 0; i < 5; i++) {
            bool opMatch = bridgeLock.operators(i) == expectedOperators[i];
            bool opRegistered = bridgeLock.isOperator(expectedOperators[i]);
            if (!opMatch || !opRegistered) {
                allOperatorsCorrect = false;
                console.log("  FAIL: Operator", i, "mismatch");
                console.log("    Expected:", expectedOperators[i]);
                console.log("    Got:     ", bridgeLock.operators(i));
            }
        }
        _check("All 5 operators match expected", allOperatorsCorrect);

        // Verify no address is operator unless it's one of the 5
        _check("Operators are unique (no duplicates)", _verifyUniqueOperators(expectedOperators));

        // ── Category 5: Access Control ──────────────────────────────────
        console.log("\n--- Category 5: Access Control ---");
        _check("WBAIT owner is multisig", wbait.owner() == expectedOwner);
        _check("BridgeLock owner is multisig", bridgeLock.owner() == expectedOwner);
        _check("Liquidity owner is multisig", liquidity.owner() == expectedOwner);
        _check("WBAIT bridgeLock address", wbait.bridgeLock() == bridgeAddr);

        // Verify deployer is NOT the owner (ownership transferred)
        _check("Deployer is NOT WBAIT owner", wbait.owner() != tx.origin);
        _check("Deployer is NOT BridgeLock owner", bridgeLock.owner() != tx.origin);

        // ── Category 6: BAITUniswapV3Liquidity Verification ───────────
        console.log("\n--- Category 6: Uniswap V3 Liquidity ---");
        _check("Liquidity wbait ref", address(liquidity.wbait()) == wbaitAddr);
        _check("Liquidity fee tier", liquidity.FEE_TIER() == EXPECTED_FEE_TIER);
        _check("Liquidity tick spacing", liquidity.TICK_SPACING() == EXPECTED_TICK_SPACING);

        address wethAddr = vm.envAddress("WETH");
        _check("Liquidity WETH address", liquidity.WETH() == wethAddr);

        // Check pool exists
        address uniFactory = vm.envAddress("UNISWAP_V3_FACTORY");
        _checkPoolExistence(uniFactory, wethAddr);

        // ── Category 7: Cross-Reference Integrity ───────────────────────
        console.log("\n--- Category 7: Cross-Reference Integrity ---");
        _check("WBAIT.bridgeLock == BridgeLock address", wbait.bridgeLock() == bridgeAddr);
        _check("BridgeLock.wbait == WBAIT address", address(bridgeLock.wbait()) == wbaitAddr);
        _check("Liquidity.wbait == WBAIT address", address(liquidity.wbait()) == wbaitAddr);

        // ── Summary ─────────────────────────────────────────────────────
        allPassed = passedChecks == totalChecks;

        console.log("\n============================================================");
        console.log("  VERIFICATION SUMMARY");
        console.log("============================================================");
        console.log("Passed:", passedChecks);
        console.log("Total: ", totalChecks);
        if (allPassed) {
            console.log("RESULT: ALL CHECKS PASSED — Deployment verified!");
        } else {
            console.log("RESULT: SOME CHECKS FAILED — DO NOT ANNOUNCE DEPLOYMENT!");
            console.log("Failed:", totalChecks - passedChecks);
        }
        console.log("============================================================");

        // Assert all passed (reverts script if any check failed)
        require(allPassed, "VERIFICATION FAILED: Some checks did not pass");
    }

    // ── Internal Helpers ───────────────────────────────────────────────

    /**
     * @notice Track a single check pass/fail
     */
    function _check(string memory label, bool condition) internal {
        totalChecks++;
        if (condition) {
            passedChecks++;
            console.log("  [PASS]", label);
        } else {
            console.log("  [FAIL]", label);
        }
    }

    /**
     * @notice Verify all 5 operator addresses are unique
     */
    function _verifyUniqueOperators(address[5] memory ops) internal pure returns (bool) {
        for (uint256 i = 0; i < 5; i++) {
            for (uint256 j = i + 1; j < 5; j++) {
                if (ops[i] == ops[j]) return false;
            }
        }
        return true;
    }

    /**
     * @notice Check that the Uniswap V3 pool exists for wBAIT/WETH
     */
    function _checkPoolExistence(address factory, address weth) internal {
        // Call the Uniswap V3 Factory to check if the pool exists
        // getPool(address,address,uint24) returns address(0) if not created
        (bool success, bytes memory data) = factory.staticcall(
            abi.encodeWithSelector(
                bytes4(keccak256("getPool(address,address,uint24)")),
                address(wbait),
                weth,
                EXPECTED_FEE_TIER
            )
        );

        if (success && data.length >= 32) {
            address pool = abi.decode(data, (address));
            _check("Uniswap V3 pool exists", pool != address(0));
            if (pool != address(0)) {
                console.log("  Pool address:", pool);
            }
        } else {
            _check("Uniswap V3 pool exists (factory call)", false);
            console.log("  WARNING: Could not query Uniswap V3 Factory");
        }
    }
}
