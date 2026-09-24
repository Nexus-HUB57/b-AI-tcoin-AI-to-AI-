// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/governance/TimelockController.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/**
 * @title EchidnaBridgeTester
 * @notice Concrete Echidna property harness for Phase-2 BridgeLock.
 * @dev Operators are fixed addresses (see echidna.yaml senders). Constructor deploys
 *      Timelock + WBAIT + BridgeLock and initializeBridgeLock.
 *
 * Run:
 *   cd contracts && forge build
 *   echidna . --contract EchidnaBridgeTester --config test/echidna.yaml
 */
contract EchidnaBridgeTester {
    WBAIT public wbait;
    BridgeLock public bridge;
    TimelockController public timelock;

    // Fixed operators — must match echidna.yaml `sender` / `deployer`
    address constant OP0 = address(0x10000);
    address constant OP1 = address(0x20000);
    address constant OP2 = address(0x30000);
    address constant OP3 = address(0x40000);
    address constant OP4 = address(0x50000);

    uint256 constant ONE = 10**8;
    uint256 public requestNonce;

    constructor() {
        address[] memory proposers = new address[](1);
        proposers[0] = address(this);
        address[] memory executors = new address[](1);
        executors[0] = address(this);
        // minDelay=1 day; admin = this (can renounce later)
        timelock = new TimelockController(1 days, proposers, executors, address(this));

        wbait = new WBAIT(address(0), address(timelock));

        address[5] memory ops;
        ops[0] = OP0;
        ops[1] = OP1;
        ops[2] = OP2;
        ops[3] = OP3;
        ops[4] = OP4;

        bridge = new BridgeLock(address(wbait), address(timelock), ops);
        wbait.initializeBridgeLock(address(bridge));
    }

    // ── Target functions (called by Echidna with random senders among OPs) ──

    function requestLock(bytes32 l1Salt, address recipient, uint256 amount) external {
        if (!bridge.isOperator(msg.sender)) return;
        if (recipient == address(0)) recipient = address(0xBEEF);
        // Bound amount to rate limit to explore more paths
        amount = (amount % (100_000 * ONE)) + 1;
        bytes32 requestId = keccak256(abi.encodePacked("req", requestNonce++, l1Salt));
        bytes32 l1TxId = keccak256(abi.encodePacked("l1", l1Salt, requestNonce));
        try bridge.requestLockMint(requestId, l1TxId, recipient, amount) {}
        catch {}
    }

    function confirmLock(bytes32 requestId) external {
        if (!bridge.isOperator(msg.sender)) return;
        try bridge.confirmLockMint(requestId) {}
        catch {}
    }

    /// @dev Confirm first N pending request ids (bounded exploration)
    function confirmByIndex(uint256 index) external {
        if (!bridge.isOperator(msg.sender)) return;
        uint256 n = bridge.getLockRequestCount();
        if (n == 0) return;
        index = index % n;
        bytes32 id = bridge.lockRequestIds(index);
        try bridge.confirmLockMint(id) {}
        catch {}
    }

    function burnPartial(uint256 amount, string calldata l1Addr) external {
        uint256 bal = wbait.balanceOf(msg.sender);
        if (bal == 0) return;
        amount = amount % bal;
        if (amount == 0) amount = 1;
        if (bytes(l1Addr).length == 0) l1Addr = "b'release";
        try wbait.approve(address(bridge), amount) {}
        catch { return; }
        try bridge.initiateBurnRelease(amount, l1Addr) {}
        catch {}
    }

    // ── Echidna properties (must hold after every call sequence) ──

    function echidna_minted_le_locked() public view returns (bool) {
        return bridge.totalMinted() <= bridge.totalLockedOnL1();
    }

    function echidna_supply_eq_minted() public view returns (bool) {
        return wbait.totalSupply() == bridge.totalMinted();
    }

    function echidna_under_cap() public view returns (bool) {
        return wbait.totalSupply() <= wbait.MAX_SUPPLY();
    }

    function echidna_threshold_is_three() public view returns (bool) {
        return bridge.REQUIRED_CONFIRMATIONS() == 3;
    }

    function echidna_rate_limit_positive() public view returns (bool) {
        return bridge.RATE_LIMIT() > 0;
    }

    function echidna_operators_count() public view returns (bool) {
        uint256 c;
        if (bridge.isOperator(OP0)) c++;
        if (bridge.isOperator(OP1)) c++;
        if (bridge.isOperator(OP2)) c++;
        if (bridge.isOperator(OP3)) c++;
        if (bridge.isOperator(OP4)) c++;
        return c == 5;
    }
}
