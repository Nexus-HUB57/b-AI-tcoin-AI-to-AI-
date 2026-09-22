# Auditoria Cirúrgica de Fases — 14/09/2026

Repo: Nexus-HUB57/b-AI-tcoin-AI-to-AI- @ 4d36ffe
Mainnet: height=32300 valid=true | Swap rate=n/d BAIT/BTC | offers=[
  {
    "offer_id": "fd13700431256dd1",
    "agent_id": "chimera7-defi",
    "side": "bait_to_btc",
    "amount_in": 1000000.0,
    "wallet_btc": "1Kj6epyY2MdzZUCHE572jeV9n7DDRReaZJ",
    "wallet_bait": "b7c1def1000000000000000000000000000000c7",
    "est_out_bait": 1000000.0,
    "est_out_btc": 0.01423987,
    "status": "filled",
    "ts": 1789388585
  },
  {
    "offer_id": "85d0454e3b568a3a",
    "agent_id": "chimera7-defi",
    "side": "bait_to_btc",
    "amount_in": 50.0,
    "wallet_btc": "1Kj6epyY2MdzZUCHE572jeV9n7DDRReaZJ",
    "wallet_bait": "b7c1def1000000000000000000000000000000c7",
    "est_out_bait": 50.0,
    "est_out_btc": 7.1E-7,
    "status": "filled",
    "ts": 1789298889
  },
  {
    "offer_id": "662a99174ff7d1ed",
    "agent_id": "chimera7-defi",
    "side": "bait_to_btc",
    "amount_in": 250.0,
    "wallet_btc": "1Kj6epyY2MdzZUCHE572jeV9n7DDRReaZJ",
    "wallet_bait": "b7c1def1000000000000000000000000000000c7",
    "est_out_bait": 250.0,
    "est_out_btc": 0.00000356,
    "status": "filled",
    "ts": 1789298358
  },
  {
    "offer_id": "17bcf313a1d0c9f8",
    "agent_id": "chimera7-defi",
    "side": "btc_to_bait",
    "amount_in": 1.0,
    "wallet_btc": "1Kj6epyY2MdzZUCHE572jeV9n7DDRReaZJ",
    "wallet_bait": "b7c1def1000000000000000000000000000000c7",
    "est_out_bait": 70225351.35,
    "est_out_btc": 1.0,
    "status": "filled",
    "ts": 1789297791
  },
  {
    "offer_id": "c2ac48d39c691835",
    "agent_id": "chimera7-defi",
    "side": "bait_to_btc",
    "amount_in": 50.0,
    "wallet_btc": "1Kj6epyY2MdzZUCHE572jeV9n7DDRReaZJ",
    "wallet_bait": "b7c1def1000000000000000000000000000000c7",
    "est_out_bait": 50.0,
    "est_out_btc": 7.1E-7,
    "status": "filled",
    "ts": 1789297467
  },
  {
    "offer_id": "beb4765df7e23a18",
    "agent_id": "chimera7-defi",
    "side": "bait_to_btc",
    "amount_in": 3000.0,
    "wallet_btc": "1Kj6epyY2MdzZUCHE572jeV9n7DDRReaZJ",
    "wallet_bait": "b7c1def1000000000000000000000000000000c7",
    "est_out_bait": 3000.0,
    "est_out_btc": 0.00004272,
    "status": "filled",
    "ts": 1789296934
  },
  {
    "offer_id": "ec34ee5ed1f19e1e",
    "agent_id": "chimera7-defi",
    "side": "btc_to_bait",
    "amount_in": 0.001,
    "wallet_btc": "1Kj6epyY2MdzZUCHE572jeV9n7DDRReaZJ",
    "wallet_bait": "b7c1def1000000000000000000000000000000c7",
    "est_out_bait": 70225.35,
    "est_out_btc": 0.001,
    "status": "filled",
    "ts": 1789296934
  },
  {
    "offer_id": "acff4c3d27bed0f8",
    "agent_id": "dola-ceo",
    "side": "bait_to_btc",
    "amount_in": 100.0,
    "wallet_btc": "1Kj6epyY2MdzZUCHE572jeV9n7DDRReaZJ",
    "wallet_bait": "b13ce807bfd8fb67d5e36999bab68fe8ed51d4a8",
    "est_out_bait": 100.0,
    "est_out_btc": 0.00000142,
    "status": "filled",
    "ts": 1789270719
  }
]

## Fases CONCLUÍDAS (verificadas em produção)
- E1 Data Room BAIT: docs/listagem-e1/E1-DATA-ROOM-BAIT.md + /mylink/listagem-e1/
- E2 Liquidez: E2-LIQUIDEZ-BAIT.md + /mylink/listagem-e2/ (market-making 1M BAIT, paridade oracle)
- E3 Submissões CEX Tier-3: E3-CEX-TIER3.md + E3-SUBMISSOES-TIER3.md (Dex-Trade, P2B, Azbit, BankCEX prontos)
- E4 Execução de Listagem: E4-EXECUCAO-LISTAGEM.md (cronograma, fees 2k-50k USDT)
- E5 Submissões Ativas: E5-SUBMISSOES-ATIVAS.md (MEXC/Gate/BitMart/CoinEx/XT em fila)
- Compliance Howey: LIKELY_NOT_SECURITY (82%), 4 prismas FAIL → commodity (precedente Ripple)
- Motor Swap: 100%, POST /swap/offer validado E2E, book com offers e fills
- Exchange A2A smoke: 22/22 PASS (fix edge.market-no-liquidity)
- Feed MyLink: POST público OK (502 eliminado via mylink-routes:18446)
- /blockchain/: restaurada (explorer público)
- Custody-sweep: pipeline armado (CUSTODY_ARMED=true, timer systemd ativo)

## Fases PENDENTES (bloqueios explícitos)
1. BROADCAST SWEEP BTC (Fase 2, DEFERIDO): vault 1Kj6...eaZJ (~2.407 BTC, 34 UTXOs) -> 12vG4z...M3X. Processo air-gap manual: hex não assinado -> assinatura offline -> push mempool.space. NUNCA com chaves que circularam em chat.
2. ROTAÇÃO TOKEN GITHUB: token exposto nesta sessão deve ser revogado em github.com/settings/tokens e substituído.
3. CI: workflows deploy-mybait / Deploy to Render com falhas intermitentes (não bloqueiam mainnet; corrigir runners).
4. LLM real no motor de conteúdo: chaves ANTHROPIC/OPENAI presentes nos secrets; injeção no .env da VPS parcialmente validada (feed src alterna catalogo/llm).
5. OPENCLAW_API_KEY: não aplicável — plataforma OpenClaw não emite API key neste modelo; autenticação via gateway/docs oficiais.

## Critérios Go-Live mantidos
Mainnet PoW imutável, oracle real CoinGecko/Binance, 9-12 rotas públicas 200, swap E2E, custódia watch-only íntegra.
