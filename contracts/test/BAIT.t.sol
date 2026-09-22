// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

contract WBAITTest is Test {
    WBAIT public wbait;
    BridgeLock public bridgeLock;
    address public owner;
    address[5] public operators;

    function setUp() public {
        owner = address(this);
        operators[0] = address(0xA1);
        operators[1] = address(0xA2);
        operators[2] = address(0xA3);
        operators[3] = address(0xA4);
        operators[4] = address(0xA5);
        wbait = new WBAIT();
        bridgeLock = new BridgeLock(address(wbait), operators);
        wbait.setBridgeLock(address(bridgeLock));
    }

    function test_Name() public view { assertEq(wbait.name(), "Wrapped bAIitcoin"); }
    function test_Symbol() public view { assertEq(wbait.symbol(), "wBAIT"); }
    function test_Decimals() public view { assertEq(wbait.decimals(), 8); }
    function test_MaxSupply() public view { assertEq(wbait.MAX_SUPPLY(), 21_000_000 * 10**8); }
    function test_InitialSupplyZero() public view { assertEq(wbait.totalSupply(), 0); }
    function test_BridgeWired() public view { assertEq(wbait.bridgeLock(), address(bridgeLock)); }

    function test_MintByBridge() public {
        uint256 amount = 1000 * 10**8;
        bytes32 reqId = keccak256("mint1");
        vm.prank(operators[0]);
        bridgeLock.requestLockMint(reqId, keccak256("l1"), owner, amount);
        for (uint i = 0; i < 3; i++) {
            vm.prank(operators[i]);
            bridgeLock.confirmLockMint(reqId);
        }
        assertEq(wbait.totalSupply(), amount);
        assertEq(wbait.balanceOf(owner), amount);
    }

    function test_RevertMintByNonBridge() public {
        vm.expectRevert("WBAIT: caller is not BridgeLock");
        wbait.mint(owner, 1e8);
    }

    function test_Pause() public {
        uint256 amount = 1000 * 10**8;
        bytes32 reqId = keccak256("pause-mint");
        vm.prank(operators[0]);
        bridgeLock.requestLockMint(reqId, keccak256("l1"), owner, amount);
        for (uint i = 0; i < 3; i++) {
            vm.prank(operators[i]);
            bridgeLock.confirmLockMint(reqId);
        }
        wbait.pause();
        vm.expectRevert();
        wbait.transfer(address(0x1), 100 * 10**8);
    }

    function test_Burn() public {
        uint256 amount = 1000 * 10**8;
        bytes32 reqId = keccak256("burn-mint");
        vm.prank(operators[0]);
        bridgeLock.requestLockMint(reqId, keccak256("l1"), owner, amount);
        for (uint i = 0; i < 3; i++) {
            vm.prank(operators[i]);
            bridgeLock.confirmLockMint(reqId);
        }
        wbait.burn(amount / 2);
        assertEq(wbait.totalSupply(), amount / 2);
    }

    function test_SetBridgeLockOnlyOnce() public {
        vm.expectRevert("WBAIT: bridge already set");
        wbait.setBridgeLock(address(0xBEEF));
    }
}

contract BridgeLockTest is Test {
    WBAIT public wbait;
    BridgeLock public bridgeLock;
    address[5] public operators;

    function setUp() public {
        operators[0] = address(0xA1);
        operators[1] = address(0xA2);
        operators[2] = address(0xA3);
        operators[3] = address(0xA4);
        operators[4] = address(0xA5);
        wbait = new WBAIT();
        bridgeLock = new BridgeLock(address(wbait), operators);
        wbait.setBridgeLock(address(bridgeLock));
    }

    function test_OperatorCount() public view {
        for (uint i = 0; i < 5; i++) {
            assertTrue(bridgeLock.isOperator(bridgeLock.operators(i)));
        }
    }

    function test_RequestLockMintNoAutoConfirm() public {
        bytes32 requestId = keccak256("test-lock-1");
        uint256 amount = 10_000 * 10**8;
        vm.prank(operators[0]);
        bridgeLock.requestLockMint(requestId, keccak256("l1-tx-1"), address(0xB1), amount);
        assertEq(bridgeLock.totalLocked(), amount);
        assertEq(bridgeLock.totalMinted(), 0);
        assertTrue(bridgeLock.conservationHolds());
        assertEq(wbait.balanceOf(address(0xB1)), 0);
    }

    function test_FullMintRequiresThreeConfirms() public {
        bytes32 requestId = keccak256("full-mint");
        address recipient = address(0xB1);
        uint256 amount = 5_000 * 10**8;
        vm.prank(operators[0]);
        bridgeLock.requestLockMint(requestId, keccak256("l1"), recipient, amount);
        vm.prank(operators[0]);
        bridgeLock.confirmLockMint(requestId);
        assertEq(wbait.balanceOf(recipient), 0);
        vm.prank(operators[1]);
        bridgeLock.confirmLockMint(requestId);
        assertEq(wbait.balanceOf(recipient), 0);
        vm.prank(operators[2]);
        bridgeLock.confirmLockMint(requestId);
        assertEq(wbait.balanceOf(recipient), amount);
        assertEq(bridgeLock.totalMinted(), amount);
        assertTrue(bridgeLock.conservationHolds());
    }

    function test_RevertNonOperator() public {
        vm.prank(address(0x99));
        vm.expectRevert("BridgeLock: not operator");
        bridgeLock.requestLockMint(keccak256("x"), keccak256("l1"), address(0x1), 1000);
    }

    function test_ProposeOperatorUpdate() public {
        bridgeLock.proposeOperatorUpdate(0, address(0xD1));
        (uint256 idx, address proposed,, bool active) = bridgeLock.pendingOperatorUpdate();
        assertEq(idx, 0);
        assertEq(proposed, address(0xD1));
        assertTrue(active);
    }

    function test_ExecuteOperatorUpdateAfterTimelock() public {
        address oldOp = bridgeLock.operators(0);
        bridgeLock.proposeOperatorUpdate(0, address(0xD1));
        vm.warp(block.timestamp + 24 hours + 1);
        bridgeLock.executeOperatorUpdate();
        assertEq(bridgeLock.operators(0), address(0xD1));
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

    function test_RateLimit() public {
        uint256 limit = bridgeLock.RATE_LIMIT();
        vm.prank(operators[0]);
        vm.expectRevert("BridgeLock: rate limit exceeded");
        bridgeLock.requestLockMint(keccak256("rate"), keccak256("l1"), address(0xB1), limit + 1);
    }

    function test_BurnReleasePersistsBeforeConfirmation() public {
        address holder = address(0xB1);
        uint256 amount = 100 * 10**8;
        bytes32 reqId = keccak256("for-burn");
        vm.prank(operators[0]);
        bridgeLock.requestLockMint(reqId, keccak256("l1"), holder, amount);
        for (uint i = 0; i < 3; i++) {
            vm.prank(operators[i]);
            bridgeLock.confirmLockMint(reqId);
        }
        vm.prank(holder);
        wbait.approve(address(bridgeLock), amount);
        vm.prank(holder);
        bridgeLock.initiateBurnRelease("bait1releaseaddress");
        assertEq(wbait.balanceOf(holder), 0);
        assertEq(bridgeLock.getBurnReleaseCount(), 1);
    }
}
