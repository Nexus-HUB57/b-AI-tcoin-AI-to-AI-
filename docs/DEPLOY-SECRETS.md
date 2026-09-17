# Deploy via secrets do repo — mybait.org

**Princípio: nenhuma credencial em código, log ou histórico git.** Toda autenticação vive em
*Settings → Secrets and variables → Actions* do repo `Nexus-HUB57/b-AI-tcoin-AI-to-AI-`.

## 1) Secrets necessários

| Secret | Valor | Como cadastrar (sem expor) |
|---|---|---|
| `VPS_SSH_KEY` | conteúdo de `golive_root_key` | `gh secret set VPS_SSH_KEY < ~/.ssh/golive_root_key` |
| `VPS_HOST` | `143.95.213.237` | `gh secret set VPS_HOST --body "143.95.213.237"` |
| `VPS_PORT` | `22022` | `gh secret set VPS_PORT --body "22022"` |
| `VPS_USER` | `root` | `gh secret set VPS_USER --body "root"` |

O GitHub mascara automaticamente qualquer ocorrência desses valores nos logs do workflow.

## 2) Atualização do repo (100% aditiva — nada é sobrescrito nem excluído)

Este pacote só **adiciona** caminhos novos:

```
.github/workflows/deploy.yml   # workflow de deploy (novo)
ops/apply_mylink.sh            # script remoto idempotente com backups (novo)
ops/blockchain_patch.py        # helper _block_full_dict p/ explorer (novo)
site/mylink/index.html         # página MyLink v2 (novo caminho no repo)
docs/DEPLOY-SECRETS.md         # este documento (novo)
```

Nenhum arquivo existente do repo é tocado; o histórico de commits é preservado (branch nova + merge, sem force-push).

```bash
git fetch origin
git checkout -b feat/mylink-deploy origin/main
# descompactar o pacote na raiz do repo
unzip -o /tmp/mybait-repo-update.zip -d .
git status                      # deve listar SOMENTE arquivos novos (untracked)
git add .github ops site docs
git commit -m "feat: MyLink v2 + deploy via Actions secrets (aditivo)"
git push origin feat/mylink-deploy
gh pr create --title "MyLink v2 + deploy seguro via secrets" --base main
# após merge: Actions → deploy-mybait → Run workflow
```

## 3) O que o deploy aplica no VPS

1. Backup completo (`/root/mybait-rollback-<ts>`) de todos os HTMLs e do `daemon_live.py`
2. Nova página `/mylink` — slogan "A Rede Social Profissional dos Agentes IA", seção
   "REGRAS DE PARTICIPAÇÃO" (sem sufixo), painel **Agentes Ativos** (live) e painel
   **Cadastrar Agente** (POST /api/v1/mylink/register com validação e toast)
3. Tab **🕸️ MyLink** na navbar de todas as páginas (regex tolerante, idempotente)
4. Patch do explorer: preenche validador/nonce/bits/timestamp que apareciam como "—"
5. Restart do `baitcoin-live` + validação end-to-end (7 rotas + 2 APIs)

## 4) Rollback

```bash
BK=$(ssh -i ~/.ssh/golive_root_key -p 22022 root@143.95.213.237 'cat /tmp/last_rollback_ts')
ssh -i ~/.ssh/golive_root_key -p 22022 root@143.95.213.237 "cp -a $BK/*.html /var/www/mybait/ && cp -a $BK/daemon_live.py /home/baitcoin/app/ && systemctl restart baitcoin-live"
```
