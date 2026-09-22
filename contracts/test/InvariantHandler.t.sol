// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "forge-std/StdInvariant.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

contract BridgeHandler is Test {
    WBAIT public wbait;
    BridgeLock public bridge;
    address public op1;
    address public op2;
    address public op3;
    address[] public actors;
    uint256 public reqNonce;

    constructor(WBAIT _wbait, BridgeLock _bridge, address[5] memory ops) {
        wbait = _wbait;
        bridge = _bridge;
        op1 = ops[0];
        op2 = ops[1];
        op3 = ops[2];
        actors.push(address(0xBEEF));
        actors.push(address(0xCAFE));
    }

    function requestLock(uint256 amountSeed, uint256 actorSeed) external {
        uint256 amount = bound(amountSeed, 1, bridge.RATE_LIMIT());
        address recipient = actors[actorSeed % actors.length];
        bytes32 reqId = keccak256(abi.encodePacked(reqNonce++, amount, recipient));
        bytes32 l1Tx = keccak256(abi.encodePacked(reqId));
        vm.prank(op1);
        try bridge.requestLockMint(reqId, l1Tx, recipient, amount) {} catch {}
    }

    function confirmAsOp2(uint256 idSeed) external {
        if (reqNonce == 0) return;
        bytes32 reqId = keccak256(abi.encodePacked(idSeed % reqNonce));
        vm.prank(op2);
        try bridge.confirmLockMint(reqId) {} catch {}
    }

    function confirmAsOp3(uint256 idSeed) external {
        if (reqNonce == 0) return;
        bytes32 reqId = keccak256(abi.encodePacked(idSeed % reqNonce));
        vm.prank(op3);
        try bridge.confirmLockMint(reqId) {} catch {}
    }
}

contract BridgeFoundryInvariant is StdInvariant, Test {
    WBAIT public wbait;
    BridgeLock public bridge;
    BridgeHandler public handler;

    address public op1 = address(0x1001);
    address public op2 = address(0x1002);
    address public op3 = address(0x1003);
    address public op4 = address(0x1004);
    address public op5 = address(0x1005);

    function setUp() public {
        wbait = new WBAIT();
        address[5] memory ops = [op1, op2, op3, op4, op5];
        bridge = new BridgeLock(address(wbait), ops);
        wbait.setBridgeLock(address(bridge));
        handler = new BridgeHandler(wbait, bridge, ops);
        targetContract(address(handler));
    }

    function invariant_mintedLeqLocked() public view {
        assertLe(bridge.totalMinted(), bridge.totalLocked());
    }

    function invariant_conservationHolds() public view {
        assertTrue(bridge.conservationHolds());
    }

    function invariant_supplyUnderCap() public view {
        assertLe(wbait.totalSupply(), wbait.MAX_SUPPLY());
    }

    function invariant_supplyLeqMinted() public view {
        assertLe(wbait.totalSupply(), bridge.totalMinted());
    }

    function invariant_bridgeWired() public view {
        assertEq(wbait.bridgeLock(), address(bridge));
    }
}
