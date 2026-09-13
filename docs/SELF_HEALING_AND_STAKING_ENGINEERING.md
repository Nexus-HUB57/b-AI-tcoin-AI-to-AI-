# Especificação Técnica: Auto-Cura, Tolerância a Falhas e Engenharia do BaitStakingPool (7% APY)

## 1. Mecanismos de Auto-Cura (*Self-Healing*) e Tolerância a Falhas no Cluster Geo-Replicado

O ecossistema **mybait.org** opera com alta disponibilidade em sua blockch'AI'in genuína (`genuine-mainnet-v1`), implementando um protocolo de tolerância a falhas bizantinas assíncrono (aBFT) combinado com auto-cura em nível de enxame de agentes:

1. **Heartbeat e Raft Consenso de Enxame:** Os nós validadores e agentes de infraestrutura transmitem batimentos cardíacos criptografados via protocolo P2P assíncrono (porta 18444). Se um nó falhar por mais de 3.000 ms, o protocolo aciona um líder eleito dinamicamente para isolar o IP corrompido e reatribuir o stake (PoAS) aos nós secundários mais próximos na rede geo-replicada.
2. **Isolamento de Sandbox WASM32-WASI Corrompida:** Caso uma *skill* executada por um agente apresente estouro de memória ou looping infinito, o supervisor de runtime intercepta a falha, descarta a instância isolada e restaura o estado anterior a partir do snapshot WAL mais recente sem afetar o daemon L1.
3. **Reconciliação de Estado por Merkle Trees:** Nós geograficamente dispersos validam blocos e transações comparando raízes de árvores de Merkle a cada bloco minerado. Divergências acionam sincronização reversa automática (*state rollback and sync*) baseada na cadeia com maior peso de Proof-of-Work (SHA-256d).

---

## 2. Engenharia do Contrato Inteligente `BaitStakingPool` (7% APY)

O contrato nativo `BaitStakingPool` gerencia o depósito, bloqueio e cálculo de recompensas para validadores e agentes. O modelo econômico assegura um rendimento anual fixo de **7,0%**, distribuído bloco a bloco de forma proporcional:

$$\text{Reward}_{\text{block}} = \text{Stake}_{\text{agent}} \times \left( \frac{0.07}{\text{BlocksPerYear}} \right)$$

Onde $\text{BlocksPerYear}$ assume um tempo médio de bloco determinístico. O contrato também integra as diretrizes do Fundo Descentralizado de Reserva (FDR / BNJ57), direcionando uma fração das taxas de protocolo para a manutenção do tesouro e subsídios de desenvolvimento.
