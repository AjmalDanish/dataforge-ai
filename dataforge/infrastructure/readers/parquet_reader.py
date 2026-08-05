"""Parquet file reader implementation for DataForge AI v2.

This module provides the ParquetReader class for reading Parquet files
with PyArrow backend and robust error handling.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from dataforge.core.models import FileMetadata
from dataforge.infrastructure.interfaces import FileReader
from dataforge.infrastructure.readers.base import handle_file_errors


class ParquetReader(FileReader):
    """Reader for Parquet files with PyArrow backend.

    Supports:
    - Parquet files (.parquet)
    - PyArrow backend
    - Column pruning via kwargs
    - Schema preservation
    """

    SUPPORTED_EXTENSIONS = {".parquet"}

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
        """Read a Parquet file and return the data with metadata.

        Args:
            file_path: Path to the Parquet file to read.
            **kwargs: Additional pandas read_parquet options:
                - columns: List of columns to read (column pruning)
                - engine: Parquet engine (default: 'pyarrow')

        Returns:
            A tuple of (data, metadata) where data is a pandas DataFrame
            and metadata contains file information.

        Raises:
            DataIngestionError: If the file cannot be read.
        """
        path = Path(file_path)

        # Set default engine to pyarrow
        kwargs.setdefault("engine", "pyarrow")

        # Read the Parquet file
        df = pd.read_parquet(path, **kwargs)

        # Check for empty dataframe
        if df.empty:
            raise ValueError("Parquet file is empty or contains no data")

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
            file_format="parquet",
            encoding="utf-8",  # Parquet uses UTF-8 for strings
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

            # Try to read schema to validate format
            try:
                import pyarrow.parquet as pq

                pq.read_schema(path)
                return True
            except Exception:
                # Fallback: try to read with pandas
                try:
                    pd.read_parquet(path, engine="pyarrow", nrows=1)
                    return True
                except Exception:
                    return False
        except Exception:
            return False

    @handle_file_errors
    async def peek_metadata(self, file_path: str | Path) -> FileMetadata:
        """Extract metadata without loading full data.

        Uses Parquet metadata for efficient extraction.

        Args:
            file_path: Path to the Parquet file to inspect.

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

        # Try to get metadata from Parquet file
        try:
            import pyarrow.parquet as pq

            parquet_file = pq.ParquetFile(path)

            # Get metadata from Parquet file
            row_count = parquet_file.metadata.num_rows
            column_names = parquet_file.metadata.schema.names
            column_count = len(column_names)

            # Create metadata
            metadata = FileMetadata(
                filename=path.name,
                file_path=str(path),
                file_size_bytes=file_size_bytes,
                file_size_mb=file_size_mb,
                file_format="parquet",
                encoding="utf-8",  # Parquet uses UTF-8 for strings
                row_count=row_count,
                column_count=column_count,
                column_names=column_names,
            )

            return metadata
        except Exception:
            # Fallback: read first few rows
            df = pd.read_parquet(path, engine="pyarrow", nrows=1000)

            # Check for empty dataframe
            if df.empty:
                raise ValueError("Parquet file is empty or contains no data")

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
                file_format="parquet",
                encoding="utf-8",  # Parquet uses UTF-8 for strings
                row_count=estimated_rows,
                column_count=len(df.columns),
                column_names=list(df.columns),
            )

            return metadata