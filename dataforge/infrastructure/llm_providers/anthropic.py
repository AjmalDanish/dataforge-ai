"""Anthropic LLM provider implementation."""

import asyncio
from typing import Any

try:
    import anthropic
    from anthropic import AsyncAnthropic
except ImportError:
    raise ImportError("Anthropic package is required. Install with: pip install anthropic")

from dataforge.core.llm import LLMConfig, LLMMessage, LLMProvider, LLMResponse
from dataforge.shared.errors import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
)


class AnthropicProvider(LLMProvider):
    """Anthropic implementation of LLM provider."""

    DEFAULT_MODELS = [
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    def __init__(self, config: LLMConfig):
        """Initialize the Anthropic provider.

        Args:
            config: LLM configuration.
        """
        super().__init__(config)

        if not config.api_key:
            raise LLMAuthenticationError(
                "Anthropic API key is required",
                {"provider": "anthropic"},
            )

        self.client = AsyncAnthropic(
            api_key=config.api_key,
            timeout=config.timeout,
            base_url=config.base_url,
        )

    async def generate(
        self, messages: list[LLMMessage], config: LLMConfig | None = None
    ) -> LLMResponse:
        """Generate a response from Anthropic.

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
            # Anthropic expects system message separate from messages
            system_message = None
            conversation_messages = []

            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    conversation_messages.append({"role": msg.role, "content": msg.content})

            response = await self.client.messages.create(
                model=effective_config.model,
                system=system_message,
                messages=conversation_messages,
                temperature=effective_config.temperature,
                max_tokens=effective_config.max_tokens,
            )

            return LLMResponse(
                content=response.content[0].text if response.content else "",
                model=response.model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                finish_reason=response.stop_reason,
                provider="anthropic",
            )

        except anthropic.AuthenticationError as e:
            raise LLMAuthenticationError(
                f"Anthropic authentication failed: {e}",
                self._extract_error_details(e),
            ) from e

        except anthropic.RateLimitError as e:
            raise LLMRateLimitError(
                f"Anthropic rate limit exceeded: {e}",
                self._extract_error_details(e),
            ) from e

        except anthropic.APITimeoutError as e:
            raise LLMConnectionError(
                f"Anthropic API timeout: {e}",
                self._extract_error_details(e),
            ) from e

        except anthropic.APIConnectionError as e:
            raise LLMConnectionError(
                f"Anthropic connection error: {e}",
                self._extract_error_details(e),
            ) from e

        except anthropic.APIError as e:
            raise LLMProviderError(
                f"Anthropic API error: {e}",
                self._extract_error_details(e),
            ) from e

        except Exception as e:
            raise LLMProviderError(
                f"Unexpected error: {e}",
                self._extract_error_details(e),
            ) from e

    def validate_config(self, config: LLMConfig) -> bool:
        """Validate Anthropic configuration.

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
        """Format messages for Anthropic API.

        Args:
            messages: List of LLM messages.

        Returns:
            Anthropic-formatted messages.
        """
        # Anthropic separates system message
        formatted = []
        for msg in messages:
            if msg.role != "system":
                formatted.append({"role": msg.role, "content": msg.content})
        return formatted

    def _extract_error_details(self, error: Exception) -> dict[str, Any]:
        """Extract error details from Anthropic exception.

        Args:
            error: Exception to extract from.

        Returns:
            Dictionary of error details.
        """
        details = super()._extract_error_details(error)

        # Add Anthropic-specific details if available
        if hasattr(error, "status_code"):
            details["status_code"] = error.status_code
        if hasattr(error, "error"):
            details["error"] = str(error.error)

        return details
