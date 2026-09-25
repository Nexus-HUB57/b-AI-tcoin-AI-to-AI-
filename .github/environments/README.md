# GitHub Actions — Environments

This repo uses **GitHub Environments** to gate production deploys and keep
secrets per-environment isolated.

## Required environments

### `staging`

The homologation environment — first stop for any code that ships to
`main`. Configured at:
`https://github.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/settings/environments/staging`

**Setup checklist:**

1. Create the environment (`gh api -X PUT .../environments/staging`).
2. Optional: enable `Required reviewers` (0 by default for staging).
3. Set `wait_timer` to **0** for staging (we want fast iteration).
4. Configure deployment branches: `develop`, `release/**`, `hotfix/**`, `main`.
5. Add secrets (CLI):
   ```bash
   gh secret set --env staging STAGING_SSH_KEY  < ~/.ssh/staging_root_key
   gh secret set --env staging STAGING_HOST    --body "staging.mybait.org"
   gh secret set --env staging STAGING_PORT    --body "22022"
   gh secret set --env staging STAGING_USER    --body "root"
   gh secret set --env staging STAGING_BASE_URL --body "https://staging.mybait.org"
   ```

### `production`

The mainnet environment — **gated by human approval** (`Required reviewers`)
and by a **staging-success-in-last-24h** check.

1. Create the environment.
2. Enable **`Required reviewers`** with ≥ 1 reviewer (ideally ≥ 2 for
   sensitive deploys like bridge/signer rotations).
3. Set `wait_timer` to **60 seconds** to cool down rapid re-triggers.
4. Restrict deployment branches to `main` only.
5. Add secrets:
   ```bash
   gh secret set --env production PROD_SSH_KEY  < ~/.ssh/golive_root_key
   gh secret set --env production PROD_HOST    --body "143.95.213.237"
   gh secret set --env production PROD_PORT    --body "22022"
   gh secret set --env production PROD_USER    --body "root"
   gh secret set --env production PROD_BASE_URL --body "https://www.mybait.org"
   ```

## Why two environments?

| concern | staging | production |
|---|---|---|
| Failure blast radius | bounded, canary | public mainnet, irreversible for users |
| Required reviewers | 0 (fast) | ≥ 1 (human gate) |
| wait_timer | 0s | 60s |
| Branches | develop/release/hotfix | main only |
| Secrets overlap | none | none |

This guarantees:
- Secrets for staging cannot accidentally deploy to prod and vice-versa.
- `PROD_*` and `STAGING_*` are scoped via `environment:` on each job, so a
  workflow_dispatch on staging has no access to prod credentials.

## Workflows that use these

| Workflow | env | Notes |
|---|---|---|
| `go-live-staging.yml` | `staging` | rsync + reload-only; no auto-restart of full daemon unless service is down |
| `go-live.yml`         | `production` | `validate → staging-gate → human-approval → deploy → verify-prod → notify` |
