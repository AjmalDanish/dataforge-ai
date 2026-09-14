"""CSV file reader implementation for DataForge AI v2.

This module provides the CSVReader class for reading CSV files with
encoding detection, delimiter auto-detection, and robust error handling.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from dataforge.core.models import FileMetadata
from dataforge.infrastructure.interfaces import FileReader
from dataforge.infrastructure.readers.base import detect_encoding, handle_file_errors


class CSVReader(FileReader):
    """Reader for CSV files with encoding detection and delimiter auto-detection.

    Supports:
    - CSV files (.csv, .tsv, .txt)
    - Encoding detection with fallback (UTF-8 → Latin-1 → CP1252)
    - Delimiter auto-detection (comma, semicolon, tab, pipe)
    - Quoted fields
    - Various line endings (CRLF, LF, CR)
    """

    SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".txt"}

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
        """Read a CSV file and return the data with metadata.

        Args:
            file_path: Path to the CSV file to read.
            **kwargs: Additional pandas read_csv options:
                - encoding: File encoding (auto-detected if not provided)
                - delimiter: Field delimiter (auto-detected if not provided)
                - sheet_name: Not applicable for CSV
                - nrows: Number of rows to read (for testing)

        Returns:
            A tuple of (data, metadata) where data is a pandas DataFrame
            and metadata contains file information.

        Raises:
            DataIngestionError: If the file cannot be read.
        """
        path = Path(file_path)

        # Detect encoding if not provided
        encoding = kwargs.pop("encoding", None) or detect_encoding(path)

        # Detect delimiter if not provided
        delimiter = kwargs.pop("delimiter", None)
        if delimiter is None:
            delimiter = self._detect_delimiter(path, encoding)

        # Read the CSV file
        df = pd.read_csv(path, encoding=encoding, delimiter=delimiter, **kwargs)

        # Check for empty dataframe
        if df.empty:
            raise ValueError("CSV file is empty or contains no data")

        # Get file stats
        file_stats = path.stat()
        file_size_bytes = file_stats.st_size
        file_size_mb = file_size_bytes / (1024 * 1024)

        # Create metadata
        metadata = FileMetadata(
            filename=path.name,
            file_path=str(path),
            file_size_bytes=file_size_bytes,
            file_size_mb=file_size_mb,
            file_format="csv",
            encoding=encoding,
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

            # Try to read a few lines to validate format
            encoding = detect_encoding(path)
            delimiter = self._detect_delimiter(path, encoding)

            with open(path, "r", encoding=encoding) as f:
                # Read first few lines
                lines = [f.readline() for _ in range(5)]

                # Check if we have at least one line
                if not lines or not lines[0].strip():
                    return False

                # Check if delimiter is present in header
                if delimiter not in lines[0]:
                    return False

            return True
        except Exception:
            return False

    @handle_file_errors
    async def peek_metadata(self, file_path: str | Path) -> FileMetadata:
        """Extract metadata without loading full data.

        Uses sampling for large files to provide quick metadata extraction.

        Args:
            file_path: Path to the CSV file to inspect.

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

        # Detect encoding and delimiter
        encoding = detect_encoding(path)
        delimiter = self._detect_delimiter(path, encoding)

        # For small files (<10MB), read all
        if file_size_bytes < 10 * 1024 * 1024:
            df = pd.read_csv(path, encoding=encoding, delimiter=delimiter, nrows=None)
        # For large files, sample first 1000 rows
        else:
            df = pd.read_csv(path, encoding=encoding, delimiter=delimiter, nrows=1000)

        # Check for empty dataframe
        if df.empty:
            raise ValueError("CSV file is empty or contains no data")

        # Estimate total rows for large files
        if file_size_bytes >= 10 * 1024 * 1024:
            avg_row_size = file_size_bytes / len(df)
            estimated_rows = int(file_size_bytes / avg_row_size)
        else:
            estimated_rows = len(df)

        # Create metadata
        metadata = FileMetadata(
            filename=path.name,
            file_path=str(path),
            file_size_bytes=file_size_bytes,
            file_size_mb=file_size_mb,
            file_format="csv",
            encoding=encoding,
            row_count=estimated_rows,
            column_count=len(df.columns),
            column_names=list(df.columns),
        )

        return metadata

    def _detect_delimiter(self, file_path: Path, encoding: str) -> str:
        """Detect the delimiter used in a CSV file.

        Args:
            file_path: Path to the CSV file.
            encoding: File encoding.

        Returns:
            Detected delimiter character.
        """
        # Common delimiters to try
        delimiters = [",", ";", "\t", "|"]

        try:
            with open(file_path, "r", encoding=encoding) as f:
                first_line = f.readline()

                # Count occurrences of each delimiter
                delimiter_counts = {}
                for delim in delimiters:
                    delimiter_counts[delim] = first_line.count(delim)

                # Return the delimiter with the most occurrences
                if delimiter_counts:
                    return max(delimiter_counts, key=delimiter_counts.get)

        except Exception:
            pass

        # Default to comma
        return ","