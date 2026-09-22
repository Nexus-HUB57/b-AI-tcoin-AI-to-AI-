// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/**
 * @title SetupTimelock
 * @notice Deploys TimelockController (48h) and transfers ownership of WBAIT + BridgeLock.
 */
contract SetupTimelock is Script {
    uint256 public constant MIN_DELAY = 48 hours;

    function run() external {
        uint256 pk = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address wbaitAddr = vm.envAddress("WBAIT_ADDRESS");
        address bridgeAddr = vm.envAddress("BRIDGELOCK_ADDRESS");

        address multisig = vm.envOr("MULTISIG_ADDRESS", address(0));
        address[] memory proposers = new address[](1);
        address[] memory executors = new address[](1);

        if (multisig != address(0)) {
            proposers[0] = multisig;
            executors[0] = multisig;
        } else {
            proposers[0] = vm.addr(pk);
            executors[0] = vm.addr(pk);
            console.log("WARNING: using deployer as proposer/executor — replace with multisig before mainnet");
        }

        vm.startBroadcast(pk);

        TimelockController timelock = new TimelockController(
            MIN_DELAY,
            proposers,
            executors,
            address(0)
        );
        console.log("TimelockController deployed at:", address(timelock));

        WBAIT wbait = WBAIT(wbaitAddr);
        BridgeLock bridge = BridgeLock(bridgeAddr);

        wbait.transferOwnership(address(timelock));
        bridge.transferOwnership(address(timelock));
        console.log("transferOwnership proposed for WBAIT and BridgeLock");
        console.log("Schedule acceptOwnership() on Timelock after minDelay");

        vm.stopBroadcast();

        console.log("=== SetupTimelock Summary ===");
        console.log("Timelock:", address(timelock));
    }
}
