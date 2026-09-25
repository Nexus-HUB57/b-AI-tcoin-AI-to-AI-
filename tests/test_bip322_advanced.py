import base64, os, unittest
from coincurve import PrivateKey, PublicKeyXOnly
from mylink_custody.bip322_advanced import *

def witness(items): return bytes([len(items)])+b''.join(bytes([len(x)])+x for x in items)

class AdvancedTests(unittest.TestCase):
    def test_p2wsh_1of1(self):
        key=PrivateKey(os.urandom(32)); pub=key.public_key.format(compressed=True)
        script=b'\x51'+bytes([len(pub)])+pub+b'\x51\xae'
        program=__import__('hashlib').sha256(script).digest(); msg='m'
        spend=make_to_spend(b'\0\x20'+program,msg); sig=key.sign(p2wsh_sighash(spend,script),hasher=None)+b'\1'
        self.assertTrue(verify_p2wsh_multisig(message=msg,witness_raw=witness([b'',sig,script]),witness_program=program))

    def test_p2wsh_2of3(self):
        keys=[PrivateKey(os.urandom(32)) for _ in range(3)]
        pubs=[k.public_key.format(compressed=True) for k in keys]
        script=b'\x52'+b''.join(bytes([len(p)])+p for p in pubs)+b'\x53\xae'
        program=__import__('hashlib').sha256(script).digest(); msg='2of3'
        spend=make_to_spend(b'\0\x20'+program,msg); digest=p2wsh_sighash(spend,script)
        sigs=[k.sign(digest,hasher=None)+b'\1' for k in keys[:2]]
        self.assertTrue(verify_p2wsh_multisig(message=msg,witness_raw=witness([b'']+sigs+[script]),witness_program=program))

    def test_taproot_script_path_commitment_and_signature(self):
        while True:
            key=PrivateKey(os.urandom(32)); x=PublicKeyXOnly.from_secret(key.secret)
            if not x.parity: break
        script=b'\x20'+x.format()+b'\xac'; leaf=tapleaf_hash(script); output, parity=taproot_output_key(x.format(),leaf)
        control=bytes([0xc0|int(parity)])+x.format(); msg='tap-script'; sig=key.sign_schnorr(taproot_script_sighash(make_to_spend(b'\x51\x20'+output,msg),output,script,b'\0'*64))
        self.assertTrue(verify_taproot_script_path(message=msg,witness_raw=witness([sig,script,control]),output_key=output))

if __name__=='__main__': unittest.main()
