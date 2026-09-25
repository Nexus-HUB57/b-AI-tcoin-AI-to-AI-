// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";

/**
 * @title WBAIT — Wrapped b'AI'tcoin (ERC-20)
 * @notice Lock-and-Mint bridge representation of native BAIT on Ethereum.
 *         Conservation invariant: totalSupply == totalLockedOnL1
 *         Max supply: 21,000,000 wBAIT (8 decimals)
 * @dev Only BridgeLock can mint. Pause/unpause via TimelockController.
 */
contract WBAIT is ERC20, ERC20Burnable, ERC20Permit, Ownable2Step, Pausable {
    uint256 public constant MAX_SUPPLY = 21_000_000 * 10**8;
    address public bridgeLock;
    bool private _bridgeLockInitialized;
    TimelockController public immutable timelock;

    modifier onlyTimelock() {
        require(msg.sender == address(timelock), "WBAIT: OnlyTimelock");
        _;
    }

    event Minted(address indexed to, uint256 amount);
    event SupplyCapApproaching(uint256 currentSupply, uint256 maxSupply);

    constructor(address _bridgeLock, address _timelock)
        ERC20("Wrapped bAIitcoin", "wBAIT")
        ERC20Permit("Wrapped bAIitcoin")
        Ownable(msg.sender)
    {
        bridgeLock = _bridgeLock;
        if (_bridgeLock != address(0)) { _bridgeLockInitialized = true; }
        require(_timelock != address(0), "WBAIT: zero timelock address");
        timelock = TimelockController(payable(_timelock));
    }

    modifier onlyBridge() {
        require(msg.sender == bridgeLock, "WBAIT: caller is not BridgeLock");
        _;
    }

    function initializeBridgeLock(address _bridgeLock) external onlyOwner {
        require(!_bridgeLockInitialized, "WBAIT: bridgeLock already initialized");
        require(_bridgeLock != address(0), "WBAIT: zero bridge address");
        bridgeLock = _bridgeLock;
        _bridgeLockInitialized = true;
    }

    function mint(address to, uint256 amount) external onlyBridge whenNotPaused {
        require(totalSupply() + amount <= MAX_SUPPLY, "WBAIT: exceeds max supply cap");
        _mint(to, amount);
        emit Minted(to, amount);
        if (totalSupply() > (MAX_SUPPLY * 90) / 100) {
            emit SupplyCapApproaching(totalSupply(), MAX_SUPPLY);
        }
    }

    function pause() external onlyTimelock { _pause(); }
    function unpause() external onlyTimelock { _unpause(); }

    function decimals() public pure override returns (uint8) { return 8; }

    function _update(address from, address to, uint256 value) internal override(ERC20) whenNotPaused {
        super._update(from, to, value);
    }
}
