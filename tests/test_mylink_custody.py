import unittest
from embit.bip32 import HDKey
from mylink_custody.reconcile import UTXO, derive_address, reconcile_utxos

class CustodyTests(unittest.TestCase):
    def test_xpub_derivation_and_reconciliation(self):
        root=HDKey.from_seed(b'\x01'*32)
        xpub=root.derive("m/84h/0h/0h").to_public().to_base58()
        address=derive_address(xpub,0,0,'p2wpkh')
        result=reconcile_utxos(derived_addresses=[address], observed=[UTXO('a'*64,0,12345,address,True,900000)])
        self.assertEqual(result['status'],'PASS'); self.assertEqual(result['total_sats'],12345)
    def test_unknown_address_blocks(self):
        result=reconcile_utxos(derived_addresses=['bc1qallowed'], observed=[UTXO('a'*64,0,1,'bc1qother',True,None)])
        self.assertEqual(result['status'],'BLOCKED')

if __name__=='__main__': unittest.main()
