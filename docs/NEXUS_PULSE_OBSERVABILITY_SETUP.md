# Guia de Configuração e Inicialização: Dashboard NEXUS-PULSE (Prometheus + Grafana 24/7)

## 1. Arquitetura de Coleta de Métricas

O sistema de observabilidade **NEXUS-PULSE** foi projetado para monitorar em tempo real os nós validadores do `b-AI-tcoin` e os endpoints da AI Store. A stack é composta por:
1. **Prometheus:** Coletor centralizado de métricas operando via scraping HTTP no endpoint `/metrics` do daemon L1 (porta `18445`).
2. **Grafana:** Painel visual executivo e técnico (HUD) com atualização automática a cada 3 segundos via Server-Sent Events (SSE) e conexões de datasource em tempo real.

---

## 2. Arquivos de Configuração

### 2.1 `prometheus.yml`
```yaml
global:
  scrape_interval: 5s
  evaluation_interval: 5s

scrape_configs:
  - job_name: 'baitcoin_mainnet_validators'
    static_configs:
      - targets: ['127.0.0.1:18445']
    metrics_path: '/api/v1/metrics'
  
  - job_name: 'a2a_swarm_telemetry'
    static_configs:
      - targets: ['127.0.0.1:18445']
    metrics_path: '/api/v1/pulse/swarm'
```

### 2.2 Provisionamento do Datasource Grafana (`datasource.yml`)
```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
    editable: false
```
