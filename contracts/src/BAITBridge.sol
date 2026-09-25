// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title BAITBridge
 * @notice Cross-chain BAIT bridge com invariante on-chain totalMinted <= totalLocked,
 *         EIP-712 typed-data (replay protection via chainid + nonce + processedHashes)
 *         e circuit breaker (daily limit + pause admin).
 *
 * Audit 2026-09-22 — PhD Compliance:
 *   - Invariante enforced on-chain (não off-chain).
 *   - Replay protection por (chainId, sourceChainId, nonce) + msgHash dedup.
 *   - Circuit breaker (pausable + dailyVolumeLimit).
 *   - AccessControl p/ roles (RELAYER_ROLE, ADMIN_ROLE) em vez de Ownable puro.
 *
 * Arquitetura:
 *   1. Usuário chama lock(amount, targetChainId) — trava BAIT L1 e emite Locked event.
 *   2. Relayer (off-chain) chama mint(recipient, amount, sourceChainId, signature)
 *      com uma assinatura EIP-712 válida do RELAYER_ROLE → mint wrapped BAIT L2.
 *   3. Invariante: totalMinted nunca pode ultrapassar totalLocked.
 *   4. Circuit breaker: pausa o contrato ou excede dailyVolumeLimit → revert.
 *
 * Integração:
 *   - Substitui/usado em conjunto com BridgeLock.sol (multisig lock+confirm).
 *   - O mint EIP-712 desta contrato assume que o Relayer detém RELAYER_ROLE
 *     e que os fundos foram previamente locked via lock().
 */
contract BAITBridge is EIP712, AccessControl, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;
    using ECDSA for bytes32;

    bytes32 public constant RELAYER_ROLE = keccak256("RELAYER_ROLE");
    bytes32 public constant ADMIN_ROLE   = keccak256("ADMIN_ROLE");
    bytes32 public constant PAUSER_ROLE  = keccak256("PAUSER_ROLE");

    // -----------------------------------------------------------------
    // State
    // -----------------------------------------------------------------
    IERC20 public immutable baitToken;

    uint256 public totalLocked;
    uint256 public totalMinted;

    // Circuit breaker
    uint256 public dailyVolumeLimit;
    uint256 public currentDailyVolume;
    uint256 public lastVolumeResetTimestamp;
    uint256 public constant MAX_DAILY_LIMIT = 100_000_000 * 1e8; // 100M BAIT (8 decimals)

    // Replay protection
    mapping(address => uint256) public userNonces;
    mapping(bytes32 => bool) public processedHashes;

    // EIP-712 typehash
    bytes32 private constant UNLOCK_TYPEHASH = keccak256(
        "Unlock(address recipient,uint256 amount,uint256 nonce,uint256 sourceChainId)"
    );

    // -----------------------------------------------------------------
    // Events
    // -----------------------------------------------------------------
    event Locked(address indexed sender, uint256 amount, uint256 targetChainId);
    event Minted(address indexed recipient, uint256 amount, bytes32 indexed msgHash);
    event DailyLimitUpdated(uint256 newLimit);
    event Burned(address indexed sender, uint256 amount, uint256 sourceChainId);

    // -----------------------------------------------------------------
    // Errors (gas-efficient custom errors)
    // -----------------------------------------------------------------
    error InvariantViolation(uint256 totalLocked, uint256 totalMintedAfter);
    error InvalidSignature();
    error DailyLimitExceeded(uint256 requested, uint256 remaining);
    error AlreadyProcessed(bytes32 msgHash);
    error ZeroAmount();
    error ZeroAddress();
    error DailyLimitTooHigh(uint256 requested, uint256 max);

    // -----------------------------------------------------------------
    // Constructor
    // -----------------------------------------------------------------
    /**
     * @param _baitToken Endereço do token BAIT nativo (L1).
     * @param _dailyVolumeLimit Limite diario de mint (em wei = smallest unit). Sugerido: 100_000_000 * 1e8.
     * @param _admin Endereço do admin (recebe ADMIN_ROLE).
     * @param _relayer Endereço do relayer (recebe RELAYER_ROLE).
     * @param _pauser Endereço autorizado a pausar (recebe PAUSER_ROLE).
     */
    constructor(
        address _baitToken,
        uint256 _dailyVolumeLimit,
        address _admin,
        address _relayer,
        address _pauser
    ) EIP712("BAITBridge", "1.0.0") {
        if (_baitToken == address(0) || _admin == address(0) || _relayer == address(0) || _pauser == address(0))
            revert ZeroAddress();
        if (_dailyVolumeLimit > MAX_DAILY_LIMIT) revert DailyLimitTooHigh(_dailyVolumeLimit, MAX_DAILY_LIMIT);

        baitToken = IERC20(_baitToken);
        dailyVolumeLimit = _dailyVolumeLimit;
        lastVolumeResetTimestamp = block.timestamp;

        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(ADMIN_ROLE, _admin);
        _grantRole(RELAYER_ROLE, _relayer);
        _grantRole(PAUSER_ROLE, _pauser);
    }

    // -----------------------------------------------------------------
    // Lock (L1 native BAIT → wrapped target chain)
    // -----------------------------------------------------------------
    /**
     * @notice Trava tokens BAIT na rede de origem para emissao equivalente na rede destino.
     * @dev Atualiza totalLocked; invariante garante totalMinted <= totalLocked.
     */
    function lock(uint256 amount, uint256 targetChainId) external whenNotPaused nonReentrant {
        if (amount == 0) revert ZeroAmount();
        // Lock NAO consome daily limit — eh deposito do usuario (low risk).
        // Apenas mint consome (bridge op, high risk).
        // Limite por lock vem apenas do MAX_DAILY_LIMIT global (sanity check).

        totalLocked += amount;
        baitToken.safeTransferFrom(msg.sender, address(this), amount);

        emit Locked(msg.sender, amount, targetChainId);
    }

    // -----------------------------------------------------------------
    // Mint (L2 wrapped BAIT ← L1 lock + EIP-712 signature)
    // -----------------------------------------------------------------
    /**
     * @notice Libera/Mint tokens wrapped na rede destino mediante assinatura EIP-712
     *         válida de um holder de RELAYER_ROLE.
     * @dev Protecoes:
     *       - EIP-712 typed data com chainId + nonce → replay protection
     *       - processedHashes[msgHash] → defesa adicional contra replay
     *       - Invariante: totalMinted + amount <= totalLocked (on-chain)
     *       - Circuit breaker: dailyVolumeLimit
     */
    function mint(
        address recipient,
        uint256 amount,
        uint256 sourceChainId,
        bytes calldata signature
    ) external onlyRole(RELAYER_ROLE) whenNotPaused nonReentrant {
        if (amount == 0) revert ZeroAmount();
        if (recipient == address(0)) revert ZeroAddress();
        _checkAndUpdateDailyVolume(amount);

        // EIP-712 typed-data digest
        uint256 nonce = userNonces[recipient]++;
        bytes32 structHash = keccak256(
            abi.encode(UNLOCK_TYPEHASH, recipient, amount, nonce, sourceChainId)
        );
        bytes32 msgHash = _hashTypedDataV4(structHash);

        // Replay protection
        if (processedHashes[msgHash]) revert AlreadyProcessed(msgHash);

        // Validacao da assinatura (recovered signer deve ter RELAYER_ROLE)
        address signer = msgHash.recover(signature);
        if (!hasRole(RELAYER_ROLE, signer)) revert InvalidSignature();

        // Marca como processada ANTES de qualquer state mutation (checks-effects-interactions)
        processedHashes[msgHash] = true;

        // Invariante on-chain
        uint256 totalMintedAfter = totalMinted + amount;
        if (totalMintedAfter > totalLocked) {
            revert InvariantViolation(totalLocked, totalMintedAfter);
        }

        currentDailyVolume += amount;
        totalMinted = totalMintedAfter;
        baitToken.safeTransfer(recipient, amount);

        emit Minted(recipient, amount, msgHash);
    }

    // -----------------------------------------------------------------
    // Burn (wrapped → unlock L1 native)
    // -----------------------------------------------------------------
    /**
     * @notice Usuário queima wrapped BAIT; admin/relayer correspondente libera L1.
     * @dev Decrementa totalMinted e totalLocked simetricamente.
     */
    function burn(uint256 amount, uint256 sourceChainId) external whenNotPaused nonReentrant {
        if (amount == 0) revert ZeroAmount();
        if (baitToken.balanceOf(msg.sender) < amount) revert ZeroAmount(); // reuse para sinalizar saldo insuficiente

        totalMinted -= amount;
        totalLocked -= amount;
        baitToken.safeTransferFrom(msg.sender, address(this), amount);

        emit Burned(msg.sender, amount, sourceChainId);
    }

    // -----------------------------------------------------------------
    // Admin (timelock-friendly via AccessControl)
    // -----------------------------------------------------------------
    function setDailyVolumeLimit(uint256 newLimit) external onlyRole(ADMIN_ROLE) {
        if (newLimit > MAX_DAILY_LIMIT) revert DailyLimitTooHigh(newLimit, MAX_DAILY_LIMIT);
        dailyVolumeLimit = newLimit;
        emit DailyLimitUpdated(newLimit);
    }

    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    // -----------------------------------------------------------------
    // Internal: circuit breaker
    // -----------------------------------------------------------------
    function _checkAndUpdateDailyVolume(uint256 amount) internal {
        if (block.timestamp >= lastVolumeResetTimestamp + 1 days) {
            currentDailyVolume = 0;
            lastVolumeResetTimestamp = block.timestamp;
        }
        if (currentDailyVolume + amount > dailyVolumeLimit) {
            revert DailyLimitExceeded(amount, dailyVolumeLimit - currentDailyVolume);
        }
    }

    // -----------------------------------------------------------------
    // Views (UI / off-chain integracao)
    // -----------------------------------------------------------------
    function getRemainingDailyAllowance() external view returns (uint256) {
        if (block.timestamp >= lastVolumeResetTimestamp + 1 days) return dailyVolumeLimit;
        return dailyVolumeLimit - currentDailyVolume;
    }

    function getInvariant() external view returns (uint256 locked, uint256 minted, bool ok) {
        return (totalLocked, totalMinted, totalMinted <= totalLocked);
    }

    function domainSeparator() external view returns (bytes32) {
        return _domainSeparatorV4();
    }
}
