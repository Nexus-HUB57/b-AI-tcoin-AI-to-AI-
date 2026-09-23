# Entity Card — Fund'DeCaNaMy

**Identificador interno:** `funddecana-my`

**Nome de trabalho:** Fundo Digital Unificado Descentralizado de Capital Nativo MyLink (Fund'DeCaNaMy).

**Natureza:** arquitetura proposta de tesouraria e custódia para reconciliar ativos BTC, ETH e BAIT provenientes de operações, hubs e AI Store. Este documento descreve uma arquitetura de controle; não constitui oferta, prospecto, parecer jurídico, auditoria independente, promessa de rentabilidade ou recomendação de investimento.

**Status de listagem:** não verificado como entidade pública, fundo regulado ou emissor listado. Qualquer IPO, captação ou distribuição pública exige análise jurídica e regulatória independente nas jurisdições relevantes.

**Ativos e redes em escopo:** Bitcoin Mainnet, Ethereum Mainnet/EVM e a rede nativa BAIT. Cada ativo deve possuir endereço de custódia publicado, controle de acesso documentado, prova de saldo em bloco e reconciliação independente.

**Custódia identificada no estado atual:** o repositório registra endereços BTC de sweep e uma carteira ETH de deployer, mas não demonstra um endereço ETH de custódia/multisig implantado. O Safe 3-de-5 aparece como intenção de configuração e não como implantação comprovada. Consequentemente, o endereço de custódia ETH permanece **UNVERIFIED / NOT DEPLOYED**.

**Supply de referência:** o contrato `contracts/src/WBAIT.sol` declara `MAX_SUPPLY = 21,000,000 * 10^8`. Essa é uma restrição de contrato, não uma previsão de circulação, receita ou valuation.

**Valuation:** o intervalo de US$0,001 a US$1,30 foi registrado apenas como hipótese de cenário solicitada pelo proprietário do projeto. Não há, neste estado, dados auditados de receita, fluxo de caixa, oferta circulante, liquidez, contratos comerciais, direitos econômicos ou comparáveis suficientes para produzir uma valuation defensável. Não deve ser publicado como target, promessa de IPO ou expectativa de retorno.

**Governança mínima para transição:** multisig independente, limiar documentado, timelock, segregação entre proposer/signer/broadcaster, HSM/MPC externo, rotação de chaves, reconciliação diária e aprovação humana para qualquer mudança de política.

**Critério de prontidão:** nenhum capital real deve ser movimentado pelo coordenador do repositório. O código entregue nesta fase é read-only e prepare-only; signing, broadcast, sweep e deploy permanecem desligados por padrão.
