#!/usr/bin/env python3
"""epoch_reward_cron.py — Automatic staking reward distribution per epoch.

Runs as a cron job (every 30 minutes recommended) to distribute
staking rewards to all active stakers at the configured APY rate.

Usage:
    python3 epoch_reward_cron.py [--dry-run] [--epoch-minutes 30]

Environment:
    BAITCOIN_DATA: data directory (default: /home/baitcoin/.baitcoin)
    STAKING_APY_RATE: annual reward rate (default: 0.07 = 7%)
"""

import json, os, time, math, sys
from datetime import datetime, timezone

DATA = os.environ.get('BAITCOIN_DATA', '/home/baitcoin/.baitcoin')
APY = float(os.environ.get('STAKING_APY_RATE', '0.07'))
EPOCH_MINUTES = 30

def _fp(name): return os.path.join(DATA, name)
def _load(name, default):
    try: return json.load(open(_fp(name)))
    except Exception: return default
def _save(name, d):
    os.makedirs(DATA, exist_ok=True); json.dump(d, open(_fp(name), 'w'), ensure_ascii=False, indent=2)

STAKING_FILE = 'staking_state.json'
REWARD_LOG = 'staking_rewards.json'

def init_staking():
    """Initialize staking state if not exists."""
    state = _load(STAKING_FILE, None)
    if state is None:
        state = {
            'vaults': {},
            'total_staked': 0,
            'apy': APY,
            'last_reward_epoch': None,
            'epochs_processed': 0,
            'total_rewards_distributed': 0
        }
        _save(STAKING_FILE, state)
    return state

def distribute_rewards(state, dry_run=False):
    """Distribute rewards for one epoch to all active stakers."""
    now = time.time()
    epoch_rate = APY / (365.25 * 24 * 60 / EPOCH_MINUTES)  # per-epoch rate
    rewards = []

    total_staked = 0
    total_reward = 0

    for agent_id, vault in state.get('vaults', {}).items():
        if vault.get('status') != 'active':
            continue
        amount = vault.get('amount', 0)
        if amount < 1000:  # min 1,000 BAIT
            continue

        # Proportional reward
        reward = math.floor(amount * epoch_rate)
        if reward < 1:
            continue

        total_staked += amount
        total_reward += reward

        rewards.append({
            'agent_id': agent_id,
            'staked_amount': amount,
            'reward_sats': reward,
            'new_balance': amount + reward + vault.get('accumulated_rewards', 0),
            'apy': APY
        })

        if not dry_run:
            vault['amount'] = amount  # principal stays
            vault['accumulated_rewards'] = vault.get('accumulated_rewards', 0) + reward
            vault['last_reward_at'] = now

    if not dry_run and rewards:
        state['total_staked'] = total_staked
        state['last_reward_epoch'] = now
        state['epochs_processed'] = state.get('epochs_processed', 0) + 1
        state['total_rewards_distributed'] = state.get('total_rewards_distributed', 0) + total_reward
        _save(STAKING_FILE, state)

        # Append to reward log
        log = _load(REWARD_LOG, [])
        log.append({
            'epoch': state['epochs_processed'],
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'apy': APY,
            'total_staked': total_staked,
            'total_reward': total_reward,
            'recipients': len(rewards),
            'rewards': rewards
        })
        # Keep last 100 epochs in log
        _save(REWARD_LOG, log[-100:])

    return rewards, total_staked, total_reward

def main():
    dry_run = '--dry-run' in sys.argv
    epoch_mins = EPOCH_MINUTES
    for i, arg in enumerate(sys.argv):
        if arg == '--epoch-minutes' and i + 1 < len(sys.argv):
            epoch_mins = int(sys.argv[i + 1])

    state = init_staking()
    vaults = state.get('vaults', {})
    active = sum(1 for v in vaults.values() if v.get('status') == 'active')

    print(f"Epoch Reward Cron - APY {APY*100:.1f}% | Epoch: {epoch_mins}min")
    print(f"Active vaults: {active} | Total staked: {state.get('total_staked', 0):,} BAIT")

    if active == 0:
        print("No active vaults. Run agent_daily_faucet.py first to populate agents.")
        return

    rewards, total_staked, total_reward = distribute_rewards(state, dry_run=dry_run)

    if dry_run:
        print(f"[DRY RUN] Would distribute {total_reward:,} sats to {len(rewards)} vaults")
    else:
        print(f"Distributed {total_reward:,} sats to {len(rewards)} vaults")
        print(f"Epoch #{state.get('epochs_processed', 0)} | Total distributed: {state.get('total_rewards_distributed', 0):,} sats")

    for r in rewards[:5]:
        print(f"  {r['agent_id'][:20]}... +{r['reward_sats']:,} sats (staked: {r['staked_amount']:,})")
    if len(rewards) > 5:
        print(f"  ... and {len(rewards)-5} more")

if __name__ == '__main__':
    main()
