// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title FoundersVesting
 * @notice Vesting on-chain substitui founders_faucet_cron.sh.
 *
 * Audit 2026-09-22 — PhD Compliance:
 *   - Cron job manual removido; libera apenas on-chain e matematicamente.
 *   - Cliff: sem liberacao antes de startTimestamp + cliffSeconds.
 *   - Linear vesting: apos cliff, libera proporcional ao tempo decorrido.
 *   - AccessControl: admin (geral) + releaser (caso queira pausar releases).
 *
 * Fluxo:
 *   1. Owner (admin multisig 3/5) chama addBeneficiary(addr, totalAmount, cliffSeconds).
 *   2. Beneficiary chama release() quando quiser; o contrato calcula vested - released.
 *   3. Pause via PAUSER_ROLE trava novos releases (admin pode investigar/explorar).
 */
contract FoundersVesting is AccessControl, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    bytes32 public constant ADMIN_ROLE  = keccak256("ADMIN_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    IERC20 public immutable token;
    uint256 public immutable startTimestamp;     // global vesting start (TGE)
    uint256 public immutable durationSeconds;    // duracao total (ex: 4 * 365 days)

    struct VestingSchedule {
        uint256 totalAmount;
        uint256 cliffSeconds;     // cliff individual (0 = sem cliff)
        uint256 releasedAmount;
    }

    mapping(address => VestingSchedule) public vestingSchedules;
    address[] public beneficiaries;

    uint256 public totalAllocated;
    uint256 public totalReleased;

    event BeneficiaryAdded(address indexed beneficiary, uint256 totalAmount, uint256 cliffSeconds);
    event BeneficiaryRemoved(address indexed beneficiary, uint256 unallocatedAmount);
    event TokensReleased(address indexed beneficiary, uint256 amount);

    error AlreadyBeneficiary(address beneficiary);
    error NotBeneficiary(address beneficiary);
    error ZeroAmount();
    error NothingToRelease();
    error InsufficientContractBalance(uint256 needed, uint256 available);
    error CliffNotReached(uint256 unlockAt);

    constructor(
        address _token,
        uint256 _startTimestamp,
        uint256 _durationSeconds,
        address _admin,
        address _pauser
    ) {
        require(_token != address(0), "token zero");
        require(_durationSeconds > 0, "duration zero");
        token = IERC20(_token);
        startTimestamp = _startTimestamp;
        durationSeconds = _durationSeconds;

        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(ADMIN_ROLE, _admin);
        _grantRole(PAUSER_ROLE, _pauser);
    }

    function addBeneficiary(address beneficiary, uint256 totalAmount, uint256 cliffSeconds)
        external
        onlyRole(ADMIN_ROLE)
        whenNotPaused
    {
        if (beneficiary == address(0)) revert ZeroAmount();
        if (totalAmount == 0) revert ZeroAmount();
        if (vestingSchedules[beneficiary].totalAmount != 0) revert AlreadyBeneficiary(beneficiary);

        vestingSchedules[beneficiary] = VestingSchedule({
            totalAmount: totalAmount,
            cliffSeconds: cliffSeconds,
            releasedAmount: 0
        });
        beneficiaries.push(beneficiary);
        totalAllocated += totalAmount;

        emit BeneficiaryAdded(beneficiary, totalAmount, cliffSeconds);
    }

    /**
     * @notice Beneficiary chama para liberar tokens vested. Idempotente.
     * @dev Aplica cliff individual; depois calculo linear comecando do TGE.
     */
    function release() external whenNotPaused nonReentrant {
        VestingSchedule storage schedule = vestingSchedules[msg.sender];
        if (schedule.totalAmount == 0) revert NotBeneficiary(msg.sender);

        uint256 vested = _releasableAmount(schedule);
        if (vested == 0) revert NothingToRelease();

        schedule.releasedAmount += vested;
        totalReleased += vested;

        uint256 bal = token.balanceOf(address(this));
        if (bal < vested) revert InsufficientContractBalance(vested, bal);

        token.safeTransfer(msg.sender, vested);
        emit TokensReleased(msg.sender, vested);
    }

    /**
     * @notice View: quanto o beneficiary pode sacar agora.
     */
    function releasableAmountOf(address beneficiary) external view returns (uint256) {
        return _releasableAmount(vestingSchedules[beneficiary]);
    }

    function beneficiariesCount() external view returns (uint256) {
        return beneficiaries.length;
    }

    function _releasableAmount(VestingSchedule memory schedule) internal view returns (uint256) {
        if (block.timestamp < startTimestamp) return 0;
        uint256 cliffEnd = startTimestamp + schedule.cliffSeconds;
        if (block.timestamp < cliffEnd) revert CliffNotReached(cliffEnd);

        uint256 vestedTotal;
        uint256 endTime = startTimestamp + durationSeconds;
        if (block.timestamp >= endTime) {
            vestedTotal = schedule.totalAmount;
        } else {
            uint256 timeFromStart = block.timestamp - startTimestamp;
            vestedTotal = (schedule.totalAmount * timeFromStart) / durationSeconds;
        }

        return vestedTotal - schedule.releasedAmount;
    }

    // --- Admin ---
    function pause() external onlyRole(PAUSER_ROLE) { _pause(); }
    function unpause() external onlyRole(PAUSER_ROLE) { _unpause(); }
}
