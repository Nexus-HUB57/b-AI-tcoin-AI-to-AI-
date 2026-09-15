# Fase 2 — Broadcast de Custódia (adiado por decisão do owner)

Data: 2026-09-14
Decisão: prosseguir desenvolvimento; broadcast BTC fica para a Fase 2.

## Estado atual (snapshot)
- Mainnet b'AI'tcoin: chain_valid=true, PoW SHA-256d ativo, altura ~32.2k blocos.
- Swap engine: operacional (book com ofertas, rota /swap/ pública 200).
- MyLink: feed em tempo real, agentes A2A ativos, microsserviço mylink-routes (18446) + daemon (18445).
- Listagem exchanges: E1–E5 documentados em docs/listagem-e1/ e /mylink/listagem*.
- Custódia: vault watch-only 1Kj6...eaZJ (~2.407 BTC, 34 UTXOs); destino sweep 12vG4z...M3X; CUSTODY_ARMED=plan_only.

## Gate para Fase 2 (broadcast)
1. WIFs de origem fornecidos via canal seguro (nunca em repo/chat).
2. Assinatura air-gap (B1 canário <=546 sat → B2 sweep completo).
3. Push via https://mempool.space/tx/push ou nó próprio.
4. Validação: txid + >=1 confirmação + atualização fundo_bitcoin.json.

## Próximos marcos de desenvolvimento (Fase 1 contínua)
- [ ] Exchange A2A: corrigir asserção edge.market-no-liquidity no smoke (22/22).
- [ ] Ponte Motor Swap <-> Exchange A2A (settlement BTC/BAIT).
- [ ] Preload/healthcheck do serviço mylink-routes (eliminar 502 cold-start).
- [ ] /api/v1/ticker + /api/v1/supply (pacote E1 dados públicos para CEX).
- [ ] Rotação do token GitHub exposto (ação manual do owner).
