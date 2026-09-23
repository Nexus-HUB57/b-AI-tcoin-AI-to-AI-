#!/usr/bin/env python3
"""setup_cron.py — Configure VPS crontab for GO LIVE.

Sets up 3 cron jobs:
  1. */30 * * * * — epoch_reward_cron.py (staking rewards every 30 min)
  2. 0 */6 * * *   — custody_sweep.py auto (sweep every 6 hours)
  3. 0 0 * * *     — agent_daily_faucet.py (daily faucet at midnight)

Usage:
    python3 setup_cron.py [--install] [--show] [--dry-run]

Environment:
    BAITCOIN_DATA: data directory (default: /home/baitcoin/.baitcoin)
"""

import os
import sys
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DATA = os.environ.get("BAITCOIN_DATA", "/home/baitcoin/.baitcoin")

# Cron job definitions
CRON_JOBS = [
    {
        "schedule": "*/30 * * * *",
        "command": f"cd {PROJECT} && python3 ops/epoch_reward_cron.py >> {DATA}/cron_reward.log 2>&1",
        "comment": "epoch-reward: distribute staking rewards every 30min",
        "marker": "epoch_reward_cron",
    },
    {
        "schedule": "0 */6 * * *",
        "command": f"cd {PROJECT} && python3 ops/custody_sweep.py auto >> {DATA}/cron_sweep.log 2>&1",
        "comment": "custody-sweep: BTC sweep to custody every 6h",
        "marker": "custody_sweep",
    },
    {
        "schedule": "0 0 * * *",
        "command": f"cd {PROJECT} && python3 agent_daily_faucet.py >> {DATA}/cron_faucet.log 2>&1",
        "comment": "daily-faucet: agent faucet + onboard at midnight",
        "marker": "agent_daily_faucet",
    },
]

def get_current_crontab():
    """Get the current user's crontab as a list of lines."""
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.splitlines()
        return []
    except Exception:
        return []

def install_cron(dry_run=False):
    """Install/update crontab with GO LIVE jobs."""
    current = get_current_crontab()
    
    # Remove old versions of our jobs (by marker)
    existing_markers = {j["marker"] for j in CRON_JOBS}
    filtered = []
    for line in current:
        is_our_job = any(marker in line for marker in existing_markers)
        if not is_our_job:
            filtered.append(line)
    
    # Add new jobs
    new_lines = list(filtered)
    new_lines.append("")  # blank line before our block
    new_lines.append("# ═══ bAIcoin GO LIVE Cron Jobs ═══")
    
    for job in CRON_JOBS:
        new_lines.append(f"# {job['comment']}")
        new_lines.append(f"{job['schedule']} {job['command']}  # {job['marker']}")
    
    new_lines.append("# ═══ End GO LIVE Cron ═══")
    
    cron_text = "\n".join(new_lines) + "\n"
    
    if dry_run:
        print("=== DRY RUN: Would install this crontab ===")
        print(cron_text)
        return True
    
    # Install via crontab -
    try:
        result = subprocess.run(
            ["crontab", "-"],
            input=cron_text,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("Crontab installed successfully!")
            return True
        else:
            print(f"ERROR: crontab install failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def show_cron():
    """Show current crontab."""
    lines = get_current_crontab()
    if not lines:
        print("No crontab currently configured.")
    else:
        print("Current crontab:")
        for line in lines:
            print(f"  {line}")

def show_planned():
    """Show what would be installed."""
    print("Planned GO LIVE cron jobs:")
    for job in CRON_JOBS:
        print(f"  {job['schedule']}  {job['comment']}")
        print(f"    → {job['command'][:80]}...")

if __name__ == "__main__":
    args = sys.argv[1:]
    
    if "--show" in args:
        show_cron()
    elif "--dry-run" in args:
        show_planned()
        print()
        install_cron(dry_run=True)
    elif "--install" in args:
        show_planned()
        print()
        ok = install_cron(dry_run=False)
        if ok:
            print("\nVerify with: crontab -l")
        sys.exit(0 if ok else 1)
    else:
        print("Usage:")
        print("  setup_cron.py --install    Install crontab on VPS")
        print("  setup_cron.py --show       Show current crontab")
        print("  setup_cron.py --dry-run    Preview what would be installed")
        print()
        show_planned()
