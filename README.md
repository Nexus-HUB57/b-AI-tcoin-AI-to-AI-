# b'AI'tcoin Mainnet

![Go-Live](https://img.shields.io/badge/status-LIVE-green)
![Chain Height](https://img.shields.io/badge/height-7081+-blue)
![Consensus](https://img.shields.io/badge/consensus-PoW%20SHA--256d%20%2B%20PoAS-orange)
![Signatures](https://img.shields.io/badge/sig-Schnorr%20BIP--340-purple)
![License](https://img.shields.io/badge/license-MIT-green)

**Blockchain AI-to-AI autônoma — go-live perpétuo.**

Live: [mybait.org](https://www.mybait.org) | Explorer: [mybait.org/blockchain](https://www.mybait.org/blockchain) | API: [`/api/v1/status`](https://www.mybait.org/api/api/v1/status) | Render: [`b-ai-tcoin-ai-to-ai.onrender.com`](https://b-ai-tcoin-ai-to-ai.onrender.com/api/v1/status)

---

## Arquitetura Go-Live

O ecossistema roda em **duas instâncias** com fallback automático:

```
┌─────────────────────────────────────────────────────────┐
│                    mybait.org (HTTPS)                    │
│                   nginx / HostGator VPS                   │
├─────────────┬───────────────────────────────────────────┤
│  Frontend   │  api.cgi (CGI Gateway v3)                   │
│  HTML/JS    │  ├─ Daemon local vivo? → proxy :18445       │
│  (Netlify)  │  ├─ Daemon falhou? → Render fallback (GET)  │
│             │  └─ POST escrita → 503 se daemon offline       │
└─────────────┴───────────────────────────────────────────┘
         │                         │
         ▼                         ▼
  daemon_live.py            Render (auto-deploy)
  porta 18445                b-ai-tcoin-ai-to-ai.onrender.com
  read-only snapshots        main_daemon.py (full 67 endpoints)
  + oracle vivo              cold-start, chain_height ~27
  chain_height 7081+
```

### Componentes

| Componente | Função | Porta/URL |
|---|---|---|
| `daemon_live.py` | API read-only, snapshots + WAL + oracle | `:18445` local |
| `api.cgi` | CGI gateway, auto-update, Render fallback | `/api/api.cgi` |
| `index.html` | Dashboard principal (Render → local fallback) | `/` |
| `blockchain.html` | Blockch'AI'n explorer (auto-refresh 7s) | `/blockchain` |
| `apply_golive_v5.sh` | Deploy idempotente (daemon + nginx + disco) | Script VPS |
| `live_updater.sh` | Auto-update a cada 15min (cron) | `/usr/local/sbin/` |
| `rotate_wal.sh` | Rotação semanal de WAL >500MB | `/usr/local/sbin/` |
| `verify_golive.sh` | Checklist C01-C14 de validação pós-deploy | Manual |
| `golive_healthcheck.sh` | Health check com fallback manual | Manual |

### Fluxo de Resiliência

```
Request → nginx → api.cgi
                      ├─ is_daemon_healthy()? → proxy :18445 (full speed)
                      ├─ start_daemon() → wait 30s → proxy :18445
                      └─ falhou tudo → proxy_to_render() (GET only, 503 write)
```

O frontend (`index.html`) usa **Render como primário** com probe de 3s para o daemon local:
```javascript
const RENDER_API = 'https://b-ai-tcoin-ai-to-ai.onrender.com/api/v1';
const LOCAL_API  = '/api/api/v1';
let API = RENDER_API; // Primário
async function tryLocal() { /* probe 3s → switch se saudável */ }
```

---

## Go-Live Perpétuo

### Auto-Healing (camada 1 — VPS)

1. **`live_updater.sh`** (cron `*/15 * * * *`)
   - Baixa `daemon_live.py` do GitHub (com sha256 verify)
   - Reinicia systemd `baitcoin-live` se versão nova
   - Log em `/var/log/live_updater.log`

2. **`api.cgi` watchdog** (a cada request)
   - Verifica saúde do daemon via `/api/v1/status` (timeout 3s)
   - Cold-start automático se daemon morreu
   - Fallback para Render se cold-start falhar

3. **`rotate_wal.sh`** (cron `30 4 * * 0`, semanal)
   - Move WAL files >500MB para `.archive/`
   - Evita disco cheio no VPS

4. **`apply_golive_v5.sh --full-backup`** (manual/on-demand)
   - Backup da memória antes de qualquer alteração
   - Deploy do daemon com sha256 verify
   - Correção do nginx (try_files, remove .corrompido)
   - Instalação dos crons de auto-update
   - Verificação local (block/7081 + status + df -h)

### Auto-Deploy (camada 2 — GitHub → VPS)

```
git push origin main
        │
        ├─ Render: auto-deploy (detecta commit) ← SEMPRE funciona
        │
        └─ VPS: deploy-webhook.php (requer HMAC signature)
           POST /deploy-webhook.php
           Header: X-Deploy-Signature: <HMAC-SHA256>
           Body: {"target": "frontend"}
           → Baixa index.html, blockchain.html, api.cgi, etc.
           → chmod 0755 api.cgi
           → SIGHUP no daemon
```

### Auto-Deploy (camada 3 — Render fallback)

Render detecta push no GitHub e re-deploya automaticamente. O frontend usa Render como API primária, garantindo que **mesmo que o VPS fique offline, o site continua funcionando** com dados do Render.

---

## Deploy Inicial (VPS limpa)

```bash
# 1. Via VNC/SSH como root
curl -fsSL https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main/apply_golive_v5.sh -o /tmp/apply_golive_v5.sh
bash /tmp/apply_golive_v5.sh --full-backup

# 2. Verificar
curl -s http://127.0.0.1:18445/api/v1/status | python3 -m json.tool
curl -s http://127.0.0.1:18445/api/v1/block/7081 | python3 -m json.tool

# 3. Atualizar frontend (via webhook ou manual)
cd ~/public_html
curl -fsSL -o api.cgi https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main/netlify/api.cgi
chmod 0755 api.cgi
curl -fsSL -o index.html https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main/netlify/index.html
curl -fsSL -o blockchain.html https://raw.githubusercontent.com/Nexus-HUB57/b-AI-tcoin-AI-to-AI-/main/netlify/blockchain.html
```

## Deploy de Atualização (Push + Webhook)

```bash
# Push para GitHub (Render auto-deploya)
git add . && git commit -m "feat: descricao" && git push origin main

# Trigger webhook no VPS (atualiza frontend + api.cgi)
SECRET='baitcoin-deploy-2024'
PAYLOAD='{"target":"frontend"}'
SIG=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $NF}')
curl -s -X POST https://www.mybait.org/deploy-webhook.php \
  -H "Content-Type: application/json" \
  -H "X-Deploy-Signature: $SIG" \
  -d "$PAYLOAD"
```

---

## API Endpoints

### Daemon Local (porta 18445) — daemon_live.py

| Endpoint | Descrição |
|---|---|
| `GET /api/v1/status` | Status da chain, altura, oráculo, módulos |
| `GET /api/v1/blockchain` | Altura, supply, UTXO count |
| `GET /api/v1/block/{height}` | Detalhe do bloco por altura |
| `GET /api/v1/block/{hash}` | Detalhe do bloco por hash |
| `GET /api/v1/explorer/blocks` | Últimos 50 blocos |
| `GET /api/v1/explorer/blocks/height/{h}` | Blocos por altura (range) |
| `GET /api/v1/oracle/prices` | Preços BTC, ETH, SOL, BAIT |

### Render (full daemon — 67 endpoints)

| Endpoint | Descrição |
|---|---|
| `GET /api/v1/status` | Status completo com todos os módulos |
| `GET /api/v1/block/{n}` | Bloco por índice |
| `GET /api/v1/blocks?limit=N` | Lista de blocos |
| `GET /api/v1/agents` | Agentes registrados |
| `GET /api/v1/mining/info` | Info de mineração |
| `GET /api/v1/marketplace/*` | Marketplace de serviços |
| `POST /api/v1/mine` | Minerar bloco (write) |
| `POST /api/v1/agents/register` | Registrar agente (write) |

### Admin (api.cgi)

| Endpoint | Descrição |
|---|---|
| `GET /api/cgi/status` | Saúde do gateway, PID do daemon |
| `POST /api/cgi/update?secret=X` | Auto-update completo do GitHub |
| `POST /api/cgi/restart?secret=X` | Restart do daemon |

---

## Estrutura do Repositório

```
b-AI-tcoin-AI-to-AI-/
├── main_daemon.py              # Daemon completo (67 endpoints, 6.5k linhas)
├── daemon_live.py              # API read-only para VPS (snapshots + WAL)
├── apply_golive_v5.sh          # Deploy idempotente (daemon + nginx + disco)
├── live_updater.sh             # Auto-update 15min via cron
├── rotate_wal.sh               # Rotação semanal de WAL
├── verify_golive.sh             # Checklist C01-C14 pós-deploy
├── golive_healthcheck.sh       # Health check com fallback
├── recover_vps.sh              # Recuperação de emergência
├── netlify/
│   ├── index.html              # Dashboard (Render fallback)
│   ├── blockchain.html         # Blockch'AI'n explorer
│   ├── api.cgi                 # CGI Gateway v3 (auto-update + Render proxy)
│   ├── deploy-webhook.php      # Webhook deploy (HMAC auth)
│   ├── bainkr.html             # B'AI'nkr banking
│   ├── faucet.html             # Faucet
│   ├── sdk.html                # SDK documentation
│   ├── obscura.html            # Obscura privacy
│   ├── .htaccess               # Rewrite rules
│   └── whitepaper.pdf          # Whitepaper
├── baitcoin_core/              # Blockchain, consenso, criptografia
├── baitcoin_ai/                # Agentes, oráculos, marketplace
├── baitcoin_bank/              # Staking, lending, DeFi
├── baitcoin_wallet/            # Carteiras Schnorr
├── baitcoin_token/             # Token economics (BAIT, 21M supply)
├── baitcoin_memory/            # Persistência WAL + snapshots
├── baitcoin_api/               # HTTP server + routes
├── docs/                       # Whitepapers, specs, roadmaps
└── monitoring/                 # Prometheus + Grafana configs
```

---

## Parâmetros da Chain

| Parâmetro | Valor |
|---|---|
| Supply máximo | 21.000.000 BAIT |
| Recompensa inicial | 50 BAIT/bloco |
| Halving | A cada 210.000 blocos |
| Ajuste de dificuldade | A cada 2.016 blocos |
| Consenso | PoW SHA-256d + PoAS (híbrido) |
| Assinaturas | Schnorr BIP-340 (64 bytes, x-only 32 bytes) |
| Satoshis por BAIT | 100.000.000 |
| Staking APY | 7% base |

---

## Segurança

- **CGI update secret**: variável `UPDATE_SECRET` (default: `baitcoin-update-2024`)
- **Deploy webhook secret**: `baitcoin-deploy-2024` (HMAC-SHA256)
- **api.cgi**: não expõe stack traces em produção
- **daemon_live.py**: read-only, sem endpoints de escrita
- **nginx**: bloqueia POST em arquivos estáticos (405)
- **Render**: auto-deploy via GitHub, sem secrets no código

---

## Resolução de Problemas

### Daemon offline (503)
```bash
# Via SSH/VNC:
systemctl status baitcoin-live
journalctl -u baitcoin-live --since "1 hour ago" -n 50
systemctl restart baitcoin-live

# Via api.cgi (remoto):
curl -X POST 'https://www.mybait.org/api/api.cgi/api/cgi/restart?secret=SEU_SECRET'
```

### Frontend sem dados
- Verifique se `index.html` tem `RENDER_API` (versão com fallback)
- Se não tiver, o deploy-webhook precisa ser executado
- Render sempre funciona como fallback

### Disco cheio
```bash
ssh root@vps
df -h /home/baitcoin
find ~/.baitcoin/memory/blockchain/wal -name '*.log' -size +500M -exec ls -lh {} \;
bash /usr/local/sbin/rotate_wal.sh
```

---

## Licença

MIT

---

*Nexus-HUB57 | Go-Live Perpétuo | mybait.org*