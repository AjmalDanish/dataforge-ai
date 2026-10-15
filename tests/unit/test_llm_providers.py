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


def _message(blocks, stop_reason="end_turn", stop_details=None):
    from types import SimpleNamespace as NS

    return NS(
        content=[NS(type=t, text=x) for t, x in blocks],
        model="claude-opus-5-5",
        usage=NS(input_tokens=10, output_tokens=5),
        stop_reason=stop_reason,
        stop_details=stop_details,
    )


@anthropic_skip
class TestAnthropicProvider:
    """AnthropicProvider against a mocked SDK client."""

    @pytest.fixture
    def provider(self):
        config = LLMConfig(provider="anthropic", model="claude-opus-5-5", api_key="test-key")
        return LLMProviderFactory.create(config)

    @pytest.mark.asyncio
    async def test_returns_text_blocks_only(self, provider) -> None:
        create = AsyncMock(return_value=_message([("thinking", ""), ("text", "hr")]))
        provider.client.beta.messages.create = create

        response = await provider.generate(
            [LLMMessage(role="system", content="sys"), LLMMessage(role="user", content="q")]
        )

        assert response.content == "hr"
        assert response.tokens_used == 15
        kwargs = create.call_args.kwargs
        assert kwargs["system"] == "sys"
        assert kwargs["messages"] == [{"role": "user", "content": "q"}]
        assert "temperature" not in kwargs  # rejected by current models
        assert kwargs["fallbacks"] == "default"
        assert kwargs["max_tokens"] >= 16000

    @pytest.mark.asyncio
    async def test_refusal_raises_provider_error(self, provider) -> None:
        from types import SimpleNamespace as NS

        provider.client.beta.messages.create = AsyncMock(
            return_value=_message([], stop_reason="refusal", stop_details=NS(category="cyber"))
        )
        with pytest.raises(LLMProviderError, match="declined"):
            await provider.generate([LLMMessage(role="user", content="q")])

    @pytest.mark.asyncio
    async def test_rate_limit_is_mapped(self, provider) -> None:
        import anthropic
        import httpx2

        request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
        error = anthropic.RateLimitError(
            "slow down", response=httpx2.Response(429, request=request), body=None
        )
        provider.client.beta.messages.create = AsyncMock(side_effect=error)
        with pytest.raises(LLMRateLimitError):
            await provider.generate([LLMMessage(role="user", content="q")])


class TestLLMFromEnv:
    """Provider selection from environment variables."""

    def test_none_without_keys(self, monkeypatch) -> None:
        from dataforge.infrastructure.llm_providers import llm_from_env

        for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "LLM_PROVIDER", "DATAFORGE_DISABLE_LLM"):
            monkeypatch.delenv(var, raising=False)
        assert llm_from_env() is None

    @anthropic_skip
    def test_prefers_anthropic_and_respects_disable(self, monkeypatch) -> None:
        from dataforge.infrastructure.llm_providers import llm_from_env

        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("LLM_MODEL", raising=False)
        monkeypatch.delenv("DATAFORGE_DISABLE_LLM", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "a-key")
        monkeypatch.setenv("OPENAI_API_KEY", "o-key")
        llm = llm_from_env()
        assert llm.provider_name == "anthropic"
        assert llm.config.model == "claude-opus-5-5"

        monkeypatch.setenv("LLM_PROVIDER", "openai")
        assert llm_from_env().provider_name == "openai"

        monkeypatch.setenv("DATAFORGE_DISABLE_LLM", "1")
        assert llm_from_env() is None
