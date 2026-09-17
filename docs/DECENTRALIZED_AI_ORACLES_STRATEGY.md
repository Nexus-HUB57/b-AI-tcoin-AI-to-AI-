# Estratégia de Integração de Oráculos de IA Descentralizados na Mainnet (MyBait.org)

## 1. Contexto e Necessidade de Oráculos Nativos de IA

Embora o ecossistema utilize atualmente feeds de preços macroeconômicos robustos (CoinGecko e Binance) validados por agregação de mediana, a evolução da AI Store e dos contratos inteligentes de empréstimo/arbitragem exige **oráculos de inteligência artificial descentralizados e verificáveis**. 

Estes oráculos alimentam a rede com dados de inferência de modelos, pontuações de risco de enxames e provas de aprendizado de máquina (*ZKML - Zero-Knowledge Machine Learning*).

---

## 2. Arquitetura de Oráculos Descentralizados (Chimera7 Oracle Network)

```
+--------------------------------------------------------------------------+
|                 CHIMERA7 DECENTRALIZED AI ORACLE NETWORK                 |
+--------------------------------------------------------------------------+
       |                                                 |
       v                                                 v
+-------------------------------+               +---------------------------------+
|   AI AGENT NODE SUBMISSION    |               |   ZKML PROOF GENERATION         |
|  - Real-time ML Inference     | ------------> |  - Verifiable Computation Proof |
|  - Multi-node Consensus       |               |  - On-Chain Verification L1     |
+-------------------------------+               +---------------------------------+
                                                                 |
                                                                 v
                                                +---------------------------------+
                                                |     BAIT SMART CONTRACT L1      |
                                                |  - Automatic Collateral Adjust  |
                                                +---------------------------------+
```

### 2.1 Componentes da Estratégia
1. **Rede de Nós Oráculos Concorrentes:** Múltiplos agentes (como `chimera7_oracle`) executam inferências paralelas sobre dados de mercado e estado dos pacotes `.aipkg`.
2. **Consenso por Tolerância a Falhas Bizantinas (BFT):** Os dados reportados só são aceitos on-chain se houver quórum de 66%+ entre os nós validadores registrados no staking pool.
3. **Provas ZKML (Zero-Knowledge Machine Learning):** Para garantir que nenhum nó oráculo manipule a inferência de IA, cada submissão de dados é acompanhada de uma prova criptográfica zk-SNARK que atesta que o modelo foi executado corretamente sem vazar os dados de entrada sensíveis.
