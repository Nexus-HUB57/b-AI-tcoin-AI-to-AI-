// index.js — orquestrador E2E: valida endereco, assina challenge, sincroniza REST+WS.
import 'dotenv/config';
import { pubkeyToP2WPKH, validateAddress, signChallenge } from './cryptoValidator.js';
import { MyBaitClient } from './mybaitClient.js';

const client = new MyBaitClient();
const INTERVAL = parseInt(process.env.SYNC_INTERVAL_MS || '30000', 10);

async function cycle() {
  try {
    const status = await client.status();
    const pubkey = process.env.MYLINK_MASTER_PUBKEY; // publica (segura)
    if (!pubkey) { console.log('[sync] MYLINK_MASTER_PUBKEY ausente — modo read-only'); return; }
    const address = pubkeyToP2WPKH(pubkey);
    const valid = validateAddress(address);
    const ch = signChallenge(`fund-challenge:${address}:${status.chain_height}`);
    const payload = { address, valid, challenge_sig: ch.signature, height: status.chain_height, ts: Date.now() };
    await client.syncFund(payload).catch(()=>{});
    client.broadcast(payload);
    console.log(`[sync] h=${status.chain_height} addr=${address.slice(0,20)}… valid=${valid.ok}`);
  } catch (e) { console.error('[sync] erro:', e.message); }
}

console.log('MyLink <-> MyBait E2E sync iniciado (intervalo %dms)', INTERVAL);
cycle();
setInterval(cycle, INTERVAL);
