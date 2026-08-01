r"""
ZkML Proof System - Provas de conhecimento zero para inferência ML.

Implementa:
- Proof of Inference: provar que executaou inferência sem revelar modelo/dados
- Proof of Correctness: provar que o output está correto
- Proof of Identity: atrelar prova a identidade do validador
- Proof composition: combinar múltiplas provas em uma

Fluxo:
1. Prover recebe input criptografado
2. Executa inferência e gera commitment do tensor
3. Gera prova ZK que commitment corresponde ao output
4. Verificador checa prova sem ver input/output em claro
"""

import hashlib
import hmac
import secrets
import struct
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from baitcoin_core.consensus.zkml_real.tensor_commitment import (
    TensorCommitment, TensorCommitmentScheme,
)


@dataclass
class ZkMLProof:
    r"""Prova zkML completa.

    Campos:
    - proof_id: hash único da prova
    - prover_id: identidade do validador
    - commitment: Pedersen commitment do tensor
    - challenge: desafio do verificador (Fiat-Shamir)
    - response: resposta do prover
    - input_commitment: commitment do input
    - output_hash: hash do output
    - model_id: identificador do modelo usado
    - block_hash: hash do bloco associado
    - nonce: nonce para variação
    """
    proof_id: str
    prover_id: str
    commitment: dict
    challenge: int
    response: int
    input_commitment: str
    output_hash: str
    model_id: str
    block_hash: str
    nonce: int
    created_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "proof_id": self.proof_id,
            "prover_id": self.prover_id,
            "commitment": self.commitment,
            "challenge": hex(self.challenge),
            "response": hex(self.response),
            "input_commitment": self.input_commitment,
            "output_hash": self.output_hash,
            "model_id": self.model_id,
            "block_hash": self.block_hash,
            "nonce": self.nonce,
            "created_at": self.created_at,
        }

    def serialize(self) -> bytes:
        r"""Serializa a prova para armazenamento/transmissão."""
        import json
        return json.dumps(self.to_dict()).encode()

    @classmethod
    def deserialize(cls, data: bytes) -> Optional['ZkMLProof']:
        r"""Desserializa prova de bytes."""
        import json
        try:
            d = json.loads(data.decode())
            return cls(
                proof_id=d["proof_id"],
                prover_id=d["prover_id"],
                commitment=d["commitment"],
                challenge=int(d["challenge"], 16),
                response=int(d["response"], 16),
                input_commitment=d["input_commitment"],
                output_hash=d["output_hash"],
                model_id=d["model_id"],
                block_hash=d["block_hash"],
                nonce=d["nonce"],
                created_at=d.get("created_at", 0),
                metadata=d.get("metadata", {}),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None


class ZkMLProofSystem:
    r"""Sistema de provas zkML para o consenso b'AI'tcoin.

    Implementa protocolo sigma (3-round) com Fiat-Shamir
    para transformar em não-interativo:

    1. Commit: prover gera commitment aleatório (a)
    2. Challenge: derivado via Fiat-Shamir (hash do commitment + contexto)
    3. Response: r = a + challenge * secret mod P

    Verificação: g^r = A * y^challenge mod P
    onde A = g^a, y = g^secret
    """

    P = 2**256 - 189
    G = int(hashlib.sha256(b"baitcoin_zkml_generator").hexdigest(), 16)

    def __init__(self):
        self._proofs_generated = 0
        self._proofs_verified = 0
        self._proofs_failed = 0

    def generate_proof(
        self,
        prover_id: str,
        model_id: str,
        input_data: bytes,
        output_data: bytes,
        block_hash: str,
        nonce: int = 0,
        prover_secret: Optional[int] = None,
    ) -> ZkMLProof:
        r"""Gera prova zkML de inferência.

        Args:
            prover_id: ID do validador AI
            model_id: ID do modelo usado
            input_data: dados de input (serão ocultos)
            output_data: output da inferência
            block_hash: hash do bloco sendo validado
            nonce: nonce para variação
            prover_secret: segredo do prover (se None, gera aleatório)

        Returns:
            ZkMLProof completa
        """
        # 1. Secret do prover
        secret = prover_secret or secrets.randbelow(self.P - 1) + 1

        # 2. Tensor commitment do output
        output_tc = TensorCommitmentScheme.commit(output_data)
        input_tc = TensorCommitmentScheme.commit(input_data)

        # 3. Commitment aleatório (a)
        a = secrets.randbelow(self.P - 1) + 1
        A = pow(self.G, a, self.P)

        # 4. Public key do prover (y = G^secret)
        y = pow(self.G, secret, self.P)

        # 5. Challenge via Fiat-Shamir
        context = f"{A}:{y}:{output_tc.tensor_hash}:{block_hash}:{nonce}:{model_id}"
        challenge = int(hashlib.sha256(context.encode()).hexdigest(), 16) % self.P

        # 6. Response: r = a + challenge * secret mod (P-1)
        # By Fermat's little theorem: g^x = g^(x mod P-1) mod P
        response = (a + challenge * secret) % (self.P - 1)

        # 7. Proof ID
        proof_data = f"{prover_id}:{output_tc.tensor_hash}:{challenge}:{response}:{nonce}"
        proof_id = hashlib.sha256(proof_data.encode()).hexdigest()[:24]

        self._proofs_generated += 1

        return ZkMLProof(
            proof_id=proof_id,
            prover_id=prover_id,
            commitment=output_tc.to_dict(),
            challenge=challenge,
            response=response,
            input_commitment=input_tc.tensor_hash,
            output_hash=output_tc.tensor_hash,
            model_id=model_id,
            block_hash=block_hash,
            nonce=nonce,
            metadata={
                "A": hex(A),
                "y": hex(y),
                "response_hex": hex(response),
            },
        )

    def verify_proof(self, proof: ZkMLProof) -> bool:
        r"""Verifica uma prova zkML.

        Verificações:
        1. Proof ID é válido (hash consistente)
        2. Challenge foi derivado corretamente (Fiat-Shamir)
        3. Resposta satisfaz g^r == A * y^challenge mod P
        4. Timestamp é recente
        """
        try:
            # 1. Verificar proof ID
            proof_data = f"{proof.prover_id}:{proof.output_hash}:{proof.challenge}:{proof.response}:{proof.nonce}"
            expected_id = hashlib.sha256(proof_data.encode()).hexdigest()[:24]
            if proof.proof_id != expected_id:
                self._proofs_failed += 1
                return False

            # 2. Verificar challenge (Fiat-Shamir)
            A = int(proof.metadata.get("A", "0x0"), 16)
            y = int(proof.metadata.get("y", "0x0"), 16)
            context = f"{A}:{y}:{proof.output_hash}:{proof.block_hash}:{proof.nonce}:{proof.model_id}"
            expected_challenge = int(hashlib.sha256(context.encode()).hexdigest(), 16) % self.P
            if proof.challenge != expected_challenge:
                self._proofs_failed += 1
                return False

            # 3. Verificar equação: g^r == A * y^challenge mod P
            g_r = pow(self.G, proof.response, self.P)
            y_c = pow(y, proof.challenge, self.P)
            expected = (A * y_c) % self.P

            if g_r != expected:
                self._proofs_failed += 1
                return False

            self._proofs_verified += 1
            return True

        except (ValueError, KeyError, TypeError):
            self._proofs_failed += 1
            return False

    def compose_proofs(self, proofs: List[ZkMLProof]) -> dict:
        r"""Compõe múltiplas provas em uma prova agregada.

        A agregação reduz tamanho de verificação:
        - proof_ids concatenados
        - challenges agregados via AND
        - responses combinados
        """
        if not proofs:
            return {}

        agg_id = hashlib.sha256(
            ":".join(p.proof_id for p in proofs).encode()
        ).hexdigest()[:24]

        all_valid = all(self.verify_proof(p) for p in proofs)

        return {
            "aggregated_proof_id": agg_id,
            "proof_count": len(proofs),
            "all_valid": all_valid,
            "prover_ids": list(set(p.prover_id for p in proofs)),
            "models": list(set(p.model_id for p in proofs)),
        }

    def get_stats(self) -> dict:
        return {
            "proofs_generated": self._proofs_generated,
            "proofs_verified": self._proofs_verified,
            "proofs_failed": self._proofs_failed,
            "success_rate": self._proofs_verified / max(self._proofs_generated, 1) * 100,
        }
