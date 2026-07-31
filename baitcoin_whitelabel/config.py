r"""Whitelabel configuration dataclass for b'AI'tcoin ecosystem deployments.

Defines all customizable branding and network parameters that partners
can override when deploying their own branded instance of the protocol.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, List
from enum import Enum


class ThemeMode(Enum):
    """Visual theme mode."""
    DARK = "dark"
    LIGHT = "light"
    AUTO = "auto"


class NetworkPreset(Enum):
    """Pre-configured network presets."""
    MAINNET = "mainnet"
    TESTNET = "testnet"
    PARTNER_DEV = "partner_dev"
    LOCAL = "local"


@dataclass
class BrandPreset:
    r"""Visual branding preset — colors, typography, logos."""
    primary_color: str = "#6C5CE7"          # b'AI'tcoin purple
    secondary_color: str = "#00D2D3"        # Teal accent
    accent_color: str = "#FFD700"            # Gold for rewards
    background_dark: str = "#0A0A1A"         # Deep dark
    background_light: str = "#FFFFFF"        # Clean white
    text_primary: str = "#FFFFFF"            # White text on dark
    text_secondary: str = "#A0A0C0"          # Muted text
    success_color: str = "#00E676"           # Green
    error_color: str = "#FF5252"             # Red
    warning_color: str = "#FFD740"           # Yellow
    font_heading: str = "Inter, system-ui, sans-serif"
    font_body: str = "Inter, system-ui, sans-serif"
    font_mono: str = "JetBrains Mono, monospace"
    logo_url: str = ""
    logo_dark_url: str = ""
    favicon_url: str = ""
    theme_mode: ThemeMode = ThemeMode.DARK
    border_radius: str = "12px"
    spacing_unit: str = "8px"
    custom_css_url: str = ""
    opengraph_image: str = ""

    def to_css_variables(self) -> Dict[str, str]:
        r"""Export as CSS custom properties for web integration."""
        return {
            '--brand-primary': self.primary_color,
            '--brand-secondary': self.secondary_color,
            '--brand-accent': self.accent_color,
            '--bg-dark': self.background_dark,
            '--bg-light': self.background_light,
            '--text-primary': self.text_primary,
            '--text-secondary': self.text_secondary,
            '--color-success': self.success_color,
            '--color-error': self.error_color,
            '--color-warning': self.warning_color,
            '--font-heading': self.font_heading,
            '--font-body': self.font_body,
            '--font-mono': self.font_mono,
            '--border-radius': self.border_radius,
            '--spacing-unit': self.spacing_unit,
        }

    def to_dict(self) -> dict:
        d = asdict(self)
        d['theme_mode'] = self.theme_mode.value
        return d


@dataclass
class WhitelabelConfig:
    r"""Master whitelabel configuration.

    Partners create one WhitelabelConfig to fully brand their b'AI'tcoin deployment.
    All fields have defaults matching the official b'AI'tcoin branding.

    Example:
        config = WhitelabelConfig(
            network_name='ManusChain',
            token_symbol='MANUS',
            partner_name='Manus AI',
            brand=BrandPreset(primary_color='#FF6B6B'),
        )
    """
    # --- Identity ---
    network_name: str = "b'AI'tcoin"
    network_slug: str = "baitcoin"
    token_name: str = "BAIT"
    token_symbol: str = "BAIT"
    token_decimals: int = 8
    subunit_name: str = "s'AI'toshi"
    partner_name: str = "Nexus-HUB57"
    partner_website: str = "https://github.com/Nexus-HUB57"
    partner_logo: str = ""
    contact_email: str = ""

    # --- Branding ---
    brand: BrandPreset = field(default_factory=BrandPreset)

    # --- Network Parameters ---
    network_preset: NetworkPreset = NetworkPreset.MAINNET
    p2p_port: int = 18444
    api_port: int = 18445
    rpc_port: int = 18446
    max_peers: int = 50
    protocol_version: str = "baitcoin-p2p/0.2.0"
    bootstrap_peers: List[str] = field(default_factory=lambda: [
        "bootstrap1.baitcoin.eco:18444",
        "bootstrap2.baitcoin.eco:18444",
        "bootstrap3.baitcoin.eco:18444",
    ])

    # --- Blockchain ---
    total_supply: int = 21_000_000
    initial_reward: float = 50.0
    halving_interval: int = 210_000
    block_time_seconds: int = 30
    max_block_size: int = 1_000_000
    max_txs_per_block: int = 1000
    min_fee_sats: int = 100
    difficulty_adjustment_interval: int = 2016

    # --- DeFi ---
    staking_apy: float = 0.07
    staking_min_bait: int = 1000
    staking_lock_days: int = 30
    staking_penalty: float = 0.10
    lending_min_collateral: float = 1.5
    lending_liquidation_threshold: float = 1.2
    marketplace_fee: float = 0.025

    # --- Faucet ---
    faucet_claim_amount: float = 10.0
    faucet_cooldown_seconds: int = 86400
    faucet_max_per_agent: float = 100.0
    faucet_rate_limit_per_minute: int = 60

    # --- Consensus ---
    consensus_type: str = "zkml-pouw"
    zkml_target: str = "0x0000ffff00000000000000000000000000000000000000000000000000000000"

    # --- Governance ---
    governance_quorum_pct: float = 4.0
    governance_voting_days: int = 7
    governance_pass_threshold: float = 50.0

    # --- Moltbook Auth ---
    moltbook_enabled: bool = True
    moltbook_audience: str = "baitcoin.ecosystem"
    moltbook_min_karma: int = 0

    # --- Platform Faucets ---
    platform_faucets_enabled: bool = True
    platform_faucet_amount: float = 1000.0
    platform_faucet_categories: List[str] = field(default_factory=lambda: [
        "LLM & Chatbots",
        "Code & Dev Tools",
        "Image & Video Gen",
        "Research & Analysis",
        "Automation & Agents",
        "Voice & Audio",
        "Multi-Modal",
    ])

    # --- API Branding ---
    api_response_header: str = r"""{ "network": "b'AI'tcoin", "version": "0.2.0" }"""
    api_docs_url: str = ""
    api_terms_url: str = ""
    api_privacy_url: str = ""

    # --- Meta ---
    deployment_id: str = ""
    environment: str = "production"
    maintenance_mode: bool = False
    custom_metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        r"""Export full config as dictionary (no private keys or secrets)."""
        d = asdict(self)
        d['brand'] = self.brand.to_dict()
        d['network_preset'] = self.network_preset.value
        return d

    def get_tokenomics_summary(self) -> dict:
        r"""Tokenomics at-a-glance for this deployment."""
        return {
            'token': self.token_symbol,
            'supply': self.total_supply,
            'decimals': self.token_decimals,
            'subunit': self.subunit_name,
            'initial_reward': self.initial_reward,
            'halving_every': self.halving_interval,
            'block_time_s': self.block_time_seconds,
            'staking_apy': f"{self.staking_apy * 100}%",
            'marketplace_fee': f"{self.marketplace_fee * 100}%",
        }

    def get_network_summary(self) -> dict:
        r"""Network info for this deployment."""
        return {
            'network': self.network_name,
            'preset': self.network_preset.value,
            'consensus': self.consensus_type,
            'p2p_port': self.p2p_port,
            'api_port': self.api_port,
            'peers': self.max_peers,
            'bootstrap': self.bootstrap_peers,
            'environment': self.environment,
            'partner': self.partner_name,
        }
    
    def validate(self) -> List[str]:
        r"""Validate configuration. Returns list of errors (empty = valid)."""
        errors = []
        if self.total_supply <= 0:
            errors.append('total_supply must be positive')
        if self.token_decimals < 0 or self.token_decimals > 18:
            errors.append('token_decimals must be 0-18')
        if self.staking_apy < 0 or self.staking_apy > 1:
            errors.append('staking_apy must be 0-1')
        if self.lending_min_collateral < 1.0:
            errors.append('lending_min_collateral must be >= 1.0')
        if self.marketplace_fee < 0 or self.marketplace_fee > 0.5:
            errors.append('marketplace_fee must be 0-0.5')
        if self.block_time_seconds < 1:
            errors.append('block_time_seconds must be >= 1')
        if not self.network_name.strip():
            errors.append('network_name is required')
        if not self.token_symbol.strip():
            errors.append('token_symbol is required')
        return errors
