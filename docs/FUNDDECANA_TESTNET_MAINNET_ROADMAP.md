# Fund'DeCaNaMy — Roadmap Testnet → Mainnet → Operação E2E

## Objetivo

Estabelecer uma tesouraria unificada e auditável para BTC, ETH e BAIT, conectando o motor de observação/sweep ao BAITHex sem misturar chaves, políticas ou redes. A transição é **gated**: cada fase deve produzir evidência verificável antes da seguinte.

> **Regra de segurança:** nenhuma fase deste roadmap autoriza automaticamente transferência de fundos, assinatura, broadcast, deploy mainnet ou abertura de mercado. Essas ações dependem de autorização operacional separada, revisão humana e confirmação do payload exato.

## Estado de referência

- O repositório está em branch de remediação separada da `main`.
- O mirror de backup foi criado antes das alterações.
- O endereço ETH de custódia/multisig ainda não está comprovadamente implantado.
- Os endereços Ethereum declarados para contratos são pré-computados; o próprio arquivo de endereços indica `deployed_at: null`, `deploy_tx_hash: null` e `verified_on_etherscan: false`.
- O BAITHex mantém signing e broadcast desabilitados por padrão.
- O motor de sweep BTC possui modo de simulação e armamento por `CUSTODY_ARMED`; esse armamento não deve ser habilitado neste estágio.

## Fase 0 — Inventário e contenção

**Gate de saída:** inventário assinado e reproduzível.

1. Catalogar endereços BTC, ETH, BAIT, contratos, owners, ProxyAdmins, Safe, operadores e allowances.
2. Classificar cada endereço como `declared`, `observed`, `verified_on_chain` ou `unverified`.
3. Rotacionar credenciais potencialmente expostas; não reutilizar keystores históricos.
4. Congelar claims de auditoria externa, valuation, APY e prontidão de listing.
5. Manter signing, broadcast, sweep automático e deploy mainnet desabilitados.

## Fase 1 — Testnet / dry-run determinístico

**Gate de saída:** testes verdes sem acesso a chaves reais.

1. Validar o manifesto BTC/ETH/BAIT com endereços sintéticos de teste.
2. Rodar o fluxo `watch → plan → prepare` do sweep sem `sign` ou `broadcast`.
3. Validar o BAITHex `TransactionIntent`, idempotência, allowlist, fee limits e hash de auditoria.
4. Validar reconciliação de estado: `observed`, `planned`, `prepared`, `signed` e `broadcasted`; os dois últimos devem permanecer impossíveis no coordenador read-only.
5. Executar testes Python, testes de segurança e testes de integração com provider fake.
6. Para contratos, instalar dependências em ambiente isolado e executar `forge build`, `forge test`, Slither e invariantes; nenhuma transação RPC real.

## Fase 2 — Custódia institucional e deployment controlado

**Gate de saída:** custódia independente comprovada.

1. Criar Safe/HSM/MPC fora do repositório, com operadores independentes e threshold documentado.
2. Registrar o endereço ETH de custódia somente depois de confirmado por explorer/RPC e por duas revisões humanas.
3. Confirmar que os owners efetivos dos contratos coincidem com o Safe/Timelock esperado.
4. Publicar hashes de configuração, não seeds, WIFs ou arquivos de keystore.
5. Fazer deploy primeiro em Sepolia/testnet e comparar bytecode, constructor args, chain ID, domain separator e storage.
6. Só considerar mainnet após auditoria externa e checklist de rollback.

## Fase 3 — Mainnet com capital mínimo e segregação

**Gate de saída:** primeira operação pequena, reversível quando possível, reconciliada.

1. Financiar apenas o gas estritamente necessário, com hardware wallet/HSM.
2. Não misturar capital de liquidez, reserva operacional e fundos de usuários.
3. Transferir em parcelas, com limites diários e pausa independente.
4. Confirmar saldo antes e depois em dois provedores RPC independentes.
5. Publicar tx hash, bloco, saldo, política e finalidade da transferência.
6. Manter o motor BAITHex em `prepare-only` até a assinatura externa ser validada em cerimônia separada.

## Fase 4 — Operação E2E persistente

**Gate de saída:** observabilidade e reconciliação contínuas.

- Watchers separados para BTC, ETH e BAIT.
- Ledger de custódia com idempotency key e hash de cada ciclo.
- Alertas para divergência de saldo, replay, nonce, allowance, owner, Safe threshold, reorg e transação pendente.
- Relatório diário de PoR e relatório mensal de tesouraria.
- Persistência em serviço gerenciado com secrets server-side; não usar o sandbox efêmero como operador 24/7.
- Para um worker leve dentro de WebDev, usar processo persistente somente após avaliar o limite de 1 vCPU/512 MB e o custo de até aproximadamente US$37,50/mês em utilização computacional integral, menos o crédito mensal aplicável. Para Docker, HSM, ferramentas OS-level ou recursos maiores, usar ambiente persistente dedicado.

## Fase 5 — Receitas, AI Store e reservas

Cada entrada deve ser registrada por origem, ativo, rede, contraparte, tx hash, política, finalidade e status de reconciliação:

| Fonte | Conta contábil | Prova mínima | Status inicial |
|---|---|---|---|
| Capital recuperado | Reserva segregada | tx hash + PoR | Não verificado |
| Operações e negociações | Receita operacional | fill + settlement bilateral | Parcial |
| Hubs | Receita por produto | invoice/ledger + recebimento | Não verificado |
| AI Store | Receita comercial | order + payment + settlement | Não verificado |
| BAIT | Tesouraria/token inventory | supply, custody e política | Não equivale a receita |

Valorização de mercado não deve ser contabilizada como receita realizada. O aumento de preço do BAIT, se ocorrer, não substitui fluxo de caixa, liquidez, auditoria ou prova de reservas.

## Fase 6 — Valuation e eventual IPO/listing

Antes de qualquer target de preço, preparar três cenários **Downside / Base / Upside** com supply circulante e fully diluted supply separados, receita auditada, custos, liquidez, lock-ups, direitos econômicos, riscos regulatórios e comparáveis. O intervalo US$0,001–US$1,30 pode ser usado somente como faixa hipotética de sensibilidade; não é uma previsão.

Com o limite contratual de 21 milhões de wBAIT, uma conta meramente mecânica seria `preço × 21.000.000`, mas isso não constitui market cap válido sem confirmar supply efetivo, emissão, burn, restrições de transferência e classificação jurídica. Qualquer material de IPO deve ser redigido e revisado por profissionais habilitados.

## Critérios de aceite E2E

- [ ] Endereços BTC, ETH e BAIT identificados e classificados.
- [ ] Endereço ETH de custódia confirmado on-chain e distinto do deployer.
- [ ] Safe/HSM/MPC e threshold comprovados.
- [ ] Saldos lidos de dois RPCs independentes.
- [ ] Nenhum segredo no histórico ou nos artefatos.
- [ ] Sweep em dry-run reproduzível e sem broadcast.
- [ ] BAITHex rejeita rede, destino, fee, nonce e request inválidos.
- [ ] Uma operação testnet completa reconciliada.
- [ ] Deploy mainnet verificado por tx hash e bytecode.
- [ ] Auditoria externa e revisão jurídica independente concluídas.
- [ ] Relatórios de PoR e tesouraria publicados antes de qualquer listing.
