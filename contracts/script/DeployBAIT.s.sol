// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

contract DeployBAIT is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");

        // Operator keys (replace with actual operator addresses for mainnet)
        address[5] memory operators = [
            vm.envAddress("OPERATOR_1"),
            vm.envAddress("OPERATOR_2"),
            vm.envAddress("OPERATOR_3"),
            vm.envAddress("OPERATOR_4"),
            vm.envAddress("OPERATOR_5")
        ];

        vm.startBroadcast(deployerPrivateKey);

        // Step 1: Deploy WBAIT with BridgeLock address = deployer (temporary)
        // In production, use CREATE2 to pre-compute BridgeLock address
        WBAIT wbait = new WBAIT(msg.sender);
        console.log("WBAIT deployed at:", address(wbait));

        // Step 2: Deploy BridgeLock referencing WBAIT
        BridgeLock bridgeLock = new BridgeLock(address(wbait), operators);
        console.log("BridgeLock deployed at:", address(bridgeLock));

        vm.stopBroadcast();

        console.log("=== Deployment Summary ===");
        console.log("WBAIT:", address(wbait));
        console.log("BridgeLock:", address(bridgeLock));
        console.log("Operator 1:", operators[0]);
        console.log("Operator 2:", operators[1]);
        console.log("Operator 3:", operators[2]);
        console.log("Operator 4:", operators[3]);
        console.log("Operator 5:", operators[4]);
    }
}
