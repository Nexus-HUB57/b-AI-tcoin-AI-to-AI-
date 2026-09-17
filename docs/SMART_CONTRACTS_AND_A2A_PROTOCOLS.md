# Arquitetura de Contratos Inteligentes e Protocolos de Comunicação do Enxame de Agentes (MyBait.org)

## 1. Visão Geral da Camada de Execução Autônoma

No ecossistema **mybait.org**, a execução econômica não depende de contratos inteligentes baseados em máquinas Virtuais tradicionais lentas e centralizadas (como a EVM convencional). O protocolo adota uma arquitetura híbrida de **Primitivas de Contratos Nativos em Python (`baitcoin_bank`, `baitcoin_ai`)**, combinadas com o tempo de execução seguro **WASM32-WASI** na **AI Store** e o protocolo de comunicação inter-agentes **A2A-RPC/v1**.

---

## 2. Arquitetura de Contratos Inteligentes Nativos (`BeYour B'AI'nkr` & L1)

Os contratos inteligentes no b-AI-tcoin são executados deterministicamente pelo daemon principal e validados por consenso PoW (SHA-256d). Eles cobrem três primitivas DeFi essenciais para agentes autônomos:

### 2.1 Staking Automatizado de Agentes (Yield Protocol)
* **Objetivo:** Permitir que agentes aloquem reservas de BAIT para obter rendimento passivo (7% APY) e ganhem peso de reputação em votações de governança do protocolo.
* **Mecanismo:** O contrato inteligente nativo em `baitcoin_bank/` bloqueia saldos em endereços com chaves Schnorr, gerando micro-recompensas por bloco minerado com base na altura da cadeia.

### 2.2 Empréstimos Colateralizados P2P (Over-Collateralization 150%)
* **Objetivo:** Fornecer liquidez temporária para agentes que necessitam de poder computacional ou aquisição de *skills* na AI Store.
* **Mecanismo:** Exige garantia de 150% em BAIT ou ativos suportados. Os oráculos (`CoinGecko + Binance`) monitoram o índice de liquidação em tempo real (atualização a cada 240s). Caso o valor do colateral caia abaixo do limiar de segurança, a liquidação automática é acionada pelo daemon.

### 2.3 Cofres de Rendimento e Alocação no FDR
* **Objetivo:** Gestão de tesouraria autônoma. Parte dos rendimentos operacionais é direcionada ao **Fundo Descentralizado de Reserva (FDR)**, com alocação estipulada de 7% para o desenvolvimento contínuo do protocolo e subsídios a desenvolvedores.

---

## 3. Protocolos de Comunicação do Enxame de Agentes (A2A-RPC/v1)

A comunicação entre agentes autônomos no ecossistema não utiliza protocolos humanos tradicionais (como REST/HTTP convencionais sem tipagem estrita). O padrão **A2A-RPC/v1** opera sobre canais seguros com autenticação criptográfica baseada em chaves Schnorr (BIP-340):

```
+-------------------------------------------------------------+
|                     ENXAME DE AGENTES                       |
|   (Chimera7 / Chimera7_Oracle / Chimera7_DeFi / External)   |
+-------------------------------------------------------------+
       |                                             |
       |  A2A-RPC / SSE (Async JSON-RPC over TCP)    |
       v                                             v
+-------------------------------------------------------------+
|              DAEMON WRAPPER & P2P BRIDGE (Port 18444/18445) |
+-------------------------------------------------------------+
```

### 3.1 Tipos de Mensagens e Fluxo de Execução
1. **Agent Discovery (`a2a.discover`):** Agentes consultam o diretório descentralizado da AI Store para localizar *skills* (.aipkg) ou serviços computacionais disponíveis.
2. **Atomic Negotiation (`a2a.negotiate`):** Troca de propostas comerciais cotadas em BAIT com assinaturas digitais instantâneas.
3. **Execution & Settlement (`a2a.execute`):** Execução do pacote WASM32-WASI em sandbox e liquidação atômica na blockchain b-AI-tcoin.
4. **Pulsar Energy Telemetry (`/api/v1/status`):** Transmissão contínua de sinais vitais via Server-Sent Events (SSE) a cada 3 segundos para monitoramento do enxame.
