r"""
ZkML Verifier - Verificador de provas para o consenso.

Integra com o motor de consenso para:
- Validar provas antes de aceitar blocos
- Manter cache de provas já verificadas
- Pontuar validadores por provas corretas
- Detectar provas duplicadas ou inválidas
"""
import time
from typing import Dict, List, Optional, Set
from collections import OrderedDict
from baitcoin_core.consensus.zkml_real.proof_system import ZkMLProofSystem, ZkMLProof


class ProofCache:
    r"""Cache LRU de provas verificadas."""
    MAX_SIZE = 10_000

    def __init__(self):
        self._cache: OrderedDict[str, bool] = OrderedDict()

    def add(self, proof_id: str, valid: bool) -> None:
        if len(self._cache) >= self.MAX_SIZE:
            self._cache.popitem(last=False)
        self._cache[proof_id] = valid

    def get(self, proof_id: str) -> Optional[bool]:
        return self._cache.get(proof_id)

    def has(self, proof_id: str) -> bool:
        return proof_id in self._cache

    def clear(self) -> None:
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


class ZkMLVerifier:
    r"""Verificador zkML integrado ao consenso.

    Funcionalidades:
    - Verificação de provas com cache
    - Detecção de duplicatas (anti-replay)
    - Pontuação de validadores
    - Limpeza periódica de cache
    """
    MAX_AGE_SECONDS = 3600
    CLEANUP_INTERVAL = 300

    def __init__(self):
        self.proof_system = ZkMLProofSystem()
        self.cache = ProofCache()
        self._seen_proofs: Set[str] = set()
        self._validator_scores: Dict[str, float] = {}
        self._validator_proof_count: Dict[str, int] = {}
        self._last_cleanup = time.time()

    def verify(self, proof: ZkMLProof) -> dict:
        r"""Verifica uma prova zkML completa.

        Returns:
            Dict com 'valid', 'cached', 'duplicate', 'details'
        """
        # Anti-replay
        if proof.proof_id in self._seen_proofs:
            return {"valid": False, "cached": False, "duplicate": True}

        self._seen_proofs.add(proof.proof_id)

        # Cache check
        cached = self.cache.get(proof.proof_id)
        if cached is not None:
            return {"valid": cached, "cached": True, "duplicate": False}

        # Verify
        valid = self.proof_system.verify_proof(proof)
        self.cache.add(proof.proof_id, valid)

        # Update validator score
        if proof.prover_id:
            self._validator_proof_count[proof.prover_id] = \
                self._validator_proof_count.get(proof.prover_id, 0) + 1
            if valid:
                self._validator_scores[proof.prover_id] = \
                    self._validator_scores.get(proof.prover_id, 50.0) + 1.0
            else:
                self._validator_scores[proof.prover_id] = \
                    max(0, self._validator_scores.get(proof.prover_id, 50.0) - 5.0)

        return {"valid": valid, "cached": False, "duplicate": False}

    def verify_batch(self, proofs: List[ZkMLProof]) -> dict:
        r"""Verifica lote de provas."""
        results = {"total": len(proofs), "valid": 0, "invalid": 0, "duplicates": 0}
        for proof in proofs:
            r = self.verify(proof)
            if r["duplicate"]:
                results["duplicates"] += 1
            elif r["valid"]:
                results["valid"] += 1
            else:
                results["invalid"] += 1
        return results

    def get_validator_score(self, validator_id: str) -> float:
        return self._validator_scores.get(validator_id, 0.0)

    def get_top_validators(self, count: int = 10) -> List[dict]:
        sorted_vals = sorted(self._validator_scores.items(), key=lambda x: x[1], reverse=True)
        return [
            {"validator": vid, "score": score, "proofs": self._validator_proof_count.get(vid, 0)}
            for vid, score in sorted_vals[:count]
        ]

    def cleanup(self) -> int:
        r"""Limpa cache e proof IDs antigos."""
        if time.time() - self._last_cleanup < self.CLEANUP_INTERVAL:
            return 0
        self._last_cleanup = time.time()
        old_count = len(self._seen_proofs)
        self.cache.clear()
        if old_count > 100_000:
            self._seen_proofs.clear()
        return old_count

    def get_stats(self) -> dict:
        return {
            "cache_size": self.cache.size,
            "seen_proofs": len(self._seen_proofs),
            "validators_tracked": len(self._validator_scores),
            "proof_system": self.proof_system.get_stats(),
            "top_validators": self.get_top_validators(5),
        }
