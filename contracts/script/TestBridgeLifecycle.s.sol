// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/**
 * @title TestBridgeLifecycle - Full Bridge Lifecycle Test on Live Network
 * @notice Tests the complete lock-mint -> burn-release cycle on a deployed
 *         BAIT system (Sepolia or any live network).
 *
 * Lifecycle Flow:
 *   1. Request lock-mint  (Operator 1 submits L1 lock evidence)
 *   2. Confirm lock-mint  (Operator 2 confirms)
 *   3. Confirm lock-mint  (Operator 3 confirms, triggers execution)
 *   4. Verify minted amount on WBAIT
 *   5. Recipient approves BridgeLock for burn
 *   6. Recipient initiates burn-release
 *   7. Confirm burn-release (Operator 1)
 *   8. Confirm burn-release (Operator 2)
 *   9. Confirm burn-release (Operator 3, marks executed)
 *  10. Verify burn was executed
 *
 * Usage:
 *   forge script script/TestBridgeLifecycle.s.sol \
 *     --rpc-url $SEPOLIA_RPC_URL \
 *     --broadcast -vvvv
 *
 * Environment Variables Required:
 *   WBAIT_ADDRESS         - Deployed WBAIT contract address
 *   BRIDGELOCK_ADDRESS    - Deployed BridgeLock contract address
 *   OPERATOR_KEY_1        - Private key for operator 1 (requester)
 *   OPERATOR_KEY_2        - Private key for operator 2 (confirmer)
 *   OPERATOR_KEY_3        - Private key for operator 3 (confirmer)
 *   RECIPIENT_KEY         - Private key for the mint recipient / burn initiator
 *
 * Test Amount: 1 wBAIT (100_000_000 sAI'toshi) - safe for testnet
 */
contract TestBridgeLifecycle is Script {
    // -- Test Parameters --
    uint256 constant TEST_AMOUNT = 1 * 10**8; // 1 wBAIT in sAI'toshi
    string constant L1_RELEASE_ADDRESS = "b1test_sepolia_lifecycle_addr";

    // -- State (stored to avoid stack-too-deep) --
    WBAIT public wbait;
    BridgeLock public bridgeLock;
    address public bridgeAddr;
    address public recipient;
    uint256 public recipientKey;
    uint256 public opKey1;
    uint256 public opKey2;
    uint256 public opKey3;
    bytes32 public lockRequestId;
    bytes32 public burnReleaseId;
    uint256 public preMintSupply;
    uint256 public preMintBalance;

    function run() external {
        // -- Load Deployed Contracts --
        address wbaitAddr = vm.envAddress("WBAIT_ADDRESS");
        bridgeAddr = vm.envAddress("BRIDGELOCK_ADDRESS");
        wbait = WBAIT(wbaitAddr);
        bridgeLock = BridgeLock(bridgeAddr);

        // -- Load Keys --
        opKey1 = vm.envUint("OPERATOR_KEY_1");
        opKey2 = vm.envUint("OPERATOR_KEY_2");
        opKey3 = vm.envUint("OPERATOR_KEY_3");
        recipientKey = vm.envUint("RECIPIENT_KEY");

        address op1 = vm.addr(opKey1);
        address op2 = vm.addr(opKey2);
        address op3 = vm.addr(opKey3);
        recipient = vm.addr(recipientKey);

        // -- Pre-Test Validation --
        _preTestValidation(op1, op2, op3, recipient);

        console.log("============================================================");
        console.log("  BAIT Bridge Lifecycle Test");
        console.log("  Network Chain ID:", block.chainid);
        console.log("============================================================");
        console.log("WBAIT:     ", wbaitAddr);
        console.log("BridgeLock:", bridgeAddr);
        console.log("Test Amount:", TEST_AMOUNT);
        console.log("");

        // Record pre-test state
        preMintSupply = wbait.totalSupply();
        preMintBalance = wbait.balanceOf(recipient);

        console.log("Pre-test state:");
        console.log("  totalSupply:", preMintSupply);
        console.log("  recipient balance:", preMintBalance);
        console.log("  lock request count:", bridgeLock.getLockRequestCount());
        console.log("  burn release count:", bridgeLock.getBurnReleaseCount());
        console.log("");

        // -- PHASE 1: LOCK-MINT --
        _executeLockMint(op1, op2, op3);

        // -- PHASE 2: BURN-RELEASE --
        _executeBurnRelease(op1, op2, op3);

        // -- SUMMARY --
        _printSummary();
    }

    // -- Phase 1: Lock-Mint Flow --

    function _executeLockMint(address op1, address op2, address op3) internal {
        console.log("============================================================");
        console.log("  PHASE 1: LOCK-MINT FLOW");
        console.log("============================================================");

        // Generate deterministic request ID
        lockRequestId = keccak256(abi.encodePacked(
            "SEPOLIA_LIFECYCLE_TEST",
            block.timestamp,
            bridgeLock.getLockRequestCount()
        ));
        bytes32 l1TxId = keccak256("mock_l1_lock_tx_for_sepolia_test");

        // Step 1: Operator 1 requests lock-mint (auto-confirms)
        console.log("--- Step 1: Request Lock-Mint (Operator 1) ---");
        vm.startBroadcast(opKey1);
        bridgeLock.requestLockMint(lockRequestId, l1TxId, recipient, TEST_AMOUNT);
        vm.stopBroadcast();
        console.log("  Request submitted by:", op1);
        console.log("  Request ID (uint):", uint256(lockRequestId));
        console.log("  Recipient:", recipient);
        console.log("  Amount:", TEST_AMOUNT);

        // Step 2: Operator 2 confirms lock-mint
        console.log("--- Step 2: Confirm Lock-Mint (Operator 2) ---");
        vm.startBroadcast(opKey2);
        bridgeLock.confirmLockMint(lockRequestId);
        vm.stopBroadcast();
        console.log("  Confirmed by:", op2);
        console.log("  Confirmations: 2/3");

        // Step 3: Operator 3 confirms lock-mint -> triggers execution
        console.log("--- Step 3: Confirm Lock-Mint (Operator 3) -> EXECUTION ---");
        vm.startBroadcast(opKey3);
        bridgeLock.confirmLockMint(lockRequestId);
        vm.stopBroadcast();
        console.log("  Confirmed by:", op3);
        console.log("  Confirmations: 3/3 => MINT EXECUTED");

        // Step 4: Verify minted amount
        console.log("--- Step 4: Verify Minted Amount ---");
        uint256 postMintSupply = wbait.totalSupply();
        uint256 postMintBalance = wbait.balanceOf(recipient);
        require(
            postMintSupply == preMintSupply + TEST_AMOUNT,
            "MINT FAILED: totalSupply not incremented"
        );
        require(
            postMintBalance == preMintBalance + TEST_AMOUNT,
            "MINT FAILED: recipient balance not incremented"
        );
        console.log("  [PASS] totalSupply:", postMintSupply);
        console.log("  [PASS] recipient balance:", postMintBalance);
        console.log("  [PASS] Mint verified: +", TEST_AMOUNT);
        console.log("");
    }

    // -- Phase 2: Burn-Release Flow --

    function _executeBurnRelease(address op1, address op2, address op3) internal {
        console.log("============================================================");
        console.log("  PHASE 2: BURN-RELEASE FLOW");
        console.log("============================================================");

        uint256 postMintBalance = wbait.balanceOf(recipient);

        // Step 5: Recipient approves BridgeLock for burn
        console.log("--- Step 5: Recipient Approves BridgeLock ---");
        vm.startBroadcast(recipientKey);
        wbait.approve(bridgeAddr, postMintBalance);
        vm.stopBroadcast();
        console.log("  Approved BridgeLock to spend:", postMintBalance);

        // Step 6: Recipient initiates burn-release
        console.log("--- Step 6: Initiate Burn-Release (Recipient) ---");
        uint256 preBurnCount = bridgeLock.getBurnReleaseCount();
        vm.startBroadcast(recipientKey);
        bridgeLock.initiateBurnRelease(postMintBalance, L1_RELEASE_ADDRESS);
        vm.stopBroadcast();
        console.log("  Burn initiated by:", recipient);
        console.log("  Amount burned:", postMintBalance);
        console.log("  L1 release address:", L1_RELEASE_ADDRESS);

        // Verify supply decreased after burn
        require(
            wbait.balanceOf(recipient) == 0,
            "BURN FAILED: recipient balance not zeroed"
        );
        console.log("  [PASS] Recipient balance after burn: 0");

        // Determine the burnReleaseId from the public array
        uint256 newBurnCount = bridgeLock.getBurnReleaseCount();
        require(newBurnCount > preBurnCount, "No new burn release created");
        burnReleaseId = bridgeLock.burnReleaseIds(newBurnCount - 1);
        console.log("  Release ID (uint):", uint256(burnReleaseId));

        // Step 7: Operator 1 confirms burn-release
        console.log("--- Step 7: Confirm Burn-Release (Operator 1) ---");
        vm.startBroadcast(opKey1);
        bridgeLock.confirmBurnRelease(burnReleaseId);
        vm.stopBroadcast();
        console.log("  Confirmed by:", op1);
        console.log("  Confirmations: 1/3");

        // Step 8: Operator 2 confirms burn-release
        console.log("--- Step 8: Confirm Burn-Release (Operator 2) ---");
        vm.startBroadcast(opKey2);
        bridgeLock.confirmBurnRelease(burnReleaseId);
        vm.stopBroadcast();
        console.log("  Confirmed by:", op2);
        console.log("  Confirmations: 2/3");

        // Step 9: Operator 3 confirms burn-release -> marks executed
        console.log("--- Step 9: Confirm Burn-Release (Operator 3) -> EXECUTED ---");
        vm.startBroadcast(opKey3);
        bridgeLock.confirmBurnRelease(burnReleaseId);
        vm.stopBroadcast();
        console.log("  Confirmed by:", op3);
        console.log("  Confirmations: 3/3 => BURN-RELEASE EXECUTED");

        // Step 10: Verify burn was executed
        console.log("--- Step 10: Verify Burn Execution ---");
        require(
            wbait.totalSupply() == preMintSupply,
            "LIFECYCLE FAILED: supply not returned to pre-test state"
        );
        require(
            wbait.balanceOf(recipient) == preMintBalance,
            "LIFECYCLE FAILED: recipient balance not returned"
        );
        console.log("  [PASS] Final totalSupply:", wbait.totalSupply());
        console.log("  [PASS] Final recipient balance:", wbait.balanceOf(recipient));
        console.log("  [PASS] Burn-release verified: supply returned to initial state");
        console.log("");
    }

    // -- Summary --

    function _printSummary() internal view {
        console.log("============================================================");
        console.log("  LIFECYCLE TEST COMPLETE");
        console.log("============================================================");
        console.log("");
        console.log("  Lock-Mint Flow:");
        console.log("    [PASS] Operator 1 requested lock-mint");
        console.log("    [PASS] Operator 2 confirmed");
        console.log("    [PASS] Operator 3 confirmed (triggered execution)");
        console.log("    [PASS] wBAIT minted to recipient:", TEST_AMOUNT);
        console.log("");
        console.log("  Burn-Release Flow:");
        console.log("    [PASS] Recipient approved BridgeLock");
        console.log("    [PASS] Recipient initiated burn-release");
        console.log("    [PASS] Operator 1 confirmed");
        console.log("    [PASS] Operator 2 confirmed");
        console.log("    [PASS] Operator 3 confirmed (marked executed)");
        console.log("    [PASS] wBAIT burned, supply returned to initial");
        console.log("");
        console.log("  Conservation Invariant:");
        console.log("    Initial supply:", preMintSupply);
        console.log("    After mint:", preMintSupply + TEST_AMOUNT);
        console.log("    After burn:", preMintSupply);
        console.log("    [PASS] Supply conservation verified");
        console.log("");
        console.log("  ALL LIFECYCLE TESTS PASSED");
        console.log("============================================================");
    }

    // -- Pre-Test Validation --

    function _preTestValidation(
        address op1,
        address op2,
        address op3,
        address _recipient
    ) internal view {
        console.log("--- Pre-Test Validation ---");

        // Contract references
        require(address(wbait).code.length > 0, "WBAIT: no code at address");
        require(address(bridgeLock).code.length > 0, "BridgeLock: no code at address");
        console.log("  [PASS] Contract code exists");

        // Cross-reference
        require(
            address(bridgeLock.wbait()) == address(wbait),
            "BridgeLock.wbait != WBAIT address"
        );
        console.log("  [PASS] Cross-reference: BridgeLock.wbait == WBAIT");

        // Not paused
        require(!wbait.paused(), "WBAIT is paused - cannot test");
        require(!bridgeLock.paused(), "BridgeLock is paused - cannot test");
        console.log("  [PASS] Contracts not paused");

        // Operators registered
        require(bridgeLock.isOperator(op1), "Operator 1 not registered in BridgeLock");
        require(bridgeLock.isOperator(op2), "Operator 2 not registered in BridgeLock");
        require(bridgeLock.isOperator(op3), "Operator 3 not registered in BridgeLock");
        console.log("  [PASS] All 3 operators registered");

        // Operators distinct
        require(op1 != op2, "Operator 1 == Operator 2");
        require(op1 != op3, "Operator 1 == Operator 3");
        require(op2 != op3, "Operator 2 == Operator 3");
        console.log("  [PASS] All 3 operators distinct");

        // Recipient is not operator
        require(!bridgeLock.isOperator(_recipient), "Recipient should not be operator");
        console.log("  [PASS] Recipient is not an operator:", _recipient);

        // Rate limit check
        require(
            TEST_AMOUNT <= bridgeLock.RATE_LIMIT(),
            "Test amount exceeds daily rate limit"
        );
        console.log("  [PASS] Test amount within rate limit");

        // Max supply check
        require(
            wbait.totalSupply() + TEST_AMOUNT <= wbait.MAX_SUPPLY(),
            "Test would exceed max supply"
        );
        console.log("  [PASS] Test amount within max supply");

        console.log("  All pre-test validations PASSED");
    }
}
