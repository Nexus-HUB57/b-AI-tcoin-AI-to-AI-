// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/aa/BAITVerifyingPaymaster.sol";
import "../src/aa/IEntryPoint.sol";

/**
 * @notice Deploy BAITVerifyingPaymaster and optionally seed EntryPoint deposit.
 *
 * Env:
 *   ENTRY_POINT   — defaults to canonical v0.6 addresses per chain
 *   VERIFYING_SIGNER — address of PAYMASTER_SIGNER_KEY public key
 *   OWNER         — admin (Gnosis Safe recommended on mainnet)
 *   DEPOSIT_ETH   — optional ETH to deposit (e.g. 0.1)
 *
 * Example (Sepolia):
 *   forge script script/DeployPaymaster.s.sol:DeployPaymaster \
 *     --rpc-url $SEPOLIA_RPC --broadcast --verify
 */
contract DeployPaymaster is Script {
    // Canonical EntryPoint v0.6 (same on most EVM L1/L2)
    address constant ENTRY_POINT_V06 = 0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789;

    function run() external {
        address entryPoint = vm.envOr("ENTRY_POINT", ENTRY_POINT_V06);
        address verifyingSigner = vm.envAddress("VERIFYING_SIGNER");
        address owner = vm.envOr("OWNER", msg.sender);
        uint256 depositWei = vm.envOr("DEPOSIT_ETH", uint256(0));

        uint256 pk = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(pk);

        BAITVerifyingPaymaster pm =
            new BAITVerifyingPaymaster(IEntryPoint(entryPoint), verifyingSigner, owner);

        if (depositWei > 0) {
            pm.deposit{value: depositWei}();
        }

        vm.stopBroadcast();

        console2.log("BAITVerifyingPaymaster", address(pm));
        console2.log("EntryPoint", entryPoint);
        console2.log("VerifyingSigner", verifyingSigner);
        console2.log("Owner", owner);
        console2.log("DepositWei", depositWei);
    }
}
