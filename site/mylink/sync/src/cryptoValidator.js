// cryptoValidator.js — validacao do endereco Native SegWit (P2WPKH) + assinatura de challenge.
// Master key NUNCA em codigo: lida de process.env.MYLINK_MASTER_KEY (GitHub Secrets em CI).
import createHash from 'create-hash';
import { bech32 } from 'bech32';
import ECPairFactory from 'ecpair';
import * as ecc from 'tiny-secp256k1';

const ECPair = ECPairFactory(ecc);

export function pubkeyToP2WPKH(pubkeyHex) {
  const pub = Buffer.from(pubkeyHex, 'hex');
  const h160 = createHash('ripemd160').update(createHash('sha256').update(pub).digest()).digest();
  const words = bech32.toWords(h160);
  return bech32.encode('bc', words); // bc1q... (P2WPKH, BIP-173)
}

export function validateAddress(addr) {
  try {
    const dec = bech32.decode(addr);
    return { ok: dec.prefix === 'bc' && dec.words.length > 0, type: 'p2wpkh', address: addr };
  } catch (e) { return { ok: false, error: e.message, address: addr }; }
}

export function signChallenge(challenge) {
  const key = process.env.MYLINK_MASTER_KEY;
  if (!key) throw new Error('MYLINK_MASTER_KEY ausente (definir via env/secret, nunca em codigo)');
  const pair = ECPair.fromPrivateKey(Buffer.from(key, 'hex'));
  const digest = createHash('sha256').update(Buffer.from(challenge)).digest();
  const sig = pair.sign(digest);
  return { challenge, signature: sig.toString('hex'), pubkey: pair.publicKey.toString('hex') };
}
