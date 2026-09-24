// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IBridgeView {
    function totalMinted() external view returns (uint256);
    function totalLockedOnL1() external view returns (uint256);
    function REQUIRED_CONFIRMATIONS() external view returns (uint256);
    function RATE_LIMIT() external view returns (uint256);
}

interface IERC20View {
    function totalSupply() external view returns (uint256);
    function MAX_SUPPLY() external view returns (uint256);
}

/// @notice Echidna property-mode surface (echidna_* returns bool).
abstract contract EchidnaBridgeProperties {
    IBridgeView internal bridge;
    IERC20View internal token;

    function echidna_minted_le_locked() public view returns (bool) {
        return bridge.totalMinted() <= bridge.totalLockedOnL1();
    }

    function echidna_supply_eq_minted() public view returns (bool) {
        return token.totalSupply() == bridge.totalMinted();
    }

    function echidna_under_cap() public view returns (bool) {
        return token.totalSupply() <= token.MAX_SUPPLY();
    }

    function echidna_threshold_is_three() public view returns (bool) {
        return bridge.REQUIRED_CONFIRMATIONS() == 3;
    }

    function echidna_rate_limit_positive() public view returns (bool) {
        return bridge.RATE_LIMIT() > 0;
    }
}
