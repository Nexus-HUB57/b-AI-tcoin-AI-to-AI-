# 🏛️ ROADMAP OFICIAL DE LISTAGEM — BAIT (b'AI'tcoin) nas Exchanges Mundiais

> **Documento canônico do ecossistema** — gerado em 13/09/2026 (UTC)
> Rede: AI'tcoin Mainnet · altura 30.632 · chain_valid=true · PoW SHA-256d · 21M BAIT supply

---

## 0. VEREDITO EXECUTIVO

O BAIT possui hoje todos os **pré-requisitos técnicos** de um ativo listável: mainnet PoW própria em produção (30.600+ blocos), criptografia Schnorr BIP-340, endereços Base58Check com prefixo próprio, explorador com 52+ endpoints REST, oráculo de preço dual (CoinGecko + Binance), documentação OpenAPI 3.0.3 e supply idêntico ao do Bitcoin (21M, halving a cada 210.000 blocos).

O que **falta** são os requisitos de mercado: volume on-chain público, liquidez em pools externas, auditoria de terceiros e conformidade regulatória. Este roadmap fecha essa lacuna em **5 fases (13/09/2026 → 13/09/2028)**, com o unicórnio A2A como destino final (04/09/2036).

---

## 1. MATRIZ DE EXCHANGES — TIERS E CRITÉRIOS

| Tier | Exchanges | Requisito principal | Prazo alvo | Status |
|------|-----------|--------------------|-----------:|--------|
| **T0 — Listagem por mérito** | CoinGecko, CoinMarketCap, CoinPaprika, LiveCoinWatch | API pública de supply + volume + endpoint de ticker | **Q4 2026** | 🟡 API pronta, volume pendente |
| **T1 — DEX primeiro** | Raydium (SOL), Uniswap v3 (wrapped BAIT), Jupiter Aggregator | Ponte wBAIT + pool de liquidez | **Q1 2027** | 🔴 ponte L2 existe, contrato não deployado |
| **T2 — CEX Tier-3** | MEXC, Gate.io, BitMart, LBank, XT.com | Formulário + volume > $50k/dia + comunidade | **Q2–Q3 2027** | ⚪ não iniciado |
| **T3 — CEX Tier-2** | KuCoin, Bybit, OKX, Kraken | Auditoria CertiK/Hacken + KYC do time + market maker | **Q4 2027 – Q2 2028** | ⚪ |
| **T4 — CEX Tier-1** | Binance, Coinbase | Tração comprovada, volume sustentado, review jurídico | **2028+** | ⚪ |

---

## 2. FASES DO ROADMAP

### 🔵 FASE E1 — "LISTÁVEL" (13/09/2026 → 13/12/2026) — *Fundação Técnica*
**Objetivo: tornar o BAIT indexável pelos agregadores de dados.**

- [ ] **E1.1** Endpoint `/api/v1/ticker` compatível com spec CoinGecko (base/target/last/volume) — *o daemon já expõe 52+ endpoints; falta o formato exigido*
- [ ] **E1.2** Endpoint `/api/v1/supply` com circulating/max supply verificável on-chain (já existe via halving schedule — expor JSON dedicado)
- [ ] **E1.3** Página pública `/markets/` com preço, volume 24h e book do Motor Swap nativo
- [ ] **E1.4** Submissão CoinGecko + CoinMarketCap (formulário gratuito; exige: site ativo ✓, explorer ✓, comunidade, volume mínimo)
- [ ] **E1.5** Meta-transações: volume orgânico ≥ $1k/dia no Motor Swap BTC/BAIT (52 agentes A2A gerando fluxo real)
- [ ] **E1.6** Whitepaper v1.0 PDF + página `/docs/whitepaper/` (síntese dos docs NEXUS-HUB-V3)
- **Critério de saída:** BAIT indexado em ≥2 agregadores com preço live.

### 🟢 FASE E2 — "LIQUIDEZ" (01/01/2027 → 31/03/2027) — *DEX First*
**Objetivo: primeiro mercado externo real, sem depender de aprovação de CEX.**

- [ ] **E2.1** Deploy do contrato wBAIT (SPL token na Solana OU ERC-20 na Ethereum) — a lógica `baitcoin_bridge/` já existe (L2); falta o contrato
- [ ] **E2.2** Lock/mint bridge auditável: BAIT travado on-chain → wBAIT emitido 1:1 (prova de reserva via explorer)
- [ ] **E2.3** Pool wBAIT/USDC na Raydium ou Uniswap v3 com seed de liquidez do Fundo Bitcoin (2,407 BTC em custódia)
- [ ] **E2.4** Jupiter Aggregator routing (Solana) — listagem automática após pool ativa
- [ ] **E2.5** Verificação do token (logo, metadados, redes sociais) em Solscan/Etherscan
- **Critério de saída:** par wBAIT/USDC negociável publicamente com pool ≥ $100k TVL.

### 🟡 FASE E3 — "CEX TIER-3" (01/04/2027 → 30/09/2027) — *Primeiras Corretoras*
**Objetivo: 2–3 listagens CEX pagas/meritocráticas.**

- [ ] **E3.1** Data room de listagem: whitepaper, tokenomics, auditoria interna, GitHub activity (repo já tem 60+ PRs merged), prova de mainnet
- [ ] **E3.2** Aplicações: MEXC (formulário público), Gate.io (Startup), BitMart, LBank — custo típico $20k–$80k/listagem ou via votação comunitária
- [ ] **E3.3** Integração técnica: as exchanges exigem (a) RPC node estável ✓ porta 18444, (b) depósito/saque por endereço BAIT ✓, (c) memo/height API — *preparar pacote "exchange-integration-kit" no repo*
- [ ] **E3.4** Market maker designado (usa o exchange-a2a/ já construído: orderbook, matching, settlement — 21/22 smoke tests PASS)
- [ ] **E3.5** Campanha de comunidade: Discord/Telegram ≥ 5k membros (requisito CEX tier-3)
- **Critério de saída:** BAIT negociado em ≥1 CEX com volume ≥ $50k/dia.

### 🟠 FASE E4 — "CONFORMIDADE" (01/10/2027 → 31/03/2028) — *Tier-2*
- [ ] **E4.1** Auditoria de segurança externa (CertiK, Hacken ou Trail of Bits) do core + bridge
- [ ] **E4.2** Parecer jurídico (legal opinion) — classificação do BAIT (utility vs security) por jurisdição (US/EU/BR)
- [ ] **E4.3** Entidade legal constituída (fundação ou LLC) — requisito Kraken/OKX/KuCoin
- [ ] **E4.4** Aplicações KuCoin, Bybit, OKX, Kraken
- **Critério de saída:** listagem em ≥1 CEX tier-2.

### 🔴 FASE E5 — "TIER-1" (2028+) — *Binance/Coinbase*
- Sem atalhos: exige volume orgânico sustentado, usuários ativos reais, narrativa A2A comprovada (o próprio Hub V3 operando 100% autônomo É a narrativa). Aplicação quando o ecossistema estiver no top-500 por volume real.

---

## 3. PACOTE TÉCNICO DE LISTAGEM (o que entregamos a cada exchange)

| Item | Status atual | Ação |
|------|:---:|------|
| Blockchain própria PoW | ✅ produção | — |
| Node RPC estável (pública) | ✅ 18444/18445 | abrir seeds públicos (P2 do roadmap anterior) |
| Explorer público | ✅ 52+ endpoints | página `/blockchain/` dedicada |
| Ticker API (formato agregador) | 🟡 | **E1.1 — construir** |
| Supply verificável | ✅ 21M + halving on-chain | **E1.2 — expor JSON** |
| Wallet SDK | ✅ baitcoin_sdk | publicar no PyPI |
| Logo/brand kit | 🟡 | gerar kit oficial (SVG + PNG 200/500px) |
| Whitepaper | 🟡 docs dispersos | **E1.6 — consolidar PDF** |
| Bridge + wrapped token | 🔴 lógica apenas | **E2.1 — deploy contrato** |
| Auditoria externa | ❌ | **E4.1 — contratar** |
| Entidade legal | ❌ | **E4.3 — constituir** |
| Market maker | 🟡 exchange-a2a pronto | **E3.4 — ativar** |

---

## 4. DEPENDÊNCIAS CRUZADAS (já em execução no Hub V3)

1. **P3 Custódia/Sweep** (2,407 BTC) → financia seed de liquidez E2.3 e taxas de listagem E3.2. *Crítico: concluir sweep ANTES de qualquer aplicação paga.*
2. **Motor Swap** (100% validado) → gera o volume orgânico E1.5 que os agregadores exigem.
3. **Exchange A2A** (21/22 PASS) → vira o market maker E3.4.
4. **Enxame 32 nós / 35 agentes** → força de comunidade e volume A2A genuíno (diferencial narrativo para tier-1: "a primeira cripto negociada por agentes autônomos").

---

## 5. RISCOS E MITIGAÇÕES

| Risco | Prob. | Mitigação |
|-------|:---:|-----------|
| Agregadores rejeitarem por volume baixo | Alta | E1.5: motor swap + agentes gerando fluxo real 24/7 antes da submissão |
| Exploit na bridge wBAIT | Média | E2.2: lock verificável on-chain + auditoria antes de pool pública |
| Bloqueio regulatório (security) | Média | E4.2: parecer jurídico antes de CEX tier-2+ |
| Chaves/tokens expostos (3.407 BTC, ghp_*) | **Crítica** | Rotação imediata: github.com/settings/tokens + sweep offline + secrets |
| Falso volume (wash trading) → ban | Média | Somente fluxo A2A genuíno; nunca inflar volume artificialmente |

---

## 6. MARCOS-CHAVE (timeline visual)

```
2026 Q4 ████████ E1 LISTÁVEL      → CoinGecko/CMC indexação
2027 Q1 ████████ E2 LIQUIDEZ      → wBAIT + pool DEX ($100k TVL)
2027 Q2 ████████ E3 CEX T3        → MEXC/Gate/BitMart (1ª CEX)
2027 Q4 ████████ E4 CONFORMIDADE  → auditoria + entidade legal
2028 Q1 ████████ E4→E5            → KuCoin/Kraken/OKX
2028+   ████████ E5 TIER-1        → Binance/Coinbase (orgânico)
2036    ████████ UNICÓRNIO A2A    → US$1B+ valuation (04/09/2036)
```

---

*Documento vivo — cada fase concluída atualiza este roadmap e dispara a próxima automaticamente via nexus-perpetual loop.*
