// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/// @notice Invariant + lifecycle tests for Phase-2 BridgeLock (H-02 no auto-confirm, partial burn)
contract BridgeInvariantTest is Test {
    WBAIT public wbait;
    BridgeLock public bridgeLock;
    TimelockController public timelock;
    address public owner;
    address[5] public ops;
    uint256 constant MIN_DELAY = 1 days;
    uint256 constant ONE = 10**8;

    function setUp() public {
        owner = address(this);
        ops[0] = makeAddr("op0");
        ops[1] = makeAddr("op1");
        ops[2] = makeAddr("op2");
        ops[3] = makeAddr("op3");
        ops[4] = makeAddr("op4");
        address[] memory proposers = new address[](1);
        proposers[0] = owner;
        address[] memory executors = new address[](1);
        executors[0] = owner;
        timelock = new TimelockController(MIN_DELAY, proposers, executors, owner);
        wbait = new WBAIT(address(0), address(timelock));
        bridgeLock = new BridgeLock(address(wbait), address(timelock), ops);
        wbait.initializeBridgeLock(address(bridgeLock));
    }

    function _request(bytes32 id, address recipient, uint256 amount) internal {
        vm.prank(ops[0]);
        bridgeLock.requestLockMint(id, keccak256("l1tx"), recipient, amount);
    }

    function _confirm(bytes32 id, address op) internal {
        vm.prank(op);
        bridgeLock.confirmLockMint(id);
    }

    function _mintWith3(bytes32 id, address recipient, uint256 amount) internal {
        _request(id, recipient, amount);
        _confirm(id, ops[0]);
        _confirm(id, ops[1]);
        _confirm(id, ops[2]);
    }

    function test_H02_RequestDoesNotAutoConfirm() public {
        bytes32 id = keccak256("req1");
        _request(id, address(0xBEEF), 100 * ONE);
        (,, uint256 amount, uint256 confs,, bool executed) = _lockView(id);
        assertEq(amount, 100 * ONE);
        assertEq(confs, 0);
        assertFalse(executed);
        assertEq(wbait.totalSupply(), 0);
    }

    function test_H02_NeedsThreeExplicitConfirms() public {
        bytes32 id = keccak256("req2");
        address recipient = makeAddr("alice");
        uint256 amount = 50 * ONE;
        _request(id, recipient, amount);
        _confirm(id, ops[0]);
        _confirm(id, ops[1]);
        assertEq(wbait.totalSupply(), 0);
        _confirm(id, ops[2]);
        assertEq(wbait.totalSupply(), amount);
        assertEq(wbait.balanceOf(recipient), amount);
        assertEq(bridgeLock.totalMinted(), amount);
        assertEq(bridgeLock.totalLockedOnL1(), amount);
    }

    function test_H02_RequesterMustAlsoConfirm() public {
        bytes32 id = keccak256("req3");
        address recipient = makeAddr("bob");
        uint256 amount = 10 * ONE;
        _request(id, recipient, amount);
        _confirm(id, ops[1]);
        _confirm(id, ops[2]);
        _confirm(id, ops[3]);
        assertEq(wbait.totalSupply(), amount);
    }

    function test_RevertDoubleConfirm() public {
        bytes32 id = keccak256("req4");
        _request(id, makeAddr("c"), 1 * ONE);
        _confirm(id, ops[0]);
        vm.prank(ops[0]);
        vm.expectRevert("BridgeLock: already confirmed");
        bridgeLock.confirmLockMint(id);
    }

    function test_RevertConfirmBeforeRequest() public {
        bytes32 id = keccak256("ghost");
        vm.prank(ops[0]);
        vm.expectRevert("BridgeLock: not requested");
        bridgeLock.confirmLockMint(id);
    }

    function test_Invariant_MintNeverExceedsLocked() public {
        bytes32 id = keccak256("inv1");
        uint256 amount = 1000 * ONE;
        _mintWith3(id, makeAddr("user"), amount);
        assertLe(bridgeLock.totalMinted(), bridgeLock.totalLockedOnL1());
        assertEq(bridgeLock.totalMinted(), wbait.totalSupply());
    }

    function test_Invariant_HoldsAfterPartialBurn() public {
        bytes32 id = keccak256("inv2");
        address user = makeAddr("burner");
        uint256 amount = 100 * ONE;
        _mintWith3(id, user, amount);
        vm.prank(user);
        wbait.approve(address(bridgeLock), amount);
        vm.prank(user);
        bridgeLock.initiateBurnRelease(40 * ONE, "b'aliceL1address");
        assertEq(wbait.totalSupply(), 60 * ONE);
        assertEq(bridgeLock.totalMinted(), 60 * ONE);
        assertLe(bridgeLock.totalMinted(), bridgeLock.totalLockedOnL1());
    }

    function test_PartialBurn_LeavesRemainder() public {
        bytes32 id = keccak256("burn1");
        address user = makeAddr("u1");
        _mintWith3(id, user, 100 * ONE);
        vm.prank(user);
        wbait.approve(address(bridgeLock), type(uint256).max);
        vm.prank(user);
        bridgeLock.initiateBurnRelease(25 * ONE, "b'release1");
        assertEq(wbait.balanceOf(user), 75 * ONE);
        vm.prank(user);
        bridgeLock.initiateBurnRelease(75 * ONE, "b'release2");
        assertEq(wbait.balanceOf(user), 0);
        assertEq(wbait.totalSupply(), 0);
        assertEq(bridgeLock.totalMinted(), 0);
    }

    function test_RevertBurnZero() public {
        bytes32 id = keccak256("burn0");
        address user = makeAddr("u0");
        _mintWith3(id, user, 10 * ONE);
        vm.prank(user);
        wbait.approve(address(bridgeLock), 10 * ONE);
        vm.prank(user);
        vm.expectRevert("BridgeLock: zero amount");
        bridgeLock.initiateBurnRelease(0, "b'x");
    }

    function test_RevertBurnInsufficient() public {
        bytes32 id = keccak256("burnIns");
        address user = makeAddr("uIns");
        _mintWith3(id, user, 10 * ONE);
        vm.prank(user);
        wbait.approve(address(bridgeLock), 100 * ONE);
        vm.prank(user);
        vm.expectRevert("BridgeLock: insufficient wBAIT");
        bridgeLock.initiateBurnRelease(50 * ONE, "b'x");
    }

    function test_RevertMintExceedsCap() public {
        bytes32 id = keccak256("cap");
        vm.prank(ops[0]);
        vm.expectRevert("BridgeLock: rate limit exceeded");
        bridgeLock.requestLockMint(id, keccak256("l1"), makeAddr("whale"), 200_000 * ONE);
    }

    function test_RateLimit_ResetsNextDay() public {
        address recipient = makeAddr("r");
        bytes32 id1 = keccak256("d1");
        _mintWith3(id1, recipient, 100_000 * ONE);
        bytes32 id2 = keccak256("d2");
        vm.prank(ops[0]);
        vm.expectRevert("BridgeLock: rate limit exceeded");
        bridgeLock.requestLockMint(id2, keccak256("l1b"), recipient, 1);
        vm.warp(block.timestamp + 1 days + 1);
        _mintWith3(id2, recipient, 50_000 * ONE);
        assertEq(wbait.balanceOf(recipient), 150_000 * ONE);
    }

    function test_OnlyBridgeCanMint() public {
        vm.expectRevert("WBAIT: caller is not BridgeLock");
        wbait.mint(address(this), 1 * ONE);
    }

    function test_MaxSupplyConstant() public view {
        assertEq(wbait.MAX_SUPPLY(), 21_000_000 * ONE);
    }

    function _lockView(bytes32 id)
        internal
        view
        returns (bytes32 l1TxId, address recipient, uint256 amount, uint256 confirmations, bool, bool executed)
    {
        (l1TxId, recipient, amount, confirmations, executed) = bridgeLock.lockRequests(id);
        return (l1TxId, recipient, amount, confirmations, false, executed);
    }
}
