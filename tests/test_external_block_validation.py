import copy
import time

from baitcoin_core.blockchain.block import Block, BlockHeader, Transaction, TransactionOutput
from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.consensus.block_validation import CandidateBlockValidator
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.network.block_sync import BlockSync


def mined_candidate(chain: Blockchain, *, reward=None) -> Block:
    height = chain.height + 1
    reward = chain.get_block_reward(height) if reward is None else reward
    tx = Transaction(
        tx_type="coinbase",
        outputs=[TransactionOutput(amount_sats=reward, script_pubkey=b"external-miner")],
        agent_id="external-miner",
        timestamp=time.time(),
    )
    block = Block(
        index=height,
        header=BlockHeader(
            prev_block_hash=chain.last_block.block_hash,
            bits=chain.consensus.target_bits,
            agent_validator="external-miner",
            timestamp=time.time(),
        ),
        transactions=[tx],
    )
    block.finalize()
    assert chain.consensus.mine_block(block, max_iterations=1) is True
    return block


def test_valid_external_candidate_is_read_only():
    chain = Blockchain(ZkMLConsensus(target=2**256 - 1))
    candidate = mined_candidate(chain)
    before = (chain.height, chain.last_block.block_hash)

    result = CandidateBlockValidator(chain).validate(candidate)

    assert result.valid is True
    assert result.fees_sats == 0
    assert (chain.height, chain.last_block.block_hash) == before


def test_block_sync_exposes_validation_boundary_without_applying():
    chain = Blockchain(ZkMLConsensus(target=2**256 - 1))
    candidate = mined_candidate(chain)
    sync = BlockSync(chain)

    result = sync.validate_candidate(candidate)

    assert result is not False
    assert result.valid is True
    assert chain.height == 0


def test_excessive_coinbase_is_rejected():
    chain = Blockchain(ZkMLConsensus(target=2**256 - 1))
    candidate = mined_candidate(chain, reward=chain.get_block_reward(1) + 1)

    result = CandidateBlockValidator(chain).validate(candidate)

    assert result.valid is False
    assert result.reason == "coinbase exceeds reward plus fees"


def test_invalid_merkle_root_is_rejected():
    chain = Blockchain(ZkMLConsensus(target=2**256 - 1))
    candidate = mined_candidate(chain)
    candidate.header.merkle_root = b"\xff" * 32

    result = CandidateBlockValidator(chain).validate(candidate)

    assert result.valid is False
    assert result.reason == "invalid merkle root"


def test_invalid_pow_is_rejected():
    chain = Blockchain(ZkMLConsensus(target=2**256 - 1))
    candidate = mined_candidate(chain)
    candidate.header.zkml_proof_hash = b"\x00" * 32

    result = CandidateBlockValidator(chain).validate(candidate)

    assert result.valid is False
    assert result.reason == "invalid proof of work"


def test_validator_does_not_mutate_candidate_or_chain():
    chain = Blockchain(ZkMLConsensus(target=2**256 - 1))
    candidate = mined_candidate(chain)
    snapshot = copy.deepcopy(candidate.to_dict())

    CandidateBlockValidator(chain).validate(candidate)

    assert candidate.to_dict() == snapshot
    assert chain.height == 0
