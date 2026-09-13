// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title WBAIT — Wrapped b'AI'tcoin (ERC-20)
 * @notice Lock-and-Mint bridge representation of native BAIT on Ethereum.
 *         Conservation invariant: totalSupply == totalLockedOnL1
 *         Max supply: 21,000,000 wBAIT (8 decimals = 2,100,000,000,000 smallest units)
 * @dev Only BridgeLock can mint. Owner can pause for emergencies.
 */
contract WBAIT is ERC20, ERC20Burnable, ERC20Permit, Ownable2Step, Pausable {
    uint256 public constant MAX_SUPPLY = 21_000_000 * 10**8; // 21M with 8 decimals
    address public immutable bridgeLock;

    event Minted(address indexed to, uint256 amount);
    event SupplyCapApproaching(uint256 currentSupply, uint256 maxSupply);

    constructor(address _bridgeLock)
        ERC20("Wrapped bAIitcoin", "wBAIT")
        ERC20Permit("Wrapped bAIitcoin")
        Ownable(msg.sender)
    {
        require(_bridgeLock != address(0), "WBAIT: zero bridge address");
        bridgeLock = _bridgeLock;
    }

    modifier onlyBridge() {
        require(msg.sender == bridgeLock, "WBAIT: caller is not BridgeLock");
        _;
    }

    /**
     * @notice Mint wBAIT — callable only by the BridgeLock contract
     * @param to Recipient address
     * @param amount Amount in smallest unit (s'AI'toshi, 8 decimals)
     */
    function mint(address to, uint256 amount) external onlyBridge whenNotPaused {
        require(totalSupply() + amount <= MAX_SUPPLY, "WBAIT: exceeds max supply cap");
        _mint(to, amount);
        emit Minted(to, amount);

        // Alert when supply > 90% of cap
        if (totalSupply() > (MAX_SUPPLY * 90) / 100) {
            emit SupplyCapApproaching(totalSupply(), MAX_SUPPLY);
        }
    }

    /**
     * @notice Emergency pause — only owner
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice Unpause — only owner
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    // Override decimals to 8 (s'AI'toshi) instead of OZ default 18
    function decimals() public pure override returns (uint8) {
        return 8;
    }

    // Override _update to enforce pause on transfers
    function _update(address from, address to, uint256 value) internal override(ERC20) whenNotPaused {
        super._update(from, to, value);
    }
}
