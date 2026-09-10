# b'AI'tcoin (BAIT): infraestrutura monetária para agentes de IA

> **Estado deste documento:** revisão técnica em 10 de setembro de 2026. O repositório contém componentes experimentais e de integração que devem ser tratados como software em validação. A presença de um módulo, teste ou endpoint não constitui autorização para liquidação financeira, operação de custódia ou lançamento em produção.

**Site público:** [mybait.org](https://mybait.org/)
**Repositório:** `Nexus-HUB57/b-AI-tcoin-AI-to-AI-`
**Especificação pública:** [OpenAPI da plataforma](https://www.mybait.org/mylink/openapi.json)

## 1. Escopo e estado operacional

b'AI'tcoin é uma implementação experimental de uma camada de ativos e serviços para agentes de inteligência artificial. O código reúne um núcleo de blockchain baseado em UTXO, processamento nativo de swaps, componentes de bridge, APIs para agentes e ferramentas de observabilidade. A arquitetura foi organizada para separar o caminho de simulação do caminho de liquidação real.

A validação realizada nesta revisão cobre o conjunto de testes de processamento nativo, handoff de bridge, autorização Ed25519, rotação de credenciais LND, monitoramento e mocks gRPC. O resultado observado foi de **39 testes aprovados** nos grupos executados nesta sessão. Essa evidência demonstra comportamento local reproduzível; não demonstra disponibilidade, solvência, segurança econômica ou prontidão para Mainnet.

O caminho de liquidação Lightning permanece **fail-closed**. O executor exige configuração explícita, limites positivos, autorização operacional, desbloqueio manual, aprovação de duas pessoas, nó na rede requerida, invoice BOLT11 compatível e macaroon de escopo limitado. Os testes usam stubs e mocks locais. Nenhuma credencial real foi carregada e nenhum pagamento foi transmitido durante a validação.

## 2. Modelo arquitetural

A plataforma deve ser analisada como um conjunto de subsistemas com fronteiras de confiança distintas:

| Subsistema | Responsabilidade | Estado de validação local |
|---|---|---|
| Núcleo UTXO e consenso | Blocos, transações, validação, PoW e primitivas Schnorr | Testes unitários e de protocolo presentes |
| Swap nativo | Cotações, intenções assinadas, limites e idempotência | Dry-run e testes de ciclo de vida |
| BridgeManager | Lock, prova, threshold de assinaturas, mint, burn e release | Testes locais com handoff |
| Autorização de relayers | Assinaturas Ed25519 sobre envelope canônico de prova | Verificação individual e rejeição de adulteração |
| Integração LND | Preflight, DecodePayReq, SendPaymentV2 e reconciliação | Stubs locais; conexão real não executada |
| Rotação e monitoramento | Credenciais, recriação de canal, healthcheck e métricas | Mocks gRPC e servidor Prometheus local |
| MyLink e AI Store | APIs de agentes, marketplace e superfícies de aplicação | Implementações e documentação específicas do projeto |

O princípio central é **separar autorização, execução e observabilidade**. Um monitor não deve possuir permissão de pagamento. Um relayer não deve possuir chave de custódia. Um processo de CI não deve possuir endpoint ou credencial Mainnet.

## 3. Fluxo de swap e bridge

O fluxo nativo começa com uma cotação e uma intenção assinada. A intenção contém identificadores, ativos, valores, nonce, janela temporal, chave pública e assinatura. O verificador rejeita campos inconsistentes, expiração, derivações inválidas de `order_id` e assinaturas Ed25519 inválidas.

O handoff correlaciona uma intenção a no máximo um lock por `order_id`. A correlação é persistida em SQLite com WAL e operações idempotentes. A prova de bridge só pode avançar quando o evento, a transferência, a cadeia, o valor e a prova Merkle permanecem consistentes.

No caminho de mint, cada assinatura de relayer é verificada individualmente **antes** de ser submetida ao `BridgeManager`. Quando o manager recebe um `RelayerAuthorization`, ele repete a verificação antes de mutar `event.signatures`, o estado da transferência ou os contadores de threshold. Essa defesa em profundidade reduz o risco de um chamador incorreto contornar o componente de autorização.

```text
SwapIntent assinada
        │
        ▼
validação de envelope e expiração
        │
        ▼
lock idempotente no BridgeManager
        │
        ▼
prova Merkle + assinaturas Ed25519 individuais
        │
        ▼
BridgeManager.submit_proof
        │
        ▼
threshold N-of-M
        │
        ▼
mint_wrapped
```

## 4. Integração Lightning LND

O `MainnetSettlementAdapter` não deve ser confundido com o executor dry-run. O primeiro é um adaptador explicitamente protegido para uma operação que pode produzir efeito financeiro; o segundo é a superfície recomendada para desenvolvimento e integração contínua.

O adaptador real requer stubs protobuf gerados a partir das definições oficiais do LND. O canal deve ser criado com TLS, autoridade certificadora controlada e macaroon externo de menor privilégio. O macaroon não deve ser colocado em YAML, código-fonte, argumentos de processo ou logs.

Antes de `SendPaymentV2`, o adaptador verifica os seguintes invariantes:

1. O executor não está pausado.
2. A ordem contém `order_id`, invoice, valor, estado e allowlist.
3. O estado é `bait_confirmed`.
4. O valor está dentro dos limites por ordem e diário.
5. O nó LND anuncia a rede requerida.
6. A invoice é BOLT11 Bitcoin Mainnet e não está expirada.
7. O valor decodificado coincide exatamente com o valor da ordem.
8. O `ApprovalGate` confirma duas aprovações de operadores distintos.
9. A aprovação está vinculada ao hash da invoice e ao hash da configuração.
10. O resultado terminal é persistido para reconciliação e idempotência.

### 4.1 Rotação de macaroon e sessão gRPC

A rotação usa três estados de arquivo: credencial ativa, candidata staged e credencial anterior. A ativação é atômica. Após a ativação, o `LndGrpcConnectionManager` recria o canal e os stubs, executa `GetInfo`, valida a rede e confirma uma identidade de nó não vazia. Somente depois disso a sessão nova substitui a antiga.

Se a revalidação falhar, o manager restaura a credencial anterior e mantém a sessão validada anterior. O canal antigo só é fechado depois que a sessão candidata passa no healthcheck.

### 4.2 Monitoramento Prometheus

`LndMonitor` executa apenas `GetInfo`, persiste snapshots em SQLite e pode expor `/metrics` no formato Prometheus. As métricas incluem disponibilidade, timestamp da observação, altura de bloco, canais por estado e informação do último erro.

Exemplo de inicialização local:

```python
from threading import Thread
from scripts.lnd_monitor import LndMonitor

monitor = LndMonitor(
    lightning_stub=lnd_lightning_stub,
    message_module=lnrpc_pb2,
    state_db="/var/lib/baitcoin/lnd-monitor.sqlite3",
)

server = monitor.serve_metrics(host="127.0.0.1", port=9899)
Thread(target=server.serve_forever, daemon=True).start()
monitor.run_forever(interval_seconds=5)
```

O endpoint deve permanecer em rede privada ou atrás de uma camada de autenticação e TLS. Não se deve expor o servidor embutido diretamente à Internet.

## 5. Controles de segurança

| Controle | Implementação | Limitação conhecida |
|---|---|---|
| Autorização de relayer | Ed25519, envelope canônico, chaves públicas registradas | Registro de chaves ainda depende de operação externa segura |
| Aprovação operacional | Dois operadores distintos, assinatura vinculada à ordem | Requer infraestrutura de identidade e cofre de aprovações |
| Credencial LND | Provider externo, permissões restritas, validação de arquivo | Renovação do segredo deve ser integrada ao secret manager operacional |
| Idempotência | SQLite, chaves por ordem e reconciliação | Produção distribuída exige coordenação de armazenamento |
| Pausa e rollback | Controle local, rollback de macaroon e preservação de sessão | Procedimento humano e autoridade de emergência ainda são necessários |
| CI | Sem secrets, endpoint desabilitado, modo dry-run e `pip-audit` | Auditoria externa e análise de supply chain continuam necessárias |

Nenhum controle local substitui auditoria independente, revisão de modelo de ameaça, gestão de chaves, monitoramento de fraude, testes de recuperação ou aprovação formal de produção.

## 6. Layout de código relevante

| Caminho | Conteúdo |
|---|---|
| `baitcoin_core/` | Núcleo blockchain, consenso e criptografia |
| `baitcoin_bridge/manager.py` | Máquina de estados lock/mint/burn/release |
| `baitcoin_bridge/authorization.py` | Verificação Ed25519 de relayers |
| `native_processing/swap_protocol.py` | Intenções e assinaturas do swap |
| `native_processing/bridge_handoff.py` | Correlação entre swap e BridgeManager |
| `scripts/swap_dry_run.py` | Executor sem transmissão |
| `scripts/lnd_mainnet_adapter.py` | Adaptador LND protegido |
| `scripts/lnd_channel_rotation.py` | Recriação e revalidação de sessão gRPC |
| `scripts/macaroon_rotation.py` | Staging, ativação e rollback de macaroon |
| `scripts/lnd_monitor.py` | Healthcheck, persistência e métricas Prometheus |
| `config/isp-lightning.template.yaml` | Template sem credenciais operacionais |
| `.github/workflows/approval-gate-security.yml` | CI de segurança sem acesso Mainnet |
| `tests/` | Testes nativos, bridge, autorização, mocks e integração local |

## 7. Desenvolvimento local

A execução deve utilizar Python 3.11 ou superior, ambiente virtual isolado e dependências declaradas no repositório. Um ciclo mínimo de validação é:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-lightning-adapter.txt pytest

PYTHONDONTWRITEBYTECODE=1 python -m pytest -q \
  tests/test_swap_bridge_handoff.py \
  tests/test_bridge_authorization_handoff_local.py \
  tests/test_lnd_channel_authorization_local.py \
  tests/test_approval_and_macaroon_local.py \
  tests/test_lnd_mainnet_adapter_local.py \
  tests/test_lnd_monitor_rotation_local.py \
  tests/test_native_processing.py
```

O template de configuração deve ser validado em modo de placeholders durante o desenvolvimento:

```bash
python scripts/validate_lightning_config.py \
  config/isp-lightning.template.yaml \
  --allow-placeholders
```

Uma configuração operacional não pode conter placeholders, limites nulos, endpoint não autorizado ou credenciais embutidas. O dry-run deve ser usado antes de qualquer integração com um serviço externo.

## 8. CI/CD e colaboração

O workflow de segurança executa em Pull Requests e em alterações relevantes na branch principal. Ele compila os componentes, executa testes locais, procura material privado, verifica whitespace e audita dependências. As permissões são somente leitura e as variáveis de segurança desabilitam explicitamente a Mainnet.

Alterações em um repositório compartilhado devem seguir esta sequência:

1. Atualizar referências remotas com `git fetch`.
2. Inspecionar divergência com `git rev-list --left-right --count HEAD...origin/main`.
3. Preservar alterações não commitadas antes de um fast-forward.
4. Aplicar somente fast-forward quando a branch local não possuir commits divergentes.
5. Reaplicar alterações locais e resolver conflitos de forma explícita.
6. Executar testes direcionados e testes de regressão.
7. Criar Pull Request para revisão; não fazer merge automaticamente.

Arquivos gerados, como `__pycache__`, não devem ser incluídos em commits. Credenciais, seeds, chaves privadas e macaroons nunca devem ser adicionados ao Git.

## 9. Limites e próximos gates

O projeto ainda requer gates independentes antes de qualquer operação financeira real. Esses gates incluem revisão de código por pares, auditoria criptográfica, teste de recuperação, threat modeling do bridge, gestão formal de chaves, validação de limites econômicos, observabilidade de produção, procedimento de incidente e aprovação explícita da infraestrutura Lightning.

A documentação e os testes deste repositório não autorizam liquidação real. A mudança de `dry-run` para operação real deve ser uma decisão operacional separada, com endpoint, carteira, credencial, limites, allowlist, política de confirmação e rollback documentados e aprovados.

## 10. Referências

[1]: https://www.mybait.org/ "Site público da plataforma mybait.org"

[2]: https://www.mybait.org/mylink/openapi.json "Especificação OpenAPI pública do MyLink"

[3]: https://github.com/lightningnetwork/lnd "Lightning Network Daemon — repositório oficial"

[4]: https://api.lightning.community/ "Documentação da API do LND"

[5]: https://prometheus.io/docs/instrumenting/exposition_formats/ "Prometheus text-based exposition format"
