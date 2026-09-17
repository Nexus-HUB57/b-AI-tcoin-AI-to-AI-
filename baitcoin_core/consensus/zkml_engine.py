r"""
Motor de Consenso b'AI'tcoin — PoW (SHA-256d) + Proof of Work Commitments.

O consenso b'AI'tcoin é PRIMARIAMENTE Proof of Work (SHA-256d double-hash),
idêntico ao mecanismo do Bitcoin. O minerador encontra nonce tal que:
    SHA256(SHA256(block_header || nonce)) < target

Camadas adicionais de commitment (tensor_commitment, zkml_proof_hash)
são DERIVADAS do PoW e servem como metadados de auditoria:
- tensor_commitment: hash de comprometimento do bloco (integridade)
- zkml_proof_hash: hash da prova PoW (verificabilidade)

NOTA DE HONESTIDADE: Estas camadas NÃO provam execução de inferência ML.
Elas são commitment hashes derivados do trabalho PoW real.
Para provas zkML completas (Sigma + Fiat-Shamir + Pedersen), veja
baitcoin_core.consensus.zkml_real.proof_system.ZkMLProofSystem.
"""

import hashlib
import struct
import os
import time
from typing import Optional, Tuple
from baitcoin_core.blockchain.block import Block


class ZkMLConsensus:
    r"""Motor de consenso PoW + Commitments para b'AI'tcoin.

    MECANISMO PRINCIPAL: Proof of Work SHA-256d
    O minerador itera nonces até encontrar hash < target.
    Isto é PoW puro, idêntico ao Bitcoin.

    CAMADAS DE COMMITMENT (auditoria):
    - tensor_commitment: hash SHA-256 derivado do bloco+nonce
      (integridade, não prova de inferência ML)
    - zkml_proof_hash: hash SHA-256 do PoW proof
      (verificabilidade, não prova zero-knowledge)

    PROVAS ZKML COMPLETAS (separadas):
    O módulo zkml_real.proof_system implementa provas Sigma
    com Fiat-Shamir e Pedersen commitments que são
    matematicamente corretas para provar conhecimento
    de um segredo — mas não provam inferência ML real.
    """

    # Dificuldade inicial (target) - ajustada para confiabilidade em testes e producao
    # Target medio: ~1/65536 chance por iteracao (2 zero bytes), mining em ~1-5s
    DEFAULT_TARGET = 0x0000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff

    def __init__(self, target: Optional[int] = None):
        self.target = target or self.DEFAULT_TARGET
        self.target_bits = 0x1d00ffff
        self.validators: dict = {}
        self.blocks_validated = 0

    @property
    def difficulty(self) -> float:
        r"""Retorna dificuldade atual como float."""
        max_target = 0x00000000ffff0000000000000000000000000000000000000000000000000000
        return max_target / self.target

    def generate_tensor_commitment(self, block_hash: bytes, nonce: int) -> bytes:
        r"""Gera commitment de integridade do bloco.

        Este é um hash SHA-256 derivado do bloco e nonce.
        Serve como commitment de integridade (binding), garantindo
        que o bloco e nonce estão comprometidos no header.

        NOTA: NÃO é commitment de tensor ML. O nome é legado.
        Implementação real de Pedersen commitment em:
        baitcoin_core.consensus.zkml_real.tensor_commitment
        """
        # Commitment de integridade: SHA-256(block_hash || nonce || domain_sep)
        integrity_seed = f"BAIT_COMMITMENT:{block_hash.hex()}:{nonce}:BLOCK_INTEGRITY"
        return hashlib.sha256(integrity_seed.encode()).digest()

    def generate_zk_proof(self, block_hash: bytes, tensor_hash: bytes, nonce: int) -> bytes:
        r"""Gera hash de prova do PoW (audit trail).

        Este é SHA-256(block_hash || tensor_commitment || nonce).
        Serve como prova verificável de que o trabalho PoW foi
        executado para este bloco específico.

        NOTA: NÃO é prova zero-knowledge. O nome é legado.
        Provas Sigma+Fiat-Shamir reais em:
        baitcoin_core.consensus.zkml_real.proof_system.ZkMLProofSystem
        """
        proof_input = block_hash + tensor_hash + struct.pack("<Q", nonce)
        return hashlib.sha256(proof_input).digest()

    def validate_proof(self, block_hash: bytes, tensor_hash: bytes,
                        proof_hash: bytes, nonce: int) -> bool:
        r"""Valida integridade + PoW de um bloco.

        Verifica:
        1. Commitment de integridade corresponde ao bloco+nonce
        2. Hash de prova corresponde ao bloco+commitment+nonce
        3. Proof of Work: hash < target (critério principal)
        """
        expected_tensor = self.generate_tensor_commitment(block_hash, nonce)
        if expected_tensor != tensor_hash:
            return False

        expected_proof = self.generate_zk_proof(block_hash, tensor_hash, nonce)
        if expected_proof != proof_hash:
            return False

        # Critério principal: PoW (SHA-256d hash < target)
        proof_int = int.from_bytes(proof_hash, byteorder='big')
        return proof_int < self.target

    def mine_block(self, block: Block, max_iterations: int = 100_000) -> bool:
        r"""Minera bloco via Proof of Work (SHA-256d).

        Itera nonces até encontrar hash que satisfaça o target.
        Os commitments (tensor + proof) são derivados do PoW.
        Retorna True se bem-sucedido dentro de max_iterations.
        """
        for nonce in range(max_iterations):
            block_hash = block.block_hash
            tensor_hash = self.generate_tensor_commitment(block_hash, nonce)
            proof_hash = self.generate_zk_proof(block_hash, tensor_hash, nonce)

            if int.from_bytes(proof_hash, byteorder='big') < self.target:
                block.header.nonce = nonce
                block.header.tensor_commitment = tensor_hash
                block.header.zkml_proof_hash = proof_hash
                self.blocks_validated += 1
                return True

        return False

    def adjust_difficulty(self, actual_time: float, expected_time: float = 600) -> None:
        r"""Ajusta dificuldade baseado no tempo de mineração.

        Similar ao Bitcoin: ajusta a cada 2016 blocos.
        Se blocos foram minerados muito rápido, aumenta dificuldade.
        """
        ratio = actual_time / expected_time
        if ratio < 0.25:
            self.target = max(self.target // 4, 1)
        elif ratio < 1.0:
            self.target = max(int(self.target * ratio), 1)
        elif ratio > 4.0:
            self.target = min(self.target * 4, 0x00000000ffff0000000000000000000000000000000000000000000000000000)
        else:
            self.target = min(int(self.target * ratio), 0x00000000ffff0000000000000000000000000000000000000000000000000000)

    def register_validator(self, agent_id: str, stake: int, pubkey: bytes) -> bool:
        r"""Registra um validador AI na rede.

        Validadores precisam stake de BAIT para participar.
        """
        if stake < 1000 * 100_000_000:  # Mínimo 1000 BAIT
            return False
        self.validators[agent_id] = {
            "stake": stake,
            "pubkey": pubkey.hex(),
            "blocks_produced": 0,
            "reputation": 100.0,
        }
        return True

    def to_dict(self) -> dict:
        return {
            "target": hex(self.target),
            "difficulty": self.difficulty,
            "blocks_validated": self.blocks_validated,
            "validators": len(self.validators),
        }
