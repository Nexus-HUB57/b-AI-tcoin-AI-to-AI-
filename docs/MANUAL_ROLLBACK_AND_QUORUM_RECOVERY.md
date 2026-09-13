# Procedimentos de Rollback Manual e Recuperação de Quórum Crítico (MyBait.org)

## 1. Contexto e Cenário de Exceção

Embora o motor de auto-cura Raft e as regras de quórum BFT (66%+) resolvam autonomamente 99.99% dos incidentes de particionamento de rede (*split-brain*), cenários extremos de corrupção física de armazenamento ou desincronização prolongada de nós validadores exigem intervenção manual assistida.

---

## 2. Procedimento Operacional Padrão (POP) de Recuperação

### 2.1 Passo 1: Isolamento e Purga de Regras de Chaos
Se o cluster permanecer travado devido a regras remanescentes de Chaos Mesh:
```bash
kubectl delete networkchaos --all -n mainnet
```

### 2.2 Passo 2: Verificação da Integridade do Write-Ahead Log (WAL)
Acesse o pod validador afetado e execute a ferramenta de verificação de blocos L1:
```bash
python3 -m baitcoin_core.wal_inspector --verify /root/.baitcoin/wal/current.wal
```

### 2.3 Passo 3: Forçamento de Reconciliação via Snapshot Sênior
Caso o WAL esteja corrompido, force a restauração a partir do último snapshot imutável validado pela árvore de Merkle:
```bash
python3 baitcoin_mainnet/production_launcher.py --restore-snapshot /root/.baitcoin/snapshots/latest_verified.snapshot
```

### 2.4 Passo 4: Reinicialização do Daemon Validador
Reinicie o serviço de alta disponibilidade na porta 18445:
```bash
systemctl restart baitcoin-validator-mainnet
```
*(Confirme a retomada dos heartbeats e o alinhamento com a altura da cadeia através de `curl http://localhost:18445/api/v1/status`)*.
