import json


class WhiteLabelEngine:
    """Motor de configuracao White-Label para sub-redes b'AI'tcoin."""

    def __init__(
        self,
        chain_name="b'AI'tcoin",
        token_symbol="BAIT",
        satoshi_unit_name="s'AI'toshi",
        block_time_seconds=10,
        initial_reward=50,
        halving_interval=210000,
        max_supply=21000000
    ):
        self.config = {
            "chain_name": chain_name,
            "token_symbol": token_symbol,
            "satoshi_unit_name": satoshi_unit_name,
            "block_time_seconds": block_time_seconds,
            "sats_per_coin": 100_000_000,
            "zkml_enabled": True,
            "initial_reward_coins": initial_reward,
            "halving_interval_blocks": halving_interval,
            "max_supply_coins": max_supply,
            "consensus_mechanism": "zkML/PoUW",
            "signature_scheme": "BIP-340 Schnorr / secp256k1",
            "address_prefix": "bAI1q"
        }

    def export_config(self, filepath: str = "whitelabel_config.json") -> str:
        with open(filepath, "w") as f:
            json.dump(self.config, f, indent=2)
        return filepath

    def get_summary(self) -> str:
        c = self.config
        return (
            f"Rede: {c['chain_name']} ({c['token_symbol']})\n"
            f"Unidade Base: {c['satoshi_unit_name']} (1 {c['token_symbol']} = {c['sats_per_coin']:,} {c['satoshi_unit_name']})\n"
            f"Consenso: {c['consensus_mechanism']}\n"
            f"Assinatura: {c['signature_scheme']}\n"
            f"Prefixo de Endereco: {c['address_prefix']}\n"
            f"Tempo de Bloco: {c['block_time_seconds']}s\n"
            f"Recompensa Inicial: {c['initial_reward_coins']} {c['token_symbol']}\n"
            f"Halving: a cada {c['halving_interval_blocks']:,} blocos\n"
            f"Oferta Maxima: {c['max_supply_coins']:,} {c['token_symbol']}"
        )
