// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";

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
