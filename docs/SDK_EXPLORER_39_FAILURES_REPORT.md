# Auditoria 04 — Classificação das 39 falhas do SDK e do Explorer

## Adendo de execução cirúrgica — 2026-09-07

Após a auditoria histórica abaixo, foram corrigidos e validados os pontos do indexador do explorer que impediam o fluxo nominal: scripts genesis inválidos agora recebem endereço determinístico e parseável; entradas resolvem outpoints conhecidos; saldos nativos não são sobrescritos por saldos de token; múltiplas saídas usam o próprio índice de saída; e o auto-rebuild usa a blockchain vinculada ao índice. A suíte `tests/test_blockchain_explorer.py` passou com **55 testes**.

O core Schnorr também foi atualizado separadamente para conformidade BIP-340, com **19/19 vetores oficiais**, mas os achados relativos a providers mobile, keystore, attestation, API e contratos SDK permanecem abertos. O resultado do explorer não autoriza custódia, broadcast, exposição pública como fonte de saldo ou transição Mainnet.

O relatório original abaixo preserva as evidências e a classificação inicial. Achados que mencionam o Schnorr core como placeholder devem ser lidos em conjunto com `native_processing/BIP340_VALIDATION_PROTOCOL.md`; placeholders nativos/mobile ainda não foram promovidos a implementação de produção.

**Repositório auditado:** `/home/ubuntu/work/swap-btc-bait/repos/bait-core`  
**Escopo:** `baitcoin_sdk/`, `baitcoin_explorer/`, handlers relacionados em `baitcoin_api/server.py`, SDKs nativos mobile e testes diretamente relacionados.  
**Data da análise:** 7 de setembro de 2026.  
**Autor:** Manus AI.  
**Estado do trabalho:** somente leitura no repositório; nenhum commit e nenhum push foram feitos.

## 1. Conclusão executiva

Foram classificados **39 achados**. A classificação é de prontidão de engenharia e risco operacional, não uma certificação de segurança, uma auditoria criptográfica formal ou uma validação de cadeia. O resultado global é **não aprovado para produção, custódia, broadcast de BTC ou exposição pública como explorer de confiança**.

Os bloqueadores mais graves são: importação de carteira que associa uma chave pública diferente à chave privada fornecida; assinatura mobile feita por uma chave recém-gerada em vez da carteira selecionada; criptografia de bundle AES-GCM que não consegue ser desencriptada pelo próprio código; biometria e attestation aceitas sem prova suficiente; implementações nativas que usam SHA-256 como substituto de secp256k1/Schnorr e que aceitam qualquer assinatura de 64 bytes; saldos do explorer que não debitam entradas; bug de contabilidade em transações com múltiplas saídas; índice que nasce vazio no servidor e não mostra ligação de inicialização ao daemon; contratos OpenAPI sem segurança aplicada e divergentes dos handlers; e gestão de API keys com segredo HMAC hard-coded e estado apenas em memória.

A referência oficial do BIP-340 exige chaves públicas x-only de 32 bytes, assinaturas de 64 bytes, tagged hashes e verificação de `s < n`, ponto não infinito, paridade de `R` e igualdade de `x(R)` [1]. Os placeholders nativos não implementam essas propriedades. O modo regtest é o ambiente apropriado para criar uma cadeia privada controlada e reduzir riscos durante testes [2]. A orientação OWASP recomenda ciclo de vida de segredos, menor privilégio, rotação, auditoria e minimização do tempo em claro [3].

## 2. Base de evidências e limitações

A análise combinou leitura estática, inspeção de contratos, execução local de testes focados e pequenas provas locais sem conexão a Bitcoin. O teste `pytest -q tests/test_blockchain_explorer.py tests/test_smoke.py` não passou: a preparação dos casos do explorer falhou repetidamente com `ValueError: Schnorr pubkey must be 32 bytes, got 16`, causado pelos dados de teste que passam `bytes([i + 1]) * 33` e depois são tratados como hex em `_pubkey_to_bait_address`. O resultado é evidência de que a suíte não valida o fluxo nominal completo; não é evidência de falha de uma rede Bitcoin.

A inspeção local também confirmou que `MobileWallet.import_wallet` gera um novo par de chaves, que `sign_message` gera outro par em vez de usar a carteira carregada, que o bundle mobile Python é apenas Base64 e que `MobileSecurity.encrypt_key_bundle` produz um bundle AES-GCM que `decrypt_key_bundle` rejeita por `integrity_check_failed`. Nenhuma transação BTC foi criada, assinada, transmitida ou movimentada.

O arquivo `/home/ubuntu/upload/pasted_content.txt` é **dado do usuário não verificado**. Ele mistura um snapshot de uma cadeia chamada b'AI'tcoin com dados de um explorer de Bitcoin, BCH, Ethereum e Solana, além de um valor no cabeçalho `X-Explorer-Auth-Key`. Esses dados não foram usados como prova de estado de rede, saldo, preço ou custódia. O relatório usa o snapshot apenas como sinal de risco de proveniência e de possível confusão de domínios, não como confirmação factual.

## 3. Legenda de risco e gate

| Nível | Interpretação | Decisão recomendada |
|---|---|---|
| **Crítico** | Pode permitir roubo, assinatura inválida, perda de chave, falsificação de estado ou bypass de controle. | Bloquear produção e qualquer custódia/broadcast. |
| **Alto** | Pode produzir perda financeira, integração incorreta, exposição relevante ou dados de explorer materialmente errados. | Corrigir antes de beta público ou uso com valor. |
| **Médio** | Falha de contrato, disponibilidade, observabilidade ou robustez que pode causar erro operacional. | Corrigir antes de GA; permitir somente testes isolados. |
| **Baixo** | Problema de documentação ou ergonomia sem perda imediata de integridade. | Corrigir no próximo ciclo, sem mascarar o gate. |

**Gate atual: RED.** Nenhum componente de custódia, wallet mobile, broadcast ou explorer público deve ser promovido a produção. Qualquer teste de BTC deve usar somente `bitcoind -regtest`, RPC com `-regtest`, chaves descartáveis e dados artificiais. Nenhuma valorização abaixo constitui promessa de preço.

## 4. Matriz consolidada dos 39 achados

| ID | Área | Severidade | Confiança | Decisão |
|---|---|---:|---:|---|
| SDK-01 | Contrato Python | Baixa | Alta | Corrigir documentação e exemplos |
| SDK-02 | Transporte | Alta | Alta | Bloqueador para endpoint remoto |
| SDK-03 | Transporte | Média | Alta | Corrigir tratamento tipado de erros |
| SDK-04 | Valores | Alta | Alta | Usar inteiros/Decimal e validação |
| SDK-05 | Modo local/remoto | Média | Alta | Tornar seleção explícita |
| SDK-06 | Registro de agente | Alta | Alta | Implementar endpoint ou falhar explicitamente |
| SDK-07 | Wallet Python | Alta | Alta | Implementar armazenamento/importação segura |
| SDK-08 | Endereços | Alta | Alta | Unificar contrato de endereço |
| SDK-09 | Staking Python | Alta | Alta | Implementar remoto ou retornar erro |
| SDK-10 | Marketplace Python | Alta | Alta | Implementar transporte remoto |
| SDK-11 | Importação mobile | Crítica | Alta | Bloqueador de wallet |
| SDK-12 | Exposição de chave | Crítica | Alta | Bloqueador de wallet |
| SDK-13 | Exportação mobile | Crítica | Alta | Substituir Base64 por AEAD real |
| SDK-14 | Assinatura mobile | Crítica | Alta | Bloqueador de assinatura |
| SDK-15 | Canonicalização de TX | Alta | Alta | Especificar serialização e nonce |
| SDK-16 | Falsos sucessos remotos | Alta | Alta | Propagar resposta e estado |
| SDK-17 | Staking mobile | Alta | Alta | Validar lock, valor e resposta |
| SDK-18 | Posições staking | Alta | Alta | IDs únicos e regras de desbloqueio |
| SDK-19 | Calculadora staking | Média | Alta | Separar cenário matemático de APY real |
| SDK-20 | Marketplace mobile | Alta | Alta | Verificar compra, posse e resposta |
| SDK-21 | Notificações | Média | Alta | Validar e transportar tokens |
| SDK-22 | Biometria | Crítica | Alta | Prova criptográfica obrigatória |
| SDK-23 | Attestation | Alta | Alta | Estado de challenge e anti-replay |
| SDK-24 | Crypto nativa | Crítica | Alta | Remover placeholders |
| SDK-25 | Base58 nativo | Alta | Alta | Implementar aritmética de bytes |
| SDK-26 | RIPEMD nativo | Alta | Alta | Falhar fechado sem provider |
| SDK-27 | Bundle AES-GCM | Crítica | Alta | Corrigir verificação por algoritmo |
| SDK-28 | URLs | Média | Alta | Codificar query parameters |
| SDK-29 | Autorização | Alta | Alta | Alinhar Bearer/Bait e aplicar security |
| EX-30 | Auto-rebuild | Alta | Alta | Remover caminho quebrado ou injetar dependências |
| EX-31 | Reorg/deduplicação | Alta | Alta | Detectar conflito e reconstruir |
| EX-32 | Débitos e endereços de entrada | Crítica | Alta | Corrigir modelo UTXO |
| EX-33 | Múltiplas saídas | Crítica | Alta | Corrigir variável fora do escopo |
| EX-34 | Token versus saldo on-chain | Alta | Alta | Expor dimensões separadas |
| EX-35 | Estado derivado | Alta | Alta | Atualizar confirmações e fee corretamente |
| EX-36 | Busca/paginação | Média | Alta | Validar parâmetros e cobrir todo o índice |
| EX-37 | OpenAPI | Alta | Alta | Gerar contrato a partir do runtime ou validar CI |
| EX-38 | Servidor/índice | Alta | Alta | Inicializar índice e tratar entrada inválida |
| EX-39 | API keys/rate limit | Crítica | Alta | Secret manager, persistência e atomicidade |

## 5. Achados detalhados

### SDK-01 — Documentação e assinatura pública do cliente não coincidem

**Evidência:** `baitcoin_sdk/__init__.py:11-15` documenta `BaitcoinSDK(agent_id='my_agent')`, `create_wallet()` sem argumento e `transfer(wallet, recipient_pubkey, ...)`. A implementação real em `baitcoin_sdk/client.py:13-21` aceita apenas `endpoint` e `api_key`, e `create_wallet` em `client.py:129-130` exige `agent_id`.

**Impacto:** um integrador que siga a documentação recebe `TypeError` ou usa chamadas com semântica incompatível. Isso é particularmente perigoso em SDK financeiro porque o usuário pode acreditar que a carteira e o destinatário foram selecionados quando a API espera IDs de agente.

**Classificação:** Baixa para segurança direta, mas Alta para adoção e integração. **Correção:** publicar uma especificação de API versionada, gerar exemplos a partir de testes executáveis e rejeitar documentação que não passe por um teste de quick-start.

### SDK-02 — Endpoint padrão usa HTTP sem TLS

**Evidência:** `baitcoin_sdk/client.py:14` define `DEFAULT_ENDPOINT = 'http://localhost:18445'`; `_request` em `client.py:31-42` não impõe HTTPS, autenticação mútua, pinning ou política de host. O cliente mobile usa HTTPS por padrão, mas permite qualquer endpoint em `client.py:81-91`.

**Impacto:** fora de localhost, bearer tokens, identificadores de sessão, dados de carteira e transações podem ser interceptados ou redirecionados. Mesmo em uma rede privada, a ausência de política de transporte deixa o comportamento dependente do chamador.

**Classificação:** Alta. **Correção:** exigir HTTPS por padrão, permitir HTTP somente com um modo explícito `regtest/local`, validar hostname e registrar o modo inseguro. Nunca enviar chaves privadas por HTTP.

### SDK-03 — Tratamento de resposta HTTP é não tipado e pode vazar exceções

**Evidência:** `baitcoin_sdk/client.py:39-42` faz `json.loads` sem capturar JSON inválido, códigos HTTP de erro de forma estruturada ou conteúdo inesperado. O cliente mobile melhora parte do tratamento em `mobile/client.py:131-142`, mas ainda retorna `{"error": str(e)}` diretamente, sem tipos de erro estáveis.

**Impacto:** uma página HTML de proxy, erro parcial ou resposta 204 pode gerar exceção no caminho de produção. Consumidores não conseguem distinguir indisponibilidade, autorização, validação e rejeição de transação.

**Classificação:** Média. **Correção:** criar um envelope de erro versionado com `code`, `http_status`, `retryable` e `request_id`; rejeitar schema inválido; nunca incluir exceções internas diretamente no payload público.

### SDK-04 — Valores financeiros usam `float` e não validam sinal, finitude ou precisão

**Evidência:** `client.py:64-75` e `mobile/client.py:153-172` convertem `amount_bait * 100_000_000` para `int` sem rejeitar números negativos, `NaN`, infinito, excesso de casas ou arredondamento binário. O mesmo padrão aparece em `client.py:86-92` para staking.

**Impacto:** valores como `0.000000009` podem truncar para zero; números especiais podem causar exceções ou comportamento divergente; valores negativos podem alcançar camadas que não deveriam aceitá-los. A conversão não é um contrato monetário determinístico.

**Classificação:** Alta. **Correção:** aceitar somente inteiros em satoshis ou `Decimal` com quantização explícita, limitar `0 <= amount <= policy_max`, rejeitar `NaN`/infinito e testar fronteiras.

### SDK-05 — Seleção de modo local/remoto é implícita e o cliente não oferece uma transição segura

**Evidência:** `BaitcoinSDK.__init__` marca `self._local_mode = True` em `client.py:22`; `configure_local` também força `True` em `client.py:44-53`. Não há método público equivalente para configurar um transporte remoto com política explícita, nem uma distinção forte entre estado local e endpoint remoto.

**Impacto:** o mesmo código pode alternar entre objetos locais e HTTP conforme quais dependências foram injetadas. Em uma aplicação de custódia, essa ambiguidade pode fazer uma operação de teste parecer confirmada por rede ou vice-versa.

**Classificação:** Média. **Correção:** separar `LocalTransport` e `HttpTransport`, tornar o modo obrigatório no construtor e incluir `network`, `chain_id`, `transport` e `is_simulation` em cada resposta.

### SDK-06 — Registro remoto de agente falha silenciosamente

**Evidência:** `client.py:100-106` converte capabilities e, se não estiver em modo local com registry, simplesmente retorna `False`; não existe chamada HTTP para registro remoto nem uma exceção de “not implemented”.

**Impacto:** um cliente remoto pode concluir que o registro foi tentado quando a operação nunca saiu do processo. Isso quebra autorização posterior, indexação por agente e fluxos de marketplace.

**Classificação:** Alta. **Correção:** implementar o endpoint remoto com autenticação e idempotência, ou retornar `UnsupportedOperation` explícito. Nunca usar `False` como substituto de transporte ausente.

### SDK-07 — Wallet Python é somente memória e não tem ciclo de vida seguro

**Evidência:** `wallet_sdk.py:47-57` mantém `_wallets` em um dicionário do processo; `create` substitui a carteira quando o mesmo `agent_id` é usado. Não há importação, exportação cifrada, zeroização, persistência ou confirmação de substituição.

**Impacto:** reinício perde a carteira; recriação acidental pode produzir identidade diferente; processos long-lived mantêm chaves privadas indefinidamente. A carteira não atende ao ciclo de criação, recuperação, revogação e backup.

**Classificação:** Alta. **Correção:** usar um keystore externo/hardware-backed, exigir confirmação para substituir identidade, separar segredo de metadados e implementar import/export com AEAD real e testes de recuperação.

### SDK-08 — O contrato de endereço diverge entre documentação, testes e núcleo

**Evidência:** o núcleo `baitcoin_core/blockchain/addresses.py:8-10,124-157` usa formato `b'`/`t'` mais Base58Check; alguns testes antigos em `tests/test_phases_7_10.py:406-407,455-457` esperam `bAI1q`. `wallet_sdk.py:54-55` chama `pubkey_to_address`, enquanto os contratos mobile e os exemplos usam outra nomenclatura.

**Impacto:** endereços legítimos podem ser rejeitados no SDK ou exibidos com um formato que o backend não aceita. Isso cria risco de enviar a uma cadeia/rede errada, além de tornar impossível garantir interoperabilidade entre Python, Swift e Kotlin.

**Classificação:** Alta. **Correção:** publicar um único BIP interno de endereço com prefixo, version byte, tamanho, rede e checksum; gerar fixtures oficiais; remover expectativas antigas e validar round-trip em todas as linguagens.

### SDK-09 — Staking SDK Python retorna zeros ou não implementa o remoto

**Evidência:** `staking_sdk.py:10-18` retorna `0` para `unstake` e `get_rewards` quando não há pool local. Não há chamadas remotas equivalentes, apesar de `client.py:86-92` expor `stake` remoto.

**Impacto:** uma aplicação remota pode exibir recompensa zero e considerar uma operação de retirada concluída sem que nada tenha sido enviado. O contrato de retorno também mistura booleano, inteiro e estado implícito.

**Classificação:** Alta. **Correção:** implementar operações remotas com `position_id`, confirmações e estado on-chain; em caso de ausência, levantar erro tipado, nunca retornar zero como se fosse saldo real.

### SDK-10 — Marketplace SDK clássico é local-only e devolve valores vazios fora do processo

**Evidência:** `marketplace_sdk.py:11-17` retorna `[]` quando não há marketplace local; `purchase` retorna `None` em `:22-25`, `rate` retorna `False` em `:27-30` e `get_info` retorna `{}` em `:32-35`. Não há transporte HTTP.

**Impacto:** integração remota não consegue pesquisar, comprar ou avaliar serviços. O chamador não consegue diferenciar “não há listings” de “SDK não implementado”.

**Classificação:** Alta. **Correção:** criar endpoints tipados e idempotentes para listing, purchase e rating, propagar `purchase_id`/`tx_id` e rejeitar chamadas remotas não implementadas.

### SDK-11 — Importação mobile guarda uma chave privada com uma chave pública diferente

**Evidência:** `mobile/wallet.py:147-160` cria `kp = SchnorrKeyPair()` sem usar `privkey_hex`, deriva `pubkey_hex` e endereço desse par novo, mas grava `privkey_hex` fornecida pelo usuário no mesmo `WalletInfo`.

**Impacto:** o endereço exibido não corresponde à chave privada importada. Qualquer assinatura posterior é inválida para o endereço apresentado, e uma recuperação pode fazer o usuário assinar ou enviar fundos com identidade incorreta.

**Classificação:** **Crítica e bloqueadora.** **Correção:** construir o keypair a partir da chave privada validada, derivar a pública novamente, comparar a chave fornecida com o formato permitido e rejeitar chaves inválidas ou fora de intervalo.

### SDK-12 — Criação mobile retorna a chave privada em claro

**Evidência:** `mobile/wallet.py:121-130` retorna `wallet.to_dict(include_private=True)`; o resultado contém `privkey_hex`. A própria documentação afirma que chaves devem ficar em armazenamento seguro do dispositivo, mas o método entrega o segredo a qualquer camada que receba o retorno.

**Impacto:** logs, telemetria, crash reports, serialização de estado e bridges JavaScript podem capturar a chave. O risco é agravado porque não há política de redaction nem tipo separado para segredo.

**Classificação:** **Crítica.** **Correção:** retornar somente um handle não exportável; exigir uma chamada explícita de exportação protegida por hardware/biometria; marcar material secreto como não serializável e testar que logs não o contêm.

### SDK-13 — Exportação Python mobile é Base64, não cifragem

**Evidência:** `mobile/wallet.py:61-80` documenta AES-256-GCM futuro, mas implementa `base64.b64encode(bundle)`. O `passphrase` é recebido e não participa do cálculo.

**Impacto:** qualquer pessoa com o bundle recupera a chave privada. Base64 não fornece confidencialidade, integridade, rotação ou resistência a tentativa de senha.

**Classificação:** **Crítica.** **Correção:** usar AES-256-GCM ou XChaCha20-Poly1305 com KDF aprovado, salt e nonce únicos, parâmetros versionados, verificação atômica e integração com Secure Enclave/Keystore. A orientação OWASP exige proteção do segredo em repouso e gestão do ciclo de vida [3].

### SDK-14 — Assinatura de mensagem mobile usa uma chave recém-gerada

**Evidência:** `mobile/wallet.py:214-228` carrega `wallet`, mas cria `kp = SchnorrKeyPair()` e assina com `kp.sign(msg_hash)`. O retorno informa `wallet.pubkey_hex`, que não é a pública de `kp`.

**Impacto:** a assinatura não verifica com a chave pública retornada nem com o endereço da carteira. Isso quebra autenticação, autorização e qualquer fluxo de assinatura offline.

**Classificação:** **Crítica.** **Correção:** reconstruir ou manter o keypair correto associado ao wallet handle, assinar o digest canônico exigido pelo protocolo e testar `verify(pubkey, message, signature)` antes de devolver o resultado.

### SDK-15 — Assinatura de transação não tem serialização de protocolo estável

**Evidência:** `mobile/wallet.py:255-273` cria `tx_for_signing`, mas define `tx_hash` em `:262-263` e não o usa. O nonce padrão é `int(time.time())`, os campos assinados podem divergir de `tx_data`, e o `tx_id` é um hash de string JSON mais assinatura.

**Impacto:** dois clientes podem assinar bytes diferentes para a mesma intenção; campos não incluídos no digest podem ser alterados; retries podem criar IDs diferentes. Isso facilita rejeição, replay ou ambiguidade de pagamento.

**Classificação:** Alta. **Correção:** especificar serialização binária/canonical JSON, incluir todos os campos relevantes, nonce de cadeia, domain separation (`network`/`chain_id`), hash único e verificação no servidor antes do mempool.

### SDK-16 — Operações remotas mobile ignoram falhas e fabricam sucesso local

**Evidência:** `mobile/staking.py:107-127` chama `_request` e ignora a resposta; `mobile/marketplace.py:114-119` ignora a resposta de busca e continua no catálogo local; `mobile/marketplace.py:170-187` cria compra `status: completed` mesmo se o POST remoto falhar.

**Impacto:** a UI pode mostrar stake, compra ou disponibilidade que nunca foi confirmada. Esse é um falso positivo de liquidação, perigoso quando o usuário associa a tela a uma transferência de valor.

**Classificação:** Alta. **Correção:** tratar cada resposta como máquina de estados (`submitted`, `confirmed`, `rejected`), propagar erro e `request_id`, usar idempotency key e nunca marcar `completed` sem prova do backend.

### SDK-17 — Staking mobile aceita lock period e valor fora da política

**Evidência:** `mobile/staking.py:60-68` define períodos permitidos, mas `stake` em `:74-131` não verifica se `lock_days` pertence a eles, nem rejeita negativo, não finito ou valor acima de limites. O mínimo é a única validação.

**Impacto:** o cliente pode construir posição com prazo negativo ou decimal não suportado pelo servidor. A interface local pode exibir unlock no passado enquanto o backend usa outra política.

**Classificação:** Alta. **Correção:** validar `amount` como inteiro de unidade mínima, aceitar apenas os períodos enumerados, validar resposta do servidor e exibir a política efetiva retornada pela cadeia.

### SDK-18 — IDs de posição podem colidir e `unstake` não aplica a regra de desbloqueio

**Evidência:** `mobile/staking.py:103-105` forma `position_id` com agente e segundos do relógio; duas operações no mesmo segundo colidem conceitualmente. `:138-151` marca a posição como `unstaking` sem verificar `unlock_time`, sem exigir que tenha sido encontrada e retorna sucesso local mesmo para ID inexistente.

**Impacto:** uma posição pode ser sobrescrita ou a UI pode reportar retirada de uma posição que não existe. O lock period deixa de ser uma propriedade de segurança.

**Classificação:** Alta. **Correção:** usar UUID/ID da cadeia, exigir correspondência única, verificar estado e altura/tempo de desbloqueio no servidor e retornar erro explícito para posição inexistente ou bloqueada.

### SDK-19 — Calculadora de staking apresenta projeção como se fosse rendimento efetivo

**Evidência:** `mobile/staking.py:181-233` usa juros compostos fixos com `apy = apy or DEFAULT_APY`; portanto `apy=0` cai para 7%, valores negativos são aceitos e não há vínculo com saldo, emissão, lock ou APY efetivo. O retorno sempre cria 12 pontos mensais, inclusive além de `days`.

**Impacto:** a calculadora pode produzir projeções incompatíveis com a política real. A nomenclatura “APY” e “projected” deve deixar claro que é cenário matemático, não cotação nem promessa.

**Classificação:** Média. **Correção:** aceitar zero explicitamente, rejeitar valores fora da política, separar APY nominal de taxa realizada, indicar composição, arredondamento, período e incerteza, e adicionar testes de cenário.

### SDK-20 — Marketplace mobile não verifica compra, autorização de rating ou resposta do servidor

**Evidência:** `mobile/marketplace.py:145-187` aceita qualquer `buyer_id`, `service_id` e `amount_bait`, ignora a resposta remota e marca `completed`. `:189-224` aceita rating, mas não verifica compra, identidade do comprador ou existência do serviço; a chamada remota também é ignorada.

**Impacto:** a camada cliente pode criar compras fictícias, avaliações não autorizadas e histórico inconsistente. Qualquer autorização deve ocorrer no servidor, não em IDs fornecidos pelo cliente.

**Classificação:** Alta. **Correção:** resolver listing e preço no servidor, autorizar o comprador pelo token, exigir prova de entrega/compra para rating, usar idempotência e devolver estado confirmado.

### SDK-21 — Notificações são somente locais e não validam plataforma/token

**Evidência:** `mobile/notifications.py:71-93` registra qualquer string e qualquer `platform`, sem chamada ao backend; `:127-168` mantém histórico apenas em memória e aceita qualquer `notification_type` em `add_notification`.

**Impacto:** tokens não chegam a FCM/APNs, preferências não persistem e dados de notificação podem ser inseridos com tipos inválidos. O usuário pode acreditar que recebeu uma confirmação que só existe no processo local.

**Classificação:** Média. **Correção:** validar tokens e enum de plataforma, registrar/remover no servidor com autenticação, persistir preferências, limitar tamanho de payload e separar evento confirmado de notificação local.

### SDK-22 — Biometria e token são aceitos sem prova criptográfica

**Evidência:** `mobile/security.py:211-220` sempre retorna `eligible: True`; `:250-257` considera válido qualquer token não vazio com 16 ou mais caracteres e o comentário admite que JWT assinado ainda não é verificado.

**Impacto:** um atacante que conheça `device_id` pode satisfazer a camada de biometria sem biometria, assinatura de plataforma, nonce ou vínculo de sessão. Isso não pode proteger movimentação de valor.

**Classificação:** **Crítica.** **Correção:** mover a decisão para Secure Enclave/Keystore, verificar attestation e token assinado com issuer/audience/nonce/expiração, atrelar a operação específica e falhar fechado.

### SDK-23 — Challenge de dispositivo não tem estado, expiração efetiva nem anti-replay

**Evidência:** `generate_device_challenge` em `mobile/security.py:259-270` devolve `expires_at`, mas não armazena o challenge. `verify_device_response` em `:272-301` não consulta expiração, não marca uso, não confirma que o challenge foi emitido para o mesmo dispositivo e aceita a chave pública enviada na própria requisição.

**Impacto:** um challenge antigo pode ser reapresentado; qualquer chave pública pode ser escolhida pelo chamador; a prova não demonstra posse de uma identidade previamente registrada.

**Classificação:** Alta. **Correção:** armazenar challenge com TTL e uso único, vincular `device_id`, sessão e ação, registrar chave pública no enrollment, exigir attestation e rejeitar replay.

### SDK-24 — Crypto providers nativos são placeholders incompatíveis com BIP-340

**Evidência:** Swift `BaitcoinKit.swift:91-119` deriva pública com SHA-256, produz assinatura por concatenação de hashes e aceita qualquer assinatura de 64 bytes. Kotlin repete isso em `BaitcoinKit.kt:118-141`. O README reconhece que os providers são placeholders.

**Impacto:** chaves não são pontos secp256k1, assinaturas não são Schnorr e verificação não autentica nada. Uma assinatura arbitrária de 64 bytes passa na verificação nativa.

**Classificação:** **Crítica e bloqueadora.** **Correção:** remover o provider placeholder da configuração de produção, exigir uma implementação testada contra vetores BIP-340 [1], bloquear build release se o provider for placeholder e comparar assinatura entre Python, iOS, Android e servidor.

### SDK-25 — Base58 nativo usa aritmética estreita para payload de 25 bytes

**Evidência:** `BaitcoinKit.swift:182-204` usa `Int` para acumular todos os bytes; `BaitcoinKit.kt:221-241` usa `Long`. Um payload Base58Check de endereço tem 25 bytes e excede esses tipos. O resultado não é uma implementação geral de Base58 e pode sofrer overflow/truncamento.

**Impacto:** endereços produzidos no mobile podem não ser interoperáveis, variar por plataforma ou falhar silenciosamente. Uma validação incompleta não deve ser usada para direcionar fundos.

**Classificação:** Alta. **Correção:** implementar conversão por vetor de bytes ou biblioteca auditada, testar payloads com zeros à esquerda e vetores de 25 bytes, e comparar com `baitcoin_core.blockchain.addresses`.

### SDK-26 — RIPEMD-160 cai para hash incorreto em Android

**Evidência:** `BaitcoinKit.kt:165-180` tenta provider `BC` e, em qualquer exceção, usa os primeiros 20 bytes de SHA-256. Isso não é RIPEMD-160. O endereço resultante diverge do núcleo e do padrão declarado.

**Impacto:** ausência ou falha de configuração do provider muda o endereço sem erro fatal. O fallback transforma defeito de instalação em identidade financeira incorreta.

**Classificação:** Alta. **Correção:** empacotar/testar provider suportado, verificar `RIPEMD160` em startup e falhar fechado; nunca substituir algoritmo criptográfico por truncamento silencioso.

### SDK-27 — Bundle AES-GCM Python é rejeitado pelo próprio decryptor

**Evidência:** quando `cryptography` está disponível, `encrypt_key_bundle` em `mobile/security.py:123-153` grava `auth_tag` GCM. `decrypt_key_bundle` em `:178-184` primeiro calcula HMAC-SHA256 sobre `iv + ciphertext` e compara com o tag GCM, retornando `integrity_check_failed` antes de `AESGCM.decrypt`.

**Impacto:** bundles legítimos não podem ser recuperados; o fallback de erro pode induzir reexportações perigosas ou perda de acesso. A implementação também mistura dois protocolos de autenticação.

**Classificação:** **Crítica.** **Correção:** selecionar o algoritmo pelo campo versionado: para AES-GCM, passar `ciphertext + auth_tag` diretamente ao `AESGCM.decrypt`; para fallback legado, manter protocolo separado e migrar somente após verificação. Criar teste encrypt/decrypt, wrong-passphrase, tamper e upgrade.

### SDK-28 — Query strings são interpoladas sem URL encoding

**Evidência:** `mobile/client.py:208-212` concatena `q` em `/explorer/search?q={query}`; `mobile/marketplace.py:114-116` monta `k=v` manualmente. Caracteres `&`, `#`, `?`, `%` e Unicode alteram a requisição.

**Impacto:** buscas podem perder filtros, atingir parâmetros não pretendidos ou gerar respostas inconsistentes. Em proxies e logs, a falta de encoding pode permitir confusão de parâmetros.

**Classificação:** Média. **Correção:** usar `urllib.parse.urlencode` ou cliente HTTP estruturado, limitar tamanho e validar parâmetros no servidor.

### SDK-29 — Esquema de autorização é incompatível entre SDK, OpenAPI e servidor

**Evidência:** `client.py:34-36` e `mobile/client.py:124-125` enviam `Authorization: Bearer <key>`. O esquema OpenAPI em `baitcoin_explorer/docs.py:507-512` descreve `Authorization: Bait <api_key>`, e o handler em `baitcoin_api/server.py:1121-1134` só interpreta o prefixo `Bait` para rate-limit. Além disso, a probe do spec mostrou `security: None` na rota do explorer.

**Impacto:** uma key válida do SDK pode ser tratada como anônima; a documentação não comunica proteção efetiva; endpoints podem ficar públicos por acidente. O snapshot externo também contém uma API key não verificável, o que reforça a necessidade de rotação e não prova que aquela credencial seja válida.

**Classificação:** Alta. **Correção:** escolher um único esquema (`Authorization: Bearer` ou `Bait`), aplicar `security` por operação, testar 401/403/429 e retirar qualquer credencial exposta do ambiente.

### EX-30 — Caminho de auto-rebuild do índice está quebrado e engole a exceção

**Evidência:** `baitcoin_explorer/indices.py:283-289` usa `self.chain.blocks`, mas `BlockchAInIndex` não define `self.chain`; chama `self.rebuild()` sem o argumento obrigatório `blockchain`; e captura qualquer exceção com `pass`.

**Impacto:** quando o índice fica atrasado, o mecanismo anunciado de autorrecuperação não reconstrói nada e não produz alerta. O explorer pode permanecer stale indefinidamente.

**Classificação:** Alta. **Correção:** injetar uma fonte de cadeia no índice, validar altura/hash, reconstruir com lock e emitir métrica/alerta quando o rebuild falhar. Remover `except Exception: pass` de caminhos de integridade.

### EX-31 — Conflitos de altura, reorg e transações duplicadas são sobrescritos

**Evidência:** `_index_block` grava `self._block_by_hash[block_hash]` e `self._block_by_height[block.index]` em `indices.py:357-359`, sem verificar `prev_hash`, altura já ocupada ou mudança de cadeia. Em `:400-401`, um `tx_id` repetido sobrescreve o objeto, mas contadores e listas invertidas já podem ter sido incrementados.

**Impacto:** uma reorg ou replay pode exibir bloco de uma cadeia diferente, contaminar contagens e deixar referências órfãs. O explorer não é uma fonte de verdade se não distingue canonical, orphaned e reorged.

**Classificação:** Alta. **Correção:** validar encadeamento, detectar conflito, marcar/reverter ramo órfão, tornar indexação idempotente por hash e fazer rebuild atômico em caso de reorg.

### EX-32 — O modelo de endereços de entrada não representa UTXO e nunca debita o saldo

**Evidência:** `indices.py:370-372` transforma uma entrada em `prev_tx_id[:16]:index`, que não é o endereço de origem. O processamento de endereços em `:404-421` adiciona somente outputs; não há resolução do UTXO gasto, débito de `balance_sats` ou atualização de `total_sent_sats`.

**Impacto:** saldo, recebimentos, remetentes e histórico de endereço ficam materialmente incorretos. O endpoint pode afirmar saldo positivo após o UTXO ter sido gasto e não consegue atribuir a entrada ao endereço real.

**Classificação:** **Crítica.** **Correção:** manter índice de outpoints, resolver cada input para o output anterior, debitar exatamente uma vez, tratar coinbase e spentness, e testar cadeia com spend, change, fee e double-spend rejeitado.

### EX-33 — Bug de variável fora do escopo atribui o valor da última saída a todos os endereços

**Evidência:** em `indices.py:404-413`, o loop `for out in tx.outputs` termina antes do loop `for addr in output_addrs`, mas o corpo usa `out.amount_sats`. Para uma transação com várias saídas, cada endereço recebe o valor da última saída iterada.

**Impacto:** saldos e total recebido são inflados ou atribuídos ao endereço errado. Esse é um erro determinístico de contabilidade, não apenas uma imprecisão de apresentação.

**Classificação:** **Crítica.** **Correção:** iterar em pares `(out, out_addr)` ou atualizar `AddressInfo` dentro do loop de outputs; adicionar teste com três valores distintos e verificar soma por endereço.

### EX-34 — Saldo de token sobrescreve saldo on-chain sem separar ativos

**Evidência:** `_enrich_with_token` em `indices.py:435-440` substitui `AddressInfo.balance_sats` pelo saldo do token para o endereço associado ao agente. A dataclass afirma incluir UTXO e token no mesmo saldo, mas não há campo separado nem soma com semântica documentada.

**Impacto:** o endpoint pode mostrar BAIT token como se fosse saldo UTXO, ou apagar o saldo on-chain ao enriquecer o índice. Usuários e integrações não conseguem saber qual ativo está sendo exibido.

**Classificação:** Alta. **Correção:** separar `native_balance_sats`, `token_balance_sats`, `total_received_native`, `total_sent_native` e identificador do ativo; não sobrescrever dados derivados de fontes distintas.

### EX-35 — Confirmações e taxa do mempool são métricas stale ou de unidade errada

**Evidência:** confirmações são calculadas somente ao indexar (`indices.py:310-314`) e atualizadas apenas se alguém chamar explicitamente `update_confirmations` em `:552-558`. O `get_mempool_info` calcula `fee_sats` como `tx.gas_price * tx.gas_limit` em `:521-534`, embora taxa de uma transação UTXO deva derivar de entradas menos saídas ou do fee rate do protocolo.

**Impacto:** uma transação antiga pode continuar com confirmações antigas; o mempool pode mostrar uma taxa economicamente falsa. Isso afeta priorização, UX de confirmação e análises de custo.

**Classificação:** Alta. **Correção:** atualizar confirmações ao avançar a altura, expor altura de referência, definir `fee_sats`/`fee_rate` no modelo e calcular conforme o tipo de transação; cobrir coinbase, UTXO e gas-based separadamente.

### EX-36 — Busca não é universal e aceita paginação inválida

**Evidência:** `search.py:207-228`, `:249-273` e `:294-315` limitam substring search aos 100 itens recentes, embora a descrição prometa busca em todos os índices. `query` em `:94-168` não valida `limit`/`offset`; `MAX_RESULTS` é definido em `:87`, mas não é aplicado ao resultado geral. Tipos desconhecidos em `:115-128` são ignorados.

**Impacto:** um hash antigo ou endereço de baixo saldo pode não ser encontrado; `limit` negativo altera slicing; filtro inválido retorna zero em vez de erro. Agentes podem tomar ausência de resultado como inexistência on-chain.

**Classificação:** Média. **Correção:** usar índices invertidos completos, validar `1 <= limit <= MAX_RESULTS` e `offset >= 0`, rejeitar tipos desconhecidos com 400 e incluir `complete`, `canonical_height` e paginação determinística na resposta.

### EX-37 — OpenAPI não representa segurança, tipos e erros do runtime

**Evidência:** `_path_param` em `docs.py:25-27` declara todo parâmetro como string, inclusive `height`; `_get` em `:42-56` documenta apenas 200 e 503, enquanto handlers retornam 400/404; `securitySchemes` existem em `:500-512`, mas as operações não têm campo `security`. A probe local confirmou `security` ausente na rota `/api/v1/explorer/blocks`.

**Impacto:** clientes gerados podem aceitar tipos errados, não tratar 404/400 e não enviar autenticação. A especificação cria uma falsa sensação de contrato e impede testes de conformidade.

**Classificação:** Alta. **Correção:** gerar schemas a partir de modelos/handlers ou validar spec contra runtime em CI; declarar `integer`, ranges, required fields, 400/401/404/429/503, headers e security por operação.

### EX-38 — O servidor cria um índice vazio e trata entrada de paginação sem proteção

**Evidência:** `baitcoin_api/server.py:1571-1587` cria `BlockchAInIndex()` e `UniversalSearch`, mas não mostra `rebuild` nem ligação de `index_new_block` no `create_app`. Assim, o serviço pode responder vazio até uma inicialização externa não documentada. Nos handlers, `int(query.get(...))` em `:865-866`, `:917-918`, `:932-933` e `:948-950` não é protegido contra valores inválidos. O endpoint de transações de endereço em `:919-925` retorna 200 com zero para endereço desconhecido.

**Impacto:** disponibilidade e semântica dependem de efeitos externos; uma requisição malformada pode virar 500; endereço inexistente é indistinguível de endereço sem transações. Isso é incompatível com um explorer público confiável.

**Classificação:** Alta. **Correção:** inicializar/reconstruir o índice explicitamente antes de anunciar readiness, conectar atualizações do daemon, validar limites com 400, e retornar 404 para recurso inexistente.

### EX-39 — API keys e rate limit não têm gestão de segredo, persistência ou atomicidade suficientes

**Evidência:** `rate_limiter.py:138` usa `HMAC_SECRET` hard-coded; `:141-147` guarda keys e contadores apenas em memória. `:170-191` usa prefixo de seis hex para `_prefix_map`, sujeito a colisão. `:244-258` incrementa contadores e `total_requests` antes de verificar limite, portanto requisições rejeitadas consomem quota. O handler `server.py:1101-1105` aceita `body.get('agent_id', 'anonymous')` quando não há identidade Moltbook, apesar de a documentação declarar proteção.

**Impacto:** reinício perde revogações e quota, segredo no código pode ser extraído, colisão pode revogar a key errada, chamadas bloqueadas consomem quota e um cliente não autenticado pode escolher a identidade declarada. O sistema não satisfaz menor privilégio, rotação e auditoria de segredos [3].

**Classificação:** **Crítica.** **Correção:** usar secret manager e rotação, armazenar somente hashes de key com persistência transacional, eliminar prefixo ambíguo, aplicar check-and-increment atomicamente conforme a política, exigir autenticação de identidade e registrar criação, uso, expiração e revogação.

## 6. Plano de correção por fase

| Fase | Objetivo | Entregáveis e critérios de saída |
|---|---|---|
| P0 — Contenção | Impedir perda de valor e falsos estados | Desabilitar wallet mobile/nativo em release, staking/marketplace remoto, broadcast e custódia; publicar `regtest-only`; remover credenciais do ambiente; manter gate RED. |
| P1 — Criptografia e identidade | Tornar assinatura e recuperação corretas | Implementação secp256k1/BIP-340 validada por vetores oficiais [1]; importação deriva a pública correta; assinatura verifica; AEAD com round-trip; attestation com nonce/TTL; testes cross-language. |
| P2 — Unidades e protocolo | Eliminar ambiguidade financeira | Valores em inteiros/Decimal; serialização canônica; `chain_id`/rede no domínio; nonce de cadeia; idempotência; erros tipados; contrato de endereço único. |
| P3 — Explorer correto | Garantir integridade de dados | Índice de outpoints; débito/crédito; múltiplas saídas; token/native separados; reorg/canonical state; confirmações atualizadas; fee por tipo; rebuild atômico e readiness verdadeiro. |
| P4 — API e segurança operacional | Alinhar runtime e documentação | OpenAPI validado contra handlers; security aplicado; 400/401/404/429 documentados; rate limiter persistente/atômico; secret manager; rotação e auditoria. |
| P5 — Testes regtest | Validar sem BTC real | `bitcoind -regtest` isolado, RPC explicitamente prefixado `-regtest`, dados descartáveis, testes de reorg/double-spend/fee/confirmations, nenhum endpoint mainnet habilitado. |
| P6 — Release gate | Provar não regressão | Testes unitários, property-based, fuzz de parser, integração local, matriz iOS/Android/Python, verificação de SBOM e revisão independente; só então reavaliar o gate. |

## 7. Cenários matemáticos de valorização, sem previsão de preço

O snapshot do usuário contém `BAIT = 0.00111071`, mas esse valor não foi verificado e não deve ser tratado como cotação. Para manter a análise honesta, defina `P0` como um **valor de referência hipotético** e `N` como a quantidade de BAIT. A fórmula é `V = N × P`. Os múltiplos abaixo são apenas cenários matemáticos:

| Cenário | Preço hipotético | Valor de 100.000 BAIT | Múltiplo de P0 |
|---|---:|---:|---:|
| Queda | `0,5 × P0` | `50.000 × P0` | 0,5x |
| Referência | `1,0 × P0` | `100.000 × P0` | 1,0x |
| Alta moderada | `2,0 × P0` | `200.000 × P0` | 2,0x |
| Alta extrema | `10,0 × P0` | `1.000.000 × P0` | 10,0x |

Se, **apenas para ilustrar a aritmética**, `P0 = US$ 0,00111071`, os preços hipotéticos seriam US$ 0,000555355, US$ 0,00111071, US$ 0,00222142 e US$ 0,0111071. Esses números não são metas, forecast, preço justo, liquidez disponível ou recomendação. Eles não incorporam supply, vesting, emissão, liquidez, spread, slippage, impostos, risco de contraparte ou possibilidade de preço zero.

Da mesma forma, para uma posição hipotética de 100 BAIT e uma taxa nominal de 7% ao ano, juros simples dariam `100 × (1 + 0,07) = 107 BAIT`; composição diária, se explicitamente adotada, daria aproximadamente `100 × (1 + 0,07/365)^365 ≈ 107,25 BAIT`. O código atual não prova que a taxa é sustentável, financiada ou efetiva; portanto esses valores são somente cenários de fórmula.

## 8. Risk gate operacional

1. **Bloquear** produção, custodiante, saque, swap BTC/BAIT e broadcast até que SDK-11, SDK-12, SDK-13, SDK-14, SDK-22, SDK-24, SDK-27, EX-32, EX-33 e EX-39 estejam corrigidos e aprovados por revisão independente.
2. Usar somente `bitcoind -regtest`; não usar `mainnet`, `testnet` pública, exploradores de terceiros ou chaves com saldo real durante validação. A cadeia regtest é privada e controlada pelo operador [2].
3. Tratar o explorer atual como **não confiável para saldos, confirmações, remetentes, taxas ou prova de reservas** até a conclusão de P3.
4. Não usar a cotação do snapshot nem APY declarado para prometer valorização, rendimento ou retorno.
5. Antes de qualquer release, verificar que `git status` não contém alterações de auditoria no repositório, que nenhum segredo aparece em logs/artefatos e que o CI falha se placeholders criptográficos forem incluídos.

## 9. Referências

[1]: https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki "BIP-340: Schnorr Signatures for secp256k1"
[2]: https://developer.bitcoin.org/examples/testing.html "Bitcoin Core Developer Examples: Testing Applications and Regtest"
[3]: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html "OWASP Secrets Management Cheat Sheet"

**Resultado final:** os 39 achados acima permanecem abertos; o estado recomendado é **RED / não liberar**. Nenhum BTC real foi movimentado nesta auditoria.

---

## Apêndice A — Lista curta para triagem

A ordem de correção recomendada é: **SDK-11 → SDK-14 → SDK-27 → SDK-24 → SDK-22 → SDK-13/12 → EX-32/33 → EX-39 → EX-30/31/34/35 → SDK-29/02 → EX-37/38 → demais achados**. Essa ordem prioriza perda de chave, assinatura inválida, falsificação de autorização, saldos incorretos e exposição operacional antes de ergonomia.

## Apêndice B — Escopo não coberto

Não foi feita auditoria completa de consenso, rede P2P, contratos fora do escopo SDK/explorer, infraestrutura de produção, dependências de terceiros ou segurança física de dispositivos. Também não foi feita conexão a endpoints públicos, consulta de preço em tempo real, broadcast de transação ou movimentação de BTC. Essas limitações não reduzem o gate RED porque os bloqueadores listados são demonstráveis no código e nos testes locais.

Não foi feito commit nem push. O único artefato produzido por esta tarefa é este relatório em `/home/ubuntu/work/swap-btc-bait/audits/04-sdk-explorer.md`.
