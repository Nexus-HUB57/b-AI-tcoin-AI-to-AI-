# CI — GitHub Actions (Foundry)

Workflow: `.github/workflows/foundry-ci.yml`

## Jobs

| Job | Required | Description |
|---|---|---|
| **test** | Yes | `forge build --sizes` + unit + stateful invariants |
| **lint** | Yes | `forge lint` — fail only on errors |
| **dry-run-fork** | After test | `DryRunLifecycle` on public fork (no broadcast) |
| **slither** | Optional | Static analysis; continue-on-error |
| **ci-success** | Gate | Requires test + lint success |

## Triggers

- Push to main/master/fix/**/feat/** (paths contracts/**)
- Pull requests to main/master
- workflow_dispatch

## Optional secret

`ETH_RPC_URL` for fork dry-run (default: https://ethereum.publicnode.com)

## Branch protection

Require status check: **CI gate**
