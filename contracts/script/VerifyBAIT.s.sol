// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/**
 * @title VerifyBAIT - Post-Deployment Verification Script
 * @notice Comprehensive on-chain verification of all deployed BAIT contracts.
 *         Run this AFTER deployment and BEFORE announcing the deployment publicly.
 *
 * Usage:
 *   forge script script/VerifyBAIT.s.sol \
 *     --rpc-url $RPC_URL \
 *     -vvv
 *
 * Environment Variables Required:
 *   WBAIT_ADDRESS          - Deployed WBAIT contract address
 *   BRIDGELOCK_ADDRESS     - Deployed BridgeLock contract address
 *   EXPECTED_OWNER         - Expected final owner (multisig)
 *   OPERATOR_1..5          - Expected operator addresses
 */
contract VerifyBAIT is Script {
    // -- Constants --
    uint256 constant EXPECTED_MAX_SUPPLY = 21_000_000 * 10**8;
    uint256 constant EXPECTED_RATE_LIMIT = 100_000 * 10**8;
    uint256 constant EXPECTED_TIMELOCK = 24 hours;
    uint256 constant EXPECTED_CONFIRMATIONS = 3;
    uint256 constant EXPECTED_NUM_OPERATORS = 5;
    uint8   constant EXPECTED_DECIMALS = 8;

    // -- State --
    WBAIT public wbait;
    BridgeLock public bridgeLock;

    uint256 public passedChecks;
    uint256 public totalChecks;
    bool    public allPassed;

    // -- Verification Entry Point --

    function run() external {
        // Load deployed addresses from environment
        address wbaitAddr = vm.envAddress("WBAIT_ADDRESS");
        address bridgeAddr = vm.envAddress("BRIDGELOCK_ADDRESS");
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

        passedChecks = 0;
        totalChecks = 0;

        console.log("============================================================");
        console.log("  BAIT Post-Deployment Verification");
        console.log("============================================================");
        console.log("WBAIT:              ", wbaitAddr);
        console.log("BridgeLock:         ", bridgeAddr);
        console.log("");

        // -- Category 1: WBAIT Token Verification --
        console.log("--- Category 1: WBAIT Token ---");
        _check("WBAIT decimals", wbait.decimals() == EXPECTED_DECIMALS);
        _check("WBAIT max supply", wbait.MAX_SUPPLY() == EXPECTED_MAX_SUPPLY);
        _check("WBAIT not paused", wbait.paused() == false);

        // -- Category 2: Conservation Invariant --
        console.log("--- Category 2: Conservation Invariant ---");
        uint256 totalSupply = wbait.totalSupply();
        console.log("  totalSupply:", totalSupply);
        _check("Conservation: totalSupply <= MAX_SUPPLY", totalSupply <= EXPECTED_MAX_SUPPLY);
        _check("Conservation: initial supply is 0", totalSupply == 0);

        // -- Category 3: BridgeLock Configuration --
        console.log("--- Category 3: BridgeLock Configuration ---");
        _check("BridgeLock wbait ref", address(bridgeLock.wbait()) == wbaitAddr);
        _check("BridgeLock threshold", bridgeLock.REQUIRED_CONFIRMATIONS() == EXPECTED_CONFIRMATIONS);
        _check("BridgeLock num operators", bridgeLock.NUM_OPERATORS() == EXPECTED_NUM_OPERATORS);
        _check("BridgeLock rate limit", bridgeLock.RATE_LIMIT() == EXPECTED_RATE_LIMIT);
        _check("BridgeLock timelock", bridgeLock.TIMELOCK_DURATION() == EXPECTED_TIMELOCK);
        _check("BridgeLock not paused", bridgeLock.paused() == false);

        // -- Category 4: Operator Verification --
        console.log("--- Category 4: Operator Configuration ---");
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
        _check("Operators are unique", _verifyUniqueOperators(expectedOperators));

        // -- Category 5: Access Control --
        console.log("--- Category 5: Access Control ---");
        _check("WBAIT owner is expected", wbait.owner() == expectedOwner);
        _check("BridgeLock owner is expected", bridgeLock.owner() == expectedOwner);
        _check("WBAIT bridgeLock addr", wbait.bridgeLock() == bridgeAddr);
        _check("Deployer is NOT WBAIT owner", wbait.owner() != tx.origin);
        _check("Deployer is NOT BridgeLock owner", bridgeLock.owner() != tx.origin);

        // -- Category 6: Cross-Reference Integrity --
        console.log("--- Category 6: Cross-Reference Integrity ---");
        _check("WBAIT.bridgeLock == BridgeLock addr", wbait.bridgeLock() == bridgeAddr);
        _check("BridgeLock.wbait == WBAIT addr", address(bridgeLock.wbait()) == wbaitAddr);

        // -- Summary --
        allPassed = passedChecks == totalChecks;

        console.log("");
        console.log("============================================================");
        console.log("  VERIFICATION SUMMARY");
        console.log("============================================================");
        console.log("Passed:", passedChecks);
        console.log("Total: ", totalChecks);
        if (allPassed) {
            console.log("RESULT: ALL CHECKS PASSED - Deployment verified!");
        } else {
            console.log("RESULT: SOME CHECKS FAILED - DO NOT ANNOUNCE!");
            console.log("Failed:", totalChecks - passedChecks);
        }
        console.log("============================================================");

        require(allPassed, "VERIFICATION FAILED");
    }

    // -- Internal Helpers --

    function _check(string memory label, bool condition) internal {
        totalChecks++;
        if (condition) {
            passedChecks++;
            console.log("  [PASS]", label);
        } else {
            console.log("  [FAIL]", label);
        }
    }

    function _verifyUniqueOperators(address[5] memory ops) internal pure returns (bool) {
        for (uint256 i = 0; i < 5; i++) {
            for (uint256 j = i + 1; j < 5; j++) {
                if (ops[i] == ops[j]) return false;
            }
        }
        return true;
    }
}
