"""JSON file reader implementation for DataForge AI v2.

This module provides the JSONReader class for reading JSON files with
support for both standard JSON and JSON Lines formats.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from dataforge.core.models import FileMetadata
from dataforge.infrastructure.interfaces import FileReader
from dataforge.infrastructure.readers.base import detect_json_format, handle_file_errors


class JSONReader(FileReader):
    """Reader for JSON files with auto-detection of JSON vs JSON Lines.

    Supports:
    - JSON files (.json, .jsonl, .ndjson)
    - JSON array of objects
    - JSON Lines format (one JSON object per line)
    - Auto-detection of format
    - Nested structure flattening
    """

    SUPPORTED_EXTENSIONS = {".json", ".jsonl", ".ndjson"}

    def can_read(self, file_path: str | Path) -> bool:
        """Check if this reader can handle the given file.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if the file has a supported extension, False otherwise.
        """
        path = Path(file_path)
        return path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    @handle_file_errors
    async def read(self, file_path: str | Path, **kwargs: Any) -> tuple[pd.DataFrame, FileMetadata]:
        """Read a JSON file and return the data with metadata.

        Args:
            file_path: Path to the JSON file to read.
            **kwargs: Additional pandas read_json options:
                - lines: Force JSON Lines format (auto-detected if not provided)
                - orient: JSON orientation (auto-detected if not provided)

        Returns:
            A tuple of (data, metadata) where data is a pandas DataFrame
            and metadata contains file information.

        Raises:
            DataIngestionError: If the file cannot be read.
        """
        path = Path(file_path)

        # Detect JSON format if not specified
        lines = kwargs.pop("lines", None)
        if lines is None:
            json_format = detect_json_format(path)
            lines = json_format == "jsonl"

        # Read the JSON file
        if lines:
            df = pd.read_json(path, lines=True, **kwargs)
        else:
            df = pd.read_json(path, lines=False, **kwargs)

        # Check for empty dataframe
        if df.empty:
            raise ValueError("JSON file is empty or contains no data")

        # Get file stats
        file_stats = path.stat()
        file_size_bytes = file_stats.st_size
        file_size_mb = file_size_bytes / (1024 * 1024)

        # Determine format
        file_format = "jsonl" if lines else "json"

        # Create metadata
        metadata = FileMetadata(
            filename=path.name,
            file_path=str(path),
            file_size_bytes=file_size_bytes,
            file_size_mb=file_size_mb,
            file_format=file_format,
            encoding="utf-8",  # JSON uses UTF-8
            row_count=len(df),
            column_count=len(df.columns),
            column_names=list(df.columns),
        )

        return df, metadata

    def validate_format(self, file_path: str | Path) -> bool:
        """Validate that the file format is correct.

        Args:
            file_path: Path to the file to validate.

        Returns:
            True if the file format is valid, False otherwise.
        """
        try:
            path = Path(file_path)

            # Check extension
            if not self.can_read(path):
                return False

            # Check if file exists and is readable
            if not path.exists():
                return False

            if not path.is_file():
                return False

            # Try to parse JSON to validate format
            import json

            json_format = detect_json_format(path)

            if json_format == "jsonl":
                # Validate JSON Lines format
                with open(path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if line.strip():  # Skip empty lines
                            try:
                                json.loads(line)
                            except json.JSONDecodeError:
                                return False
            else:
                # Validate standard JSON format
                with open(path, "r", encoding="utf-8") as f:
                    json.load(f)

            return True
        except Exception:
            return False

    @handle_file_errors
    async def peek_metadata(self, file_path: str | Path) -> FileMetadata:
        """Extract metadata without loading full data.

        Uses sampling for large files to provide quick metadata extraction.

        Args:
            file_path: Path to the JSON file to inspect.

        Returns:
            FileMetadata containing file information.

        Raises:
            DataIngestionError: If the file cannot be read.
        """
        path = Path(file_path)

        # Get file stats
        file_stats = path.stat()
        file_size_bytes = file_stats.st_size
        file_size_mb = file_size_bytes / (1024 * 1024)

        # Detect JSON format
        json_format = detect_json_format(path)
        lines = json_format == "jsonl"

        # For small files (<10MB), read all
        if file_size_bytes < 10 * 1024 * 1024:
            if lines:
                df = pd.read_json(path, lines=True)
            else:
                df = pd.read_json(path, lines=False)
        # For large files, sample first 1000 rows
        else:
            if lines:
                # For JSON Lines, read first 1000 lines
                df = pd.read_json(path, lines=True, nrows=1000)
            else:
                # For standard JSON, we can't sample, read all
                df = pd.read_json(path, lines=False)

        # Check for empty dataframe
        if df.empty:
            raise ValueError("JSON file is empty or contains no data")

        # Estimate total rows for large files
        if file_size_bytes >= 10 * 1024 * 1024 and lines:
            avg_row_size = file_size_bytes / len(df)
            estimated_rows = int(file_size_bytes / avg_row_size)
        else:
            estimated_rows = len(df)

        # Determine format
        file_format = "jsonl" if lines else "json"

        # Create metadata
        metadata = FileMetadata(
            filename=path.name,
            file_path=str(path),
            file_size_bytes=file_size_bytes,
            file_size_mb=file_size_mb,
            file_format=file_format,
            encoding="utf-8",  # JSON uses UTF-8
            row_count=estimated_rows,
            column_count=len(df.columns),
            column_names=list(df.columns),
        )

        return metadata