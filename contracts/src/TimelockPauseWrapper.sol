// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/governance/TimelockController.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title IPausableTarget
 * @notice Interface mínima que o target deve implementar p/ ser wrappable.
 */
interface IPausableTarget {
    function pause() external;
    function unpause() external;
    function paused() external view returns (bool);
}

/**
 * @title TimelockPauseWrapper
 * @notice Adapter que torna pause()/unpause() em contratos existentes
 *         (BridgeLock.sol, WBAIT.sol) dependentes de TimelockController 48h.
 *
 * Audit 2026-09-22 — PhD Compliance (P2 item):
 *   "pause() monárquico sem timelock" → CRITICAL.
 *   Substituímos Ownable-only pause por:
 *     1. Wrapper expõe schedulePause() e scheduleUnpause().
 *     2. Cada chamada agenda operation no TimelockController com delay 48h.
 *     3. Após 48h, qualquer um chama Timelock.execute() → Timelock chama
 *        executePause() no wrapper → wrapper chama pause()/unpause() no target.
 *     4. Janela mínima de 48h para a comunidade reagir.
 */
contract TimelockPauseWrapper is AccessControl {
    bytes32 public constant GUARDIAN_ROLE = keccak256("GUARDIAN_ROLE");

    TimelockController public immutable timelock;
    IPausableTarget public immutable target;
    uint256 public constant DELAY = 48 hours;

    event PauseScheduled(address indexed caller, uint256 executeAfter);
    event UnpauseScheduled(address indexed caller, uint256 executeAfter);
    event PauseExecuted();
    event UnpauseExecuted();

    error NotTimelock();
    error DelayTooShort(uint256 requested, uint256 minimum);

    constructor(TimelockController _timelock, IPausableTarget _target, address _admin) {
        require(address(_timelock) != address(0) && address(_target) != address(0), "zero addr");
        uint256 minDelay = _timelock.getMinDelay();
        if (minDelay < DELAY) revert DelayTooShort(minDelay, DELAY);

        timelock = _timelock;
        target = _target;

        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(GUARDIAN_ROLE, _admin);
    }

    function schedulePause() external onlyRole(GUARDIAN_ROLE) returns (uint256 executeAfter) {
        executeAfter = block.timestamp + DELAY;
        timelock.schedule(
            address(this), 0,
            abi.encodeWithSelector(this.executePause.selector),
            bytes32(0), bytes32(0), DELAY
        );
        emit PauseScheduled(msg.sender, executeAfter);
    }

    function scheduleUnpause() external onlyRole(GUARDIAN_ROLE) returns (uint256 executeAfter) {
        executeAfter = block.timestamp + DELAY;
        timelock.schedule(
            address(this), 0,
            abi.encodeWithSelector(this.executeUnpause.selector),
            bytes32(0), bytes32(0), DELAY
        );
        emit UnpauseScheduled(msg.sender, executeAfter);
    }

    function executePause() external {
        if (msg.sender != address(timelock)) revert NotTimelock();
        target.pause();
        emit PauseExecuted();
    }

    function executeUnpause() external {
        if (msg.sender != address(timelock)) revert NotTimelock();
        target.unpause();
        emit UnpauseExecuted();
    }
}

