// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ChainlinkPriceConsumer
 * @notice Minimal AggregatorV3Interface consumer for BAIT Ethereum contracts.
 * @dev Fail-closed: rejects non-positive answers and stale rounds.
 *      Feed addresses are immutable (set at deploy). Use proxy addresses from
 *      https://docs.chain.link/data-feeds/price-feeds/addresses
 *
 * Ethereum Mainnet examples:
 *   BTC/USD  0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c
 *   ETH/USD  0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419
 *   USDT/USD 0x3E7d1eAB13ad0104d2750B8863b489D65364e32D
 */

interface AggregatorV3Interface {
    function decimals() external view returns (uint8);
    function description() external view returns (string memory);
    function latestRoundData()
        external
        view
        returns (
            uint80 roundId,
            int256 answer,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        );
}

contract ChainlinkPriceConsumer {
    AggregatorV3Interface public immutable feed;
    uint256 public immutable maxStaleness; // seconds

    error InvalidPrice();
    error StalePrice(uint256 updatedAt, uint256 maxAge);
    error IncompleteRound();

    constructor(address feedAddress, uint256 maxStalenessSeconds) {
        require(feedAddress != address(0), "feed=0");
        require(maxStalenessSeconds > 0, "staleness=0");
        feed = AggregatorV3Interface(feedAddress);
        maxStaleness = maxStalenessSeconds;
    }

    /// @notice Latest price scaled to 1e18 (WAD) regardless of feed decimals.
    function getPriceWad() external view returns (uint256) {
        (, int256 answer, , uint256 updatedAt, ) = feed.latestRoundData();
        if (updatedAt == 0) revert IncompleteRound();
        if (answer <= 0) revert InvalidPrice();
        if (block.timestamp > updatedAt + maxStaleness) {
            revert StalePrice(updatedAt, maxStaleness);
        }
        uint8 dec = feed.decimals();
        if (dec == 18) {
            return uint256(answer);
        } else if (dec < 18) {
            return uint256(answer) * (10 ** (18 - dec));
        } else {
            return uint256(answer) / (10 ** (dec - 18));
        }
    }

    /// @notice Raw answer + metadata for off-chain / UI.
    function getLatest()
        external
        view
        returns (int256 answer, uint8 decimals, uint256 updatedAt, uint80 roundId)
    {
        (roundId, answer, , updatedAt, ) = feed.latestRoundData();
        if (updatedAt == 0) revert IncompleteRound();
        if (answer <= 0) revert InvalidPrice();
        if (block.timestamp > updatedAt + maxStaleness) {
            revert StalePrice(updatedAt, maxStaleness);
        }
        decimals = feed.decimals();
    }
}
