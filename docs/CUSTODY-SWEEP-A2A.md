# Protocolo Sweep A2A — Custodia Autonoma (Hub V3)

Pipeline 100% A2A sem intervencao humana:

1. **custody-watcher** — monitora enderecos do Fundo Bitcoin (mempool.space) a cada 6h via `custody-sweep.timer` (systemd)
2. **sweep-planner** — monta tx de sweep com fee dinamica (halfHourFee) e guardrail canario (primeiro sweep <= 0.01 BTC)
3. **airgap-signer** — assina legacy P2PKH em memoria (ecdsa, low-S, DER+SIGHASH_ALL); WIFs apenas em vault cifrado (MAC + keystream SHA-256), nunca plaintext em disco
4. **custody-broadcaster** — relay do hex bruto via mempool.space/api/tx
5. **custody-registrar** — registra txids no vault cifrado + `fundo_bitcoin.json` + post no feed MyLink

## Controle de armamento
`/etc/custody-sweep.env`: `CUSTODY_ARMED=false` (padrao = simulacao completa end-to-end).
Com `true`, o ciclo executa assinatura e broadcast autonomos — comecando pelo canario.

## Arquivos
- `ops/custody_sweep.py` — modulo operacional
- VPS: `/home/baitcoin/app/custody_sweep.py`, `/etc/systemd/system/custody-sweep.{service,timer}`, `/etc/custody-sweep.env`
- Estado: `/home/baitcoin/.baitcoin/{fundo_bitcoin.json,sweep_plan.json,custody_vault.enc.json}`
