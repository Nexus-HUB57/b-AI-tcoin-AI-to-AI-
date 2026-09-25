// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/**
 * @title Handler
 * @notice Stateful fuzzer actor for BridgeLock/WBAIT invariants.
 *         Only calls the public API in valid sequences so the invariant suite
 *         can stress conservation: totalMinted <= totalLockedOnL1 and
 *         totalSupply == totalMinted (after burns).
 */
contract Handler is Test {
    WBAIT public immutable wbait;
    BridgeLock public immutable bridge;
    address[5] public ops;

    uint256 public ghostMintedCumulative;
    uint256 public ghostBurnedCumulative;
    uint256 public ghostRequests;
    uint256 public ghostConfirms;
    uint256 public ghostExecutions;

    bytes32[] public openRequestIds;
    mapping(bytes32 => bool) public isOpen;
    mapping(bytes32 => uint8) public confCount;

    address[] public actors;

    constructor(WBAIT _wbait, BridgeLock _bridge, address[5] memory _ops) {
        wbait = _wbait;
        bridge = _bridge;
        ops = _ops;
        actors.push(makeAddr("actor0"));
        actors.push(makeAddr("actor1"));
        actors.push(makeAddr("actor2"));
    }

    function requestLock(uint256 opSeed, uint256 amountSeed, uint256 actorSeed) external {
        address op = ops[opSeed % 5];
        address recipient = actors[actorSeed % actors.length];
        uint256 amount = bound(amountSeed, 1, 50_000 * 10**8);

        bytes32 id = keccak256(abi.encode(ghostRequests, op, recipient, amount, block.timestamp));
        if (isOpen[id]) return;

        vm.prank(op);
        try bridge.requestLockMint(id, keccak256(abi.encode(id)), recipient, amount) {
            openRequestIds.push(id);
            isOpen[id] = true;
            confCount[id] = 0;
            ghostRequests++;
        } catch {}
    }

    function confirmLock(uint256 opSeed, uint256 reqSeed) external {
        if (openRequestIds.length == 0) return;
        bytes32 id = openRequestIds[reqSeed % openRequestIds.length];
        if (!isOpen[id]) return;

        address op = ops[opSeed % 5];
        vm.prank(op);
        try bridge.confirmLockMint(id) {
            confCount[id]++;
            ghostConfirms++;
            if (confCount[id] >= 3) {
                isOpen[id] = false;
                ghostExecutions++;
                ghostMintedCumulative = bridge.totalMinted() + ghostBurnedCumulative;
            }
        } catch {}
    }

    function burnPartial(uint256 actorSeed, uint256 amountSeed) external {
        address user = actors[actorSeed % actors.length];
        uint256 bal = wbait.balanceOf(user);
        if (bal == 0) return;

        uint256 amount = bound(amountSeed, 1, bal);

        vm.startPrank(user);
        if (wbait.allowance(user, address(bridge)) < amount) {
            wbait.approve(address(bridge), type(uint256).max);
        }
        try bridge.initiateBurnRelease(amount, "b'fuzzL1") {
            ghostBurnedCumulative += amount;
            ghostMintedCumulative = bridge.totalMinted() + ghostBurnedCumulative;
        } catch {}
        vm.stopPrank();
    }

    function openCount() external view returns (uint256) {
        return openRequestIds.length;
    }
}
