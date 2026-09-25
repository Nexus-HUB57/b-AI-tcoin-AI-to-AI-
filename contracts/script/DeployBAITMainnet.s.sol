// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";

/**
 * @title DeployBAITMainnet - Enhanced Mainnet Deployment Script
 * @notice Production-ready deployment script for BAIT system.
 *         Includes pre/post-deployment validations, ownership transfer,
 *         and comprehensive logging.
 *
 * Usage:
 *   forge script script/DeployBAITMainnet.s.sol \
 *     --rpc-url $RPC_URL \
 *     --broadcast --verify -vvvv
 *
 * Environment Variables Required:
 *   DEPLOYER_PRIVATE_KEY  - Deployer private key
 *   OPERATOR_1..5         - 5 unique bridge operator addresses
 *   TIMELOCK_ADDRESS      - Existing TimelockController contract
 *   MULTISIG_OWNER        - Multisig address for ownership transfer
 */
contract DeployBAITMainnet is Script {
    uint256 constant MAX_SUPPLY = 21_000_000 * 10**8;

    WBAIT public wbait;
    BridgeLock public bridgeLock;
    address public multisig;

    function run() external {
        uint256 deployerKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(deployerKey);

        address[5] memory operators = [
            vm.envAddress("OPERATOR_1"),
            vm.envAddress("OPERATOR_2"),
            vm.envAddress("OPERATOR_3"),
            vm.envAddress("OPERATOR_4"),
            vm.envAddress("OPERATOR_5")
        ];
        address timelockAddress = vm.envAddress("TIMELOCK_ADDRESS");
        multisig = vm.envAddress("MULTISIG_OWNER");

        // Pre-deployment checks
        _preDeploymentChecks(deployer, operators, multisig);

        console.log("============================================================");
        console.log("  BAIT Deployment");
        console.log("  Network Chain ID:", block.chainid);
        console.log("============================================================");

        vm.startBroadcast(deployerKey);

        // Step 1: Deploy WBAIT (bridge = deployer temporarily)
        console.log("--- Step 1: Deploy WBAIT ---");
        wbait = new WBAIT(deployer, timelockAddress);
        console.log("WBAIT deployed at:", address(wbait));
        console.log("  decimals:", wbait.decimals());
        console.log("  MAX_SUPPLY:", wbait.MAX_SUPPLY());
        console.log("  totalSupply:", wbait.totalSupply());

        // Step 2: Deploy BridgeLock
        console.log("--- Step 2: Deploy BridgeLock ---");
        bridgeLock = new BridgeLock(address(wbait), timelockAddress, operators);
        console.log("BridgeLock deployed at:", address(bridgeLock));
        console.log("  wbait ref:", address(bridgeLock.wbait()));
        console.log("  threshold:", bridgeLock.REQUIRED_CONFIRMATIONS());
        console.log("  num operators:", bridgeLock.NUM_OPERATORS());
        console.log("  rate limit:", bridgeLock.RATE_LIMIT());
        console.log("  timelock:", bridgeLock.TIMELOCK_DURATION());

        // Step 3: Verify deployment integrity
        console.log("--- Step 3: Verify Deployment Integrity ---");
        _verifyDeploymentIntegrity(operators);

        // Step 4: Transfer Ownership to Multisig (2-step)
        console.log("--- Step 4: Transfer Ownership to Multisig ---");
        wbait.transferOwnership(multisig);
        bridgeLock.transferOwnership(multisig);
        console.log("  Ownership transfer initiated to:", multisig);
        console.log("  Multisig must call acceptOwnership() on each contract.");

        vm.stopBroadcast();

        // Post-deployment report
        console.log("");
        console.log("============================================================");
        console.log("  DEPLOYMENT COMPLETE");
        console.log("============================================================");
        console.log("WBAIT:    ", address(wbait));
        console.log("BridgeLock:", address(bridgeLock));
        console.log("Multisig: ", multisig);
        console.log("");
        console.log("NEXT STEPS:");
        console.log("  1. Multisig calls acceptOwnership() on both contracts");
        console.log("  2. Verify contracts on Etherscan");
        console.log("  3. Run VerifyBAIT.s.sol for comprehensive checks");
        console.log("  4. Create Uniswap V3 pool + seed liquidity");
        console.log("  5. Set up monitoring (bridge-monitoring.py + dex-monitoring.py)");
    }

    function _preDeploymentChecks(
        address deployer,
        address[5] memory operators,
        address _multisig
    ) internal view {
        console.log("--- Pre-Deployment Checks ---");

        require(deployer != address(0), "Deployer is zero address");
        require(deployer.balance >= 0.01 ether, "Insufficient ETH for deployment");
        console.log("  [PASS] Deployer:", deployer);
        console.log("  [PASS] Balance:", deployer.balance / 1e15, "finney");

        require(_multisig != address(0), "Multisig is zero address");
        require(_multisig != deployer, "Multisig same as deployer");
        console.log("  [PASS] Multisig:", _multisig);

        for (uint256 i = 0; i < 5; i++) {
            require(operators[i] != address(0), "Operator is zero address");
            for (uint256 j = i + 1; j < 5; j++) {
                require(operators[i] != operators[j], "Duplicate operator");
            }
        }
        console.log("  [PASS] All 5 operators unique and non-zero");

        for (uint256 i = 0; i < 5; i++) {
            require(operators[i] != deployer, "Operator is deployer");
        }
        console.log("  [PASS] No operator is deployer");
        console.log("  All pre-deployment checks PASSED");
    }

    function _verifyDeploymentIntegrity(address[5] memory operators) internal view {
        require(wbait.decimals() == 8, "WBAIT: wrong decimals");
        require(wbait.MAX_SUPPLY() == MAX_SUPPLY, "WBAIT: wrong max supply");
        require(wbait.totalSupply() == 0, "WBAIT: non-zero initial supply");
        require(wbait.paused() == false, "WBAIT: initially paused");
        console.log("  [PASS] WBAIT integrity OK");

        require(address(bridgeLock.wbait()) == address(wbait), "BridgeLock: wrong wbait ref");
        require(bridgeLock.REQUIRED_CONFIRMATIONS() == 3, "BridgeLock: wrong threshold");
        require(bridgeLock.NUM_OPERATORS() == 5, "BridgeLock: wrong operator count");
        require(bridgeLock.RATE_LIMIT() == 100_000 * 10**8, "BridgeLock: wrong rate limit");
        require(bridgeLock.TIMELOCK_DURATION() == 24 hours, "BridgeLock: wrong timelock");
        console.log("  [PASS] BridgeLock integrity OK");

        for (uint256 i = 0; i < 5; i++) {
            require(bridgeLock.operators(i) == operators[i], "Operator mismatch");
            require(bridgeLock.isOperator(operators[i]), "Operator not registered");
        }
        console.log("  [PASS] All operators correctly registered");

        require(wbait.totalSupply() == 0, "CONSERVATION INVARIANT VIOLATED");
        console.log("  [PASS] Conservation invariant: totalSupply == 0");
        console.log("  All deployment integrity checks PASSED");
    }
}
