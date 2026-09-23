import base64
import pytest

from baith_policy.psbt import PsbtFormatError, decode_psbt_base64, psbt_payload_sha256


def test_psbt_magic_and_hash():
    value = base64.b64encode(b"psbt\xff\x00").decode()
    assert decode_psbt_base64(value) == b"psbt\xff\x00"
    assert len(psbt_payload_sha256(value)) == 64


def test_psbt_rejects_wrong_magic():
    value = base64.b64encode(b"notpsbt").decode()
    with pytest.raises(PsbtFormatError, match="magic"):
        decode_psbt_base64(value)


def test_psbt_rejects_invalid_base64():
    with pytest.raises(PsbtFormatError, match="base64"):
        decode_psbt_base64("!")
