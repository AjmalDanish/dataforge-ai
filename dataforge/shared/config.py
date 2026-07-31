"""Configuration management for DataForge AI."""

import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()


class Settings(BaseModel):
    """Application settings."""

    # Application
    app_name: str = "DataForge AI"
    app_version: str = "0.1.0"
    debug: bool = False

    # LLM Configuration
    llm_provider: str = "openai"  # "openai" or "anthropic"
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1000
    llm_timeout: int = 30

    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # File Processing
    max_file_size_mb: int = 100
    max_rows: int = 1_000_000
    max_columns: int = 1_000
    supported_formats: list[str] = [".csv", ".parquet", ".pq"]

    # Execution
    max_retries: int = 3
    retry_backoff_base: int = 1  # seconds
    execution_timeout: int = 300  # 5 minutes

    # Output
    default_output_dir: str = "./output"
    log_format: str = "both"  # "console", "file", "both"

    # Visualization
    max_visualizations: int = 6
    visualization_width: int = 1200
    visualization_height: int = 800
    visualization_scale: int = 2
    visualization_dpi: int = 300

    model_config = {
        "extra": "ignore",
    }

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "openai"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4"),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000")),
            llm_timeout=int(os.getenv("LLM_TIMEOUT", "30")),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "100")),
            max_rows=int(os.getenv("MAX_ROWS", "1000000")),
            max_columns=int(os.getenv("MAX_COLUMNS", "1000")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            execution_timeout=int(os.getenv("EXECUTION_TIMEOUT", "300")),
            default_output_dir=os.getenv("DEFAULT_OUTPUT_DIR", "./output"),
            max_visualizations=int(os.getenv("MAX_VISUALIZATIONS", "6")),
        )


# Global settings instance
settings = Settings.from_env()


def get_output_dir(dataset_path: str) -> Path:
    """Get output directory for a dataset.

    Args:
        dataset_path: Path to the input dataset.

    Returns:
        Path object for the output directory.
    """
    dataset_name = Path(dataset_path).stem
    output_path = Path(settings.default_output_dir) / dataset_name
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path
