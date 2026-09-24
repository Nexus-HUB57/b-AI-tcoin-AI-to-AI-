// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/// @notice Phase-2 compatible tests (WBAIT + BridgeLock with TimelockController)
contract BAITPhase2Test is Test {
    WBAIT public wbait;
    BridgeLock public bridgeLock;
    TimelockController public timelock;
    address public owner;
    address[5] public operators;

    uint256 constant MIN_DELAY = 1 days;

    function setUp() public {
        owner = address(this);
        operators[0] = address(0xA1);
        operators[1] = address(0xA2);
        operators[2] = address(0xA3);
        operators[3] = address(0xA4);
        operators[4] = address(0xA5);

        address[] memory proposers = new address[](1);
        proposers[0] = owner;
        address[] memory executors = new address[](1);
        executors[0] = owner;

        timelock = new TimelockController(MIN_DELAY, proposers, executors, owner);

        // Deploy WBAIT with placeholder bridge, then link
        wbait = new WBAIT(address(0), address(timelock));
        bridgeLock = new BridgeLock(address(wbait), address(timelock), operators);
        wbait.initializeBridgeLock(address(bridgeLock));
    }

    function test_Name() public view {
        assertEq(wbait.name(), "Wrapped bAIitcoin");
    }

    function test_Symbol() public view {
        assertEq(wbait.symbol(), "wBAIT");
    }

    function test_Decimals() public view {
        assertEq(wbait.decimals(), 8);
    }

    function test_MaxSupply() public view {
        assertEq(wbait.MAX_SUPPLY(), 21_000_000 * 10**8);
    }

    function test_InitialSupplyZero() public view {
        assertEq(wbait.totalSupply(), 0);
    }

    function test_BridgeLockLinked() public view {
        assertEq(wbait.bridgeLock(), address(bridgeLock));
    }

    function test_RevertMintByNonBridge() public {
        vm.expectRevert("WBAIT: caller is not BridgeLock");
        wbait.mint(owner, 1000 * 10**8);
    }

    function test_RevertDoubleInitBridgeLock() public {
        vm.expectRevert("WBAIT: bridgeLock already initialized");
        wbait.initializeBridgeLock(address(0xBEEF));
    }

    function test_OperatorsConfigured() public view {
        // BridgeLock exposes isOperator mapping
        assertTrue(bridgeLock.isOperator(operators[0]));
        assertTrue(bridgeLock.isOperator(operators[2]));
        assertFalse(bridgeLock.isOperator(address(0xDEAD)));
    }

    function test_TimelockSet() public view {
        assertEq(address(wbait.timelock()), address(timelock));
        assertEq(address(bridgeLock.timelock()), address(timelock));
    }
}
