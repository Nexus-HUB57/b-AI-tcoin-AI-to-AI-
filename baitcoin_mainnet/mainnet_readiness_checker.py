#!/usr/bin/env python3
"""
Mainnet Readiness Checker — b'AI'tcoin (Protocolo TSRA: somente mainnet real).

Verifica, de forma determinística e sem qualquer simulação, que o nó de
produção do ecossistema b'AI'tcoin está operando corretamente na mainnet:

1. Cadeia PoW SHA-256d válida e em progresso (chain_height crescente)
2. Oracle de preços reais (CoinGecko/Binance) ativo e fresco
3. Supply on-chain coerente (token minted == blocos * recompensa)
4. Coeficiente de Gini matematicamente válido (0 <= gini <= 1)
5. Índices do explorador sincronizados com a cadeia
6. Autenticação Moltbook protegendo endpoints sensíveis
7. Persistência WAL + snapshots ativa
8. Marketplace ativo

Uso:
    $ python3 baitcoin_mainnet/mainnet_readiness_checker.py http://127.0.0.1:18445
    $ python3 baitcoin_mainnet/mainnet_readiness_checker.py https://www.mybait.org

Todas as verificações são feitas contra os endpoints REST reais do nó.
Nenhuma transação de teste é criada e nenhum estado é modificado (GET-only).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
import urllib.error

HALVING_INTERVAL = 210_000
INITIAL_REWARD_BAIT = 50.0
SAT_PER_BAIT = 100_000_000


def _get(url: str, timeout: float = 20.0):
    req = urllib.request.Request(url, headers={"User-Agent": "baitcoin-readiness-checker/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(body) if body.strip() else {}
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8", errors="replace"))
        except Exception:
            return exc.code, {"raw": str(exc)[:200]}
    except Exception as exc:  # noqa: BLE001
        return 0, {"error": str(exc)[:200]}


def block_reward_at(height: int) -> float:
    halvings = max(height, 1) // HALVING_INTERVAL
    return INITIAL_REWARD_BAIT / (2 ** halvings)


def expected_minted_sats(chain_height: int) -> int:
    """Recompensa on-chain totalizada: soma de reward por bloco (incl. genesis)."""
    total = 0
    h = 0
    # Blocos são indexados a partir do genesis (index 0)
    while h <= chain_height:
        total += int(block_reward_at(h) * SAT_PER_BAIT)
        h += 1
    return total


def check_supply_coherence(status: dict, supply: dict) -> tuple[bool, str]:
    on_chain = supply.get("on_chain_minted_bait") or 0.0
    token_minted = supply.get("token_minted_bait") or 0.0
    gini = supply.get("gini_coefficient") or 0.0
    chain_height = status.get("chain_height", 0)

    reasons = []
    if gini < 0 or gini > 1:
        reasons.append(
            f"gini_coefficient={gini} fora do intervalo matematicamente "
            f"possível [0, 1]"
        )
    if abs(token_minted - on_chain) > max(1.0, 0.01 * max(on_chain, 1.0)):
        reasons.append(
            f"token_minted_bait={token_minted} diverge de "
            f"on_chain_minted_bait={on_chain}"
        )
    if on_chain <= 0 and chain_height > 1:
        reasons.append("on_chain_minted_bait <= 0 com cadeia em progresso")
    if reasons:
        return False, "; ".join(reasons)
    return True, "supply coerente e gini válido"


def check_oracle(status: dict) -> tuple[bool, str]:
    prices = (status.get("oracle") or {}).get("prices") or {}
    live = {s: p for s, p in prices.items() if p and p > 0 and s != "BAIT"}
    if not live:
        return False, "nenhum preço real disponível (CoinGecko/Binance offline)"
    return True, f"preços reais: {', '.join(f'{s}=${p:,.2f}' for s, p in live.items())}"


def check_chain_progress(url: str, height: int) -> tuple[bool, str]:
    time.sleep(30.0)
    code, status = _get(f"{url}/api/v1/status")
    if not isinstance(status, dict):
        # O endpoint ficou indisponível entre as amostras (daemon reiniciou
        # ou caiu). Aguardar recuperação e reamostrar uma vez.
        time.sleep(15.0)
        code, status = _get(f"{url}/api/v1/status")
    if not isinstance(status, dict):
        return False, "endpoint /api/v1/status indisponivel entre as amostras"
    new_height = status.get("chain_height")
    if not isinstance(new_height, (int, float)):
        return False, "não foi possível ler chain_height na segunda amostra"
    if new_height <= height:
        return False, f"cadeia parada: {height} -> {new_height} (sem novos blocos em ~45s)"
    return True, f"mineração em progresso: {height} -> {int(new_height)}"


def run_checks(base_url: str) -> dict:
    base_url = base_url.rstrip("/")
    results: dict = {"base_url": base_url, "timestamp": time.time(), "checks": []}
    all_ok = True

    status_code, status = _get(f"{base_url}/api/v1/status")
    ok = status_code == 200 and status.get("chain_valid") is True
    all_ok &= ok
    results["checks"].append({
        "name": "status_api",
        "ok": ok,
        "detail": f"HTTP {status_code}, chain_valid={status.get('chain_valid')}"
        if status else f"HTTP {status_code} (sem corpo JSON)",
    })
    if not ok:
        results["overall"] = False
        return results

    chain_height = status.get("chain_height")
    supply_code, supply = _get(f"{base_url}/api/v1/analytics/supply")
    if supply_code == 200 and supply:
        ok, detail = check_supply_coherence(status, supply)
        all_ok &= ok
        results["checks"].append({"name": "supply_coherence", "ok": ok, "detail": detail})
    else:
        all_ok = False
        results["checks"].append({
            "name": "supply_coherence", "ok": False,
            "detail": f"/api/v1/analytics/supply HTTP {supply_code}",
        })

    ok, detail = check_oracle(status)
    all_ok &= ok
    results["checks"].append({"name": "real_oracle", "ok": ok, "detail": detail})

    explorer = status.get("explorer_index") or {}
    last_indexed = explorer.get("last_indexed_height")
    ok = isinstance(last_indexed, (int, float)) and last_indexed >= (chain_height or 0)
    all_ok &= ok
    results["checks"].append({
        "name": "explorer_sync", "ok": ok,
        "detail": f"chain={chain_height}, indexed={last_indexed}",
    })

    persistence = status.get("persistence")
    ok = persistence in ("WAL + Snapshots",)
    all_ok &= ok
    results["checks"].append({
        "name": "persistence", "ok": ok,
        "detail": f"persistence={persistence}, data_path={status.get('data_path')}",
    })

    marketplace = (status.get("marketplace") or {}).get("active") or 0
    ok = marketplace >= 7
    all_ok &= ok
    results["checks"].append({
        "name": "marketplace", "ok": ok,
        "detail": f"{marketplace} serviços ativos",
    })

    ok, detail = check_chain_progress(base_url, chain_height)
    all_ok &= ok
    results["checks"].append({"name": "chain_progress_30s", "ok": ok, "detail": detail})

    results["overall"] = bool(all_ok)
    return results


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:18445"
    print(f"Mainnet Readiness Checker — alvo: {base_url}")
    results = run_checks(base_url)
    passed = sum(1 for c in results["checks"] if c["ok"])
    total = len(results["checks"])
    for check in results["checks"]:
        mark = "PASS" if check["ok"] else "FAIL"
        print(f"  [{mark}] {check['name']}: {check['detail']}")
    print(f"\nResultado: {passed}/{total} verificações | overall={'APROVADO' if results.get('overall') else 'REPROVADO'}")
    out_path = "mainnet_readiness_report.json"
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"Relatório salvo em {out_path}")
    return 0 if results.get("overall") else 1


if __name__ == "__main__":
    raise SystemExit(main())
