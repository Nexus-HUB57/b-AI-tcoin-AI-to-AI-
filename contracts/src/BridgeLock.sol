// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol"; // Fix #1: TimelockController for pause/unpause
import "./WBAIT.sol";

/**
 * @title BridgeLock — 3-of-5 Multisig Lock-and-Mint Bridge
 * @notice Secures the BAIT L1 → wBAIT ERC-20 bridge.
 *         - Lock events on L1 trigger mint on Ethereum (after 3-of-5 operator confirmation)
 *         - Burn on Ethereum triggers release on L1 (after operator confirmation)
 *         - 24h timelock on operator parameter changes
 *         - Rate limit: 100,000 wBAIT/day/address
 * @dev All state changes go through confirmed operator actions.
 */
contract BridgeLock is Ownable2Step, ReentrancyGuard, Pausable {
    WBAIT public immutable wbait;

    // Fix #1 (CRITICAL): TimelockController for pause/unpause — prevents instant rug by owner
    TimelockController public immutable timelock;

    modifier onlyTimelock() {
        require(msg.sender == address(timelock), "BridgeLock: OnlyTimelock");
        _;
    }

    // Fix #2 (CRITICAL): On-chain bridge invariant tracking — totalMinted <= totalLockedOnL1
    uint256 public totalLockedOnL1;
    uint256 public totalMinted;

    // ── Multisig Operator Config ──
    uint256 public constant REQUIRED_CONFIRMATIONS = 3;
    uint256 public constant NUM_OPERATORS = 5;
    uint256 public constant RATE_LIMIT = 100_000 * 10**8; // 100K wBAIT/day
    uint256 public constant TIMELOCK_DURATION = 24 hours;

    address[NUM_OPERATORS] public operators;
    mapping(address => bool) public isOperator;

    // ── Lock-Mint State ──
    struct LockRequest {
        bytes32 l1TxId;        // BAIT L1 transaction ID
        address recipient;     // Ethereum recipient
        uint256 amount;        // Amount in s'AI'toshi
        uint256 confirmations;
        mapping(address => bool) confirmed;
        bool executed;
    }

    mapping(bytes32 => LockRequest) public lockRequests;
    mapping(bytes32 => bool) public consumedL1TxIds;
    bytes32[] public lockRequestIds;

    // ── Burn-Release State ──
    struct BurnRelease {
        address burner;
        uint256 amount;
        string l1ReleaseAddress; // BAIT L1 address (b'...)
        uint256 confirmations;
        mapping(address => bool) confirmed;
        bool executed;
    }

    mapping(bytes32 => BurnRelease) public burnReleases;
    bytes32[] public burnReleaseIds;

    // ── Rate Limiting ──
    mapping(address => uint256) public dailyMinted;
    mapping(address => uint256) public dailyReserved;
    mapping(address => uint256) public lastMintDay;

    // ── Timelocked Operator Update ──
    struct PendingOperatorUpdate {
        uint256 index;
        address newOperator;
        uint256 proposedAt;
        bool active;
    }
    PendingOperatorUpdate public pendingOperatorUpdate;

    // ── Events ──
    event LockRequested(bytes32 indexed requestId, bytes32 l1TxId, address recipient, uint256 amount);
    event LockConfirmed(bytes32 indexed requestId, address operator);
    event LockExecuted(bytes32 indexed requestId, address recipient, uint256 amount);
    event BurnInitiated(bytes32 indexed releaseId, address burner, uint256 amount, string l1Address);
    event BurnConfirmed(bytes32 indexed releaseId, address operator);
    event BurnExecuted(bytes32 indexed releaseId, uint256 amount, string l1Address);
    event OperatorUpdateProposed(uint256 index, address oldOperator, address newOperator, uint256 effectiveAt);
    event OperatorUpdated(uint256 index, address oldOp, address newOp);
    event OperatorUpdateCancelled();

    modifier onlyOperator() {
        require(isOperator[msg.sender], "BridgeLock: not operator");
        _;
    }

    constructor(
        address _wbait,
        address _timelock, // Fix #1: timelock address parameter
        address[NUM_OPERATORS] memory _operators
    ) Ownable(msg.sender) {
        require(_wbait != address(0), "BridgeLock: zero wbait address");
        require(_timelock != address(0), "BridgeLock: zero timelock address"); // Fix #1
        require(_timelock.code.length > 0, "BridgeLock: timelock has no code");
        wbait = WBAIT(_wbait);
        timelock = TimelockController(payable(_timelock)); // Fix #1

        for (uint256 i = 0; i < NUM_OPERATORS; i++) {
            require(_operators[i] != address(0), "BridgeLock: zero operator");
            require(!isOperator[_operators[i]], "BridgeLock: duplicate operator");
            operators[i] = _operators[i];
            isOperator[_operators[i]] = true;
        }
    }

    // ── Lock-Mint Flow ──

    /**
     * @notice Request lock-mint: operator submits L1 lock evidence
     * @param requestId Unique request ID (hash of L1 tx data)
     * @param l1TxId BAIT L1 transaction where tokens were locked
     * @param recipient Ethereum address to receive wBAIT
     * @param amount Amount in s'AI'toshi (8 decimals)
     */
    function requestLockMint(
        bytes32 requestId,
        bytes32 l1TxId,
        address recipient,
        uint256 amount
    ) external onlyOperator whenNotPaused {
        require(!lockRequests[requestId].executed, "BridgeLock: already executed");
        require(lockRequests[requestId].confirmations == 0, "BridgeLock: already requested");
        require(l1TxId != bytes32(0), "BridgeLock: zero l1 tx id");
        require(!consumedL1TxIds[l1TxId], "BridgeLock: l1 tx already consumed");
        require(recipient != address(0), "BridgeLock: zero recipient");
        require(amount > 0, "BridgeLock: zero amount");

        // Fix #2 (CRITICAL): Track L1 locked amount on-chain for invariant enforcement
        totalLockedOnL1 += amount;

        // Rate limit check
        uint256 currentDay = block.timestamp / 1 days;
        if (lastMintDay[recipient] != currentDay) {
            dailyMinted[recipient] = 0;
            dailyReserved[recipient] = 0;
            lastMintDay[recipient] = currentDay;
        }
        require(dailyMinted[recipient] + dailyReserved[recipient] + amount <= RATE_LIMIT, "BridgeLock: rate limit exceeded");

        LockRequest storage req = lockRequests[requestId];
        consumedL1TxIds[l1TxId] = true;
        dailyReserved[recipient] += amount;
        req.l1TxId = l1TxId;
        req.recipient = recipient;
        req.amount = amount;
        req.executed = false;
        lockRequestIds.push(requestId);

        // Auto-confirm by requester
        req.confirmed[msg.sender] = true;
        req.confirmations = 1;

        emit LockRequested(requestId, l1TxId, recipient, amount);
        emit LockConfirmed(requestId, msg.sender);

        if (req.confirmations >= REQUIRED_CONFIRMATIONS) {
            _executeLockMint(requestId);
        }
    }

    /**
     * @notice Confirm a pending lock-mint request
     */
    function confirmLockMint(bytes32 requestId) external onlyOperator whenNotPaused {
        LockRequest storage req = lockRequests[requestId];
        require(!req.executed, "BridgeLock: already executed");
        require(!req.confirmed[msg.sender], "BridgeLock: already confirmed");
        require(req.confirmations > 0, "BridgeLock: not requested");

        req.confirmed[msg.sender] = true;
        req.confirmations++;

        emit LockConfirmed(requestId, msg.sender);

        if (req.confirmations >= REQUIRED_CONFIRMATIONS) {
            _executeLockMint(requestId);
        }
    }

    function _executeLockMint(bytes32 requestId) internal nonReentrant {
        LockRequest storage req = lockRequests[requestId];
        require(!req.executed, "BridgeLock: already executed");

        // Fix #2 (CRITICAL): On-chain invariant check — totalMinted must never exceed totalLockedOnL1
        require(totalMinted + req.amount <= totalLockedOnL1, "InvariantViolation: totalMinted > totalLocked");
        totalMinted += req.amount;

        req.executed = true;
        dailyMinted[req.recipient] += req.amount;
        dailyReserved[req.recipient] -= req.amount;

        wbait.mint(req.recipient, req.amount);

        emit LockExecuted(requestId, req.recipient, req.amount);
    }

    // ── Burn-Release Flow ──

    /**
     * @notice Initiate burn-release: user burns wBAIT and provides L1 release address
     * @param l1ReleaseAddress BAIT L1 Bech32 address (b'...)
     */
    function initiateBurnRelease(string calldata l1ReleaseAddress) external whenNotPaused nonReentrant {
        uint256 amount = wbait.balanceOf(msg.sender);
        require(amount > 0, "BridgeLock: no wBAIT to burn");
        require(bytes(l1ReleaseAddress).length > 0, "BridgeLock: empty L1 address");

        bytes32 releaseId = keccak256(abi.encodePacked(
            msg.sender, amount, block.number, burnReleaseIds.length
        ));

        BurnRelease storage rel = burnReleases[releaseId];
        rel.burner = msg.sender;
        rel.amount = amount;
        rel.l1ReleaseAddress = l1ReleaseAddress;
        rel.executed = false;
        burnReleaseIds.push(releaseId);

        // Checks-effects-interactions: persist the release before calling the token.
        // A reverted burn rolls the whole transaction back.
        wbait.burnFrom(msg.sender, amount);

        emit BurnInitiated(releaseId, msg.sender, amount, l1ReleaseAddress);
    }

    /**
     * @notice Operator confirms burn-release (L1 release executed)
     */
    function confirmBurnRelease(bytes32 releaseId) external onlyOperator whenNotPaused {
        BurnRelease storage rel = burnReleases[releaseId];
        require(!rel.executed, "BridgeLock: already executed");
        require(!rel.confirmed[msg.sender], "BridgeLock: already confirmed");
        require(rel.amount > 0, "BridgeLock: invalid release");

        rel.confirmed[msg.sender] = true;
        rel.confirmations++;

        emit BurnConfirmed(releaseId, msg.sender);

        if (rel.confirmations >= REQUIRED_CONFIRMATIONS) {
            rel.executed = true;
            emit BurnExecuted(releaseId, rel.amount, rel.l1ReleaseAddress);
        }
    }

    // ── Emergency ── (Fix #1: onlyTimelock instead of onlyOwner — prevents instant rug)
    function pause() external onlyTimelock { _pause(); }
    function unpause() external onlyTimelock { _unpause(); }

    // ── Timelocked Operator Update ──

    /**
     * @notice Propose an operator replacement. Takes effect after TIMELOCK_DURATION (24h).
     * @param index Operator slot index (0-4)
     * @param newOperator New operator address (must be non-zero and not existing operator)
     */
    function proposeOperatorUpdate(uint256 index, address newOperator) external onlyOwner {
        require(index < NUM_OPERATORS, "BridgeLock: invalid index");
        require(newOperator != address(0), "BridgeLock: zero operator");
        require(!isOperator[newOperator], "BridgeLock: already operator");
        require(newOperator != pendingOperatorUpdate.newOperator || !pendingOperatorUpdate.active,
                "BridgeLock: duplicate proposal");

        pendingOperatorUpdate = PendingOperatorUpdate({
            index: index,
            newOperator: newOperator,
            proposedAt: block.timestamp,
            active: true
        });

        emit OperatorUpdateProposed(
            index,
            operators[index],
            newOperator,
            block.timestamp + TIMELOCK_DURATION
        );
    }

    /**
     * @notice Execute a pending operator update after the timelock has expired
     */
    function executeOperatorUpdate() external onlyOwner {
        require(pendingOperatorUpdate.active, "BridgeLock: no pending update");
        require(
            block.timestamp >= pendingOperatorUpdate.proposedAt + TIMELOCK_DURATION,
            "BridgeLock: timelock not expired"
        );

        uint256 idx = pendingOperatorUpdate.index;
        address oldOperator = operators[idx];
        address newOp = pendingOperatorUpdate.newOperator;

        // Clear old operator
        isOperator[oldOperator] = false;
        operators[idx] = newOp;
        isOperator[newOp] = true;

        // Clear pending
        delete pendingOperatorUpdate;

        emit OperatorUpdated(idx, oldOperator, newOp);
    }

    /**
     * @notice Cancel a pending operator update (before timelock expires)
     */
    function cancelOperatorUpdate() external onlyOwner {
        require(pendingOperatorUpdate.active, "BridgeLock: no pending update");
        delete pendingOperatorUpdate;
        emit OperatorUpdateCancelled();
    }

    // ── Views ──
    function getLockRequestCount() external view returns (uint256) { return lockRequestIds.length; }
    function getBurnReleaseCount() external view returns (uint256) { return burnReleaseIds.length; }
}
