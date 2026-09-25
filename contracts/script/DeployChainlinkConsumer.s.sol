// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console2} from "forge-std/Script.sol";
import {ChainlinkPriceConsumer} from "../src/ChainlinkPriceConsumer.sol";

/// @dev Anvil / local deploy. On plain Anvil there is no real Chainlink feed;
///      we deploy a MockAggregator so getPriceWad() is exercisable E2E.
contract MockAggregator {
    uint8 public decimals = 8;
    int256 public answer;
    uint256 public updatedAt;
    uint80 public roundId = 1;

    constructor(int256 _answer) {
        answer = _answer;
        updatedAt = block.timestamp;
    }

    function description() external pure returns (string memory) {
        return "MOCK / USD";
    }

    function latestRoundData()
        external
        view
        returns (uint80, int256, uint256, uint256, uint80)
    {
        return (roundId, answer, updatedAt, updatedAt, roundId);
    }

    function setAnswer(int256 _answer) external {
        answer = _answer;
        updatedAt = block.timestamp;
        roundId += 1;
    }
}

contract DeployChainlinkConsumer is Script {
    function run() external {
        int256 mockBtc = 8386_595_700;

        vm.startBroadcast();
        MockAggregator mock = new MockAggregator(mockBtc);
        ChainlinkPriceConsumer consumer = new ChainlinkPriceConsumer(
            address(mock),
            3600
        );
        vm.stopBroadcast();

        console2.log("MockAggregator", address(mock));
        console2.log("ChainlinkPriceConsumer", address(consumer));
        console2.log("priceWad", consumer.getPriceWad());
    }
}
