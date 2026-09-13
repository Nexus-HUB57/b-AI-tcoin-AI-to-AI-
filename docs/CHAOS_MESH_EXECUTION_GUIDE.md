# Guia Prático de Execução de Testes com Chaos Mesh no Cluster de Validadores (MyBait.org)

## 1. Visão Geral da Integração Chaos Mesh

Para validar empiricamente a resiliência 24/7 e os SLAs de recuperação pós-particionamento da blockch'AI'in genuína (`genuine-mainnet-v1`), utilizamos o **Chaos Mesh** integrado ao nosso cluster Kubernetes de nós validadores. O Chaos Mesh permite injetar falhas determinísticas de rede, latência e interrupção de pods de forma declarativa via manifests YAML.

---

## 2. Manifests Práticos de Injeção de Falhas

### 2.1 Simulação de Latência Cruzada (Network Delay)
O manifesto abaixo injeta um atraso de rede de 300ms com jitter de 50ms na porta P2P (`18444`) do pod validador alvo.

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: validator-network-delay
  namespace: mainnet
spec:
  action: delay
  mode: one
  selector:
    namespaces:
      - mainnet
    labelSelectors:
      app: baitcoin-validator
  delay:
    latency: '300ms'
    jitter: '50ms'
    correlation: '25'
  direction: to
  target:
    selector:
      namespaces:
        - mainnet
      labelSelectors:
        app: baitcoin-validator
  duration: '5m'
  scheduler:
    cron: '@every 30m'
```

### 2.2 Simulação de Particionamento Total (Network Partition / Split-Brain)
O manifesto a seguir isola completamente o nó validador secundário da rede, simulando um cenário severo de split-brain para testar o tempo de recuperação do quórum Raft (< 10s).

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: validator-network-partition
  namespace: mainnet
spec:
  action: partition
  mode: fixed
  value: '1'
  selector:
    namespaces:
      - mainnet
    labelSelectors:
      app: baitcoin-validator
  direction: both
  target:
    selector:
      namespaces:
        - mainnet
      labelSelectors:
        app: baitcoin-validator
  duration: '2m'
```
