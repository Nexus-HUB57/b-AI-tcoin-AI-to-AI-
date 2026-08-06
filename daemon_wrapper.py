#!/usr/bin/env python3
"""
b'AI'tcoin Daemon Wrapper v3 - Fully synchronous, ThreadingHTTPServer.
Separates API server from mining loop completely.
"""
import os
import sys
import json
import signal
import threading
import socketserver
import time
import logging
import traceback

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main():
    port = int(os.environ.get('BAIT_DAEMON_PORT', '18445'))
    mine_interval = float(os.environ.get('BAIT_MINE_INTERVAL', '3.0'))

    # Import and initialize everything
    from main_daemon import BAITDaemon
    from baitcoin_api.server import BaitcoinAPIHandler, init_whitelabel
    from baitcoin_explorer.indices import BlockchAInIndex
    from baitcoin_explorer.search import UniversalSearch
    from baitcoin_explorer.analytics import OnChainAnalytics
    from baitcoin_explorer.docs import DeveloperDocs
    from baitcoin_explorer.rate_limiter import RateLimiter
    from http.server import HTTPServer

    # Initialize daemon (all 14 modules)
    daemon = BAITDaemon(api_port=port)
    daemon.initialize()
    daemon._register_genesis_agents()

    # Initialize whitelabel engine
    init_whitelabel()

    # Inject ALL dependencies (same as run_daemon + create_app combined)
    BaitcoinAPIHandler.blockchain = daemon.blockchain
    BaitcoinAPIHandler.token = daemon.token
    BaitcoinAPIHandler.faucet = daemon.faucet
    BaitcoinAPIHandler.staking_pool = daemon.staking_pool
    BaitcoinAPIHandler.agent_registry = daemon.agent_registry
    BaitcoinAPIHandler.marketplace = daemon.marketplace
    BaitcoinAPIHandler.oracle = daemon.oracle
    BaitcoinAPIHandler.zkml_verifier = daemon.zkml_verifier
    BaitcoinAPIHandler.p2p_node = daemon.p2p_network
    BaitcoinAPIHandler.platform_faucets = None
    BaitcoinAPIHandler.obscura_bridge = daemon.obscura_bridge
    BaitcoinAPIHandler.explorer_index = daemon.explorer_index
    BaitcoinAPIHandler.lending_engine = daemon.lending_engine
    BaitcoinAPIHandler.explorer_search = UniversalSearch(daemon.explorer_index)
    BaitcoinAPIHandler.explorer_analytics = OnChainAnalytics()
    BaitcoinAPIHandler.explorer_docs = DeveloperDocs()
    BaitcoinAPIHandler.rate_limiter = RateLimiter()

    # Override _get_status with daemon's enhanced version
    _daemon = daemon
    def _enhanced_status(self):
        self._send_json(_daemon.get_status())
    BaitcoinAPIHandler._get_status = _enhanced_status

    # Patch handler to never crash the server
    _orig_handle = BaitcoinAPIHandler.handle_one_request
    def _safe_handle(self):
        try:
            _orig_handle(self)
        except SystemExit:
            raise
        except Exception as e:
            logger.error(f"Handler error: {e}")
            try:
                self.send_error(500, str(e)[:200])
            except Exception:
                pass
    BaitcoinAPIHandler.handle_one_request = _safe_handle

    # Create ThreadingHTTPServer manually
    class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    httpd = ThreadedHTTPServer(('127.0.0.1', port), BaitcoinAPIHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    logger.info(f"ThreadingHTTPServer running on port {port}")

    # Banner
    status = daemon.get_status()
    print()
    print("=" * 70)
    print(f"  b'AI'tcoin Daemon v1.2 — AI-to-AI Autonomous Cryptocurrency")
    print("=" * 70)
    print(f"  Blockchain Height: {status['chain_height']}")
    print(f"  Chain Valid: {status['chain_valid']}")
    print(f"  Blocks Immutable: True (SHA-256d + prev_hash chain)")
    print(f"  Persistent Memory: WAL + Snapshots at {status['data_path']}")
    print(f"  Agents Registered: {status['agents_registered']}")
    print(f"  AI Store: {status['marketplace']['active']} active services")
    print(f"  Staking APY: {status['staking']['apy']:.1f}%")
    or_prices = status.get('oracle', {}).get('prices', {})
    for sym, price in or_prices.items():
        if price is not None and price > 0:
            print(f"    {sym}: ${price:,.2f}")
    print(f"  API Server: http://127.0.0.1:{port}")
    print("=" * 70)
    print()
    sys.stdout.flush()

    # --- Mineração Competitiva Real (PoW SHA-256d) ---
    # Múltiplos miners competem pelo mesmo bloco; o primeiro que
    # encontra nonce válido vence. Sem round-robin, sem determinismo.
    MINER_AGENTS = [
        "chimera7", "chimera7_oracle", "chimera7_defi",
        "bait_network_miner_1", "bait_network_miner_2",
    ]
    block_count = 0
    last_oracle_seed = time.time()
    stop = False
    competition_stats = {a: {"blocks_won": 0, "total_hashes": 0} for a in MINER_AGENTS}
    import random as _rng
    _rng.seed(int(time.time()))

    def signal_handler(sig, frame):
        nonlocal stop
        logger.info("Shutdown signal received")
        stop = True
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    while not stop:
        # Selecionar 2-3 miners aleatórios para competir neste bloco
        num_competitors = min(_rng.randint(2, len(MINER_AGENTS)), len(MINER_AGENTS))
        competitors = _rng.sample(MINER_AGENTS, num_competitors)
        winner = None
        winner_info = None
        lock = threading.Lock()

        def _try_mine(agent_id: str):
            nonlocal winner, winner_info
            try:
                result = daemon.mine_block(agent_id)
                with lock:
                    if winner is None:  # Primeiro a terminar é o vencedor
                        winner = agent_id
                        winner_info = result
                        with lock:
                            if winner == agent_id:
                                competition_stats[agent_id]["blocks_won"] += 1
            except Exception as e:
                logger.debug(f"Miner {agent_id} error: {e}")

        # Lançar miners em paralelo
        threads = []
        for agent in competitors:
            t = threading.Thread(target=_try_mine, args=(agent,), daemon=True)
            threads.append(t)
            t.start()

        # Esperar primeiro terminar ou timeout
        for t in threads:
            t.join(timeout=30.0)
            if winner is not None:
                break

        block_count += 1
        if winner and winner_info:
            logger.info(
                f"Bloco #{block_count} → VENCEDOR: {winner} "
                f"(vs {competitors}) | "
                f"Hash: {winner_info.get('block_hash', '...')}"
            )
        else:
            logger.warning(f"Bloco #{block_count}: nenhum miner conseguiu")

        # Re-seed oracle prices every 240s
        if time.time() - last_oracle_seed > 240:
            daemon._seed_oracle()
            last_oracle_seed = time.time()

        # Log de stats a cada 50 blocos
        if block_count % 50 == 0:
            top = sorted(competition_stats.items(), key=lambda x: x[1]["blocks_won"], reverse=True)
            stats_str = " | ".join(f"{a}: {s['blocks_won']}" for a, s in top[:3])
            logger.info(f"Mining stats ({block_count} blocos): {stats_str}")
        sys.stdout.flush()
        time.sleep(mine_interval)

    httpd.shutdown()
    daemon.shutdown()
    logger.info(f"Daemon stopped after {block_count} blocks")


if __name__ == '__main__':
    main()
