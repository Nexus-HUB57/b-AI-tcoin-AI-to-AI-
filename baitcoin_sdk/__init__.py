r"""b'AI'tcoin SDK - Integração para agentes AI terceiros.

Fornece interface simples para:
- Criar carteiras e chaves
- Enviar/receber BAIT
- Fazer stake e lending
- Consultar preços via oracle
- Registrar-se como agente
- Consumir serviços do marketplace

Uso básico:
    sdk = BaitcoinSDK(agent_id='my_agent')
    wallet = sdk.create_wallet()
    sdk.faucet_claim(wallet.pubkey_hex)
    sdk.transfer(wallet, recipient_pubkey, 1.5)  # 1.5 BAIT
"""

from baitcoin_sdk.client import BaitcoinSDK
from baitcoin_sdk.wallet_sdk import AgentWalletSDK
from baitcoin_sdk.staking_sdk import StakingSDK
from baitcoin_sdk.marketplace_sdk import MarketplaceSDK

__version__ = '0.2.0'
__all__ = ['BaitcoinSDK', 'AgentWalletSDK', 'StakingSDK', 'MarketplaceSDK']
