r"""
Construtor de Transações - Cria transações AI-to-AI.

Monta transações com múltiplos inputs/outputs,
calcula fees e prepara para assinatura.
"""

import time
from typing import List, Optional, Tuple
from baitcoin_core.blockchain.block import Transaction, TransactionInput, TransactionOutput


class TransactionBuilder:
    r"""Builder para transações b'AI'tcoin.

    Facilita a construção de transações complexas:
    - Pagamentos simples AI-to-AI
    - Pagamentos em lote
    - Transações com payload de dados
    """

    DEFAULT_GAS_PRICE = 1  # sat por byte
    MIN_FEE_SATS = 100

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._inputs: List[TransactionInput] = []
        self._outputs: List[TransactionOutput] = []
        self._gas_limit = 0
        self._gas_price = self.DEFAULT_GAS_PRICE
        self._payload = b""
        self._nonce = 0

    def add_input(self, prev_tx_id: bytes, prev_output_index: int,
                  script_sig: bytes = b"") -> 'TransactionBuilder':
        r"""Adiciona input (referência a UTXO)."""
        self._inputs.append(TransactionInput(
            prev_tx_id=prev_tx_id,
            prev_output_index=prev_output_index,
            script_sig=script_sig,
        ))
        return self

    def add_output(self, amount_sats: int, script_pubkey: bytes) -> 'TransactionBuilder':
        r"""Adiciona output (destino + valor)."""
        self._outputs.append(TransactionOutput(
            amount_sats=amount_sats,
            script_pubkey=script_pubkey,
        ))
        return self

    def with_gas(self, gas_limit: int, gas_price: int) -> 'TransactionBuilder':
        r"""Define limit e preço de gas."""
        self._gas_limit = gas_limit
        self._gas_price = gas_price
        return self

    def with_payload(self, data: bytes) -> 'TransactionBuilder':
        r"""Adiciona payload de dados (memo/metadata)."""
        self._payload = data
        return self

    def with_nonce(self, nonce: int) -> 'TransactionBuilder':
        r"""Define nonce para replay protection."""
        self._nonce = nonce
        return self

    def build(self) -> Transaction:
        r"""Constrói a transação final."""
        return Transaction(
            tx_type="transfer",
            inputs=self._inputs,
            outputs=self._outputs,
            nonce=self._nonce,
            timestamp=time.time(),
            agent_id=self.agent_id,
            gas_limit=self._gas_limit,
            gas_price=self._gas_price,
            payload=self._payload,
        )

    def build_payment(self, from_pubkey: bytes, to_pubkey: bytes,
                       amount_sats: int, utxo_tx_id: bytes,
                       utxo_index: int, change_amount: int) -> Transaction:
        r"""Cria transação de pagamento completa (conveniência)."""
        tx = (self
              .add_input(utxo_tx_id, utxo_index)
              .add_output(amount_sats, to_pubkey))
        if change_amount > 0:
            tx = tx.add_output(change_amount, from_pubkey)
        return tx.build()
