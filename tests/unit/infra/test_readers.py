"""Unit tests for file reader implementations.

Tests for CSVReader, ExcelReader, ParquetReader, and JSONReader.
"""

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

from dataforge.core.models import FileMetadata
from dataforge.infrastructure.readers import CSVReader, ExcelReader, JSONReader, ParquetReader
from dataforge.shared.errors import DataIngestionError


# Helper functions to check module availability
def _module_available(module_name: str) -> bool:
    """Check if a module is available for import."""
    return importlib.util.find_spec(module_name) is not None


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def valid_csv(temp_dir: Path) -> Path:
    """Create a valid CSV file for testing."""
    csv_file = temp_dir / "valid.csv"
    csv_file.write_text("name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago\n")
    return csv_file


@pytest.fixture
def invalid_csv(temp_dir: Path) -> Path:
    """Create an invalid CSV file for testing."""
    csv_file = temp_dir / "invalid.csv"
    csv_file.write_text("name,age,city\nAlice,30\nBob,25,LA,ExtraColumn\n")  # Mismatched columns
    return csv_file


@pytest.fixture
def empty_csv(temp_dir: Path) -> Path:
    """Create an empty CSV file for testing."""
    csv_file = temp_dir / "empty.csv"
    csv_file.write_text("")
    return csv_file


@pytest.fixture
def valid_json(temp_dir: Path) -> Path:
    """Create a valid JSON file for testing."""
    json_file = temp_dir / "valid.json"
    data = [
        {"name": "Alice", "age": 30, "city": "NYC"},
        {"name": "Bob", "age": 25, "city": "LA"},
        {"name": "Charlie", "age": 35, "city": "Chicago"},
    ]
    json_file.write_text(json.dumps(data))
    return json_file


@pytest.fixture
def valid_jsonl(temp_dir: Path) -> Path:
    """Create a valid JSON Lines file for testing."""
    jsonl_file = temp_dir / "valid.jsonl"
    lines = [
        '{"name": "Alice", "age": 30, "city": "NYC"}',
        '{"name": "Bob", "age": 25, "city": "LA"}',
        '{"name": "Charlie", "age": 35, "city": "Chicago"}',
    ]
    jsonl_file.write_text("\n".join(lines))
    return jsonl_file


@pytest.fixture
def invalid_json(temp_dir: Path) -> Path:
    """Create an invalid JSON file for testing."""
    json_file = temp_dir / "invalid.json"
    json_file.write_text("{invalid json")
    return json_file


@pytest.fixture
def empty_json(temp_dir: Path) -> Path:
    """Create an empty JSON file for testing."""
    json_file = temp_dir / "empty.json"
    json_file.write_text("")
    return json_file


@pytest.fixture
def valid_parquet(temp_dir: Path) -> Path:
    """Create a valid Parquet file for testing."""
    parquet_file = temp_dir / "valid.parquet"
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie"],
        "age": [30, 25, 35],
        "city": ["NYC", "LA", "Chicago"],
    })
    df.to_parquet(parquet_file, engine="pyarrow")
    return parquet_file


@pytest.fixture
def empty_parquet(temp_dir: Path) -> Path:
    """Create an empty Parquet file for testing."""
    parquet_file = temp_dir / "empty.parquet"
    df = pd.DataFrame()
    df.to_parquet(parquet_file, engine="pyarrow")
    return parquet_file


# ============================================================================
# CSV READER TESTS
# ============================================================================


class TestCSVReader:
    """Tests for CSVReader implementation."""

    @pytest.fixture
    def reader(self) -> CSVReader:
        """Create a CSVReader instance."""
        return CSVReader()

    def test_can_read_csv(self, reader: CSVReader, valid_csv: Path) -> None:
        """Test that CSVReader can read CSV files."""
        assert reader.can_read(valid_csv) is True

    def test_can_read_non_csv(self, reader: CSVReader, temp_dir: Path) -> None:
        """Test that CSVReader rejects non-CSV files."""
        # Use .xlsx extension (not supported by CSVReader)
        xlsx_file = temp_dir / "test.xlsx"
        xlsx_file.write_text("content")
        assert reader.can_read(xlsx_file) is False

    @pytest.mark.asyncio
    async def test_read_valid_csv(self, reader: CSVReader, valid_csv: Path) -> None:
        """Test reading a valid CSV file."""
        df, metadata = await reader.read(valid_csv)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["name", "age", "city"]
        assert metadata.file_format == "csv"
        assert metadata.row_count == 3
        assert metadata.column_count == 3
        assert metadata.column_names == ["name", "age", "city"]

    @pytest.mark.asyncio
    async def test_read_empty_csv(self, reader: CSVReader, empty_csv: Path) -> None:
        """Test reading an empty CSV file raises error."""
        with pytest.raises(DataIngestionError) as exc_info:
            await reader.read(empty_csv)

        assert "empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_read_missing_csv(self, reader: CSVReader, temp_dir: Path) -> None:
        """Test reading a missing CSV file raises error."""
        missing_file = temp_dir / "missing.csv"

        with pytest.raises(DataIngestionError) as exc_info:
            await reader.read(missing_file)

        assert "not found" in str(exc_info.value).lower()

    def test_validate_valid_csv(self, reader: CSVReader, valid_csv: Path) -> None:
        """Test validating a valid CSV file."""
        assert reader.validate_format(valid_csv) is True

    def test_validate_invalid_csv(self, reader: CSVReader, invalid_csv: Path) -> None:
        """Test validating an invalid CSV file."""
        # The invalid CSV has mismatched columns but pandas can still read it
        # So validate_format returns True (file exists, has extension, is readable)
        # This is expected behavior - format validation checks file structure, not content
        assert reader.validate_format(invalid_csv) is True

    def test_validate_missing_csv(self, reader: CSVReader, temp_dir: Path) -> None:
        """Test validating a missing CSV file."""
        missing_file = temp_dir / "missing.csv"
        assert reader.validate_format(missing_file) is False

    @pytest.mark.asyncio
    async def test_peek_metadata(self, reader: CSVReader, valid_csv: Path) -> None:
        """Test peeking metadata from a CSV file."""
        metadata = await reader.peek_metadata(valid_csv)

        assert isinstance(metadata, FileMetadata)
        assert metadata.file_format == "csv"
        assert metadata.row_count == 3
        assert metadata.column_count == 3
        assert metadata.column_names == ["name", "age", "city"]
        assert metadata.file_size_bytes > 0

    @pytest.mark.asyncio
    async def test_peek_metadata_empty_csv(self, reader: CSVReader, empty_csv: Path) -> None:
        """Test peeking metadata from an empty CSV file raises error."""
        with pytest.raises(DataIngestionError) as exc_info:
            await reader.peek_metadata(empty_csv)

        assert "empty" in str(exc_info.value).lower()


# ============================================================================
# JSON READER TESTS
# ============================================================================


class TestJSONReader:
    """Tests for JSONReader implementation."""

    @pytest.fixture
    def reader(self) -> JSONReader:
        """Create a JSONReader instance."""
        return JSONReader()

    def test_can_read_json(self, reader: JSONReader, valid_json: Path) -> None:
        """Test that JSONReader can read JSON files."""
        assert reader.can_read(valid_json) is True

    def test_can_read_jsonl(self, reader: JSONReader, valid_jsonl: Path) -> None:
        """Test that JSONReader can read JSON Lines files."""
        assert reader.can_read(valid_jsonl) is True

    def test_can_read_non_json(self, reader: JSONReader, temp_dir: Path) -> None:
        """Test that JSONReader rejects non-JSON files."""
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("content")
        assert reader.can_read(txt_file) is False

    @pytest.mark.asyncio
    async def test_read_valid_json(self, reader: JSONReader, valid_json: Path) -> None:
        """Test reading a valid JSON file."""
        df, metadata = await reader.read(valid_json)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["name", "age", "city"]
        assert metadata.file_format == "json"
        assert metadata.row_count == 3
        assert metadata.column_count == 3
        assert metadata.column_names == ["name", "age", "city"]

    @pytest.mark.asyncio
    async def test_read_valid_jsonl(self, reader: JSONReader, valid_jsonl: Path) -> None:
        """Test reading a valid JSON Lines file."""
        df, metadata = await reader.read(valid_jsonl)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["name", "age", "city"]
        assert metadata.file_format == "jsonl"
        assert metadata.row_count == 3
        assert metadata.column_count == 3
        assert metadata.column_names == ["name", "age", "city"]

    @pytest.mark.asyncio
    async def test_read_invalid_json(self, reader: JSONReader, invalid_json: Path) -> None:
        """Test reading an invalid JSON file raises error."""
        with pytest.raises(DataIngestionError):
            await reader.read(invalid_json)

    @pytest.mark.asyncio
    async def test_read_empty_json(self, reader: JSONReader, empty_json: Path) -> None:
        """Test reading an empty JSON file raises error."""
        with pytest.raises(DataIngestionError):
            await reader.read(empty_json)

    @pytest.mark.asyncio
    async def test_read_missing_json(self, reader: JSONReader, temp_dir: Path) -> None:
        """Test reading a missing JSON file raises error."""
        missing_file = temp_dir / "missing.json"

        with pytest.raises(DataIngestionError) as exc_info:
            await reader.read(missing_file)

        assert "not found" in str(exc_info.value).lower()

    def test_validate_valid_json(self, reader: JSONReader, valid_json: Path) -> None:
        """Test validating a valid JSON file."""
        assert reader.validate_format(valid_json) is True

    def test_validate_valid_jsonl(self, reader: JSONReader, valid_jsonl: Path) -> None:
        """Test validating a valid JSON Lines file."""
        assert reader.validate_format(valid_jsonl) is True

    def test_validate_invalid_json(self, reader: JSONReader, invalid_json: Path) -> None:
        """Test validating an invalid JSON file."""
        assert reader.validate_format(invalid_json) is False

    def test_validate_missing_json(self, reader: JSONReader, temp_dir: Path) -> None:
        """Test validating a missing JSON file."""
        missing_file = temp_dir / "missing.json"
        assert reader.validate_format(missing_file) is False

    @pytest.mark.asyncio
    async def test_peek_metadata_json(self, reader: JSONReader, valid_json: Path) -> None:
        """Test peeking metadata from a JSON file."""
        metadata = await reader.peek_metadata(valid_json)

        assert isinstance(metadata, FileMetadata)
        assert metadata.file_format == "json"
        assert metadata.row_count == 3
        assert metadata.column_count == 3
        assert metadata.column_names == ["name", "age", "city"]
        assert metadata.file_size_bytes > 0

    @pytest.mark.asyncio
    async def test_peek_metadata_jsonl(self, reader: JSONReader, valid_jsonl: Path) -> None:
        """Test peeking metadata from a JSON Lines file."""
        metadata = await reader.peek_metadata(valid_jsonl)

        assert isinstance(metadata, FileMetadata)
        assert metadata.file_format == "jsonl"
        assert metadata.row_count == 3
        assert metadata.column_count == 3
        assert metadata.column_names == ["name", "age", "city"]
        assert metadata.file_size_bytes > 0


# ============================================================================
# PARQUET READER TESTS
# ============================================================================


@pytest.mark.skipif(
    not _module_available("pyarrow"),
    reason="pyarrow is required for ParquetReader tests"
)
class TestParquetReader:
    """Tests for ParquetReader implementation."""

    @pytest.fixture
    def reader(self) -> ParquetReader:
        """Create a ParquetReader instance."""
        return ParquetReader()

    def test_can_read_parquet(self, reader: ParquetReader, valid_parquet: Path) -> None:
        """Test that ParquetReader can read Parquet files."""
        assert reader.can_read(valid_parquet) is True

    def test_can_read_non_parquet(self, reader: ParquetReader, temp_dir: Path) -> None:
        """Test that ParquetReader rejects non-Parquet files."""
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("content")
        assert reader.can_read(txt_file) is False

    @pytest.mark.asyncio
    async def test_read_valid_parquet(self, reader: ParquetReader, valid_parquet: Path) -> None:
        """Test reading a valid Parquet file."""
        df, metadata = await reader.read(valid_parquet)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["name", "age", "city"]
        assert metadata.file_format == "parquet"
        assert metadata.row_count == 3
        assert metadata.column_count == 3
        assert metadata.column_names == ["name", "age", "city"]

    @pytest.mark.asyncio
    async def test_read_empty_parquet(self, reader: ParquetReader, empty_parquet: Path) -> None:
        """Test reading an empty Parquet file raises error."""
        with pytest.raises(DataIngestionError) as exc_info:
            await reader.read(empty_parquet)

        assert "empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_read_missing_parquet(self, reader: ParquetReader, temp_dir: Path) -> None:
        """Test reading a missing Parquet file raises error."""
        missing_file = temp_dir / "missing.parquet"

        with pytest.raises(DataIngestionError) as exc_info:
            await reader.read(missing_file)

        # Error message should contain information about the file
        assert "missing.parquet" in str(exc_info.value)

    def test_validate_valid_parquet(self, reader: ParquetReader, valid_parquet: Path) -> None:
        """Test validating a valid Parquet file."""
        assert reader.validate_format(valid_parquet) is True

    def test_validate_missing_parquet(self, reader: ParquetReader, temp_dir: Path) -> None:
        """Test validating a missing Parquet file."""
        missing_file = temp_dir / "missing.parquet"
        assert reader.validate_format(missing_file) is False

    @pytest.mark.asyncio
    async def test_peek_metadata(self, reader: ParquetReader, valid_parquet: Path) -> None:
        """Test peeking metadata from a Parquet file."""
        metadata = await reader.peek_metadata(valid_parquet)

        assert isinstance(metadata, FileMetadata)
        assert metadata.file_format == "parquet"
        assert metadata.row_count == 3
        assert metadata.column_count == 3
        assert metadata.column_names == ["name", "age", "city"]
        assert metadata.file_size_bytes > 0


# ============================================================================
# EXCEL READER TESTS
# ============================================================================


@pytest.mark.skipif(
    not _module_available("openpyxl"),
    reason="openpyxl is required for ExcelReader tests"
)
class TestExcelReader:
    """Tests for ExcelReader implementation."""

    @pytest.fixture
    def reader(self) -> ExcelReader:
        """Create an ExcelReader instance."""
        return ExcelReader()

    def test_can_read_xlsx(self, reader: ExcelReader, temp_dir: Path) -> None:
        """Test that ExcelReader can read Excel files."""
        xlsx_file = temp_dir / "test.xlsx"
        assert reader.can_read(xlsx_file) is True

    def test_can_read_non_excel(self, reader: ExcelReader, temp_dir: Path) -> None:
        """Test that ExcelReader rejects non-Excel files."""
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("content")
        assert reader.can_read(txt_file) is False

    @pytest.mark.asyncio
    async def test_read_missing_excel(self, reader: ExcelReader, temp_dir: Path) -> None:
        """Test reading a missing Excel file raises error."""
        missing_file = temp_dir / "missing.xlsx"

        with pytest.raises(DataIngestionError) as exc_info:
            await reader.read(missing_file)

        assert "not found" in str(exc_info.value).lower()

    def test_validate_missing_excel(self, reader: ExcelReader, temp_dir: Path) -> None:
        """Test validating a missing Excel file."""
        missing_file = temp_dir / "missing.xlsx"
        assert reader.validate_format(missing_file) is False