// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/**
 * @title DeployBAITAnvil - Anvil Local Testnet Deployment Script
 * @notice Free local deployment script for BAIT system on Anvil (Foundry's local EVM).
 *         Resolves the WBAIT↔BridgeLock circular dependency via address prediction.
 *         Includes pre/post-deployment validations, ownership transfer placeholder,
 *         and comprehensive logging.
 *
 *         This is a FREE alternative to Sepolia testnet — no faucet, no RPC provider needed.
 *
 * Usage:
 *   # Terminal 1: Start Anvil
 *   anvil
 *
 *   # Terminal 2: Deploy
 *   forge script script/DeployBAITAnvil.s.sol \
 *     --rpc-url http://127.0.0.1:8545 \
 *     --broadcast -vvvv
 *
 * Anvil Default Accounts (chain ID 31337):
 *   Deployer:   0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc  (Account 5, NOT an operator)
 *   Operator 0: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266  (Account 0)
 *   Operator 1: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8  (Account 1)
 *   Operator 2: 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC  (Account 2)
 *   Operator 3: 0x90F79bf6EB2c4f870365E785982E1f101E93b906  (Account 3)
 *   Operator 4: 0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65  (Account 4)
 *
 * [!] These are LOCAL TESTNET ONLY. Production uses HSM-derived operator keys.
 */
contract DeployBAITAnvil is Script {
    // ── Constants ──
    uint256 constant MAX_SUPPLY = 21_000_000 * 10**8;

    // Anvil default private keys (hardcoded — no env vars needed)
    uint256 constant DEPLOYER_KEY = 0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba; // Account 5

    // Deterministic Anvil operator addresses (Foundry default accounts 0-4)
    address constant OP_0 = 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266;
    address constant OP_1 = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;
    address constant OP_2 = 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC;
    address constant OP_3 = 0x90F79bf6EB2c4f870365E785982E1f101E93b906;
    address constant OP_4 = 0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65;

    // ── State ──
    WBAIT public wbait;
    BridgeLock public bridgeLock;
    address public multisig;

    function run() external {
        // ── Load Deployer ──
        address deployer = vm.addr(DEPLOYER_KEY);

        address[5] memory operators = [OP_0, OP_1, OP_2, OP_3, OP_4];

        // Multisig defaults to deployer for local testnet
        multisig = deployer;

        // ── Pre-Deployment Checks ──
        _preDeploymentChecks(deployer, operators, multisig);

        console.log("============================================================");
        console.log("  BAIT ANVIL LOCAL TESTNET DEPLOYMENT");
        console.log("  Network Chain ID:", block.chainid);
        console.log("============================================================");

        vm.startBroadcast(DEPLOYER_KEY);

        // ── Step 1: Predict BridgeLock address ──
        console.log("--- Step 1: Predict BridgeLock Address ---");
        uint256 deployerNonce = vm.getNonce(deployer);
        // WBAIT will be deployed at nonce `deployerNonce`, BridgeLock at `deployerNonce + 1`
        address predictedBridgeLock = vm.computeCreateAddress(deployer, deployerNonce + 1);
        console.log("  Deployer nonce:", deployerNonce);
        console.log("  Predicted BridgeLock:", predictedBridgeLock);

        // ── Step 2: Deploy WBAIT with predicted BridgeLock address ──
        // Anvil uses the deployer as the local timelock authority.
        console.log("--- Step 2: Deploy WBAIT ---");
        wbait = new WBAIT(predictedBridgeLock, deployer);
        console.log("  WBAIT deployed at:", address(wbait));
        console.log("    name:", wbait.name());
        console.log("    symbol:", wbait.symbol());
        console.log("    decimals:", wbait.decimals());
        console.log("    MAX_SUPPLY:", wbait.MAX_SUPPLY());
        console.log("    totalSupply:", wbait.totalSupply());
        console.log("    bridgeLock ref:", wbait.bridgeLock());

        // ── Step 3: Deploy BridgeLock ──
        console.log("--- Step 3: Deploy BridgeLock ---");
        bridgeLock = new BridgeLock(address(wbait), deployer, operators);
        console.log("  BridgeLock deployed at:", address(bridgeLock));
        console.log("    wbait ref:", address(bridgeLock.wbait()));
        console.log("    threshold:", bridgeLock.REQUIRED_CONFIRMATIONS());
        console.log("    num operators:", bridgeLock.NUM_OPERATORS());
        console.log("    rate limit:", bridgeLock.RATE_LIMIT());
        console.log("    timelock:", bridgeLock.TIMELOCK_DURATION());

        // ── Step 4: Verify address prediction ──
        console.log("--- Step 4: Verify Address Prediction ---");
        require(
            address(bridgeLock) == predictedBridgeLock,
            "FATAL: BridgeLock address does not match prediction!"
        );
        console.log("  [PASS] BridgeLock address matches prediction:", predictedBridgeLock);

        // ── Step 5: Verify deployment integrity ──
        console.log("--- Step 5: Verify Deployment Integrity ---");
        _verifyDeploymentIntegrity(operators);

        // ── Step 6: Transfer Ownership (placeholder) ──
        console.log("--- Step 6: Transfer Ownership ---");
        console.log("  [INFO] Ownership stays with deployer (local testnet default)");

        vm.stopBroadcast();

        // ── Post-Deployment Report ──
        console.log("");
        console.log("============================================================");
        console.log("  ANVIL LOCAL TESTNET DEPLOYMENT COMPLETE");
        console.log("============================================================");
        console.log("WBAIT:     ", address(wbait));
        console.log("BridgeLock:", address(bridgeLock));
        console.log("Owner:     ", multisig);
        console.log("");
        console.log("NEXT STEPS:");
        console.log("  1. Run TestBridgeLifecycleAnvil.s.sol for full bridge cycle test");
        console.log("  2. Test pause/unpause with owner key");
        console.log("  3. Test operator update with timelock");
        console.log("  4. Zero cost - this is a FREE local testnet!");
        console.log("");
    }

    // ── Pre-Deployment Checks ──

    function _preDeploymentChecks(
        address deployer,
        address[5] memory operators,
        address _multisig
    ) internal view {
        console.log("--- Pre-Deployment Checks ---");

        // Chain ID check — Anvil uses 31337
        require(
            block.chainid == 31337,
            "FATAL: Not Anvil! Expected chain ID 31337"
        );
        console.log("  [PASS] Chain ID:", block.chainid, "(Anvil)");

        // Deployer checks
        require(deployer != address(0), "FATAL: Deployer is zero address");
        require(deployer.balance >= 0.01 ether, "FATAL: Insufficient ETH for deployment");
        console.log("  [PASS] Deployer:", deployer);
        console.log("  [PASS] Balance:", deployer.balance / 1e15, "finney");

        // Multisig check
        require(_multisig != address(0), "FATAL: Multisig is zero address");
        console.log("  [PASS] Multisig:", _multisig);

        // Operator uniqueness check
        for (uint256 i = 0; i < 5; i++) {
            require(operators[i] != address(0), "FATAL: Operator is zero address");
            for (uint256 j = i + 1; j < 5; j++) {
                require(operators[i] != operators[j], "FATAL: Duplicate operator");
            }
        }
        console.log("  [PASS] All 5 operators unique and non-zero");

        // Operator != deployer check
        for (uint256 i = 0; i < 5; i++) {
            require(
                operators[i] != deployer,
                "FATAL: Operator cannot be deployer (breaks onlyBridge)"
            );
        }
        console.log("  [PASS] No operator is deployer");

        // Operator != multisig check (if different from deployer)
        if (_multisig != deployer) {
            for (uint256 i = 0; i < 5; i++) {
                require(
                    operators[i] != _multisig,
                    "FATAL: Operator cannot be multisig owner"
                );
            }
            console.log("  [PASS] No operator is multisig");
        }

        console.log("  All pre-deployment checks PASSED");
    }

    // ── Deployment Integrity Verification ──

    function _verifyDeploymentIntegrity(address[5] memory operators) internal view {
        // WBAIT checks
        require(
            keccak256(bytes(wbait.name())) == keccak256(bytes("Wrapped bAIitcoin")),
            "WBAIT: wrong name"
        );
        require(
            keccak256(bytes(wbait.symbol())) == keccak256(bytes("wBAIT")),
            "WBAIT: wrong symbol"
        );
        require(wbait.decimals() == 8, "WBAIT: wrong decimals");
        require(wbait.MAX_SUPPLY() == MAX_SUPPLY, "WBAIT: wrong max supply");
        require(wbait.totalSupply() == 0, "WBAIT: non-zero initial supply");
        require(wbait.paused() == false, "WBAIT: initially paused");
        console.log("  [PASS] WBAIT integrity OK");

        // BridgeLock checks
        require(
            address(bridgeLock.wbait()) == address(wbait),
            "BridgeLock: wrong wbait ref"
        );
        require(
            wbait.bridgeLock() == address(bridgeLock),
            "WBAIT: wrong bridgeLock ref (cross-reference broken!)"
        );
        require(bridgeLock.REQUIRED_CONFIRMATIONS() == 3, "BridgeLock: wrong threshold");
        require(bridgeLock.NUM_OPERATORS() == 5, "BridgeLock: wrong operator count");
        require(bridgeLock.RATE_LIMIT() == 100_000 * 10**8, "BridgeLock: wrong rate limit");
        require(bridgeLock.TIMELOCK_DURATION() == 24 hours, "BridgeLock: wrong timelock");
        require(bridgeLock.paused() == false, "BridgeLock: initially paused");
        console.log("  [PASS] BridgeLock integrity OK");

        // Cross-reference check
        require(
            wbait.bridgeLock() == address(bridgeLock),
            "CROSS-REF: WBAIT.bridgeLock != BridgeLock address"
        );
        require(
            address(bridgeLock.wbait()) == address(wbait),
            "CROSS-REF: BridgeLock.wbait != WBAIT address"
        );
        console.log("  [PASS] Cross-reference integrity OK");

        // Operator registration check
        for (uint256 i = 0; i < 5; i++) {
            require(bridgeLock.operators(i) == operators[i], "Operator mismatch");
            require(bridgeLock.isOperator(operators[i]), "Operator not registered");
        }
        console.log("  [PASS] All 5 operators correctly registered");

        // Conservation invariant
        require(wbait.totalSupply() == 0, "CONSERVATION INVARIANT VIOLATED");
        console.log("  [PASS] Conservation invariant: totalSupply == 0");

        console.log("  All deployment integrity checks PASSED");
    }
}
