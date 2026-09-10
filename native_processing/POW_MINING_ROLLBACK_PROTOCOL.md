# Protocolo técnico — Correção de rollback na mineração PoW

## 1. Objetivo

Este protocolo define a correção aplicada ao ciclo de mineração da blockchain BAIT para garantir que uma tentativa de Proof of Work (PoW) malsucedida não descarte transações válidas do mempool, não consuma UTXOs e não deixe o estado contábil divergente do estado da cadeia.

A correção é especialmente relevante para o settlement BTC/BAIT: uma transação BAIT pode estar validada e pronta para confirmação, enquanto uma tentativa individual de mineração ainda pode não encontrar um nonce válido dentro do limite de iterações.

## 2. Falha anterior

O fluxo anterior validava as transações selecionadas e removia seus UTXOs de entrada antes de concluir `consensus.mine_block(block)`. O mempool também era podado antes do resultado do PoW. Quando o consenso retornava `False`, a transação desaparecia do mempool apesar de continuar não confirmada, e o UTXO de origem já não estava disponível.

Esse comportamento violava duas propriedades fundamentais:

1. **Atomicidade da mineração:** uma tentativa que não produz bloco não pode alterar o ledger confirmado.
2. **Retry seguro:** uma transação válida deve permanecer reprocessável até uma tentativa PoW bem-sucedida.

Com a dificuldade de teste do consenso, uma falha de uma tentativa é esperada e não representa rejeição da transação.

## 3. Protocolo corrigido

A função de mineração agora opera em duas fases:

### Fase A — Preparação sem efeitos irreversíveis

1. Selecionar transações do fee market.
2. Validar cada transação com `TransactionVerifier`.
3. Montar o coinbase e o cabeçalho candidato.
4. Executar `consensus.mine_block(block)`.
5. Se o PoW falhar, retornar sem alterar cadeia, UTXO ou mempool.

### Fase B — Commit após PoW

Somente quando o consenso retorna sucesso:

1. Finalizar o bloco.
2. Remover UTXOs consumidos pelas transações confirmadas.
3. Podar do mempool somente as transações incluídas.
4. Registrar a mediana de taxas do bloco.
5. Acrescentar o bloco à cadeia.
6. Atualizar o UTXO set com coinbase e outputs das transações.
7. Persistir o bloco quando a blockchain estiver em modo persistente.

## 4. Invariantes de segurança

| Invariante | Verificação |
|---|---|
| Falha de PoW não altera altura | `height` permanece igual antes e depois da tentativa |
| Falha de PoW preserva mempool | tx validada continua em `fee_market.entries` |
| Falha de PoW preserva funding | UTXO de entrada continua em `utxo_set` |
| Commit acontece uma vez | UTXO e mempool só são mutados após `mined=True` |
| Settlement pode ser repetido | o executor continua vendo o tx como pendente até confirmação |
| Confirmação é observável | settlement reporta `confirmed` somente após a transação estar em bloco |

## 5. Relação com o motor BTC/BAIT

O `BaitBlockchainSettlement` insere uma transação BAIT assinada no mempool. O `SwapExecutor` mantém o estado `bait_submitted` enquanto a transação não estiver em bloco. Se a mineração falhar, uma próxima tentativa pode incluir a mesma transação sem recriar a ordem e sem selecionar outro UTXO indevidamente.

A transação é idempotente por `order_id` no banco de settlement e por seu `tx_id` determinístico. Uma falha de mineração não deve ser convertida em `reconciling` nem em perda silenciosa de liquidez.

## 6. Testes de aceitação

O teste nativo `tests/test_native_swap_executor.py` cobre:

- funding do bridge BAIT;
- criação e assinatura da transação de settlement;
- entrada no mempool;
- tentativa de mineração;
- confirmação em bloco;
- idempotência do settlement;
- transição final `bait_submitted → settled`.

O teste repete tentativas de mineração porque o PoW local tem limite finito de iterações. A aceitação exige que a transação seja confirmada dentro do limite sem ser perdida entre tentativas.

## 7. Operação

Em produção, falha de uma tentativa de mineração deve gerar métrica de retry, não rejeição financeira. O operador deve monitorar:

- tamanho e idade do mempool;
- número de tentativas PoW sem bloco;
- idade de ordens em `bait_submitted`;
- divergências entre mempool, UTXO set e settlement database;
- persistência WAL/snapshot após reinicialização.

A correção não altera a dificuldade, não relaxa a validação de transações e não transforma PoW em confirmação automática.
