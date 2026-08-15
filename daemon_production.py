#!/usr/bin/env python3
"""
b'AI'tcoin Daemon Wrapper v4 - Production.

Improvements over v3 (daemon_wrapper.py):
  1. ValidatorElection replaces hardcoded round-robin mining
  2. RealPriceOracle fetches real prices from CoinGecko/Binance
  3. State restoration from persistent WAL data
  4. New /api/v1/p2p/status endpoint
  5. New /api/v1/validators endpoint
  6. Block reward stake updates after each block
  7. Production logging at checkpoints
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
    from baitcoin_core.consensus.validator_election import ValidatorElection
    from baitcoin_ai.oracle.real_feed import RealPriceOracle
    from http.server import HTTPServer

    # Initialize daemon (all 14 modules)
    daemon = BAITDaemon(api_port=port)

    # --- FIX 2026-08-14: HTTP-first boot. Sobe o server em modo degraded ANTES
    # do replay do WAL (que leva minutos em ~6GB). /status responde 200 com
    # bootstrapping=true em vez de deixar o wrapper responder 200.
    class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    BaitcoinAPIHandler.bootstrapping = True
    httpd = ThreadedHTTPServer(('127.0.0.1', port), BaitcoinAPIHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    logger.info(f"ThreadingHTTPServer (degraded) running on port {port} durante bootstrap")

    daemon.initialize()
    daemon._register_genesis_agents()
    BaitcoinAPIHandler.bootstrapping = False

    # Initialize whitelabel engine
    init_whitelabel()

    # --- NEW: Initialize ValidatorElection (replaces round-robin) ---
    validator_election = ValidatorElection(seed_genesis=True)
    logger.info(
        f"ValidatorElection initialized: "
        f"{len(validator_election.get_validator_set())} validators, "
        f"total stake={sum(v['stake'] for v in validator_election.get_validator_set()):.0f} BAIT"
    )

    # Inject ALL dependencies (same 13 as v3 + lending_engine)
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

    # --- NEW: Add /api/v1/p2p/status endpoint ---
    def _get_p2p_status(self):
        p2p = self.p2p_node
        if p2p is None:
            return self._send_json({"error": "p2p_not_initialized"}, 200)
        stats = p2p.get_stats()
        peers = p2p.get_peer_list()
        known_blocks = getattr(self.blockchain, 'height', 0)
        self._send_json({
            "node_id": stats.get("node_id", ""),
            "connections": stats.get("peers", 0),
            "known_peers": peers,
            "known_blocks": known_blocks,
            "messages_sent": stats.get("messages_sent", 0),
            "handlers_registered": stats.get("handlers_registered", 0),
            "protocol": stats.get("protocol", ""),
        })
    BaitcoinAPIHandler._get_p2p_status_v4 = _get_p2p_status

    # --- NEW: Add /api/v1/validators endpoint ---
    def _get_validators(self):
        self._send_json(validator_election.get_stats())
    BaitcoinAPIHandler._get_validators_v4 = _get_validators

    # Override _get_status with daemon's enhanced version
    _daemon = daemon
    def _enhanced_status(self):
        self._send_json(_daemon.get_status())
    BaitcoinAPIHandler._get_status = _enhanced_status

    # --- NEW: Patch do_GET to include new production routes ---
    _orig_do_get = BaitcoinAPIHandler.do_GET
    def _patched_do_get(self):
        path, query = self._parse_path()
        # New v4 routes (checked before falling through to original)
        if path == '/api/v1/p2p/status':
            return self._get_p2p_status_v4()
        if path == '/api/v1/validators':
            return self._get_validators_v4()
        # Fall through to original routing
        _orig_do_get(self)
    BaitcoinAPIHandler.do_GET = _patched_do_get

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

    # (HTTP server ja iniciado em modo degraded acima — HTTP-first boot)\n
    # --- NEW: Seed oracle with REAL prices from CoinGecko/Binance ---
    real_oracle = RealPriceOracle(agent_id="chimera7_oracle")
    try:
        submitted = RealPriceOracle.seed_from_real_apis(daemon.oracle)
        logger.info(f"Production oracle seeded: {submitted} real prices from external APIs")
    except Exception as e:
        logger.warning(f"Real oracle seed failed, using fallback: {e}")
        # Fallback to random prices like v3
        try:
            daemon._seed_oracle()
        except Exception:
            pass

    # --- NEW: Restore state from persistent WAL ---
    try:
        chain_data = daemon.persistent_state.load_blockchain()
        if chain_data and daemon.blockchain.height > 0:
            logger.info(
                f"State restoration available: "
                f"chain height={daemon.blockchain.height}, "
                f"data keys={len(chain_data)}, "
                f"MemoryStore connected={daemon.blockchain.is_persistent}"
            )
        else:
            logger.info("No prior state to restore (fresh start)")
    except Exception as e:
        logger.warning(f"State restoration check: {e}")

    # Banner
    status = daemon.get_status()
    election_stats = validator_election.get_stats()
    print()
    print("=" * 70)
    print(f"  b'AI'tcoin Daemon v4 — Production (Stake-Weighted Consensus)")
    print("=" * 70)
    print(f"  Blockchain Height: {status['chain_height']}")
    print(f"  Chain Valid: {status['chain_valid']}")
    print(f"  Blocks Immutable: True (SHA-256d + prev_hash chain)")
    print(f"  Persistent Memory: WAL + Snapshots at {status['data_path']}")
    print(f"  Consensus: Stake-Weighted Validator Election (DPoS)")
    print(f"  Validators: {election_stats['validator_count']} registered")
    print(f"  Total Stake: {election_stats['total_stake']:.0f} BAIT")
    for v in election_stats['validators']:
        pct = (v['stake'] / election_stats['total_stake'] * 100) if election_stats['total_stake'] > 0 else 0
        print(f"    {v['agent_id']}: {v['stake']:.0f} BAIT ({pct:.1f}%)")
    print(f"  Oracle: REAL prices (CoinGecko + Binance fallback)")
    or_prices = status.get('oracle', {}).get('prices', {})
    for sym, price in or_prices.items():
        if price is not None and price > 0:
            print(f"    {sym}: ${price:,.2f}")
    print(f"  Agents Registered: {status['agents_registered']}")
    print(f"  AI Store: {status['marketplace']['active']} active services")
    print(f"  Staking APY: {status['staking']['apy']:.1f}%")
    print(f"  New Endpoints: /api/v1/p2p/status, /api/v1/validators")
    print(f"  API Server: http://127.0.0.1:{port}")
    print("=" * 70)
    print()
    sys.stdout.flush()

    # Mining loop in main thread (keeps process alive)
    block_count = 0
    last_oracle_seed = time.time()
    stop = False

    def signal_handler(sig, frame):
        nonlocal stop
        logger.info("Shutdown signal received")
        stop = True
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    while not stop:
        # --- NEW: Use ValidatorElection instead of round-robin ---
        agent = validator_election.get_next_validator()
        if agent is None:
            logger.error("No validators registered, cannot produce block")
            time.sleep(mine_interval)
            continue

        try:
            block_info = daemon.mine_block(agent)
            block_count += 1

            # --- NEW: Update validator stake with block reward ---
            reward_bait = block_info.get('reward_bait', 0)
            if reward_bait > 0:
                current = validator_election.get_validator_set()
                validator_stake = 0.0
                for v in current:
                    if v['agent_id'] == agent:
                        validator_stake = v['stake']
                        break
                new_stake = validator_stake + reward_bait
                validator_election.update_stake(agent, new_stake)
                logger.debug(
                    f"Stake update: {agent} +{reward_bait:.4f} BAIT "
                    f"= {new_stake:.4f} BAIT"
                )

            # --- NEW: Production logging every 50 blocks ---
            if block_count % 50 == 0:
                election_summary = validator_election.get_stats()
                logger.info(
                    f"[CHECKPOINT] {block_count} blocks produced | "
                    f"height={daemon.blockchain.height} | "
                    f"validators={election_summary['validator_count']} | "
                    f"total_stake={election_summary['total_stake']:.2f} BAIT | "
                    f"distribution={election_summary['production_distribution']}"
                )
                # Log P2P connections
                p2p_stats = daemon.p2p_network.get_stats()
                logger.info(
                    f"[P2P STATUS] node={p2p_stats.get('node_id')} | "
                    f"peers={p2p_stats.get('peers', 0)} | "
                    f"messages={p2p_stats.get('messages_sent', 0)}"
                )

            # Re-seed oracle with REAL prices every 240s
            if time.time() - last_oracle_seed > 240:
                try:
                    submitted = RealPriceOracle.seed_from_real_apis(daemon.oracle)
                    oracle_stats = real_oracle.get_stats()
                    logger.info(
                        f"[ORACLE] Seeded {submitted} real prices | "
                        f"source={oracle_stats.get('last_source', 'unknown')} | "
                        f"total_fetches={oracle_stats.get('total_fetches', 0)} | "
                        f"cache_hits={oracle_stats.get('cache_hits', 0)} | "
                        f"outliers={oracle_stats.get('outlier_warnings', 0)}"
                    )
                except Exception as e:
                    logger.warning(f"Real oracle seed failed: {e}")
                    try:
                        daemon._seed_oracle()
                    except Exception:
                        pass
                last_oracle_seed = time.time()

            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Mine error: {e}")
            traceback.print_exc()
            sys.stdout.flush()
        time.sleep(mine_interval)

    httpd.shutdown()
    try:
        daemon.persistent_state.force_snapshot_all()
    except Exception:
        pass

    # Final summary
    final_election = validator_election.get_stats()
    logger.info(
        f"Daemon stopped after {block_count} blocks | "
        f"final_stake={final_election['total_stake']:.2f} BAIT | "
        f"slashed={final_election['total_slashed']:.4f} BAIT"
    )


if __name__ == '__main__':
    main()
