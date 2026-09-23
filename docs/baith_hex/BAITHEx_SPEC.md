# BAITHex — especificação clean-room

## Escopo

O BAITHex é uma camada própria de orquestração de transações para Bitcoin Mainnet e redes EVM compatíveis com HEX. Esta implementação é **Mainnet-only**: não cria, executa ou habilita regtest, testnet, faucet, signer simulado ou broadcast de teste. O código usa padrões públicos e interfaces originais; não copia código proprietário, parâmetros internos ou APIs privadas de custodiante.

## Componentes implementados

### `baith_policy`

O `policy-engine` valida uma intenção de transação antes da assinatura. A política exige `bitcoin-mainnet`, `policy_id`, `request_id`, inputs no formato `txid:vout`, exatamente um output de destino, destino em allowlist, change em allowlist, valor positivo, fee e fee rate dentro dos limites e payload unsigned em hexadecimal válido.

A política não interpreta uma assinatura nem transmite. A montagem final deve repetir a validação depois do retorno do signer, incluindo decode independente de inputs, outputs, scripts, fee e rede.

### `baith_exchange`

O `baith-exchange` mantém a fronteira operacional. `validate_and_prepare` produz um evento auditável com `payload_sha256` e `audit_digest`; `sign` e `broadcast` são capacidades separadas e permanecem desabilitadas por padrão. O `request_id` é idempotente para impedir duplicação de solicitações.

O serviço não possui armazenamento de chave privada. A interface `Signer` é um contrato para um signer externo 2-de-3; a interface `Broadcaster` é separada para reduzir o blast radius.

## Threshold signer 2-de-3

A especificação alvo é um quorum de três participantes, exigindo duas aprovações válidas para liberar uma assinatura. O BAITHex deve receber somente o resultado assinado e metadados de auditoria; material de chave não deve entrar no agente, repositório ou logs.

A configuração de um cluster local regtest não foi executada porque o ambiente operacional vigente é Mainnet-only. A implementação atual deixa o signer desabilitado e fornece o contrato para um cluster real de custódia/threshold, que deverá ser provisionado fora do repositório com HSM/MPC e secret manager.

## Fluxo PSBT/política

1. Um watcher consulta UTXOs reais da Mainnet.
2. `baith-exchange` cria um request idempotente.
3. `policy-engine` verifica rede, destino, change, valor, fee, fee rate, inputs e payload unsigned.
4. Um decoder independente calcula o hash do payload e compara com o request.
5. O signer threshold aplica a política 2-de-3 fora do agente.
6. O agente verifica novamente o raw signed retornado.
7. Um broadcaster separado transmite apenas se todas as invariantes forem satisfeitas.
8. O monitor reconcilia txid, mempool, bloco, confirmações e reorgs.

## Clean-room e fontes públicas

A implementação foi derivada de interfaces e padrões públicos, não de código proprietário:

- [Bitcoin Core](https://github.com/bitcoin/bitcoin) — RPC, transação e operação de nó.
- [BIP-174 PSBT](https://github.com/bitcoin/bips/blob/master/bip-0174.mediawiki) — separação entre construção e assinatura.
- [rust-bitcoin](https://github.com/rust-bitcoin/rust-bitcoin) — tipos públicos para transações e PSBT.
- [rust-miniscript](https://github.com/rust-bitcoin/rust-miniscript) — políticas e scripts Bitcoin.
- [FROST IETF draft](https://datatracker.ietf.org/doc/draft-irtf-cfrg-frost/) — conceitos públicos de assinaturas threshold.

Essas fontes são referências funcionais e normativas. O BAITHex mantém código, contratos, políticas e armazenamento próprios.

## Sincronização com o ecossistema

A integração nesta etapa é aditiva e permanece em branch própria. Não houve merge, push ou alteração do `main`. Para sincronizar posteriormente:

1. revisar o diff dos novos diretórios;
2. executar os testes do projeto e os testes BAITHex;
3. revisar política e threat model;
4. abrir PR separado;
5. obter revisão de pelo menos dois mantenedores;
6. habilitar signer/broadcast somente por configuração externa após aprovação.
