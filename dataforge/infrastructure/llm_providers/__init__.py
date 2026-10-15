"""LLM provider implementations."""

from dataforge.core.llm import LLMProviderFactory

# Try to import and register OpenAI provider
try:
    from dataforge.infrastructure.llm_providers.openai import OpenAIProvider

    LLMProviderFactory.register("openai", OpenAIProvider)
    _openai_available = True
except ImportError:
    _openai_available = False
    OpenAIProvider = None

# Try to import and register Anthropic provider
try:
    from dataforge.infrastructure.llm_providers.anthropic import AnthropicProvider

    LLMProviderFactory.register("anthropic", AnthropicProvider)
    _anthropic_available = True
except ImportError:
    _anthropic_available = False
    AnthropicProvider = None

__all__ = []

if OpenAIProvider is not None:
    __all__.append("OpenAIProvider")
if AnthropicProvider is not None:
    __all__.append("AnthropicProvider")


def llm_from_env():
    """Build an LLM provider from environment variables, or None if unconfigured.

    ``LLM_PROVIDER`` picks the vendor (``anthropic`` | ``openai``); when unset,
    the first vendor with an API key wins (Anthropic first). ``LLM_MODEL``
    overrides the vendor's default model. ``DATAFORGE_DISABLE_LLM=1`` forces
    the deterministic (rule-based) path.
    """
    import os

    from dataforge.core.llm import LLMConfig

    if os.getenv("DATAFORGE_DISABLE_LLM", "").strip() in ("1", "true", "yes"):
        return None

    keys = {
        "anthropic": os.getenv("ANTHROPIC_API_KEY", "").strip(),
        "openai": os.getenv("OPENAI_API_KEY", "").strip(),
    }
    defaults = {"anthropic": "claude-opus-5-5", "openai": "gpt-4o"}
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if not provider:
        provider = next((name for name, key in keys.items() if key), "")
    if provider not in keys or not keys[provider] or not LLMProviderFactory.is_registered(provider):
        return None

    config = LLMConfig(
        provider=provider,
        model=os.getenv("LLM_MODEL", "").strip() or defaults[provider],
        api_key=keys[provider],
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "16000")),
        timeout=int(os.getenv("LLM_TIMEOUT", "120")),
    )
    try:
        return LLMProviderFactory.create(config)
    except Exception:
        return None


__all__.append("llm_from_env")
