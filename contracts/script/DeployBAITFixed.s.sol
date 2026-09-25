// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title DeployBAITFixed
 * @notice Versao corrigida do DeployBAIT.s.sol.
 *
 * Audit 2026-09-22 — Bug critico identificado:
 *   No script original (DeployBAIT.s.sol:26):
 *       WBAIT wbait = new WBAIT(msg.sender);   // <-- BUG: passa deployer, nao BridgeLock
 *       BridgeLock bridgeLock = new BridgeLock(address(wbait), operators);
 *
 *   Como `bridgeLock` em WBAIT.sol é `immutable`, depois do deploy
 *   NAO É POSSÍVEL corrigi-lo. O contrato WBAIT aceita mint de qualquer
 *   endereço que seja o deployer original — vetor de mint sem lastro.
 *
 * FIX:
 *   - Usamos CREATE2 com salt determinístico para pré-computar o endereço
 *     do BridgeLock ANTES de deployar o WBAIT.
 *   - WBAIT recebe o endereço pré-computado, eliminando o chicken-and-egg.
 *   - Verificação pós-deploy: assert(wbait.bridgeLock() == address(bridgeLock)).
 *
 * Requer: same deployer (privkey) e mesmo salt → mesmo endereço CREATE2.
 */

import "forge-std/Script.sol";
import "forge-std/console.sol";
import "../src/WBAIT.sol";
import "../src/BridgeLock.sol";
import "../src/BAITBridge.sol";
import "../src/FoundersVesting.sol";
import "../src/TimelockPauseWrapper.sol";

contract DeployBAITFixed is Script {
    bytes32 public constant BRIDGE_LOCK_SALT = keccak256("BAIT_BRIDGE_LOCK_V1");
    bytes32 public constant WBAIT_SALT       = keccak256("BAIT_WBAIT_V1");

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        address[5] memory operators = [
            vm.envAddress("OPERATOR_1"),
            vm.envAddress("OPERATOR_2"),
            vm.envAddress("OPERATOR_3"),
            vm.envAddress("OPERATOR_4"),
            vm.envAddress("OPERATOR_5")
        ];

        // Admin multisig 3/5 + pauser + relayer + vesting admin
        address admin     = vm.envAddress("ADMIN_MULTISIG_3OF5");
        address pauser    = vm.envAddress("PAUSER_ROLE_ADDRESS");
        address relayer   = vm.envAddress("RELAYER_ADDRESS");
        address vestingAdmin = vm.envAddress("VESTING_ADMIN_ADDRESS");

        uint256 tgeTimestamp      = vm.envOr("TGE_TIMESTAMP", block.timestamp);
        uint256 vestingDuration   = vm.envOr("VESTING_DURATION_SECONDS", uint256(4 * 365 days));
        uint256 dailyVolumeLimit  = vm.envOr("DAILY_VOLUME_LIMIT_WEI", uint256(100_000_000 * 1e8));

        vm.startBroadcast(deployerPrivateKey);

        // 1. Pré-computar endereço do BridgeLock via CREATE2
        bytes memory bridgeLockBytecode = abi.encodePacked(
            type(BridgeLock).creationCode,
            abi.encode(address(0), operators)  // placeholder p/ WBAIT — atualizamos depois
        );
        address predictedBridgeLock = vm.computeCreate2Address(
            BRIDGE_LOCK_SALT, keccak256(bridgeLockBytecode), deployer
        );
        console.log("Predicted BridgeLock:", predictedBridgeLock);

        // 2. Deploy WBAIT com o endereço PRE-COMPUTADO do BridgeLock
        WBAIT wbait = new WBAIT{salt: WBAIT_SALT}(predictedBridgeLock);
        console.log("WBAIT deployed at:", address(wbait));

        // 3. Deploy BridgeLock com o WBAIT real
        BridgeLock bridgeLock = new BridgeLock{salt: BRIDGE_LOCK_SALT}(address(wbait), operators);
        require(address(bridgeLock) == predictedBridgeLock, "CREATE2 prediction mismatch");
        console.log("BridgeLock deployed at:", address(bridgeLock));

        // 4. ASSERT pós-deploy — verifica o fix do bug original
        require(wbait.bridgeLock() == address(bridgeLock), "WBAIT.bridgeLock != BridgeLock (bug original)");
        console.log("ASSERT PASSED: WBAIT.bridgeLock == BridgeLock");

        // 5. Deploy BAITBridge (v2 — EIP-712 + circuit breaker)
        BAITBridge baitBridge = new BAITBridge(
            address(wbait),       // baitToken
            dailyVolumeLimit,
            admin,                // admin
            relayer,              // relayer
            pauser                // pauser
        );
        console.log("BAITBridge deployed at:", address(baitBridge));

        // 6. Deploy TimelockController (48h delay)
        address[] memory timelockProposers = new address[](1);
        address[] memory timelockExecutors = new address[](1);
        timelockProposers[0] = admin;
        timelockExecutors[0] = address(0); // 0 = aberto a qualquer um executar após delay
        TimelockController timelock = new TimelockController(48 hours, timelockProposers, timelockExecutors, admin);
        console.log("TimelockController deployed at:", address(timelock));

        // 7. Deploy TimelockPauseWrapper sobre BridgeLock (gatekeeper)
        TimelockPauseWrapper pauseWrapper = new TimelockPauseWrapper(timelock, IPausableTarget(address(bridgeLock)), admin);
        console.log("TimelockPauseWrapper deployed at:", address(pauseWrapper));

        // 8. Deploy FoundersVesting (substitui founders_faucet_cron.sh)
        FoundersVesting foundersVesting = new FoundersVesting(
            address(wbait),
            tgeTimestamp,
            vestingDuration,
            vestingAdmin,
            pauser
        );
        console.log("FoundersVesting deployed at:", address(foundersVesting));

        vm.stopBroadcast();

        // 9. Relatório final
        console.log("\n=== DEPLOY SUMMARY ===");
        console.log("Network:        ", vm.envOr("NETWORK_NAME", string("unknown")));
        console.log("Deployer:       ", deployer);
        console.log("WBAIT:          ", address(wbait));
        console.log("BridgeLock:     ", address(bridgeLock));
        console.log("BAITBridge:     ", address(baitBridge));
        console.log("Timelock:       ", address(timelock));
        console.log("PauseWrapper:   ", address(pauseWrapper));
        console.log("FoundersVesting:", address(foundersVesting));
        console.log("\n--- POST-DEPLOY CHECKS ---");
        console.log("WBAIT.bridgeLock   :", wbait.bridgeLock());
        console.log("== BridgeLock      :", address(bridgeLock));
        console.log("MATCH              :", wbait.bridgeLock() == address(bridgeLock));
        console.log("\n--- AUDIT INVARIANTS ---");
        console.log("BAITBridge.totalLocked:", baitBridge.totalLocked());
        console.log("BAITBridge.totalMinted:", baitBridge.totalMinted());
        console.log("Invariant OK         :", baitBridge.totalMinted() <= baitBridge.totalLocked());

        // 10. JSON summary p/ CI/CD
        string memory summary = string.concat(
            '{"network":"', vm.envOr("NETWORK_NAME", string("unknown")), '",',
            '"wbait":"', vm.toString(address(wbait)), '",',
            '"bridgeLock":"', vm.toString(address(bridgeLock)), '",',
            '"baitBridge":"', vm.toString(address(baitBridge)), '",',
            '"timelock":"', vm.toString(address(timelock)), '",',
            '"pauseWrapper":"', vm.toString(address(pauseWrapper)), '",',
            '"foundersVesting":"', vm.toString(address(foundersVesting)), '",',
            '"invariant_ok":', vm.toString(baitBridge.totalMinted() <= baitBridge.totalLocked()), ',',
            '"wBait_bridgeLock_match":', vm.toString(wbait.bridgeLock() == address(bridgeLock)), '}'
        );
        vm.writeFile("./deploy-summary.json", summary);
        console.log("\nSummary written to ./deploy-summary.json");
    }
}
