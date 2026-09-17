#!/usr/bin/env python3
"""FIX P0-P6 FINAL (16-set-2026) — 4 bugs: (1) P0-P6 apos serve_forever() = dead code; (2) Handler vs classe H; (3) ripemd160 removido do OpenSSL 3.x mesmo com usedforsecurity=False -> RIPEMD-160 pure-Python; (4) nginx sem rotas admin/agent/register. E2E: login 200/401, register 200, stages 1-4 200, regressao OK."""
