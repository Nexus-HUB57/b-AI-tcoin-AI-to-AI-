#!/usr/bin/env bash
# Native Atheris (property model) with Echidna fallback for on-chain properties.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-all}"

run_atheris() {
  echo "=== Atheris / fallback property model ==="
  python3 "$ROOT/fuzz/atheris_bridge_props.py" || true
}

run_echidna() {
  echo "=== Echidna (on-chain) ==="
  if ! command -v echidna >/dev/null 2>&1 && ! command -v echidna-test >/dev/null 2>&1; then
    echo "Echidna not in PATH. Install: https://github.com/crytic/echidna/releases"
    echo "Or: docker run --rm -v \"$ROOT/contracts\":/src -w /src trailofbits/eth-security-toolbox \\
      echidna . --contract EchidnaBridgeTester --config test/echidna.yaml"
    return 0
  fi
  BIN=$(command -v echidna || command -v echidna-test)
  cd "$ROOT/contracts"
  forge build --skip script 2>/dev/null || forge build || true
  "$BIN" . --contract EchidnaBridgeTester --config test/echidna.yaml
}

run_foundry_inv() {
  echo "=== Foundry invariant (CI source of truth) ==="
  cd "$ROOT/contracts"
  FOUNDRY_INVARIANT_RUNS="${FOUNDRY_INVARIANT_RUNS:-64}" \
  FOUNDRY_INVARIANT_DEPTH="${FOUNDRY_INVARIANT_DEPTH:-32}" \
    forge test --match-contract "InvariantBridgeTest|InvariantAdvancedTest|BridgeInvariantTest" -vv --summary || true
}

case "$MODE" in
  atheris) run_atheris ;;
  echidna) run_echidna ;;
  foundry) run_foundry_inv ;;
  all)
    run_atheris
    run_foundry_inv
    run_echidna
    ;;
  *)
    echo "Usage: $0 [atheris|echidna|foundry|all]"
    exit 1
    ;;
esac
