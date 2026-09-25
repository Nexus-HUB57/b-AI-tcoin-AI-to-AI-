// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/**
 * @title TestBridgeLifecycleAnvil - Full Bridge Lifecycle Test on Anvil
 * @notice Deploys and tests the complete BAIT system on Anvil (Foundry's local EVM).
 *         ZERO cost alternative to Sepolia — no faucet, no RPC provider needed.
 *
 * Tests Performed:
 *   1. Deploy WBAIT + BridgeLock with address prediction
 *   2. Verify deployment integrity (all invariants)
 *   3. Lock-Mint flow (3-of-5 operator confirmation → mint)
 *   4. Burn-Release flow (user burn → 3-of-5 confirmation → release)
 *   5. Supply conservation invariant (supply returns to initial after full cycle)
 *   6. Operator update with timelock (propose → wait 24h → execute)
 *   7. Operator update rejection before timelock
 *   8. Operator update cancellation
 *   9. Emergency pause (owner pauses both contracts)
 *  10. Emergency unpause (owner unpauses both contracts)
 *  11. Post-unpause lifecycle still works
 *  12. Final invariant verification
 *
 * Usage:
 *   # Terminal 1: Start Anvil
 *   anvil
 *
 *   # Terminal 2: Run lifecycle test
 *   forge script script/TestBridgeLifecycleAnvil.s.sol \
 *     --rpc-url http://127.0.0.1:8545 \
 *     --broadcast -vvvv
 *
 * All keys are hardcoded — no environment variables needed.
 */
contract TestBridgeLifecycleAnvil is Script {
    // ── Anvil Default Private Keys ──
    uint256 constant DEPLOYER_KEY = 0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba; // Account 5
    uint256 constant OP_KEY_0     = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80; // Account 0
    uint256 constant OP_KEY_1     = 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d; // Account 1
    uint256 constant OP_KEY_2     = 0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a; // Account 2
    uint256 constant OP_KEY_3     = 0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6; // Account 3
    uint256 constant OP_KEY_4     = 0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a; // Account 4
    uint256 constant RECIPIENT_KEY = 0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e; // Account 6

    // ── Anvil Default Addresses ──
    address constant OP_0 = 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266;
    address constant OP_1 = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;
    address constant OP_2 = 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC;
    address constant OP_3 = 0x90F79bf6EB2c4f870365E785982E1f101E93b906;
    address constant OP_4 = 0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65;

    // ── Test Parameters ──
    uint256 constant MAX_SUPPLY = 21_000_000 * 10**8;
    uint256 constant TEST_AMOUNT = 1 * 10**8; // 1 wBAIT in sAI'toshi
    string constant L1_RELEASE_ADDRESS = "b1test_anvil_lifecycle_addr";

    // ── State ──
    WBAIT public wbait;
    BridgeLock public bridgeLock;
    address public deployer;
    address public recipient;
    bytes32 public lockRequestId;
    bytes32 public burnReleaseId;
    uint256 public initialSupply;
    uint256 public passCount;
    uint256 public failCount;

    function run() external {
        deployer = vm.addr(DEPLOYER_KEY);
        recipient = vm.addr(RECIPIENT_KEY);

        console.log("============================================================");
        console.log("  BAIT Full Bridge Lifecycle Test (Anvil)");
        console.log("  Network Chain ID:", block.chainid);
        console.log("============================================================");
        console.log("Deployer: ", deployer);
        console.log("Recipient:", recipient);
        console.log("Test Amount:", TEST_AMOUNT);
        console.log("");

        // ── TEST 1: Deploy WBAIT + BridgeLock ──
        _testDeploy();

        // ── TEST 2: Verify Deployment Integrity ──
        _testDeploymentIntegrity();

        // ── TEST 3: Full Lock-Mint → Burn-Release Cycle ──
        _testLockMintBurnRelease();

        // ── TEST 4: Operator Update with Timelock ──
        _testOperatorUpdateTimelock();

        // ── TEST 5: Emergency Pause/Unpause ──
        _testEmergencyPauseUnpause();

        // ── TEST 6: Post-Unpause Lifecycle ──
        _testPostUnpauseLifecycle();

        // ── TEST 7: Final Invariant Verification ──
        _testFinalInvariants();

        // ── SUMMARY ──
        _printSummary();
    }

    // ─────────────────────────────────────────────
    // TEST 1: Deploy WBAIT + BridgeLock
    // ─────────────────────────────────────────────

    function _testDeploy() internal {
        console.log("============================================================");
        console.log("  TEST 1: Deploy WBAIT + BridgeLock");
        console.log("============================================================");

        address[5] memory operators = [OP_0, OP_1, OP_2, OP_3, OP_4];

        // Verify deployer is not an operator
        for (uint256 i = 0; i < 5; i++) {
            require(operators[i] != deployer, "Deployer cannot be operator");
        }
        console.log("  [PASS] Deployer is not an operator");

        // Verify recipient is not an operator
        for (uint256 i = 0; i < 5; i++) {
            require(operators[i] != recipient, "Recipient cannot be operator");
        }
        console.log("  [PASS] Recipient is not an operator");

        vm.startBroadcast(DEPLOYER_KEY);

        // Predict BridgeLock address
        uint256 deployerNonce = vm.getNonce(deployer);
        address predictedBridgeLock = vm.computeCreateAddress(deployer, deployerNonce + 1);
        console.log("  Deployer nonce:", deployerNonce);
        console.log("  Predicted BridgeLock:", predictedBridgeLock);

        // Deploy WBAIT; the deployer is the local timelock authority.
        wbait = new WBAIT(predictedBridgeLock, deployer);
        console.log("  WBAIT deployed at:", address(wbait));

        // Deploy BridgeLock
        bridgeLock = new BridgeLock(address(wbait), deployer, operators);
        console.log("  BridgeLock deployed at:", address(bridgeLock));

        // Verify address prediction
        require(
            address(bridgeLock) == predictedBridgeLock,
            "BridgeLock address prediction failed!"
        );
        console.log("  [PASS] BridgeLock address matches prediction");

        vm.stopBroadcast();

        initialSupply = wbait.totalSupply();
        console.log("  Initial supply:", initialSupply);
        console.log("");
    }

    // ─────────────────────────────────────────────
    // TEST 2: Verify Deployment Integrity
    // ─────────────────────────────────────────────

    function _testDeploymentIntegrity() internal view {
        console.log("============================================================");
        console.log("  TEST 2: Verify Deployment Integrity");
        console.log("============================================================");

        // WBAIT checks
        require(keccak256(bytes(wbait.name())) == keccak256(bytes("Wrapped bAIitcoin")), "WBAIT: wrong name");
        console.log("  [PASS] WBAIT.name() == 'Wrapped bAIitcoin'");

        require(keccak256(bytes(wbait.symbol())) == keccak256(bytes("wBAIT")), "WBAIT: wrong symbol");
        console.log("  [PASS] WBAIT.symbol() == 'wBAIT'");

        require(wbait.decimals() == 8, "WBAIT: wrong decimals");
        console.log("  [PASS] WBAIT.decimals() == 8");

        require(wbait.MAX_SUPPLY() == MAX_SUPPLY, "WBAIT: wrong max supply");
        console.log("  [PASS] WBAIT.MAX_SUPPLY() == 21,000,000 * 10^8");

        require(wbait.totalSupply() == 0, "WBAIT: non-zero initial supply");
        console.log("  [PASS] WBAIT.totalSupply() == 0");

        require(wbait.paused() == false, "WBAIT: initially paused");
        console.log("  [PASS] WBAIT.paused() == false");

        require(wbait.bridgeLock() == address(bridgeLock), "WBAIT: wrong bridgeLock ref");
        console.log("  [PASS] WBAIT.bridgeLock() == BridgeLock address");

        // BridgeLock checks
        require(address(bridgeLock.wbait()) == address(wbait), "BridgeLock: wrong wbait ref");
        console.log("  [PASS] BridgeLock.wbait() == WBAIT address");

        require(bridgeLock.REQUIRED_CONFIRMATIONS() == 3, "BridgeLock: wrong threshold");
        console.log("  [PASS] BridgeLock.REQUIRED_CONFIRMATIONS() == 3");

        require(bridgeLock.NUM_OPERATORS() == 5, "BridgeLock: wrong operator count");
        console.log("  [PASS] BridgeLock.NUM_OPERATORS() == 5");

        require(bridgeLock.RATE_LIMIT() == 100_000 * 10**8, "BridgeLock: wrong rate limit");
        console.log("  [PASS] BridgeLock.RATE_LIMIT() == 100,000 * 10^8");

        require(bridgeLock.TIMELOCK_DURATION() == 24 hours, "BridgeLock: wrong timelock");
        console.log("  [PASS] BridgeLock.TIMELOCK_DURATION() == 86400");

        require(bridgeLock.paused() == false, "BridgeLock: initially paused");
        console.log("  [PASS] BridgeLock.paused() == false");

        // Operator registration
        address[5] memory ops = [OP_0, OP_1, OP_2, OP_3, OP_4];
        for (uint256 i = 0; i < 5; i++) {
            require(bridgeLock.operators(i) == ops[i], "Operator mismatch");
            require(bridgeLock.isOperator(ops[i]), "Operator not registered");
        }
        console.log("  [PASS] All 5 operators correctly registered");

        // Conservation invariant
        require(wbait.totalSupply() == 0, "CONSERVATION INVARIANT VIOLATED at deployment");
        console.log("  [PASS] Conservation invariant: totalSupply == 0");
        console.log("");
    }

    // ─────────────────────────────────────────────
    // TEST 3: Full Lock-Mint → Burn-Release Cycle
    // ─────────────────────────────────────────────

    function _testLockMintBurnRelease() internal {
        console.log("============================================================");
        console.log("  TEST 3: Lock-Mint -> Burn-Release Lifecycle");
        console.log("============================================================");

        uint256 preSupply = wbait.totalSupply();
        uint256 preBalance = wbait.balanceOf(recipient);

        // ── Phase 1: Lock-Mint ──
        console.log("--- Phase 1: Lock-Mint ---");

        lockRequestId = keccak256(abi.encodePacked(
            "ANVIL_LIFECYCLE_TEST",
            block.timestamp,
            bridgeLock.getLockRequestCount()
        ));
        bytes32 l1TxId = keccak256("mock_l1_lock_tx_for_anvil_test");

        // Operator 1 requests (auto-confirms)
        vm.startBroadcast(OP_KEY_0);
        bridgeLock.requestLockMint(lockRequestId, l1TxId, recipient, TEST_AMOUNT);
        vm.stopBroadcast();
        console.log("  [PASS] Operator 0 requested lock-mint (1/3)");

        // Operator 2 confirms
        vm.startBroadcast(OP_KEY_1);
        bridgeLock.confirmLockMint(lockRequestId);
        vm.stopBroadcast();
        console.log("  [PASS] Operator 1 confirmed (2/3)");

        // Operator 3 confirms → execution
        vm.startBroadcast(OP_KEY_2);
        bridgeLock.confirmLockMint(lockRequestId);
        vm.stopBroadcast();
        console.log("  [PASS] Operator 2 confirmed (3/3) => MINT EXECUTED");

        // Verify mint
        require(wbait.totalSupply() == preSupply + TEST_AMOUNT, "MINT: supply not incremented");
        require(wbait.balanceOf(recipient) == preBalance + TEST_AMOUNT, "MINT: recipient balance not incremented");
        console.log("  [PASS] Mint verified: +", TEST_AMOUNT, "to recipient");

        // ── Phase 2: Burn-Release ──
        console.log("--- Phase 2: Burn-Release ---");

        uint256 postMintBalance = wbait.balanceOf(recipient);

        // Recipient approves BridgeLock
        vm.startBroadcast(RECIPIENT_KEY);
        wbait.approve(address(bridgeLock), postMintBalance);
        vm.stopBroadcast();
        console.log("  [PASS] Recipient approved BridgeLock");

        // Recipient initiates burn
        uint256 preBurnCount = bridgeLock.getBurnReleaseCount();
        vm.startBroadcast(RECIPIENT_KEY);
        bridgeLock.initiateBurnRelease(postMintBalance, L1_RELEASE_ADDRESS);
        vm.stopBroadcast();
        console.log("  [PASS] Recipient initiated burn-release");

        // Verify burn
        require(wbait.balanceOf(recipient) == 0, "BURN: recipient balance not zeroed");
        console.log("  [PASS] Recipient balance after burn: 0");

        // Get burnReleaseId
        uint256 newBurnCount = bridgeLock.getBurnReleaseCount();
        require(newBurnCount > preBurnCount, "No new burn release created");
        burnReleaseId = bridgeLock.burnReleaseIds(newBurnCount - 1);

        // Operator 1 confirms
        vm.startBroadcast(OP_KEY_0);
        bridgeLock.confirmBurnRelease(burnReleaseId);
        vm.stopBroadcast();
        console.log("  [PASS] Operator 0 confirmed burn-release (1/3)");

        // Operator 2 confirms
        vm.startBroadcast(OP_KEY_1);
        bridgeLock.confirmBurnRelease(burnReleaseId);
        vm.stopBroadcast();
        console.log("  [PASS] Operator 1 confirmed burn-release (2/3)");

        // Operator 3 confirms → executed
        vm.startBroadcast(OP_KEY_2);
        bridgeLock.confirmBurnRelease(burnReleaseId);
        vm.stopBroadcast();
        console.log("  [PASS] Operator 2 confirmed burn-release (3/3) => EXECUTED");

        // Verify conservation
        require(wbait.totalSupply() == preSupply, "LIFECYCLE: supply not returned to initial");
        require(wbait.balanceOf(recipient) == preBalance, "LIFECYCLE: recipient balance not returned");
        console.log("  [PASS] Supply conservation: totalSupply == initialSupply");
        console.log("  [PASS] Recipient balance == initial balance");
        console.log("");
    }

    // ─────────────────────────────────────────────
    // TEST 4: Operator Update with Timelock
    // ─────────────────────────────────────────────

    function _testOperatorUpdateTimelock() internal {
        console.log("============================================================");
        console.log("  TEST 4: Operator Update with Timelock");
        console.log("============================================================");

        address newOp = vm.addr(RECIPIENT_KEY); // Use recipient address as new operator candidate
        address oldOp = bridgeLock.operators(0);

        // 4a: Propose operator update
        vm.startBroadcast(DEPLOYER_KEY);
        bridgeLock.proposeOperatorUpdate(0, newOp);
        vm.stopBroadcast();
        console.log("  [PASS] Proposed operator update: slot 0, new operator:", newOp);

        // Verify pending update
        (uint256 idx, address proposed, uint256 proposedAt, bool active) = bridgeLock.pendingOperatorUpdate();
        require(idx == 0, "Wrong pending index");
        require(proposed == newOp, "Wrong pending operator");
        require(active == true, "Pending update not active");
        console.log("  [PASS] Pending update verified: index=", idx, "active=", active);

        // 4b: Try to execute before timelock expires (should fail)
        vm.startBroadcast(DEPLOYER_KEY);
        (bool success,) = address(bridgeLock).call(
            abi.encodeWithSelector(bridgeLock.executeOperatorUpdate.selector)
        );
        vm.stopBroadcast();
        require(success == false, "Should not execute before timelock expires");
        console.log("  [PASS] Execute before timelock: correctly rejected");

        // 4c: Cancel the operator update
        vm.startBroadcast(DEPLOYER_KEY);
        bridgeLock.cancelOperatorUpdate();
        vm.stopBroadcast();

        (,,, bool activeAfterCancel) = bridgeLock.pendingOperatorUpdate();
        require(activeAfterCancel == false, "Pending update should be cancelled");
        console.log("  [PASS] Operator update cancelled successfully");

        // 4d: Propose again and execute after timelock
        vm.startBroadcast(DEPLOYER_KEY);
        bridgeLock.proposeOperatorUpdate(0, newOp);
        vm.stopBroadcast();
        console.log("  [PASS] Re-proposed operator update");

        // Warp time forward past timelock (24 hours + 1 second)
        vm.warp(block.timestamp + 24 hours + 1);
        console.log("  [INFO] Warped time: +24h 1s past timelock");

        vm.startBroadcast(DEPLOYER_KEY);
        bridgeLock.executeOperatorUpdate();
        vm.stopBroadcast();

        // Verify operator was replaced
        require(bridgeLock.operators(0) == newOp, "Operator not replaced");
        require(bridgeLock.isOperator(newOp) == true, "New operator not registered");
        require(bridgeLock.isOperator(oldOp) == false, "Old operator still registered");
        console.log("  [PASS] Operator replaced: slot 0 now", newOp);

        (,,, bool activeAfterExec) = bridgeLock.pendingOperatorUpdate();
        require(activeAfterExec == false, "Pending update should be cleared");
        console.log("  [PASS] Pending update cleared after execution");

        // Restore original operator for subsequent tests
        vm.startBroadcast(DEPLOYER_KEY);
        bridgeLock.proposeOperatorUpdate(0, oldOp);
        vm.stopBroadcast();

        vm.warp(block.timestamp + 24 hours + 1);

        vm.startBroadcast(DEPLOYER_KEY);
        bridgeLock.executeOperatorUpdate();
        vm.stopBroadcast();

        require(bridgeLock.operators(0) == oldOp, "Operator not restored");
        require(bridgeLock.isOperator(oldOp) == true, "Old operator not re-registered");
        console.log("  [PASS] Original operator restored for subsequent tests");
        console.log("");
    }

    // ─────────────────────────────────────────────
    // TEST 5: Emergency Pause/Unpause
    // ─────────────────────────────────────────────

    function _testEmergencyPauseUnpause() internal {
        console.log("============================================================");
        console.log("  TEST 5: Emergency Pause/Unpause");
        console.log("============================================================");

        // First, mint some tokens to recipient so we can test WBAIT transfer pause
        bytes32 preMintRequestId = keccak256(abi.encodePacked(
            "PRE_PAUSE_MINT", block.timestamp, bridgeLock.getLockRequestCount()
        ));
        vm.startBroadcast(OP_KEY_0);
        bridgeLock.requestLockMint(preMintRequestId, keccak256("pre_pause_l1"), recipient, TEST_AMOUNT);
        vm.stopBroadcast();
        vm.startBroadcast(OP_KEY_1);
        bridgeLock.confirmLockMint(preMintRequestId);
        vm.stopBroadcast();
        vm.startBroadcast(OP_KEY_2);
        bridgeLock.confirmLockMint(preMintRequestId);
        vm.stopBroadcast();
        console.log("  [INFO] Pre-pause mint: tokens available for transfer test");

        // 5a: Pause WBAIT
        vm.startBroadcast(DEPLOYER_KEY);
        wbait.pause();
        vm.stopBroadcast();
        require(wbait.paused() == true, "WBAIT not paused");
        console.log("  [PASS] WBAIT paused by owner");

        // 5b: Verify WBAIT transfer is blocked while paused
        vm.startBroadcast(RECIPIENT_KEY);
        (bool transferSuccess,) = address(wbait).call(
            abi.encodeWithSelector(wbait.transfer.selector, deployer, TEST_AMOUNT)
        );
        vm.stopBroadcast();
        require(transferSuccess == false, "Transfer should fail while WBAIT paused");
        console.log("  [PASS] WBAIT transfer correctly rejected while paused");

        // 5c: Verify mint through BridgeLock also fails when WBAIT is paused
        // (WBAIT.mint() has whenNotPaused modifier)
        bytes32 pausedMintRequestId = keccak256(abi.encodePacked(
            "PAUSED_MINT_TEST", block.timestamp
        ));
        vm.startBroadcast(OP_KEY_0);
        bridgeLock.requestLockMint(pausedMintRequestId, keccak256("paused_mint_l1"), recipient, TEST_AMOUNT);
        vm.stopBroadcast();
        vm.startBroadcast(OP_KEY_1);
        bridgeLock.confirmLockMint(pausedMintRequestId);
        vm.stopBroadcast();
        vm.startBroadcast(OP_KEY_2);
        (bool mintSuccess,) = address(bridgeLock).call(
            abi.encodeWithSelector(bridgeLock.confirmLockMint.selector, pausedMintRequestId)
        );
        vm.stopBroadcast();
        require(mintSuccess == false, "Mint should fail while WBAIT paused");
        console.log("  [PASS] Lock-mint correctly rejected while WBAIT paused");

        // 5d: Unpause WBAIT
        vm.startBroadcast(DEPLOYER_KEY);
        wbait.unpause();
        vm.stopBroadcast();
        require(wbait.paused() == false, "WBAIT still paused");
        console.log("  [PASS] WBAIT unpaused by owner");

        // 5e: Pause BridgeLock (independent of WBAIT)
        vm.startBroadcast(DEPLOYER_KEY);
        bridgeLock.pause();
        vm.stopBroadcast();
        require(bridgeLock.paused() == true, "BridgeLock not paused");
        console.log("  [PASS] BridgeLock paused by owner");

        // 5f: Verify BridgeLock operations are blocked while paused
        bytes32 pausedRequestId = keccak256(abi.encodePacked("BL_PAUSED_TEST", block.timestamp));
        vm.startBroadcast(OP_KEY_0);
        (bool blSuccess,) = address(bridgeLock).call(
            abi.encodeWithSelector(
                bridgeLock.requestLockMint.selector,
                pausedRequestId,
                keccak256("paused_l1_tx"),
                recipient,
                TEST_AMOUNT
            )
        );
        vm.stopBroadcast();
        require(blSuccess == false, "Lock-mint should fail while BridgeLock paused");
        console.log("  [PASS] Lock-mint correctly rejected while BridgeLock paused");

        // 5g: Unpause BridgeLock
        vm.startBroadcast(DEPLOYER_KEY);
        bridgeLock.unpause();
        vm.stopBroadcast();
        require(bridgeLock.paused() == false, "BridgeLock still paused");
        console.log("  [PASS] BridgeLock unpaused by owner");

        // Clean up: burn the pre-minted tokens to restore supply
        uint256 recipientBal = wbait.balanceOf(recipient);
        vm.startBroadcast(RECIPIENT_KEY);
        wbait.approve(address(bridgeLock), recipientBal);
        bridgeLock.initiateBurnRelease(recipientBal, L1_RELEASE_ADDRESS);
        vm.stopBroadcast();

        uint256 bc = bridgeLock.getBurnReleaseCount();
        bytes32 cleanupId = bridgeLock.burnReleaseIds(bc - 1);
        vm.startBroadcast(OP_KEY_0);
        bridgeLock.confirmBurnRelease(cleanupId);
        vm.stopBroadcast();
        vm.startBroadcast(OP_KEY_1);
        bridgeLock.confirmBurnRelease(cleanupId);
        vm.stopBroadcast();
        vm.startBroadcast(OP_KEY_2);
        bridgeLock.confirmBurnRelease(cleanupId);
        vm.stopBroadcast();
        console.log("  [PASS] Pause test cleanup: burned pre-minted tokens");
        console.log("");
    }

    // ─────────────────────────────────────────────
    // TEST 6: Post-Unpause Lifecycle
    // ─────────────────────────────────────────────

    function _testPostUnpauseLifecycle() internal {
        console.log("============================================================");
        console.log("  TEST 6: Post-Unpause Lifecycle");
        console.log("============================================================");

        // Full lock-mint -> burn-release cycle after pause/unpause
        uint256 preSupply = wbait.totalSupply();

        bytes32 postUnpauseRequestId = keccak256(abi.encodePacked(
            "POST_UNPAUSE_TEST",
            block.timestamp,
            bridgeLock.getLockRequestCount()
        ));

        vm.startBroadcast(OP_KEY_0);
        bridgeLock.requestLockMint(postUnpauseRequestId, keccak256("post_unpause_l1"), recipient, TEST_AMOUNT);
        vm.stopBroadcast();
        vm.startBroadcast(OP_KEY_1);
        bridgeLock.confirmLockMint(postUnpauseRequestId);
        vm.stopBroadcast();
        vm.startBroadcast(OP_KEY_2);
        bridgeLock.confirmLockMint(postUnpauseRequestId);
        vm.stopBroadcast();
        console.log("  [PASS] Post-unpause lock-mint executed");

        require(wbait.totalSupply() == preSupply + TEST_AMOUNT, "Post-unpause mint failed");
        console.log("  [PASS] Post-unpause supply increased correctly");

        // Burn-release
        uint256 bal = wbait.balanceOf(recipient);
        vm.startBroadcast(RECIPIENT_KEY);
        wbait.approve(address(bridgeLock), bal);
        bridgeLock.initiateBurnRelease(bal, L1_RELEASE_ADDRESS);
        vm.stopBroadcast();

        uint256 bc = bridgeLock.getBurnReleaseCount();
        bytes32 pid = bridgeLock.burnReleaseIds(bc - 1);

        vm.startBroadcast(OP_KEY_0);
        bridgeLock.confirmBurnRelease(pid);
        vm.stopBroadcast();
        vm.startBroadcast(OP_KEY_1);
        bridgeLock.confirmBurnRelease(pid);
        vm.stopBroadcast();
        vm.startBroadcast(OP_KEY_2);
        bridgeLock.confirmBurnRelease(pid);
        vm.stopBroadcast();
        console.log("  [PASS] Post-unpause burn-release executed");

        require(wbait.totalSupply() == preSupply, "Post-unpause conservation violated");
        console.log("  [PASS] Post-unpause supply conservation verified");
        console.log("");
    }

    // ─────────────────────────────────────────────
    // TEST 7: Final Invariant Verification
    // ─────────────────────────────────────────────

    function _testFinalInvariants() internal view {
        console.log("============================================================");
        console.log("  TEST 7: Final Invariant Verification");
        console.log("============================================================");

        // Conservation: supply should be back to initial
        require(wbait.totalSupply() == initialSupply, "FINAL: supply != initial");
        console.log("  [PASS] totalSupply == initialSupply (", initialSupply, ")");

        // Cross-reference integrity
        require(wbait.bridgeLock() == address(bridgeLock), "FINAL: cross-ref broken WBAIT->BridgeLock");
        require(address(bridgeLock.wbait()) == address(wbait), "FINAL: cross-ref broken BridgeLock->WBAIT");
        console.log("  [PASS] Cross-reference integrity maintained");

        // Not paused
        require(wbait.paused() == false, "FINAL: WBAIT still paused");
        require(bridgeLock.paused() == false, "FINAL: BridgeLock still paused");
        console.log("  [PASS] Both contracts unpaused");

        // All operators registered
        address[5] memory ops = [OP_0, OP_1, OP_2, OP_3, OP_4];
        for (uint256 i = 0; i < 5; i++) {
            require(bridgeLock.operators(i) == ops[i], "FINAL: operator mismatch");
            require(bridgeLock.isOperator(ops[i]), "FINAL: operator not registered");
        }
        console.log("  [PASS] All 5 operators still correctly registered");

        // Contract constants unchanged
        require(wbait.MAX_SUPPLY() == MAX_SUPPLY, "FINAL: MAX_SUPPLY changed");
        require(bridgeLock.REQUIRED_CONFIRMATIONS() == 3, "FINAL: threshold changed");
        require(bridgeLock.NUM_OPERATORS() == 5, "FINAL: operator count changed");
        require(bridgeLock.RATE_LIMIT() == 100_000 * 10**8, "FINAL: rate limit changed");
        require(bridgeLock.TIMELOCK_DURATION() == 24 hours, "FINAL: timelock changed");
        console.log("  [PASS] All contract constants unchanged");

        // Ownership
        require(wbait.owner() == deployer, "FINAL: WBAIT owner changed");
        require(bridgeLock.owner() == deployer, "FINAL: BridgeLock owner changed");
        console.log("  [PASS] Ownership unchanged (deployer)");

        // No pending operator updates
        (,,, bool activePending) = bridgeLock.pendingOperatorUpdate();
        require(activePending == false, "FINAL: pending operator update exists");
        console.log("  [PASS] No pending operator updates");
        console.log("");
    }

    // ─────────────────────────────────────────────
    // SUMMARY
    // ─────────────────────────────────────────────

    function _printSummary() internal view {
        console.log("============================================================");
        console.log("  ANVIL LIFECYCLE TEST COMPLETE");
        console.log("============================================================");
        console.log("");
        console.log("  Deployed Contracts:");
        console.log("    WBAIT:     ", address(wbait));
        console.log("    BridgeLock:", address(bridgeLock));
        console.log("    Owner:     ", deployer);
        console.log("");
        console.log("  Test Results:");
        console.log("    [PASS] TEST 1: Deploy WBAIT + BridgeLock");
        console.log("    [PASS] TEST 2: Deployment Integrity Verification");
        console.log("    [PASS] TEST 3: Lock-Mint -> Burn-Release Lifecycle");
        console.log("    [PASS] TEST 4: Operator Update with Timelock");
        console.log("    [PASS] TEST 5: Emergency Pause/Unpause");
        console.log("    [PASS] TEST 6: Post-Unpause Lifecycle");
        console.log("    [PASS] TEST 7: Final Invariant Verification");
        console.log("");
        console.log("  Conservation Invariant:");
        console.log("    Initial supply:", initialSupply);
        console.log("    Final supply:  ", wbait.totalSupply());
        console.log("    [PASS] Supply conservation verified");
        console.log("");
        console.log("  ALL LIFECYCLE TESTS PASSED ON ANVIL (FREE LOCAL TESTNET)");
        console.log("============================================================");
    }
}
