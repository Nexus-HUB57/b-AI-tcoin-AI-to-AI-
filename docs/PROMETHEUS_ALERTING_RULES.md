# Guia de Configuração: Alertas Automáticos Prometheus & Alertmanager (NEXUS-PULSE 24/7)

## 1. Visão Geral do Sistema de Alerta

Para garantir a resposta imediata a falhas críticas em nós validadores e enxames de agentes, configuramos regras estritas de alerta no **Prometheus Alertmanager**, com integração direta a canais de notificação em tempo real (Webhook, PagerDuty, Slack).

---

## 2. Arquivos de Configuração de Alerta

### 2.1 Regras de Alerta (`alert_rules.yml`)
```yaml
groups:
  - name: baitcoin_mainnet_critical_alerts
    rules:
      - alert: ValidatorNodeDown
        expr: up{job="baitcoin_mainnet_validators"} == 0
        for: 15s
        labels:
          severity: critical
        annotations:
          summary: "Validator node is offline (Instance {{ $labels.instance }})"
          description: "Node validator has failed heartbeats for more than 15 seconds. Self-healing protocol initiated."

      - alert: LowSwarmThroughput
        expr: baitcoin_swarm_tps < 1000
        for: 30s
        labels:
          severity: warning
        annotations:
          summary: "A2A swarm throughput below threshold"
          description: "Current swarm TPS is {{ $value }}, indicating potential network congestion."

      - alert: StakingPoolTVLDrop
        expr: deriv(baitcoin_staking_tvl_bait[5m]) < -50000
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Significant TVL drop in BaitStakingPool"
          description: "Staking pool liquidity has dropped sharply over the last 5 minutes."
```

### 2.2 Configuração do Alertmanager (`alertmanager.yml`)
```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 1m
  repeat_interval: 3h
  receiver: 'pagerduty-critical-team'

receivers:
  - name: 'pagerduty-critical-team'
    webhook_configs:
      - url: 'https://api.mybait.org/internal/alerts/webhook'
        send_resolved: true
```
