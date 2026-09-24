.PHONY: install build test test-unit test-invariant lint dry-run ci sizes clean
install:
	forge install foundry-rs/forge-std --no-commit 2>/dev/null || true
	forge install OpenZeppelin/openzeppelin-contracts@v5.0.2 --no-commit 2>/dev/null || true
build:
	forge build --sizes
test: test-unit test-invariant
test-unit:
	forge test --match-contract "BAITPhase2Test|BridgeInvariantTest|BAITTest" -vv --summary
test-invariant:
	FOUNDRY_INVARIANT_RUNS=$${FOUNDRY_INVARIANT_RUNS:-64} FOUNDRY_INVARIANT_DEPTH=$${FOUNDRY_INVARIANT_DEPTH:-32} \
	forge test --match-contract "InvariantBridgeTest|InvariantAdvancedTest" -vv --summary
lint:
	forge build && forge lint src/ || true
dry-run:
	forge script script/DryRunLifecycle.s.sol:DryRunLifecycle --fork-url $${ETH_RPC_URL:-https://ethereum.publicnode.com} -vv
ci: install build test lint
	@echo "Local CI parity OK"
sizes:
	forge build --sizes
clean:
	forge clean
