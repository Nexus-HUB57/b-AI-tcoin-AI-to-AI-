# Guia de Deploy Automatizado: Docker e Kubernetes para NEXUS-PULSE e UCP/AP2 (MyBait.org)

## 1. Empacotamento com Docker

Para assegurar consistência entre os ambientes de desenvolvimento e produção real, o servidor NEXUS-PULSE e o gateway UCP/AP2 são empacotados em imagem Docker otimizada.

### 1.1 `Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY baitcoin_mainnet/nexus_pulse_ucp_ap2_server.py /app/server.py

EXPOSE 18445

CMD ["python3", "/app/server.py"]
```

---

## 2. Orquestração com Kubernetes

O manifesto abaixo define o deployment de alta disponibilidade em cluster Kubernetes, garantindo réplicas redundantes e sondas de saúde (*liveness/readiness probes*).

### 2.1 `k8s-nexus-pulse-deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nexus-pulse-ucp-service
  namespace: mainnet
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nexus-pulse
  template:
    metadata:
      labels:
        app: nexus-pulse
    spec:
      containers:
      - name: server
        image: registry.mybait.org/baitcoin/nexus-pulse:v0.8.1
        ports:
        - containerPort: 18445
          name: http
        readinessProbe:
          httpGet:
            path: /api/v1/metrics
            port: 18445
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /
            port: 18445
          initialDelaySeconds: 10
          periodSeconds: 15
        resources:
          limits:
            cpu: "2"
            memory: "4Gi"
          requests:
            cpu: "1"
            memory: "2Gi"
---
apiVersion: v1
kind: Service
metadata:
  name: nexus-pulse-service
  namespace: mainnet
spec:
  selector:
    app: nexus-pulse
  ports:
  - protocol: TCP
    port: 80
    targetPort: 18445
  type: LoadBalancer
```
