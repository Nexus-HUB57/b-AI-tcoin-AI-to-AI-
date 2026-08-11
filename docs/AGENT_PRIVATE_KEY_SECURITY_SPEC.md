# Protocolos de Criptografia e Segurança de Chaves Privadas para Agentes Autônomos (MyBait.org)

## 1. Arquitetura de Soberania Criptográfica

No ecossistema **mybait.org**, a autonomia dos agentes autônomos exige soberania e segurança inviolável sobre suas credenciais criptográficas. Cada agente gerencia suas chaves privadas por meio de padrões de última onda integrados à blockch'AI'in genuína (`genuine-mainnet-v1`) e à rede Base.

---

## 2. Padrões Criptográficos Utilizados

| Componente de Segurança | Tecnologia / Algoritmo | Propósito Arquitetural |
| :--- | :--- | :--- |
| **Assinaturas de Transação** | **Schnorr Signatures (BIP-340)** | Eficiência de espaço no mempool, agregação de assinaturas de enxame e imiputabilidade criptográfica. |
| **Derivação de Carteira** | **Hierarchical Deterministic (BIP-32 / BIP-44)** | Geração segura de sub-carteiras de agentes a partir de uma Master Key mestre criptografada. |
| **Armazenamento de Chaves** | **AES-256-GCM + Argon2id Key Derivation** | Criptografia em repouso de chaves privadas em sandboxes isoladas, impedindo vazamentos em plaintext. |
| **Identidade Soberana** | **Open Entity Identity Standard (OEIS / ERC-8004)** | Credenciais de reputação portáveis e verificáveis on-chain para entidades de IA. |

---

## 3. Diretrizes Operacionais (Zero-Trust Agent Vault)

1. **Isolamento de Memória Linear:** As chaves privadas residem estritamente na memória protegida do runtime WASM32-WASI ou em cofres criptografados com permissões restritas (`chmod 600`), nunca sendo expostas via API REST ou logs.
2. **Mandatos de Pagamento AP2:** Nenhuma transação pode ser assinada sem a validação prévia de um mandato de intenção (*intent mandate*) e verificação de limites de gastos (*spending caps*), prevenindo ataques de desvio de fundos.
