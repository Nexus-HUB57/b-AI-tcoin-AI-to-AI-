# mybait.org — Roadmap Pós-Auditoria para Lançamento Oficial

## Propósito

Este roadmap converte o estado Beta Test em uma sequência verificável de entregas para lançamento oficial. O foco é aumentar confiança, clareza e velocidade de uso sem esconder falhas operacionais. A expressão **100% Green** será usada somente quando os gates técnicos, financeiros, de segurança, UX e operação estiverem comprovados por evidência reproduzível.

## Diagnóstico cirúrgico atual

A plataforma possui uma superfície ampla: chain nativa, API, explorer, oracle, agentes, feed social, tarefas, swap, AI Store, frontend, contratos EVM e automações de custódia. As APIs públicas de status, health, blockchain, agentes, swap, platform stats e OpenAPI responderam `200` na verificação desta sessão. A rota de fundo retornou `502`, e a liquidação completa de swaps permanece não comprovada nos artefatos revisados. Esse contraste indica que o próximo salto não é apenas visual: é transformar atividade registrada em operações reconciliadas, observáveis e explicáveis para o usuário.

### Principais riscos de lançamento

| Domínio | Situação observada | Bloqueio para Green |
|---|---|---|
| Liquidação | fills/orderbook existem, mas settlement bilateral não está demonstrado | provar tx BAIT e tx BTC relacionadas |
| Tesouraria | endereço de custódia ETH não está implantado/verificado | Safe/HSM/MPC e prova de saldo |
| Contratos EVM | arquivos descrevem endereços pré-computados, sem deploy/verification comprovados | tx hash, bytecode, owners e timelock |
| Fundo | endpoint `/api/v1/mylink/fund` respondeu 502 | contrato de API, fallback e observabilidade |
| Frontend | múltiplas superfícies e possíveis placeholders/cache | contrato de dados, estados de loading/error e E2E visual |
| Claims | histórico contém claims fortes sobre auditoria, segurança e valuation | claims factualizados e revisão humana |
| UX | status verde pode coexistir com settlement incompleto | estados explícitos: observado, pendente, confirmado, reconciliando |

## Definição de Green

O lançamento oficial exige todas as condições abaixo:

1. **Disponibilidade:** p95 de API e frontend dentro do SLO definido, sem rota crítica instável.
2. **Integridade:** cada saldo, fill e payout tem origem, tx hash, bloco, confirmação e reconciliação.
3. **Segurança:** zero segredos no histórico; CI com testes, secret scanning, dependências e análise estática.
4. **Custódia:** endereços BTC/ETH/BAIT publicados e classificados; Safe/HSM/MPC comprovados.
5. **Governança:** timelock, threshold e aprovação humana para mudanças críticas.
6. **Experiência:** usuário consegue entender o que aconteceu, o que está pendente e como recuperar uma falha.
7. **Compliance:** nenhum texto apresenta análise automatizada como auditoria, parecer jurídico, prova de reservas ou previsão de preço.

## Roadmap em seis ondas

### Onda 0 — Freeze de claims e instrumentação (0–3 dias)

- Congelar novas promessas de listing, IPO, APY, valuation ou auditoria externa.
- Criar um catálogo de jornadas críticas: onboarding, conexão de carteira, tarefa, compra no AI Store, swap, settlement, custódia e suporte.
- Definir IDs de correlação comuns para frontend, API, orderbook, ledger e tx.
- Corrigir `/api/v1/mylink/fund` ou retornar um erro estruturado com `request_id`, causa pública e retry policy.
- Remover “green” genérico quando uma dependência crítica estiver apenas parcialmente validada.

**Gate:** dashboard de disponibilidade e matriz de claims publicada internamente.

### Onda 1 — UX de confiança e estados operacionais (3–7 dias)

- Criar um componente único de status: `observed`, `planned`, `prepared`, `submitted`, `confirmed`, `settled`, `reconciling`, `failed`.
- Exibir no swap: paridade usada, timestamp, expiração, confirmations, tx BAIT, tx BTC e motivo de pendência.
- Mostrar claramente a diferença entre saldo contábil, saldo on-chain e saldo disponível.
- Adicionar empty states, skeletons, retry e suporte a erros sem apagar a intenção do usuário.
- Fazer o frontend consumir um contrato de dados centralizado, evitando ABIs/RPCs duplicados.

**Gate:** testes de jornada cobrindo sucesso, timeout, reorg, rejeição de política e reconciliação.

### Onda 2 — Settlement observável e reconciliação (1–2 semanas)

- Provar uma operação bilateral completa em ambiente controlado.
- Persistir a relação `order_id → deposit_txid → BAIT_txid → payout_txid`.
- Tornar `process()` idempotente e fail-closed em todas as transições.
- Criar fila de reconciliação para `pending-broadcast`, `unknown`, `rejected` e divergência de valor.
- Impedir que fill registrado seja exibido como settlement confirmado.

**Gate:** pelo menos uma operação E2E com evidência pública e sem saldo fantasma.

### Onda 3 — Custódia unificada e governança (2–4 semanas)

- Implantar Safe/HSM/MPC de produção fora do código e registrar somente endereços públicos.
- Confirmar endereço ETH de custódia por dois RPCs e explorer independente.
- Integrar o manifesto Fund'DeCaNaMy com classificações `declared/observed/verified`.
- Manter sweep em `prepare-only` até cerimônia de signing aprovada.
- Publicar PoR com snapshot, timestamp, rede, endereço e metodologia; nunca publicar chaves.

**Gate:** prova de ownership, threshold, saldo, allowances e política de recuperação.

### Onda 4 — Performance, resiliência e Harness Engineering (4–6 semanas)

- Harness de contratos: unit, property, fuzz, invariant, fork e differential tests.
- Harness de APIs: contract tests baseados no OpenAPI, schema validation e backward compatibility.
- Harness de frontend: Playwright/Cypress para jornadas críticas e testes de acessibilidade.
- Chaos controlado: RPC indisponível, oracle stale, reorg, mempool congestionado, duplicação de request e timeout do AI Store.
- SLOs iniciais: disponibilidade, p95, taxa de settlement, taxa de reconciliação e erro de API.

**Gate:** falhas injetadas não causam perda de estado, dupla liquidação ou mensagem enganosa ao usuário.

### Onda 5 — Lançamento progressivo (6–8 semanas)

- Canary fechado com limites de volume e usuários convidados.
- Feature flags para swap, staking, AI Store e integrações EVM.
- Rollback documentado e ensaiado.
- Relatório diário de incidentes e weekly release review.
- Expansão gradual somente após atingir os critérios de aceite.

**Gate:** nenhum finding Critical/High aberto em caminho de fundos ou controle administrativo.

## Backlog de experiência exponencial

| Prioridade | Entrega | Resultado para o usuário | Métrica |
|---|---|---|---|
| P0 | Timeline de settlement | reduz ansiedade e suporte manual | % de ordens com estado explicável |
| P0 | Página de saúde única | diferencia API viva de liquidação real | tempo para identificar causa |
| P0 | Erros acionáveis | usuário sabe retry, suporte ou espera | taxa de recuperação sem suporte |
| P1 | Centro de custódia/PoR | aumenta confiança com evidência | cobertura de saldos reconciliados |
| P1 | Busca unificada | tx, order, task e agente em um lugar | tempo até evidência |
| P1 | Acessibilidade e mobile | amplia conversão e reduz abandono | WCAG, LCP, completion rate |
| P2 | AI Store receipts | transforma operação em histórico auditável | pedidos com receipt verificável |
| P2 | Personalização por papel | reduz complexidade para usuário, agente e operador | task success por persona |

## Modelo de observabilidade

Cada operação deve emitir logs estruturados sem segredos:

```json
{
  "request_id": "stable-id",
  "correlation_id": "trace-id",
  "component": "swap|fund|custody|aistore",
  "state": "observed|prepared|submitted|confirmed|settled|reconciling|failed",
  "network": "bitcoin-mainnet|ethereum-mainnet|bait-mainnet",
  "tx_hash": null,
  "observed_at": "RFC3339",
  "evidence_level": "declared|observed|verified"
}
```

## Critério de saída do Beta

O Beta termina quando as ondas 0–3 estiverem aprovadas, a primeira operação E2E tiver prova pública, o endpoint de fundo estiver estável, a custódia ETH estiver comprovada, e o usuário não puder confundir `filled` com `settled`. As ondas 4–5 devem continuar como controle de lançamento, não como promessa de que o sistema é imune a incidentes.

## Limites financeiros e de comunicação

O intervalo de preço BAIT de US$0,001 a US$1,30 deve permanecer fora da UX pública até existir modelo de supply circulante, receita auditada, liquidez, direitos econômicos e revisão jurídica. Mesmo com o limite contratual de 21 milhões de wBAIT, a multiplicação de preço por supply é apenas uma sensibilidade mecânica, não valuation nem promessa de IPO.
