#!/usr/bin/env python3
"""Executa um swap BTC/BAIT local com Bitcoin Core regtest e BAIT P2P.

O teste inicia um bitcoind efêmero, cria um depósito BTC real em regtest,
observa-o via BitcoinCoreReader, cria uma liquidação BAIT nativa e valida a
propagação da transação por dois P2PNode locais. Nenhuma rede pública é usada.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
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
from native_processing.swap_executor import Deposit, OrderState, SwapExecutor
from native_processing.swap_protocol import sign_quote


class BitcoinRegtest:
    def __init__(self, bitcoind: Path, root: Path, rpc_user: str, rpc_password: str):
        self.bitcoind = bitcoind
        self.root = root
        self.rpc_user = rpc_user
        self.rpc_password = rpc_password
        self.datadir = root / "bitcoin-data"
        self.rpc_port = 18443
        self.process: subprocess.Popen[str] | None = None

    def cli(self, *args: str, wallet: str | None = None):
        command = [
            str(self.bitcoind.parent / "bitcoin-cli"),
            "-regtest",
            f"-datadir={self.datadir}",
            f"-rpcuser={self.rpc_user}",
            f"-rpcpassword={self.rpc_password}",
            f"-rpcport={self.rpc_port}",
        ]
        if wallet:
            command.append(f"-rpcwallet={wallet}")
        command.extend(args)
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        output = result.stdout.strip()
        if not output:
            return None
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return output

    def start(self) -> None:
        self.datadir.mkdir(parents=True, exist_ok=True)
        self.process = subprocess.Popen(
            [
                str(self.bitcoind), "-regtest=1", f"-datadir={self.datadir}",
                "-server=1", "-listen=0", "-txindex=1",
                "-fallbackfee=0.0001", "-discover=0",
                f"-rpcbind=127.0.0.1", f"-rpcport={self.rpc_port}",
                f"-rpcuser={self.rpc_user}", f"-rpcpassword={self.rpc_password}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        for _ in range(120):
            try:
                if self.cli("getblockchaininfo").get("chain") == "regtest":
                    return
            except (subprocess.CalledProcessError, OSError):
                pass
            time.sleep(0.25)
        raise RuntimeError("Bitcoin Core regtest did not become ready")

    def stop(self) -> None:
        try:
            self.cli("stop")
        except Exception:
            pass
        if self.process is not None:
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)


def mine_bait_funding(blockchain: Blockchain, bridge_key: SchnorrKeyPair) -> None:
    for _ in range(16):
        blockchain.mine_block("swap-bridge-funder", bridge_key.pub_bytes)
        if any(output.script_pubkey == bridge_key.pub_bytes for output in blockchain.utxo_set.values()):
            return
    raise RuntimeError("BAIT bridge funding block was not mined after 16 attempts")


async def run(args: argparse.Namespace) -> dict:
    root = Path(tempfile.mkdtemp(prefix="swap-btc-bait-"))
    bitcoin = BitcoinRegtest(Path(args.bitcoind).resolve(), root, "swaptest", "swaptest-password")
    executor = settlement = store = None
    node_a = node_b = None
    try:
        bitcoin.start()
        try:
            bitcoin.cli("createwallet", "swaptest")
        except subprocess.CalledProcessError:
            pass
        funding_address = bitcoin.cli("getnewaddress", wallet="swaptest")
        deposit_address = bitcoin.cli("getnewaddress", wallet="swaptest")
        bitcoin.cli("generatetoaddress", "110", funding_address)
        deposit_txid = bitcoin.cli("sendtoaddress", deposit_address, "0.001", wallet="swaptest")
        bitcoin.cli("generatetoaddress", "1", funding_address)

        reader = BitcoinCoreReader(
            f"http://127.0.0.1:{bitcoin.rpc_port}",
            bitcoin.rpc_user,
            bitcoin.rpc_password,
            network="regtest",
        )
        now = time.time()
        observed = None
        for _ in range(20):
            observed = reader.find_deposit("local-order", type("Intent", (), {
                "btc_deposit_address": deposit_address,
                "btc_sats": 100_000,
            })())
            if observed is not None:
                break
            time.sleep(0.25)
        if observed is None:
            raise AssertionError("BitcoinCoreReader did not observe the regtest deposit")

        blockchain = Blockchain()
        bridge_key = SchnorrKeyPair(private_key=12345)
        recipient_key = SchnorrKeyPair(private_key=67890)
        mine_bait_funding(blockchain, bridge_key)

        gossiped: list[dict] = []
        node_a = P2PNode("127.0.0.1", 0, node_id="bait-node-a", seeds=[])
        node_b = P2PNode("127.0.0.1", 0, node_id="bait-node-b", seeds=[])
        node_b.on_tx_received(lambda payload, _peer: gossiped.append(payload))
        await node_a.start()
        await node_b.start()
        port_a = node_a._server.sockets[0].getsockname()[1]
        if not await node_b.connect_to_peer("127.0.0.1", port_a):
            raise AssertionError("BAIT P2P node B could not connect to node A")
        await asyncio.sleep(0.15)

        engine = SwapEngine(str(root / "engine.sqlite"), quote_ttl_seconds=120)
        quote = engine.quote("buy_bait", 100_000, 2_000_000, now=now)
        intent = sign_quote(
            quote,
            "maker-local",
            Ed25519PrivateKey.generate(),
            "client-local",
            now=now + 1,
            btc_deposit_address=deposit_address,
            bait_recipient_pubkey=recipient_key.pub_bytes,
            network="regtest",
            # Fixture exclusively for regtest; production requires a verified oracle.
            parity_attestation={
                "version": 1, "pair": "BAIT/USDT", "bait_usdt_ppm": 1_000_000,
                "usdt_usd_ppm": 1_000_000, "usd_brl_ppm": 5_000_000,
                "observed_at": now, "expires_at": now + 60, "round_id": "regtest-round",
                "source_ids": ["regtest-a", "regtest-b", "regtest-c"], "quorum": 3,
                "proof_b64": "regtest-fixture",
            },
        )
        settlement = BaitBlockchainSettlement(
            blockchain,
            bridge_key,
            network="regtest",
            db_path=str(root / "settlement.sqlite"),
            p2p_node=node_a,
        )
        executor = SwapExecutor(
            str(root / "executor.sqlite"),
            reader,
            settlement,
            required_confirmations=1,
            enable_settlement=True,
            clock=time.time,
            parity_gate=ParityGate(lambda _attestation: True, clock=time.time),
        )
        if executor.admit(intent) != OrderState.INTENT_VALIDATED:
            raise AssertionError("signed intent was not admitted")
        first_state = executor.process(intent.order_id)
        if first_state != OrderState.BAIT_SUBMITTED:
            raise AssertionError(f"expected bait_submitted, got {first_state}")
        txid = executor.get_order(intent.order_id)["external_id"]
        await asyncio.sleep(0.25)
        if not gossiped or gossiped[0].get("tx_id") != txid:
            raise AssertionError("BAIT settlement was not gossiped to the second P2P node")

        final_state = first_state
        for _ in range(16):
            blockchain.mine_block("swap-validator", SchnorrKeyPair(private_key=99999).pub_bytes)
            final_state = executor.process(intent.order_id)
            if final_state == OrderState.SETTLED:
                break
        if final_state != OrderState.SETTLED:
            raise AssertionError(f"expected settled, got {final_state}")

        return {
            "bitcoin_core": bitcoin.cli("getnetworkinfo").get("subversion"),
            "bitcoin_chain": bitcoin.cli("getblockchaininfo").get("chain"),
            "bitcoin_deposit_txid": deposit_txid,
            "observed_deposit_txid": observed.txid,
            "observed_confirmations": observed.confirmations,
            "bait_settlement_txid": txid,
            "bait_state": final_state.value,
            "bait_height": blockchain.height,
            "p2p_connections": len(node_a._connections) + len(node_b._connections),
            "p2p_gossiped_transactions": len(gossiped),
            "datadir": str(root),
        }
    finally:
        if executor is not None:
            executor.close()
        if settlement is not None:
            settlement.close()
        if node_b is not None:
            await node_b.stop()
        if node_a is not None:
            await node_a.stop()
        if bitcoin.process is not None:
            bitcoin.stop()
        if not args.keep_data:
            shutil.rmtree(root, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bitcoind", required=True, help="Caminho para o binário bitcoind")
    parser.add_argument("--keep-data", action="store_true", help="Preserva datadir temporário para inspeção")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
