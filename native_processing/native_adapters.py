"""Adaptadores de full node para o executor de swap BTC/BAIT.

``BitcoinCoreReader`` usa apenas RPC de leitura do Bitcoin Core. Ele não
assina, não importa chaves e não faz broadcast. ``BaitBlockchainSettlement``
é um adaptador para a instância nativa ``Blockchain`` do repositório; a chave
privada de liquidação é recebida pelo processo hospedeiro e nunca é persistida
por este módulo.
"""
from __future__ import annotations

import base64
import asyncio
import hashlib
import inspect
import json
import logging
import re
import sqlite3
import threading
import time
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .swap_executor import Deposit, ExecutorError


logger = logging.getLogger(__name__)


class BitcoinRpcError(RuntimeError):
    pass


class BitcoinCoreReader:
    """Leitor watch-only baseado em ``scantxoutset`` do Bitcoin Core.

    O endereço e a rede são fornecidos pela intenção assinada. A rede também
    é conferida contra ``getblockchaininfo``; nunca é inferida da URL do RPC.
    """

    _CHAIN_NAMES = {"mainnet": "main", "testnet": "test", "regtest": "regtest", "signet": "signet"}

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        *,
        network: str,
        timeout: float = 10.0,
        max_scan_results: int = 1000,
    ):
        if not url or not username or not password or network not in self._CHAIN_NAMES:
            raise ValueError("Bitcoin Core RPC URL, credentials and explicit network are required")
        if timeout <= 0 or max_scan_results < 1:
            raise ValueError("invalid Bitcoin RPC reader configuration")
        self.url = url
        self.username = username
        self.password = password
        self.network = network
        self.timeout = timeout
        self.max_scan_results = max_scan_results
        self._rpc_id = 0
        self._lock = threading.Lock()
        self._network_checked = False

    def _rpc(self, method: str, params: list[Any]) -> Any:
        with self._lock:
            self._rpc_id += 1
            request_id = self._rpc_id
        body = json.dumps({"jsonrpc": "1.0", "id": request_id, "method": method, "params": params}).encode()
        token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        request = Request(
            self.url,
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Basic {token}"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode())
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise BitcoinRpcError(f"Bitcoin Core RPC {method} failed") from exc
        if payload.get("error") is not None:
            error = payload["error"]
            raise BitcoinRpcError(f"Bitcoin Core RPC {method} error: {error.get('code')} {error.get('message')}")
        return payload.get("result")

    def _ensure_network(self) -> None:
        if self._network_checked:
            return
        info = self._rpc("getblockchaininfo", [])
        if not isinstance(info, Mapping) or info.get("chain") != self._CHAIN_NAMES[self.network]:
            actual = info.get("chain") if isinstance(info, Mapping) else "unknown"
            raise BitcoinRpcError(f"Bitcoin network mismatch: expected {self.network}, got {actual}")
        self._network_checked = True

    @staticmethod
    def _sats_from_btc(value: Any) -> int:
        try:
            sats = (Decimal(str(value)) * Decimal(100_000_000)).to_integral_value()
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise BitcoinRpcError("invalid BTC amount from RPC") from exc
        if sats != Decimal(str(value)) * Decimal(100_000_000):
            raise BitcoinRpcError("BTC amount has more than 8 decimal places")
        return int(sats)

    def find_deposit(self, order_id: str, intent: Any) -> Optional[Deposit]:
        del order_id  # Correlation is encoded in the signed address/order policy.
        address = str(getattr(intent, "btc_deposit_address", ""))
        if not address:
            return None
        self._ensure_network()
        expected_sats = int(intent.btc_sats)
        result = self._rpc("scantxoutset", ["start", [f"addr({address})"]])
        if not isinstance(result, Mapping) or not result.get("success", False):
            return None
        unspent = result.get("unspents", [])
        if not isinstance(unspent, list) or len(unspent) > self.max_scan_results:
            raise BitcoinRpcError("unexpected or excessive scantxoutset result")
        chain_height = int(self._rpc("getblockcount", []))
        candidates: list[Deposit] = []
        for item in unspent:
            if not isinstance(item, Mapping):
                continue
            try:
                amount_sats = self._sats_from_btc(item["amount"])
                txid = str(item["txid"])
                vout = int(item["vout"])
                height = int(item["height"])
            except (KeyError, TypeError, ValueError, BitcoinRpcError):
                continue
            if not re.fullmatch(r"[0-9a-fA-F]{64}", txid) or vout < 0 or height < 0:
                continue
            raw_hex = self._rpc("getrawtransaction", [txid, False])
            if not isinstance(raw_hex, str) or len(raw_hex) % 2 or not re.fullmatch(r"[0-9a-fA-F]+", raw_hex):
                continue
            try:
                bytes.fromhex(raw_hex)
            except ValueError:
                continue
            verbose = self._rpc("getrawtransaction", [txid, True])
            tx_outputs = verbose.get("vout", []) if isinstance(verbose, Mapping) else []
            if not isinstance(verbose, Mapping) or str(verbose.get("txid", "")).lower() != txid.lower() or vout >= len(tx_outputs):
                continue
            output = tx_outputs[vout]
            script = output.get("scriptPubKey", {}) if isinstance(output, Mapping) else {}
            script_hex = str(script.get("hex", "")) if isinstance(script, Mapping) else ""
            if not script_hex or len(script_hex) % 2 or not re.fullmatch(r"[0-9a-fA-F]+", script_hex):
                continue
            txout = self._rpc("gettxout", [txid, vout, True])
            if not isinstance(txout, Mapping) or txout.get("bestblock") is None:
                continue
            confirmations = 0 if height <= 0 else max(0, chain_height - height + 1)
            if amount_sats == expected_sats:
                candidates.append(Deposit(
                    txid=txid,
                    btc_sats=amount_sats,
                    confirmations=confirmations,
                    recipient=address,
                    network=self.network,
                    block_hash=str(verbose.get("blockhash", "")),
                    vout=vout,
                    script_pubkey_hex=script_hex,
                    validated_hex=True,
                ))
        if not candidates:
            return None
        # Deterministic choice avoids changing the observed outpoint between runs.
        return sorted(candidates, key=lambda item: (item.txid, item.vout))[0]


class BaitBlockchainSettlement:
    """Liquidação nativa em uma ``Blockchain`` BAIT local/full node.

    O adaptador cria uma transação BAIT normal, assina com a chave fornecida
    pelo operador, coloca-a no mempool e reporta ``confirmed`` somente depois
    que um bloco da própria blockchain contiver a transação.
    """

    def __init__(
        self,
        blockchain: Any,
        bridge_key: Any,
        *,
        network: str = "mainnet",
        fee_rate: int = 10,
        db_path: str = ":memory:",
        p2p_node: Any = None,
    ):
        if network not in {"mainnet", "testnet", "regtest", "signet"} or fee_rate < 1:
            raise ValueError("invalid BAIT settlement configuration")
        if not hasattr(bridge_key, "pub_bytes") or not hasattr(bridge_key, "sign"):
            raise ValueError("bridge_key must be a SchnorrKeyPair-like signer")
        self.blockchain = blockchain
        self.bridge_key = bridge_key
        self.network = network
        self.fee_rate = fee_rate
        self.p2p_node = p2p_node
        self.db = sqlite3.connect(db_path, timeout=30, isolation_level=None, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS swap_settlements ("
            "order_id TEXT PRIMARY KEY, txid TEXT NOT NULL UNIQUE, deposit_txid TEXT NOT NULL, created_at REAL NOT NULL)"
        )
        self._lock = threading.RLock()

    def close(self) -> None:
        self.db.close()

    @staticmethod
    def _recipient_pubkey(intent: Any) -> bytes:
        encoded = str(getattr(intent, "bait_recipient_pubkey_b64", ""))
        if not encoded:
            raise ExecutorError("signed intent has no BAIT recipient public key")
        try:
            pubkey = base64.b64decode(encoded.encode("ascii"), validate=True)
        except Exception as exc:
            raise ExecutorError("invalid BAIT recipient public key") from exc
        if len(pubkey) != 32:
            raise ExecutorError("invalid BAIT recipient public key length")
        return pubkey

    def _find_transaction(self, txid: str) -> Optional[Any]:
        for block in getattr(self.blockchain, "chain", []):
            for tx in getattr(block, "transactions", []):
                if tx.tx_id.hex() == txid:
                    return tx
        for entry in getattr(getattr(self.blockchain, "fee_market", None), "entries", []):
            if entry.tx.tx_id.hex() == txid:
                return entry.tx
        return None

    def submit(self, intent: Any, deposit: Deposit) -> str:
        order_id = str(intent.order_id)
        with self._lock:
            prior = self.db.execute("SELECT txid FROM swap_settlements WHERE order_id=?", (order_id,)).fetchone()
            if prior:
                return str(prior[0])

            recipient = self._recipient_pubkey(intent)
            required = int(intent.bait_units)
            if required <= 0:
                raise ExecutorError("invalid BAIT settlement amount")
            candidates = [
                (key, output) for key, output in self.blockchain.utxo_set.items()
                if output.script_pubkey == self.bridge_key.pub_bytes and output.amount_sats > required
            ]
            if not candidates:
                raise ExecutorError("bridge wallet has no BAIT UTXO for settlement")
            input_key, input_output = sorted(candidates, key=lambda item: (item[1].amount_sats, item[0]))[0]
            prev_txid, prev_index = input_key.rsplit(":", 1)

            from baitcoin_core.blockchain.block import Transaction, TransactionInput, TransactionOutput
            tx = Transaction(
                tx_type="transfer",
                inputs=[TransactionInput(prev_tx_id=bytes.fromhex(prev_txid), prev_output_index=int(prev_index))],
                outputs=[TransactionOutput(amount_sats=required, script_pubkey=recipient)],
                nonce=int.from_bytes(hashlib.sha256(order_id.encode()).digest()[:8], "big"),
                agent_id="swap-bridge",
                gas_limit=100_000,
                gas_price=self.fee_rate,
                payload=json.dumps({
                    "protocol": "bait.swap.settlement.v1",
                    "order_id": order_id,
                    "btc_txid": deposit.txid,
                    "btc_vout": deposit.vout,
                    "network": self.network,
                    "parity_digest": hashlib.sha256(
                        str(getattr(intent, "parity_attestation_json", "")).encode("utf-8")
                    ).hexdigest(),
                }, sort_keys=True, separators=(",", ":")).encode(),
            )
            # Keep the bridge change output deterministic and pay the fee from change.
            tx_size = 100 + len(tx.inputs) * 148 + 2 * 34 + len(tx.payload)
            fee = max(self.fee_rate * tx_size, 1)
            if input_output.amount_sats <= required + fee:
                raise ExecutorError("bridge wallet UTXO is insufficient for amount plus fee")
            tx.outputs.append(TransactionOutput(
                amount_sats=input_output.amount_sats - required - fee,
                script_pubkey=self.bridge_key.pub_bytes,
            ))
            tx.signature = self.bridge_key.sign(tx.tx_id).raw
            if not self.blockchain.add_transaction(tx, fee_rate=self.fee_rate, validate=True):
                raise ExecutorError("BAIT full node rejected settlement transaction")
            txid = tx.tx_id.hex()
            self._broadcast(tx)
            self.db.execute(
                "INSERT INTO swap_settlements(order_id,txid,deposit_txid,created_at) VALUES(?,?,?,?)",
                (order_id, txid, deposit.txid, time.time()),
            )
            return txid

    def _broadcast(self, tx: Any) -> None:
        """Gossip da transação, sem tornar a confirmação dependente do P2P."""
        if self.p2p_node is None or not hasattr(self.p2p_node, "broadcast_tx"):
            return
        try:
            result = self.p2p_node.broadcast_tx(tx.to_dict())
            if inspect.isawaitable(result):
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    asyncio.run(result)
                else:
                    loop.create_task(result)
        except Exception:
            logger.warning("BAIT settlement entered local mempool but P2P gossip failed", exc_info=True)

    def status(self, external_id: str) -> str:
        tx = self._find_transaction(external_id)
        if tx is None:
            return "unknown"
        for block in getattr(self.blockchain, "chain", []):
            if any(item.tx_id.hex() == external_id for item in getattr(block, "transactions", [])):
                return "confirmed"
        return "pending"
