import time

from baitcoin_core.blockchain.block import Block, BlockHeader, Transaction, TransactionOutput
from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.network.block_sync import BlockSync
from baitcoin_explorer.indices import BlockchAInIndex


def candidate_block(index, parent_hash, agent):
    tx = Transaction(
        tx_type="coinbase",
        outputs=[TransactionOutput(amount_sats=50 * 100_000_000, script_pubkey=b"\x01" * 32)],
        agent_id=agent,
        timestamp=time.time(),
    )
    block = Block(
        index=index,
        header=BlockHeader(
            prev_block_hash=parent_hash,
            agent_validator=agent,
            timestamp=time.time(),
        ),
        transactions=[tx],
    )
    block.finalize()
    return block


def test_longer_chain_reorg_rebuilds_canonical_explorer_state():
    chain = Blockchain(ZkMLConsensus(target=2**256 - 1))
    chain.mine_block("canonical-1", b"\x02" * 32)
    chain.mine_block("canonical-2", b"\x03" * 32)
    old_tip_hash = chain.last_block.block_hash.hex()

    sync = BlockSync(chain)
    fork_parent = chain.chain[0].block_hash
    candidate = []
    parent = fork_parent
    for index in range(1, 4):
        block = candidate_block(index, parent, f"fork-{index}")
        candidate.append(block)
        parent = block.block_hash

    index = BlockchAInIndex()
    index.rebuild(chain)
    assert index.get_block_by_hash(old_tip_hash) is not None

    assert sync.resolve_longer_chain(candidate) is True
    assert chain.height == 3
    assert chain.last_block.header.agent_validator == "fork-3"
    assert old_tip_hash not in {block.block_hash.hex() for block in chain.chain}

    index.rebuild(chain)
    assert index.get_block_by_height(3).validator == "fork-3"
    assert index.get_block_by_hash(old_tip_hash) is None
    assert sync.get_sync_status()["forks_resolved"] == 1


def test_single_competing_block_is_not_enough_for_reorg():
    chain = Blockchain(ZkMLConsensus(target=2**256 - 1))
    chain.mine_block("canonical-1", b"\x02" * 32)
    sync = BlockSync(chain)
    competing = candidate_block(2, chain.chain[0].block_hash, "competing")

    assert sync.handle_fork(competing) is False
    assert sync.get_sync_status()["forks_resolved"] == 1
    assert chain.height == 1
    assert sync.get_sync_status()["orphan_pool_size"] == 1
