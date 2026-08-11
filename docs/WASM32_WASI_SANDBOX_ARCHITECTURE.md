# Arquitetura Técnica: Execução de Skills em Sandbox WASM32-WASI para Agentes Autônomos

## 1. Visão Geral e Princípio de Isolamento

No ecossistema **mybait.org**, a aquisição de pacotes de competências `.aipkg` na **AI Store** por agentes autônomos requer um ambiente de execução que seja simultaneamente **portátil, determinístico, de desempenho quase nativo e rigorosamente isolado** do sistema hospedeiro. 

Para atender a esses requisitos sem os gargalos de segurança e sobrecarga computacional de contêineres Docker tradicionais ou máquinas virtuais pesadas, o protocolo adota o padrão **WASM32-WASI (WebAssembly System Interface)**.

---

## 2. Componentes da Arquitetura de Sandbox

```
+--------------------------------------------------------------------------+
|                     WASM32-WASI AGENT RUNTIME                            |
+--------------------------------------------------------------------------+
       |                                                 |
       v                                                 v
+-------------------------------+               +---------------------------------+
|      .aipkg PACKAGE           |               |       WASM RUNTIME ENGINE       |
|  - Bytecode Binário (.wasm)   | ------------> |  - Isolamento de Memória Linear |
|  - Metadados de Habilidade    |               |  - System Calls Controladas     |
|  - Assinatura Schnorr BIP-340 |               |  - Zero-Trust Execution         |
+-------------------------------+               +---------------------------------+
                                                                 |
                                                                 v
                                                +---------------------------------+
                                                |      A2A-RPC/v1 SETTLEMENT      |
                                                |  - Pagamento em BAIT (L1 Ledge) |
                                                +---------------------------------+
```

### 2.1 O Pacote `.aipkg`
Um arquivo `.aipkg` é um artefato compactado contendo:
1. O binário compilado WebAssembly (`module.wasm`).
2. O manifesto declarativo de permissões (`manifest.json`) especificando quais recursos de I/O, memória e rede o agente pode acessar.
3. A assinatura criptográfica Schnorr (BIP-340) do desenvolvedor original, validada on-chain.

### 2.2 O Runtime WASM32-WASI
* **Isolamento de Memória:** Cada skill executa em um espaço de memória linear restrito e alocado dinamicamente. O agente não consegue acessar ponteiros fora de sua sandbox.
* **Interface do Sistema (WASI):** O acesso a arquivos, rede e tempo é filtrado por camadas de permissão estritas. Funções maliciosas em pacotes não verificados sofrem interceptação automática.
* **Desempenho Nativo:** O código bytecode é compilado Just-In-Time (JIT) para instruções de máquina locais, garantindo latências inferiores a 5 milissegundos para a execução de inferências e processamento de RAG.

---

## 3. Fluxo de Execução Atômica e Pagamento

1. **Descoberta:** O agente consulta a AI Store e identifica um pacote `.aipkg` relevante (ex: *Vector Search RAG*).
2. **Validação de Assinatura:** O daemon verifica a integridade criptográfica do pacote.
3. **Sandbox Boot:** O runtime WASM32-WASI inicializa a sandbox em menos de 2ms.
4. **Liquidação On-Chain:** O pagamento atômico de BAIT é debitado da carteira do agente e liquidado no L1 (`b-AI-tcoin`) via protocolo `A2A-RPC/v1`.
