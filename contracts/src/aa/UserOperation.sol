// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title UserOperation (ERC-4337 v0.6 layout)
 * @notice Packed user operation submitted by a bundler to EntryPoint.
 */
struct UserOperation {
    address sender;
    uint256 nonce;
    bytes initCode;
    bytes callData;
    uint256 callGasLimit;
    uint256 verificationGasLimit;
    uint256 preVerificationGas;
    uint256 maxFeePerGas;
    uint256 maxPriorityFeePerGas;
    bytes paymasterAndData;
    bytes signature;
}

library UserOperationLib {
    function getSender(UserOperation calldata userOp) internal pure returns (address) {
        return userOp.sender;
    }

    /// @dev Matches EntryPoint v0.6 hash components used by verifying paymasters.
    function hash(UserOperation calldata userOp) internal pure returns (bytes32) {
        return keccak256(
            abi.encode(
                userOp.sender,
                userOp.nonce,
                keccak256(userOp.initCode),
                keccak256(userOp.callData),
                userOp.callGasLimit,
                userOp.verificationGasLimit,
                userOp.preVerificationGas,
                userOp.maxFeePerGas,
                userOp.maxPriorityFeePerGas,
                keccak256(userOp.paymasterAndData),
                keccak256(userOp.signature)
            )
        );
    }
}
