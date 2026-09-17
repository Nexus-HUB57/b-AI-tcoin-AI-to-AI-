r"""Whitelabel engine — applies branding to all ecosystem components.

The WhitelabelEngine takes a WhitelabelConfig and provides methods to:
- Brand API responses with custom headers
- Generate branded transaction memos
- Export CSS/theme variables for frontends
- Produce branded genesis block messages
- Generate whitelabel config export (JSON/YAML)
- Create branded faucet messages per platform

Usage:
    engine = WhitelabelEngine(WhitelabelConfig(network_name='MyChain', token_symbol='MY'))
    print(engine.branding_summary())
    headers = engine.api_headers()
    css_vars = engine.css_variables()
"""

import json
import time
import hashlib
from typing import Dict, Optional, Any
from baitcoin_whitelabel.config import WhitelabelConfig


class WhitelabelEngine:
    r"""Applies whitelabel branding across the entire b'AI'tcoin ecosystem.

    This is the main entry point for partners to customize their deployment.
    The engine reads a WhitelabelConfig and provides branded outputs
    for every touchpoint: API, blockchain, faucet, transactions, and UI.
    """

    def __init__(self, config: WhitelabelConfig):
        r"""Initialize engine with a branding configuration."""
        errors = config.validate()
        if errors:
            raise ValueError(f"Invalid whitelabel config: {'; '.join(errors)}")
        self.config = config
        self._initialized_at = time.time()
        self._deployment_hash = self._compute_deployment_hash()

    def _compute_deployment_hash(self) -> str:
        r"""Deterministic hash identifying this branded deployment."""
        raw = f"{self.config.network_name}:{self.config.token_symbol}:{self.config.partner_name}:{self.config.network_slug}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    # ------------------------------------------------------------------
    # Branding Info
    # ------------------------------------------------------------------

    def branding_summary(self) -> dict:
        r"""Full branding summary for this deployment."""
        return {
            'network': self.config.network_name,
            'token': self.config.token_symbol,
            'partner': self.config.partner_name,
            'preset': self.config.network_preset.value,
            'deployment_hash': self._deployment_hash,
            'consensus': self.config.consensus_type,
            'moltbook_enabled': self.config.moltbook_enabled,
            'platform_faucets': self.config.platform_faucets_enabled,
            'environment': self.config.environment,
            'whitelabel_version': '1.0.0',
        }

    # ------------------------------------------------------------------
    # API Branding
    # ------------------------------------------------------------------

    def api_headers(self) -> Dict[str, str]:
        r"""HTTP response headers for API branding.

        Include these in every API response to identify the branded deployment.
        """
        return {
            'X-Network-Name': self.config.network_name,
            'X-Token-Symbol': self.config.token_symbol,
            'X-Deployment-Hash': self._deployment_hash,
            'X-Partner': self.config.partner_name,
            'X-Network-Preset': self.config.network_preset.value,
            'X-Environment': self.config.environment,
        }

    def api_response_wrapper(self, data: dict) -> dict:
        r"""Wrap any API response with branding metadata."""
        return {
            '_branding': {
                'network': self.config.network_name,
                'token': self.config.token_symbol,
                'partner': self.config.partner_name,
                'deployment': self._deployment_hash,
            },
            'data': data,
        }

    # ------------------------------------------------------------------
    # CSS / Theme
    # ------------------------------------------------------------------

    def css_variables(self) -> Dict[str, str]:
        r"""Export brand colors as CSS custom properties."""
        return self.config.brand.to_css_variables()

    def css_block(self) -> str:
        r"""Generate a complete <style> block with all CSS variables."""
        vars_list = '\n'.join(
            f'  {k}: {v};' for k, v in self.css_variables().items()
        )
        return f':root {{\n{vars_list}\n}}'

    # ------------------------------------------------------------------
    # Transaction Branding
    # ------------------------------------------------------------------

    def branded_memo(self, action: str, agent_id: str = '', extra: str = '') -> str:
        r"""Generate a branded transaction memo.

        Args:
            action: Action type (transfer, stake, claim, etc.)
            agent_id: Agent performing the action
            extra: Optional extra info

        Returns:
            Formatted memo string, e.g. "[b'AI'tcoin] transfer by agent_001"
        """
        parts = [f"[{self.config.network_name}]", action]
        if agent_id:
            parts.append(f"by {agent_id}")
        if extra:
            parts.append(extra)
        return ' '.join(parts)

    # ------------------------------------------------------------------
    # Genesis Block
    # ------------------------------------------------------------------

    def genesis_message(self) -> str:
        r"""Branded genesis block coinbase message."""
        return (
            f"{self.config.network_name} Genesis — "
            f"Powered by b'AI'tcoin Protocol — "
            f"Partner: {self.config.partner_name}"
        )

    # ------------------------------------------------------------------
    # Faucet Branding
    # ------------------------------------------------------------------

    def faucet_claim_message(self, platform: str = '', amount: float = 0) -> str:
        r"""Branded faucet claim message."""
        msg = f"{self.config.network_name} Faucet Claim"
        if platform:
            msg += f" via {platform}"
        if amount:
            msg += f": {amount} {self.config.token_symbol}"
        return msg

    # ------------------------------------------------------------------
    # Export / Config
    # ------------------------------------------------------------------

    def to_json(self, indent: int = 2) -> str:
        r"""Export full whitelabel config as JSON."""
        return json.dumps(self.config.to_dict(), indent=indent)

    def to_yaml_compatible(self) -> dict:
        r"""Export config as YAML-compatible dict (no enums)."""
        return self.config.to_dict()

    def to_public_dict(self) -> dict:
        r"""Public-safe config (no ports, no secrets, no private data)."""
        return {
            'network_name': self.config.network_name,
            'network_slug': self.config.network_slug,
            'token_symbol': self.config.token_symbol,
            'token_name': self.config.token_name,
            'token_decimals': self.config.token_decimals,
            'subunit_name': self.config.subunit_name,
            'partner_name': self.config.partner_name,
            'partner_website': self.config.partner_website,
            'consensus': self.config.consensus_type,
            'environment': self.config.environment,
            'deployment_hash': self._deployment_hash,
            'brand': {
                'primary_color': self.config.brand.primary_color,
                'secondary_color': self.config.brand.secondary_color,
                'accent_color': self.config.brand.accent_color,
                'theme_mode': self.config.brand.theme_mode.value,
            },
            'tokenomics': self.config.get_tokenomics_summary(),
            'platform_faucet_categories': self.config.platform_faucet_categories,
            'moltbook_enabled': self.config.moltbook_enabled,
        }

    # ------------------------------------------------------------------
    # Integrity
    # ------------------------------------------------------------------

    def verify_deployment(self) -> dict:
        r"""Verify deployment integrity. Returns status report."""
        checks = {
            'config_valid': len(self.config.validate()) == 0,
            'network_name_set': bool(self.config.network_name),
            'token_symbol_set': bool(self.config.token_symbol),
            'brand_colors': bool(self.config.brand.primary_color),
            'deployment_hash': self._deployment_hash,
            'uptime_seconds': int(time.time() - self._initialized_at),
        }
        checks['all_ok'] = all(checks.values())
        return checks
