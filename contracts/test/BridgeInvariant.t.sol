// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

contract BridgeInvariantTest is Test {
    WBAIT public wbait;
    BridgeLock public bridge;

    address public op1 = address(0x1001);
    address public op2 = address(0x1002);
    address public op3 = address(0x1003);
    address public op4 = address(0x1004);
    address public op5 = address(0x1005);
    address public user = address(0xBEEF);

    function setUp() public {
        wbait = new WBAIT();
        address[5] memory ops = [op1, op2, op3, op4, op5];
        bridge = new BridgeLock(address(wbait), ops);
        wbait.setBridgeLock(address(bridge));
    }

    function test_DeployWiring() public view {
        assertEq(wbait.bridgeLock(), address(bridge));
        assertEq(address(bridge.wbait()), address(wbait));
    }

    function test_OnlyBridgeCanMint() public {
        bytes32 reqId = keccak256("lock1");
        bytes32 l1Tx = keccak256("l1tx1");

        vm.prank(op1);
        bridge.requestLockMint(reqId, l1Tx, user, 1000e8);

        vm.prank(op1);
        bridge.confirmLockMint(reqId);
        vm.prank(op2);
        bridge.confirmLockMint(reqId);
        vm.prank(op3);
        bridge.confirmLockMint(reqId);

        assertEq(wbait.balanceOf(user), 1000e8);
        assertEq(bridge.totalMinted(), 1000e8);
        assertEq(bridge.totalLocked(), 1000e8);
        assertTrue(bridge.conservationHolds());
    }

    function test_NoAutoConfirm() public {
        bytes32 reqId = keccak256("lock2");
        vm.prank(op1);
        bridge.requestLockMint(reqId, keccak256("l1"), user, 100e8);

        assertEq(bridge.totalMinted(), 0);
        assertEq(bridge.totalLocked(), 100e8);
        assertTrue(bridge.conservationHolds());
    }

    function test_DeployerCannotMintDirectly() public {
        vm.expectRevert("WBAIT: caller is not BridgeLock");
        wbait.mint(user, 1e8);
    }

    function test_SetBridgeLockOnlyOnce() public {
        vm.expectRevert("WBAIT: bridge already set");
        wbait.setBridgeLock(address(0xDEAD));
    }

    function test_RateLimit() public {
        uint256 limit = bridge.RATE_LIMIT();
        bytes32 reqId = keccak256("rate");
        vm.prank(op1);
        vm.expectRevert("BridgeLock: rate limit exceeded");
        bridge.requestLockMint(reqId, keccak256("l1"), user, limit + 1);
    }
}
