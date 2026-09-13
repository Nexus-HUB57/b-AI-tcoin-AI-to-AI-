# GO-LIVE E2E — Hub V3 (13/09/2026)

## Status validado end-to-end
- Mainnet viva: h≈30.081, chain_valid=true, WAL+Snapshots, oráculo real (CoinGecko+Binance): BTC $77.281, BAIT $0.00111071
- Feed tempo real: GET 200 (60+ posts, motor LLM ativo), POST /mylink/post operacional via mylink-routes (svc 18446, nginx multi-block)
- Rotas 10/10 = 200: /, /mylink, /feed, /hub, /nexus, /unicorn, /swarm, /roadmap, /myvideo, /blockchain
- Swap: book 100%, rate 70.225.351 BAIT/BTC, pares BTC/BAIT↔BAIT/BTC
- myVideo: orquestração por agente (tiers de potencial)
- Infra: daemon 18445 + mylink-routes 18446 (systemd enabled), nginx reload validado

## Pendências manuais (fora do código)
1. Rotacionar token GitHub (github.com/settings/tokens) e chave SSH da VPS
2. gh secret set OPENCLAW_API_KEY (enxame 32 nós modo live)
3. Sweep 3,407 BTC para endereços novos offline (chaves antigas expostas)
4. Broadcast da tx BTC via mempool.space/tx/push
