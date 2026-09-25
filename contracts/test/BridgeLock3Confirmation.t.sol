// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/**
 * @title BridgeLock3ConfirmationTest
 * @notice Validates the 3-of-5 multisig confirmation flow for BridgeLock.
 *
 * Test cases:
 *   1. Single request + 2 confirmations = no mint (need 3 total incl. requester)
 *   2. Single request + 2 additional confirmations = mint (3 total)
 *   3. Duplicate l1TxId rejection
 *   4. Double-confirmation rejection (same operator twice)
 *   5. Non-operator rejection
 *   6. Rate limit enforcement
 *   7. Burn-release 3-confirmation flow
 *   8. Pause blocks lock requests
 */
contract BridgeLock3ConfirmationTest is Test {
    WBAIT wbait;
    BridgeLock bridge;

    address owner;
    address[5] operators;
    address user1;
    address user2;

    function setUp() public {
        owner = address(this);
        user1 = makeAddr("user1");
        user2 = makeAddr("user2");

        for (uint256 i = 0; i < 5; i++) {
            operators[i] = makeAddr(string.concat("op", vm.toString(i)));
        }

        // Deploy WBAIT with placeholder bridge, then BridgeLock, then fix
        wbait = new WBAIT(address(1)); // placeholder
        bridge = new BridgeLock(address(wbait), operators);

        // Re-deploy WBAIT with correct bridge address
        wbait = new WBAIT(address(bridge));

        // Re-deploy BridgeLock with correct WBAIT
        bridge = new BridgeLock(address(wbait), operators);
    }

    // ── Helpers ──

    function _requestLockMint(
        bytes32 requestId,
        bytes32 l1TxId,
        address recipient,
        uint256 amount,
        uint8 operatorIndex
    ) internal {
        vm.prank(operators[operatorIndex]);
        bridge.requestLockMint(requestId, l1TxId, recipient, amount);
    }

    function _confirmLockMint(bytes32 requestId, uint8 operatorIndex) internal {
        vm.prank(operators[operatorIndex]);
        bridge.confirmLockMint(requestId);
    }

    // ── Test 1: 2 confirmations (total = requester + 1) → NOT minted ──

    function test_TwoConfirmationsDoesNotMint() public {
        bytes32 requestId = keccak256("req1");
        bytes32 l1TxId = keccak256("l1tx1");
        uint256 amount = 1000 * 10**8;

        // Operator 0 requests (auto-confirms = 1 confirmation)
        _requestLockMint(requestId, l1TxId, user1, amount, 0);

        // Operator 1 confirms (total = 2)
        _confirmLockMint(requestId, 1);

        // Should NOT be executed yet (need 3)
        BridgeLock.LockRequest memory req = bridge.lockRequests(requestId);
        assertEq(req.confirmations, 2);
        assertFalse(req.executed);
        assertEq(wbait.balanceOf(user1), 0);
    }

    // ── Test 2: 3 confirmations (requester + 2 more) → MINTED ──

    function test_ThreeConfirmationsMints() public {
        bytes32 requestId = keccak256("req2");
        bytes32 l1TxId = keccak256("l1tx2");
        uint256 amount = 1000 * 10**8;

        // Operator 0 requests (auto-confirms = 1)
        vm.prank(operators[0]);
        bridge.requestLockMint(requestId, l1TxId, user1, amount);

        // Operator 1 confirms (total = 2)
        vm.prank(operators[1]);
        bridge.confirmLockMint(requestId);

        // Operator 2 confirms (total = 3) → triggers mint
        vm.prank(operators[2]);
        bridge.confirmLockMint(requestId);

        // Verify minted
        assertEq(wbait.balanceOf(user1), amount);

        BridgeLock.LockRequest memory req = bridge.lockRequests(requestId);
        assertEq(req.confirmations, 3);
        assertTrue(req.executed);
    }

    // ── Test 3: Duplicate l1TxId rejection ──

    function test_DuplicateL1TxIdRejected() public {
        bytes32 l1TxId = keccak256("duplicate-l1");
        uint256 amount = 500 * 10**8;

        // First request succeeds
        _requestLockMint(keccak256("req3a"), l1TxId, user1, amount, 0);

        // Second request with same l1TxId fails
        vm.prank(operators[1]);
        vm.expectRevert("BridgeLock: l1TxId already processed");
        bridge.requestLockMint(keccak256("req3b"), l1TxId, user2, amount);
    }

    // ── Test 4: Same operator double-confirmation rejected ──

    function test_DoubleConfirmationRejected() public {
        bytes32 requestId = keccak256("req4");
        bytes32 l1TxId = keccak256("l1tx4");
        uint256 amount = 100 * 10**8;

        _requestLockMint(requestId, l1TxId, user1, amount, 0);

        // Same operator (0) tries to confirm again
        vm.prank(operators[0]);
        vm.expectRevert("BridgeLock: already confirmed");
        bridge.confirmLockMint(requestId);
    }

    // ── Test 5: Non-operator rejected ──

    function test_NonOperatorRejected() public {
        bytes32 requestId = keccak256("req5");
        bytes32 l1TxId = keccak256("l1tx5");
        uint256 amount = 100 * 10**8;

        vm.prank(user1);
        vm.expectRevert("BridgeLock: not operator");
        bridge.requestLockMint(requestId, l1TxId, user1, amount);
    }

    // ── Test 6: Rate limit enforcement ──

    function test_RateLimitEnforced() public {
        // Rate limit = 100,000 wBAIT/day/address
        uint256 rateLimit = 100_000 * 10**8;
        uint256 overLimit = rateLimit + 1;

        vm.prank(operators[0]);
        vm.expectRevert("BridgeLock: rate limit exceeded");
        bridge.requestLockMint(keccak256("req6"), keccak256("l1tx6"), user1, overLimit);
    }

    // ── Test 7: Burn-release 3-confirmation flow ──

    function test_BurnReleaseThreeConfirmations() public {
        // First: mint wBAIT to user1 via 3-of-5
        uint256 mintAmount = 5000 * 10**8;
        bytes32 lockReqId = keccak256("burn-lock-req");
        bytes32 l1TxId = keccak256("burn-l1tx");

        vm.prank(operators[0]);
        bridge.requestLockMint(lockReqId, l1TxId, user1, mintAmount);
        vm.prank(operators[1]);
        bridge.confirmLockMint(lockReqId);
        vm.prank(operators[2]);
        bridge.confirmLockMint(lockReqId);

        assertEq(wbait.balanceOf(user1), mintAmount);

        // User initiates burn-release
        vm.prank(user1);
        bridge.initiateBurnRelease("bait1qburnaddress...");

        // Get the releaseId from the last BurnInitiated event
        Vm.Log[] memory entries = vm.getRecordedLogs();
        bytes32 releaseId = 0;
        for (uint256 i = 0; i < entries.length; i++) {
            if (entries[i].topics[0] == keccak256("BurnInitiated(bytes32,address,uint256,string)")) {
                releaseId = entries[i].topics[1];
                break;
            }
        }
        assertTrue(releaseId != bytes32(0), "releaseId not found in events");

        // 2 confirmations (not enough)
        vm.prank(operators[0]);
        bridge.confirmBurnRelease(releaseId);
        vm.prank(operators[1]);
        bridge.confirmBurnRelease(releaseId);

        // Still not executed (need 3)
        assertFalse(bridge.burnReleases(releaseId).executed);

        // 3rd confirmation → executed
        vm.prank(operators[2]);
        bridge.confirmBurnRelease(releaseId);

        assertTrue(bridge.burnReleases(releaseId).executed);
        assertEq(wbait.balanceOf(user1), 0);
    }

    // ── Test 8: Pause blocks lock requests ──

    function test_PauseBlocksLockRequests() public {
        bridge.pause();

        vm.prank(operators[0]);
        vm.expectRevert("EnforcedPause()");
        bridge.requestLockMint(keccak256("req8"), keccak256("l1tx8"), user1, 100 * 10**8);
    }

    // ── Test 9: Exact 3-confirmation threshold (no more, no less) ──

    function test_ExactlyThreeConfirmationsThreshold() public {
        bytes32 requestId = keccak256("req-threshold");
        bytes32 l1TxId = keccak256("l1tx-threshold");
        uint256 amount = 1000 * 10**8;

        // Request with operator 0 (1 confirmation)
        vm.prank(operators[0]);
        bridge.requestLockMint(requestId, l1TxId, user1, amount);

        // 1st additional confirmation (total = 2) → not yet
        vm.prank(operators[1]);
        bridge.confirmLockMint(requestId);
        assertFalse(bridge.lockRequests(requestId).executed);
        assertEq(wbait.balanceOf(user1), 0);

        // 2nd additional confirmation (total = 3) → minted!
        vm.prank(operators[2]);
        bridge.confirmLockMint(requestId);
        assertTrue(bridge.lockRequests(requestId).executed);
        assertEq(wbait.balanceOf(user1), amount);
    }

    // ── Test 10: Already executed request cannot be re-confirmed ──

    function test_CannotConfirmExecutedRequest() public {
        bytes32 requestId = keccak256("req-exec");
        bytes32 l1TxId = keccak256("l1tx-exec");
        uint256 amount = 1000 * 10**8;

        // Get to 3 confirmations → executed
        vm.prank(operators[0]);
        bridge.requestLockMint(requestId, l1TxId, user1, amount);
        vm.prank(operators[1]);
        bridge.confirmLockMint(requestId);
        vm.prank(operators[2]);
        bridge.confirmLockMint(requestId);

        // Operator 3 tries to confirm an already-executed request
        vm.prank(operators[3]);
        vm.expectRevert("BridgeLock: already executed");
        bridge.confirmLockMint(requestId);
    }
}
