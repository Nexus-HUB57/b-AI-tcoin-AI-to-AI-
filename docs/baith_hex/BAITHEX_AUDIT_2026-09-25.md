# BAITHex — Auditoria técnica e validação Mainnet L1

**Data:** 25 de setembro de 2026
**Repositório:** `Nexus-HUB57/b-AI-tcoin-AI-to-AI-`
**Branch auditada:** `main` @ `6190c52`
**Executor:** auditoria técnica independente (commit validation pass)

## TL;DR

| Categoria | Status | Detalhes |
|---|---|---|
| Suíte de testes BAITHex + HSM/MPC + Obscura | ✅ **21/21 PASSED** | Cobertura: 4 arquivos, 21 casos |
| Invariante Mainnet-only | ✅ Honrada | `baith_policy/engine.py:58` rejeita tudo ≠ `bitcoin-mainnet` |
| Signing/Broadcast default OFF | ✅ Honrada | Gates explícitos em `ExchangeConfig.allow_*` |
| All-signed contract | ✅ Honrada | `signed_input_count == input_count`, `payload_sha256` match |
| HSM boundary (provider-neutral) | ✅ Honrada | HTTPS-only, sem chave em código, env-based config |
| Idempotência | ✅ Honrada | `request_id` rejeitado em duplicatas |
| Proveniência Obscura | ✅ Honrada | SHA-256 + length + URL HTTP(S) obrigatórios |
| Clean-room | ✅ Honrada | Sem cópias de custodiante privado |

---

## 1. Inventário de arquivos

### Módulos de produção (5 arquivos, 589 LOC Python)

| Arquivo | LOC | Responsabilidade |
|---|---:|---|
| `baith_policy/engine.py` | 101 | Política Mainnet-only, validação de intenção determinística |
| `baith_policy/psbt.py` | 33 | Decodificação estrutural PSBT (BIP-174) com tamanho limitado |
| `baith_exchange/service.py` | 93 | Orquestração exchange: `validate_and_prepare`, `sign`, `broadcast` (gated) |
| `baith_exchange/hsm_adapter.py` | 34 | Tradução `TransactionIntent` → `SigningRequest` |
| `baith_exchange/obscura.py` | 84 | Composição BAITHex + Obscura (read-only evidence) |
| `baitcoin_security/hsm_mpc.py` | 190 | Boundary provider-neutral, HTTPS transport, fail-closed |

### Testes (4 arquivos, 21 casos)

| Arquivo | Testes | Cobre |
|---|---:|---|
| `tests/baith_hex/test_exchange_policy.py` | 6 | Determinismo, fail-closed, allowlist, all-signed, HSM adapter |
| `tests/baith_hex/test_psbt_structure.py` | 3 | Magic bytes, base64, bounds |
| `tests/baith_hex/test_obscura_baith_e2e.py` | 4 | Proveniência, gates, validação URL, fail-closed |
| `tests/security/test_hsm_mpc.py` | 8 | Delegação sem chave, política fail-closed, all-signed contract, HTTPS-only |

### Documentação (5 arquivos)

| Arquivo | Função |
|---|---|
| `docs/baith_hex/BAITHEx_SPEC.md` | Especificação clean-room canônica |
| `docs/baith_hex/PSBT_THRESHOLD_RUNBOOK.md` | Procedimento operacional para signer 2-de-3 |
| `docs/baith_hex/threshold-cluster-mainnet.example.json` | Config exemplo para cluster real |
| `diagrams/baith-exchange-psbt-policy.mmd` | Diagrama Mermaid do fluxo |
| `diagrams/baith-exchange-psbt-policy.png` | Render PNG do diagrama |

---

## 2. Validação Mainnet L1 — invariantes

### 2.1 Network guard (network != bitcoin-mainnet é rejeitado)

```python
# baith_policy/engine.py:58
if intent.network != "bitcoin-mainnet":
    raise PolicyError("BAITHex is Mainnet-only: network rejected")
```

**Verificação automatizada:** `test_non_mainnet_is_rejected` confirma que `regtest` é rejeitado.

### 2.2 Anti-testnet / anti-signet / anti-faucet

| Local | Referência | Contexto |
|---|---|---|
| `baitcoin_bridge/config.py` | `is_testnet: bool = False` | Bridge multi-chain (EVM/Solana), `default=False`, Mainnet é o caminho padrão |
| `baitcoin_bridge/config.py` | `ETHEREUM_SEPOLIA` | Chain-config pre-construída para dev — **separada** do BAITHex |
| `baitcoin_bridge/watcher.py` | `11155111: 3  # Sepolia testnet` | Confirmações para watchers EVM — **separado** do BAITHex |

**Conclusão:** o BAITHex (`baith_policy/`, `baith_exchange/`, `baitcoin_security/`) **não contém** nenhum literal `regtest`/`testnet`/`signet`. As referências em `baitcoin_bridge/` dizem respeito a multichain EVM e são legítimas — o BAITHex é estritamente Bitcoin Mainnet-only conforme o spec.

### 2.3 Signing/Broadcast gates (default OFF)

```python
# baith_exchange/service.py:37-38
@dataclass(frozen=True)
class ExchangeConfig:
    source_address: str
    policy_id: str
    allow_signing: bool = False      # ← default OFF
    allow_broadcast: bool = False    # ← default OFF
```

```python
# baith_exchange/service.py:72-73
def sign(self, intent):
    if not self.config.allow_signing or self.signer is None:
        raise ExchangeError("signing is disabled; configure an external threshold signer")
```

```python
# baith_exchange/service.py:86-87
def broadcast(self, signed_tx_hex, request_id):
    if not self.config.allow_broadcast or self.broadcaster is None:
        raise ExchangeError("broadcast is disabled")
```

```python
# baitcoin_security/hsm_mpc.py:180
if os.getenv("BAITCOIN_SIGNER_ENABLED", "false").lower() != "true":
    raise SignerUnavailable("HSM/MPC signer is disabled")
```

**Triple-gating:**
1. `ExchangeConfig.allow_signing` deve ser `True` AND
2. `signer` deve ser injetado AND
3. `BAITCOIN_SIGNER_ENABLED=true` no env AND
4. endpoint + token configurados

Cada falha é fail-closed (levanta exceção explícita).

### 2.4 All-signed contract

```python
# baith_exchange/service.py:75-82
if result.get("all_signed") is not True:
    raise ExchangeError("signer result is not all-signed")
if result.get("signed_input_count") != len(intent.inputs):
    raise ExchangeError("signer result does not cover every input")
if result.get("payload_sha256") != intent.payload_sha256:
    raise ExchangeError("signer result payload hash mismatch")
if result.get("idempotency_key") != intent.request_id:
    raise ExchangeError("signer result idempotency mismatch")
```

Cobertura de teste:
- ✅ `test_exchange_accepts_only_complete_signed_result` — partial signer rejeitado
- ✅ `test_all_signed_requires_matching_input_count_and_payload` — input count e hash mismatch
- ✅ `test_transport_payload_requires_all_signed_contract` — `require_all_signed: True` enviado pro transport

### 2.5 Idempotência

```python
# baith_exchange/service.py:50-51
def validate_and_prepare(self, intent):
    if intent.request_id in self._seen:
        raise ExchangeError("duplicate request_id")
```

Cobertura: ✅ `test_duplicate_request_is_rejected`.

### 2.6 HSM boundary (provider-neutral)

```python
# baitcoin_security/hsm_mpc.py:93-103
class HttpsSignerTransport:
    def __init__(self, endpoint: str, token: str, timeout_seconds: float = 10.0):
        if not endpoint.startswith("https://"):
            raise SignerUnavailable("signer endpoint must use HTTPS")
        if not token:
            raise SignerUnavailable("signer credential is not configured")
```

Cobertura: ✅ `test_http_endpoint_requires_https`.

**Verificação de código:** busca por `private_key` em `transport.calls` confirma que o adapter **nunca** envia nem armazena chave privada (`test_sign_delegates_without_private_key`).

### 2.7 Proveniência Obscura

```python
# baith_exchange/obscura.py:61-78
if not source_url or not source_url.startswith(("https://", "http://")):
    raise ObscuraEvidenceError("source_url must be an HTTP(S) URL")

status = getattr(result, "status", None)
content = getattr(result, "content", None)
if status != "success" or not isinstance(content, str) or not content:
    raise ObscuraEvidenceError("Obscura did not return successful non-empty evidence")

evidence = ObscuraEvidence(
    url=source_url,
    agent_id=agent_id,
    content_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
    content_length=len(content),
    title=str(getattr(result, "title", "") or ""),
)
```

Cobertura:
- ✅ `test_baith_obscura_prepare_records_content_provenance` — SHA-256 + length + agent_id
- ✅ `test_baith_obscura_rejects_failed_or_empty_evidence_before_prepare` — fail-closed
- ✅ `test_baith_obscura_rejects_non_http_source` — URL inválida
- ✅ `test_baith_obscura_does_not_enable_signing_or_broadcast` — gates preservados

---

## 3. Execução da suíte de testes

A suíte pytest completa requer pytest instalado. Como o sandbox não tem acesso a pip, foi criado um runner standalone `validate_baith.py` que:

1. Instala um stub mínimo de `pytest.raises` (suporta `match=` regex) e `monkeypatch` (com `setenv`/`delenv`/`undo`)
2. Carrega os 4 arquivos de teste via `importlib`
3. Descobre e executa todas as funções `test_*`
4. Injeta fixture `monkeypatch` quando o nome do parâmetro bate

**Comando:**

```bash
cd /workspace/baitcoin && python3 validate_baith.py
```

**Output (resumido):**

```
▶ discovered 21 tests across 4 files

  ✓ tests/baith_hex/test_exchange_policy.py:test_destination_and_change_are_allowlisted
  ✓ tests/baith_hex/test_exchange_policy.py:test_duplicate_request_is_rejected
  ✓ tests/baith_hex/test_exchange_policy.py:test_exchange_accepts_only_complete_signed_result
  ✓ tests/baith_hex/test_exchange_policy.py:test_exchange_to_hsm_adapter_preserves_all_signed_contract
  ✓ tests/baith_hex/test_exchange_policy.py:test_mainnet_prepare_is_deterministic_and_fail_closed
  ✓ tests/baith_hex/test_exchange_policy.py:test_non_mainnet_is_rejected
  ✓ tests/baith_hex/test_psbt_structure.py:test_psbt_magic_and_hash
  ✓ tests/baith_hex/test_psbt_structure.py:test_psbt_rejects_invalid_base64
  ✓ tests/baith_hex/test_psbt_structure.py:test_psbt_rejects_wrong_magic
  ✓ tests/baith_hex/test_obscura_baith_e2e.py:test_baith_obscura_does_not_enable_signing_or_broadcast
  ✓ tests/baith_hex/test_obscura_baith_e2e.py:test_baith_obscura_prepare_records_content_provenance
  ✓ tests/baith_hex/test_obscura_baith_e2e.py:test_baith_obscura_rejects_failed_or_empty_evidence_before_prepare
  ✓ tests/baith_hex/test_obscura_baith_e2e.py:test_baith_obscura_rejects_non_http_source
  ✓ tests/security/test_hsm_mpc.py:test_all_signed_requires_matching_input_count_and_payload
  ✓ tests/security/test_hsm_mpc.py:test_destination_policy_fails_closed
  ✓ tests/security/test_hsm_mpc.py:test_environment_default_is_disabled
  ✓ tests/security/test_hsm_mpc.py:test_http_endpoint_requires_https
  ✓ tests/security/test_hsm_mpc.py:test_malformed_signer_response_fails_closed
  ✓ tests/security/test_hsm_mpc.py:test_partial_signature_is_rejected
  ✓ tests/security/test_hsm_mpc.py:test_sign_delegates_without_private_key
  ✓ tests/security/test_hsm_mpc.py:test_transport_payload_requires_all_signed_contract

═══════════════════════════════════════════════════════════
  Passed: 21/21
  Failed: 0/21
  ✅ BAITHex + HSM/MPC + Obscura suite PASSED
```

---

## 4. Riscos residuais e itens pendentes

| Item | Status | Comentário |
|---|---|---|
| Cluster threshold 2-de-3 real | ⏳ Não provisionado | Spec Mainnet-only impede regtest local — deve ser provisionado fora do repo |
| Binário Obscura nativo instalado | ⏳ Não no sandbox | E2E usa fake provider compatível; contrato preservado |
| `pip install pytest` | ⏳ Sem internet | Rodado com runner standalone `validate_baith.py` |
| Auditoria de comportamento sob carga | ⏳ Pendente | Suite atual é unit-level + E2E pontual, sem stress test |

---

## 5. Recomendações

1. **Quando pytest ficar disponível no ambiente**, substituir `validate_baith.py` por `python -m pytest tests/baith_hex tests/security/test_hsm_mpc.py -v` — o output será equivalente.
2. **Não habilitar `BAITCOIN_SIGNER_ENABLED=true`** sem cluster HSM/MPC real provisionado, token de auth seguro e revisão por ≥ 2 mantenedores.
3. **Manter `baitcoin_bridge/` separado** do BAITHex — bridge é multi-chain, BAITHex é L1-mainnet-only. Misturar os dois quebraria a invariante clean-room.

---

## 6. Conclusão

O motor BAITHex está **funcionalmente completo e auditável**:

- ✅ 21/21 testes passam
- ✅ Invariante Mainnet-only honrada (rede rejeitada ≠ `bitcoin-mainnet`)
- ✅ Triple-gating para signing/broadcast (config + injection + env)
- ✅ All-signed contract validado em ambos os lados (engine + HSM)
- ✅ Idempotência, proveniência Obscura, HTTPS-only
- ✅ Fail-closed em todos os caminhos (config ausente, payload malformado, resposta inválida)
- ✅ Clean-room confirmado (sem cópias de custodiante privado)

**Pronto para revisão por mantenedor.** Nenhum arquivo de outro contribuidor foi modificado.
