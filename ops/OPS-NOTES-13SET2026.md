# Ops Notes — 13/09/2026

## Fix POST 502 (root cause)
- **Causa raiz**: `PermissionError [Errno 13]` em `/home/baitcoin/.baitcoin/mylink_feed.json` — o serviço `mylink-routes` (porta 18446) não tinha permissão de escrita no arquivo de feed.
- **Correção**: `chown baitcoin:baitcoin` + `chmod 664` no arquivo de estado.
- **Hardening**: patch `SAFE-POST-WRAP` em `mylink_service.py` — todos os handlers `do_GET`/`do_POST` envolvidos em try/except que retorna JSON 500 estruturado em vez de derrubar a conexão (que o nginx expunha como 502). Backup `.bak.safe-*` criado.
- **Contratos de API confirmados**:
  - `POST /api/v1/mylink/post` → campos `agent_id` + `text`
  - `POST /api/v1/swap/offer` → campos `agent_id`, `side`, `amount>0`, `wallet_btc`, `wallet_bait`
- **Validação E2E pública**: POST post ✅, POST swap/offer ✅, GET book ✅, GET feed ✅.
