# Esquemas de Assinatura Agregada Nativa — Exploração para BAIT Parity

**Data:** 2026-09-23  
**Contexto:** ParityGate atualmente usa multi-sig **não-agregada** (N assinaturas de 64 bytes concatenadas).  
Este documento avalia opções de agregação nativa para reduzir tamanho de proof e custo de verificação.

---

## 1. Estado atual (multi-sig simples)

```
proof = sig₀ || sig₁ || ... || sigₙ₋₁     # n × 64 bytes
verify: contar quantas sigs BIP-340 válidas ≥ quorum
```

| n (oráculos) | Tamanho proof | Verificações |
|--------------|---------------|--------------|
| 3            | 192 bytes     | 3            |
| 5            | 320 bytes     | 5            |
| 7            | 448 bytes     | 7            |

**Prós:** simples, fail-closed, já implementado em Python + Rust.  
**Contras:** proof cresce linearmente; não há compressão.

---

## 2. Opções de agregação

### 2.1 MuSig2 (BIP-327)

- Agrega n chaves e n nonces em **1 assinatura de 64 bytes**.
- Requer 2 rodadas de comunicação (nonce exchange → partial sigs).
- Segurança: proven no ROM + AGM (Bellare et al. / Nick et al.).
- Adequado quando os oráculos podem coordenar off-chain antes de publicar a attestation.

| n | Proof size | Rounds |
|---|------------|--------|
| qualquer | 64 bytes | 2 |

**Recomendação:** candidato principal se os oráculos forem online e sincronizados (ex.: daemon interno + 2 feeds externos).

### 2.2 FROST (Flexible Round-Optimized Schnorr Threshold)

- Threshold t-of-n com assinatura agregada de 64 bytes.
- Suporta dkg e rotação de shares.
- Ideal para “3-of-5 oráculos” sem revelar quais assinaram.
- Implementações: Zcash, secp256k1-zkp, frost-dalek.

**Recomendação:** quando houver requisito de threshold sem identificação dos signatários.

### 2.3 ROAST (Robust Asynchronous Schnorr Threshold)

- Camada de robustez sobre FROST para ambientes assíncronos / adversários.
- Mais complexo; overhead de coordenação maior.

### 2.4 Cross-input / Scriptless scripts (não aplicável direto)

- Útil em atomic swaps on-chain; não reduz o proof de attestation off-chain.

---

## 3. Comparativo

| Esquema | Proof size | Rounds | Threshold | Identifica signers | Maturidade |
|---------|------------|--------|-----------|--------------------|------------|
| Multi-sig atual | n×64 B | 0 (offline) | sim (contagem) | sim | produção |
| MuSig2 | 64 B | 2 | não (n-of-n) | não | alta |
| FROST | 64 B | 2+ | t-of-n | não | alta |
| ROAST | 64 B | async | t-of-n | não | média |

---

## 4. Recomendação para BAIT Parity v1 → v2

**v1 (agora):** manter multi-sig concatenada BIP-340 (já implementada e testada).  
**v2 (quando oráculos forem daemons sempre-on):** migrar para **MuSig2** se todos os oráculos participam (n-of-n), ou **FROST** se precisar de threshold t-of-n.

Critérios de migração:
1. Oráculos respondem em < 5 s com nonces.
2. Há canal autenticado entre eles (mTLS / signed messages).
3. Testes de regressão com o ParityGate atual passam com proof MuSig2/FROST.

---

## 5. Impacto no código atual

- `ParityAttestation.proof_b64` permanece opaco (Base64).
- `verify_proof` pode ser trocado por `verify_musig2` / `verify_frost` sem mudar a API do `ParityGate`.
- O digest da attestation (`bait.swap.parity.v1\n` + JSON) continua igual.

Nenhuma mudança de breaking API é necessária para adotar agregação depois.
