"""Excel file reader implementation for DataForge AI v2.

This module provides the ExcelReader class for reading Excel files (.xlsx)
with support for multiple sheets and robust error handling.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from dataforge.core.models import FileMetadata
from dataforge.infrastructure.interfaces import FileReader
from dataforge.infrastructure.readers.base import handle_file_errors


class ExcelReader(FileReader):
    """Reader for Excel files with multi-sheet support.

    Supports:
    - Excel files (.xlsx, .xls)
    - Multiple sheets
    - Sheet selection via kwargs
    - Default to first sheet if not specified
    """

    SUPPORTED_EXTENSIONS = {".xlsx", ".xls"}

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
        """Read an Excel file and return the data with metadata.

        Args:
            file_path: Path to the Excel file to read.
            **kwargs: Additional pandas read_excel options:
                - sheet_name: Sheet name or index (default: 0)
                - header: Row number for header (default: 0)
                - nrows: Number of rows to read (for testing)

        Returns:
            A tuple of (data, metadata) where data is a pandas DataFrame
            and metadata contains file information.

        Raises:
            DataIngestionError: If the file cannot be read.
        """
        path = Path(file_path)

        # Get sheet name (default to first sheet)
        sheet_name = kwargs.pop("sheet_name", 0)

        # Read the Excel file
        df = pd.read_excel(path, sheet_name=sheet_name, **kwargs)

        # Check for empty dataframe
        if df.empty:
            raise ValueError("Excel file is empty or contains no data")

        # Get file stats
        file_stats = path.stat()
        file_size_bytes = file_stats.st_size
        file_size_mb = file_size_bytes / (1024 * 1024)

        # Get sheet names
        sheet_names = self._get_sheet_names(path)

        # Create metadata
        metadata = FileMetadata(
            filename=path.name,
            file_path=str(path),
            file_size_bytes=file_size_bytes,
            file_size_mb=file_size_mb,
            file_format="excel",
            encoding="utf-8",  # Excel files use UTF-8 internally
            row_count=len(df),
            column_count=len(df.columns),
            column_names=list(df.columns),
            sheet_names=sheet_names,
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

            # Try to read sheet names to validate format
            sheet_names = self._get_sheet_names(path)

            # Check if we have at least one sheet
            if not sheet_names:
                return False

            return True
        except Exception:
            return False

    @handle_file_errors
    async def peek_metadata(self, file_path: str | Path) -> FileMetadata:
        """Extract metadata without loading full data.

        Uses sampling for large files to provide quick metadata extraction.

        Args:
            file_path: Path to the Excel file to inspect.

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

        # Get sheet names
        sheet_names = self._get_sheet_names(path)

        # Get sheet name (default to first sheet)
        sheet_name = 0

        # For small files (<10MB), read all
        if file_size_bytes < 10 * 1024 * 1024:
            df = pd.read_excel(path, sheet_name=sheet_name, nrows=None)
        # For large files, sample first 1000 rows
        else:
            df = pd.read_excel(path, sheet_name=sheet_name, nrows=1000)

        # Check for empty dataframe
        if df.empty:
            raise ValueError("Excel file is empty or contains no data")

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
            file_format="excel",
            encoding="utf-8",  # Excel files use UTF-8 internally
            row_count=estimated_rows,
            column_count=len(df.columns),
            column_names=list(df.columns),
            sheet_names=sheet_names,
        )

        return metadata

    def _get_sheet_names(self, file_path: Path) -> list[str]:
        """Get all sheet names from an Excel file.

        Args:
            file_path: Path to the Excel file.

        Returns:
            List of sheet names.
        """
        try:
            import openpyxl

            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            return wb.sheetnames
        except Exception:
            # Fallback: try to read with pandas
            try:
                xl_file = pd.ExcelFile(file_path)
                return xl_file.sheet_names
            except Exception:
                return []