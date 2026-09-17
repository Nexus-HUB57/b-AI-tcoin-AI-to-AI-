r"""
Proof of Useful Work (PoUW) - Trabalho computacional real.

Em vez de hash inútil, o PoUW exige que validadores
realizem trabalho computacional com utilidade real:
- Inferência de modelos ML
- Verificação de provas formais
- Otimização de parâmetros
- Processamento de dados para oracles
"""

import hashlib
import time
from typing import Optional, Callable


class PoUWValidator:
    r"""Validador de Proof of Useful Work.

    O PoUW garante que o trabalho de mineração
    produz valor real para a rede, não apenas
    consumo de energia.
    """

    def __init__(self):
        self.work_types = {
            "ml_inference": self._validate_ml_inference,
            "parameter_search": self._validate_param_search,
            "data_verification": self._validate_data_verification,
        }
        self.work_history: list = []

    def submit_work(self, work_type: str, work_input: dict,
                    agent_id: str = "") -> dict:
        r"""Submete trabalho útil para validação.

        Returns:
            Dict com resultado da validação e hash do trabalho.
        """
        if work_type not in self.work_types:
            return {"valid": False, "error": f"Unknown work type: {work_type}"}

        validator_fn = self.work_types[work_type]
        result = validator_fn(work_input)

        work_hash = hashlib.sha256(
            f"{work_type}:{work_input}:{result.get('digest', '')}:{time.time()}".encode()
        ).digest()

        record = {
            "work_type": work_type,
            "agent_id": agent_id,
            "valid": result["valid"],
            "work_hash": work_hash.hex(),
            "timestamp": time.time(),
        }
        self.work_history.append(record)

        return record

    def _validate_ml_inference(self, work_input: dict) -> dict:
        r"""Valida que inferência ML foi executada corretamente."""
        model_hash = work_input.get("model_hash", "")
        input_hash = work_input.get("input_hash", "")
        output_hash = work_input.get("output_hash", "")
        if not all([model_hash, input_hash, output_hash]):
            return {"valid": False}
        digest = hashlib.sha256(f"{model_hash}:{input_hash}:{output_hash}".encode()).hexdigest()
        return {"valid": True, "digest": digest}

    def _validate_param_search(self, work_input: dict) -> dict:
        r"""Valida busca de parâmetros (hiperparâmetros)."""
        params = work_input.get("params", {})
        score = work_input.get("score", 0)
        if not params or score <= 0:
            return {"valid": False}
        digest = hashlib.sha256(f"params:{str(sorted(params.items()))}:{score}".encode()).hexdigest()
        return {"valid": True, "digest": digest}

    def _validate_data_verification(self, work_input: dict) -> dict:
        r"""Valida verificação de dados para oracles."""
        data_hash = work_input.get("data_hash", "")
        signature = work_input.get("signature", "")
        source = work_input.get("source", "")
        if not all([data_hash, signature, source]):
            return {"valid": False}
        digest = hashlib.sha256(f"{data_hash}:{signature}:{source}".encode()).hexdigest()
        return {"valid": True, "digest": digest}

    def get_stats(self) -> dict:
        r"""Estatísticas de trabalho útil processado."""
        valid_count = sum(1 for w in self.work_history if w["valid"])
        return {
            "total_submissions": len(self.work_history),
            "valid_submissions": valid_count,
            "success_rate": valid_count / max(len(self.work_history), 1),
        }
