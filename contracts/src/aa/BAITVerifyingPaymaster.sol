// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";
import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "./IEntryPoint.sol";
import "./IPaymaster.sol";
import "./UserOperation.sol";

/**
 * @title BAITVerifyingPaymaster
 * @notice ERC-4337 verifying paymaster for b'AI'tcoin / MyLink gas sponsorship.
 *
 * paymasterAndData layout (min 52 + 65 bytes):
 *   [0:20]  paymaster address
 *   [20:26] validUntil  (uint48 big-endian)
 *   [26:32] validAfter  (uint48 big-endian)
 *   [32:]   ECDSA signature (65 bytes) over:
 *           keccak256(abi.encode(userOpHash, validUntil, validAfter, address(this), chainid))
 *
 * Off-chain signer key is operational (PAYMASTER_SIGNER_KEY) — never a user keystore.
 * Fund gas via EntryPoint.depositTo(paymaster).
 */
contract BAITVerifyingPaymaster is IPaymaster, Ownable2Step, Pausable {
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;

    IEntryPoint public immutable entryPoint;
    address public verifyingSigner;

    uint256 public maxCostWei;
    mapping(address => bool) public allowedSenders; // empty map = allow all
    bool public restrictSenders;

    event VerifyingSignerUpdated(address indexed previous, address indexed current);
    event MaxCostUpdated(uint256 previous, uint256 current);
    event RestrictSendersUpdated(bool enabled);
    event SenderAllowed(address indexed sender, bool allowed);
    event UserOpSponsored(bytes32 indexed userOpHash, address indexed sender, uint256 maxCost);

    modifier onlyEntryPoint() {
        require(msg.sender == address(entryPoint), "Paymaster: not EntryPoint");
        _;
    }

    constructor(IEntryPoint _entryPoint, address _verifyingSigner, address _owner) Ownable(_owner) {
        require(address(_entryPoint) != address(0), "Paymaster: zero EntryPoint");
        require(_verifyingSigner != address(0), "Paymaster: zero signer");
        entryPoint = _entryPoint;
        verifyingSigner = _verifyingSigner;
        maxCostWei = 0.05 ether; // default cap per UserOp
    }

    // ── Admin ──────────────────────────────────────────────────────────────

    function setVerifyingSigner(address signer) external onlyOwner {
        require(signer != address(0), "Paymaster: zero signer");
        emit VerifyingSignerUpdated(verifyingSigner, signer);
        verifyingSigner = signer;
    }

    function setMaxCostWei(uint256 maxCost) external onlyOwner {
        emit MaxCostUpdated(maxCostWei, maxCost);
        maxCostWei = maxCost;
    }

    function setRestrictSenders(bool enabled) external onlyOwner {
        restrictSenders = enabled;
        emit RestrictSendersUpdated(enabled);
    }

    function setSenderAllowed(address sender, bool allowed) external onlyOwner {
        allowedSenders[sender] = allowed;
        emit SenderAllowed(sender, allowed);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function deposit() external payable {
        entryPoint.depositTo{value: msg.value}(address(this));
    }

    function withdrawTo(address payable to, uint256 amount) external onlyOwner {
        entryPoint.withdrawTo(to, amount);
    }

    function getDeposit() external view returns (uint256) {
        return entryPoint.balanceOf(address(this));
    }

    // ── IPaymaster ─────────────────────────────────────────────────────────

    function validatePaymasterUserOp(
        UserOperation calldata userOp,
        bytes32 userOpHash,
        uint256 maxCost
    ) external override onlyEntryPoint whenNotPaused returns (bytes memory context, uint256 validationData) {
        require(maxCost <= maxCostWei, "Paymaster: maxCost too high");
        if (restrictSenders) {
            require(allowedSenders[userOp.sender], "Paymaster: sender not allowed");
        }

        (uint48 validUntil, uint48 validAfter, bytes calldata signature) = parsePaymasterAndData(userOp.paymasterAndData);

        bytes32 hash = MessageHashUtils.toEthSignedMessageHash(
            getHash(userOpHash, validUntil, validAfter)
        );
        address recovered = ECDSA.recover(hash, signature);
        bool sigFailed = recovered != verifyingSigner;

        validationData = _packValidationData(sigFailed, validUntil, validAfter);
        context = abi.encode(userOp.sender, userOpHash, maxCost);

        if (!sigFailed) {
            emit UserOpSponsored(userOpHash, userOp.sender, maxCost);
        }
    }

    function postOp(PostOpMode /*mode*/, bytes calldata /*context*/, uint256 /*actualGasCost*/)
        external
        override
        onlyEntryPoint
    {
        // No post-charge accounting in verifying mode; gas was prepaid via deposit.
    }

    // ── Hash / parse helpers (used off-chain for signing) ───────────────────

    function getHash(bytes32 userOpHash, uint48 validUntil, uint48 validAfter)
        public
        view
        returns (bytes32)
    {
        return keccak256(abi.encode(userOpHash, validUntil, validAfter, address(this), block.chainid));
    }

    function parsePaymasterAndData(bytes calldata paymasterAndData)
        public
        pure
        returns (uint48 validUntil, uint48 validAfter, bytes calldata signature)
    {
        require(paymasterAndData.length >= 52 + 65, "Paymaster: short paymasterAndData");
        require(address(bytes20(paymasterAndData[0:20])) == address(this), "Paymaster: wrong pm");
        validUntil = uint48(bytes6(paymasterAndData[20:26]));
        validAfter = uint48(bytes6(paymasterAndData[26:32]));
        signature = paymasterAndData[32:];
    }

    function _packValidationData(bool sigFailed, uint48 validUntil, uint48 validAfter)
        internal
        pure
        returns (uint256)
    {
        return (sigFailed ? 1 : 0) | (uint256(validUntil) << 160) | (uint256(validAfter) << (160 + 48));
    }

    receive() external payable {
        entryPoint.depositTo{value: msg.value}(address(this));
    }
}
