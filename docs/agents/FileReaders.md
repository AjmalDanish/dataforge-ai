# File Readers — DataForge AI v2

> Infrastructure Layer: File Reading Components

---

## Purpose

File Readers are infrastructure components responsible for reading data files in various formats and extracting metadata. They provide a unified interface for the DataValidationAgent to load data from CSV, Excel, Parquet, and JSON files.

---

## Responsibilities

### Core Responsibilities

1. **File Reading**: Read data files and convert them to pandas DataFrames
2. **Metadata Extraction**: Extract file metadata without loading full data
3. **Format Validation**: Validate that files have the correct format
4. **Error Handling**: Gracefully handle all error conditions
5. **Encoding Detection**: Automatically detect file encoding with fallback

### Non-Responsibilities

- **Data Validation**: Not responsible for validating data quality (handled by DataValidationAgent)
- **Data Cleaning**: Not responsible for cleaning data (handled by DataCleaningAgent)
- **Schema Detection**: Not responsible for detecting schema (handled by SchemaDetectionAgent)
- **Business Logic**: No business logic or domain-specific processing

---

## Supported Formats

| Format | Extensions | Reader | Notes |
|--------|-----------|--------|-------|
| CSV | `.csv`, `.tsv`, `.txt` | CSVReader | Encoding detection, delimiter auto-detection |
| Excel | `.xlsx`, `.xls` | ExcelReader | Multi-sheet support, default to first sheet |
| Parquet | `.parquet` | ParquetReader | PyArrow backend, efficient metadata extraction |
| JSON | `.json`, `.jsonl`, `.ndjson` | JSONReader | Auto-detect JSON vs JSON Lines format |

---

## Architecture

### Layer Position

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AGENT LAYER                                      │
│  DataValidationAgent (consumer of FileReader)                        │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                              │
│  CSVReader │ ExcelReader │ ParquetReader │ JSONReader               │
│         (implement FileReader interface)                             │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                     CORE LAYER                                       │
│  FileMetadata │ DataForgeError │ GraphState                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Dependency Direction

- Readers depend on: Core layer (FileMetadata, DataForgeError)
- Readers are depended on by: Agent layer (DataValidationAgent)
- Readers are managed by: DI Container

---

## FileReader Interface

### Methods

```python
class FileReader(ABC):
    @abstractmethod
    def can_read(self, file_path: str | Path) -> bool:
        """Check if this reader can handle the given file."""
        ...

    @abstractmethod
    async def read(self, file_path: str | Path, **kwargs: Any) -> tuple[Any, FileMetadata]:
        """Read a file and return the data with metadata."""
        ...

    @abstractmethod
    def validate_format(self, file_path: str | Path) -> bool:
        """Validate that the file format is correct."""
        ...

    @abstractmethod
    async def peek_metadata(self, file_path: str | Path) -> FileMetadata:
        """Extract metadata without loading full data."""
        ...
```

### FileMetadata

```python
class FileMetadata(BaseModel):
    filename: str                          # Original filename
    file_path: str                         # Full file path
    file_size_bytes: int                   # File size in bytes
    file_size_mb: float                    # File size in MB
    file_format: str                       # File format (csv, excel, parquet, json, jsonl)
    encoding: str                          # Detected file encoding
    row_count: int | None                  # Number of rows
    column_count: int | None               # Number of columns
    column_names: list[str]                # List of column names
    sheet_names: list[str]                 # List of sheet names (Excel only)
    created_at: str                        # When metadata was created
    last_modified: str | None              # File last modified time
```

---

## Error Handling

### Error Types

All readers gracefully handle the following error conditions:

| Error Type | Description | Error Details |
|------------|-------------|---------------|
| Missing File | File does not exist | `error_type: "missing_file"` |
| Permission Denied | Insufficient permissions | `error_type: "permission_denied"` |
| Corrupted File | File is corrupted or invalid | `error_type: "corrupted_file"` |
| Unsupported Encoding | Encoding not supported | `error_type: "unsupported_encoding"` |
| Invalid Extension | File extension not supported | `error_type: "invalid_extension"` |
| Empty File | File is empty | `error_type: "empty_file"` |
| Empty DataFrame | No data in file | `error_type: "empty_file"` |

### Error Handling Strategy

All readers use the `@handle_file_errors` decorator to catch and convert exceptions to `DataIngestionError`:

```python
@handle_file_errors
async def read(self, file_path: str | Path, **kwargs: Any) -> tuple[Any, FileMetadata]:
    # Implementation
    ...
```

This ensures:
- **Never crash**: All exceptions are caught and converted
- **Consistent errors**: All errors are `DataIngestionError` with details
- **Informative messages**: Error messages include context and details

---

## Reader Implementations

### CSVReader

**Features:**
- Encoding detection with fallback (UTF-8 → Latin-1 → CP1252)
- Delimiter auto-detection (comma, semicolon, tab, pipe)
- Handles quoted fields
- Handles various line endings (CRLF, LF, CR)
- Sampling for large files (>10MB)

**Example:**
```python
from dataforge.infrastructure.readers import CSVReader

reader = CSVReader()
df, metadata = await reader.read("data.csv")

print(f"Rows: {metadata.row_count}")
print(f"Columns: {metadata.column_names}")
print(f"Encoding: {metadata.encoding}")
```

### ExcelReader

**Features:**
- Multi-sheet support
- Default to first sheet
- Sheet selection via kwargs
- Extract sheet names metadata
- Sampling for large files (>10MB)

**Example:**
```python
from dataforge.infrastructure.readers import ExcelReader

reader = ExcelReader()

# Read first sheet (default)
df, metadata = await reader.read("data.xlsx")

# Read specific sheet
df, metadata = await reader.read("data.xlsx", sheet_name="Sheet2")

print(f"Sheets: {metadata.sheet_names}")
```

### ParquetReader

**Features:**
- PyArrow backend
- Efficient metadata extraction from Parquet metadata
- Column pruning via kwargs
- Schema preservation

**Example:**
```python
from dataforge.infrastructure.readers import ParquetReader

reader = ParquetReader()
df, metadata = await reader.read("data.parquet")

print(f"Rows: {metadata.row_count}")
print(f"Columns: {metadata.column_names}")
```

### JSONReader

**Features:**
- Auto-detect JSON vs JSON Lines format
- Handle nested structures (flatten to DataFrame)
- Handle array of objects vs single object
- Sampling for large files (>10MB)

**Example:**
```python
from dataforge.infrastructure.readers import JSONReader

reader = JSONReader()

# Auto-detects JSON vs JSON Lines
df, metadata = await reader.read("data.json")

print(f"Format: {metadata.file_format}")  # "json" or "jsonl"
print(f"Rows: {metadata.row_count}")
```

---

## Dependency Injection

### Registration

All readers are registered in the DI Container as factories:

```python
from dataforge.shared.container import DIContainer
from dataforge.shared.readers_container import register_file_readers

container = DIContainer()
register_file_readers(container)
```

### Resolution

Readers are resolved from the container:

```python
csv_reader = container.resolve(CSVReader)
excel_reader = container.resolve(ExcelReader)
parquet_reader = container.resolve(ParquetReader)
json_reader = container.resolve(JSONReader)
```

### Reader Selection

Use `get_reader_for_file()` to automatically select the appropriate reader:

```python
from dataforge.shared.readers_container import get_reader_for_file

reader = get_reader_for_file(container, "data.csv")
if reader:
    df, metadata = await reader.read("data.csv")
```

---

## Performance Considerations

### Metadata Extraction

For large files (>10MB), `peek_metadata()` uses sampling to extract metadata quickly:

- **CSV**: Read first 1000 rows, estimate total rows
- **Excel**: Read first 1000 rows, estimate total rows
- **Parquet**: Use Parquet metadata (no sampling needed)
- **JSON**: Read first 1000 lines (JSON Lines) or all (JSON)

### Memory Usage

- Readers use pandas for data loading
- For very large files, consider chunking or streaming
- Memory-efficient operations where possible

---

## Testing

### Test Coverage

Target: 95%+ code coverage

### Test Cases

- Valid files for each format
- Invalid files for each format
- Empty files
- Missing files
- Permission errors
- Encoding detection
- Metadata extraction
- Format validation

### Running Tests

```bash
# Run all reader tests
pytest tests/unit/infra/test_readers.py -v

# Run with coverage
pytest tests/unit/infra/test_readers.py --cov=dataforge/infrastructure/readers --cov-report=term-missing
```

---

## Best Practices

### For Users

1. **Use DI Container**: Always resolve readers from the DI Container
2. **Check can_read()**: Before reading, check if the reader can handle the file
3. **Handle Errors**: Always catch `DataIngestionError` when reading files
4. **Use peek_metadata()**: For validation, use `peek_metadata()` instead of `read()`

### For Developers

1. **Use @handle_file_errors**: Always use the decorator for error handling
2. **Implement all methods**: Ensure all interface methods are implemented
3. **Test error conditions**: Test all error conditions, not just happy paths
4. **Document kwargs**: Document all format-specific kwargs in docstrings

---

## Example Usage

### Complete Example

```python
from dataforge.shared.container import DIContainer
from dataforge.shared.readers_container import register_file_readers, get_reader_for_file
from dataforge.shared.errors import DataIngestionError

# Initialize container and register readers
container = DIContainer()
register_file_readers(container)

# Get appropriate reader for file
file_path = "data.csv"
reader = get_reader_for_file(container, file_path)

if reader:
    try:
        # Peek metadata first (fast)
        metadata = await reader.peek_metadata(file_path)
        print(f"Format: {metadata.file_format}")
        print(f"Rows: {metadata.row_count}")
        print(f"Columns: {metadata.column_names}")

        # Read full data
        df, full_metadata = await reader.read(file_path)
        print(f"Loaded {len(df)} rows")

    except DataIngestionError as e:
        print(f"Error reading file: {e}")
        print(f"Details: {e.details}")
else:
    print("No reader available for this file format")
```

---

## Future Enhancements

Potential future enhancements:

- **Streaming Support**: Add streaming support for very large files
- **Additional Formats**: Support for additional formats (e.g., XML, Avro, ORC)
- **Compression**: Support for compressed files (e.g., .csv.gz, .parquet.snappy)
- **Progress Callbacks**: Add progress callbacks for large file operations
- **Caching**: Add metadata caching for repeated reads

---

## References

- Implementation Plan: `plans/SPRINT_2_TASK_1_FILE_READERS_IMPLEMENTATION_PLAN.md`
- FileReader Interface: `dataforge/infrastructure/interfaces.py`
- Reader Implementations: `dataforge/infrastructure/readers/`
- DI Container: `dataforge/shared/container.py`
- Reader Registration: `dataforge/shared/readers_container.py`
- Unit Tests: `tests/unit/infra/test_readers.py`