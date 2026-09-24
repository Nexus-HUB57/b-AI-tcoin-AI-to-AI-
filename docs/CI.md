# CI — GitHub Actions (Foundry)

Workflow: `.github/workflows/foundry-ci.yml`

## Jobs

| Job | Required | Description |
|---|---|---|
| **test** | Yes | forge build + unit + stateful invariants |
| **lint** | Yes | forge lint — fail only on errors |
| **ci-success** | Gate | Requires test + lint success |

## Triggers

- Push/PR on contracts/** paths
- workflow_dispatch

## Optional secret

`ETH_RPC_URL` for fork dry-run (default public node)

## Branch protection

Require status check: **CI gate**
