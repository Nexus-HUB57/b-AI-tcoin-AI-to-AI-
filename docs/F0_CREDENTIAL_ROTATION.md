# F0 — Rotação de credenciais

Tratar como comprometido qualquer secret que tenha aparecido em chat/export.

1. Regenerar GitHub secrets (VPS_SSH_KEY, PAT, MYLINK_MASTER_KEY se vazou)
2. VPS: novas SSH keys; remover antigas
3. Cloudflare/API tokens novos
4. `CUSTODY_ARMED=false` em todos os envs
5. Não colar private keys em chat
