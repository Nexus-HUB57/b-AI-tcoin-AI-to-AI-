// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "forge-std/console2.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/**
 * @title DeployBAITLocal
 * @notice Anvil / local deploy for integration tests (no Safe, no env operators).
 *
 *   anvil &
 *   forge script script/DeployBAITLocal.s.sol --rpc-url http://127.0.0.1:8545 --broadcast
 */
contract DeployBAITLocal is Script {
    function run() external {
        uint256 pk = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80; // anvil[0]
        address deployer = vm.addr(pk);

        address[5] memory operators;
        operators[0] = vm.addr(uint256(keccak256("op0")));
        operators[1] = vm.addr(uint256(keccak256("op1")));
        operators[2] = vm.addr(uint256(keccak256("op2")));
        operators[3] = vm.addr(uint256(keccak256("op3")));
        operators[4] = vm.addr(uint256(keccak256("op4")));

        address[] memory proposers = new address[](1);
        proposers[0] = deployer;
        address[] memory executors = new address[](1);
        executors[0] = deployer;

        vm.startBroadcast(pk);

        TimelockController timelock = new TimelockController(1 hours, proposers, executors, deployer);
        WBAIT wbait = new WBAIT(address(0), address(timelock));
        BridgeLock bridge = new BridgeLock(address(wbait), address(timelock), operators);
        wbait.initializeBridgeLock(address(bridge));

        vm.stopBroadcast();

        console2.log("Timelock", address(timelock));
        console2.log("WBAIT   ", address(wbait));
        console2.log("Bridge  ", address(bridge));
        console2.log("OP0     ", operators[0]);
        console2.log("OP1     ", operators[1]);
        console2.log("OP2     ", operators[2]);
    }
}
