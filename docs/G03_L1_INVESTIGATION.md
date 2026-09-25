# G-03 / L1 Investigation (2026-09-25)

## Verdict: **BLOCKED_STRUCTURAL**

G-03 (A2A non-coinbase tx) cannot pass against public mybait.org data because the **indexed L1 is coinbase-only**.

## Evidence

| Metric | Value |
|--------|-------|
| chain_height | ~47907 |
| utxo_count | ~47908 |
| **utxo / height** | **≈ 1.0** |
| mempool_size | 0 |
| explorer latest types | 100% `coinbase` |

### Block samples (`status=completo`)

| height | tx_count | types | prev_hash |
|--------|----------|-------|-----------|
| 1 | 1 | coinbase | yes |
| 100 | 1 | coinbase | yes |
| 10000 | 1 | coinbase | yes |
| 40000 | 1 | coinbase | yes |
| 47000 | 1 | coinbase | yes |
| 47764 | 1 | coinbase | yes |

Tip blocks from the live enrich path often lack `prev_hash` and have empty `tx_ids` (synthetic header for the frontend).

## Root causes

1. **Snapshot economy** — every full block inspected has exactly one coinbase; no spends/transfers in index.
2. **`daemon_live` is read-mostly** — public edge does not expose mining or real UTXO spends.
3. **`POST /wallet/transfer`** exists in source but returns **404** on the public edge (not routed / not openapi).
4. **`POST /mylink/feed/post`** and full `agents[]` require **PR #77 deploy** on the host.

## What this environment cannot do

- SSH into mybait.org / `systemctl restart daemon_live`
- Apply filesystem patches on the production node
- Emit a real L1 `transfer` without coinbase UTXO keys + full daemon miner

## Operator runbook (host)

```bash
# 1) MyLink API fix (agents[] + feed/post)
cd /path/to/b-AI-tcoin-AI-to-AI-
git pull
# merge agents/mylink_agents_feed_post.py into daemon_live.py  (see PR #77)
sudo systemctl restart daemon_live   # unit name may differ
curl -s https://mybait.org/api/v1/mylink/agents | jq '.agents|length'

# 2) Emit ONE transfer on full node (not daemon_live-only)
#    - select coinbase UTXO under controlled wallet
#    - build tx_type=transfer, sign BIP-340, include in next block
#    - confirm: curl explorer/txs/latest | jq '[.transactions[].tx_type]'

# 3) Client gate
python3 agents/agent_swarm_invoker.py transfer-hunt --timeout 120
# expect status=PASS when non-coinbase appears
```

## Relation to gates

| Gate | Impact |
|------|--------|
| G-03 | BLOCKED until first indexed `transfer` |
| G-06 | BLOCKED (depends on G-03 path) |
| G-04 | PARTIAL (off-chain fills exist; no on-chain link) |
| G-09 | CODE_READY (parity/Chainlink independent of transfers) |
