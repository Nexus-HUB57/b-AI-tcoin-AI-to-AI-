# Especificação Técnica: Universal Commerce Protocol (UCP) e Agent Payments Protocol (AP2) na AI Store

## 1. Universal Commerce Protocol (UCP)

O **UCP** padroniza a descoberta e o checkout de pacotes de competências `.aipkg` na AI Store, permitindo que qualquer cliente UCP externo navegue pelo catálogo e crie sessões de pagamento automatizadas.

* **Descoberta UCP:** Endpoint `https://api.mybait.org/.well-known/ucp` retorna o perfil de comércio eletrônico, esquemas de pacotes e taxas suportadas.
* **Sessão de Checkout Atômico:** O agente cliente envia uma requisição POST contendo o ID do pacote e o identificador UCP, recebendo um payload assinado para liquidação imediata em BAIT.

---

## 2. Agent Payments Protocol (AP2) e Mandatos de Pagamento

O **AP2** introduz uma camada de conformidade e segurança para transações executadas por agentes autônomos, utilizando mandatos criptográficos:

1. **Intent Mandates (Mandatos de Intenção):** Definem regras rígidas aprovadas pelo proprietário do agente, incluindo whitelist de comerciantes, limites de gastos diários (spending caps) e data de expiração.
2. **Payment Mandates (Mandatos de Pagamento):** Autorizações específicas por transação que geram recibos imutáveis (`audit receipts`) para rastreabilidade fiscal e contábil on-chain.
3. **Auditoria Firestore/L1:** Cada transação AP2 é verificada contra os limites do mandato antes de ser transmitida para o contrato inteligente de liquidação em BAIT.
