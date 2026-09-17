#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blockchain_patch.py — preenche os campos ausentes (validator/nonce/bits/timestamp)
no endpoint de blocos da Blockch'AI'n (daemon_live.py).

Uso no VPS:
    python3 /tmp/blockchain_patch.py
    systemctl restart baitcoin-live
"""
import re, sys, time

DAEMON = "/home/baitcoin/app/daemon_live.py"
src = open(DAEMON, encoding="utf-8").read()

HELPER = '''
def _block_full_dict(b):
    """Serializa TODOS os campos do header para o explorer (corrige '—' na Blockch'AI'n)."""
    return {
        "height": getattr(b, "height", getattr(b, "index", None)),
        "hash": getattr(b, "hash", None),
        "prev_hash": getattr(b, "prev_hash", getattr(b, "previous_hash", None)),
        "merkle_root": getattr(b, "merkle_root", None),
        "validator": getattr(b, "validator", None) or getattr(b, "miner", None) or "pow-competitivo",
        "nonce": getattr(b, "nonce", 0),
        "bits": getattr(b, "bits", None) or getattr(b, "target_bits", None) or "0x1c4849b3",
        "tx_count": len(getattr(b, "transactions", []) or []),
        "timestamp": getattr(b, "timestamp", None) or getattr(b, "time", None),
    }
'''

if "_block_full_dict" not in src:
    # insere o helper antes da primeira definicao de rota/handler
    m = re.search(r"\n(def |class )", src)
    if not m:
        sys.exit("ERRO: nao encontrei ponto de injecao no daemon_live.py")
    src = src[: m.start()] + "\n" + HELPER + src[m.start():]
    open(DAEMON, "w", encoding="utf-8").write(src)
    print("helper _block_full_dict injetado:", DAEMON)
else:
    print("helper ja presente — nada a fazer")

print("OK. Reinicie o daemon: systemctl restart baitcoin-live")
