"""Tests for LLM providers."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from dataforge.core.llm import (
    LLMConfig,
    LLMMessage,
    LLMProviderFactory,
)
from dataforge.infrastructure.llm_providers import AnthropicProvider, OpenAIProvider
from dataforge.shared.errors import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
)

# Skip anthropic tests if package not available
if AnthropicProvider is None:
    anthropic_skip = pytest.mark.skip(reason="anthropic package not installed")
else:
    anthropic_skip = pytest.mark.skipif(False, reason="")


class TestLLMProviders:
    """Tests for LLM provider implementations."""

    def test_openai_provider_registration(self) -> None:
        """Test OpenAI provider is registered."""
        assert LLMProviderFactory.is_registered("openai")

    @anthropic_skip
    def test_anthropic_provider_registration(self) -> None:
        """Test Anthropic provider is registered."""
        assert LLMProviderFactory.is_registered("anthropic")

    def test_openai_requires_api_key(self) -> None:
        """Test OpenAI provider requires API key."""
        config = LLMConfig(provider="openai", model="gpt-4", api_key=None)

        with pytest.raises(LLMAuthenticationError):
            LLMProviderFactory.create(config)

    @anthropic_skip
    def test_anthropic_requires_api_key(self) -> None:
        """Test Anthropic provider requires API key."""
        config = LLMConfig(provider="anthropic", model="claude-3", api_key=None)

        with pytest.raises(LLMAuthenticationError):
            LLMProviderFactory.create(config)

    def test_openai_without_model(self) -> None:
        """Test OpenAI provider requires model."""
        config = LLMConfig(provider="openai", model="", api_key="test-key")

        with pytest.raises(LLMProviderError):
            LLMProviderFactory.create(config)

    def test_invalid_provider(self) -> None:
        """Test invalid provider raises error."""
        config = LLMConfig(provider="invalid", model="test", api_key="test-key")

        with pytest.raises(ValueError, match="Unknown provider"):
            LLMProviderFactory.create(config)

    @pytest.mark.asyncio
    async def test_provider_generate_signature(self) -> None:
        """Test provider generate method signature."""
        from dataforge.infrastructure.llm_providers import OpenAIProvider

        config = LLMConfig(provider="openai", model="gpt-4", api_key="test-key")
        provider = OpenAIProvider(config)

        messages = [LLMMessage(role="user", content="test")]

        # Should have async generate method
        assert hasattr(provider, "generate")
        assert callable(provider.generate)

        # Should have generate_with_retry method
        assert hasattr(provider, "generate_with_retry")
        assert callable(provider.generate_with_retry)

    def test_provider_validate_config(self) -> None:
        """Test provider config validation."""
        from dataforge.infrastructure.llm_providers import OpenAIProvider

        # Valid config
        valid_config = LLMConfig(provider="openai", model="gpt-4", api_key="test-key")
        provider = OpenAIProvider(valid_config)
        assert provider.validate_config(valid_config) is True

        # Invalid config (no api key)
        invalid_config = LLMConfig(provider="openai", model="gpt-4", api_key=None)
        provider2 = OpenAIProvider.__new__(OpenAIProvider)
        provider2.config = invalid_config
        assert provider2.validate_config(invalid_config) is False
