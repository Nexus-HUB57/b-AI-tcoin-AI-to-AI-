import copy
import time

from baitcoin_core.blockchain.chain import Blockchain
from baitcoin_core.consensus.zkml_engine import ZkMLConsensus
from baitcoin_core.consensus.work_template import ShareSubmission, WorkTemplateManager


def manager(clock=None, **kwargs):
    chain = Blockchain(ZkMLConsensus(target=2**256 - 1))
    return chain, WorkTemplateManager(
        chain,
        network="baitcoin-testnet",
        chain_id="test-chain",
        share_target=2**256 - 1,
        clock=clock or time.time,
        **kwargs,
    )


def valid_share(mgr, template_id, miner_id="miner-a", nonce=7):
    template = mgr.get_template(template_id)
    consensus = mgr.blockchain.consensus
    base_hash = bytes.fromhex(template.base_hash)
    tensor = consensus.generate_tensor_commitment(base_hash, nonce)
    proof = consensus.generate_zk_proof(base_hash, tensor, nonce)
    return ShareSubmission(
        template_id=template_id,
        miner_id=miner_id,
        nonce=nonce,
        tensor_commitment=tensor.hex(),
        proof_hash=proof.hex(),
    )


def test_template_contains_versioned_chain_and_target_fields():
    chain, mgr = manager(template_ttl_seconds=60)
    template = mgr.create_template("miner-a", b"payout-script")

    assert template.version == 1
    assert template.height == chain.height + 1
    assert template.prev_hash == chain.last_block.block_hash.hex()
    assert template.target == chain.consensus.target
    assert template.expires_at == template.created_at + 60
    assert template.to_dict()["bits"].startswith("0x")


def test_share_is_accepted_once_and_duplicate_is_idempotent():
    _, mgr = manager()
    template = mgr.create_template("miner-a", b"payout-script")
    submission = valid_share(mgr, template.template_id)

    accepted = mgr.submit_share(submission)
    duplicate = mgr.submit_share(submission)

    assert accepted.status == "accepted"
    assert accepted.share_id == submission.idempotency_key()
    assert accepted.is_block_solution is True
    assert duplicate.status == "duplicate"
    assert duplicate.share_id == accepted.share_id


def test_tampered_commitment_is_rejected_without_recording_share():
    _, mgr = manager()
    template = mgr.create_template("miner-a", b"payout-script")
    submission = valid_share(mgr, template.template_id)
    tampered = copy.copy(submission)
    tampered = ShareSubmission(**{**tampered.__dict__, "proof_hash": "00" * 32})

    result = mgr.submit_share(tampered)
    retry = mgr.submit_share(submission)

    assert result.status == "rejected"
    assert result.reason == "commitment does not match template"
    assert retry.status == "accepted"


def test_expired_template_is_rejected_and_removed():
    now = [1000.0]
    chain, mgr = manager(clock=lambda: now[0], template_ttl_seconds=10)
    template = mgr.create_template("miner-a", b"payout-script")
    now[0] = 1010.0

    result = mgr.submit_share(valid_share(mgr, template.template_id))
    removed = mgr.expire()

    assert result.status == "rejected"
    assert result.reason == "template expired"
    assert removed == 1
    assert mgr.get_template(template.template_id) is None
    assert chain.height == 0


def test_valid_block_submission_is_admitted_but_not_applied():
    chain, mgr = manager()
    template = mgr.create_template("miner-a", b"payout-script")
    candidate = copy.deepcopy(mgr._templates[template.template_id].block)
    assert chain.consensus.mine_block(candidate, max_iterations=1) is True
    candidate.finalize()

    result = mgr.submit_block(template.template_id, candidate)

    assert result.status == "accepted"
    assert result.validation is not None and result.validation.valid is True
    assert chain.height == 0


def test_block_with_changed_parent_is_rejected_before_consensus():
    chain, mgr = manager()
    template = mgr.create_template("miner-a", b"payout-script")
    candidate = copy.deepcopy(mgr._templates[template.template_id].block)
    candidate.header.prev_block_hash = b"\x99" * 32

    result = mgr.submit_block(template.template_id, candidate)

    assert result.status == "rejected"
    assert result.reason == "block does not match template"
    assert chain.height == 0
