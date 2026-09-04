// mybaitClient.js — REST auth + WebSocket broadcast para o mybait.org.
import axios from 'axios';
import WebSocket from 'ws';

const API = process.env.MYBAIT_API_URL || 'https://www.mybait.org/api/api/v1';
const WS  = process.env.MYBAIT_WS_URL || 'wss://www.mybait.org/ws';

export class MyBaitClient {
  async status() { return (await axios.get(`${API}/status`, { timeout: 12000 })).data; }
  async syncFund(payload) {
    return (await axios.post(`${API}/mylink/fund/sync`, payload, { timeout: 15000 })).data
      .catch?.(() => ({ ok: false }));
  }
  broadcast(payload) {
    try {
      const ws = new WebSocket(WS);
      ws.on('open', () => { ws.send(JSON.stringify(payload)); ws.close(); });
      ws.on('error', () => {});
    } catch (e) {}
  }
}
