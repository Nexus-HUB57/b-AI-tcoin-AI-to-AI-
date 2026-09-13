# Métricas de Recuperação Automática Pós-Particionamento (Split-Brain Recovery)

## 1. Visão Geral da Recuperação

Durante uma simulação de particionamento de rede (*split-brain*) no cluster geo-replicado da blockch'AI'in genuína (`genuine-mainnet-v1`), o mecanismo de consenso Raft e as regras de quórum estrito (66%+) isolam o segmento minoritário. O objetivo deste documento é detalhar as métricas e SLAs de recuperação automática após o restabelecimento da conectividade física.

---

## 2. Tabela de Métricas e SLAs de Recuperação

| Indicador de Performance (KPI) | Meta de SLA | Descrição Técnica |
| :--- | :--- | :--- |
| **Tempo de Detecção de Reconexão** | < 2.5 segundos | Identificação imediata de handshake P2P na porta 18444 entre nós reconectados. |
| **Reconciliação de Árvore de Merkle** | < 5.0 segundos | Comparação vetorial de raízes de blocos para identificar divergências temporais. |
| **Replay de Write-Ahead Log (WAL)** | < 3.0 segundos | Reaplicação transacional atômica de blocos pendentes no segmento que sofreu isolamento temporário. |
| **Estabilização do Quórum PoAS** | < 10.0 segundos | Realinhamento completo dos pesos de staking dos validadores, retornando a throughput nominal de ~5.564 TPS. |
