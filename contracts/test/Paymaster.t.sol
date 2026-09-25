// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/aa/BAITVerifyingPaymaster.sol";
import "../src/aa/IEntryPoint.sol";
import "../src/aa/UserOperation.sol";

/// @dev Minimal EntryPoint stub for unit tests (deposit bookkeeping only).
contract MockEntryPoint is IEntryPoint {
    mapping(address => uint256) public balances;

    function depositTo(address account) external payable override {
        balances[account] += msg.value;
    }

    function balanceOf(address account) external view override returns (uint256) {
        return balances[account];
    }

    function withdrawTo(address payable withdrawAddress, uint256 withdrawAmount) external override {
        require(balances[msg.sender] >= withdrawAmount, "EP: insufficient");
        balances[msg.sender] -= withdrawAmount;
        (bool ok,) = withdrawAddress.call{value: withdrawAmount}("");
        require(ok, "EP: withdraw fail");
    }

    function getUserOpHash(UserOperation calldata userOp) external pure override returns (bytes32) {
        return UserOperationLib.hash(userOp);
    }

    /// Test helper: invoke paymaster as EntryPoint would.
    function callValidate(
        BAITVerifyingPaymaster pm,
        UserOperation calldata userOp,
        bytes32 userOpHash,
        uint256 maxCost
    ) external returns (bytes memory context, uint256 validationData) {
        return pm.validatePaymasterUserOp(userOp, userOpHash, maxCost);
    }
}

contract PaymasterTest is Test {
    MockEntryPoint internal ep;
    BAITVerifyingPaymaster internal pm;
    uint256 internal signerKey;
    address internal signer;
    address internal owner = address(0xB0B);

    function setUp() public {
        ep = new MockEntryPoint();
        signerKey = 0xA11CE;
        signer = vm.addr(signerKey);
        pm = new BAITVerifyingPaymaster(IEntryPoint(address(ep)), signer, owner);

        vm.deal(address(this), 10 ether);
        pm.deposit{value: 1 ether}();
        assertEq(pm.getDeposit(), 1 ether);
    }

    function _packPmData(uint48 validUntil, uint48 validAfter, bytes memory sig)
        internal
        view
        returns (bytes memory)
    {
        return abi.encodePacked(address(pm), validUntil, validAfter, sig);
    }

    function _sign(bytes32 userOpHash, uint48 validUntil, uint48 validAfter)
        internal
        view
        returns (bytes memory)
    {
        bytes32 digest = pm.getHash(userOpHash, validUntil, validAfter);
        bytes32 ethHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", digest));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(signerKey, ethHash);
        return abi.encodePacked(r, s, v);
    }

    function _baseUserOp(bytes memory pmData) internal pure returns (UserOperation memory) {
        return UserOperation({
            sender: address(0x1234),
            nonce: 0,
            initCode: "",
            callData: "",
            callGasLimit: 100000,
            verificationGasLimit: 100000,
            preVerificationGas: 21000,
            maxFeePerGas: 1 gwei,
            maxPriorityFeePerGas: 1 gwei,
            paymasterAndData: pmData,
            signature: ""
        });
    }

    function test_validSignature_sponsors() public {
        bytes32 uoh = keccak256("user-op-hash-1");
        uint48 validUntil = uint48(block.timestamp + 3600);
        uint48 validAfter = 0;
        bytes memory sig = _sign(uoh, validUntil, validAfter);
        bytes memory pmData = _packPmData(validUntil, validAfter, sig);

        UserOperation memory op = _baseUserOp(pmData);
        (bytes memory ctx, uint256 vd) = ep.callValidate(pm, op, uoh, 0.01 ether);

        // sigFailed bit must be 0
        assertEq(vd & 1, 0);
        (address sender,,) = abi.decode(ctx, (address, bytes32, uint256));
        assertEq(sender, address(0x1234));
    }

    function test_badSignature_failsFlag() public {
        bytes32 uoh = keccak256("user-op-hash-2");
        uint48 validUntil = uint48(block.timestamp + 3600);
        // sign with wrong key
        uint256 badKey = 0xBAD;
        bytes32 digest = pm.getHash(uoh, validUntil, 0);
        bytes32 ethHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", digest));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(badKey, ethHash);
        bytes memory sig = abi.encodePacked(r, s, v);
        bytes memory pmData = _packPmData(validUntil, 0, sig);

        UserOperation memory op = _baseUserOp(pmData);
        (, uint256 vd) = ep.callValidate(pm, op, uoh, 0.01 ether);
        assertEq(vd & 1, 1);
    }

    function test_maxCostRejected() public {
        bytes32 uoh = keccak256("user-op-hash-3");
        uint48 validUntil = uint48(block.timestamp + 3600);
        bytes memory sig = _sign(uoh, validUntil, 0);
        bytes memory pmData = _packPmData(validUntil, 0, sig);
        UserOperation memory op = _baseUserOp(pmData);

        vm.expectRevert("Paymaster: maxCost too high");
        ep.callValidate(pm, op, uoh, 1 ether); // > default 0.05 ether
    }

    function test_restrictSenders() public {
        vm.prank(owner);
        pm.setRestrictSenders(true);

        bytes32 uoh = keccak256("user-op-hash-4");
        uint48 validUntil = uint48(block.timestamp + 3600);
        bytes memory sig = _sign(uoh, validUntil, 0);
        bytes memory pmData = _packPmData(validUntil, 0, sig);
        UserOperation memory op = _baseUserOp(pmData);

        vm.expectRevert("Paymaster: sender not allowed");
        ep.callValidate(pm, op, uoh, 0.01 ether);

        vm.prank(owner);
        pm.setSenderAllowed(address(0x1234), true);
        (, uint256 vd) = ep.callValidate(pm, op, uoh, 0.01 ether);
        assertEq(vd & 1, 0);
    }

    function test_onlyEntryPoint() public {
        bytes32 uoh = keccak256("x");
        UserOperation memory op = _baseUserOp(hex"");
        vm.expectRevert("Paymaster: not EntryPoint");
        pm.validatePaymasterUserOp(op, uoh, 0);
    }
}
