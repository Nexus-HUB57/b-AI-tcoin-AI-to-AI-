# Atheris / libFuzzer mutation strategies (BAIT)

## Stack

Atheris wraps **libFuzzer**. Mutations happen on **byte buffers** that our harness maps onto bridge operations via `FuzzedDataProvider` or structured `run_biased_steps`.

We **do not** relax `minted <= locked` / `supply == minted` asserts. We only improve *how often* valid deep paths are sampled.

---

## Built-in libFuzzer mutations

| Strategy | Behavior | When it helps BAIT |
|----------|----------|--------------------|
| **BitFlip** | Flip 1–n bits | Edge cases in amount / recipient fields |
| **ByteFlip / interesting bytes** | 0x00, 0xff, 0x7f… | Zero amount, max rate-limit boundaries |
| **Add/Sub** | ± small integers on byte lanes | Nudge amounts near `RATE_LIMIT` |
| **Insert/Erase bytes** | Length change | Different `n_steps` / op sequences |
| **Shuffle / Copy part** | Reorder regions | Reorder confirm vs burn |
| **Cross-over (splice)** | Concat two corpus inputs | Combine happy-path prefix + random suffix |
| **ASCII / dict** (if `-dict=`) | Token insertion | Less relevant (we use binary ops) |

Throughput signals: `cov:` (edges), `corp:` (corpus size), `exec/s`.

---

## Custom strategies in `atheris_bridge_props.py`

### 1. Seed corpus (`fuzz/corpus_atheris/`)

Structured **happy-path** buffers:

```
steps | op=request | l1|recipient|amount | confirm×3 | burn frac
```

Bootstraps `req_ok` → `conf_inc` → `conf_mint` so coverage is not stuck on reject edges.

### 2. Operation bias (not mutation of bytes — scheduling bias)

After state is non-empty:

- ~40% **confirm `last_rid`** if pending
- ~25–35% request
- ~20% burn (fraction of supply)
- ~15% advance day

Raises `conf_mint` without changing invariant checks.

### 3. Demo-mode mutations (fallback / `--demo`)

| ID | Name | Implementation |
|----|------|----------------|
| 0 | **Splice** | `a[:cut]+b[cut:]` from two seeds |
| 1 | **Bitflip** | XOR random bits on a seed copy |
| 2 | **Uniform random** | `randbytes(16..128)` |
| 3 | **Interesting integers** | pack 0, 1, 2³²−1, 10⁸, RATE_LIMIT |

### 4. Dict / manual extras (optional)

```bash
# libFuzzer dictionary of 8-byte L1-like tokens
echo -e '"\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x01"\n"l1txseed"' > fuzz/bait.dict
python fuzz/atheris_bridge_props.py -dict=fuzz/bait.dict -max_total_time=60
```

---

## What we refuse to do

- Remove or weaken `conf_inv_block` / `ok()` checks
- Auto-`try/except` swallow invariant failures
- Count “coverage” only on reject paths as success metric

Primary health metrics:

1. `conf_inv_block == 0`
2. `conf_mint` grows with seeds/bias
3. Model branches ≥ ~90% over a 5k+ demo run

---

## Commands

```bash
# Metrics-only biased campaign (no infinite Fuzz loop)
python3 fuzz/atheris_bridge_props.py --demo

# Full Atheris + corpus dir
pip install atheris
ATHERIS_MAX_TIME=60 python3 fuzz/atheris_bridge_props.py

# Shell driver
./fuzz/run_fuzzers.sh atheris
```

Compare with on-chain:

```bash
cd contracts
echidna . --contract EchidnaBridgeTester --config test/echidna.yaml
forge test --match-contract BridgeInvariantTest -vv
```
