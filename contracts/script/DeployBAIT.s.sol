// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/**
 * @title DeployBAIT (remediated)
 * @notice Correct deploy order:
 *   1. Deploy WBAIT (no bridge address yet)
 *   2. Deploy BridgeLock(wbait, operators)
 *   3. wbait.setBridgeLock(bridgeLock)
 *   4. (Optional) transfer ownership to Timelock
 */
contract DeployBAIT is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");

        address[5] memory operators = [
            vm.envAddress("OPERATOR_1"),
            vm.envAddress("OPERATOR_2"),
            vm.envAddress("OPERATOR_3"),
            vm.envAddress("OPERATOR_4"),
            vm.envAddress("OPERATOR_5")
        ];

        vm.startBroadcast(deployerPrivateKey);

        WBAIT wbait = new WBAIT();
        console.log("WBAIT deployed at:", address(wbait));

        BridgeLock bridgeLock = new BridgeLock(address(wbait), operators);
        console.log("BridgeLock deployed at:", address(bridgeLock));

        wbait.setBridgeLock(address(bridgeLock));
        console.log("WBAIT.bridgeLock set to:", wbait.bridgeLock());

        require(wbait.bridgeLock() == address(bridgeLock), "Deploy: bridge mismatch");
        require(address(bridgeLock.wbait()) == address(wbait), "Deploy: wbait mismatch");

        vm.stopBroadcast();

        console.log("=== Deployment Summary ===");
        console.log("WBAIT:", address(wbait));
        console.log("BridgeLock:", address(bridgeLock));
        console.log("Operator 1:", operators[0]);
        console.log("Operator 2:", operators[1]);
        console.log("Operator 3:", operators[2]);
        console.log("Operator 4:", operators[3]);
        console.log("Operator 5:", operators[4]);
        console.log("Next: run SetupTimelock.s.sol to transfer ownership");
    }
}
