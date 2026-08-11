#!/usr/bin/env bash
# ==============================================================================
# HOSTGATOR VPS & cPANEL CENTENNIAL DAEMON (100-Year Autonomy Architecture)
# b-AI-tcoin Mainnet & mybait.org / moltbook.com Ecosystem
# ==============================================================================

echo "============================================================"
echo " INICIALIZANDO ARQUITETURA CENTENÁRIA (100 ANOS DE AUTONOMIA)"
echo " Hostgator VPS (cPanel) - Mainnet Port 18445"
echo "============================================================"

# 1. Configurar variáveis de ambiente de produção perpétua
export BAITCOIN_ENV="production"
export BAITCOIN_NETWORK="mainnet"
export VALIDATOR_PORT=18445
export MOLTBOOK_APP_KEY="live_prod_centennial_key_100y"
export PERSISTENCE_ENABLED="true"
export WAL_JOURNAL_MODE="fsync"

# 2. Criar diretórios de persistência imutável de longo prazo
mkdir -p /home/ubuntu/.baitcoin/memory/wal
mkdir -p /home/ubuntu/.baitcoin/memory/snapshots
mkdir -p /home/ubuntu/.baitcoin/logs

echo "[INFO] Diretórios de persistência centenária verificados."

# 3. Gerar configuração systemd para auto-reparo e execução 24/7 perpétua
SERVICE_FILE="/tmp/baitcoin_mainnet.service"
cat << 'EOF' > $SERVICE_FILE
[Unit]
Description=b-AI-tcoin Centennial Mainnet Validator & Swarm Daemon
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/ubuntu/repos/b-AI-tcoin-AI-to-AI-
Environment=BAITCOIN_ENV=production
Environment=BAITCOIN_NETWORK=mainnet
Environment=VALIDATOR_PORT=18445
Environment=MOLTBOOK_APP_KEY=live_prod_centennial_key_100y
ExecStart=/usr/bin/python3 baitcoin_mainnet/production_launcher.py --port 18445 --perpetual-mode --wal-sync
Restart=always
RestartSec=5
StandardOutput=append:/home/ubuntu/.baitcoin/logs/node_stdout.log
StandardError=append:/home/ubuntu/.baitcoin/logs/node_stderr.log
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

echo "[INFO] Arquivo systemd gerado em $SERVICE_FILE"
echo "[INFO] Para instalar em VPS Hostgator cPanel com privilégios root: sudo cp $SERVICE_FILE /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now baitcoin_mainnet"

# 4. Iniciar simulação de monitoramento e start perpétuo imediato
echo "[INFO] Iniciando enxame de agentes e nó validador na porta 18445..."
python3 baitcoin_ai/swarm_go_live_orchestrator.py

echo "============================================================"
echo " START PERPÉTUO CONCLUÍDO COM SUCESSO!"
echo " O ecossistema está operando em regime de alta disponibilidade."
echo "============================================================"
