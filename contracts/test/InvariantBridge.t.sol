// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "forge-std/console2.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";
import "./Handler.sol";

/**
 * @title InvariantBridgeTest
 * @notice Stateful invariant suite (Foundry invariant fuzzer).
 */
contract InvariantBridgeTest is Test {
    WBAIT public wbait;
    BridgeLock public bridge;
    TimelockController public timelock;
    Handler public handler;
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

        handler = new Handler(wbait, bridge, ops);
        targetContract(address(handler));

        bytes4[] memory selectors = new bytes4[](3);
        selectors[0] = Handler.requestLock.selector;
        selectors[1] = Handler.confirmLock.selector;
        selectors[2] = Handler.burnPartial.selector;
        targetSelector(FuzzSelector({addr: address(handler), selectors: selectors}));
    }

    function invariant_MintedLeLocked() public view {
        assertLe(bridge.totalMinted(), bridge.totalLockedOnL1(), "INV: totalMinted > totalLockedOnL1");
    }

    function invariant_SupplyEqMinted() public view {
        assertEq(wbait.totalSupply(), bridge.totalMinted(), "INV: totalSupply != totalMinted");
    }

    function invariant_UnderCap() public view {
        assertLe(wbait.totalSupply(), wbait.MAX_SUPPLY(), "INV: over max supply");
    }

    function invariant_Decimals() public view {
        assertEq(wbait.decimals(), 8);
    }

    function invariant_BridgeLinked() public view {
        assertEq(address(wbait.bridgeLock()), address(bridge));
    }

    function invariant_OperatorsStable() public view {
        for (uint256 i = 0; i < 5; i++) {
            assertTrue(bridge.isOperator(ops[i]), "INV: operator lost");
        }
    }

    function invariant_CallSummary() public view {
        assertTrue(true);
        console2.log("ghostRequests   ", handler.ghostRequests());
        console2.log("ghostConfirms   ", handler.ghostConfirms());
        console2.log("ghostExecutions ", handler.ghostExecutions());
        console2.log("ghostBurned     ", handler.ghostBurnedCumulative());
        console2.log("totalMinted     ", bridge.totalMinted());
        console2.log("totalLockedOnL1 ", bridge.totalLockedOnL1());
        console2.log("totalSupply     ", wbait.totalSupply());
    }
}
