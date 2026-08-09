# b'AI'tcoin — Deploy HostGator v0.8.1 (Fulltime Daemon)

## O que muda nesta release

| # | Correção | Arquivo |
|---|----------|---------|
| 1 | **Daemon fulltime** com watchdog cron + auto-recovery | `api.cgi` v2 + `watchdog.sh` |
| 2 | **Favicon** 🪙 → 🤖 (robô) | `index.html` + `bainkr.html` |
| 3 | **Título aba**: "b'AI'nkr — Be Your Own Bank" → "b'AI'tcoin Cryptocurrency" | `bainkr.html` |
| 4 | **Ícone casa 🏛 → 🤖** ao lado de "B'AI'nkr" na nav | `bainkr.html` |

---

## 1. Upload dos arquivos (via cPanel File Manager ou FTP)

Enviar para `~/public_html/` (raiz do domínio `mybait.org`):

```
public_html/
├── index.html          ← Substituir (favicon 🤖 + title corrigido)
├── bainkr.html         ← NOVO (página B'AI'nkr com ícone 🤖 + reconnect)
├── api.cgi             ← Substituir (v2 com watchdog + auto-recovery)
├── .htaccess           ← Substituir (rotas /bainkr, /mainnet, /explorer)
├── whitepaper.pdf      ← Manter
```

Enviar para `~/baitcoin-api/` (fora do public_html):

```
baitcoin-api/
├── watchdog.sh         ← NOVO (script de recovery)
├── main_daemon.py      ← Já deve existir
├── venv/               ← Já deve existir
├── daemon.pid          ← Auto-criado
├── daemon.log          ← Auto-criado
└── watchdog.log        ← Auto-criado pelo watchdog
```

**Permissões:**
```bash
chmod +x ~/public_html/api.cgi
chmod +x ~/baitcoin-api/watchdog.sh
chmod 644 ~/public_html/*.html ~/public_html/.htaccess
```

---

## 2. Configurar o cron watchdog (a peça-chave do "fulltime")

No cPanel → **Cron Jobs**, adicionar:

```
* * * * * /home1/luca2490/baitcoin-api/watchdog.sh >> /home1/luca2490/baitcoin-api/watchdog.log 2>&1
```

Isso executa o watchdog **a cada 1 minuto**, garantindo:
- Se PID morto → cold-start automático
- Se HTTP não responde → mata zumbi + reinicia
- Logs rotativos em `watchdog.log` (max 2MB)

---

## 3. Cold-start manual (primeiro deploy)

Via SSH ou terminal cPanel:

```bash
cd ~/baitcoin-api
bash watchdog.sh
# Aguardar 5s e verificar
curl http://127.0.0.1:18445/api/v1/status
tail -20 watchdog.log
```

Esperado: HTTP 200 com JSON `{"network":"b'AI'tcoin Mainnet","chain_height":...}`.

---

## 4. Validação end-to-end (do browser)

Acessar:
- `https://www.mybait.org/` → homepage (favicon 🤖, title "b'AI'tcoin Cryptocurrency")
- `https://www.mybait.org/bainkr` → página B'AI'nkr (título aba correto, ícone 🤖 nav)
- `https://www.mybait.org/api.cgi/api/v1/status` → JSON do daemon
- `https://www.mybait.org/api.cgi/api/v1/dev/spec` → OpenAPI 3.0.3

---

## 5. Arquitetura fulltime — 3 camadas de recovery

```
┌─────────────────────────────────────────────────────────┐
│  1. Cron Watchdog (1min)  →  cold-start se caído       │
├─────────────────────────────────────────────────────────┤
│  2. CGI Auto-Start        →  cada request checa health  │
├─────────────────────────────────────────────────────────┤
│  3. Frontend Poll (8s)    →  UI mostra estado em tempo real │
└─────────────────────────────────────────────────────────┘
```

Se HostGator matar o processo (ex: idle timeout), qualquer uma das 3 camadas o traz de volta em < 60s.

---

## 6. Troubleshooting

| Sintoma | Diagnóstico | Ação |
|---------|-------------|------|
| `Daemon Offline` persiste > 2min | Cron desabilitado | Verificar cPanel → Cron Jobs |
| CGI retorna 500 | Permissões erradas | `chmod +x api.cgi` |
| CGI retorna 502 | Python indisponível | Verificar `~/baitcoin-api/venv/bin/python3` |
| Watchdog `PID vivo mas HTTP=000` | Porta 18445 bloqueada | Verificar firewall HostGator |
| Favicon não atualiza | Cache do browser | Ctrl+Shift+R (hard reload) |

Logs para debug:
```bash
tail -f ~/baitcoin-api/watchdog.log
tail -f ~/baitcoin-api/daemon.log
tail -f ~/logs/mybait.org.error.log  # HostGator error log
```
