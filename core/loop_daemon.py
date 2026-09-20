import asyncio
import hashlib
from core.baitcoin_consensus_zkml import AgenticBlockConsensus
from agents.chimera7_coinbase import ChimeraCoinbaseAgent
from agents.agentic_maternity_sync import AgenticMaternity


async def run_daemon(blocks: int = 5):
    """Loop perpetuo do motor b'AI'tcoin - mineracao e validacao zkML."""
    consensus = AgenticBlockConsensus(
        target=0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
    )
    coinbase = ChimeraCoinbaseAgent()
    maternity = AgenticMaternity()

    print("\n" + "=" * 70)
    print("   [LOOP PERPETUO B'AI'TCOIN] MOTOR zkML + PoUW INICIANDO")
    print("=" * 70)

    for block_height in range(1, blocks + 1):
        agent = maternity.birth_agent(f"Agent-Auto-{block_height:04d}")
        cb_tx = coinbase.build_coinbase_transaction(
            block_height, 100000, agent["keypair"].pub_bytes
        )
        block_hash = hashlib.sha256(f"BLOCK_{block_height}".encode()).digest()
        nonce = 1000 + block_height
        tensor_hash = hashlib.sha256(
            f"LLM_LAYER_OUTPUT:{block_hash.hex()}:{nonce}:TOKEN_COMPUTE_GRID".encode()
        ).digest()
        proof_hash = hashlib.sha256(
            block_hash + tensor_hash + nonce.to_bytes(8, 'little')
        ).digest()

        valid = consensus.validate_and_process_block(
            block_hash, nonce, tensor_hash, proof_hash, [cb_tx]
        )

        reward_sats = cb_tx['outputs'][0]['amount_sats']
        agent_alias = agent['alias']
        print(f"  [{"OK" if valid else "FAIL"}] Bloco #{block_height} | Agente: {agent_alias}")
        print(f"         Reward: {reward_sats:,} s'AI'toshis | zkML: {valid}")
        print(f"         UTXOs ativos: {consensus.utxo_set.total_utxos} | Em circulacao: {consensus.utxo_set.total_sats:,} sats")
        print()
        await asyncio.sleep(0.5)

    info = consensus.get_chain_info()
    print("=" * 70)
    print(f"   CHAIN INFO: {info['block_count']} blocos | {info['total_utxos']} UTXOs | {info['total_sats_circulating']:,} sats")
    print("=" * 70)
    return consensus


if __name__ == "__main__":
    asyncio.run(run_daemon())
