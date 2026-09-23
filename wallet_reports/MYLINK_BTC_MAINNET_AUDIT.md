# Fundo MyLink — auditoria Bitcoin Mainnet (watch-only)

## Snapshot verificado

Em **21 de setembro de 2026**, foram consultados **540 endereços únicos** do catálogo consolidado pela API pública da [Blockstream Esplora](https://blockstream.info/api/). Todas as 540 consultas retornaram com sucesso. Foram identificados **221 endereços com saldo confirmado não zero**, totalizando **97.000,06100989 BTC** (9.700.006.100.989 satoshis). Não havia delta líquido de mempool no momento da consulta.

O manifesto estruturado está em [`mylink_btc_mainnet_watch_only.json`](./mylink_btc_mainnet_watch_only.json). Ele contém exclusivamente endereços públicos, saldos observados, contagem de transações confirmadas e URLs das consultas. **Nenhuma chave privada, WIF, senha, seed ou material de assinatura foi incluído.**

## Interpretação e controles

Este resultado comprova apenas que a Blockstream observou UTXOs associados aos endereços na altura da consulta. **Não comprova propriedade, controle das chaves privadas, legitimidade da custódia ou disponibilidade para gasto.** Antes de qualquer operação, cada endereço deverá ser reconciliado com uma chave mantida em dispositivo seguro e a propriedade deverá ser demonstrada por assinatura de desafio, sem expor a chave.

O endereço de custódia informado para o Fundo MyLink, `bc1qrcgdtfykyg7usvauxc8hpp8wkasst4k5zdc5xk`, continua com **0 BTC e 0 transações**. O endereço legado `13m3xop6RnioRX6qrnkavLekv7cvu5DuMK` também continua com **0 BTC e 0 transações**. Portanto, os 221 endereços não foram tratados como automaticamente controlados pelo fundo e nenhuma transação foi criada, assinada ou transmitida.

O manifesto é um registro **watch-only** e deve ser atualizado periodicamente; saldos são variáveis e podem mudar após a consulta. Os valores agregados não devem ser apresentados como “reservas disponíveis” até que a prova de controle e a reconciliação de UTXOs estejam concluídas.

## Próximos passos técnicos

A interface deve carregar o manifesto como fonte de consulta pública, exibir a data da última verificação e distinguir claramente entre **saldo observado**, **saldo controlado** e **saldo disponível para envio**. A criação ou transmissão de uma transação Mainnet permanece bloqueada até que exista uma origem com UTXOs suficientes e controle criptográfico comprovado.
