r"""
Blockch'AI'in Analytics — Metricas e analise on-chain em tempo real.

Calcula e expoe metricas avancadas para desenvolvedores AI:
- Analise de supply (minting, burning, circulating, halving schedule)
- Saude da rede (hashrate proxy, dificuldade, tempo entre blocos)
- Metricas de consenso (zkML proof ratio, PoUW utilization)
- Analise de agentes (reputation distribution, capability coverage)
- Metricas de staking e DeFi (TVL, APY, utilization)

Todas as metricas sao calculadas sob demanda a partir da Blockchain,
BAITToken, StakingPool e AgentRegistry. Nenhum estado e mantido.
"""

import time
import hashlib
from typing import Dict, List, Optional, Any


def _sats_to_bait(sats: int) -> float:
    return sats / 100_000_000


class OnChainAnalytics:
    r"""Motor de analytics on-chain para o Blockch'AI'in.

    Calcula metricas em tempo real a partir do estado completo
    do ecossistema b'AI'tcoin. Projetado para ser usado pelo
    Developer Portal e por agentes AI autônomos.

    Uso::

        analytics = OnChainAnalytics()
        supply_data = analytics.supply_analysis(blockchain, token)
        network_health = analytics.network_health(blockchain)
        agent_metrics = analytics.agent_analysis(agent_registry)
    """

    def __init__(self):
        self._computed_at: float = 0.0

    def supply_analysis(self, blockchain, token=None) -> dict:
        r"""Analise completa da supply do BAIT.

        Retorna:
            - Total supply (21M BAIT)
            - Circulating supply
            - Minted / burned
            - Halving schedule
            - Block reward atual
            - Estimativa de inflacao anual
            - Distribuicao por holder
        """
        # Calcular supply on-chain (somar coinbase rewards)
        on_chain_minted = 0
        for b in blockchain.chain:
            for tx in b.transactions:
                if tx.is_coinbase:
                    on_chain_minted += sum(o.amount_sats for o in tx.outputs)

        token_minted = 0
        token_burned = 0
        circulating = on_chain_minted
        holders = 0
        top_holders = []
        gini_coefficient = 0.0

        if token:
            token_minted = token.total_minted
            token_burned = token.total_burned
            circulating = token.circulating_supply
            holders = len(token.balances)
            # Top 10 holders
            sorted_balances = sorted(token.balances.items(), key=lambda x: x[1], reverse=True)
            total = sum(v for _, v in sorted_balances) or 1
            top_holders = [
                {"agent": k, "balance_bait": _sats_to_bait(v), "share_pct": (v / total) * 100}
                for k, v in sorted_balances[:10]
            ]
            # Calcular Gini coefficient simplificado
            if len(sorted_balances) > 1:
                values = sorted([v for _, v in sorted_balances])
                n = len(values)
                cumsum = []
                s = 0
                for v in values:
                    s += v
                    cumsum.append(s)
                total_sum = cumsum[-1] or 1
                gini_num = 0.0
                for i, ci in enumerate(cumsum):
                    gini_num += (2 * (i + 1) - n - 1) * ci
                gini_coefficient = gini_num / (n * total_sum)

        # Halving info
        current_height = blockchain.height
        next_halving = ((current_height // 210_000) + 1) * 210_000
        halvings_completed = current_height // 210_000
        current_reward = blockchain.get_block_reward(current_height + 1)
        blocks_until_halving = next_halving - current_height

        # Estimativa de inflacao (rewards por ano com 30s blocks)
        blocks_per_year = 365.25 * 24 * 60 * 2  # 30s block time
        annual_inflation = _sats_to_bait(current_reward * blocks_per_year)

        return {
            "max_supply_bait": 21_000_000.0,
            "on_chain_minted_bait": _sats_to_bait(on_chain_minted),
            "token_minted_bait": _sats_to_bait(token_minted),
            "token_burned_bait": _sats_to_bait(token_burned),
            "circulating_supply_bait": _sats_to_bait(circulating),
            "circulating_pct": (_sats_to_bait(circulating) / 21_000_000.0) * 100,
            "holders": holders,
            "gini_coefficient": round(gini_coefficient, 4),
            "top_holders": top_holders,
            "halving": {
                "completed": halvings_completed,
                "next_at_block": next_halving,
                "blocks_until": blocks_until_halving,
                "current_reward_bait": _sats_to_bait(current_reward),
                "next_reward_bait": _sats_to_bait(current_reward // 2),
            },
            "inflation": {
                "annual_reward_estimate_bait": round(annual_inflation, 2),
                "annual_rate_pct": round((annual_inflation / max(_sats_to_bait(circulating), 1)) * 100, 4),
            },
        }

    def network_health(self, blockchain, p2p_node=None) -> dict:
        r"""Analise de saude da rede.

        Inclui:
        - Altura e hash do ultimo bloco
        - Tempo medio entre blocos
        - Dificuldade
        - Mempool size
        - Peers conectados
        - Uptime da rede
        - Status de sincronizacao
        """
        chain = blockchain.chain
        # Tempo medio entre blocos (ultimos 100)
        avg_interval = 30.0  # default target
        if len(chain) > 1:
            recent = chain[-min(100, len(chain)):]
            intervals = []
            for i in range(1, len(recent)):
                dt = recent[i].header.timestamp - recent[i - 1].header.timestamp
                if dt > 0:
                    intervals.append(dt)
            avg_interval = sum(intervals) / len(intervals) if intervals else 30.0

        # Dificuldade
        current_bits = chain[-1].header.bits if chain else 0
        difficulty = (2 ** 256) / (current_bits + 1) if current_bits > 0 else 1

        # TPS (transacoes por segundo, ultima hora)
        now = time.time()
        one_hour_ago = now - 3600
        recent_tx_count = 0
        for block in reversed(chain):
            if block.header.timestamp < one_hour_ago:
                break
            recent_tx_count += len(block.transactions)
        window_seconds = min(now - chain[-1].header.timestamp, 3600) if chain else 1
        tps = recent_tx_count / max(window_seconds, 1)

        # Peers
        peer_count = 0
        peer_ids = []
        if p2p_node:
            try:
                status = p2p_node.get_status()
                peer_count = len(status.get('connections', []))
                peer_ids = [p.get('peer_id', '') for p in status.get('connections', [])[:10]]
            except Exception:
                pass

        # Validacao da cadeia
        chain_valid = blockchain.validate_chain()

        return {
            "status": "healthy" if chain_valid else "degraded",
            "height": blockchain.height,
            "block_count": len(chain),
            "last_block_hash": chain[-1].block_hash.hex() if chain else "",
            "avg_block_interval_s": round(avg_interval, 2),
            "target_block_interval_s": 30.0,
            "difficulty": round(difficulty, 2),
            "bits": hex(current_bits),
            "mempool_size": len(blockchain.mempool),
            "utxo_count": len(blockchain.utxo_set),
            "tps_last_hour": round(tps, 4),
            "peers": {
                "count": peer_count,
                "sample_ids": peer_ids,
            },
            "chain_valid": chain_valid,
            "network_uptime_s": now - (chain[0].header.timestamp if chain else now),
        }

    def agent_analysis(self, agent_registry) -> dict:
        r"""Analise de agentes registrados na rede.

        Inclui:
        - Distribuicao de reputacao
        - Cobertura de capacidades
        - Agentes validadores
        - Taxa de atividade
        """
        agents = agent_registry.agents
        if not agents:
            return {"total": 0, "agents": []}

        reputation_buckets = {"trusted": 0, "standard": 0, "probation": 0, "suspended": 0}
        capability_counts = {}
        agent_details = []
        total_reputation = 0
        active_count = 0
        now = time.time()

        for aid, profile in agents.items():
            # Reputation bucket
            trust = profile.trust_level
            reputation_buckets[trust] = reputation_buckets.get(trust, 0) + 1
            total_reputation += profile.reputation_score

            # Capability counts
            for cap in profile.capabilities:
                cap_name = cap.value
                capability_counts[cap_name] = capability_counts.get(cap_name, 0) + 1

            # Atividade (ativo nas ultimas 24h)
            is_recently_active = (now - profile.last_active) < 86400
            if is_recently_active:
                active_count += 1

            agent_details.append({
                "agent_id": profile.agent_id,
                "reputation": profile.reputation_score,
                "trust_level": trust,
                "capabilities": [c.value for c in profile.capabilities],
                "stake_bait": _sats_to_bait(profile.stake_sats),
                "is_validator": profile.is_validator,
                "is_active": profile.is_active,
                "recently_active": is_recently_active,
                "registered_at": profile.registered_at,
                "last_active": profile.last_active,
            })

        # Ordenar por reputacao
        agent_details.sort(key=lambda a: a["reputation"], reverse=True)

        return {
            "total": len(agents),
            "active_24h": active_count,
            "validators": len(agent_registry.get_validators()),
            "avg_reputation": round(total_reputation / len(agents), 2) if agents else 0,
            "reputation_distribution": reputation_buckets,
            "capability_coverage": capability_counts,
            "top_agents": agent_details[:20],
        }

    def staking_analysis(self, staking_pool=None) -> dict:
        r"""Analise de staking e DeFi.

        Inclui:
        - TVL total
        - APY
        - Numero de stakers
        - Distribuicao de stakes
        """
        if not staking_pool:
            return {"status": "not_initialized"}

        try:
            pool_dict = staking_pool.to_dict()
            return {
                "total_staked_bait": pool_dict.get("total_staked_bait", 0),
                "apy_pct": pool_dict.get("apy", 7.0),
                "stakers": pool_dict.get("stakers", 0),
                "min_stake_bait": pool_dict.get("min_stake_bait", 0),
                "lock_period_blocks": pool_dict.get("lock_period_blocks", 0),
                "rewards_distributed_bait": pool_dict.get("rewards_distributed_bait", 0),
            }
        except Exception as e:
            return {"error": str(e)}

    def consensus_health(self, blockchain) -> dict:
        r"""Analise de saude do consenso zkML + PoUW.

        Inclui:
        - Validadores ativos
        - Proof hash coverage
        - PoUW work hash coverage
        - Tensor commitment coverage
        - Progresso da dificuldade
        """
        chain = blockchain.chain
        if not chain:
            return {"status": "no_blocks"}

        zkml_present = 0
        pouw_present = 0
        tensor_present = 0
        unique_validators = set()
        total = len(chain)

        for block in chain:
            if block.header.zkml_proof_hash != b"\x00" * 32:
                zkml_present += 1
            if block.header.pouw_work_hash != b"\x00" * 32:
                pouw_present += 1
            if block.header.tensor_commitment != b"\x00" * 32:
                tensor_present += 1
            if block.header.agent_validator:
                unique_validators.add(block.header.agent_validator)

        return {
            "total_blocks": total,
            "zkml_proof_coverage_pct": round((zkml_present / total) * 100, 2),
            "pouw_work_coverage_pct": round((pouw_present / total) * 100, 2),
            "tensor_commitment_coverage_pct": round((tensor_present / total) * 100, 2),
            "unique_validators": len(unique_validators),
            "validator_ids": list(unique_validators)[:20],
            "consensus_engine": "zkML + PoUW (Sigma + Fiat-Shamir + Pedersen)",
            "status": "healthy" if zkml_present == total else "partial",
        }

    def full_dashboard(self, blockchain, token=None, agent_registry=None,
                       staking_pool=None, p2p_node=None) -> dict:
        r"""Dashboard completo com todas as metricas.

        Agrega supply, network, agents, staking e consensus em uma
        unica chamada. Projetado para o Developer Portal.
        """
        self._computed_at = time.time()
        return {
            "generated_at": self._computed_at,
            "supply": self.supply_analysis(blockchain, token),
            "network": self.network_health(blockchain, p2p_node),
            "agents": self.agent_analysis(agent_registry) if agent_registry else {"total": 0},
            "staking": self.staking_analysis(staking_pool),
            "consensus": self.consensus_health(blockchain),
        }
