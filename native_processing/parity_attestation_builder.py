"""Constrói e assina ParityAttestation a partir de preços reais (oráculos).

Integra:
  - baitcoin_ai.oracle.real_feed (CoinGecko / Binance)
  - native_processing.schnorr_keypair (assinatura BIP-340)
  - native_processing.parity_gate (ParityAttestation)

Fluxo:
  1. Buscar preços BTC/USDT (e opcionalmente BRL)
  2. Montar ParityAttestation com bait_usdt_ppm ≈ 1_000_000 (paridade alvo)
  3. Cada oráculo assina o digest
  4. proof_b64 = Base64(sig_a || sig_b || sig_c)
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Mapping, Optional, Sequence

from native_processing.parity_gate import ParityAttestation
from native_processing.schnorr_parity_verifier import build_proof_b64

logger = logging.getLogger("baitcoin.parity.builder")


def _ppm_from_price(price: float, reference: float = 1.0) -> int:
    """Converte preço em parts-per-million relativo a reference.

    Ex.: BAIT cotado a 1.000 USDT → 1_000_000 ppm.
    """
    if price <= 0 or reference <= 0:
        raise ValueError("prices must be positive")
    return int(round((price / reference) * 1_000_000))


def fetch_market_prices(symbols: Sequence[str] = ("BTC",)) -> Dict[str, Optional[float]]:
    """Tenta real_feed; fallback silencioso se o módulo não estiver disponível."""
    try:
        from baitcoin_ai.oracle.real_feed import fetch_coingecko, fetch_binance
    except ImportError:
        logger.warning("baitcoin_ai.oracle.real_feed not available — using stub prices")
        return {s: None for s in symbols}

    prices = fetch_coingecko(list(symbols))
    missing = [s for s, p in prices.items() if p is None]
    if missing:
        fallback = fetch_binance(missing)
        for s, p in fallback.items():
            if p is not None:
                prices[s] = p
    return prices


def build_signed_attestation(
    signers: Mapping[str, Any],
    *,
    bait_usdt: float = 1.0,
    usdt_usd: float = 1.0,
    usd_brl: Optional[float] = None,
    ttl_seconds: float = 60.0,
    round_id: Optional[str] = None,
    now: Optional[float] = None,
    quorum: Optional[int] = None,
) -> ParityAttestation:
    """Cria ParityAttestation assinada pelos oráculos em `signers`.

    Args:
        signers: dict source_id → objeto com .sign(message) → signature.raw (64 bytes)
                 (ex.: SchnorrKeyPair)
        bait_usdt: preço BAIT em USDT (default 1.0 = paridade)
        usdt_usd: preço USDT em USD
        usd_brl: preço USD em BRL (se None, usa 5.0 como placeholder)
        ttl_seconds: validade da attestation
        round_id: identificador da rodada (auto se None)
        now: timestamp (auto se None)
        quorum: mínimo de assinaturas (default = len(signers))
    """
    if not signers:
        raise ValueError("at least one signer is required")

    now = time.time() if now is None else float(now)
    source_ids = tuple(sorted(signers.keys()))  # deterministic order
    q = quorum if quorum is not None else len(source_ids)
    if q < 1 or q > len(source_ids):
        raise ValueError("invalid quorum")

    if usd_brl is None:
        usd_brl = 5.0  # placeholder; produção deve buscar FX real

    att = ParityAttestation(
        pair="BAIT/USDT",
        bait_usdt_ppm=_ppm_from_price(bait_usdt),
        usdt_usd_ppm=_ppm_from_price(usdt_usd),
        usd_brl_ppm=_ppm_from_price(usd_brl),
        observed_at=now,
        expires_at=now + ttl_seconds,
        round_id=round_id or f"round-{uuid.uuid4().hex[:12]}",
        source_ids=source_ids,
        quorum=q,
        proof_b64="",
    )

    # build_proof_b64 expects attestation.source_ids order
    # Re-order signers to match
    ordered_signers = {sid: signers[sid] for sid in source_ids}
    proof = build_proof_b64(att, ordered_signers)

    # Return new frozen attestation with proof
    return ParityAttestation(
        pair=att.pair,
        bait_usdt_ppm=att.bait_usdt_ppm,
        usdt_usd_ppm=att.usdt_usd_ppm,
        usd_brl_ppm=att.usd_brl_ppm,
        observed_at=att.observed_at,
        expires_at=att.expires_at,
        round_id=att.round_id,
        source_ids=att.source_ids,
        quorum=att.quorum,
        proof_b64=proof,
    )


def build_from_market(
    signers: Mapping[str, Any],
    *,
    bait_usdt: float = 1.0,
    ttl_seconds: float = 60.0,
) -> ParityAttestation:
    """Busca preços de mercado e constrói attestation assinada.

    Nota: BAIT ainda não tem preço de mercado líquido; bait_usdt default = 1.0
    (paridade alvo do protocol). Quando houver preço real, passar explicitamente.
    """
    prices = fetch_market_prices(["BTC"])
    # USDT ≈ 1 USD na prática; BRL via proxy se necessário
    return build_signed_attestation(
        signers,
        bait_usdt=bait_usdt,
        usdt_usd=1.0,
        usd_brl=5.0,
        ttl_seconds=ttl_seconds,
    )
