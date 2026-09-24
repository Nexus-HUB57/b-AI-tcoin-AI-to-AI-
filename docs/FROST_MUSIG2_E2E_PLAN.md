# FROST & MuSig2 — Plano E2E para ParityGate BAIT

**Data:** 2026-09-24  
**Status atual:** multi-sig BIP-340 concatenada (v1) em produção de testes  
**Alvo v2:** proof agregado de 64 bytes

---

## 1. MuSig2 (BIP-327) — agregação n-of-n

### Fluxo
```
Round 1: cada oráculo publica (pubkey, nonce commitment)
Round 2: cada oráculo envia partial signature
Agregador: combina → 1 assinatura Schnorr de 64 bytes
```

### Quando usar
- Todos os oráculos estão online e sincronizados
- Não precisa de threshold (todos devem assinar)
- Quer proof mínimo (64 B vs 192 B)

### Dependências Python / Rust
| Lang | Crate / Lib | Notas |
|------|-------------|-------|
| Rust | `secp256k1` + `musig2` / `secp256k1-zkp` | Referência de implementação |
| Python | port manual ou FFI para libsecp256k1-zkp | Ainda sem lib madura pure-Python |

### Integração com ParityGate
```python
# verify_proof v2
def verify_musig2(attestation) -> bool:
    agg_pubkey = derive_aggregate_pubkey(authorized_set)
    sig = decode_64(attestation.proof_b64)  # single sig
    return bip340_verify(agg_pubkey, message, sig)
```
A API do `ParityGate` **não muda** — só o callable `verify_proof`.

### Riscos
- 2 round-trips → latência (oráculos precisam de canal mTLS)
- Abort se 1 oráculo falhar (n-of-n)

---

## 2. FROST — threshold t-of-n

### Fluxo
```
Setup (uma vez): DKG → cada oráculo recebe share
Sign: t shares produzem 1 assinatura de 64 bytes
Verify: como Schnorr normal sobre group public key
```

### Quando usar
- Quer resiliência (ex.: 3-of-5 oráculos)
- Não quer revelar quais oráculos assinaram
- Oráculos podem estar parcialmente offline

### Dependências
| Lang | Lib | Maturidade |
|------|-----|------------|
| Rust | `frost-secp256k1` (Zcash), `secp256k1-zkp` | Alta |
| Python | experimental / FFI | Baixa |

### Integração
Idêntica ao MuSig2 do ponto de vista do verifier: 1 sig de 64 B sobre group key.

---

## 3. Roadmap sugerido

| Fase | Entrega | Critério de aceite |
|------|---------|-------------------|
| v1 (feito) | Multi-sig concatenada BIP-340 | E2E Python PASS |
| v1.1 | Pubkeys de staging no ParityGate de deploy | authorized_pubkeys.json versionado (só pubs) |
| v2-alpha | MuSig2 em Rust (lib) + FFI Python | cargo test + proof 64 B verificado |
| v2-beta | Oráculos daemons com nonce exchange | latência < 5 s, 100 rodadas |
| v2-frost | FROST 3-of-5 opcional | 1 share offline ainda produz sig |

---

## 4. Skeleton de interface (estável)

```python
class AggregateVerifier(Protocol):
    def aggregate_pubkey(self, source_ids: Sequence[str]) -> bytes: ...
    def verify(self, message: bytes, proof_b64: str, source_ids: Sequence[str], quorum: int) -> bool: ...

# v1
class ConcatSchnorrVerifier: ...
# v2
class MuSig2Verifier: ...
class FrostVerifier: ...
```

O `make_schnorr_verify_proof` atual continua válido; novos verifiers entram como drop-in.

---

## 5. Decisão

**Agora:** manter v1 (concat) — já testado e fail-closed.  
**Próximo investimentote técnico:** protótipo MuSig2 em Rust (`rust_bip340` crate) quando o build sandbox permitir, depois FFI.

Não há pressão de migrar até os oráculos de produção serem daemons com canal autenticado entre si.
