r"""Pre-built whitelabel presets for common AI platform partnerships.

Partners can use these as starting points and override specific fields:

    from baitcoin_whitelabel.presets import PresetLibrary

    config = PresetLibrary.for_platform('manus')
    config.token_symbol = 'CUSTOM'  # override any field
"""

from typing import Dict, Optional
from baitcoin_whitelabel.config import (
    WhitelabelConfig,
    BrandPreset,
    NetworkPreset,
    ThemeMode,
)


class PresetLibrary:
    r"""Library of pre-configured whitelabel presets for AI platforms.

    Each preset provides sensible defaults for a specific AI platform partner,
    including brand colors, network names, and faucet configurations.
    All presets maintain the same underlying b'AI'tcoin protocol — only branding changes.
    """

    _PRESETS: Dict[str, WhitelabelConfig] = {}

    @classmethod
    def register(cls, key: str, config: WhitelabelConfig) -> None:
        r"""Register a custom preset."""
        cls._PRESETS[key.lower()] = config

    @classmethod
    def get(cls, key: str) -> Optional[WhitelabelConfig]:
        r"""Get a preset by platform name (case-insensitive)."""
        return cls._PRESETS.get(key.lower())

    @classmethod
    def for_platform(cls, platform: str, **overrides) -> WhitelabelConfig:
        r"""Get preset for a platform, with optional overrides.

        Args:
            platform: Platform name (e.g. 'manus', 'deepseek', 'grok')
            **overrides: Any WhitelabelConfig fields to override

        Returns:
            WhitelabelConfig with preset + overrides applied

        Raises:
            KeyError: If platform preset not found
        """
        base = cls.get(platform)
        if base is None:
            available = ', '.join(sorted(cls._PRESETS.keys())) or '(none)'
            raise KeyError(
                f"No preset for '{platform}'. Available: {available}"
            )
        if overrides:
            for k, v in overrides.items():
                if hasattr(base, k):
                    setattr(base, k, v)
        return base

    @classmethod
    def list_presets(cls) -> Dict[str, dict]:
        r"""List all registered presets with their summary."""
        return {
            name: {
                'network': cfg.network_name,
                'token': cfg.token_symbol,
                'partner': cfg.partner_name,
                'preset': cfg.network_preset.value,
            }
            for name, cfg in cls._PRESETS.items()
        }

    @classmethod
    def create_custom(cls, **kwargs) -> WhitelabelConfig:
        r"""Create a fully custom config from scratch."""
        return WhitelabelConfig(**kwargs)


# ---------------------------------------------------------------------------
# Built-in Presets — 70 AI Platform Partners
# ---------------------------------------------------------------------------

def _init_presets():
    r"""Initialize all 70 built-in platform presets."""

    # === LLM & Chatbots (10) ===
    PresetLibrary.register('manus', WhitelabelConfig(
        network_name="ManusChain",
        network_slug="manus-chain",
        token_name="ManusCoin",
        token_symbol="MANUS",
        partner_name="Manus AI",
        partner_website="https://manus.im",
        brand=BrandPreset(
            primary_color="#4F46E5",
            secondary_color="#06B6D4",
            accent_color="#F59E0B",
            background_dark="#0F172A",
        ),
    ))

    PresetLibrary.register('deepseek', WhitelabelConfig(
        network_name="DeepSeek Net",
        network_slug="deepseek-net",
        token_name="DeepCoin",
        token_symbol="DSEEK",
        partner_name="DeepSeek",
        partner_website="https://deepseek.com",
        brand=BrandPreset(
            primary_color="#1E40AF",
            secondary_color="#3B82F6",
            accent_color="#60A5FA",
            background_dark="#0C1929",
        ),
    ))

    PresetLibrary.register('grok', WhitelabelConfig(
        network_name="GrokChain",
        network_slug="grok-chain",
        token_name="GrokToken",
        token_symbol="GROK",
        partner_name="xAI / Grok",
        partner_website="https://grok.x.ai",
        brand=BrandPreset(
            primary_color="#EF4444",
            secondary_color="#F97316",
            accent_color="#FBBF24",
            background_dark="#1A0A0A",
        ),
    ))

    PresetLibrary.register('gemini', WhitelabelConfig(
        network_name="Gemini Chain",
        network_slug="gemini-chain",
        token_name="GeminiToken",
        token_symbol="GEMINI",
        partner_name="Google DeepMind",
        partner_website="https://deepmind.google",
        brand=BrandPreset(
            primary_color="#4285F4",
            secondary_color="#34A853",
            accent_color="#FBBC05",
            background_dark="#0D1117",
        ),
    ))

    PresetLibrary.register('chatgpt', WhitelabelConfig(
        network_name="GPTChain",
        network_slug="gpt-chain",
        token_name="GPTToken",
        token_symbol="GPT",
        partner_name="OpenAI",
        partner_website="https://openai.com",
        brand=BrandPreset(
            primary_color="#10A37F",
            secondary_color="#1D7A5F",
            accent_color="#6EE7B7",
            background_dark="#0A0F0D",
        ),
    ))

    PresetLibrary.register('claude', WhitelabelConfig(
        network_name="ClaudeChain",
        network_slug="claude-chain",
        token_name="ClaudeToken",
        token_symbol="CLAUDE",
        partner_name="Anthropic",
        partner_website="https://anthropic.com",
        brand=BrandPreset(
            primary_color="#D4A574",
            secondary_color="#C4956A",
            accent_color="#E8C9A0",
            background_dark="#1A1612",
        ),
    ))

    PresetLibrary.register('llama', WhitelabelConfig(
        network_name="LlamaChain",
        network_slug="llama-chain",
        token_name="LlamaToken",
        token_symbol="LLAMA",
        partner_name="Meta AI",
        partner_website="https://ai.meta.com",
        brand=BrandPreset(
            primary_color="#0668E1",
            secondary_color="#1877F2",
            accent_color="#00C853",
            background_dark="#0A1628",
        ),
    ))

    PresetLibrary.register('mistral', WhitelabelConfig(
        network_name="MistralNet",
        network_slug="mistral-net",
        token_name="MistralToken",
        token_symbol="MISTRAL",
        partner_name="Mistral AI",
        partner_website="https://mistral.ai",
        brand=BrandPreset(
            primary_color="#FF7000",
            secondary_color="#FF9500",
            accent_color="#FFB84D",
            background_dark="#1A1008",
        ),
    ))

    PresetLibrary.register('cohere', WhitelabelConfig(
        network_name="Cohere Chain",
        network_slug="cohere-chain",
        token_name="CohereToken",
        token_symbol="COHERE",
        partner_name="Cohere",
        partner_website="https://cohere.com",
        brand=BrandPreset(
            primary_color="#39D0D8",
            secondary_color="#2BB5BC",
            accent_color="#7EE8ED",
            background_dark="#0A1A1B",
        ),
    ))

    PresetLibrary.register('dola', WhitelabelConfig(
        network_name="DolaChain",
        network_slug="dola-chain",
        token_name="DolaToken",
        token_symbol="DOLA",
        partner_name="Dola AI",
        partner_website="https://dola.ai",
        brand=BrandPreset(
            primary_color="#8B5CF6",
            secondary_color="#A78BFA",
            accent_color="#C4B5FD",
            background_dark="#0F0A1A",
        ),
    ))

    # === Code & Dev Tools (10) ===
    PresetLibrary.register('github_copilot', WhitelabelConfig(
        network_name="CopilotChain",
        network_slug="copilot-chain",
        token_name="CopilotToken",
        token_symbol="COPI",
        partner_name="GitHub / Microsoft",
        partner_website="https://github.com/features/copilot",
        brand=BrandPreset(
            primary_color="#6E40C9",
            secondary_color="#8B5CF6",
            accent_color="#A78BFA",
            background_dark="#0D1117",
        ),
    ))

    PresetLibrary.register('cursor', WhitelabelConfig(
        network_name="CursorChain",
        network_slug="cursor-chain",
        token_name="CursorToken",
        token_symbol="CURS",
        partner_name="Cursor",
        partner_website="https://cursor.sh",
        brand=BrandPreset(
            primary_color="#000000",
            secondary_color="#333333",
            accent_color="#6366F1",
            background_dark="#000000",
        ),
    ))

    PresetLibrary.register('replit', WhitelabelConfig(
        network_name="ReplitChain",
        network_slug="replit-chain",
        token_name="ReplitToken",
        token_symbol="REPL",
        partner_name="Replit",
        partner_website="https://replit.com",
        brand=BrandPreset(
            primary_color="#F26207",
            secondary_color="#FF6B2B",
            accent_color="#FF9F6B",
            background_dark="#1A0E04",
        ),
    ))

    PresetLibrary.register('v0', WhitelabelConfig(
        network_name="V0Chain",
        network_slug="v0-chain",
        token_name="V0Token",
        token_symbol="V0",
        partner_name="Vercel v0",
        partner_website="https://v0.dev",
        brand=BrandPreset(
            primary_color="#000000",
            secondary_color="#FFFFFF",
            accent_color="#0070F3",
            background_dark="#000000",
            theme_mode=ThemeMode.DARK,
        ),
    ))

    PresetLibrary.register('bolt', WhitelabelConfig(
        network_name="BoltChain",
        network_slug="bolt-chain",
        token_name="BoltToken",
        token_symbol="BOLT",
        partner_name="StackBlitz / Bolt",
        partner_website="https://bolt.new",
        brand=BrandPreset(
            primary_color="#0ACF83",
            secondary_color="#06D6A0",
            accent_color="#B8F3D8",
            background_dark="#041F17",
        ),
    ))

    PresetLibrary.register('windsurf', WhitelabelConfig(
        network_name="WindsurfChain",
        network_slug="windsurf-chain",
        token_name="WindsurfToken",
        token_symbol="WIND",
        partner_name="Windsurf / Codeium",
        partner_website="https://codeium.com/windsurf",
        brand=BrandPreset(
            primary_color="#09B6A2",
            secondary_color="#06D6A0",
            accent_color="#38E8C6",
            background_dark="#041F1B",
        ),
    ))

    PresetLibrary.register('devin', WhitelabelConfig(
        network_name="DevinChain",
        network_slug="devin-chain",
        token_name="DevinToken",
        token_symbol="DEVIN",
        partner_name="Cognition / Devin",
        partner_website="https://cognition.ai",
        brand=BrandPreset(
            primary_color="#7C3AED",
            secondary_color="#8B5CF6",
            accent_color="#C4B5FD",
            background_dark="#0F0A1E",
        ),
    ))

    PresetLibrary.register('aider', WhitelabelConfig(
        network_name="AiderChain",
        network_slug="aider-chain",
        token_name="AiderToken",
        token_symbol="AID",
        partner_name="Aider",
        partner_website="https://aider.chat",
        brand=BrandPreset(
            primary_color="#2563EB",
            secondary_color="#3B82F6",
            accent_color="#93C5FD",
            background_dark="#0A1228",
        ),
    ))

    PresetLibrary.register('tabnine', WhitelabelConfig(
        network_name="TabnineChain",
        network_slug="tabnine-chain",
        token_name="TabnineToken",
        token_symbol="T9",
        partner_name="Tabnine",
        partner_website="https://tabnine.com",
        brand=BrandPreset(
            primary_color="#6B54D2",
            secondary_color="#8B73E6",
            accent_color="#CAB8FF",
            background_dark="#110E1E",
        ),
    ))

    PresetLibrary.register('gitsin', WhitelabelConfig(
        network_name="GitsinChain",
        network_slug="gitsin-chain",
        token_name="GitsinToken",
        token_symbol="GSIN",
        partner_name="Gitsin AI",
        partner_website="https://gitsin.com",
        brand=BrandPreset(
            primary_color="#14B8A6",
            secondary_color="#2DD4BF",
            accent_color="#99F6E4",
            background_dark="#042F2E",
        ),
    ))

    # === Image & Video Generation (10) ===
    PresetLibrary.register('midjourney', WhitelabelConfig(
        network_name="MidjourneyChain",
        network_slug="midjourney-chain",
        token_name="MJToken",
        token_symbol="MJ",
        partner_name="Midjourney",
        partner_website="https://midjourney.com",
        brand=BrandPreset(
            primary_color="#0D47A1",
            secondary_color="#1565C0",
            accent_color="#64B5F6",
            background_dark="#050E1F",
        ),
    ))

    PresetLibrary.register('dalle', WhitelabelConfig(
        network_name="DALL-E Chain",
        network_slug="dalle-chain",
        token_name="DALLET",
        token_symbol="DALLE",
        partner_name="OpenAI (DALL-E)",
        partner_website="https://openai.com/dall-e",
        brand=BrandPreset(
            primary_color="#10A37F",
            secondary_color="#1D7A5F",
            accent_color="#6EE7B7",
            background_dark="#0A0F0D",
        ),
    ))

    PresetLibrary.register('stable_diffusion', WhitelabelConfig(
        network_name="SDChain",
        network_slug="sd-chain",
        token_name="SDToken",
        token_symbol="SD",
        partner_name="Stability AI",
        partner_website="https://stability.ai",
        brand=BrandPreset(
            primary_color="#A855F7",
            secondary_color="#C084FC",
            accent_color="#D8B4FE",
            background_dark="#150D20",
        ),
    ))

    PresetLibrary.register('flux', WhitelabelConfig(
        network_name="FluxChain",
        network_slug="flux-chain",
        token_name="FluxToken",
        token_symbol="FLUX",
        partner_name="Black Forest Labs",
        partner_website="https://blackforestlabs.ai",
        brand=BrandPreset(
            primary_color="#18181B",
            secondary_color="#3F3F46",
            accent_color="#A1A1AA",
            background_dark="#09090B",
        ),
    ))

    PresetLibrary.register('ideogram', WhitelabelConfig(
        network_name="IdeogramChain",
        network_slug="ideogram-chain",
        token_name="IdeogramToken",
        token_symbol="IDEO",
        partner_name="Ideogram",
        partner_website="https://ideogram.ai",
        brand=BrandPreset(
            primary_color="#4F46E5",
            secondary_color="#6366F1",
            accent_color="#A5B4FC",
            background_dark="#0E0D1A",
        ),
    ))

    PresetLibrary.register('runway', WhitelabelConfig(
        network_name="RunwayChain",
        network_slug="runway-chain",
        token_name="RunwayToken",
        token_symbol="RUNW",
        partner_name="Runway",
        partner_website="https://runwayml.com",
        brand=BrandPreset(
            primary_color="#00D4FF",
            secondary_color="#00B4D8",
            accent_color="#90E0EF",
            background_dark="#041520",
        ),
    ))

    PresetLibrary.register('pika', WhitelabelConfig(
        network_name="PikaChain",
        network_slug="pika-chain",
        token_name="PikaToken",
        token_symbol="PIKA",
        partner_name="Pika Labs",
        partner_website="https://pika.art",
        brand=BrandPreset(
            primary_color="#FF6B9D",
            secondary_color="#FF85B1",
            accent_color="#FFB3D0",
            background_dark="#1A0A10",
        ),
    ))

    PresetLibrary.register('kling', WhitelabelConfig(
        network_name="KlingChain",
        network_slug="kling-chain",
        token_name="KlingToken",
        token_symbol="KLING",
        partner_name="Kuaishou / Kling",
        partner_website="https://klingai.com",
        brand=BrandPreset(
            primary_color="#FF4757",
            secondary_color="#FF6B81",
            accent_color="#FFB8C6",
            background_dark="#1A0A0C",
        ),
    ))

    PresetLibrary.register('elevenlabs', WhitelabelConfig(
        network_name="ElevenChain",
        network_slug="eleven-chain",
        token_name="ElevenToken",
        token_symbol="ELEVEN",
        partner_name="ElevenLabs",
        partner_website="https://elevenlabs.io",
        brand=BrandPreset(
            primary_color="#1E1E1E",
            secondary_color="#333333",
            accent_color="#7C3AED",
            background_dark="#0A0A0A",
        ),
    ))

    PresetLibrary.register('suno', WhitelabelConfig(
        network_name="SunoChain",
        network_slug="suno-chain",
        token_name="SunoToken",
        token_symbol="SUNO",
        partner_name="Suno AI",
        partner_website="https://suno.com",
        brand=BrandPreset(
            primary_color="#FF3366",
            secondary_color="#FF5580",
            accent_color="#FF99B3",
            background_dark="#1A0810",
        ),
    ))

    # === Research & Analysis (10) ===
    PresetLibrary.register('perplexity', WhitelabelConfig(
        network_name="PerplexityChain",
        network_slug="perplexity-chain",
        token_name="PerplexityToken",
        token_symbol="PPLX",
        partner_name="Perplexity AI",
        partner_website="https://perplexity.ai",
        brand=BrandPreset(
            primary_color="#1FB8CD",
            secondary_color="#20B2AA",
            accent_color="#7FEFEF",
            background_dark="#081A1C",
        ),
    ))

    PresetLibrary.register('genspark', WhitelabelConfig(
        network_name="GensparkChain",
        network_slug="genspark-chain",
        token_name="GensparkToken",
        token_symbol="GSPK",
        partner_name="Genspark",
        partner_website="https://genspark.ai",
        brand=BrandPreset(
            primary_color="#FF6B35",
            secondary_color="#FF8C5A",
            accent_color="#FFB899",
            background_dark="#1A0E08",
        ),
    ))

    PresetLibrary.register('youcom', WhitelabelConfig(
        network_name="YouChain",
        network_slug="you-chain",
        token_name="YouToken",
        token_symbol="YOU",
        partner_name="You.com",
        partner_website="https://you.com",
        brand=BrandPreset(
            primary_color="#5B4FE9",
            secondary_color="#7C6FF7",
            accent_color="#B8AFFF",
            background_dark="#0E0C1E",
        ),
    ))

    PresetLibrary.register('phind', WhitelabelConfig(
        network_name="PhindChain",
        network_slug="phind-chain",
        token_name="PhindToken",
        token_symbol="PHIND",
        partner_name="Phind",
        partner_website="https://phind.com",
        brand=BrandPreset(
            primary_color="#44D62C",
            secondary_color="#5AE640",
            accent_color="#A0F090",
            background_dark="#081A06",
        ),
    ))

    PresetLibrary.register('consensus', WhitelabelConfig(
        network_name="ConsensusChain",
        network_slug="consensus-chain",
        token_name="ConsensusToken",
        token_symbol="CSNS",
        partner_name="Consensus",
        partner_website="https://consensus.app",
        brand=BrandPreset(
            primary_color="#6366F1",
            secondary_color="#818CF8",
            accent_color="#C7D2FE",
            background_dark="#0E0E1C",
        ),
    ))

    PresetLibrary.register('semanticscholar', WhitelabelConfig(
        network_name="S2Chain",
        network_slug="s2-chain",
        token_name="S2Token",
        token_symbol="S2",
        partner_name="Semantic Scholar",
        partner_website="https://semanticscholar.org",
        brand=BrandPreset(
            primary_color="#1857B6",
            secondary_color="#2196F3",
            accent_color="#90CAF9",
            background_dark="#0A1220",
        ),
    ))

    PresetLibrary.register('elicit', WhitelabelConfig(
        network_name="ElicitChain",
        network_slug="elicit-chain",
        token_name="ElicitToken",
        token_symbol="ELIC",
        partner_name="Elicit",
        partner_website="https://elicit.com",
        brand=BrandPreset(
            primary_color="#5C4DFF",
            secondary_color="#7C6FFF",
            accent_color="#B8ADFF",
            background_dark="#0D0B1E",
        ),
    ))

    PresetLibrary.register('scite', WhitelabelConfig(
        network_name="SciteChain",
        network_slug="scite-chain",
        token_name="SciteToken",
        token_symbol="SCITE",
        partner_name="Scite",
        partner_website="https://scite.ai",
        brand=BrandPreset(
            primary_color="#F97316",
            secondary_color="#FB923C",
            accent_color="#FDBA74",
            background_dark="#1A100A",
        ),
    ))

    PresetLibrary.register('notebooklm', WhitelabelConfig(
        network_name="NotebookChain",
        network_slug="notebook-chain",
        token_name="NotebookToken",
        token_symbol="NBLM",
        partner_name="Google NotebookLM",
        partner_website="https://notebooklm.google",
        brand=BrandPreset(
            primary_color="#4285F4",
            secondary_color="#FBBC05",
            accent_color="#34A853",
            background_dark="#0D1117",
        ),
    ))

    PresetLibrary.register('researchrabbit', WhitelabelConfig(
        network_name="RabbitChain",
        network_slug="rabbit-chain",
        token_name="RabbitToken",
        token_symbol="RABBIT",
        partner_name="Research Rabbit",
        partner_website="https://researchrabbit.ai",
        brand=BrandPreset(
            primary_color="#6C63FF",
            secondary_color="#8B83FF",
            accent_color="#B8B3FF",
            background_dark="#0F0D1E",
        ),
    ))

    # === Automation & Agents (10) ===
    PresetLibrary.register('zapier_ai', WhitelabelConfig(
        network_name="ZapierChain",
        network_slug="zapier-chain",
        token_name="ZapToken",
        token_symbol="ZAP",
        partner_name="Zapier AI",
        partner_website="https://zapier.com",
        brand=BrandPreset(
            primary_color="#FF4A00",
            secondary_color="#FF6A2A",
            accent_color="#FF9A6C",
            background_dark="#1A0E06",
        ),
    ))

    PresetLibrary.register('make', WhitelabelConfig(
        network_name="MakeChain",
        network_slug="make-chain",
        token_name="MakeToken",
        token_symbol="MAKE",
        partner_name="Make (Integromat)",
        partner_website="https://make.com",
        brand=BrandPreset(
            primary_color="#7B61FF",
            secondary_color="#9B85FF",
            accent_color="#C5B8FF",
            background_dark="#0E0B1E",
        ),
    ))

    PresetLibrary.register('n8n', WhitelabelConfig(
        network_name="N8NChain",
        network_slug="n8n-chain",
        token_name="N8NToken",
        token_symbol="N8N",
        partner_name="n8n",
        partner_website="https://n8n.io",
        brand=BrandPreset(
            primary_color="#FF6D5A",
            secondary_color="#FF8A7A",
            accent_color="#FFB8AE",
            background_dark="#1A0C0A",
        ),
    ))

    PresetLibrary.register('auto_gpt', WhitelabelConfig(
        network_name="AutoGPTChain",
        network_slug="autogpt-chain",
        token_name="AutoGPTToken",
        token_symbol="AGPT",
        partner_name="AutoGPT / Significant Gravitas",
        partner_website="https://agpt.co",
        brand=BrandPreset(
            primary_color="#E040FB",
            secondary_color="#EA80FC",
            accent_color="#F3B4FF",
            background_dark="#1A0A1E",
        ),
    ))

    PresetLibrary.register('crewai', WhitelabelConfig(
        network_name="CrewChain",
        network_slug="crew-chain",
        token_name="CrewToken",
        token_symbol="CREW",
        partner_name="CrewAI",
        partner_website="https://crewai.com",
        brand=BrandPreset(
            primary_color="#7C3AED",
            secondary_color="#8B5CF6",
            accent_color="#C4B5FD",
            background_dark="#0F0A1E",
        ),
    ))

    PresetLibrary.register('langchain', WhitelabelConfig(
        network_name="LangChain Net",
        network_slug="langchain-net",
        token_name="LangToken",
        token_symbol="LANG",
        partner_name="LangChain",
        partner_website="https://langchain.com",
        brand=BrandPreset(
            primary_color="#1C3C3C",
            secondary_color="#2C5C5C",
            accent_color="#4CE0D2",
            background_dark="#0A1A1A",
        ),
    ))

    PresetLibrary.register('autogen', WhitelabelConfig(
        network_name="AutoGenChain",
        network_slug="autogen-chain",
        token_name="AutoGenToken",
        token_symbol="AGEN",
        partner_name="Microsoft AutoGen",
        partner_website="https://microsoft.github.io/autogen",
        brand=BrandPreset(
            primary_color="#00BCF2",
            secondary_color="#0364B8",
            accent_color="#50E6FF",
            background_dark="#061820",
        ),
    ))

    PresetLibrary.register('huggingface', WhitelabelConfig(
        network_name="HFCChain",
        network_slug="hfc-chain",
        token_name="HFToken",
        token_symbol="HF",
        partner_name="Hugging Face",
        partner_website="https://huggingface.co",
        brand=BrandPreset(
            primary_color="#FFD21E",
            secondary_color="#FFEA63",
            accent_color="#FFF3A0",
            background_dark="#1A1608",
            text_primary="#1A1A1A",
        ),
    ))

    PresetLibrary.register('smithery', WhitelabelConfig(
        network_name="SmitheryChain",
        network_slug="smithery-chain",
        token_name="SmitheryToken",
        token_symbol="SMTH",
        partner_name="Smithery",
        partner_website="https://smithery.ai",
        brand=BrandPreset(
            primary_color="#6D28D9",
            secondary_color="#7C3AED",
            accent_color="#A78BFA",
            background_dark="#0C0818",
        ),
    ))

    PresetLibrary.register('composio', WhitelabelConfig(
        network_name="ComposioChain",
        network_slug="composio-chain",
        token_name="ComposioToken",
        token_symbol="COMP",
        partner_name="Composio",
        partner_website="https://composio.dev",
        brand=BrandPreset(
            primary_color="#0EA5E9",
            secondary_color="#38BDF8",
            accent_color="#7DD3FC",
            background_dark="#081820",
        ),
    ))

    # === Voice & Audio (10) ===
    PresetLibrary.register('whisper', WhitelabelConfig(
        network_name="WhisperChain",
        network_slug="whisper-chain",
        token_name="WhisperToken",
        token_symbol="WHSP",
        partner_name="OpenAI Whisper",
        partner_website="https://openai.com/research/whisper",
        brand=BrandPreset(
            primary_color="#10A37F",
            secondary_color="#1D7A5F",
            accent_color="#6EE7B7",
            background_dark="#0A0F0D",
        ),
    ))

    PresetLibrary.register('assemblyai', WhitelabelConfig(
        network_name="AssemblyChain",
        network_slug="assembly-chain",
        token_name="AssemblyToken",
        token_symbol="ASM",
        partner_name="AssemblyAI",
        partner_website="https://assemblyai.com",
        brand=BrandPreset(
            primary_color="#6C5CE7",
            secondary_color="#A29BFE",
            accent_color="#DFE6E9",
            background_dark="#0E0C1E",
        ),
    ))

    PresetLibrary.register('deepgram', WhitelabelConfig(
        network_name="DeepgramChain",
        network_slug="deepgram-chain",
        token_name="DeepgramToken",
        token_symbol="DG",
        partner_name="Deepgram",
        partner_website="https://deepgram.com",
        brand=BrandPreset(
            primary_color="#13EF93",
            secondary_color="#00C9FF",
            accent_color="#92FE9D",
            background_dark="#041A10",
        ),
    ))

    PresetLibrary.register('speechmatics', WhitelabelConfig(
        network_name="SpeechmaticsChain",
        network_slug="speechmatics-chain",
        token_name="SpeechToken",
        token_symbol="SPCH",
        partner_name="Speechmatics",
        partner_website="https://speechmatics.com",
        brand=BrandPreset(
            primary_color="#E11D48",
            secondary_color="#F43F5E",
            accent_color="#FDA4AF",
            background_dark="#1A0A0E",
        ),
    ))

    PresetLibrary.register('lovo', WhitelabelConfig(
        network_name="LovoChain",
        network_slug="lovo-chain",
        token_name="LovoToken",
        token_symbol="LOVO",
        partner_name="LOVO AI",
        partner_website="https://lovo.ai",
        brand=BrandPreset(
            primary_color="#7C3AED",
            secondary_color="#8B5CF6",
            accent_color="#C4B5FD",
            background_dark="#0F0A1E",
        ),
    ))

    PresetLibrary.register('murf', WhitelabelConfig(
        network_name="MurfChain",
        network_slug="murf-chain",
        token_name="MurfToken",
        token_symbol="MURF",
        partner_name="Murf AI",
        partner_website="https://murf.ai",
        brand=BrandPreset(
            primary_color="#4F46E5",
            secondary_color="#6366F1",
            accent_color="#A5B4FC",
            background_dark="#0E0D1A",
        ),
    ))

    PresetLibrary.register('descript', WhitelabelConfig(
        network_name="DescriptChain",
        network_slug="descript-chain",
        token_name="DescriptToken",
        token_symbol="DESC",
        partner_name="Descript",
        partner_website="https://descript.com",
        brand=BrandPreset(
            primary_color="#7C3AED",
            secondary_color="#A78BFA",
            accent_color="#DDD6FE",
            background_dark="#0F0A1E",
        ),
    ))

    PresetLibrary.register('resemble', WhitelabelConfig(
        network_name="ResembleChain",
        network_slug="resemble-chain",
        token_name="ResembleToken",
        token_symbol="RSM",
        partner_name="Resemble AI",
        partner_website="https://resemble.ai",
        brand=BrandPreset(
            primary_color="#0EA5E9",
            secondary_color="#38BDF8",
            accent_color="#7DD3FC",
            background_dark="#081820",
        ),
    ))

    PresetLibrary.register('playht', WhitelabelConfig(
        network_name="PlayHTChain",
        network_slug="playht-chain",
        token_name="PlayHTToken",
        token_symbol="PHT",
        partner_name="PlayHT",
        partner_website="https://play.ht",
        brand=BrandPreset(
            primary_color="#2563EB",
            secondary_color="#3B82F6",
            accent_color="#93C5FD",
            background_dark="#0A1228",
        ),
    ))

    PresetLibrary.register('wellsaid', WhitelabelConfig(
        network_name="WellsaidChain",
        network_slug="wellsaid-chain",
        token_name="WellsaidToken",
        token_symbol="WST",
        partner_name="WellSaid Labs",
        partner_website="https://wellsaidlabs.com",
        brand=BrandPreset(
            primary_color="#059669",
            secondary_color="#10B981",
            accent_color="#6EE7B7",
            background_dark="#041A12",
        ),
    ))

    # === Multi-Modal (10) ===
    PresetLibrary.register('gpt4o', WhitelabelConfig(
        network_name="GPT4oChain",
        network_slug="gpt4o-chain",
        token_name="GPT4oToken",
        token_symbol="G4O",
        partner_name="OpenAI GPT-4o",
        partner_website="https://openai.com/gpt-4o",
        brand=BrandPreset(
            primary_color="#10A37F",
            secondary_color="#1D7A5F",
            accent_color="#6EE7B7",
            background_dark="#0A0F0D",
        ),
    ))

    PresetLibrary.register('gemini_pro', WhitelabelConfig(
        network_name="GeminiProChain",
        network_slug="gemini-pro-chain",
        token_name="GeminiProToken",
        token_symbol="GPRO",
        partner_name="Google Gemini Pro",
        partner_website="https://deepmind.google/technologies/gemini",
        brand=BrandPreset(
            primary_color="#4285F4",
            secondary_color="#34A853",
            accent_color="#FBBC05",
            background_dark="#0D1117",
        ),
    ))

    PresetLibrary.register('claude_vision', WhitelabelConfig(
        network_name="ClaudeVisionChain",
        network_slug="claude-vision-chain",
        token_name="ClaudeVisionToken",
        token_symbol="CLVIS",
        partner_name="Anthropic Claude Vision",
        partner_website="https://anthropic.com/claude",
        brand=BrandPreset(
            primary_color="#D4A574",
            secondary_color="#C4956A",
            accent_color="#E8C9A0",
            background_dark="#1A1612",
        ),
    ))

    PresetLibrary.register('sora', WhitelabelConfig(
        network_name="SoraChain",
        network_slug="sora-chain",
        token_name="SoraToken",
        token_symbol="SORA",
        partner_name="OpenAI Sora",
        partner_website="https://openai.com/sora",
        brand=BrandPreset(
            primary_color="#FF3366",
            secondary_color="#FF6B8A",
            accent_color="#FFB3C6",
            background_dark="#1A0A10",
        ),
    ))

    PresetLibrary.register('gemini_flash', WhitelabelConfig(
        network_name="GeminiFlashChain",
        network_slug="gemini-flash-chain",
        token_name="FlashToken",
        token_symbol="GFLASH",
        partner_name="Google Gemini Flash",
        partner_website="https://deepmind.google",
        brand=BrandPreset(
            primary_color="#00BCD4",
            secondary_color="#26C6DA",
            accent_color="#80DEEA",
            background_dark="#0A181B",
        ),
    ))

    PresetLibrary.register('meta_ai', WhitelabelConfig(
        network_name="MetaAIChain",
        network_slug="meta-ai-chain",
        token_name="MetaAIToken",
        token_symbol="META",
        partner_name="Meta AI",
        partner_website="https://meta.ai",
        brand=BrandPreset(
            primary_color="#0668E1",
            secondary_color="#1877F2",
            accent_color="#00C853",
            background_dark="#0A1628",
        ),
    ))

    PresetLibrary.register('pi', WhitelabelConfig(
        network_name="PiChain",
        network_slug="pi-chain",
        token_name="PiToken",
        token_symbol="PI",
        partner_name="Inflection AI / Pi",
        partner_website="https://pi.ai",
        brand=BrandPreset(
            primary_color="#6366F1",
            secondary_color="#818CF8",
            accent_color="#C7D2FE",
            background_dark="#0E0E1C",
        ),
    ))

    PresetLibrary.register('character_ai', WhitelabelConfig(
        network_name="CharacterChain",
        network_slug="character-chain",
        token_name="CharToken",
        token_symbol="CHAR",
        partner_name="Character.ai",
        partner_website="https://character.ai",
        brand=BrandPreset(
            primary_color="#7C3AED",
            secondary_color="#8B5CF6",
            accent_color="#DDD6FE",
            background_dark="#0F0A1E",
        ),
    ))

    PresetLibrary.register('poe', WhitelabelConfig(
        network_name="PoeChain",
        network_slug="poe-chain",
        token_name="PoeToken",
        token_symbol="POE",
        partner_name="Poe (Quora)",
        partner_website="https://poe.com",
        brand=BrandPreset(
            primary_color="#5B21B6",
            secondary_color="#7C3AED",
            accent_color="#A78BFA",
            background_dark="#0E0A1E",
        ),
    ))

    PresetLibrary.register('moltbook', WhitelabelConfig(
        network_name="MoltbookChain",
        network_slug="moltbook-chain",
        token_name="MoltToken",
        token_symbol="MOLT",
        partner_name="Moltbook",
        partner_website="https://moltbook.com",
        brand=BrandPreset(
            primary_color="#F59E0B",
            secondary_color="#FBBF24",
            accent_color="#FDE68A",
            background_dark="#1A1408",
        ),
        moltbook_audience="moltbook.chain",
    ))

    # === Special / Defaults ===
    PresetLibrary.register('baitcoin', WhitelabelConfig(
        network_name="b'AI'tcoin",
        network_slug="baitcoin",
        token_name="BAIT",
        token_symbol="BAIT",
        partner_name="Nexus-HUB57",
        partner_website="https://github.com/Nexus-HUB57",
    ))

    PresetLibrary.register('testnet', WhitelabelConfig(
        network_name="b'AI'tcoin Testnet",
        network_slug="baitcoin-testnet",
        token_name="tBAIT",
        token_symbol="tBAIT",
        partner_name="Nexus-HUB57",
        network_preset=NetworkPreset.TESTNET,
        faucet_claim_amount=100.0,
        faucet_max_per_agent=10000.0,
        faucet_cooldown_seconds=60,
        environment="testnet",
    ))


# Auto-initialize on import
_init_presets()
