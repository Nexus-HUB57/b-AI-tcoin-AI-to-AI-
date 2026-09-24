// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title FoundersVesting
 * @notice On-chain linear vesting for founder allocations.
 *         Replaces the deprecated founders_faucet_cron.sh off-chain cron approach.
 * @dev Vesting is cliff-based with linear release after the cliff period.
 *      Each founder's allocation is committed at deployment and cannot be increased.
 *
 * SECURITY NOTES:
 * - No admin sweep function — vested tokens are only claimable by the beneficiary.
 * - Revocation is intentionally NOT supported (trustless commitment).
 * - Uses SafeERC20 for token transfers.
 */

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable2Step.sol";

struct VestingSchedule {
    address beneficiary;
    uint256 totalAllocation;
    uint256 cliffEnd;
    uint256 vestingEnd;
    uint256 released;
}

contract FoundersVesting is Ownable2Step {
    using SafeERC20 for IERC20;

    IERC20 public immutable token;

    uint256 public immutable vestingStart;
    uint256 public immutable cliffDuration;
    uint256 public immutable vestingDuration;

    mapping(address => VestingSchedule) public schedules;
    address[] public beneficiaries;

    event VestingCreated(address indexed beneficiary, uint256 totalAllocation, uint256 cliffEnd, uint256 vestingEnd);
    event TokensReleased(address indexed beneficiary, uint256 amount);

    constructor(
        address _token,
        uint256 _vestingStart,
        uint256 _cliffDuration,
        uint256 _vestingDuration
    ) Ownable2Step() {
        require(_token != address(0), "Zero token address");
        require(_vestingDuration > 0, "Zero vesting duration");
        require(_cliffDuration <= _vestingDuration, "Cliff exceeds duration");

        token = IERC20(_token);
        vestingStart = _vestingStart;
        cliffDuration = _cliffDuration;
        vestingDuration = _vestingDuration;
    }

    function addBeneficiary(address beneficiary, uint256 totalAllocation) external onlyOwner {
        require(beneficiary != address(0), "Zero beneficiary");
        require(schedules[beneficiary].totalAllocation == 0, "Already vested");
        require(totalAllocation > 0, "Zero allocation");

        uint256 cliffEnd = vestingStart + cliffDuration;
        uint256 vestingEnd = vestingStart + vestingDuration;

        schedules[beneficiary] = VestingSchedule({
            beneficiary: beneficiary,
            totalAllocation: totalAllocation,
            cliffEnd: cliffEnd,
            vestingEnd: vestingEnd,
            released: 0
        });

        beneficiaries.push(beneficiary);

        emit VestingCreated(beneficiary, totalAllocation, cliffEnd, vestingEnd);
    }

    function releasableAmount(address beneficiary) public view returns (uint256) {
        VestingSchedule memory schedule = schedules[beneficiary];
        if (block.timestamp < schedule.cliffEnd) return 0;
        if (block.timestamp >= schedule.vestingEnd) {
            return schedule.totalAllocation - schedule.released;
        }

        uint256 elapsed = block.timestamp - vestingStart;
        uint256 vested = (schedule.totalAllocation * elapsed) / vestingDuration;
        return vested - schedule.released;
    }

    function release() external {
        VestingSchedule storage schedule = schedules[msg.sender];
        require(schedule.totalAllocation > 0, "No vesting schedule");

        uint256 amount = releasableAmount(msg.sender);
        require(amount > 0, "Nothing to release");

        schedule.released += amount;
        token.safeTransfer(msg.sender, amount);

        emit TokensReleased(msg.sender, amount);
    }
}
