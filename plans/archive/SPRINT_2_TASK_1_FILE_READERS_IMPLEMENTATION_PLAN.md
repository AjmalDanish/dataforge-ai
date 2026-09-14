# DataForge AI V2 — Sprint 2 Task 1: File Readers Implementation Plan

> Implementation Plan for File Reader Infrastructure Layer

---

## Executive Summary

This plan details the implementation of the File Reader layer for DataForge AI v2. The file readers are infrastructure components that handle reading various data file formats (CSV, Excel, Parquet, JSON, JSON Lines) and provide metadata extraction capabilities. This is a foundational component that will be used by the DataValidationAgent.

**Status:** Planning Phase
**Branch:** v2-development
**Sprint:** Sprint 2 - Data Agents
**Task:** Task 1 - File Readers Implementation

---

## Architecture Context

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

## Requirements Analysis

### Functional Requirements

#### FR1: FileReader Interface Extension
The existing `FileReader` interface must be extended to include:

```python
@abstractmethod
async def peek_metadata(self, file_path: str | Path) -> FileMetadata:
    """Extract metadata without loading full data.
    
    Returns:
        FileMetadata with: rows, columns, column_names, file_size, 
        encoding, sheet_names (Excel), format
    """
```

#### FR2: CSVReader
- Support CSV files (.csv)
- Encoding detection with fallback (UTF-8 → Latin-1 → CP1252)
- Delimiter auto-detection (comma, semicolon, tab, pipe)
- Handle quoted fields
- Handle various line endings (CRLF, LF, CR)

#### FR3: ExcelReader
- Support Excel files (.xlsx)
- Support multiple sheets
- Default to first sheet
- Allow sheet selection via kwargs
- Extract sheet names metadata

#### FR4: ParquetReader
- Support Parquet files (.parquet)
- Use PyArrow backend
- Handle column pruning via kwargs
- Preserve schema information

#### FR5: JSONReader
- Support JSON files (.json)
- Support JSON Lines files (.jsonl, .ndjson)
- Auto-detect JSON vs JSON Lines format
- Handle nested structures (flatten to DataFrame)
- Handle array of objects vs single object

#### FR6: Error Handling
All readers must gracefully handle:
- Missing file → Return DataForgeError
- Permission denied → Return DataForgeError
- Corrupted file → Return DataForgeError
- Unsupported encoding → Return DataForgeError
- Invalid extension → Return DataForgeError
- Empty file → Return DataForgeError
- Empty dataframe → Return DataForgeError
- **Never crash** - All exceptions caught and converted to DataForgeError

#### FR7: Metadata Support
All readers must provide:
- `rows`: Number of rows in the dataset
- `columns`: Number of columns
- `column_names`: List of column names
- `file_size`: File size in bytes and MB
- `encoding`: Detected encoding (CSV, JSON)
- `sheet_names`: List of sheet names (Excel only)
- `format`: File format identifier

#### FR8: DI Container Registration
All readers must be registered in the DI Container:
- CSVReader as factory (new instance per request)
- ExcelReader as factory
- ParquetReader as factory
- JSONReader as factory

### Non-Functional Requirements

#### NFR1: Test Coverage
- Target: 95%+ code coverage
- Test all error conditions
- Test edge cases (empty files, large files, special characters)

#### NFR2: Performance
- `peek_metadata()` should be fast (sample-based for large files)
- `read()` should use streaming for large files where possible
- Memory-efficient operations

#### NFR3: Compatibility
- Python 3.11+
- pandas 2.0+
- PyArrow 12.0+
- openpyxl (for Excel)

---

## Design Decisions

### DD1: FileReader Interface Extension

**Decision:** Extend the existing `FileReader` interface with `peek_metadata()` method.

**Rationale:**
- Allows DataValidationAgent to get metadata without loading full data
- Enables early validation and format detection
- Separates concerns: metadata extraction vs data loading

**Impact:**
- Interface change requires updating all implementations
- Existing interface methods remain unchanged

### DD2: Error Handling Strategy

**Decision:** Use a unified error handling decorator pattern.

**Rationale:**
- Consistent error handling across all readers
- Reduces code duplication
- Ensures all exceptions are caught and converted to DataForgeError

**Implementation:**
```python
def handle_file_errors(func):
    """Decorator to catch and convert file reading errors."""
    async def wrapper(self, file_path: str | Path, *args, **kwargs):
        try:
            return await func(self, file_path, *args, **kwargs)
        except FileNotFoundError as e:
            raise DataIngestionError(
                f"File not found: {file_path}",
                details={"error_type": "missing_file", "file_path": str(file_path)}
            ) from e
        except PermissionError as e:
            raise DataIngestionError(
                f"Permission denied: {file_path}",
                details={"error_type": "permission_denied", "file_path": str(file_path)}
            ) from e
        # ... other error types
    return wrapper
```

### DD3: Encoding Detection Strategy

**Decision:** Use chardet library for encoding detection with fallback chain.

**Rationale:**
- chardet provides reliable encoding detection
- Fallback chain ensures robustness
- UTF-8 → Latin-1 → CP1252 covers most common encodings

**Implementation:**
```python
def detect_encoding(file_path: Path) -> str:
    """Detect file encoding with fallback."""
    try:
        import chardet
        with open(file_path, 'rb') as f:
            raw = f.read(10000)  # Sample first 10KB
        result = chardet.detect(raw)
        if result['confidence'] > 0.7:
            return result['encoding']
    except Exception:
        pass
    
    # Fallback chain
    for encoding in ['utf-8', 'latin-1', 'cp1252']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1000)
            return encoding
        except UnicodeDecodeError:
            continue
    
    return 'utf-8'  # Final fallback
```

### DD4: JSON vs JSON Lines Detection

**Decision:** Auto-detect JSON Lines by checking if every line is valid JSON.

**Rationale:**
- JSON Lines files often have .json extension (not .jsonl)
- Auto-detection provides better UX
- Fallback to standard JSON if detection fails

**Implementation:**
```python
def detect_json_format(file_path: Path) -> str:
    """Detect if file is JSON or JSON Lines."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            second_line = f.readline().strip()
        
        # If second line exists and both are valid JSON objects
        if second_line:
            import json
            json.loads(first_line)
            json.loads(second_line)
            return 'jsonl'
        
        return 'json'
    except Exception:
        return 'json'
```

### DD5: Metadata Extraction Strategy

**Decision:** Use sampling for large files to extract metadata quickly.

**Rationale:**
- Loading entire file for metadata is inefficient
- Sampling provides accurate estimates for row/column counts
- pandas `nrows` parameter enables efficient sampling

**Implementation:**
```python
async def peek_metadata(self, file_path: str | Path) -> FileMetadata:
    """Extract metadata using sampling."""
    path = Path(file_path)
    file_size = path.stat().st_size
    
    # For small files (<10MB), read all
    if file_size < 10 * 1024 * 1024:
        df = pd.read_csv(path, nrows=None)
    # For large files, sample first 1000 rows
    else:
        df = pd.read_csv(path, nrows=1000)
    
    # Estimate total rows for large files
    if file_size >= 10 * 1024 * 1024:
        avg_row_size = file_size / len(df)
        estimated_rows = int(file_size / avg_row_size)
    else:
        estimated_rows = len(df)
    
    return FileMetadata(
        filename=path.name,
        file_path=str(path),
        file_size_bytes=file_size,
        file_size_mb=file_size / (1024 * 1024),
        file_format='csv',
        encoding=detect_encoding(path),
        row_count=estimated_rows,
        column_count=len(df.columns),
        column_names=list(df.columns),
    )
```

---

## Implementation Plan

### Phase 1: Interface Extension

**Tasks:**
1. Add `peek_metadata()` method to `FileReader` interface
2. Update `FileMetadata` model to include `column_names` field
3. Add new error types for file reading (if needed)

**Files:**
- `dataforge/infrastructure/interfaces.py` - Add `peek_metadata()` method
- `dataforge/core/models.py` - Update `FileMetadata` if needed

**Tests:**
- Test that interface requires `peek_metadata()` implementation
- Test that `FileMetadata` accepts `column_names`

---

### Phase 2: CSVReader Implementation

**Tasks:**
1. Create `dataforge/infrastructure/readers/` directory
2. Create `csv_reader.py` with CSVReader class
3. Implement `can_read()` method
4. Implement `read()` method with encoding fallback
5. Implement `validate_format()` method
6. Implement `peek_metadata()` method with sampling
7. Add error handling decorator

**Files:**
- `dataforge/infrastructure/readers/__init__.py`
- `dataforge/infrastructure/readers/csv_reader.py`

**Dependencies:**
- pandas (already in pyproject.toml)
- chardet (need to add to pyproject.toml)

---

### Phase 3: ExcelReader Implementation

**Tasks:**
1. Create `excel_reader.py` with ExcelReader class
2. Implement `can_read()` method
3. Implement `read()` method with sheet selection
4. Implement `validate_format()` method
5. Implement `peek_metadata()` method with sheet names
6. Add error handling decorator

**Files:**
- `dataforge/infrastructure/readers/excel_reader.py`

**Dependencies:**
- pandas (already in pyproject.toml)
- openpyxl (need to add to pyproject.toml)

---

### Phase 4: ParquetReader Implementation

**Tasks:**
1. Create `parquet_reader.py` with ParquetReader class
2. Implement `can_read()` method
3. Implement `read()` method with PyArrow backend
4. Implement `validate_format()` method
5. Implement `peek_metadata()` method
6. Add error handling decorator

**Files:**
- `dataforge/infrastructure/readers/parquet_reader.py`

**Dependencies:**
- pandas (already in pyproject.toml)
- pyarrow (already in pyproject.toml)

---

### Phase 5: JSONReader Implementation

**Tasks:**
1. Create `json_reader.py` with JSONReader class
2. Implement `can_read()` method
3. Implement `read()` method with JSON/JSON Lines detection
4. Implement `validate_format()` method
5. Implement `peek_metadata()` method
6. Add error handling decorator

**Files:**
- `dataforge/infrastructure/readers/json_reader.py`

**Dependencies:**
- pandas (already in pyproject.toml)
- No additional dependencies needed

---

### Phase 6: Error Handling Infrastructure

**Tasks:**
1. Create error handling decorator
2. Add specific error types for file reading
3. Ensure all readers use the decorator

**Files:**
- `dataforge/infrastructure/readers/base.py` - Shared utilities and decorators

---

### Phase 7: DI Container Registration

**Tasks:**
1. Update `dataforge/shared/container.py` to register all readers
2. Create a factory function for reader registration
3. Update `dataforge/infrastructure/__init__.py` to export readers

**Files:**
- `dataforge/shared/container.py` - Add reader registration
- `dataforge/infrastructure/__init__.py` - Export readers

---

### Phase 8: Unit Tests

**Tasks:**
1. Create `tests/unit/infra/test_readers.py`
2. Test CSVReader with valid CSV
3. Test CSVReader with invalid CSV
4. Test CSVReader with empty CSV
5. Test ExcelReader with valid Excel
6. Test ParquetReader with valid Parquet
7. Test JSONReader with valid JSON
8. Test JSONReader with valid JSON Lines
9. Test encoding handling
10. Test permission errors
11. Test missing file errors
12. Test corrupted file errors
13. Test empty file errors
14. Test empty dataframe errors
15. Test metadata extraction

**Files:**
- `tests/unit/infra/test_readers.py`
- `tests/fixtures/` - Create test data files

---

### Phase 9: Documentation

**Tasks:**
1. Create `docs/agents/FileReaders.md`
2. Document purpose and responsibilities
3. Document supported formats
4. Document error handling
5. Document example usage
6. Create architecture diagram

**Files:**
- `docs/agents/FileReaders.md`

---

### Phase 10: Integration & Validation

**Tasks:**
1. Run all tests and ensure 95%+ coverage
2. Update `docs/v2/TODO.md` with completed tasks
3. Perform self-review (architecture, dependencies, technical debt)
4. Create implementation report

**Files:**
- `docs/v2/TODO.md` - Update completed tasks
- `plans/SPRINT_2_TASK_1_IMPLEMENTATION_REPORT.md` - Implementation report

---

## File Structure

```
dataforge/
├── infrastructure/
│   ├── __init__.py (update - export readers)
│   ├── interfaces.py (update - add peek_metadata)
│   └── readers/
│       ├── __init__.py
│       ├── base.py (new - shared utilities)
│       ├── csv_reader.py (new)
│       ├── excel_reader.py (new)
│       ├── parquet_reader.py (new)
│       └── json_reader.py (new)
├── shared/
│   ├── container.py (update - register readers)
│   └── errors.py (update - add file reading errors if needed)
└── core/
    └── models.py (update - FileMetadata if needed)

tests/
├── unit/
│   └── infra/
│       └── test_readers.py (new)
└── fixtures/
    ├── valid.csv (new)
    ├── invalid.csv (new)
    ├── empty.csv (new)
    ├── valid.xlsx (new)
    ├── valid.parquet (new)
    ├── valid.json (new)
    └── valid.jsonl (new)

docs/
├── agents/
│   └── FileReaders.md (new)
└── v2/
    └── TODO.md (update)

plans/
└── SPRINT_2_TASK_1_FILE_READERS_IMPLEMENTATION_PLAN.md (this file)
```

---

## Dependencies to Add

### pyproject.toml additions:

```toml
[tool.poetry.dependencies]
# ... existing dependencies ...
chardet = "^5.0.0"  # For encoding detection
openpyxl = "^3.1.0"  # For Excel file reading
```

---

## Test Data Requirements

### Test Fixtures Needed:

1. `valid.csv` - Standard CSV with various data types
2. `invalid.csv` - Malformed CSV
3. `empty.csv` - Empty CSV file
4. `valid.xlsx` - Excel file with multiple sheets
5. `valid.parquet` - Parquet file with sample data
6. `valid.json` - JSON array of objects
7. `valid.jsonl` - JSON Lines file
8. `encoding_test.csv` - CSV with non-UTF-8 encoding
9. `large.csv` - Large CSV for testing sampling (optional)

---

## Risk Analysis

### High Risks:

1. **Encoding Detection Complexity**
   - Risk: chardet may not detect all encodings accurately
   - Mitigation: Implement robust fallback chain, test with various encodings

2. **Memory Usage for Large Files**
   - Risk: Loading entire file may cause memory issues
   - Mitigation: Use sampling for metadata, streaming for read()

3. **Excel File Complexity**
   - Risk: Excel files may have complex structures (merged cells, formulas)
   - Mitigation: Document limitations, focus on tabular data

### Medium Risks:

1. **JSON Structure Variability**
   - Risk: Nested JSON structures may not flatten correctly
   - Mitigation: Document supported structures, provide clear error messages

2. **Test Coverage Target**
   - Risk: May not achieve 95%+ coverage
   - Mitigation: Comprehensive test planning, focus on edge cases

### Low Risks:

1. **DI Container Integration**
   - Risk: Registration may conflict with existing code
   - Mitigation: Follow existing patterns, test registration

---

## Success Criteria

- [ ] All four readers implemented (CSV, Excel, Parquet, JSON)
- [ ] All readers implement FileReader interface correctly
- [ ] All readers support `read()`, `validate_format()`, `peek_metadata()`
- [ ] All error conditions handled gracefully
- [ ] All readers registered in DI Container
- [ ] Unit tests created with 95%+ coverage
- [ ] Documentation created (FileReaders.md)
- [ ] TODO.md updated with completed tasks
- [ ] No architecture changes
- [ ] No dependency direction violations
- [ ] No technical debt introduced

---

## Mermaid Architecture Diagram

```mermaid
graph TB
    subgraph AGENT_LAYER
        DVA[DataValidationAgent]
    end
    
    subgraph INFRASTRUCTURE_LAYER
        FileReader[FileReader Interface]
        CSVR[CSVReader]
        EXCLR[ExcelReader]
        PARQR[ParquetReader]
        JSONR[JSONReader]
        
        FileReader <|-- CSVR
        FileReader <|-- EXCLR
        FileReader <|-- PARQR
        FileReader <|-- JSONR
    end
    
    subgraph CORE_LAYER
        FM[FileMetadata]
        DFE[DataForgeError]
    end
    
    subgraph DI_LAYER
        DIC[DI Container]
    end
    
    DVA -->|uses| FileReader
    CSVR -->|returns| FM
    EXCLR -->|returns| FM
    PARQR -->|returns| FM
    JSONR -->|returns| FM
    CSVR -->|raises| DFE
    EXCLR -->|raises| DFE
    PARQR -->|raises| DFE
    JSONR -->|raises| DFE
    DIC -->|manages| CSVR
    DIC -->|manages| EXCLR
    DIC -->|manages| PARQR
    DIC -->|manages| JSONR
    
    style FileReader fill:#f9f,stroke:#333,stroke-width:2px
    style FM fill:#bbf,stroke:#333,stroke-width:2px
    style DFE fill:#fbb,stroke:#333,stroke-width:2px
```

---

## Next Steps

1. Review this plan with stakeholders
2. Get approval for implementation
3. Switch to Code mode to begin implementation
4. Follow phases sequentially
5. Update TODO list as tasks complete

---

## References

- DataForge AI v2 Architecture: `docs/v2/ARCHITECTURE.md`
- Agent Specifications: `docs/v2/AGENTS.md`
- GraphState v2: `docs/v2/GRAPHSTATE.md`
- Sprint Plan: `docs/v2/SPRINT_PLAN.md`
- Existing Interfaces: `dataforge/infrastructure/interfaces.py`
- DI Container: `dataforge/shared/container.py`
- Core Models: `dataforge/core/models.py`
- Error Handling: `dataforge/shared/errors.py`