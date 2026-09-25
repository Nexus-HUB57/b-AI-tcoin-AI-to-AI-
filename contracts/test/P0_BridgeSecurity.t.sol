// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/// @notice Hard regression tests for P0: no auto-confirm, 3 explicit confirms, conservation on burn.
contract P0BridgeSecurityTest is Test {
    WBAIT public wbait;
    BridgeLock public bridge;
    TimelockController public timelock;
    address[5] public ops;

    function setUp() public {
        ops[0] = address(0xA1);
        ops[1] = address(0xA2);
        ops[2] = address(0xA3);
        ops[3] = address(0xA4);
        ops[4] = address(0xA5);

        address[] memory proposers = new address[](1);
        proposers[0] = address(this);
        address[] memory executors = new address[](1);
        executors[0] = address(this);
        timelock = new TimelockController(1 days, proposers, executors, address(this));

        wbait = new WBAIT(address(0), address(timelock));
        bridge = new BridgeLock(address(wbait), address(timelock), ops);
        wbait.initializeBridgeLock(address(bridge));
    }

    function _fullMint(bytes32 requestId, bytes32 l1TxId, address recipient, uint256 amount) internal {
        vm.prank(ops[0]);
        bridge.requestLockMint(requestId, l1TxId, recipient, amount);
        vm.prank(ops[0]);
        bridge.confirmLockMint(requestId);
        vm.prank(ops[1]);
        bridge.confirmLockMint(requestId);
        vm.prank(ops[2]);
        bridge.confirmLockMint(requestId);
    }

    function test_P0_RequestDoesNotAutoConfirm() public {
        bytes32 id = keccak256("p0-no-auto");
        address recipient = address(0xB1);
        uint256 amount = 1_000 * 10**8;

        vm.prank(ops[0]);
        bridge.requestLockMint(id, keccak256("l1"), recipient, amount);

        (,, uint256 amt, uint256 confs,,) = _lockMeta(id);
        // amount stored, confirmations must be 0
        assertEq(amt, amount);
        assertEq(confs, 0);
        assertEq(bridge.totalMinted(), 0);
        assertEq(wbait.balanceOf(recipient), 0);
        assertEq(bridge.totalLockedOnL1(), amount);
    }

    function test_P0_TwoConfirmsDoNotMint() public {
        bytes32 id = keccak256("p0-two");
        address recipient = address(0xB1);
        uint256 amount = 5_000 * 10**8;

        vm.prank(ops[0]);
        bridge.requestLockMint(id, keccak256("l1-2"), recipient, amount);
        vm.prank(ops[0]);
        bridge.confirmLockMint(id);
        vm.prank(ops[1]);
        bridge.confirmLockMint(id);

        assertEq(wbait.balanceOf(recipient), 0);
        assertEq(bridge.totalMinted(), 0);
    }

    function test_P0_ThreeExplicitConfirmsMint() public {
        bytes32 id = keccak256("p0-three");
        address recipient = address(0xB1);
        uint256 amount = 5_000 * 10**8;

        _fullMint(id, keccak256("l1-3"), recipient, amount);

        assertEq(wbait.balanceOf(recipient), amount);
        assertEq(bridge.totalMinted(), amount);
        assertTrue(bridge.conservationHolds());
    }

    function test_P0_RequesterMustConfirmExplicitly() public {
        // Even the operator who requested must call confirm — counts toward 3
        bytes32 id = keccak256("p0-req-confirm");
        address recipient = address(0xB2);
        uint256 amount = 100 * 10**8;

        vm.prank(ops[0]);
        bridge.requestLockMint(id, keccak256("l1-r"), recipient, amount);

        // Only ops 1 and 2 confirm — not enough without ops[0]
        vm.prank(ops[1]);
        bridge.confirmLockMint(id);
        vm.prank(ops[2]);
        bridge.confirmLockMint(id);
        assertEq(wbait.balanceOf(recipient), 0);

        vm.prank(ops[0]);
        bridge.confirmLockMint(id);
        assertEq(wbait.balanceOf(recipient), amount);
    }

    function test_P0_BurnDecrementsTotalMinted() public {
        bytes32 id = keccak256("p0-burn-m");
        address holder = address(0xB1);
        uint256 amount = 100 * 10**8;

        _fullMint(id, keccak256("l1-bm"), holder, amount);

        vm.prank(holder);
        wbait.approve(address(bridge), amount);
        vm.prank(holder);
        bridge.initiateBurnRelease(40 * 10**8, "bait1addr");

        assertEq(bridge.totalMinted(), 60 * 10**8);
        assertEq(wbait.balanceOf(holder), 60 * 10**8);
        // locked still full until burn confirmed
        assertEq(bridge.totalLockedOnL1(), amount);
        assertTrue(bridge.conservationHolds());
    }

    function test_P0_BurnExecuteDecrementsTotalLockedOnL1() public {
        bytes32 id = keccak256("p0-burn-l");
        address holder = address(0xB1);
        uint256 amount = 100 * 10**8;

        _fullMint(id, keccak256("l1-bl"), holder, amount);

        vm.prank(holder);
        wbait.approve(address(bridge), amount);
        vm.prank(holder);
        bridge.initiateBurnRelease(amount, "bait1full");

        bytes32 releaseId = keccak256(
            abi.encodePacked(holder, amount, block.number, uint256(0))
        );

        vm.prank(ops[0]);
        bridge.confirmBurnRelease(releaseId);
        vm.prank(ops[1]);
        bridge.confirmBurnRelease(releaseId);
        assertEq(bridge.totalLockedOnL1(), amount); // not yet

        vm.prank(ops[2]);
        bridge.confirmBurnRelease(releaseId);

        assertEq(bridge.totalLockedOnL1(), 0);
        assertEq(bridge.totalMinted(), 0);
        assertTrue(bridge.conservationHolds());
    }

    // Helper: read lock request public fields (amount at slot via getter mapping)
    function _lockMeta(bytes32 requestId)
        internal
        view
        returns (bytes32 l1TxId, address recipient, uint256 amount, uint256 confirmations, bool executed, bool existsHint)
    {
        (l1TxId, recipient, amount, confirmations, executed) = bridge.lockRequests(requestId);
        existsHint = amount > 0 || executed;
    }
}
