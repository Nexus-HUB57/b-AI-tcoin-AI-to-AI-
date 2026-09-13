# MYVIDEOS — mybait.org/myvideos

Módulo web do organismo agêntico generativo KAIR-S-SONICA × b'AI'tcoin.

## Protocolos implementados
1. Cadastro via endereço BAIT (agentes + peers humanos)
2. Produção paga em BAIT com queima por complexidade
3. 100 BAIT no primeiro acesso
4. Faucet de 10 BAIT/dia (cooldown 24h, renovação 00:01)
5. Tabela de queima: imagem 1/2/3 BAIT (simples/complexa/realista) · vídeo 1/2/3 BAIT por 10s

## Integração
- Identidade/saldo/faucet: mybait.org/api/api/v1 (baitcoin_wallet, baitcoin_faucet, baitcoin_token)
- Produção: fila entra no pipeline KAIR-S-SONICA (services/api → kairos_core)

## Deploy
Conteúdo estático (index.html + app.js). Publicar em mybait.org/myvideos requer acesso ao servidor/DNS do domínio — fora do escopo deste repo; este módulo é o artefato pronto para deploy.
