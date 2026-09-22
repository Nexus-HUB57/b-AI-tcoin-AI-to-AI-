// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "./WBAIT.sol";

/**
 * @title BridgeLock — 3-of-5 Multisig Lock-and-Mint Bridge (remediated)
 * @notice Rate limit reserved at request; priority 0..2 for off-chain queue only.
 * @dev Pause/unpause should be owned by a TimelockController in production.
 */
contract BridgeLock is Ownable2Step, ReentrancyGuard, Pausable {
    WBAIT public immutable wbait;

    uint256 public constant REQUIRED_CONFIRMATIONS = 3;
    uint256 public constant NUM_OPERATORS = 5;
    uint256 public constant RATE_LIMIT = 100_000 * 10**8;
    uint256 public constant TIMELOCK_DURATION = 24 hours;
    uint8 public constant MAX_PRIORITY = 2;

    address[NUM_OPERATORS] public operators;
    mapping(address => bool) public isOperator;

    uint256 public totalLocked;
    uint256 public totalMinted;

    struct LockRequest {
        bytes32 l1TxId;
        address recipient;
        uint256 amount;
        uint256 confirmations;
        mapping(address => bool) confirmed;
        bool executed;
        bool exists;
        uint8 priority;
        uint64 createdAt;
    }

    mapping(bytes32 => LockRequest) public lockRequests;
    bytes32[] public lockRequestIds;

    struct BurnRelease {
        address burner;
        uint256 amount;
        string l1ReleaseAddress;
        uint256 confirmations;
        mapping(address => bool) confirmed;
        bool executed;
    }

    mapping(bytes32 => BurnRelease) public burnReleases;
    bytes32[] public burnReleaseIds;

    mapping(address => uint256) public dailyMinted;
    mapping(address => uint256) public lastMintDay;

    struct PendingOperatorUpdate {
        uint256 index;
        address newOperator;
        uint256 proposedAt;
        bool active;
    }
    PendingOperatorUpdate public pendingOperatorUpdate;

    event LockRequested(
        bytes32 indexed requestId,
        bytes32 l1TxId,
        address recipient,
        uint256 amount,
        uint8 priority
    );
    event LockConfirmed(bytes32 indexed requestId, address operator);
    event LockExecuted(bytes32 indexed requestId, address recipient, uint256 amount);
    event BurnInitiated(bytes32 indexed releaseId, address burner, uint256 amount, string l1Address);
    event BurnConfirmed(bytes32 indexed releaseId, address operator);
    event BurnExecuted(bytes32 indexed releaseId, uint256 amount, string l1Address);
    event OperatorUpdateProposed(uint256 index, address oldOperator, address newOperator, uint256 effectiveAt);
    event OperatorUpdated(uint256 index, address oldOp, address newOp);
    event OperatorUpdateCancelled();
    event TotalLockedIncreased(uint256 amount, uint256 newTotalLocked);

    modifier onlyOperator() {
        require(isOperator[msg.sender], "BridgeLock: not operator");
        _;
    }

    constructor(address _wbait, address[NUM_OPERATORS] memory _operators) Ownable(msg.sender) {
        require(_wbait != address(0), "BridgeLock: zero wbait address");
        wbait = WBAIT(_wbait);
        for (uint256 i = 0; i < NUM_OPERATORS; i++) {
            require(_operators[i] != address(0), "BridgeLock: zero operator");
            operators[i] = _operators[i];
            isOperator[_operators[i]] = true;
        }
    }

    function requestLockMint(
        bytes32 requestId,
        bytes32 l1TxId,
        address recipient,
        uint256 amount
    ) external onlyOperator whenNotPaused {
        _requestLockMint(requestId, l1TxId, recipient, amount, 0);
    }

    function requestLockMint(
        bytes32 requestId,
        bytes32 l1TxId,
        address recipient,
        uint256 amount,
        uint8 priority
    ) external onlyOperator whenNotPaused {
        _requestLockMint(requestId, l1TxId, recipient, amount, priority);
    }

    function _requestLockMint(
        bytes32 requestId,
        bytes32 l1TxId,
        address recipient,
        uint256 amount,
        uint8 priority
    ) internal {
        require(priority <= MAX_PRIORITY, "BridgeLock: invalid priority");
        require(!lockRequests[requestId].exists, "BridgeLock: already requested");
        require(amount > 0, "BridgeLock: zero amount");
        require(recipient != address(0), "BridgeLock: zero recipient");

        uint256 currentDay = block.timestamp / 1 days;
        if (lastMintDay[recipient] != currentDay) {
            dailyMinted[recipient] = 0;
            lastMintDay[recipient] = currentDay;
        }
        require(dailyMinted[recipient] + amount <= RATE_LIMIT, "BridgeLock: rate limit exceeded");
        dailyMinted[recipient] += amount;

        LockRequest storage req = lockRequests[requestId];
        req.l1TxId = l1TxId;
        req.recipient = recipient;
        req.amount = amount;
        req.confirmations = 0;
        req.executed = false;
        req.exists = true;
        req.priority = priority;
        req.createdAt = uint64(block.timestamp);
        lockRequestIds.push(requestId);

        totalLocked += amount;
        emit TotalLockedIncreased(amount, totalLocked);
        emit LockRequested(requestId, l1TxId, recipient, amount, priority);
    }

    function confirmLockMint(bytes32 requestId) external onlyOperator whenNotPaused {
        LockRequest storage req = lockRequests[requestId];
        require(req.exists, "BridgeLock: not requested");
        require(!req.executed, "BridgeLock: already executed");
        require(!req.confirmed[msg.sender], "BridgeLock: already confirmed");

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
        require(req.confirmations >= REQUIRED_CONFIRMATIONS, "BridgeLock: insufficient confirmations");
        require(totalMinted + req.amount <= totalLocked, "BridgeLock: minted exceeds locked");

        req.executed = true;
        totalMinted += req.amount;

        wbait.mint(req.recipient, req.amount);
        emit LockExecuted(requestId, req.recipient, req.amount);
    }

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

        wbait.burnFrom(msg.sender, amount);
        if (totalMinted >= amount) {
            totalMinted -= amount;
        }
        emit BurnInitiated(releaseId, msg.sender, amount, l1ReleaseAddress);
    }

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

    function pause() external onlyOwner { _pause(); }
    function unpause() external onlyOwner { _unpause(); }

    function proposeOperatorUpdate(uint256 index, address newOperator) external onlyOwner {
        require(index < NUM_OPERATORS, "BridgeLock: invalid index");
        require(newOperator != address(0), "BridgeLock: zero operator");
        require(!isOperator[newOperator], "BridgeLock: already operator");

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

    function executeOperatorUpdate() external onlyOwner {
        require(pendingOperatorUpdate.active, "BridgeLock: no pending update");
        require(
            block.timestamp >= pendingOperatorUpdate.proposedAt + TIMELOCK_DURATION,
            "BridgeLock: timelock not expired"
        );

        uint256 idx = pendingOperatorUpdate.index;
        address oldOperator = operators[idx];
        address newOp = pendingOperatorUpdate.newOperator;

        isOperator[oldOperator] = false;
        operators[idx] = newOp;
        isOperator[newOp] = true;
        delete pendingOperatorUpdate;

        emit OperatorUpdated(idx, oldOperator, newOp);
    }

    function cancelOperatorUpdate() external onlyOwner {
        require(pendingOperatorUpdate.active, "BridgeLock: no pending update");
        delete pendingOperatorUpdate;
        emit OperatorUpdateCancelled();
    }

    function getLockRequestCount() external view returns (uint256) {
        return lockRequestIds.length;
    }

    function getBurnReleaseCount() external view returns (uint256) {
        return burnReleaseIds.length;
    }

    function getLockRequestId(uint256 index) external view returns (bytes32) {
        return lockRequestIds[index];
    }

    function getLockRequestMeta(bytes32 requestId)
        external
        view
        returns (
            address recipient,
            uint256 amount,
            uint256 confirmations,
            bool executed,
            uint8 priority,
            uint64 createdAt
        )
    {
        LockRequest storage req = lockRequests[requestId];
        return (
            req.recipient,
            req.amount,
            req.confirmations,
            req.executed,
            req.priority,
            req.createdAt
        );
    }

    function conservationHolds() external view returns (bool) {
        return totalMinted <= totalLocked;
    }
}
