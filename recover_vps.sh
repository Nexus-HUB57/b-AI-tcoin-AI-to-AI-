#!/bin/bash
# b'AI'tcoin Go Live — recovery VPS (root). Uso: sudo bash recover_vps.sh  (ou rode como root)
set +e
echo "== 1) DISCO =="; df -h / | tail -1

echo "== 2) LIMPEZA =="
rm -f /tmp/*.tar.gz /tmp/*.tgz 2>/dev/null
rm -rf /home/baitcoin/app.bak.* 2>/dev/null
rm -f /var/www/mybait/*.bak.* 2>/dev/null
journalctl --vacuum-size=80M 2>/dev/null
find /var/log -name '*.gz' -mtime +2 -delete 2>/dev/null
WAL=/home/baitcoin/.baitcoin/memory/blockchain/wal
if [ -d "$WAL" ]; then
  mkdir -p /root/wal-quarantine
  ls -t "$WAL"/*.log 2>/dev/null | tail -n +26 | xargs -r mv -t /root/wal-quarantine 2>/dev/null
  echo "WAL antigo -> quarentena: $(ls /root/wal-quarantine 2>/dev/null | wc -l) segmentos"
fi
df -h / | tail -1

echo "== 3) daemon_live.py (v4) =="
mkdir -p /home/baitcoin/app
if [ ! -s /home/baitcoin/app/daemon_live.py ]; then
  echo "!! daemon_live.py ausente — envie o arquivo e rode de novo"; fi

echo "== 4) RESTAURAR NGINX =="
CFG=/etc/nginx/sites-enabled/mybait.org.conf
if grep -q '# ---- baitcoin API' "$CFG" 2>/dev/null; then
  INJ=$(grep -n '# ---- baitcoin API' "$CFG" | head -1 | cut -d: -f1)
  head -n $((INJ-1)) "$CFG" > /tmp/cfg.new
  echo '}' >> /tmp/cfg.new
  mv /tmp/cfg.new "$CFG"
  echo "nginx restaurado (injection removida)"
fi
nginx -t 2>&1 | tail -2
nginx -s reload 2>&1 | tail -1

echo "== 5) SERVICO SYSTEMD baitcoin-live =="
cat > /etc/systemd/system/baitcoin-live.service <<'UNIT'
[Unit]
Description=b'AI'tcoin Live API (read-only snapshot, Go Live)
After=network.target
[Service]
User=baitcoin
Group=baitcoin
WorkingDirectory=/home/baitcoin/app
ExecStart=/usr/bin/python3 /home/baitcoin/app/daemon_live.py
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
UNIT
systemctl stop baitcoin.service 2>/dev/null
pkill -f daemon_production 2>/dev/null; pkill -f daemon_live 2>/dev/null; sleep 2
chown baitcoin:baitcoin /home/baitcoin/app/daemon_live.py 2>/dev/null
systemctl daemon-reload
systemctl enable baitcoin-live 2>&1 | tail -1
systemctl restart baitcoin-live
sleep 8
echo "status: $(systemctl is-active baitcoin-live)"
ss -tln 2>/dev/null | grep 18445 || echo "SEM PORTA 18445"

echo "== 6) VALIDACAO LOCAL =="
echo "--- /api/v1/blockchain:"; curl -s -m 8 http://127.0.0.1:18445/api/v1/blockchain; echo
echo "--- /api/v1/status (head):"; curl -s -m 8 http://127.0.0.1:18445/api/v1/status | head -c 300; echo
echo "--- via nginx https:"; curl -sk -m 10 https://127.0.0.1/api/api/v1/status | head -c 200; echo
echo "== FIM — depois rode: curl -s https://mybait.org/api/api/v1/status =="
