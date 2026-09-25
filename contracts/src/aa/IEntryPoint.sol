// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./UserOperation.sol";

/**
 * @title Minimal EntryPoint surface used by BAITVerifyingPaymaster
 * @dev Compatible with official EntryPoint v0.6 deposit API.
 */
interface IEntryPoint {
    function depositTo(address account) external payable;

    function balanceOf(address account) external view returns (uint256);

    function withdrawTo(address payable withdrawAddress, uint256 withdrawAmount) external;

    function getUserOpHash(UserOperation calldata userOp) external view returns (bytes32);
}
