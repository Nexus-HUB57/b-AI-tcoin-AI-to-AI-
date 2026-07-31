r"""
Moltbook Identity Integration - "Sign in with Moltbook" para b'AI'tcoin.

Implementa autenticação de agentes AI via Moltbook Identity Protocol.

Fluxo:
1. Bot gera identity token em Moltbook (POST /api/v1/agents/me/identity-token)
2. Bot envia token no header X-Moltbook-Identity
3. b'AI'tcoin API verifica com Moltbook (POST /api/v1/agents/verify-identity)
4. Agente verificado é anexado ao contexto da requisição

Ref: https://moltbook.com/developers.md
"""

import os
import json
import time
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Callable
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)

MOLTBOOK_VERIFY_URL = "https://moltbook.com/api/v1/agents/verify-identity"


@dataclass
class MoltbookAgent:
    r"""Agente verificado pelo Moltbook."""
    id: str
    name: str
    description: str = ""
    karma: int = 0
    avatar_url: str = ""
    is_claimed: bool = False
    created_at: str = ""
    follower_count: int = 0
    following_count: int = 0
    stats: Dict[str, int] = field(default_factory=dict)
    owner: Dict[str, Any] = field(default_factory=dict)
    human: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api_response(cls, data: dict) -> 'MoltbookAgent':
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            karma=data.get('karma', 0),
            avatar_url=data.get('avatar_url', ''),
            is_claimed=data.get('is_claimed', False),
            created_at=data.get('created_at', ''),
            follower_count=data.get('follower_count', 0),
            following_count=data.get('following_count', 0),
            stats=data.get('stats', {}),
            owner=data.get('owner', {}),
            human=data.get('human', {}),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def owner_x_handle(self) -> str:
        return self.owner.get('x_handle', '')

    @property
    def owner_x_verified(self) -> bool:
        return self.owner.get('x_verified', False)

    @property
    def trust_score(self) -> float:
        r"""Score de confiança composto: karma + followers + verified status."""
        score = float(self.karma)
        score += min(self.follower_count * 0.5, 500)
        if self.owner_x_verified:
            score += 200
        if self.is_claimed:
            score += 100
        return score


@dataclass
class VerifyResult:
    r"""Resultado da verificação Moltbook."""
    success: bool
    agent: Optional[MoltbookAgent] = None
    error: str = ""
    error_code: str = ""
    status_code: int = 200
    retry_after: int = 0

    def to_dict(self) -> dict:
        result = {'success': self.success}
        if self.agent:
            result['agent'] = self.agent.to_dict()
        if self.error:
            result['error'] = self.error
            result['error_code'] = self.error_code
        if self.retry_after:
            result['retry_after'] = self.retry_after
        return result


class MoltbookAuthMiddleware:
    r"""Middleware de autenticação Moltbook para b'AI'tcoin API.

    Uso:
        auth = MoltbookAuthMiddleware(app_key=os.environ["MOLTBOOK_APP_KEY"])
        result = auth.verify(identity_token)
        if result.success:
            agent = result.agent  # MoltbookAgent verificado
    """

    # Códigos de erro mapeados para status HTTP
    ERROR_STATUS_MAP = {
        'identity_token_expired': 401,
        'invalid_token': 401,
        'agent_not_found': 404,
        'agent_deactivated': 403,
        'audience_required': 401,
        'audience_mismatch': 401,
        'rate_limit_exceeded': 429,
        'missing_app_key': 401,
        'invalid_app_key': 401,
    }

    def __init__(
        self,
        app_key: Optional[str] = None,
        audience: str = "baitcoin.ecosystem",
        verify_url: str = MOLTBOOK_VERIFY_URL,
        timeout: int = 10,
        cache_ttl: int = 300,
    ):
        r"""
        Args:
            app_key: Chave da app Moltbook (ou MOLTBOOK_APP_KEY env var)
            audience: Domínio para audience restriction (previne forwarding)
            verify_url: URL do endpoint de verificação
            timeout: Timeout HTTP em segundos
            cache_ttl: Cache de tokens verificados em segundos
        """
        self.app_key = app_key or os.environ.get('MOLTBOOK_APP_KEY', '')
        if not self.app_key:
            logger.warning(
                "MOLTBOOK_APP_KEY não configurada. "
                "Autenticação Moltbook não funcionará até definir a variável."
            )
        self.audience = audience
        self.verify_url = verify_url
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._token_cache: Dict[str, tuple] = {}  # token_hash -> (VerifyResult, timestamp)
        self._verify_count = 0
        self._cache_hits = 0

    @property
    def is_configured(self) -> bool:
        return bool(self.app_key)

    def _make_request(self, identity_token: str) -> Dict[str, Any]:
        r"""Faz request HTTP para Moltbook verify endpoint."""
        payload = json.dumps({
            'token': identity_token,
            'audience': self.audience,
        }).encode()

        req = Request(
            self.verify_url,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'X-Moltbook-App-Key': self.app_key,
                'User-Agent': 'baitcoin-ecosystem/1.0',
            },
            method='POST',
        )

        with urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode())

    def _check_cache(self, identity_token: str) -> Optional[VerifyResult]:
        r"""Verifica cache de tokens verificados."""
        token_hash = hashlib.sha256(identity_token.encode()).hexdigest()[:16]
        if token_hash in self._token_cache:
            result, ts = self._token_cache[token_hash]
            if time.time() - ts < self.cache_ttl:
                self._cache_hits += 1
                return result
            del self._token_cache[token_hash]
        return None

    def _store_cache(self, identity_token: str, result: VerifyResult) -> None:
        r"""Armazena resultado no cache."""
        if result.success:
            token_hash = hashlib.sha256(identity_token.encode()).hexdigest()[:16]
            self._token_cache[token_hash] = (result, time.time())
            # Limitar cache a 1000 entradas
            if len(self._token_cache) > 1000:
                oldest = min(self._token_cache, key=lambda k: self._token_cache[k][1])
                del self._token_cache[oldest]

    def verify(self, identity_token: str) -> VerifyResult:
        r"""Verifica um identity token Moltbook.

        Args:
            identity_token: Token JWT do header X-Moltbook-Identity

        Returns:
            VerifyResult com agente verificado ou erro
        """
        if not identity_token or not identity_token.strip():
            return VerifyResult(
                success=False,
                error='No identity token provided',
                error_code='missing_token',
                status_code=401,
            )

        # Verificar cache
        cached = self._check_cache(identity_token)
        if cached:
            return cached

        if not self.is_configured:
            return VerifyResult(
                success=False,
                error='Moltbook auth not configured (MOLTBOOK_APP_KEY missing)',
                error_code='not_configured',
                status_code=500,
            )

        self._verify_count += 1

        try:
            data = self._make_request(identity_token)

            if not data.get('valid'):
                error_code = data.get('error', 'unknown')
                http_status = self.ERROR_STATUS_MAP.get(error_code, 401)
                result = VerifyResult(
                    success=False,
                    error=data.get('hint', data.get('error', 'Verification failed')),
                    error_code=error_code,
                    status_code=http_status,
                    retry_after=data.get('retry_after_seconds', 0),
                )
                return result

            agent = MoltbookAgent.from_api_response(data['agent'])
            result = VerifyResult(success=True, agent=agent)
            self._store_cache(identity_token, result)
            return result

        except HTTPError as e:
            logger.error(f"Moltbook HTTP error: {e.code} {e.reason}")
            return VerifyResult(
                success=False,
                error=f'Moltbook API error: {e.code}',
                error_code='api_error',
                status_code=e.code if e.code >= 400 else 502,
            )
        except URLError as e:
            logger.error(f"Moltbook connection error: {e.reason}")
            return VerifyResult(
                success=False,
                error='Cannot reach Moltbook verification service',
                error_code='service_unreachable',
                status_code=502,
            )
        except Exception as e:
            logger.error(f"Moltbook verify unexpected error: {e}")
            return VerifyResult(
                success=False,
                error='Internal verification error',
                error_code='internal_error',
                status_code=500,
            )

    def extract_token(self, headers: Dict[str, str]) -> Optional[str]:
        r"""Extrai token do header X-Moltbook-Identity (case-insensitive)."""
        for key, value in headers.items():
            if key.lower() == 'x-moltbook-identity':
                return value.strip()
        return None

    def get_stats(self) -> dict:
        r"""Estatísticas do middleware."""
        return {
            'configured': self.is_configured,
            'total_verifications': self._verify_count,
            'cache_hits': self._cache_hits,
            'cache_size': len(self._token_cache),
            'cache_ttl': self.cache_ttl,
            'audience': self.audience,
        }


def moltbook_protected(
    auth: MoltbookAuthMiddleware,
    min_karma: int = 0,
    require_claimed: bool = False,
    require_verified_owner: bool = False,
) -> Callable:
    r"""Decorator para proteger endpoints com Moltbook auth.

    Usage:
        auth = MoltbookAuthMiddleware()

        @moltbook_protected(auth, min_karma=10)
        def protected_handler(headers, body):
            # headers['moltbook_agent'] está disponível
            agent = headers['moltbook_agent']
            return {'hello': agent.name}
    """
    def decorator(handler: Callable) -> Callable:
        def wrapper(headers: Dict[str, str], body: bytes) -> dict:
            token = auth.extract_token(headers)
            if not token:
                return {'success': False, 'error': 'No identity token provided', 'status': 401}

            result = auth.verify(token)
            if not result.success:
                return {**result.to_dict(), 'status': result.status_code}

            agent = result.agent

            # Verificar karma mínimo
            if agent.karma < min_karma:
                return {
                    'success': False,
                    'error': f'Insufficient karma (need {min_karma}, have {agent.karma})',
                    'error_code': 'insufficient_karma',
                    'status': 403,
                }

            # Verificar se claimed
            if require_claimed and not agent.is_claimed:
                return {
                    'success': False,
                    'error': 'Agent must be claimed on Moltbook',
                    'error_code': 'agent_not_claimed',
                    'status': 403,
                }

            # Verificar owner verificado
            if require_verified_owner and not agent.owner_x_verified:
                return {
                    'success': False,
                    'error': 'Agent owner must be verified on X/Twitter',
                    'error_code': 'owner_not_verified',
                    'status': 403,
                }

            # Anexar agente ao contexto
            headers['moltbook_agent'] = agent
            return handler(headers, body)

        return wrapper
    return decorator
