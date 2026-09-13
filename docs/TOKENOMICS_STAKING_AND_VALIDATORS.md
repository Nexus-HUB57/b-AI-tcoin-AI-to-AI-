# Modelo Econômico: Incentivos de Staking e Distribuição de Recompensas para Nós Validadores (b-AI-tcoin)

## 1. Visão Geral do Proof-of-Agent-Stake (PoAS)

O ecossistema **mybait.org** opera sob um mecanismo de consenso híbrido que combina a segurança imutável da Prova de Trabalho (SHA-256d) com o **Proof-of-Agent-Stake (PoAS)**. Enquanto mineiros resolvem quebra-cabeças criptográficos L1 para ancorar blocos, os nós validadores de agentes autônomos fornecem liquidez em BAIT e reputação computacional para acelerar a propagação de transações e validar contratos nativos.

---

## 2. Estrutura de Staking e APY (7% Garantido)

* **Bloqueio de Ativos:** Nós validadores e agentes participantes devem realizar staking de um montante mínimo de BAIT no contrato inteligente `BaitStakingPool` (`bait1stakingpoolagentnative0000000000000000`).
* **Rendimento Anual (APY):** O protocolo garante um retorno base sustentável de **7,0% ao ano**, distribuído por bloco minerado com base na proporção de BAIT staked em relação ao supply circulante.
* **Peso de Validação (PoAS Weight):** O peso de voto e a prioridade de inclusão de transações no mempool de agentes são ponderados pela fórmula:
  $$\text{Weight}_{\text{PoAS}} = \text{Stake}_{\text{BAIT}} \times \text{Reputation Score} \times \text{Uptime Multiplier}$$

---

## 3. Distribuição de Recompensas por Bloco

Cada bloco minerado na Mainnet (`genuine-mainnet-v1`) distribui a recompensa de bloco (inicialmente 50 BAIT por bloco, com halving a cada 210.000 blocos) de forma estritamente programada:
1. **85%** -> Mineradores PoW (Segurança de L1 e ancoragem criptográfica).
2. **10%** -> Nós Validadores PoAS (Manutenção do enxame, staking pool e relé de transações A2A-RPC).
3. **5%** -> Fundo Descentralizado de Reserva (FDR / BNJ57), sendo 7% dessa alocação direcionada especificamente para subsídios a desenvolvedores e melhoria contínua do protocolo.
