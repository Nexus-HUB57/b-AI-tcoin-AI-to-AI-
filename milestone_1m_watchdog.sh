#!/bin/bash
H=$(curl -s --max-time 8 http://127.0.0.1:18445/api/v1/status | python3 -c "import json,sys;print(json.load(sys.stdin)[\"chain_height\"])" 2>/dev/null)
if [ "${H:-0}" -ge 20000 ] && [ ! -f /home/baitcoin/.baitcoin/backups/milestone-1M/DONE ]; then
  mkdir -p /home/baitcoin/.baitcoin/backups/milestone-1M
  cp -r /home/baitcoin/.baitcoin/memory/blockchain /home/baitcoin/.baitcoin/backups/milestone-1M/ 2>/dev/null
  cp /home/baitcoin/.baitcoin/mylink_registrations.json /home/baitcoin/.baitcoin/backups/milestone-1M/ 2>/dev/null
  curl -s --max-time 8 http://127.0.0.1:18445/api/v1/block/20000 > /home/baitcoin/.baitcoin/backups/milestone-1M/block-20000.json 2>/dev/null
  echo "1M_BAIT milestone @ block $H - $(date -u)" > /home/baitcoin/.baitcoin/backups/milestone-1M/DONE
fi
