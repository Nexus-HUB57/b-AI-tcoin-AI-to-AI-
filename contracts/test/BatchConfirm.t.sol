// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

contract BatchConfirmTest is Test {
    WBAIT public wbait;
    BridgeLock public bridge;
    address[5] public ops;

    function setUp() public {
        ops[0] = address(0xA1);
        ops[1] = address(0xA2);
        ops[2] = address(0xA3);
        ops[3] = address(0xA4);
        ops[4] = address(0xA5);
        wbait = new WBAIT();
        bridge = new BridgeLock(address(wbait), ops);
        wbait.setBridgeLock(address(bridge));
    }

    function test_BatchConfirmMintsWhenThirdOps() public {
        address r0 = address(0xB1);
        address r1 = address(0xB2);
        uint256 amt = 1_000 * 10**8;
        bytes32 id0 = keccak256("b0");
        bytes32 id1 = keccak256("b1");

        vm.startPrank(ops[0]);
        bridge.requestLockMint(id0, keccak256("l0"), r0, amt);
        bridge.requestLockMint(id1, keccak256("l1"), r1, amt);
        vm.stopPrank();

        bytes32[] memory ids = new bytes32[](2);
        ids[0] = id0;
        ids[1] = id1;

        vm.prank(ops[0]);
        bridge.confirmLockMintBatch(ids);
        vm.prank(ops[1]);
        bridge.confirmLockMintBatch(ids);

        assertEq(wbait.balanceOf(r0), 0);

        vm.prank(ops[2]);
        bridge.confirmLockMintBatch(ids);

        assertEq(wbait.balanceOf(r0), amt);
        assertEq(wbait.balanceOf(r1), amt);
        assertEq(bridge.totalMinted(), amt * 2);
    }

    function test_BatchEmptyReverts() public {
        bytes32[] memory ids = new bytes32[](0);
        vm.prank(ops[0]);
        vm.expectRevert("BridgeLock: bad batch size");
        bridge.confirmLockMintBatch(ids);
    }

    function test_BatchTooLargeReverts() public {
        bytes32[] memory ids = new bytes32[](51);
        vm.prank(ops[0]);
        vm.expectRevert("BridgeLock: bad batch size");
        bridge.confirmLockMintBatch(ids);
    }

    function test_BatchInvalidIdRevertsAll() public {
        bytes32 id0 = keccak256("ok");
        vm.prank(ops[0]);
        bridge.requestLockMint(id0, keccak256("l"), address(0xB1), 1e8);

        bytes32[] memory ids = new bytes32[](2);
        ids[0] = id0;
        ids[1] = keccak256("missing");

        vm.prank(ops[0]);
        vm.expectRevert("BridgeLock: not requested");
        bridge.confirmLockMintBatch(ids);
    }
}
