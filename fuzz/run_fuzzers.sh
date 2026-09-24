#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-all}"

run_atheris() {
  echo "=== Atheris / biased seeds demo ==="
  python3 "$ROOT/fuzz/atheris_bridge_props.py" --demo || true
  if python3 -c "import atheris" 2>/dev/null; then
    echo "=== Atheris timed fuzz (corpus) ==="
    ATHERIS_MAX_TIME="${ATHERIS_MAX_TIME:-15}" python3 "$ROOT/fuzz/atheris_bridge_props.py" || true
  else
    echo "(install atheris for libFuzzer loop)"
  fi
}

run_echidna() {
  echo "=== Echidna (on-chain) ==="
  if ! command -v echidna >/dev/null 2>&1 && ! command -v echidna-test >/dev/null 2>&1; then
    echo "Echidna not in PATH — see docs/FUZZERS_ATHERIS_ECHIDNA.md"
    return 0
  fi
  BIN=$(command -v echidna || command -v echidna-test)
  cd "$ROOT/contracts"
  forge build --skip script 2>/dev/null || true
  "$BIN" . --contract EchidnaBridgeTester --config test/echidna.yaml
}

run_foundry_inv() {
  echo "=== Foundry invariant ==="
  cd "$ROOT/contracts"
  FOUNDRY_INVARIANT_RUNS="${FOUNDRY_INVARIANT_RUNS:-64}" \
    forge test --match-contract "InvariantBridgeTest|InvariantAdvancedTest|BridgeInvariantTest" -vv --summary || true
}

case "$MODE" in
  atheris) run_atheris ;;
  echidna) run_echidna ;;
  foundry) run_foundry_inv ;;
  all) run_atheris; run_foundry_inv; run_echidna ;;
  *) echo "Usage: $0 [atheris|echidna|foundry|all]"; exit 1 ;;
esac
