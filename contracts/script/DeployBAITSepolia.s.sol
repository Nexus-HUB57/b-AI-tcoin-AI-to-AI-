// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/**
 * @title DeployBAITSepolia - Sepolia Testnet Deployment Script
 * @notice Production-style deployment script for BAIT system on Sepolia testnet.
 *         Resolves the WBAIT↔BridgeLock circular dependency via address prediction.
 *         Includes pre/post-deployment validations, ownership transfer placeholder,
 *         and comprehensive logging.
 *
 * Usage:
 *   forge script script/DeployBAITSepolia.s.sol \
 *     --rpc-url $SEPOLIA_RPC_URL \
 *     --private-key $DEPLOYER_PRIVATE_KEY \
 *     --broadcast --verify -vvvv
 *
 * Environment Variables Required:
 *   SEPOLIA_RPC_URL       - Sepolia RPC endpoint (Alchemy, Infura, etc.)
 *   DEPLOYER_PRIVATE_KEY  - Deployer private key (funded with Sepolia ETH)
 *
 * Optional Environment Variables:
 *   MULTISIG_OWNER        - Multisig address for ownership transfer (defaults to deployer)
 *
 * Testnet Operators (deterministic Foundry default accounts for testing):
 *   Operator 0: 0xf39FD6E46aAd4f21Ab2D9B4D2386C90789b70653
 *   Operator 1: 0x70997970C51812DcdeA1F10b5BB9bd5F3f3dEB5D
 *   Operator 2: 0x3c44cDDdb6a900Fa2B385dD3C5a7C1A3c4D495F7
 *   Operator 3: 0x90f79bF6f509F8B6e11C0800b9Bd1C3d1FE8c73b
 *   Operator 4: 0x15d34aAf5dB67d33767E7f02D2D4C6C0C0C0c0C0
 *
 * [!] These are TESTNET ONLY. Production uses HSM-derived operator keys.
 */
contract DeployBAITSepolia is Script {
    // ── Constants ──
    uint256 constant MAX_SUPPLY = 21_000_000 * 10**8;
    uint256 constant SEPOLIA_CHAIN_ID = 11155111;

    // Deterministic testnet operator addresses (Foundry default accounts)
    address constant OP_0 = 0xf39FD6E46aAd4f21Ab2D9B4D2386C90789b70653;
    address constant OP_1 = 0x70997970C51812DcdeA1F10b5BB9bd5F3f3dEB5D;
    address constant OP_2 = 0x3c44cDDdb6a900Fa2B385dD3C5a7C1A3c4D495F7;
    address constant OP_3 = 0x90f79bF6f509F8B6e11C0800b9Bd1C3d1FE8c73b;
    address constant OP_4 = 0x15d34aAf5dB67d33767E7f02D2D4C6C0C0C0c0C0;

    // ── State ──
    WBAIT public wbait;
    BridgeLock public bridgeLock;
    address public multisig;

    function run() external {
        // ── Load Environment ──
        uint256 deployerKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(deployerKey);

        address[5] memory operators = [OP_0, OP_1, OP_2, OP_3, OP_4];

        // Load optional multisig (default to deployer for testnet)
        address targetMultisig;
        try vm.envAddress("MULTISIG_OWNER") returns (address _ms) {
            targetMultisig = _ms;
        } catch {
            targetMultisig = deployer;
            console.log("  [INFO] MULTISIG_OWNER not set, using deployer as owner");
        }
        multisig = targetMultisig;

        // ── Pre-Deployment Checks ──
        _preDeploymentChecks(deployer, operators, multisig);

        console.log("============================================================");
        console.log("  BAIT Sepolia Testnet Deployment");
        console.log("  Network Chain ID:", block.chainid);
        console.log("============================================================");

        vm.startBroadcast(deployerKey);

        // ── Step 1: Predict BridgeLock address ──
        console.log("--- Step 1: Predict BridgeLock Address ---");
        uint256 deployerNonce = vm.getNonce(deployer);
        // WBAIT will be deployed at nonce `deployerNonce`, BridgeLock at `deployerNonce + 1`
        address predictedBridgeLock = vm.computeCreateAddress(deployer, deployerNonce + 1);
        console.log("  Deployer nonce:", deployerNonce);
        console.log("  Predicted BridgeLock:", predictedBridgeLock);

        // ── Step 2: Deploy WBAIT with predicted BridgeLock address ──
        console.log("--- Step 2: Deploy WBAIT ---");
        wbait = new WBAIT(predictedBridgeLock);
        console.log("  WBAIT deployed at:", address(wbait));
        console.log("    name:", wbait.name());
        console.log("    symbol:", wbait.symbol());
        console.log("    decimals:", wbait.decimals());
        console.log("    MAX_SUPPLY:", wbait.MAX_SUPPLY());
        console.log("    totalSupply:", wbait.totalSupply());
        console.log("    bridgeLock ref:", wbait.bridgeLock());

        // ── Step 3: Deploy BridgeLock ──
        console.log("--- Step 3: Deploy BridgeLock ---");
        bridgeLock = new BridgeLock(address(wbait), operators);
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
        if (multisig != deployer) {
            wbait.transferOwnership(multisig);
            bridgeLock.transferOwnership(multisig);
            console.log("  Ownership transfer initiated to:", multisig);
            console.log("  Multisig must call acceptOwnership() on both contracts.");
        } else {
            console.log("  [INFO] Ownership stays with deployer (testnet default)");
            console.log("  To transfer: set MULTISIG_OWNER env var and re-run");
        }

        vm.stopBroadcast();

        // ── Post-Deployment Report ──
        console.log("");
        console.log("============================================================");
        console.log("  SEPOLIA DEPLOYMENT COMPLETE");
        console.log("============================================================");
        console.log("WBAIT:     ", address(wbait));
        console.log("BridgeLock:", address(bridgeLock));
        console.log("Owner:     ", multisig);
        console.log("");
        console.log("Deployed Contracts:");
        console.log("  WBAIT  => https://sepolia.etherscan.io/address/", address(wbait));
        console.log("  Bridge => https://sepolia.etherscan.io/address/", address(bridgeLock));
        console.log("");
        console.log("NEXT STEPS:");
        console.log("  1. Verify contracts on Etherscan (auto if --verify flag used)");
        console.log("  2. Run VerifyBAIT.s.sol for comprehensive on-chain checks");
        console.log("  3. Run TestBridgeLifecycle.s.sol for full bridge cycle test");
        console.log("  4. Test pause/unpause with owner key");
        console.log("  5. Test operator update with timelock");
        console.log("  6. Monitor for 48h before mainnet promotion");
        console.log("");
        console.log("VERIFY COMMANDS:");
        console.log("  forge verify-contract", address(wbait), "WBAIT --chain sepolia");
        console.log("  forge verify-contract", address(bridgeLock), "BridgeLock --chain sepolia");
    }

    // ── Pre-Deployment Checks ──

    function _preDeploymentChecks(
        address deployer,
        address[5] memory operators,
        address _multisig
    ) internal view {
        console.log("--- Pre-Deployment Checks ---");

        // Chain ID check
        require(
            block.chainid == SEPOLIA_CHAIN_ID,
            "FATAL: Not Sepolia! Expected chain ID 11155111"
        );
        console.log("  [PASS] Chain ID:", block.chainid, "(Sepolia)");

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
