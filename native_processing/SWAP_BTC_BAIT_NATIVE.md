# Motor de swap BTC/BAIT em full nodes nativos

## Fluxo implementado

O fluxo end-to-end agora é composto por quatro camadas. `SwapEngine` gera a cotação e mantém a ordem idempotente em SQLite. `SwapIntent` transforma a ordem em uma mensagem Ed25519 auto-verificável, contendo a rede Bitcoin explícita, o endereço de depósito BTC e a chave pública BAIT de destino. `SwapSyncStore` valida, deduplica e replica a intenção por sequência através do TCP/P2P nativo. `SwapExecutor` observa o depósito em Bitcoin Core, exige o número configurado de confirmações e só então chama o settlement BAIT.

O `BitcoinCoreReader` é watch-only: consulta `getblockchaininfo`, `scantxoutset`, `getrawtransaction`, `gettxout` e `getblockcount`, confere a rede declarada e só retorna depósitos com txid/vout/scriptPubKey em HEX válido e comprovadamente não gastos. Ele não importa chaves, assina ou transmite transações Bitcoin. O `BaitBlockchainSettlement` prepara uma transação BAIT nativa com UTXO do bridge, valida-a contra o UTXO set antes do mempool, assina com Schnorr através da chave fornecida pelo processo hospedeiro, vincula o digest da paridade ao payload e só reporta `confirmed` depois da inclusão em bloco.

## Estados

| Estado | Condição | Efeito externo |
|---|---|---|
| `intent_validated` | Assinatura, identidade e validade aceitas | Nenhum |
| `btc_observed` | UTXO de valor exato encontrado | Nenhum |
| `btc_confirmed` | Confirmações mínimas atingidas | Nenhum quando a proteção padrão está ativa |
| `bait_submitted` | Settlement BAIT idempotente aceitou a transação | Uma transação BAIT |
| `settled` | A transação BAIT está em bloco | Fluxo concluído |
| `reconciling` | Rede, endereço, valor, outpoint ou settlement divergente | Pagamento automático interrompido |

O executor começa com `enable_settlement=False`. A ativação deve ser feita apenas em ambiente controlado, com limites de valor, segregação de chaves, monitoramento e procedimento de reconciliação. O módulo não persiste a chave privada; o processo hospedeiro deve fornecer um signer protegido por carteira/HSM ou equivalente.

Quando `enable_settlement=True`, o executor exige um `ParityGate` com verificador externo de attestation. A attestation precisa provar `BAIT/USDT` dentro da tolerância configurada, ter quorum, timestamp, expiração e fontes distintas. Sem essa prova, o executor rejeita a intenção antes de observar/liquidar o depósito. O fixture aceito pelo harness regtest é exclusivamente local e não é um oráculo de produção.

## Integração mínima

```python
from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
from native_processing.native_adapters import BaitBlockchainSettlement, BitcoinCoreReader
from native_processing.swap_engine import SwapEngine
from native_processing.swap_executor import SwapExecutor
from native_processing.swap_service import NativeSwapService
from native_processing.swap_sync import SwapSyncStore

engine = SwapEngine("/var/lib/baitcoin/swap-engine.sqlite")
store = SwapSyncStore("/var/lib/baitcoin/swap-sync.sqlite", "node-a")
bitcoin = BitcoinCoreReader(
    "http://127.0.0.1:8332",
    username="rpc-user",
    password="RPC_PASSWORD_FROM_SECRET_STORE",
    network="mainnet",
)
blockchain = Blockchain(persistent=True)
bridge_signer = SchnorrKeyPair()  # carregar via carteira segura; não commitar segredo
bait = BaitBlockchainSettlement(
    blockchain,
    bridge_signer,
    network="mainnet",
    db_path="/var/lib/baitcoin/swap-settlement.sqlite",
)
executor = SwapExecutor(
    "/var/lib/baitcoin/swap-executor.sqlite",
    bitcoin,
    bait,
    required_confirmations=3,
    enable_settlement=False,
)
service = NativeSwapService(engine, store, executor)
```

Para colocar o fluxo em produção, o operador deve fornecer o endereço de depósito Bitcoin por ordem, um destinatário BAIT válido e a chave de bridge por um componente de custódia separado. O endereço de RPC nunca deve ser usado para inferir a rede; `network` é obrigatório e deve ser comparado com o resultado de `getblockchaininfo`.

## Verificação

No repositório principal:

```bash
python3 -m pytest -q tests/test_native_processing.py tests/test_native_swap_executor.py tests/test_p2p_swap_tcp_e2e.py
```

O teste TCP do pacote entregue foi incorporado ao caminho principal antes da execução, porque o ZIP original importava `baitcoin_core` e `native_processing` sem conter esses pacotes no diretório de testes.

Os testes não conectam em Bitcoin Mainnet nem movem fundos reais. O teste de settlement usa uma `Blockchain` BAIT local e minera um bloco de confirmação, validando a transação nativa, a assinatura Schnorr, a idempotência e a transição final para `settled`.
