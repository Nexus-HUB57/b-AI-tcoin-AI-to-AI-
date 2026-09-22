// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../../src/WBAIT.sol";
import "../../src/BridgeLock.sol";

/**
 * @title BridgeEchidna — property-based tests for remediated BridgeLock/WBAIT
 * CRITICAL: totalMinted <= totalLocked must never break.
 */
contract BridgeEchidna {
    WBAIT public wbait;
    BridgeLock public bridge;

    address constant OP1 = address(0x1001);
    address constant OP2 = address(0x1002);
    address constant OP3 = address(0x1003);
    address constant OP4 = address(0x1004);
    address constant OP5 = address(0x1005);

    address constant USER_A = address(0xBEEF);
    address constant USER_B = address(0xCAFE);

    uint256 public requestCounter;

    constructor() {
        wbait = new WBAIT();
        address[5] memory ops = [OP1, OP2, OP3, OP4, OP5];
        bridge = new BridgeLock(address(wbait), ops);
        wbait.setBridgeLock(address(bridge));
    }

    function echidna_minted_leq_locked() public view returns (bool) {
        return bridge.totalMinted() <= bridge.totalLocked();
    }

    function echidna_conservation_holds() public view returns (bool) {
        return bridge.conservationHolds();
    }

    function echidna_supply_under_cap() public view returns (bool) {
        return wbait.totalSupply() <= wbait.MAX_SUPPLY();
    }

    function echidna_bridge_wired() public view returns (bool) {
        return wbait.bridgeLock() == address(bridge);
    }

    function echidna_supply_leq_minted() public view returns (bool) {
        return wbait.totalSupply() <= bridge.totalMinted();
    }

    function op_requestLockMint(uint256 amountSeed, uint8 userPick) public {
        uint256 amount = (amountSeed % (100_000 * 10**8 - 1)) + 1;
        address recipient = (userPick % 2 == 0) ? USER_A : USER_B;
        bytes32 reqId = keccak256(abi.encodePacked(requestCounter++, amount, recipient, block.timestamp));
        bytes32 l1Tx = keccak256(abi.encodePacked(reqId, "l1"));
        try bridge.requestLockMint(reqId, l1Tx, recipient, amount) {} catch {}
    }

    function op_confirmLockMint(uint256 indexSeed) public {
        if (requestCounter == 0) return;
        uint256 idx = indexSeed % requestCounter;
        bytes32 reqId = keccak256(abi.encodePacked(idx));
        try bridge.confirmLockMint(reqId) {} catch {}
    }

    function op_requestOnly(uint256 amountSeed) public {
        op_requestLockMint(amountSeed, 0);
    }
}
