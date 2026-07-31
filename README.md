# b'AI'tcoin Core: AI-to-AI Autonomous Protocol

<p align="center">
  <strong>Criptomoeda | Blockchain | Be Your Bank</strong><br>
  Protocolo Autônomo de Consenso zkML, PoUW e Coinbase Agêntica
</p>

---

## Visão Geral

**b'AI'tcoin** é um ecossistema de criptomoeda projetado para **transações autônomas AI-to-AI**. O protocolo permite que agentes de inteligência artificial operem como entidades financeiras independentes — minerando blocos, staking, emprestando e governando sem intervenção humana.

### Três Pilares

| Pilar | Descrição |
|-------|-----------|
| **Criptomoeda (BAIT)** | Token nativo com supply fixo de 21M, halvings a cada 210k blocos, transações AI-to-AI |
| **Blockchain** | Cadeia de blocos com consenso zkML + PoUW, Schnorr/BIP-340, P2P gossip |
| **Be Your Bank** | Staking, lending P2P, Vaults auto-custodiados, DeFi para agentes AI |

---

## Arquitetura do Ecossistema

```
baitcoin-ecosystem/
├── baitcoin_core/           # Infraestrutura base
│   ├── blockchain/          # Blocos, cadeia, mempool
│   ├── consensus/           # zkML + PoUW
│   │   ├── zkml_engine.py  # Consenso simulado (Fase 1)
│   │   ├── pouw.py         # Proof of Useful Work
│   │   └── zkml_real/      # zkML REAL (Fase 8)
│   │       ├── proof_system.py    # Sigma protocol + Fiat-Shamir
│   │       ├── tensor_commitment.py # Pedersen commitment para tensores
│   │       └── verifier.py        # Verificador com cache e scoring
│   ├── cryptography/        # Schnorr / BIP-340
│   └── network/             # Rede P2P
│       ├── p2p.py         # Protocolo gossip (Fase 1)
│       ├── p2p_real/      # P2P REAL com asyncio TCP (Fase 7)
│       │   ├── node.py         # No P2P completo (server + client)
│       │   ├── protocol.py     # Protocolo binário com 17 msg types
│       │   └── message_handler.py # Handler com callbacks
│       └── peer_discovery/ # DHT Kademlia-like (Fase 7)
│           └── dht.py          # Routing table, k-buckets, announce
├── baitcoin_wallet/         # Carteiras AI-to-AI
│   ├── keys/                # Gerenciador de chaves
│   ├── transactions/        # Builder de transações
│   └── storage/             # KV Store persistente
├── baitcoin_bank/           # Be Your Bank
│   ├── staking/             # Pool de staking com slashing
│   ├── lending/             # Empréstimos P2P colateralizados
│   └── defi_core/           # Vaults auto-custodiados
├── baitcoin_token/          # Token e Governança
│   ├── erc20_like/          # Token BAIT (21M supply)
│   ├── governance/          # Propostas e votações on-chain
│   └── tokenomics/          # Emissão programada com halvings
├── baitcoin_ai/             # Protocolo de Agentes
│   ├── agent_protocol/      # Registro e reputação
│   ├── marketplace/         # Mercado de serviços AI
│   └── oracle/              # Oracle de preços descentralizado
├── baitcoin_faucet/          # Faucet público (Fase 9)
│   └── faucet.py            # Distribuição anti-abuso com cooldown
├── baitcoin_mainnet/         # Configuração mainnet (Fase 9)
│   ├── config.py            # Parâmetros da rede principal
│   └── launcher.py           # Orquestrador de todos os componentes
├── baitcoin_api/             # API REST (Fase 9)
│   └── server.py             # 15 endpoints HTTP sem dependência
├── baitcoin_sdk/             # SDK para terceiros (Fase 10)
│   ├── client.py             # BaitcoinSDK - ponto de entrada
│   ├── wallet_sdk.py         # Carteiras com endereços bAI1q
│   ├── staking_sdk.py        # Operações de staking
│   └── marketplace_sdk.py    # Busca e compra de serviços
├── tests/
│   ├── test_ecosystem.py     # 47 testes (Fases 1-6)
│   └── test_phases_7_10.py  # 45 testes (Fases 7-10)
├── config/                  # Configuração de rede (YAML)
├── main_daemon.py           # Daemon principal (loop perpétuo)
└── .github/workflows/       # CI/CD automático (4 workflows)
```

---

## Módulos Detalhados

### 1. baitcoin_core — Infraestrutura

#### Blockchain (`baitcoin_core/blockchain/`)
- **Block**: Estrutura completa com header zkML, Merkle root, transações coinbase agênticas
- **Blockchain**: Cadeia com UTXO set, mineração, halving de recompensas, validação de integridade
- **Mempool**: Pool de transações com priorização por fee, dedupe, evicção de expiradas

#### Consenso (`baitcoin_core/consensus/`)
- **zkML Engine** (Fase 1): Zero-Knowledge Machine Learning simulado
- **PoUW**: Proof of Useful Work — trabalho computacional real (inferência ML, busca de parâmetros, verificação de dados)
- Registro de validadores com stake mínimo e sistema de reputação

#### zkML Real (Fase 8) — `baitcoin_core/consensus/zkml_real/`
- **Proof System**: Protocolo Sigma (3-round) com transformação Fiat-Shamir para não-interativo
  - Commit: commitment aleatório `A = G^a mod P`
  - Challenge: derivado via hash do contexto (Fiat-Shamir heuristic)
  - Response: `r = (a + challenge * secret) mod (P-1)` (correto por Fermat)
  - Verificação: `g^r == A * y^challenge mod P`
- **Tensor Commitment**: Pedersen commitments para tensores ML
  - Commit: `C = G^tensor * H^blind mod P` (binding + hiding)
  - Batch commitments, agregação de commitments
- **Verifier**: Cache LRU (10k provas), anti-replay, scoring de validadores, agregação de provas
- **P**: primo 256-bit (`2^256 - 189`), **G**: hash-to-point sobre secp256k1

#### Criptografia (`baitcoin_core/cryptography/`)
- **Schnorr / BIP-340**: Chaves e assinaturas sobre secp256k1, formato x-only
- Assinaturas agregáveis, ideais para transações multi-agente

#### Rede P2P (`baitcoin_core/network/`)
- **Protocolo Binário** (Fase 7): 17 tipos de mensagem, codificação [length][type][payload][timestamp]
- **P2P Node** (Fase 7): Servidor TCP asyncio, conexões inbound/outbound, broadcast gossip
- **Message Handler**: Sistema de callbacks com handlers por tipo e globais
- **Peer Discovery DHT** (Fase 7): Kademlia-like com k-buckets, XOR distance, announce/random peers
- **Sync de Cadeia**: Headers-first, GET_DATA para blocos, sync loop periódico
- **AI Handshake**: Autenticação entre agentes via pubkey Schnorr
- **Keepalive**: Ping/Pong automático a cada 60s, bootstrap com reconexão

---

### 2. baitcoin_wallet — Carteiras AI

- **KeyManager**: Gera e gerencia pares Schnorr por agente AI, deriva agent_id da pubkey
- **TransactionBuilder**: Constrói transações com múltiplos inputs/outputs, gas e payload
- **WalletStorage**: Persistência em disco (KV Store JSON) por agente

---

### 3. baitcoin_bank — Be Your Bank

#### Staking (`baitcoin_bank/staking/`)
- Pool de staking coletivo com APY de 7%
- Mínimo: 1,000 BAIT | Lock: 30 dias | Penalty: 10% (early unstake)
- Slashing por comportamento malicioso (5%)
- Validator set automático baseado em stake

#### Lending (`baitcoin_bank/lending/`)
- Empréstimos P2P colateralizados (mínimo 150% colateral)
- Taxas de juros determinadas pelo mercado livre
- Liquidação automática abaixo de 120% ratio
- Sem KYC — identidade 100% criptográfica

#### Vault (`baitcoin_bank/defi_core/`)
- Conta auto-custodiada: cada agente AI é seu próprio banco
- 5 estratégias: HODL, Staking, Lending, LP, Compound
- Auto-compound, rebalanceamento e stop-loss automáticos
- Risco configurável (conservador a agressivo)

---

### 4. baitcoin_token — Token & Governança

#### Token BAIT (`baitcoin_token/erc20_like/`)
- **Supply total**: 21.000.000 BAIT (como Bitcoin)
- **Decimais**: 8 (s'AI'toshis)
- Transferências, approval, mint, burn
- Log de eventos on-chain

#### Tokenomics (`baitcoin_token/tokenomics/`)
- Halvings a cada 210.000 blocos (recompensa inicial: 50 BAIT)
- Block time alvo: 30 segundos
- Distribuição: 40% mineração, 20% staking, 15% treasury, 15% comunidade, 10% fundadores

#### Governança (`baitcoin_token/governance/`)
- Propostas on-chain com votação por stake (1 BAIT = 1 voto)
- Quorum: 4% do supply | Votação: 7 dias | Threshold: 50%
- Ciclo completo: criação → votação → execução

---

### 5. baitcoin_ai — Protocolo de Agentes

#### Registro (`baitcoin_ai/agent_protocol/`)
- Identidade criptográfica (chave Schnorr)
- 8 capacidades: ML inference, block validation, oracle, DeFi, lending, staking, data processing, market making
- Reputação 0-100 com 4 níveis de confiança
- Validator set automático (reputation >= 60)

#### Marketplace (`baitcoin_ai/marketplace/`)
- Mercado descentralizado de serviços AI pagos em BAIT
- Categorias: inferência ML, validação, oracle, análise, processamento
- Sistema de rating e busca
- Fee de 2.5% por transação

#### Oracle (`baitcoin_ai/oracle/`)
- Feed de preços agregado via mediana ponderada por reputação
- Mínimo 3 oracles para preço válido
- Dados com TTL de 5 minutos

---

### 6. baitcoin_faucet — Faucet Público (Fase 9)

- **Distribuição**: 10 BAIT por claim, cooldown de 24h, máximo 100 BAIT por agente
- **Anti-abuso**: Rate limiting global (60/min), cooldown por agente, limite acumulado
- **Proof-of-Agent**: Suporta desafio assinado via Schnorr
- **Estatísticas**: Histórico de claims por agente, métricas globais

---

### 7. baitcoin_mainnet — Rede Principal (Fase 9)

- **Config**: Portas P2P (18444), API (18445), RPC (18446)
- **Seeds**: 3 nós bootstrap oficiais
- **Launcher**: Orquestra startup de todos os componentes (blockchain + token + consensus + P2P + faucet)
- **Parâmetros**: Dificuldade real, 30s block time, 1M byte max block

---

### 8. baitcoin_api — API REST (Fase 9)

15 endpoints HTTP (sem dependência de framework):

| Método | Endpoint | Descrição |
|--------|----------|------------|
| GET | `/api/v1/status` | Status da rede |
| GET | `/api/v1/blockchain` | Info da blockchain |
| GET | `/api/v1/block/:height` | Bloco por altura |
| GET | `/api/v1/token` | Info do token BAIT |
| GET | `/api/v1/balance/:agent` | Saldo de agente |
| POST | `/api/v1/transfer` | Transferir BAIT |
| POST | `/api/v1/faucet/claim` | Reclamar BAIT do faucet |
| GET | `/api/v1/faucet/balance/:agent` | Saldo via faucet |
| GET | `/api/v1/staking` | Info do staking pool |
| POST | `/api/v1/staking/stake` | Fazer stake |
| GET | `/api/v1/agents` | Lista de agentes |
| GET | `/api/v1/marketplace` | Serviços do marketplace |
| GET | `/api/v1/oracle/:symbol` | Preço de ativo |
| POST | `/api/v1/zkml/proof` | Verificar prova zkML |
| GET | `/api/v1/p2p/peers` | Lista de peers |

---

### 9. baitcoin_sdk — SDK para Terceiros (Fase 10)

Interface Python simples para integração de agentes AI terceiros:

```python
from baitcoin_sdk import BaitcoinSDK

# Inicializar
sdk = BaitcoinSDK()
sdk.configure_local(blockchain, token, faucet, staking, registry, marketplace, oracle)

# Criar carteira com endereço bAI1q
wallet = sdk.create_wallet('my_agent_001')
print(wallet.address)  # bAI1q...
print(wallet.pubkey_hex)  # Chave pública hex

# Claim do faucet
result = sdk.faucet_claim('my_agent_001', wallet.pubkey_hex)
print(result['amount_bait'])  # 10.0

# Consultar saldo
balance = sdk.get_balance('my_agent_001')
print(f'{balance} BAIT')

# Transferir
sdk.transfer('my_agent_001', 'other_agent', 1.5)

# Fazer stake
sdk.stake('my_agent_001', 100.0)

# Consultar preço via oracle
price = sdk.get_price('BTC')

# Buscar serviços no marketplace
services = sdk.search_services('ml_inference')

# Status completo da rede
status = sdk.get_network_status()
```

---

## Quick Start

```bash
# Clonar
gh repo clone Nexus-HUB57/b-AI-tcoin-AI-to-AI-
cd b-AI-tcoin-AI-to-AI-

# Instalar dependências
pip install -r requirements.txt

# Rodar daemon principal
python main_daemon.py

# Rodar testes
python -m pytest tests/ -v

# Status do ecossistema
python -c "
from baitcoin_core import Blockchain
from baitcoin_token.erc20_like.bait_token import BAITToken
from baitcoin_bank.staking.pool import StakingPool

bc = Blockchain()
token = BAITToken()
pool = StakingPool()

print(f'Blockchain: {bc.to_dict()}')
print(f'Token: {token.to_dict()}')
print(f'Staking: {pool.to_dict()}')
"
```

---

## Consensus: zkML + PoUW

O consenso b'AI'tcoin é diferente de PoW ou PoS tradicionais:

1. **Zero-Knowledge ML**: Validadores AI provam que executaram inferência de modelo ML sem revelar dados privados (tensor commitment)
2. **Proof of Useful Work**: O trabalho de mineração produz valor real — inferência ML, otimização de parâmetros, verificação de dados
3. **Coinbase Agêntica**: Recompensas de bloco vão diretamente para o agente validador, sem pool intermediário

---

## Roadmap

- [x] **Fase 1**: Core blockchain, consenso zkML, criptografia Schnorr
- [x] **Fase 2**: Token BAIT, tokenomics com halvings, governança
- [x] **Fase 3**: Be Your Bank — Staking, Lending, Vaults
- [x] **Fase 4**: AI Agent Protocol — Registro, Marketplace, Oracle
- [x] **Fase 5**: Testes de integração (47 testes)
- [x] **Fase 6**: CI/CD com GitHub Actions
- [x] **Fase 7**: Rede P2P real com asyncio TCP + DHT Kademlia
- [x] **Fase 8**: zkML provas reais (Sigma + Fiat-Shamir + Pedersen commitment)
- [x] **Fase 9**: Mainnet + Faucet público + API REST (15 endpoints)
- [x] **Fase 10**: SDK Python para integração de agentes third-party

---

## Tecnologias

| Componente | Tecnologia |
|-----------|-----------|
| Linguagem | Python 3.11+ |
| Criptografia | ecdsa (secp256k1), Schnorr/BIP-340 |
| Consenso | zkML + PoUW (custom) |
| Testes | pytest (92 testes, 100% pass) |
| P2P | asyncio TCP + DHT Kademlia |
| zkML | Sigma protocol + Pedersen commitment |
| API | HTTP server nativo (15 endpoints) |
| SDK | Python SDK para terceiros |
| CI/CD | GitHub Actions (4 workflows) |
| Config | YAML |

---

## Licença

b'AI'tcoin Core — Protocolo AI-to-AI Autônomo
Nexus-HUB57 © 2025