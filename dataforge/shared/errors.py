"""Custom exception classes for DataForge AI."""


class DataForgeError(Exception):
    """Base exception for all DataForge errors."""

    def __init__(self, message: str, details: dict | None = None):
        """Initialize the error.

        Args:
            message: Error message.
            details: Additional error details.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """String representation."""
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(DataForgeError):
    """Configuration related errors."""

    pass


class LLMProviderError(DataForgeError):
    """LLM provider related errors."""

    pass


class LLMConnectionError(LLMProviderError):
    """LLM connection failures."""

    pass


class LLMRateLimitError(LLMProviderError):
    """LLM rate limit exceeded."""

    pass


class LLMAuthenticationError(LLMProviderError):
    """LLM authentication failures."""

    pass


class DataIngestionError(DataForgeError):
    """Data ingestion errors."""

    pass


class DataValidationError(DataForgeError):
    """Data validation errors."""

    pass


class AgentExecutionError(DataForgeError):
    """Agent execution errors."""

    def __init__(
        self,
        agent_name: str,
        message: str,
        details: dict | None = None,
    ):
        """Initialize the agent execution error.

        Args:
            agent_name: Name of the agent that failed.
            message: Error message.
            details: Additional error details.
        """
        super().__init__(message, details)
        self.agent_name = agent_name


class GraphExecutionError(DataForgeError):
    """Graph workflow execution errors."""

    pass


class ValidationError(DataForgeError):
    """Validation errors."""

    pass
