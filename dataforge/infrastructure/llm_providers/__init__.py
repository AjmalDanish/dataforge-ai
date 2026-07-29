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
