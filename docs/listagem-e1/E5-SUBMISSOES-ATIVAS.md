# E5 — Submissões Ativas BAIT (14/09/2026)

## Status de submissão por exchange (Tier-3 primeiro)
| Exchange | Canal | Payload | Status |
|---|---|---|---|
| Dex-Trade | Formulário oficial de listagem | Ticker BAIT, supply 21M, explorer https://www.mybait.org/blockchain/, Howey LIKELY_NOT_SECURITY (82%) | PRONTA P/ ENVIO |
| P2B | Listing request | Idem + E2 liquidez (1M BAIT, rate 70.225.351 BAIT/BTC) | PRONTA P/ ENVIO |
| Azbit | Listing application | Idem | PRONTA P/ ENVIO |
| BankCEX | Listing desk | Idem | PRONTA P/ ENVIO |
| MEXC / Gate.io / BitMart / CoinEx / XT.com | Portais oficiais | E3 data room completo | EM FILA (fees 2k–50k USDT) |

## Pré-requisitos técnicos cumpridos
- Explorer público 200 OK; supply endpoint documentado; Howey report integrado
- Swap engine operacional (3 ofertas abertas, rate estável)
- Custódia: sweep armado (CUSTODY_ARMED=true, destino 12vG4z..., fee 2 sat/vB)

## Bloqueios restantes (ação do owner)
1. Assinatura/broadcast do sweep BTC (air-gap ou WIFs) — 2.407 BTC em 1Kj6...eaZJ
2. Rotação do token GitHub exposto
3. Fees de listagem (custódia financia após sweep)
