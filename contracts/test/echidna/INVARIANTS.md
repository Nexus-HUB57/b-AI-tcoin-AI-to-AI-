# Echidna + Foundry — invariant map (BAIT)

## CRITICAL

| ID | Property | Echidna | Foundry | Unit |
|----|----------|---------|---------|------|
| I-01 | totalMinted <= totalLocked | echidna_minted_leq_locked | invariant_mintedLeqLocked | test_FullMintRequiresThreeConfirms |
| I-02 | conservationHolds() | echidna_conservation_holds | invariant_conservationHolds | several |
| I-03 | totalSupply <= MAX_SUPPLY | echidna_supply_under_cap | invariant_supplyUnderCap | test_MaxSupply |
| I-04 | bridgeLock wired | echidna_bridge_wired | invariant_bridgeWired | test_BridgeWired |
| I-05 | totalSupply <= totalMinted | echidna_supply_leq_minted | invariant_supplyLeqMinted | burn path |

## HIGH behavior

| ID | Property | Test |
|----|----------|------|
| H-A | No auto-confirm on request | test_RequestLockMintNoAutoConfirm |
| H-B | 3 distinct confirms for mint | test_FullMintRequiresThreeConfirms |
| H-C | Non-operator reverts | test_RevertNonOperator |
| H-D | Rate limit | test_RateLimit |
| H-E | setBridgeLock once | test_SetBridgeLockOnlyOnce |
| H-F | Deployer cannot mint | test_RevertMintByNonBridge |

## Run

```bash
cd contracts
forge test -vvv
forge test --match-contract BridgeFoundryInvariant
echidna test/echidna/BridgeEchidna.sol --contract BridgeEchidna --config test/echidna/echidna.yaml
```

## Optional additive improvement

```solidity
function getLockRequestId(uint256 index) external view returns (bytes32) {
    return lockRequestIds[index];
}
```
