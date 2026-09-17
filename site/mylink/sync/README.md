# mylink-mybait-sync

Sincronização E2E da Master Wallet MyLink com o mybait.org: validação do endereço
Native SegWit (P2WPKH) a partir da chave pública, assinatura de challenge (Schnorr/ECDSA secp256k1)
e transmissão do payload via REST + WebSocket (30s).

## Segurança
Chave privada/master key NUNCA no código — apenas `process.env` / GitHub Secrets
(`MYLINK_MASTER_KEY`). A spec original continha 2.712 chaves expostas; nenhuma foi usada.

## Run
cp .env.example .env && npm install && npm start
