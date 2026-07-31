r"""b'AI'tcoin Whitelabel SDK — Branding & customization for b'AI'tcoin ecosystem deployments.

Allows partners to deploy the b'AI'tcoin protocol under custom branding:
- Custom network name, token symbol, logo URLs
- Color palette and typography presets
- Network parameter presets (testnet/mainnet/partner)
- Platform faucet branding per AI partner
- API response branding headers
- Branded transaction memo prefixes

Usage:
    from baitcoin_whitelabel import WhitelabelConfig, WhitelabelEngine

    config = WhitelabelConfig(network_name='MyAI Chain', token_symbol='MYAI')
    engine = WhitelabelEngine(config)
    print(engine.branding_summary())
"""

from baitcoin_whitelabel.config import WhitelabelConfig, BrandPreset
from baitcoin_whitelabel.engine import WhitelabelEngine
from baitcoin_whitelabel.presets import PresetLibrary

__all__ = ['WhitelabelConfig', 'WhitelabelEngine', 'BrandPreset', 'PresetLibrary']
__version__ = '1.0.0'
