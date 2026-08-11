# Guia de Auditoria: Conformidade de Contratos Inteligentes com Mandatos AP2 (AI Store)

## 1. Princípios de Auditoria AP2

O **Agent Payments Protocol (AP2)** exige que toda interação financeira entre agentes autônomos na AI Store e nos contratos inteligentes de staking/empréstimo (`BaitStakingPool`, `BaitP2PLending`, `A2AStoreRegistry`) seja rigorosamente auditável. O processo de auditoria verifica se a execução on-chain respeita estritamente os mandatos de intenção (*intent mandates*).

---

## 2. Procedimentos Práticos de Auditoria

### 2.1 Verificação de Limites de Gastos (*Spending Caps*)
* **Auditoria de Payload:** Cada transação UCP/AP2 é inspecionada para garantir que o montante em BAIT transferido não ultrapasse o teto diário autorizado pelo proprietário do agente.
* **Validação de Assinatura Schnorr:** Confirmação criptográfica de que o mandato foi assinado com a chave privada mestre derivada via BIP-32/44.

### 2.2 Rastreabilidade de Recibos Imutáveis (`Audit Receipts`)
* O auditor gera um hash SHA-256 de cada sessão de checkout bem-sucedida, comparando o registro armazenado no banco de dados com o evento emitido no contrato inteligente L1.
* Divergências acionam bloqueio preventivo automático do agente no registro de enxame.
