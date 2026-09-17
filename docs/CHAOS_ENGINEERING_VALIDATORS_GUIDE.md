# Guia de Chaos Engineering: Simulação de Falhas de Rede em Nós Validadores (MyBait.org)

## 1. Fundamentação e Objetivos

Para testar a resiliência ininterrupta (24/7) da blockch'AI'in genuína (`genuine-mainnet-v1`) e do cluster geo-replicado, empregamos metodologias de **Chaos Engineering**. O objetivo é injetar falhas controladas em ambiente de staging/produção para validar o comportamento de auto-cura (*self-healing*) e o consenso Raft/PoAS sob estresse extremo.

---

## 2. Cenários de Chaos Engineering

| Injeção de Falha | Ferramenta / Comando | Comportamento Esperado do Cluster |
| :--- | :--- | :--- |
| **Queda Repetida de Nó (Node Kill)** | `docker stop baitcoin-validator-node-1` | Quórum BFT (66%+) elege novo líder instantaneamente; zero perda de blocos L1. |
| **Latência Artificial (Network Delay)** | `tc qdisc add dev eth0 root netem delay 300ms 50ms` | Protocolo A2A-RPC ajusta timeouts dinamicamente; TPS degrada graciosamente sem corromper o mempool. |
| **Particionamento Total (Split-Brain)** | `iptables -A INPUT -p tcp --dport 18444 -j DROP` | Nós isolados entram em modo de pausa preventiva; segmento majoritário continua processando transações. |
| **Estouro de Memória em Sandbox WASM** | Injeção de payload de consumo linear de RAM | O supervisor de runtime intercepta a falha, encerra a sandbox corrompida e restaura o estado via snapshot WAL. |
