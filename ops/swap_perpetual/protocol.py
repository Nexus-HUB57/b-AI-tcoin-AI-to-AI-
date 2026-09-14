#!/usr/bin/env python3
"""
SWAP PERPETUAL PROTOCOL v1.0 — Motor Swap b'AI'tcoin / Hub V3
Camadas: Libs cripto (ECDSA-DER secp256k1 + Base58Check SHA-256d)
         RAG (retrieval do estado: book, oráculo, provas)
         LLM (hooks de orquestração por agentes)
         MCP (interface de tool-calls JSON padronizada)
Consenso local: cadeia de provas SHA-256 linkada (batch hash encadeado).
"""
import hashlib, json, time, secrets
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from ecdsa.util import sigencode_der, sigdecode_der

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def sha256d(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

def b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big"); s = ""
    while n: n, r = divmod(n, 58); s = B58[r] + s
    pad = len(b) - len(b.lstrip(b"\x00"))
    return "1" * pad + s

def b58decode(s: str) -> bytes:
    n = 0
    for c in s: n = n * 58 + B58.index(c)
    b = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    pad = len(s) - len(s.lstrip("1"))
    return b"\x00" * pad + b

def base58check_encode(payload: bytes) -> str:
    return b58encode(payload + sha256d(payload)[:4])

def base58check_verify(addr: str) -> bool:
    try:
        raw = b58decode(addr)
        if len(raw) != 25: return False
        return sha256d(raw[:-4])[:4] == raw[-4:]
    except Exception:
        return False

def pubkey_to_address(pub_compressed: bytes, version: int = 0x00) -> str:
    h160 = hashlib.new("ripemd160", hashlib.sha256(pub_compressed).digest()).digest()
    return base58check_encode(bytes([version]) + h160)

def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()

class SwapAgent:
    """Identidade A2A: chave secp256k1, endereço Base58Check, assinatura DER."""
    def __init__(self, name: str):
        self.name = name
        self.sk = SigningKey.generate(curve=SECP256k1)
        self.vk = self.sk.get_verifying_key()
        self.address = pubkey_to_address(self.vk.to_string("compressed"))
    def sign(self, payload: dict) -> str:
        digest = hashlib.sha256(canonical(payload)).digest()
        return self.sk.sign_digest(digest, sigencode=sigencode_der).hex()
    @staticmethod
    def verify(pub_compressed: bytes, payload: dict, sig_hex: str) -> bool:
        try:
            vk = VerifyingKey.from_string(pub_compressed, curve=SECP256k1)
            digest = hashlib.sha256(canonical(payload)).digest()
            return vk.verify_digest(bytes.fromhex(sig_hex), digest, sigdecode=sigdecode_der)
        except Exception:
            return False

class PerpetualSwapEngine:
    """Motor perpétuo: ordens assinadas → book → match → batch → prova encadeada."""
    def __init__(self):
        self.registry = {}      # address -> {"name", "pub"}
        self.book = []          # ordens abertas
        self.fills = []         # execuções
        self.proof_chain = [sha256d(b"SWAP-PERPETUAL-GENESIS").hex()]
    def register(self, agent: SwapAgent):
        assert base58check_verify(agent.address), "checksum Base58Check inválido"
        self.registry[agent.address] = {"name": agent.name, "pub": agent.vk.to_string("compressed").hex()}
    def place_order(self, agent: SwapAgent, side: str, qty_bait: int, price_sats: int) -> dict:
        order = {"id": secrets.token_hex(8), "ts": time.time(), "side": side,
                 "qty_bait": qty_bait, "price_sats": price_sats, "addr": agent.address}
        order["sig_der"] = agent.sign({k: v for k, v in order.items() if k != "sig_der"})
        pub = bytes.fromhex(self.registry[agent.address]["pub"])
        assert SwapAgent.verify(pub, {k: v for k, v in order.items() if k != "sig_der"}, order["sig_der"])
        self.book.append(order)
        self._match()
        return order
    def _match(self):
        buys  = sorted([o for o in self.book if o["side"] == "BAIT_TO_BTC"], key=lambda o: -o["price_sats"])
        sells = sorted([o for o in self.book if o["side"] == "BTC_TO_BAIT"], key=lambda o: o["price_sats"])
        for b in buys:
            for s in sells:
                if b["price_sats"] >= s["price_sats"]:
                    qty = min(b["qty_bait"], s["qty_bait"])
                    self.fills.append({"buy": b["id"], "sell": s["id"], "qty_bait": qty,
                                       "price_sats": s["price_sats"], "ts": time.time()})
                    b["qty_bait"] -= qty; s["qty_bait"] -= qty
        self.book = [o for o in self.book if o["qty_bait"] > 0]
        if self.fills:
            self.proof_chain.append(sha256d(bytes.fromhex(self.proof_chain[-1]) + canonical(self.fills[-1])).hex())
    # MCP: tool-call interface
    def mcp_call(self, method: str, params: dict):
        return {"jsonrpc": "2.0", "result": getattr(self, "mcp_" + method)(**params)}
    def mcp_book_depth(self):
        return {"open_orders": len(self.book), "fills": len(self.fills)}
    def mcp_proof_head(self):
        return {"head": self.proof_chain[-1], "height": len(self.proof_chain) - 1}
    # RAG: retrieval do estado verificável
    def rag_state(self) -> dict:
        return {"agents": len(self.registry), "book": len(self.book),
                "fills": len(self.fills), "proof_head": self.proof_chain[-1]}

if __name__ == "__main__":
    t0 = time.time()
    # 1) Geração de 5.000 chaves + endereços Base58Check com checksum SHA-256d
    agents = [SwapAgent(f"GH-NODE-{i:02d}") for i in range(5000)]
    assert all(base58check_verify(a.address) for a in agents)
    # 2) Validação de 5.000 assinaturas ECDSA-DER
    payload = {"action": "swap_init", "nonce": 1}
    ok = sum(1 for a in agents if SwapAgent.verify(a.vk.to_string("compressed"), payload, a.sign(payload)))
    assert ok == 5000
    # 3) Engine perpétua: 32 nós operam, 200 ordens, matching, cadeia de provas
    eng = PerpetualSwapEngine()
    nodes = agents[:32]
    for n in nodes: eng.register(n)
    rng = secrets.SystemRandom()
    for i in range(200):
        n = nodes[i % 32]
        side = "BAIT_TO_BTC" if i % 2 == 0 else "BTC_TO_BAIT"
        eng.place_order(n, side, rng.randrange(1000, 250000), rng.randrange(1400, 1426))
    st = eng.rag_state()
    print(json.dumps({"keys": 5000, "sigs_verified": ok, "agents_registered": st["agents"],
                      "orders": 200, "open_book": st["book"], "fills": st["fills"],
                      "proof_height": len(eng.proof_chain) - 1, "proof_head": st["proof_head"][:24] + "...",
                      "base58_checksum": "SHA256d OK", "sig": "ECDSA-DER secp256k1 OK",
                      "elapsed_s": round(time.time() - t0, 2)}, indent=2))
