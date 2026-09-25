// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/**
 * @title HandlerAdvanced
 * @notice Advanced stateful fuzzer: multi-actor, time warps, rate-limit edges,
 *         failed paths, and ghost accounting.
 */
contract HandlerAdvanced is Test {
    WBAIT public immutable wbait;
    BridgeLock public immutable bridge;
    address[5] public ops;

    uint256 public ghostMinted;
    uint256 public ghostBurned;
    uint256 public ghostRequests;
    uint256 public ghostConfirms;
    uint256 public ghostExecutions;
    uint256 public ghostRateLimitHits;
    uint256 public ghostDoubleConfirmHits;
    uint256 public ghostWarps;

    bytes32[] public openIds;
    mapping(bytes32 => bool) public isOpen;
    mapping(bytes32 => uint8) public confs;
    mapping(bytes32 => address) public reqRecipient;
    mapping(bytes32 => uint256) public reqAmount;

    address[] public actors;
    uint256 constant RATE = 100_000 * 10**8;
    uint256 constant ONE = 10**8;

    constructor(WBAIT _w, BridgeLock _b, address[5] memory _ops) {
        wbait = _w;
        bridge = _b;
        ops = _ops;
        for (uint256 i = 0; i < 8; i++) {
            actors.push(makeAddr(string(abi.encodePacked("actor", i))));
        }
    }

    function requestLock(uint256 opSeed, uint256 amtSeed, uint256 actorSeed) public {
        address op = ops[opSeed % 5];
        address recipient = actors[actorSeed % actors.length];
        uint256 amount = bound(amtSeed, 1, RATE);

        bytes32 id = keccak256(abi.encode(ghostRequests, op, recipient, amount, block.number));
        if (isOpen[id] || reqAmount[id] != 0) return;

        vm.prank(op);
        try bridge.requestLockMint(id, keccak256(abi.encode(id)), recipient, amount) {
            openIds.push(id);
            isOpen[id] = true;
            confs[id] = 0;
            reqRecipient[id] = recipient;
            reqAmount[id] = amount;
            ghostRequests++;
        } catch {
            ghostRateLimitHits++;
        }
    }

    function confirmLock(uint256 opSeed, uint256 reqSeed) public {
        if (openIds.length == 0) return;
        bytes32 id = openIds[reqSeed % openIds.length];
        if (!isOpen[id]) return;

        address op = ops[opSeed % 5];
        vm.prank(op);
        try bridge.confirmLockMint(id) {
            confs[id]++;
            ghostConfirms++;
            if (confs[id] >= 3) {
                isOpen[id] = false;
                ghostExecutions++;
                ghostMinted += reqAmount[id];
            }
        } catch {
            ghostDoubleConfirmHits++;
        }
    }

    function burnPartial(uint256 actorSeed, uint256 amtSeed) public {
        address user = actors[actorSeed % actors.length];
        uint256 bal = wbait.balanceOf(user);
        if (bal == 0) return;
        uint256 amount = bound(amtSeed, 1, bal);

        vm.startPrank(user);
        if (wbait.allowance(user, address(bridge)) < amount) {
            wbait.approve(address(bridge), type(uint256).max);
        }
        try bridge.initiateBurnRelease(amount, "b'fuzz") {
            ghostBurned += amount;
        } catch {}
        vm.stopPrank();
    }

    function warpTime(uint256 seed) public {
        uint256 delta = bound(seed, 1 hours, 3 days);
        vm.warp(block.timestamp + delta);
        ghostWarps++;
    }

    function unauthorizedRequest(uint256 actorSeed, uint256 amtSeed) public {
        address attacker = actors[actorSeed % actors.length];
        uint256 amount = bound(amtSeed, 1, ONE);
        bytes32 id = keccak256(abi.encode("atk", ghostRequests, attacker));
        vm.prank(attacker);
        try bridge.requestLockMint(id, bytes32(0), attacker, amount) {
            revert("unauthorized request succeeded");
        } catch {}
    }

    function unauthorizedMint(uint256 actorSeed, uint256 amtSeed) public {
        address attacker = actors[actorSeed % actors.length];
        uint256 amount = bound(amtSeed, 1, ONE);
        vm.prank(attacker);
        try wbait.mint(attacker, amount) {
            revert("unauthorized mint succeeded");
        } catch {}
    }

    function actorCount() external view returns (uint256) {
        return actors.length;
    }
}
