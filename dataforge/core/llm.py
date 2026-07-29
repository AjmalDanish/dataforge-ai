"""LLM provider interface and implementations."""

import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel

from dataforge.shared.errors import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
)

__all__ = [
    "LLMMessage",
    "LLMResponse",
    "LLMConfig",
    "LLMProvider",
    "LLMProviderFactory",
]


class LLMMessage(BaseModel):
    """Unified message format for all LLM providers."""

    role: str  # "system", "user", "assistant"
    content: str

    model_config = {"frozen": True}


class LLMResponse(BaseModel):
    """Unified response format for all LLM providers."""

    content: str
    model: str
    tokens_used: int | None = None
    finish_reason: str | None = None
    provider: str = "unknown"

    model_config = {"frozen": True}


class LLMConfig(BaseModel):
    """Configuration for LLM provider."""

    provider: str = "openai"  # "openai", "anthropic", "ollama", etc.
    model: str = "gpt-4"
    api_key: str | None = None
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: int = 30
    base_url: str | None = None  # For custom endpoints

    model_config = {"frozen": True}


class LLMProvider(ABC):
    """Abstract interface for all LLM providers.

    This interface eliminates vendor lock-in and allows easy
    addition of new providers (OpenAI, Anthropic, Ollama, etc.).
    """

    def __init__(self, config: LLMConfig):
        """Initialize the LLM provider.

        Args:
            config: LLM configuration.
        """
        self.config = config
        self.provider_name = config.provider

    @abstractmethod
    async def generate(
        self, messages: list[LLMMessage], config: LLMConfig | None = None
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            messages: List of conversation messages.
            config: Optional config override.

        Returns:
            LLM response with content and metadata.

        Raises:
            LLMProviderError: On generation errors.
            LLMAuthenticationError: On authentication failures.
            LLMRateLimitError: On rate limit errors.
            LLMConnectionError: On connection errors.
        """
        pass

    async def generate_with_retry(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
    ) -> LLMResponse:
        """Generate with automatic retry on transient failures.

        Args:
            messages: List of conversation messages.
            config: Optional config override.
            max_retries: Maximum retry attempts.
            initial_backoff: Initial backoff in seconds (exponential).

        Returns:
            LLM response.

        Raises:
            LLMProviderError: If all retries fail.
        """
        effective_config = config or self.config
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                return await self.generate(messages, effective_config)
            except (LLMRateLimitError, LLMConnectionError) as e:
                last_error = e
                if attempt < max_retries:
                    backoff = initial_backoff * (2**attempt)
                    await asyncio.sleep(backoff)
                continue
            except (LLMAuthenticationError, LLMProviderError) as e:
                # Don't retry authentication or provider errors
                raise

        # All retries exhausted
        if last_error:
            raise LLMProviderError(
                f"Failed after {max_retries} retries: {last_error}",
                {"attempts": max_retries + 1, "last_error": str(last_error)},
            ) from last_error

        raise LLMProviderError("Failed with unknown error")  # pragma: no cover

    def validate_config(self, config: LLMConfig) -> bool:
        """Validate provider configuration.

        Args:
            config: Configuration to validate.

        Returns:
            True if valid, False otherwise.
        """
        if not config.model:
            return False
        return True

    def _format_messages(self, messages: list[LLMMessage]) -> list[dict[str, str]]:
        """Format messages for provider-specific API.

        Args:
            messages: List of LLM messages.

        Returns:
            Provider-formatted messages.
        """
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    def _extract_error_details(self, error: Exception) -> dict[str, Any]:
        """Extract error details from exception.

        Args:
            error: Exception to extract details from.

        Returns:
            Dictionary of error details.
        """
        return {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "provider": self.provider_name,
        }


class LLMProviderFactory:
    """Factory for creating LLM providers.

    Supports dynamic provider registration for extensibility.
    """

    _providers: dict[str, type[LLMProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[LLMProvider]) -> None:
        """Register a new provider.

        Args:
            name: Provider name.
            provider_class: Provider class (subclass of LLMProvider).
        """
        if not issubclass(provider_class, LLMProvider):
            raise ValueError(f"Provider class must inherit from LLMProvider: {provider_class}")
        cls._providers[name.lower()] = provider_class

    @classmethod
    def create(cls, config: LLMConfig) -> LLMProvider:
        """Create provider instance from config.

        Args:
            config: LLM configuration.

        Returns:
            LLM provider instance.

        Raises:
            ValueError: If provider not found.
            LLMProviderError: If provider configuration is invalid.
        """
        provider_name = config.provider.lower()
        provider_class = cls._providers.get(provider_name)

        if provider_class is None:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown provider: {config.provider}. Available providers: {available}"
            )

        provider = provider_class(config)

        if not provider.validate_config(config):
            raise LLMProviderError(
                f"Invalid configuration for provider: {config.provider}",
                {"config": config.model_dump()},
            )

        return provider

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered providers.

        Returns:
            List of provider names.
        """
        return list(cls._providers.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a provider is registered.

        Args:
            name: Provider name.

        Returns:
            True if registered, False otherwise.
        """
        return name.lower() in cls._providers
