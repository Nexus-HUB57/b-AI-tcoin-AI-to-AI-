# Guia de Configuração: Alertas em Tempo Real no Grafana para Métricas de Recuperação Pós-Particionamento (NEXUS-PULSE)

## 1. Visão Geral do Alerta no Grafana

O painel **NEXUS-PULSE** centraliza a telemetria do ecossistema `mybait.org`. Para detectar imediatamente anomalias de desempenho após simulações de Chaos Engineering (como desvios no tempo de reconciliação de Merkle ou falhas de quórum), configuramos alertas nativos no Grafana vinculados a canais de notificação instantânea (Webhook, PagerDuty, Slack).

---

## 2. Configuração de Alertas Baseados em PromQL

### 2.1 Alerta de Desvio no Tempo de Reconciliação (Merkle Sync SLA)
Se o tempo de sincronização de blocos após uma partição de rede exceder o SLA de 5 segundos, o painel aciona um gatilho de nível crítico.

* **Nome da Regra:** `MerkleReconciliationDelayWarning`
* **Query PromQL:**
  ```promql
  histogram_quantile(0.99, rate(baitcoin_merkle_sync_duration_seconds_bucket[5m])) > 5.0
  ```
* **Condição de Disparo:** Avaliação a cada 10 segundos; dispara se o valor for superior a `5.0` por mais de 30 segundos consecutivos.

### 2.2 Alerta de Falha de Quórum PoAS (Split-Brain Detection)
Monitora a proporção de validadores ativos em staking respondendo ao heartbeat assíncrono.

* **Nome da Regra:** `PoASQuorumDegradation`
* **Query PromQL:**
  ```promql
  sum(baitcoin_validator_active_nodes) / sum(baitcoin_validator_total_nodes) < 0.66
  ```
* **Condição de Disparo:** Se o quórum cair abaixo de 66.6% (limiar BFT), um alerta corporativo prioritário é enviado imediatamente via Webhook para a equipe de engenharia e operações.
