r"""
Blockch'AI'in Rate Limiter — Gestao de API keys e rate limiting por tier.

Sistema completo de controle de acesso para o Developer Portal:

- 4 tiers de acesso (Free, Developer, Pro, Enterprise)
- Rate limiting por janela deslizante
- API keys com metadata (agent_id, tier, expires_at)
- Quota tracking (requests, bandwidth)
- Auto-generated API keys com verificacao HMAC
- Dashboard de uso

Tiers:
    Free:       100 req/min, 10k req/day
    Developer:  1000 req/min, 100k req/day
    Pro:        10000 req/min, 1M req/day
    Enterprise: unlimited

Uso::

    limiter = RateLimiter()
    limiter.create_key(agent_id="chimera7", tier="developer")
    if limiter.check_rate("chimera7_key", "explorer"):
        # Process request
"""

import time
import hmac
import hashlib
import secrets
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class DevTier(Enum):
    r"""Nivel de acesso ao Developer Portal."""
    FREE = "free"
    DEVELOPER = "developer"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Limites por tier: (requests_per_minute, requests_per_day)
TIER_LIMITS = {
    DevTier.FREE: (100, 10_000),
    DevTier.DEVELOPER: (1_000, 100_000),
    DevTier.PRO: (10_000, 1_000_000),
    DevTier.ENTERPRISE: (float('inf'), float('inf')),
}

# Precos mensais (em BAIT) - futuro, para referencia
TIER_PRICING = {
    DevTier.FREE: 0.0,
    DevTier.DEVELOPER: 50.0,
    DevTier.PRO: 500.0,
    DevTier.ENTERPRISE: 0.0,  # Custom pricing
}


@dataclass
class APIKeyInfo:
    r"""Informacoes de uma API key."""
    key: str
    key_prefix: str
    agent_id: str
    tier: str
    created_at: float
    expires_at: float
    is_active: bool = True
    total_requests: int = 0
    last_used: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "key_prefix": self.key_prefix,
            "agent_id": self.agent_id,
            "tier": self.tier,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "is_active": self.is_active,
            "total_requests": self.total_requests,
            "last_used": self.last_used,
            "metadata": self.metadata,
        }


class SlidingWindowCounter:
    r"""Contador com janela deslizante para rate limiting.

    Usa buckets de tempo para limitar a memoria. Onde cada bucket
    armazena a contagem de requests em um intervalo de tempo.
    """

    def __init__(self, window_seconds: int = 60, bucket_seconds: int = 1):
        self._window = window_seconds
        self._bucket_size = bucket_seconds
        self._buckets: Dict[int, int] = {}  # bucket_index -> count
        self._lock = threading.Lock()

    def add(self, timestamp: float = None) -> int:
        r"""Registra um request e retorna o total na janela."""
        ts = timestamp or time.time()
        bucket = int(ts) // self._bucket_size
        cutoff = int(ts - self._window) // self._bucket_size

        with self._lock:
            self._buckets[bucket] = self._buckets.get(bucket, 0) + 1
            # Limpar buckets expirados
            expired = [k for k in self._buckets if k < cutoff]
            for k in expired:
                del self._buckets[k]
            return sum(self._buckets.values())

    def count(self) -> int:
        r"""Retorna a contagem atual na janela."""
        cutoff = int(time.time() - self._window) // self._bucket_size
        with self._lock:
            expired = [k for k in self._buckets if k < cutoff]
            for k in expired:
                del self._buckets[k]
            return sum(self._buckets.values())


class RateLimiter:
    r"""Gestor de rate limiting e API keys para o Blockch'AI'in.

    Thread-safe. Suporta:
    - Criacao de API keys com HMAC
    - Verificacao de keys
    - Rate limiting por janela deslizante (minuto + dia)
    - Tracking de uso
    - Listagem e revogacao de keys
    """

    HMAC_SECRET = "baitcoin_blockchain_dev_portal_hmac_v1"
    KEY_PREFIX_LEN = 8

    def __init__(self):
        self._keys: Dict[str, APIKeyInfo] = {}  # full_key -> info
        self._prefix_map: Dict[str, str] = {}  # prefix -> full_key
        self._minute_counters: Dict[str, SlidingWindowCounter] = {}
        self._day_counters: Dict[str, int] = {}
        self._day_start: float = self._current_day_start()
        self._lock = threading.Lock()

    @staticmethod
    def _current_day_start() -> float:
        now = time.time()
        return now - (now % 86400)

    def create_key(self, agent_id: str, tier: str = "free",
                   ttl_days: int = 365, metadata: Optional[dict] = None) -> dict:
        r"""Cria uma nova API key.

        Args:
            agent_id: Identificador do agente dono da key.
            tier: Tier de acesso (free, developer, pro, enterprise).
            ttl_days: Tempo de vida em dias.
            metadata: Metadados adicionais.

        Returns:
            Dicionario com key e info (a key so e mostrada uma vez).
        """
        # Validar tier
        tier_enum = DevTier(tier.lower())

        # Gerar key segura
        raw = secrets.token_hex(32)
        hmac_sig = hmac.new(
            self.HMAC_SECRET.encode(), raw.encode(), hashlib.sha256
        ).hexdigest()[:16]
        full_key = f"bait_{raw[:32]}{hmac_sig}"
        prefix = f"bait_{raw[:6]}..."

        now = time.time()
        info = APIKeyInfo(
            key=full_key,
            key_prefix=prefix,
            agent_id=agent_id,
            tier=tier_enum.value,
            created_at=now,
            expires_at=now + (ttl_days * 86400),
            metadata=metadata or {},
        )

        with self._lock:
            self._keys[full_key] = info
            self._prefix_map[prefix] = full_key
            self._minute_counters[full_key] = SlidingWindowCounter(60, 1)
            self._day_counters[full_key] = 0

        return {
            "api_key": full_key,
            "key_prefix": prefix,
            "tier": info.tier,
            "expires_at": info.expires_at,
            "rate_limits": {
                "requests_per_minute": TIER_LIMITS[tier_enum][0],
                "requests_per_day": TIER_LIMITS[tier_enum][1],
            },
            "documentation": "https://baitcoin.eco/dev/docs",
        }

    def verify_key(self, api_key: str) -> Optional[APIKeyInfo]:
        r"""Verifica uma API key. Retorna APIKeyInfo ou None."""
        with self._lock:
            info = self._keys.get(api_key)
            if info is None:
                return None
            if not info.is_active:
                return None
            if time.time() > info.expires_at:
                info.is_active = False
                return None
            return info

    def check_rate(self, api_key: str, endpoint_group: str = "default") -> Tuple[bool, dict]:
        r"""Verifica rate limit e registra o request.

        Returns:
            Tuple (allowed, info_dict).
            Se allowed=False, info_dict contem headers de retry.
        """
        info = self.verify_key(api_key)
        if info is None:
            return False, {
                "error": "invalid_or_expired_key",
                "status": 401,
            }

        tier = DevTier(info.tier)
        min_limit, day_limit = TIER_LIMITS[tier]

        # Resetar contadores diarios se mudou de dia
        with self._lock:
            day_start = self._current_day_start()
            if day_start != self._day_start:
                self._day_counters.clear()
                self._day_start = day_start

        # Contar request
        with self._lock:
            counter = self._minute_counters.get(api_key)
            if counter is None:
                counter = SlidingWindowCounter(60, 1)
                self._minute_counters[api_key] = counter

        minute_count = counter.add()

        with self._lock:
            self._day_counters[api_key] = self._day_counters.get(api_key, 0) + 1
            day_count = self._day_counters[api_key]

        info.total_requests += 1
        info.last_used = time.time()

        # Verificar limites
        if minute_count > min_limit:
            return False, {
                "error": "rate_limit_exceeded",
                "limit": "per_minute",
                "limit_value": min_limit,
                "current": minute_count,
                "retry_after_seconds": 60,
                "status": 429,
            }

        if day_count > day_limit:
            return False, {
                "error": "rate_limit_exceeded",
                "limit": "per_day",
                "limit_value": day_limit,
                "current": day_count,
                "retry_after_seconds": 86400,
                "status": 429,
            }

        return True, {
            "remaining_minute": int(min_limit - minute_count),
            "remaining_day": int(day_limit - day_count),
            "limit_minute": min_limit,
            "limit_day": day_limit,
        }

    def revoke_key(self, key_prefix: str) -> bool:
        r"""Revoga uma API key pelo prefixo."""
        with self._lock:
            full_key = self._prefix_map.get(key_prefix)
            if full_key and full_key in self._keys:
                self._keys[full_key].is_active = False
                return True
        return False

    def list_keys(self, agent_id: Optional[str] = None) -> List[dict]:
        r"""Lista keys (filtrar por agent_id se fornecido)."""
        with self._lock:
            keys = self._keys.values()
            if agent_id:
                keys = [k for k in keys if k.agent_id == agent_id]
            return [k.to_dict() for k in keys if k.is_active]

    def get_usage_stats(self) -> dict:
        r"""Estatisticas globais de uso."""
        with self._lock:
            total_keys = len([k for k in self._keys.values() if k.is_active])
            total_requests = sum(k.total_requests for k in self._keys.values())
            by_tier = {}
            for k in self._keys.values():
                if k.is_active:
                    by_tier[k.tier] = by_tier.get(k.tier, 0) + 1
            return {
                "total_active_keys": total_keys,
                "total_requests_all_time": total_requests,
                "keys_by_tier": by_tier,
                "tier_pricing_bait_monthly": {t.value: p for t, p in TIER_PRICING.items()},
            }
