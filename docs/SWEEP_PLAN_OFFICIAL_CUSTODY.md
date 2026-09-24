# Sweep Plan — Official Custody

**Date:** 2026-09-24

## Official custody address (MyLink Fund)

```
bc1qtydmzqcyltsm4tfmxl3a8f9tqvdxls62j05a8s
```

All post-sweep BTC from agent/dust UTXOs must target this address exclusively.

## Policy

1. Identify unspent UTXOs (P1–P50 agent distribution review).
2. Invoke sweep engine only with authorized keys (air-gap / HSM).
3. Destination: official custody above — never alternate addresses.
4. Publish PoR after sweep (master_pool + custody balance).

## Status

- Execution requires authorized node keys (not available in CI agent environment).
- Checklist documented; dry-run analysis only until keys available.
