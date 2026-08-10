# Mecanismo de Consenso Híbrido: PoW + Proof-of-Agent-Stake (PoAS) na Mainnet do MyBait.org

## 1. Fundamentação Teórica e Arquitetural

Para garantir simultaneamente a robustez de segurança de nível industrial (resistência à censura e imutabilidade de L1) e a eficiência operacional orientada a agentes autônomos, a Mainnet do **b-AI-tcoin** adota um **Modelo de Consenso Híbrido: Proof-of-Work (SHA-256d) combinado com Proof-of-Agent-Stake (PoAS)**.

Enquanto a Prova de Trabalho pura (*PoW*) garante o ancoramento criptográfico imutável e a emissão baseada em esforço computacional, o **Proof-of-Agent-Stake (PoAS)** introduz um peso reputacional e econômico derivado do staking de BAIT por agentes autônomos (*enxames de IA*), otimizando a validação de transações e a priorização de blocos especializados.

---

## 2. Funcionamento do Algoritmo Híbrido

```
+-----------------------------------------------------------------+
|                     BLOCO CANDIDATO (L1)                        |
+-----------------------------------------------------------------+
       |                                                 |
       v                                                 v
+-------------------------------+               +---------------------------------+
|   Proposta PoW (SHA-256d)     |               |   Validação PoAS (Agent Stake)  |
| - Mineração competitiva       |               | - Reputação & Staking de BAIT   |
| - Nonce válido com dificuldade|               | - Verificação de Assinaturas    |
| - Proteção contra Sybil       |               |   Schnorr (BIP-340)             |
+-------------------------------+               +---------------------------------+
       \                                                 /
        \                                               /
         v                                             v
+-----------------------------------------------------------------+
|              CONSENSUS HÍBRIDO APROVADO & ANCORADO              |
+-----------------------------------------------------------------+
```

### 2.1 Componente PoW (Base de Segurança L1)
* **Função Hash:** Duplo SHA-256 (`SHA-256d`), idêntico à arquitetura Bitcoin.
* **Competição de Mineração:** Threads concorrentes competem na resolução de nonces. A dificuldade ajusta-se dinamicamente (`DAA`) para manter o tempo alvo por bloco em 10 segundos.

### 2.2 Componente PoAS (Proof-of-Agent-Stake)
* **Staking de Agentes:** Agentes registrados na AI Store (como `chimera7`, `chimera7_oracle`, `chimera7_defi`) bloqueiam saldos em BAIT no módulo `baitcoin_bank/` (garantindo 7% APY).
* **Peso de Validação:** O stake e a pontuação de reputação calculada pelo oráculo multiplicam a probabilidade de seleção do bloco e reduzem a latência de propagação na rede P2P assíncrona.
* **Governança do FDR:** Vinculação direta com as diretrizes do Fundo Descentralizado de Reserva (FDR / BNJ57), onde 7% das emissões e taxas operacionais são canalizadas para o fundo de desenvolvimento e revalorização.
