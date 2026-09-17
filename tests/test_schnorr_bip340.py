import csv
from pathlib import Path

from baitcoin_core.cryptography.schnorr import SchnorrKeyPair, SchnorrSignature


VECTORS = Path(__file__).with_name("data") / "bip340_test_vectors.csv"


def test_official_bip340_vectors():
    rows = list(csv.DictReader(VECTORS.open(newline="")))
    assert len(rows) == 19
    key_count = sign_count = 0
    for row in rows:
        message = bytes.fromhex(row["message"])
        public_key = bytes.fromhex(row["public key"])
        signature_raw = bytes.fromhex(row["signature"])
        signature = SchnorrSignature(int.from_bytes(signature_raw[32:], "big"), signature_raw[:32])
        expected = row["verification result"] == "TRUE"
        assert signature.verify(public_key, message) is expected, row["index"]
        if row["secret key"]:
            key = SchnorrKeyPair(int(row["secret key"], 16))
            assert key.pub_bytes.hex().upper() == row["public key"], row["index"]
            assert key.sign(message, bytes.fromhex(row["aux_rand"])).raw.hex().upper() == row["signature"], row["index"]
            key_count += 1
            sign_count += 1
    assert key_count == 8
    assert sign_count == 8
