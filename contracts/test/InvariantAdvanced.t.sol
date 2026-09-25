// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "forge-std/console2.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";
import "./HandlerAdvanced.sol";

/**
 * @title InvariantAdvancedTest
 * @notice Advanced stateful invariants with multi-actor handler, time warps,
 *         rate-limit edges and unauthorized-path probes.
 */
contract InvariantAdvancedTest is Test {
    WBAIT public wbait;
    BridgeLock public bridge;
    TimelockController public timelock;
    HandlerAdvanced public handler;
    address[5] public ops;

    function setUp() public {
        ops[0] = makeAddr("op0");
        ops[1] = makeAddr("op1");
        ops[2] = makeAddr("op2");
        ops[3] = makeAddr("op3");
        ops[4] = makeAddr("op4");

        address[] memory proposers = new address[](1);
        proposers[0] = address(this);
        address[] memory executors = new address[](1);
        executors[0] = address(this);

        timelock = new TimelockController(1 days, proposers, executors, address(this));
        wbait = new WBAIT(address(0), address(timelock));
        bridge = new BridgeLock(address(wbait), address(timelock), ops);
        wbait.initializeBridgeLock(address(bridge));

        handler = new HandlerAdvanced(wbait, bridge, ops);

        targetContract(address(handler));

        bytes4[] memory sels = new bytes4[](6);
        sels[0] = HandlerAdvanced.requestLock.selector;
        sels[1] = HandlerAdvanced.confirmLock.selector;
        sels[2] = HandlerAdvanced.burnPartial.selector;
        sels[3] = HandlerAdvanced.warpTime.selector;
        sels[4] = HandlerAdvanced.unauthorizedRequest.selector;
        sels[5] = HandlerAdvanced.unauthorizedMint.selector;
        targetSelector(FuzzSelector({addr: address(handler), selectors: sels}));
    }

    function invariant_MintedLeLocked() public view {
        assertLe(bridge.totalMinted(), bridge.totalLockedOnL1());
    }

    function invariant_SupplyEqMinted() public view {
        assertEq(wbait.totalSupply(), bridge.totalMinted());
    }

    function invariant_UnderCap() public view {
        assertLe(wbait.totalSupply(), wbait.MAX_SUPPLY());
    }

    function invariant_GhostAccounting() public view {
        assertLe(handler.ghostBurned(), handler.ghostMinted() + bridge.totalMinted());
    }

    function invariant_OperatorsIntact() public view {
        for (uint256 i = 0; i < 5; i++) {
            assertTrue(bridge.isOperator(ops[i]));
        }
    }

    function invariant_BridgeLinked() public view {
        assertEq(address(wbait.bridgeLock()), address(bridge));
    }

    function invariant_Summary() public view {
        assertTrue(true);
        console2.log("--- advanced campaign ---");
        console2.log("requests   ", handler.ghostRequests());
        console2.log("confirms   ", handler.ghostConfirms());
        console2.log("executions ", handler.ghostExecutions());
        console2.log("burned     ", handler.ghostBurned());
        console2.log("rateHits   ", handler.ghostRateLimitHits());
        console2.log("dblConfHits", handler.ghostDoubleConfirmHits());
        console2.log("warps      ", handler.ghostWarps());
        console2.log("totalMinted", bridge.totalMinted());
        console2.log("totalLocked", bridge.totalLockedOnL1());
        console2.log("supply     ", wbait.totalSupply());
    }
}
