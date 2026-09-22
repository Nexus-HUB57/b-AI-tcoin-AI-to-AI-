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
 *         Conservation invariant (enforced in BridgeLock): totalMinted <= totalLocked
 *         Max supply: 21,000,000 wBAIT (8 decimals)
 * @dev Only BridgeLock can mint. Owner (prefer Timelock) can pause for emergencies.
 *      bridgeLock is set exactly once via setBridgeLock to allow correct deploy order.
 */
contract WBAIT is ERC20, ERC20Burnable, ERC20Permit, Ownable2Step, Pausable {
    uint256 public constant MAX_SUPPLY = 21_000_000 * 10**8;

    address public bridgeLock;
    bool private bridgeSet;

    event Minted(address indexed to, uint256 amount);
    event SupplyCapApproaching(uint256 currentSupply, uint256 maxSupply);
    event BridgeLockSet(address indexed bridgeLock);

    constructor()
        ERC20("Wrapped bAIitcoin", "wBAIT")
        ERC20Permit("Wrapped bAIitcoin")
        Ownable(msg.sender)
    {}

    function setBridgeLock(address _bridge) external onlyOwner {
        require(!bridgeSet, "WBAIT: bridge already set");
        require(_bridge != address(0), "WBAIT: zero bridge address");
        bridgeLock = _bridge;
        bridgeSet = true;
        emit BridgeLockSet(_bridge);
    }

    modifier onlyBridge() {
        require(msg.sender == bridgeLock, "WBAIT: caller is not BridgeLock");
        _;
    }

    function mint(address to, uint256 amount) external onlyBridge whenNotPaused {
        require(totalSupply() + amount <= MAX_SUPPLY, "WBAIT: exceeds max supply cap");
        _mint(to, amount);
        emit Minted(to, amount);

        if (totalSupply() > (MAX_SUPPLY * 90) / 100) {
            emit SupplyCapApproaching(totalSupply(), MAX_SUPPLY);
        }
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function decimals() public pure override returns (uint8) {
        return 8;
    }

    function _update(address from, address to, uint256 value) internal override(ERC20) whenNotPaused {
        super._update(from, to, value);
    }
}
