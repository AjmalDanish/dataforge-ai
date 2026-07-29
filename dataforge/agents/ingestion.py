"""Data Ingestion Agent - Read and parse structured data files."""

import os
from pathlib import Path
from typing import Literal

from dataforge.agents.base import Agent, AgentDecision, AgentResult
from dataforge.core.llm import LLMProvider
from dataforge.core.logger import StructuredLogger
from dataforge.core.state import GraphState


class DataIngestionAgent(Agent):
    """Agent for ingesting structured data files.

    Reads and validates CSV and Parquet files with:
    - Format detection (CSV, Parquet)
    - Encoding detection and fallback for CSV
    - Data validation
    - Error handling with clear messages

    Supported formats:
    - CSV (with automatic encoding detection: UTF-8, Latin-1, CP1252)
    - Parquet

    Error handling:
    - FileNotFoundError → Fatal error, halt workflow
    - PermissionError → Fatal error, halt workflow
    - EmptyDataError → Fatal error, halt workflow
    - EncodingError → Retry with alternate encodings
    """

    ENCODINGS = ["utf-8", "latin-1", "cp1252"]

    def __init__(
        self, llm_provider: LLMProvider | None = None, logger: StructuredLogger | None = None
    ):
        """Initialize the Data Ingestion Agent.

        Args:
            llm_provider: LLM provider instance.
            logger: Structured logger instance.
        """
        super().__init__(llm_provider, logger)

    async def execute(self, state: GraphState) -> AgentResult:
        """Ingest the dataset file.

        Args:
            state: Current graph state.

        Returns:
            AgentResult with loaded data or error information.
        """
        file_path = state.input_dataset_path
        path = Path(file_path)

        self.logger.info(
            "Starting data ingestion",
            agent=self.name,
            file_path=file_path,
            file_size_bytes=os.path.getsize(file_path) if path.exists() else 0,
        )

        # Validate path
        validation_result = self._validate_path(path)
        if validation_result is not None:
            return validation_result

        # Detect format
        file_format = self._detect_format(path)

        try:
            # Read file with encoding fallback for CSV
            if file_format == "csv":
                df = await self._read_csv_with_retry(path)
            else:  # parquet
                df = self._read_parquet(path)

            # Validate DataFrame
            validation_result = self._validate_dataframe(df)
            if validation_result is not None:
                return validation_result

            self.logger.info(
                "Data loaded successfully",
                agent=self.name,
                rows=len(df),
                columns=len(df.columns),
                file_size_bytes=os.path.getsize(file_path),
                format=file_format,
            )

            return AgentResult(
                decision=AgentDecision.CONTINUE,
                message=f"Loaded {len(df)} rows, {len(df.columns)} columns",
                data_updates={
                    "raw_data": df,
                    "file_format": file_format,
                    "original_file_size": os.path.getsize(file_path),
                    "load_timestamp": self._get_timestamp(),
                },
                metadata={
                    "rows": len(df),
                    "columns": len(df.columns),
                    "file_format": file_format,
                    "file_size_bytes": os.path.getsize(file_path),
                },
            )

        except Exception as e:
            self.logger.error(
                "Data ingestion failed",
                agent=self.name,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"Failed to read file: {str(e)}",
                metadata={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

    def _validate_path(self, path: Path) -> AgentResult | None:
        """Validate file path exists and is readable.

        Args:
            path: Path object to validate.

        Returns:
            AgentResult with error if validation fails, None otherwise.
        """
        if not path.exists():
            self.logger.error("File not found", agent=self.name, path=str(path))
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"File not found: {path}",
                metadata={"error_type": "FileNotFoundError"},
            )

        if not path.is_file():
            self.logger.error("Path is not a file", agent=self.name, path=str(path))
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"Path is not a file: {path}",
                metadata={"error_type": "NotAFileError"},
            )

        if not os.access(path, os.R_OK):
            self.logger.error("Cannot read file", agent=self.name, path=str(path))
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"Cannot read file: {path}",
                metadata={"error_type": "PermissionError"},
            )

        return None

    def _detect_format(self, path: Path) -> Literal["csv", "parquet"]:
        """Detect file format from extension.

        Args:
            path: Path object.

        Returns:
            File format string.
        """
        ext = path.suffix.lower()
        if ext == ".csv":
            return "csv"
        elif ext in [".parquet", ".pq"]:
            return "parquet"
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    async def _read_csv_with_retry(self, path: Path):
        """Read CSV file with encoding fallback.

        Args:
            path: Path to CSV file.

        Returns:
            Pandas DataFrame.

        Raises:
            ValueError: If no encoding works.
        """
        import pandas as pd

        for encoding in self.ENCODINGS:
            try:
                df = pd.read_csv(path, encoding=encoding)
                self.logger.debug(
                    f"Successfully read with encoding: {encoding}",
                    agent=self.name,
                )
                return df
            except UnicodeDecodeError:
                self.logger.debug(
                    f"Failed with encoding {encoding}, trying next",
                    agent=self.name,
                )
                continue

        raise ValueError(f"Could not decode file with any encoding: {self.ENCODINGS}")

    def _read_parquet(self, path: Path):
        """Read Parquet file.

        Args:
            path: Path to Parquet file.

        Returns:
            Pandas DataFrame.
        """
        import pandas as pd

        return pd.read_parquet(path)

    def _validate_dataframe(self, df) -> AgentResult | None:
        """Validate DataFrame structure.

        Args:
            df: Pandas DataFrame to validate.

        Returns:
            AgentResult with error if validation fails, None otherwise.
        """
        if df.empty:
            self.logger.error("File is empty", agent=self.name)
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"File is empty",
                metadata={"error_type": "EmptyDataError"},
            )

        if len(df.columns) == 0:
            self.logger.error("No columns found", agent=self.name)
            return AgentResult(
                decision=AgentDecision.ERROR,
                message=f"No columns found in file",
                metadata={"error_type": "NoColumnsError"},
            )

        return None

    def _get_timestamp(self) -> str:
        """Get current UTC timestamp.

        Returns:
            ISO formatted timestamp.
        """
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()
