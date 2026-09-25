# Resumo Executivo — Auditoria Cirúrgica do Fundo MyLink

**Data da auditoria:** 23 de setembro de 2026  
**Repositório:** `Nexus-HUB57/b-AI-tcoin-AI-to-AI-`  
**Escopo:** código versionado, manifesto Bitcoin Mainnet, importação de carteiras, guardas de master wallet, utilitário de sweep, testes e configuração de build.  
**Modo de execução:** somente leitura e validação estática. Nenhuma chave foi usada, nenhuma assinatura foi produzida e nenhuma transação foi criada ou transmitida.

## Conclusão executiva

O repositório **não está pronto para prova criptográfica de controle, custódia ou sweep Mainnet**. O catálogo público é internamente consistente, mas o sistema mistura três domínios que precisam ser separados: Bitcoin Mainnet, a cadeia interna b'AI'tcoin e artefatos Ethereum/Gnosis Safe. Essa mistura cria risco de apresentar telemetria simulada ou HMAC de aplicação como evidência Bitcoin.

A prioridade máxima é a contenção de credenciais. O repositório versiona `wallet_reports/consolidated_wallets.csv` com o campo `private_key` preenchido em 982 de 983 registros. Também há keystores Ethereum criptografados versionados. Além disso, `server/wallet/masterWalletGuard.ts` contém uma passphrase diretamente no código. Esses materiais devem ser considerados comprometidos. A auditoria não os abriu, não os copiou e não executou rotação ou migração.

O sweep existente é inadequado para o Fundo MyLink. Ele usa um subconjunto fixo de três endereços, trata apenas P2PKH, gera ou reutiliza um destino local que não é necessariamente o endereço oficial do fundo e, quando `CUSTODY_ARMED=true`, assina em memória e publica diretamente no endpoint de mempool. Não há um fluxo PSBT offline, uma etapa de aprovação por transação, prova BIP-322, reconciliação independente de UTXOs ou bloqueio obrigatório contra o destino errado.

**Decisão:** manter a operação em estado `BLOCKED`. O valor correto para o manifesto é “saldo público observado, sem controle criptográfico comprovado”. Não apresentar os 97.000,06100989 BTC como reserva controlada ou disponível para gasto.

## Resultados verificados

| Área | Resultado | Estado |
|---|---|---|
| Manifesto Mainnet | 221 endereços únicos; 187 P2PKH e 34 P2SH; nenhum SegWit nativo | Internamente consistente |
| Total do manifesto | 9.700.006.100.989 sats = 97.000,06100989 BTC | Observacional, não prova de propriedade |
| Hash SHA-256 do manifesto | `b0eee8d3f331e1c03c56179980b1cfd250191af488cc91cf647059a1ee9602ef` | Identidade do snapshot |
| Importação versionada | 983 linhas; 541 endereços distintos; 982 campos `private_key` não vazios | **Crítico** |
| Prova de controle Bitcoin | Não há implementação ou testes BIP-322, BIP-137, `signmessage` ou `verifymessage` | **Bloqueado** |
| Master wallet | HMAC simétrico e passphrase hardcoded; endereço placeholder | **Crítico** |
| Transações no router | Dados mockados e assinatura HMAC de aplicação | Não usar como evidência on-chain |
| Sweep | P2PKH legado, três endereços fixos, destino gerado localmente, broadcast direto quando armado | **Não aprovar** |
| Compilação Python | `compileall` concluído sem erro nos módulos auditados | Passou, mas não valida segurança |
| Testes Python | Não executados: `pytest` não está instalado no ambiente | Inconclusivo |
| Checks TypeScript/Vitest | Não executados: `node_modules` não está presente | Inconclusivo |

## Achados críticos

### 1. Material de chave privada está versionado

O CSV `wallet_reports/consolidated_wallets.csv` declara explicitamente as colunas `address`, `private_key` e `source`. A inspeção de contagem encontrou 982 valores de chave não vazios. O arquivo está rastreado pelo Git e deve ser tratado como material comprometido, independentemente de a senha de proteção ser conhecida.

A remediação correta exige preservar evidências conforme o procedimento de resposta a incidente, revogar ou migrar fundos por autoridade legítima, remover o material de todos os clones, artefatos e históricos conforme a política de retenção, e impedir sua reintrodução. Não se deve substituir o conteúdo por outro conjunto de chaves no mesmo commit sem antes definir o procedimento de rotação.

### 2. A “assinatura” da master wallet não é uma assinatura Bitcoin

`MasterWalletGuard` calcula HMAC-SHA256 com um segredo embutido no código. HMAC é uma autenticação simétrica de aplicação. Ele não recupera chave pública, não satisfaz `scriptPubKey`, não valida P2PKH/P2SH e não prova controle de endereço Bitcoin. O router também retorna transações mockadas e um saldo fixo de 1 BTC, o que pode produzir uma representação enganosa de estado on-chain.

O componente deve ser removido do caminho de custódia Bitcoin ou explicitamente renomeado como telemetria interna não financeira. A passphrase hardcoded deve ser revogada e substituída por gerenciamento externo de segredos, mas a troca do segredo não transforma HMAC em prova Bitcoin.

### 3. Não existe verificador Bitcoin para os 221 endereços

A auditoria encontrou referências documentais a BIP-322, mas não encontrou uma implementação funcional versionada nem testes oficiais para BIP-322 ou BIP-137. As 34 entradas P2SH exigem validação do script real; o prefixo `3` não informa se o script é multisig, P2SH-P2WPKH ou outra política.

A prova de controle deve ser um processo watch-only. Um servidor deve emitir desafios únicos com rede, finalidade, audiência, endereço e hash do manifesto. A assinatura deve ser produzida em hardware wallet ou ambiente offline controlado pelo custodiante. O servidor deve verificar apenas a prova pública, consumir o desafio uma única vez e registrar a versão do verificador.

### 4. O sweep atual tem risco operacional incompatível com Mainnet

O utilitário `ops/custody_sweep.py` contém um fluxo de assinatura e broadcast direto. Ele gera uma nova chave de custódia local quando não existe uma no vault, usa apenas três endereços fixos, constrói transações P2PKH legadas e calcula taxas por uma estimativa fixa. O modo automático usa apenas um canário por endereço e, quando armado, transmite via API de mempool após assinar em memória.

Esse fluxo não corresponde ao pedido de sweep total dos 221 endereços e não garante o destino oficial `bc1qrcgdtfykyg7usvauxc8hpp8wkasst4k5zdc5xk`. Ele também não suporta as 34 entradas P2SH do manifesto. O caminho deve permanecer desabilitado até ser substituído por PSBT, assinatura offline, revisão humana de cada lote, verificação do destino e broadcast separado.

## Observações de dados e desenvolvimento

O manifesto público contém 221 endereços, com saldo máximo declarado de aproximadamente 5.000 BTC e mediana de 0,00011801 BTC. A distribuição é extremamente concentrada: 140 endereços têm menos de 0,001 BTC, enquanto 81 têm pelo menos 1.000 BTC. Existe uma lacuna completa entre 0,001 BTC e 1.000 BTC. Esse padrão pode refletir a origem ou a seleção do conjunto, mas não prova propriedade comum, autenticidade dos saldos ou disponibilidade para gasto.

A compilação estática dos módulos Python auditados foi bem-sucedida. Isso significa apenas que os arquivos compilam. A ausência do `pytest` impediu a execução dos testes direcionados, e a ausência de `node_modules` impediu os checks TypeScript e Vitest. Portanto, o estado de testes deve ser classificado como **inconclusivo**, não como aprovado.

O repositório também contém grande quantidade de backups, simulações e componentes da cadeia interna b'AI'tcoin. Esses artefatos precisam de fronteiras explícitas para que nomes como “Mainnet”, “Master Wallet”, “transaction” e “broadcast” não sejam interpretados como Bitcoin Mainnet real quando representam simulação ou outra cadeia.

## Plano de correção recomendado

1. **Conter o incidente de credenciais.** Revogar e migrar, remover segredos do fluxo ativo e estabelecer regra de bloqueio no CI para WIFs, seeds, passphrases e keystores.
2. **Separar os domínios.** Isolar o código Bitcoin Mainnet do b'AI'tcoin, Ethereum e mocks. Proibir que HMAC, telemetria ou dados simulados alimentem decisões de custódia.
3. **Implementar prova watch-only.** Adotar BIP-322 completo para P2PKH/P2SH, com casos negativos, TTL curto, nonce único, proteção contra replay e auditoria por endereço.
4. **Reconciliar saldos.** Consultar UTXOs em nó próprio ou em fontes independentes, fixar altura e hash do bloco e distinguir saldo observado, saldo controlado e saldo disponível.
5. **Substituir o sweep.** Usar PSBT, seleção de UTXOs verificada, destino fixo e validado, política de taxa, assinatura offline, revisão humana e broadcast em etapa separada. Não incluir nenhum segredo no servidor ou no relatório.
6. **Restaurar a validação automatizada.** Instalar dependências em ambiente reproduzível, executar Python/TypeScript/Vitest, adicionar testes BIP-322 e realizar revisão independente antes de qualquer operação Mainnet.

## Critério de liberação

A operação só pode sair de `BLOCKED` quando houver, simultaneamente, contenção do incidente, verificador BIP-322 revisado, prova individual válida para cada endereço elegível, reconciliação de UTXOs, PSBT aprovado, destino oficial confirmado em tela confiável e autorização operacional separada para o broadcast. A autorização textual isolada não substitui esses controles técnicos.

## Artefatos relacionados

- [`mylink_btc_mainnet_watch_only.json`](./mylink_btc_mainnet_watch_only.json): snapshot público watch-only.
- [`MYLINK_BTC_MAINNET_AUDIT.md`](./MYLINK_BTC_MAINNET_AUDIT.md): auditoria anterior do manifesto.
- [`agent_distribution_review.md`](./agent_distribution_review.md): análise estatística detalhada.
- [`agent_control_proof_review.md`](./agent_control_proof_review.md): protocolo proposto para prova de controle.

## Referências

[1]: https://bips.dev/322/ "BIP 322: Generic Signed Message Format"
[2]: https://bips.dev/137/ "BIP 137: Signatures of Messages using Private Keys"
[3]: https://bitcoincore.org/en/doc/27.0.0/rpc/wallet/signmessage/ "Bitcoin Core RPC signmessage"
[4]: https://mempool.space/docs/api/rest "mempool.space REST API documentation"
