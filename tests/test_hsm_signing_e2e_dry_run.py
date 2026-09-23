from tools.hsm_signing_e2e_dry_run import MockHSMSigner, run


def test_local_hsm_signing_verifies_against_utxo_and_fee_policy():
    result = run()
    assert result.key_id == "hsm-test-key"
    assert len(result.public_key_hex) == 64
    assert len(result.tx_id) == 64
    assert result.fee_sats == 1_000
    assert result.estimated_size_bytes > 0
    assert result.fee_rate_sat_vb >= 1
    assert result.broadcast.startswith("blocked:")


def test_hsm_interface_rejects_non_digest_payload():
    signer = MockHSMSigner()
    try:
        try:
            signer.sign_digest(b"too-short")
        except ValueError as exc:
            assert "32-byte digest" in str(exc)
        else:
            raise AssertionError("short payload was accepted")
    finally:
        signer.forget()
