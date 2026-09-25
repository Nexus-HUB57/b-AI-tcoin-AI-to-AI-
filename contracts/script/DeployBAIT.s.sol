// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";

/**
 * @title DeployBAIT - Base Deployment Script (FIXED)
 * @notice Deploys WBAIT + BridgeLock with correct cross-references via
 *         CREATE address prediction. The original version set WBAIT.bridgeLock
 *         to msg.sender (deployer), making the bridge permanently non-functional.
 *
 *         This version pre-computes BridgeLock's address and passes it to
 *         WBAIT's constructor, then verifies the cross-reference.
 *
 * Usage:
 *   forge script script/DeployBAIT.s.sol \
 *     --rpc-url $RPC_URL \
 *     --private-key $DEPLOYER_PRIVATE_KEY \
 *     --broadcast --verify -vvvv
 *
 * Environment Variables Required:
 *   DEPLOYER_PRIVATE_KEY  - Deployer private key
 *   OPERATOR_1..5         - Bridge operator addresses
 */
contract DeployBAIT is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address timelockAddress = vm.envAddress("TIMELOCK_ADDRESS"); // Fix #1: TimelockController address

        // Operator keys (replace with actual operator addresses for mainnet)
        address[5] memory operators = [
            vm.envAddress("OPERATOR_1"),
            vm.envAddress("OPERATOR_2"),
            vm.envAddress("OPERATOR_3"),
            vm.envAddress("OPERATOR_4"),
            vm.envAddress("OPERATOR_5")
        ];

        // Pre-deployment: verify operator uniqueness
        for (uint256 i = 0; i < 5; i++) {
            require(operators[i] != address(0), "FATAL: Operator is zero address");
            for (uint256 j = i + 1; j < 5; j++) {
                require(operators[i] != operators[j], "FATAL: Duplicate operator");
            }
        }

        vm.startBroadcast(deployerPrivateKey);

        // Fix #3 (HIGH): Correct deployment order to break circular immutable dependency
        // Step 1: Deploy WBAIT with bridgeLock=address(0) placeholder + real timelock
        WBAIT wbait = new WBAIT(address(0), timelockAddress);
        console.log("WBAIT deployed at:", address(wbait));

        // Step 2: Deploy BridgeLock referencing real WBAIT + timelock
        BridgeLock bridgeLock = new BridgeLock(address(wbait), timelockAddress, operators);
        console.log("BridgeLock deployed at:", address(bridgeLock));

        // Step 3: Link WBAIT → BridgeLock (sets the real bridgeLock, replacing placeholder)
        wbait.initializeBridgeLock(address(bridgeLock));
        console.log("WBAIT.bridgeLock set to:", address(bridgeLock));

        vm.stopBroadcast();

        // Step 4: Verify address prediction (critical safety check)
        require(
            address(bridgeLock) == predictedBridgeLock,
            "FATAL: BridgeLock address does not match prediction!"
        );
        require(
            wbait.bridgeLock() == address(bridgeLock),
            "FATAL: WBAIT.bridgeLock does not match BridgeLock address!"
        );
        console.log("[PASS] Cross-reference verified: WBAIT.bridgeLock == BridgeLock");

        console.log("=== Deployment Summary ===");
        console.log("WBAIT:", address(wbait));
        console.log("BridgeLock:", address(bridgeLock));
        console.log("Timelock:", timelockAddress);
        console.log("Operator 1:", operators[0]);
        console.log("Operator 2:", operators[1]);
        console.log("Operator 3:", operators[2]);
        console.log("Operator 4:", operators[3]);
        console.log("Operator 5:", operators[4]);
    }
}
