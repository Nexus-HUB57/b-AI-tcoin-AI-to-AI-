#!/usr/bin/env python3
"""E2E local, sem fundos reais: custódia regtest de exatamente 1 BTC + settlement BAIT."""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.cryptography.schnorr import SchnorrKeyPair
from baitcoin_core.network.p2p_real.node import P2PNode
from native_processing.native_adapters import BaitBlockchainSettlement, BitcoinCoreReader
from native_processing.parity_gate import ParityGate
from native_processing.swap_engine import SwapEngine
from native_processing.swap_executor import OrderState, SwapExecutor
from native_processing.swap_protocol import sign_quote
from scripts.run_local_swap_full_nodes import BitcoinRegtest, mine_bait_funding


class CustodyLedger:
    def __init__(self, path: Path):
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE custody (txid TEXT NOT NULL, vout INTEGER NOT NULL, sats INTEGER NOT NULL, state TEXT NOT NULL, PRIMARY KEY(txid,vout))")

    def accept(self, txid: str, vout: int, sats: int) -> None:
        with self.db:
            self.db.execute("INSERT INTO custody VALUES(?,?,?,?) ON CONFLICT(txid,vout) DO UPDATE SET state=excluded.state", (txid, vout, sats, "accepted"))

    def mark_settled(self, txid: str, vout: int) -> None:
        with self.db:
            self.db.execute("UPDATE custody SET state='settled' WHERE txid=? AND vout=?", (txid, vout))

    def balance(self) -> int:
        return int(self.db.execute("SELECT COALESCE(SUM(sats),0) FROM custody WHERE state IN ('accepted','settled')").fetchone()[0])

    def close(self) -> None:
        self.db.close()


async def run(args: argparse.Namespace) -> dict:
    root = Path(tempfile.mkdtemp(prefix="swap-custody-1btc-regtest-"))
    bitcoin = BitcoinRegtest(Path(args.bitcoind).resolve(), root, "swapcustody", "ephemeral-pass")
    ledger = CustodyLedger(root / "custody.sqlite")
    executor = settlement = node_a = node_b = None
    try:
        bitcoin.start()
        assert bitcoin.cli("getblockchaininfo").get("chain") == "regtest"
        for wallet in ("miner", "custody"):
            bitcoin.cli("createwallet", wallet)
        miner_address = bitcoin.cli("getnewaddress", wallet="miner")
        custody_address = bitcoin.cli("getnewaddress", wallet="custody")
        bitcoin.cli("generatetoaddress", "110", miner_address)
        deposit_txid = bitcoin.cli("sendtoaddress", custody_address, "1.00000000", wallet="miner")
        bitcoin.cli("generatetoaddress", "1", miner_address)

        reader = BitcoinCoreReader(f"http://127.0.0.1:{bitcoin.rpc_port}", bitcoin.rpc_user, bitcoin.rpc_password, network="regtest")
        class IntentView:
            btc_deposit_address = custody_address
            btc_sats = 100_000_000
        observed = None
        for _ in range(20):
            observed = reader.find_deposit("custody-1btc-order", IntentView())
            if observed:
                break
            await asyncio.sleep(0.25)
        if observed is None or observed.btc_sats != 100_000_000:
            raise AssertionError("exact 1 BTC custody UTXO was not observed")
        ledger.accept(observed.txid, observed.vout, observed.btc_sats)

        blockchain = Blockchain()
        bridge_key = SchnorrKeyPair(private_key=12345)
        recipient_key = SchnorrKeyPair(private_key=67890)
        mine_bait_funding(blockchain, bridge_key)
        gossiped = []
        node_a = P2PNode("127.0.0.1", 0, node_id="custody-node-a", seeds=[])
        node_b = P2PNode("127.0.0.1", 0, node_id="custody-node-b", seeds=[])
        node_b.on_tx_received(lambda payload, _peer: gossiped.append(payload))
        await node_a.start(); await node_b.start()
        port_a = node_a._server.sockets[0].getsockname()[1]
        if not await node_b.connect_to_peer("127.0.0.1", port_a):
            raise AssertionError("custody P2P connection failed")

        now = time.time()
        engine = SwapEngine(str(root / "engine.sqlite"), quote_ttl_seconds=120)
        quote = engine.quote("buy_bait", 100_000_000, 2_000_000, now=now)
        intent = sign_quote(
            quote, "custody-maker", Ed25519PrivateKey.generate(), "custody-1btc-order", now=now + 1,
            btc_deposit_address=custody_address, bait_recipient_pubkey=recipient_key.pub_bytes,
            network="regtest", parity_attestation={
                "version": 1, "pair": "BAIT/USDT", "bait_usdt_ppm": 1_000_000,
                "usdt_usd_ppm": 1_000_000, "usd_brl_ppm": 5_000_000,
                "observed_at": now, "expires_at": now + 60, "round_id": "regtest-custody-round",
                "source_ids": ["regtest-a", "regtest-b", "regtest-c"], "quorum": 3,
                "proof_b64": "regtest-fixture",
            },
        )
        settlement = BaitBlockchainSettlement(blockchain, bridge_key, network="regtest", db_path=str(root / "settlement.sqlite"), p2p_node=node_a)
        executor = SwapExecutor(str(root / "executor.sqlite"), reader, settlement, required_confirmations=1, enable_settlement=True, clock=time.time, parity_gate=ParityGate(lambda _: True, clock=time.time))
        if executor.admit(intent) != OrderState.INTENT_VALIDATED:
            raise AssertionError("1 BTC custody intent not admitted")
        state = executor.process(intent.order_id)
        if state != OrderState.BAIT_SUBMITTED:
            raise AssertionError(f"expected BAIT_SUBMITTED, got {state}")
        txid = executor.get_order(intent.order_id)["external_id"]
        await asyncio.sleep(0.1)
        for _ in range(16):
            blockchain.mine_block("custody-validator", SchnorrKeyPair(private_key=99999).pub_bytes)
            state = executor.process(intent.order_id)
            if state == OrderState.SETTLED:
                break
        if state != OrderState.SETTLED:
            raise AssertionError(f"expected SETTLED, got {state}")
        ledger.mark_settled(observed.txid, observed.vout)
        custody_utxos = bitcoin.cli("listunspent", "1", "9999999", json.dumps([custody_address]), wallet="custody")
        exact = [u for u in custody_utxos if u.get("txid") == observed.txid and int(u.get("vout", -1)) == observed.vout and round(float(u.get("amount", 0)) * 100_000_000) == 100_000_000]
        if len(exact) != 1 or ledger.balance() != 100_000_000:
            raise AssertionError("custody balance invariant failed")
        return {"network": "regtest", "deposit_txid": observed.txid, "deposit_vout": observed.vout, "deposit_sats": observed.btc_sats, "custody_balance_sats": ledger.balance(), "bait_state": state.value, "bait_txid": txid, "p2p_gossiped_transactions": len(gossiped), "real_btc_used": False}
    finally:
        if executor is not None: executor.close()
        if settlement is not None: settlement.close()
        if node_a is not None: await node_a.stop()
        if node_b is not None: await node_b.stop()
        ledger.close()
        bitcoin.stop()
        if not args.keep_data: shutil.rmtree(root, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bitcoind", required=True)
    parser.add_argument("--keep-data", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args)), sort_keys=True))


if __name__ == "__main__":
    main()
