# AI Store Catalog MCP

Pacote MCP somente leitura para consultar metadados verificados de pacotes do AI Store. O pacote usa o formato `.aipkg` definido em `baitcoin_ai.aipkg`.

## Permissões

O pacote declara `network=none`, `filesystem=read-only` e `secrets=none`. O servidor não executa código de outros pacotes, não realiza compras, não faz deploy e não acessa chaves ou macaroons.

## Interface

O transporte é stdio, com mensagens JSON-RPC por linha. O servidor implementa `initialize`, `tools/list` e `tools/call` para a ferramenta `search_packages`, que aceita `query` e `capability`.

## Verificação

A publicação local deve ser feita somente após validar o manifesto e os hashes SHA-256 dos arquivos. O catálogo externo contém o hash do artefato `.aipkg`; o runtime do AI Store pode então rejeitar arquivos alterados antes de qualquer instalação.
