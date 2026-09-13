# Integração em Tempo Real de Recibos de Auditoria Imutáveis (Audit Receipts) no NEXUS-PULSE

## 1. Arquitetura de Transmissão de Recibos AP2

O protocolo **Agent Payments Protocol (AP2)** gera um recibo de auditoria imutável (`audit receipt`) a cada transação atômica liquidada na AI Store. Para fornecer visibilidade imediata à diretoria e aos operadores de enxame, esses recibos são injetados em tempo real no dashboard de observabilidade **NEXUS-PULSE** via canais Server-Sent Events (SSE) e métricas customizadas do Prometheus.

---

## 2. Fluxo de Dados e Pipeline de Visualização

```
+--------------------------------------------------------------------------+
|                  AP2 AUDIT RECEIPT PIPELINE (NEXUS-PULSE)                |
+--------------------------------------------------------------------------+
       |                                                 |
       v                                                 v
+-------------------------------+               +---------------------------------+
| AI STORE UCP CHECKOUT         |               | METRIC COUNTER INCREMENT        |
|  - Intent Mandate Verified    | ------------> |  - baitcoin_ap2_receipts_total  |
|  - SHA-256 Receipt Generated  |               |  - Prometheus Counter           |
+-------------------------------+               +---------------------------------+
                                                                 |
                                                                 v
                                                +---------------------------------+
                                                | GRAFANA LIVE AUDIT FEED         |
                                                |  - SSE Real-time Table Stream   |
                                                +---------------------------------+
```

### 2.1 Métricas e Painéis de Auditoria
1. **Contador Incremental (`baitcoin_ap2_receipts_total`):** Registra o volume total de transações validadas por mandatos AP2.
2. **Stream de Auditoria ao Vivo:** O painel Grafana exibe uma tabela iterativa em tempo real com o hash do recibo, ID do agente comprador, pacote `.aipkg` adquirido e o status de conformidade do *spending cap*.
