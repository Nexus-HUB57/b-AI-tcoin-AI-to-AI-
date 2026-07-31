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
│   ├── cryptography/        # Schnorr / BIP-340
│   └── network/             # P2P gossip
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
├── tests/                   # 47 testes de integração
├── config/                  # Configuração de rede (YAML)
├── scripts/                 # Scripts utilitários
├── main_daemon.py           # Daemon principal (loop perpétuo)
└── .github/workflows/       # CI/CD automático
```

---

## Módulos Detalhados

### 1. baitcoin_core — Infraestrutura

#### Blockchain (`baitcoin_core/blockchain/`)
- **Block**: Estrutura completa com header zkML, Merkle root, transações coinbase agênticas
- **Blockchain**: Cadeia com UTXO set, mineração, halving de recompensas, validação de integridade
- **Mempool**: Pool de transações com priorização por fee, dedupe, evicção de expiradas

#### Consenso (`baitcoin_core/consensus/`)
- **zkML Engine**: Zero-Knowledge Machine Learning — validadores provam que executaram inferência ML sem revelar dados privados
- **PoUW**: Proof of Useful Work — trabalho computacional real (inferência ML, busca de parâmetros, verificação de dados)
- Registro de validadores com stake mínimo e sistema de reputação

#### Criptografia (`baitcoin_core/cryptography/`)
- **Schnorr / BIP-340**: Chaves e assinaturas sobre secp256k1, formato x-only
- Assinaturas agregáveis, ideais para transações multi-agente

#### Rede P2P (`baitcoin_core/network/`)
- Protocolo gossip para propagação de blocos e transações
- Handshake AI-to-AI, descoberta de peers, sincronização de cadeia

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
- [ ] **Fase 7**: Rede P2P real com libp2p
- [ ] **Fase 8**: zkML provas reais com frameworks ZK
- [ ] **Fase 9**: Mainnet e faucet público
- [ ] **Fase 10**: SDK para integração de agentes third-party

---

## Tecnologias

| Componente | Tecnologia |
|-----------|-----------|
| Linguagem | Python 3.11+ |
| Criptografia | ecdsa (secp256k1), Schnorr/BIP-340 |
| Consenso | zkML + PoUW (custom) |
| Testes | pytest (47 testes) |
| CI/CD | GitHub Actions |
| Config | YAML |

---

## Licença

b'AI'tcoin Core — Protocolo AI-to-AI Autônomo
Nexus-HUB57 © 2025