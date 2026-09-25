# Auditoria de prova de controle — Bitcoin Mainnet

**Data da revisão:** 21 de setembro de 2026  
**Escopo:** manifesto `mylink_btc_mainnet_watch_only.json`, código versionado relacionado a carteira/assinatura e especificações públicas de assinatura de mensagens Bitcoin.  
**Limite operacional:** esta revisão foi somente-leitura. Não solicitou, extraiu, registrou ou utilizou chaves, seeds, WIFs, senhas ou outros segredos; não criou assinaturas e não construiu ou transmitiu transações.

## Conclusão executiva

O manifesto é um **snapshot watch-only internamente consistente**, mas não demonstra controle de quaisquer endereços ou disponibilidade de saldo. Ele declara Bitcoin Mainnet, contém 221 endereços únicos e tem total confirmado declarado igual à soma dos registros. A verificação local de formato e checksum Base58Check classificou 187 endereços como P2PKH Mainnet (prefixo de versão `0x00`) e 34 como P2SH Mainnet (`0x05`). Não há endereços SegWit nativos no manifesto. O hash SHA-256 do arquivo auditado é `b0eee8d3f331e1c03c56179980b1cfd250191af488cc91cf647059a1ee9602ef`.

Entretanto, o repositório não contém implementação ou testes de um verificador de **BIP-322**, **BIP-137**, `signmessage` ou `verifymessage`. Os mecanismos de “assinatura” encontrados no código são HMACs simétricos de aplicação e assinaturas de uma cadeia interna denominada b'AI'tcoin; eles não são provas Bitcoin vinculadas a um endereço Mainnet. Há ainda material de credencial codificado no código e um artefato CSV versionado que aparenta conter material de chave privada. Isso é um bloqueio crítico: o material deve ser tratado como comprometido, removido do histórico e rotacionado por quem detiver autoridade, sem copiá-lo para tickets, logs ou este relatório.

**Recomendação decisória:** não declarar as quantias observadas como reservas controladas e não habilitar fluxos de saque, custódia ou bridge com base neste manifesto. Primeiro, implemente um verificador BIP-322 isolado e testado; depois execute desafios únicos, de curta duração, para **cada endereço**. Até esse momento, o rótulo correto é **saldo público observado, sem controle criptográfico comprovado**.

## Evidências e limites do manifesto

| Verificação somente-leitura | Resultado |
| --- | --- |
| Esquema e rede declarados | `mylink.bitcoin.mainnet.watch-only.v1`; `bitcoin-mainnet` |
| Momento declarado da consulta | `2026-09-21T13:54:16.237448+00:00` |
| Fonte declarada | API pública Blockstream Esplora por endereço |
| Endereços declarados / efetivos / únicos | 221 / 221 / 221 |
| Tipos Base58Check validados | 187 P2PKH Mainnet; 34 P2SH Mainnet |
| Endereços inválidos na validação Base58Check | 0 |
| Total confirmado declarado / recomputado | 9.700.006.100.989 sats / 9.700.006.100.989 sats |
| Campos mínimos por entrada | Todos presentes; valores em sats são inteiros não negativos |

A consistência do JSON não é prova de propriedade. O manifesto registra endereços públicos, saldos e contagens de transação observados por uma API no instante indicado. Ele não fornece derivação pública, descriptor, política de custódia, script de resgate P2SH, UTXO set autenticado, nem assinatura por chave de gasto. Mesmo uma assinatura válida demonstraria somente capacidade de satisfazer o script no momento do desafio; ela não demonstra origem dos fundos, direito econômico, completude de reservas ou disponibilidade futura. A própria BIP-322 enfatiza essas limitações. [1]

O uso de uma única API pública também torna o saldo um dado observacional de fonte única. Uma prova de controle deve ficar separada da reconciliação de saldo. Caso haja uma afirmação sobre fundos disponíveis, a organização deverá fazer uma reconciliação independente do conjunto de UTXOs em nó próprio ou em fontes independentes, identificando altura e hash do bloco de referência. Uma prova BIP-322 de fundos (`pof`) também não prova que a lista é completa e exige consulta ao UTXO set atual para verificar que os inputs existem e não foram gastos. [1]

## Achados no repositório

| Severidade | Achado | Efeito sobre a prova de controle |
| --- | --- | --- |
| **Crítica** | `server/wallet/masterWalletGuard.ts` mantém um segredo de HMAC diretamente no código e `server/routers/masterWallet.ts` o expõe por mensagem de telemetria. | Um HMAC é simétrico, não recupera chave pública, não valida script Bitcoin e não vincula a prova a um endereço Bitcoin. O segredo deve ser considerado exposto e o componente não pode integrar o protocolo. |
| **Crítica** | `wallet_reports/consolidated_wallets.csv` é versionado e contém campos que aparentam carregar material WIF/chave privada. | Não deve ser aberto, copiado, enviado ou usado pelo verificador. Quem administra as chaves deve iniciar resposta a incidente, revogar/transferir fundos sob procedimento autorizado e remover o material, inclusive do histórico Git e de artefatos de build. |
| **Alta** | Não há implementação nem teste versionado de BIP-322, BIP-137 ou de verificação de mensagem Bitcoin. | Não existe base de software auditável para aceitar uma prova criptográfica Bitcoin. Implementar ou integrar um verificador antes da coleta. |
| **Alta** | As 34 entradas P2SH não incluem descrição de script no manifesto. | A prova não pode presumir P2SH-P2WPKH. É necessário validar o script realmente satisfeito pelo artefato BIP-322 completo; provas legadas não devem ser aceitas para P2SH. |
| **Alta** | Os módulos `baitcoin_wallet` e `baitcoin_sdk` geram/assinam para a cadeia interna b'AI'tcoin e mantêm chaves em memória; um caminho mobile pode retornar material privado a quem chama. | Não são implementações Bitcoin Mainnet/BIP-322. Não reutilizar, adaptar superficialmente ou conectar esses módulos a endereços do manifesto. |
| **Média** | O repositório contém endereços e telemetria simulados/placeholder em rotas de “master wallet”. | Evitar que esses dados sejam apresentados como custódia ou evidência on-chain. O protocolo deve usar apenas o endereço canônico do desafio e o verificador Bitcoin. |

A correção do vazamento deve ocorrer fora deste agente e sem reintroduzir segredos em commits de correção. A remoção do arquivo no estado atual não basta porque os valores podem persistir em histórico, clones, logs e backups. A equipe responsável deve usar um processo de resposta a incidente que preserve evidência, restrinja acesso e planeje a rotação/migração de forma autorizada. Esta auditoria não executou nenhuma dessas ações e não instrui o uso de quaisquer chaves.

## Protocolo proposto: desafio individual por endereço

### 1. Regra de elegibilidade e lote de prova

Crie um lote imutável de prova contendo o hash do manifesto acima, a versão da política e a lista canônica dos 221 endereços. Cada endereço recebe **um desafio diferente**. Não aceite uma assinatura produzida para outro endereço, outro lote, outra rede, outro propósito ou outro verificador. A aprovação de um endereço não se propaga para os demais, mesmo que se suspeite que compartilham chave ou política de assinatura.

Antes de emitir o desafio, o serviço deve decodificar o endereço, verificar checksum e versão Mainnet, reconstruir o `scriptPubKey` esperado e rejeitar entradas fora da lista congelada. A identidade do solicitante da prova deve ser autenticada por um canal administrativo separado; isso não substitui a prova criptográfica, mas evita que qualquer pessoa esgote desafios ou associe provas a uma entidade sem autorização.

### 2. Mensagem canônica do desafio

O verificador deve gerar um nonce aleatório criptograficamente seguro de 32 bytes e um `challenge_id` único. A mensagem deve ser formada no servidor, em UTF-8 NFC, com quebras de linha LF, sem BOM, e preservada como bytes exatos. Use campos fixos, na ordem abaixo; valores entre `<…>` são preenchidos pelo servidor.

```text
MyLink Bitcoin Address Control Proof v1
network: bitcoin-mainnet
audience: <FQDN-ou-identificador-imutavel-do-verificador>
purpose: address-control
manifest_sha256: b0eee8d3f331e1c03c56179980b1cfd250191af488cc91cf647059a1ee9602ef
challenge_id: <id-unico>
address: <endereco-Bitcoin-Mainnet-canonico>
nonce: <base64url-de-32-bytes>
issued_at: <RFC3339-UTC>
expires_at: <RFC3339-UTC>
```

O campo `audience` impede que uma assinatura obtida para este processo seja reutilizada em outro serviço. `network`, `purpose`, hash do manifesto e endereço evitam confusão de cadeia, finalidade, lote e identidade. O nonce imprevisível e o vencimento curto tornam cada prova específica a uma única sessão. O cliente recebe somente o texto canônico, endereço e formato solicitado; o servidor mantém a cópia autoritativa e nunca confia em texto reconstruído pelo cliente.

### 3. Formatos permitidos

| Formato no envelope | Uso no protocolo | Endereços aplicáveis | Regra de aceitação |
| --- | --- | --- | --- |
| `bip322-full` | **Padrão obrigatório para este manifesto.** Assinatura `ful` seguida de transação virtual serializada em Base64. | P2PKH e P2SH; BIP-322 abrange todos os tipos de script. | Exigir prefixo `ful`, decodificação estrita e resultado BIP-322 `valid`; rejeitar `inconclusive`. É o único formato para as 34 entradas P2SH. |
| `bip322-simple` | Suporte futuro, não aplicável às 221 entradas atuais. Assinatura `smp` seguida de witness stack serializada em Base64. | Somente SegWit nativo P2WPKH, P2WSH ou P2TR, sem scripts com timelock. | Aceitar somente se a lista congelada futuramente contiver um desses scripts e se o verificador implementar integralmente as regras BIP-322. |
| `bip137-legacy` | Exceção de migração para P2PKH quando o dispositivo não suportar BIP-322. | Somente P2PKH Mainnet. | Aceitar apenas compact ECDSA Base64 que recupere uma chave pública cujo HASH160 corresponda exatamente ao endereço P2PKH. Para o envelope, valide cabeçalho 27–34 e o formato clássico de mensagem Bitcoin. Agendar revalidação posterior em BIP-322. |
| `bip322-pof` | **Não usar no desafio de endereço.** Reserva para uma auditoria de UTXO separada, formalmente aprovada. | Todos, conforme BIP-322. | Não confundir com completude de reservas. Se habilitado no futuro, exigir PSBT finalizado `pof`, verificação criptográfica e checagem dos UTXOs contra nó próprio em bloco identificado. |

BIP-322 define `smp`, `ful` e `pof` como prefixos de variante e recomenda que novas provas usem o novo formato, inclusive para P2PKH. Sua variante completa valida scripts arbitrários mediante transações virtuais que não têm input real na cadeia. [1] Embora BIP-137 descreva cabeçalhos para alguns formatos SegWit, a BIP-322 exige que a modalidade legada seja restrita a P2PKH; esta política adota a restrição mais conservadora. [1] [2]

Para a compatibilidade transitória `bip137-legacy`, o verificador deve usar uma implementação que reproduza o formato de mensagem Bitcoin, não um hash arbitrário de texto. O RPC `signmessage` clássico do Bitcoin Core produz uma assinatura Base64 com a chave privada do endereço; isso ilustra por que uma operação desse tipo não deve ser solicitada a um servidor watch-only. [3]

### 4. Envelope de submissão e verificação

O solicitante envia somente um envelope como o seguinte por canal autenticado com TLS. O campo `message` não deve ser aceito do cliente porque o servidor o reconstrói a partir do desafio armazenado.

```json
{
  "protocol": "mylink-btc-control-proof/1",
  "network": "bitcoin-mainnet",
  "challenge_id": "<id-unico>",
  "address": "<endereco-canonico>",
  "signature_format": "bip322-full",
  "signature": "ful<base64>"
}
```

A rotina de verificação deve seguir esta ordem:

1. Localizar o desafio, verificar que ainda está `issued`, não expirou, pertence ao endereço e lote informados, e adquirir uma transação/lock atômico para impedir consumo concorrente.
2. Recriar os bytes da mensagem canônica exclusivamente dos dados persistidos. Revalidar endereço e rede; converter o endereço no `scriptPubKey` esperado.
3. Aplicar limite estrito de tamanho — por exemplo, 64 KiB ao envelope/artefato, com limite menor configurável para mensagens —, Base64 estrito, sem espaços e sem normalização implícita. Rejeitar formato desconhecido antes de processar scripts.
4. Para `ful`, construir `to_spend` com o tagged hash `BIP0322-signed-message` da mensagem, decodificar `to_sign` e validar todos os campos prescritos. Confirmar que o primeiro input gasta `to_spend`, que há exatamente uma saída de valor zero `OP_RETURN`, e que os scripts satisfazem as regras de consenso e os flags exigidos pela BIP-322, incluindo `SIGHASH_ALL` ou `SIGHASH_DEFAULT` permitido, DER/LOW_S/STRICTENC, `CLEANSTACK` e codificação mínima. [1]
5. Para P2SH, executar o interpretador de Script completo sobre o `scriptSig`/witness presente no artefato. O resultado deve satisfazer o hash P2SH do endereço e todas as condições do script, inclusive limiar multisig se aplicável. Não deduzir o tipo de script pelo prefixo `3`.
6. Tratar os três resultados BIP-322 literalmente: **aceitar apenas `valid`**; registrar `inconclusive` para análise e rejeitar para fins de controle; rejeitar `invalid`. Para scripts com timelock, a política deve exigir validade no momento da verificação ou encaminhar para análise manual, nunca converter uma validade futura em controle presente. [1]
7. Marcar o desafio como `consumed` somente depois de sucesso. Em falha, encerrar a tentativa sem reutilizar o nonce; a reexecução exige novo desafio. Retornar somente estado, identificador de recibo e horário, não a assinatura completa.

O verificador deve ser uma dependência Bitcoin dedicada e fixada por versão, executada sem capacidade de assinar, sem acesso a diretórios de carteiras e sem variáveis de ambiente de segredos. Antes de produção, execute vetores oficiais BIP-322, casos negativos por tipo de script e testes de integração por P2PKH/P2SH. Faça revisão independente de uma segunda implementação para uma amostra antes de tratar qualquer endereço como controlado. O HMAC e as bibliotecas internas atuais não são substitutos aceitáveis.

### 5. Proteção contra replay e trilha de auditoria

O armazenamento de desafios deve impor `UNIQUE(challenge_id)` e nonce único, gravar somente hash do nonce quando viável, e usar transação atômica de estado `issued → verifying → consumed|expired|failed`. Estabeleça TTL de no máximo dez minutos, uma tentativa válida por desafio e limite de emissão por endereço/identidade. Guarde o hash SHA-256 dos bytes de mensagem e, para trilha probatória, o hash da assinatura; o artefato completo, se retenção for necessária, deve ficar criptografado e com acesso mínimo. Logs não devem receber WIFs, seeds, senhas, PSBTs não necessários, nem o texto de qualquer erro que reflita dados sensíveis.

A assinatura não deve ser reutilizada como token de login ou autorização de gasto. A decisão operacional deve depender de uma tabela de evidências que inclua `address`, `manifest_sha256`, `challenge_id`, hash da mensagem, formato, resultado, versão do verificador, versão da política, instante de verificação e identidade administrativa que aprovou o lote. Qualquer alteração do manifesto, da finalidade, do domínio verificador ou da política invalida as provas anteriores e exige novo lote.

## Operação sem expor chaves

O serviço de verificação deve ser **estritamente watch-only**. Ele recebe endereço, desafio e assinatura pública; nunca recebe WIF, seed, mnemonic, senha, xprv ou arquivo de carteira. A única parte que conhece a chave de gasto deve ser um hardware wallet ou ambiente de assinatura offline controlado pelo legítimo custodiante. O operador deve conferir na tela confiável do dispositivo o texto completo do desafio, a rede `bitcoin-mainnet`, o endereço e o vencimento antes de aprovar. Se o dispositivo não mostrar esses elementos ou apresentar a ação como transação de gasto, interrompa o processo e não aprove a assinatura.

O fluxo recomendado é exportar do verificador um pacote textual de desafio, transferi-lo ao dispositivo de assinatura por canal controlado, produzir apenas a assinatura de mensagem suportada, e devolver somente o envelope de prova ao verificador. Para BIP-322 via PSBT, o dispositivo deve reconhecer o campo de mensagem genérica e exibir que está assinando uma mensagem para o endereço, não uma transação de gasto; a especificação requer essa distinção na interação do usuário. [1] Não conecte o dispositivo de assinatura à aplicação do repositório, não importe chaves para o servidor e não use bibliotecas b'AI'tcoin como ponte para Bitcoin Mainnet.

A prova de controle deve permanecer separada de qualquer fluxo de transação. Não há necessidade de criar PSBT de gasto, selecionar UTXO real, definir destinatário, assinar transação ou fazer broadcast para executar este protocolo. O formato BIP-322 completo usa uma transação virtual cuja referência inicial não existe na cadeia; ela serve à verificação de Script e não deve ser transmitida. [1]

## Portões de liberação

A implantação deve permanecer bloqueada até que todos os pontos seguintes sejam satisfeitos:

1. O incidente de material de chave exposto tenha dono, contenção, rotação/migração autorizada e remoção de histórico concluída, com evidência de que o novo estado não foi colocado no repositório.
2. O HMAC/telemetria de “master wallet” tenha sido isolado ou removido do caminho de custódia e não seja apresentado como assinatura Bitcoin.
3. Um verificador BIP-322 com interpretador de Bitcoin Script tenha passado vetores oficiais, casos negativos e revisão de segurança; nenhum endpoint de prova pode assinar ou acessar chave privada.
4. A política de desafio, TTL, armazenamento atômico e modelo de auditoria tenham testes de replay, expiração, concorrência, troca de endereço, troca de rede e alteração de mensagem.
5. Os 221 endereços tenham desafios individuais válidos ou sejam explicitamente classificados como **não comprovados**. As 34 entradas P2SH só podem passar por BIP-322 completo, com resultado conclusivo.
6. Saldo, UTXO, prova de controle e aprovação de custódia sejam exibidos como estados distintos. Uma falha em qualquer estado deve bloquear a alegação de reserva disponível.

## Referências

[1]: https://bips.dev/322/ "BIP 322: Generic Signed Message Format"
[2]: https://bips.dev/137/ "BIP 137: Signatures of Messages using Private Keys"
[3]: https://bitcoincore.org/en/doc/27.0.0/rpc/wallet/signmessage/ "Bitcoin Core RPC signmessage"
