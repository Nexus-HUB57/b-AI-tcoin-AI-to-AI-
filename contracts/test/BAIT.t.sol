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

        // Deploy WBAIT with temporary bridge = owner
        wbait = new WBAIT(owner);
        bridgeLock = new BridgeLock(address(wbait), operators);
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

    function test_MintByBridge() public {
        uint256 amount = 1000 * 10**8;
        // As owner (temporary bridge), mint should work
        wbait.mint(owner, amount);
        assertEq(wbait.totalSupply(), amount);
        assertEq(wbait.balanceOf(owner), amount);
    }

    function test_RevertMintExceedsCap() public {
        vm.expectRevert("WBAIT: exceeds max supply cap");
        wbait.mint(owner, 22_000_000 * 10**8);
    }

    function test_Pause() public {
        wbait.mint(owner, 1000 * 10**8);
        wbait.pause();
        vm.expectRevert();
        wbait.transfer(address(0x1), 100 * 10**8);
    }

    function test_Burn() public {
        uint256 amount = 1000 * 10**8;
        wbait.mint(owner, amount);
        wbait.burn(amount / 2);
        assertEq(wbait.totalSupply(), amount / 2);
    }
}

contract BridgeLockTest is Test {
    WBAIT public wbait;
    BridgeLock public bridgeLock;

    function setUp() public {
        address[5] memory ops;
        ops[0] = address(0xA1);
        ops[1] = address(0xA2);
        ops[2] = address(0xA3);
        ops[3] = address(0xA4);
        ops[4] = address(0xA5);
        wbait = new WBAIT(address(this));
        bridgeLock = new BridgeLock(address(wbait), ops);
    }

    function test_OperatorCount() public view {
        for (uint i = 0; i < 5; i++) {
            assertTrue(bridgeLock.isOperator(bridgeLock.operators(i)));
        }
    }

    function test_RequestLockMint() public {
        bytes32 requestId = keccak256("test-lock-1");
        bytes32 l1TxId = keccak256("l1-tx-1");
        address recipient = address(0xB1);
        uint256 amount = 10_000 * 10**8;

        vm.prank(address(0xA1));
        bridgeLock.requestLockMint(requestId, l1TxId, recipient, amount);
    }

    function test_RevertNonOperator() public {
        bytes32 requestId = keccak256("test-lock-2");
        vm.prank(address(0x99));
        vm.expectRevert("BridgeLock: not operator");
        bridgeLock.requestLockMint(requestId, keccak256("l1"), address(0x1), 1000);
    }
}
