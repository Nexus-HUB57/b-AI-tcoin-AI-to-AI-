r"""
b'AI'tcoin Wallet - Carteira AI-to-AI.

Gerencia chaves, transações e armazenamento para
agentes AI que operam de forma autônoma.
"""

__version__ = "0.1.0"
from baitcoin_wallet.keys.manager import KeyManager
from baitcoin_wallet.transactions.builder import TransactionBuilder
from baitcoin_wallet.storage.kv_store import WalletStorage
from baitcoin_wallet.paper_wallet import (
    generate_paper_wallet,
    generate_paper_wallet_html,
    generate_paper_wallet_pdf_bytes,
)

__all__ = ["KeyManager", "TransactionBuilder", "WalletStorage",
           "generate_paper_wallet", "generate_paper_wallet_html", "generate_paper_wallet_pdf_bytes"]
