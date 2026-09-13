# Guia de Implantação em Nuvem: Nós Validadores em Alta Disponibilidade 24/7 (MyBait.org)

## 1. Arquitetura de Infraestrutura

Para operar nós validadores do `b-AI-tcoin` e instâncias de enxames de IA na AI Store com uptime de 99.99% (24/7/All-Time), recomenda-se a seguinte arquitetura em nuvem (AWS / GCP / Multi-Cloud):

```
+--------------------------------------------------------------------------+
|                 HIGH-AVAILABILITY CLOUD DEPLOYMENT                       |
+--------------------------------------------------------------------------+
       |                                                 |
       v                                                 v
+-------------------------------+               +---------------------------------+
| GLOBAL ANYCAST DNS / LB       |               | PERSISTENT STORAGE (EBS/PD)     |
|  - TLS Termination            | ------------> |  - Encrypted WAL & Snapshots    |
|  - DDoS Mitigation (Cloudflare)|              |  - Automatic Daily Backups      |
+-------------------------------+               +---------------------------------+
                                                                 |
                                                                 v
                                                +---------------------------------+
                                                | KUBERNETES / EKS CLUSTER        |
                                                |  - Daemon Pods (Port 18445)     |
                                                |  - Auto-Healing & Health Probes |
                                                +---------------------------------+
```

---

## 2. Passo a Passo de Configuração

### 2.1 Provisionamento com Terraform & Docker
Cada nó validador é empacotado em um container Docker otimizado com Python 3.11 e Uvicorn, gerenciado por orquestração Kubernetes.

```yaml
# Exemplo de Deployment Kubernetes para o Nó Validador b-AI-tcoin
apiVersion: apps/v1
kind: Deployment
metadata:
  name: baitcoin-validator-node
  namespace: mainnet
spec:
  replicas: 3
  selector:
    matchLabels:
      app: baitcoin-validator
  template:
    metadata:
      labels:
        app: baitcoin-validator
    spec:
      containers:
      - name: daemon
        image: registry.mybait.org/baitcoin/core:v0.8.1-production
        command: ["python3", "baitcoin_mainnet/production_launcher.py", "18445"]
        ports:
        - containerPort: 18445
          name: http-api
        - containerPort: 18444
          name: p2p-sync
        resources:
          limits:
            cpu: "4"
            memory: "8Gi"
          requests:
            cpu: "2"
            memory: "4Gi"
        volumeMounts:
        - mountPath: /root/.baitcoin/wal
          name: wal-storage
      volumes:
      - name: wal-storage
        persistentVolumeClaim:
          claimName: baitcoin-wal-pvc
```

### 2.2 Recomendações de Segurança (Hardening)
1. **Firewall Restrito:** Apenas as portas `18444` (P2P) e `18445` (API REST) devem estar expostas, protegidas por regras estritas de IP whitelisting e Cloudflare WAF.
2. **Master Key Protegida:** As chaves privadas dos validadores e cofres de staking operam sob criptografia AES-256 com derivação de chave em ambiente isolado de HSM / Secret Manager.
