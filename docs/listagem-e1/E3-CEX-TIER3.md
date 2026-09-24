# E3 — CEX TIER-3: Pacote de Aplicação BAIT
**Data:** 14/09/2026 · **Status:** PRONTO PARA SUBMISSÃO

## Alvos e requisitos
| Exchange | Par | Requisito-chave | Taxa est. | Prazo |
|---|---|---|---|---|
| Dex-Trade | BAIT/USDT | Form + supply API + fee | 0,5–1 BTC eq. | 2–4 sem |
| P2B | BAIT/USDT | KYC emissor + auditoria | 1–2 BTC eq. | 3–6 sem |
| Azbit | BAIT/USDT | Comunidade + volume E2 | 0,3–0,8 BTC eq. | 2–4 sem |
| BankCEX | BAIT/BTC | Integração API + conformidade | 0,5–1 BTC eq. | 4–8 sem |

## Artefatos prontos no repo
- `docs/listagem-e1/E1-DATA-ROOM-BAIT.md` — tokenomics, supply 21M, halving 210k, recompensa 50 BAIT
- `docs/listagem-e1/E2-LIQUIDEZ-BAIT.md` — motor swap 100%, book BTC/BAIT ativo, rate 70.225.351 BAIT/BTC
- `compliance/howey-analysis-report.{json,md}` — LIKELY_NOT_SECURITY (82%), 4 prismas FAIL
- Endpoints vivos: `/api/v1/status`, `/api/v1/swap/book`, `/api/v1/block/{h}` (52+ REST)
- Explorer público: `/blockchain/` · Swap UI: `/swap/` · Roadmap: `/mylink/listagem/`

## Checklist de submissão (automatizável A2A)
- [x] Cadeia válida on-chain (chain_valid=true, h>30k)
- [x] Oracle real (CoinGecko/Binance, mediana, 240s)
- [x] Conformidade Howey documentada
- [x] Liquidez E2 verde (book com ofertas reais)
- [ ] Formulários Dex-Trade/P2B/Azbit/BankCEX (requer e-mail oficial do emissor)
- [ ] Par de market-making inicial (0,05 BTC + 3,5M BAIT no book)
