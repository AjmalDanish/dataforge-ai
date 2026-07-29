"""OpenAI LLM provider implementation."""

import asyncio
from typing import Any

try:
    import openai
    from openai import AsyncOpenAI
except ImportError:
    raise ImportError("OpenAI package is required. Install with: pip install openai")

from dataforge.core.llm import LLMConfig, LLMMessage, LLMProvider, LLMResponse
from dataforge.shared.errors import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
)


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of LLM provider."""

    DEFAULT_MODELS = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]

    def __init__(self, config: LLMConfig):
        """Initialize the OpenAI provider.

        Args:
            config: LLM configuration.
        """
        super().__init__(config)

        if not config.api_key:
            raise LLMAuthenticationError(
                "OpenAI API key is required",
                {"provider": "openai"},
            )

        self.client = AsyncOpenAI(
            api_key=config.api_key,
            timeout=config.timeout,
            base_url=config.base_url,
        )

    async def generate(
        self, messages: list[LLMMessage], config: LLMConfig | None = None
    ) -> LLMResponse:
        """Generate a response from OpenAI.

        Args:
            messages: List of conversation messages.
            config: Optional config override.

        Returns:
            LLM response.

        Raises:
            LLMConnectionError: On connection errors.
            LLMAuthenticationError: On authentication errors.
            LLMRateLimitError: On rate limit errors.
            LLMProviderError: On other errors.
        """
        effective_config = config or self.config

        try:
            response = await self.client.chat.completions.create(
                model=effective_config.model,
                messages=self._format_messages(messages),
                temperature=effective_config.temperature,
                max_tokens=effective_config.max_tokens,
            )

            return LLMResponse(
                content=response.choices[0].message.content or "",
                model=response.model,
                tokens_used=response.usage.total_tokens if response.usage else None,
                finish_reason=response.choices[0].finish_reason,
                provider="openai",
            )

        except openai.AuthenticationError as e:
            raise LLMAuthenticationError(
                f"OpenAI authentication failed: {e}",
                self._extract_error_details(e),
            ) from e

        except openai.RateLimitError as e:
            raise LLMRateLimitError(
                f"OpenAI rate limit exceeded: {e}",
                self._extract_error_details(e),
            ) from e

        except openai.APITimeoutError as e:
            raise LLMConnectionError(
                f"OpenAI API timeout: {e}",
                self._extract_error_details(e),
            ) from e

        except openai.APIConnectionError as e:
            raise LLMConnectionError(
                f"OpenAI connection error: {e}",
                self._extract_error_details(e),
            ) from e

        except openai.APIError as e:
            raise LLMProviderError(
                f"OpenAI API error: {e}",
                self._extract_error_details(e),
            ) from e

        except Exception as e:
            raise LLMProviderError(
                f"Unexpected error: {e}",
                self._extract_error_details(e),
            ) from e

    def validate_config(self, config: LLMConfig) -> bool:
        """Validate OpenAI configuration.

        Args:
            config: Configuration to validate.

        Returns:
            True if valid.
        """
        if not config.api_key:
            return False

        if not config.model:
            return False

        return True

    def _format_messages(self, messages: list[LLMMessage]) -> list[dict[str, str]]:
        """Format messages for OpenAI API.

        Args:
            messages: List of LLM messages.

        Returns:
            OpenAI-formatted messages.
        """
        formatted = []
        for msg in messages:
            formatted.append({"role": msg.role, "content": msg.content})
        return formatted

    def _extract_error_details(self, error: Exception) -> dict[str, Any]:
        """Extract error details from OpenAI exception.

        Args:
            error: Exception to extract from.

        Returns:
            Dictionary of error details.
        """
        details = super()._extract_error_details(error)

        # Add OpenAI-specific details if available
        if hasattr(error, "status_code"):
            details["status_code"] = error.status_code
        if hasattr(error, "code"):
            details["error_code"] = error.code

        return details
