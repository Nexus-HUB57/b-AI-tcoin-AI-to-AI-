// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./UserOperation.sol";

interface IPaymaster {
    enum PostOpMode {
        opSucceeded,
        opReverted,
        postOpReverted
    }

    /**
     * @return context opaque data for postOp
     * @return validationData packed: sigFailed | validUntil | validAfter
     */
    function validatePaymasterUserOp(
        UserOperation calldata userOp,
        bytes32 userOpHash,
        uint256 maxCost
    ) external returns (bytes memory context, uint256 validationData);

    function postOp(PostOpMode mode, bytes calldata context, uint256 actualGasCost) external;
}
