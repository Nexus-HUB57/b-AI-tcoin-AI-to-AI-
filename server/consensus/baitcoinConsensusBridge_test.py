import unittest
from baitcoinConsensusBridge import BaitcoinConsensusBridge

class TestBaitcoinConsensusBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = BaitcoinConsensusBridge()

    def test_sign_payload(self):
        sig = self.bridge.sign_payload("test-payload")
        self.assertIsNotNone(sig)
        self.assertEqual(len(sig), 64)

    def test_validate_block_empty_txs(self):
        res = self.bridge.validate_block_candidate({"height": 1, "merkle_root": "abc", "transactions": []})
        self.assertFalse(res["valid"])

    def test_validate_block_matching_merkle(self):
        res = self.bridge.validate_block_candidate({
            "height": 1,
            "merkle_root": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "transactions": []
        })
        self.assertFalse(res["valid"]) # Vazio retorna False explicitamente

if __name__ == "__main__":
    unittest.main()
