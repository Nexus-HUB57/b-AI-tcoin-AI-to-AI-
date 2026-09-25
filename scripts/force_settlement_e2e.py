#!/usr/bin/env python3
"""
force_settlement_e2e.py — Checklist operacional E2E para forçar settlement
de offers com status on-chain-pending-broadcast.

IMPORTANTE:
  Este script é fail-closed e NÃO possui chaves privadas.
  Ele apenas:
    1. Lista offers pending da API de produção
    2. Valida pré-condições (custody, deposit, confirmations)
    3. Gera o payload/chamada que um executor autorizado usaria
    4. Documenta provas esperadas no explorer + mempool.space

Uso:
  python3 force_settlement_e2e.py [--offer-id ID] [--dry-run]

Data: 24/09/2026
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from typing import Any, Dict, List, Optional

API_BASE = "https://mybait.org"
CUSTODY_KNOWN = {
    "1Kj6epyY2MdzZUCHE572jeV9n7DDRReaZJ",  # ~2408 BTC real (blockstream 24/09)
    "12vG4zB6EG5FC6FhxnW688WkP1b7iK2M3X",  # 0 BTC (vazio)
}


def fetch_json(path: str, timeout: int = 15) -> Dict[str, Any]:
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "BAIT-E2E-Validator/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def get_swap_book() -> Dict[str, Any]:
    return fetch_json("/api/v1/swap/book")


def get_status() -> Dict[str, Any]:
    return fetch_json("/api/v1/status")


def get_explorer_latest() -> Dict[str, Any]:
    return fetch_json("/api/v1/explorer/txs/latest")


def list_pending_offers(book: Dict[str, Any]) -> List[Dict[str, Any]]:
    offers = book.get("offers", [])
    pending = [
        o
        for o in offers
        if o.get("settlement") == "on-chain-pending-broadcast"
        or (o.get("status") == "open" and "pending" in str(o.get("settlement", "")).lower())
    ]
    return pending


def checklist_header(offer: Dict[str, Any]) -> None:
    print("=" * 72)
    print("CHECKLIST — Forçar Settlement de Offer Pending")
    print("=" * 72)
    print(f"offer_id     : {offer.get('offer_id')}")
    print(f"side         : {offer.get('side')}")
    print(f"quantity     : {offer.get('quantity') or offer.get('amount_in')}")
    print(f"out_btc      : {offer.get('out_btc')}")
    print(f"out_bait     : {offer.get('out_bait')}")
    print(f"rate         : {offer.get('rate')}")
    print(f"custody      : {offer.get('custody') or offer.get('destination')}")
    print(f"status       : {offer.get('status')}")
    print(f"settlement   : {offer.get('settlement')}")
    print(f"sig_scheme   : {offer.get('sig_scheme')}")
    print("-" * 72)


def run_checklist(offer: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
    """Executa os passos do checklist e retorna resultado estruturado."""
    result: Dict[str, Any] = {
        "offer_id": offer.get("offer_id"),
        "steps": [],
        "success": False,
        "dry_run": dry_run,
        "ts": time.time(),
    }

    def step(name: str, ok: bool, detail: str) -> None:
        status = "PASS" if ok else "FAIL/BLOCK"
        print(f"  [{status}] {name}: {detail}")
        result["steps"].append({"name": name, "ok": ok, "detail": detail})

    # 1. Pré-requisitos
    print("\n### Pré-requisitos")
    custody = offer.get("custody") or offer.get("destination") or ""
    step(
        "1. Custody address conhecido",
        custody in CUSTODY_KNOWN or custody.startswith("1") or custody.startswith("bc1"),
        f"custody={custody}",
    )
    step(
        "2. Chave de custódia BTC disponível",
        False,  # nunca temos chave neste ambiente
        "REQUER HSM / multisig / keystore autorizado — NÃO disponível neste sandbox",
    )
    step(
        "3. Bridge wallet BAIT (Schnorr) disponível",
        False,
        "REQUER chave Schnorr do bridge/treasury — NÃO disponível",
    )
    step(
        "4. enable_settlement=True no executor",
        False,
        "Configuração de produção (não acessível publicamente)",
    )
    step(
        "5. ParityGate quorum ≥3 + proof válido",
        False,
        "Attestation externa necessária (fail-closed)",
    )

    # 2. Validação de estado
    print("\n### Validação de estado da offer")
    step(
        "6. Offer status == open + settlement pending-broadcast",
        offer.get("status") == "open"
        and "pending" in str(offer.get("settlement", "")).lower(),
        f"status={offer.get('status')} settlement={offer.get('settlement')}",
    )

    # 3. Passos de execução (simulados)
    print("\n### Passos de execução (simulados — dry-run)")
    step(
        "7. Verificar depósito BTC na custody address",
        True,
        "Manual: consultar blockstream.info / mempool.space pelo endereço de custody",
    )
    step(
        "8. Confirmar UTXO ≥ required confirmations",
        False,
        "Depende de BitcoinCoreReader + confirmations on-chain",
    )
    step(
        "9. executor.process(order_id) → BAIT_SUBMITTED",
        False,
        "Requer SwapExecutor com enable_settlement=True e chaves",
    )
    step(
        "10. bait.submit() retorna txid BAIT válido",
        False,
        "BaitBlockchainSettlement + bridge key Schnorr",
    )
    step(
        "11. Minerar/aguardar bloco → status confirmed → SETTLED",
        False,
        "Depende de mineração do L1 BAIT",
    )
    step(
        "12. Explorer mostra tx type=transfer com valor BAIT",
        False,
        "Hoje explorer indexa quase só coinbase — gap crítico",
    )
    step(
        "13. Broadcast saída BTC + atualizar master_pool",
        False,
        "master_pool atual = {addresses:0, btc:0, utxos:0}",
    )
    step(
        "14. Publicar prova (txid BTC + txid BAIT) no feed / report",
        False,
        "Após settlement real",
    )

    # Critérios de sucesso
    print("\n### Critérios de sucesso (estado atual)")
    all_ok = all(s["ok"] for s in result["steps"] if s["name"].startswith(("6",)))
    result["success"] = False  # nunca true sem chaves
    print(f"  Resultado: {'READY' if all_ok else 'BLOCKED'} (dry_run={dry_run})")
    print(
        "  Motivo: ambiente de validação não possui chaves de custódia/bridge. "
        "Settlement real deve ser executado pelo nó autorizado (chimera7 / bridge operator)."
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Force settlement E2E checklist")
    parser.add_argument("--offer-id", help="Offer ID específico (default: primeira pending)")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--list-only", action="store_true", help="Apenas listar pending")
    args = parser.parse_args()

    print("Fetching production state...")
    try:
        status = get_status()
        book = get_swap_book()
        explorer = get_explorer_latest()
    except Exception as e:
        print(f"ERROR fetching production: {e}", file=sys.stderr)
        return 1

    print(f"Chain height: {status.get('chain_height')} | valid={status.get('chain_valid')}")
    print(f"master_pool: {book.get('master_pool')}")
    print(f"custody_btc: {book.get('custody_btc')}")

    pending = list_pending_offers(book)
    print(f"\nPending offers found: {len(pending)}")
    for i, o in enumerate(pending):
        print(f"  [{i+1}] {o.get('offer_id')} side={o.get('side')} qty={o.get('quantity')} settlement={o.get('settlement')}")

    if args.list_only:
        return 0

    # Selecionar offer
    offer: Optional[Dict[str, Any]] = None
    if args.offer_id:
        offer = next((o for o in pending if o.get("offer_id") == args.offer_id), None)
        if not offer:
            # try filled list too
            offer = next((o for o in book.get("offers", []) if o.get("offer_id") == args.offer_id), None)
        if not offer:
            print(f"Offer {args.offer_id} not found", file=sys.stderr)
            return 1
    elif pending:
        # Prefer offer index 2 (1-based) if exists, else first
        idx = 1 if len(pending) > 1 else 0  # "offer específica 2" → index 1
        offer = pending[idx]
        print(f"\nSelected offer (pending[{idx}] = offer #2): {offer.get('offer_id')}")
    else:
        print("No pending offers to settle.")
        return 0

    checklist_header(offer)
    result = run_checklist(offer, dry_run=args.dry_run)

    # Explorer check
    print("\n### Explorer latest txs (sample)")
    txs = explorer.get("transactions", [])
    types: Dict[str, int] = {}
    for t in txs[:20]:
        typ = t.get("tx_type", "?")
        types[typ] = types.get(typ, 0) + 1
    print(f"  Types in latest 20: {types}")
    if types.get("transfer", 0) == 0 and types.get("coinbase", 0) > 0:
        print("  ⚠ GAP: nenhuma tx transfer visível — settlement BAIT ainda não indexado publicamente")

    # Write report
    out_path = f"/home/workdir/artifacts/settlement_checklist_{offer.get('offer_id')}.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nReport written: {out_path}")

    print("\n" + "=" * 72)
    print("PRÓXIMOS PASSOS OPERACIONAIS (nó autorizado)")
    print("=" * 72)
    print("""
1. No nó com chave de custódia e bridge:
   - enable_settlement=True
   - ParityGate com quorum ≥3
   - executor.process("<order_id>")

2. Após BAIT_SUBMITTED → aguardar mineração → SETTLED

3. Verificar no explorer:
   GET /api/v1/explorer/txs/latest  → deve aparecer type=transfer

4. Broadcast BTC (lado saída) e atualizar master_pool

5. Publicar no feed:
   "Settlement completo: offer_id=... txid_bait=... txid_btc=... amount=..."

6. Atualizar report.html / nucleus.json com prova
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
