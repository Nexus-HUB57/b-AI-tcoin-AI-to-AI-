// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/// @notice Legacy suite updated for Phase-2 constructors (timelock + partial burn).
contract WBAITTest is Test {
    WBAIT public wbait;
    BridgeLock public bridgeLock;
    TimelockController public timelock;
    address public owner;
    address[5] public operators;

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
        timelock = new TimelockController(1 days, proposers, executors, owner);

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

    function test_RevertMintByNonBridge() public {
        vm.expectRevert("WBAIT: caller is not BridgeLock");
        wbait.mint(owner, 1000 * 10**8);
    }

    function test_BridgeLinked() public view {
        assertEq(wbait.bridgeLock(), address(bridgeLock));
    }
}

contract BridgeLockTest is Test {
    WBAIT public wbait;
    BridgeLock public bridgeLock;
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
        bridgeLock = new BridgeLock(address(wbait), address(timelock), ops);
        wbait.initializeBridgeLock(address(bridgeLock));
    }

    function test_OperatorCount() public view {
        for (uint i = 0; i < 5; i++) {
            assertTrue(bridgeLock.isOperator(bridgeLock.operators(i)));
        }
    }

    function test_RequestLockMintNoAutoConfirm() public {
        bytes32 requestId = keccak256("test-lock-1");
        bytes32 l1TxId = keccak256("l1-tx-1");
        address recipient = address(0xB1);
        uint256 amount = 10_000 * 10**8;

        vm.prank(ops[0]);
        bridgeLock.requestLockMint(requestId, l1TxId, recipient, amount);
        assertEq(wbait.totalSupply(), 0);
    }

    function test_RevertNonOperator() public {
        bytes32 requestId = keccak256("test-lock-2");
        vm.prank(address(0x99));
        vm.expectRevert("BridgeLock: not operator");
        bridgeLock.requestLockMint(requestId, keccak256("l1"), address(0x1), 1000);
    }

    function test_ProposeOperatorUpdate() public {
        address newOp = address(0xD1);
        bridgeLock.proposeOperatorUpdate(0, newOp);
        (uint256 idx, address proposed, uint256 proposedAt, bool active) =
            bridgeLock.pendingOperatorUpdate();
        assertEq(idx, 0);
        assertEq(proposed, newOp);
        assertTrue(active);
        assertGt(proposedAt, 0);
    }

    function test_ExecuteOperatorUpdateAfterTimelock() public {
        address oldOp = bridgeLock.operators(0);
        address newOp = address(0xD1);
        bridgeLock.proposeOperatorUpdate(0, newOp);
        vm.warp(block.timestamp + 24 hours + 1);
        bridgeLock.executeOperatorUpdate();
        assertEq(bridgeLock.operators(0), newOp);
        assertTrue(bridgeLock.isOperator(newOp));
        assertFalse(bridgeLock.isOperator(oldOp));
    }

    function test_RevertExecuteBeforeTimelock() public {
        bridgeLock.proposeOperatorUpdate(0, address(0xD1));
        vm.expectRevert("BridgeLock: timelock not expired");
        bridgeLock.executeOperatorUpdate();
    }

    function test_CancelOperatorUpdate() public {
        bridgeLock.proposeOperatorUpdate(0, address(0xD1));
        bridgeLock.cancelOperatorUpdate();
        (,,, bool active) = bridgeLock.pendingOperatorUpdate();
        assertFalse(active);
    }

    function test_TimelockDurationIsUsed() public view {
        assertEq(bridgeLock.TIMELOCK_DURATION(), 24 hours);
    }

    function test_PartialBurnRelease() public {
        bytes32 requestId = keccak256("burn-setup");
        address holder = address(0xB1);
        uint256 amount = 100 * 10**8;

        vm.prank(ops[0]);
        bridgeLock.requestLockMint(requestId, keccak256("l1-burn"), holder, amount);
        vm.prank(ops[0]);
        bridgeLock.confirmLockMint(requestId);
        vm.prank(ops[1]);
        bridgeLock.confirmLockMint(requestId);
        vm.prank(ops[2]);
        bridgeLock.confirmLockMint(requestId);

        assertEq(wbait.balanceOf(holder), amount);

        vm.prank(holder);
        wbait.approve(address(bridgeLock), amount);

        vm.prank(holder);
        vm.expectRevert("BridgeLock: empty L1 address");
        bridgeLock.initiateBurnRelease(amount, "");

        vm.prank(holder);
        bridgeLock.initiateBurnRelease(40 * 10**8, "bait1releaseaddress");
        assertEq(wbait.balanceOf(holder), 60 * 10**8);
        assertEq(bridgeLock.totalMinted(), 60 * 10**8);
    }
}
