# Guia de Testes de Carga e Resiliência: NEXUS-PULSE e Protocolo UCP/AP2 (MyBait.org)

## 1. Estratégia de Validação sob Alta Demanda

Para assegurar que o servidor de telemetria **NEXUS-PULSE** e o gateway de comércio atômico **UCP/AP2** operem sem degradação de performance sob concorrência extrema de enxames de agentes, estruturamos um plano de testes de carga utilizando ferramentas padrão de mercado (**Locust** e **k6**).

---

## 2. Cenários de Testes Recomendados

| Tipo de Teste | Ferramenta | Alvo / Endpoint | MMeta de Desempenho / KPI |
| :--- | :--- | :--- | :--- |
| **Teste de Carga (Load Test)** | Locust / k6 | `GET /api/v1/metrics` | 5.000 requisições simultâneas com latência p99 < 15 ms. |
| **Teste de Estresse de Checkout** | Locust | `POST /ucp/checkout` | 2.000 requisições/segundo de mandatos AP2 simulando estouro de *spending cap* (validação de rejeição 400). |
| **Teste de Pico (Spike Test)** | k6 | Endpoints UCP e de Telemetria | Salto abrupto de 200 para 10.000 conexões ativas em 10 segundos, avaliando auto-scaling do cluster. |
| **Teste de Ruptura (Soak Test)** | k6 | Sistema Completo (24 horas) | Execução contínua de rotinas de pagamento AP2 para detectar vazamentos de memória ou estouro de descritores de arquivo. |
