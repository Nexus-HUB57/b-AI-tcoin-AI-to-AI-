# Auditoria cirúrgica do repositório e integração BAITHex–Obscura

**Data:** 23 de setembro de 2026  
**Repositório:** `Nexus-HUB57/b-AI-tcoin-AI-to-AI-`  
**Clone de auditoria:** branch `main`, sem alterações prévias

## Resultado da divergência de commits

A `main` remota atual está no commit `0cb2129` e possui **376 commits alcançáveis**. O comando `git rev-list --all --count` retorna **443** porque também conta commits preservados em branches remotas. A diferença é de **67 commits fora da main**, não uma prova de perda de histórico.

Não foram encontrados objetos Git inacessíveis pelo `git fsck --full --no-reflogs --unreachable`. Portanto, não há commits removidos que possam ser restaurados com segurança a partir deste clone.

Os maiores conjuntos fora da main estão preservados em branches específicas:

| Branch | Commits não alcançáveis pela main |
|---|---:|
| `remediation/phase-2-contracts` | 53 |
| `docs/calldata-uniswap-gas` | 44 |
| `fix/stress-handshake-readiness` | 42 |
| `feat/mylink-bip322-utxo-custody` | 38 |
| `feat/hex-evm-dry-run` | 6 |
| outras branches | 1–4 cada |

Esses conjuntos se sobrepõem entre si; os números não devem ser somados para produzir um total de commits a restaurar. As branches BAITHex `feat/baith-exchange-policy-mainnet-only` e `feat/baith-all-signed-e2e` já estão integradas à main. A branch `recovery/restore-main-history` também não possui commits exclusivos em relação à main.

**Decisão:** nenhuma restauração automática ou force-push foi executado. A restauração correta, se necessária, deve ser feita por PR seletivo após revisão de cada branch, não por merge em massa.

## Estado BAITHex

A main já contém os módulos:

- `baith_policy/engine.py` — política Bitcoin Mainnet-only;
- `baith_policy/psbt.py` — validação estrutural PSBT;
- `baith_exchange/service.py` — preparação, signing gate e broadcast gate;
- `baith_exchange/hsm_adapter.py` — adaptação para HSM/MPC;
- `baitcoin_security/hsm_mpc.py` — boundary provider-neutral all-signed;
- `baitcoin_bridge/relayer.py` — relayer separado;
- `tests/baith_hex/` e `tests/security/`.

Os arquivos Python correspondentes do ZIP são byte a byte iguais aos módulos atuais nos casos de `engine.py`, `psbt.py`, `hsm_adapter.py`, `hsm_mpc.py`, `service.py`, `relayer.py` e seus testes. O ZIP funciona como snapshot de auditoria, não como fonte de commits faltantes.

## Integração BAITHex–Obscura

Foi adicionada uma composição isolada em `baith_exchange/obscura.py`. Ela:

1. solicita evidência somente leitura a um provider compatível com `ObscuraBridge`;
2. exige URL HTTP(S), status `success` e conteúdo não vazio;
3. calcula SHA-256 e comprimento do conteúdo para proveniência auditável;
4. chama `BaithExchange.validate_and_prepare()` somente depois da evidência válida;
5. preserva os gates existentes: signing e broadcast continuam desabilitados por padrão;
6. não armazena, deriva ou transmite chaves privadas.

O adaptador foi exportado em `baith_exchange/__init__.py`. A integração foi testada com provider determinístico compatível com a interface Obscura, incluindo sucesso, conteúdo vazio, erro do provider e URL inválida.

## Validação

A suíte combinada existente e nova passou:

```text
55 passed in 0.06s
```

O E2E específico BAITHex–Obscura passou:

```text
4 passed in 0.02s
```

Os 51 testes anteriores de BAITHex, HSM/MPC e Obscura também permaneceram aprovados. O binário externo Obscura não está instalado neste sandbox; por isso, o E2E usa um provider fake compatível para validar o contrato de integração e mantém o caminho real fail-closed quando o binário não responde com evidência bem-sucedida.

## Arquivos modificados

- `baith_exchange/obscura.py`
- `baith_exchange/__init__.py`
- `tests/baith_hex/test_obscura_baith_e2e.py`
- este relatório

Nenhum arquivo de outro desenvolvedor foi sobrescrito e nenhum commit histórico foi reescrito.
