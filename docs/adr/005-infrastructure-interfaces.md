# ADR-005: Infrastructure Interfaces Architecture

**Status:** Accepted

**Date:** 2025-08-03

**Context:**

DataForge AI v2 requires a clean separation between business logic and external system dependencies. The infrastructure layer must provide adapters for external libraries (file readers, chart engines, report renderers, storage, caching, event publishing) while maintaining framework independence and testability.

In v1, agents directly imported external libraries like pandas, plotly, and scipy. This created tight coupling and made testing difficult. v2 needs a contract-based approach where agents depend on abstractions, not concrete implementations.

**Problem:**

How should we design infrastructure interfaces that:
1. Provide clear contracts for external system adapters
2. Enable dependency injection for testability
3. Support framework swapping (e.g., Plotly → Matplotlib)
4. Follow SOLID principles
5. Maintain type safety
6. Support async operations where appropriate
7. Enable proper error handling and validation

**Alternatives Considered:**

### Alternative 1: Protocol Classes (typing.Protocol)
- **Pros:** No inheritance required, structural typing, duck typing
- **Cons:** Less explicit, harder to discover methods, no runtime enforcement
- **Decision:** Rejected - ABC provides clearer contracts and runtime enforcement

### Alternative 2: Concrete Classes with Mock Support
- **Pros:** Simple, no abstraction overhead
- **Cons:** Tight coupling to implementations, difficult to swap frameworks
- **Decision:** Rejected - Violates Dependency Inversion Principle

### Alternative 3: Abstract Base Classes (ABC) (Chosen)
- **Pros:** Clear contracts, runtime enforcement, explicit method signatures, IDE support
- **Cons:** Requires inheritance, slightly more verbose
- **Decision:** Accepted - Best balance of clarity and flexibility

**Decision:**

Use Python's `abc.ABC` and `abc.abstractmethod` for all infrastructure interfaces. Each interface defines a clear contract that concrete implementations must fulfill.

### Interface Categories

#### 1. File Reading Interfaces
- **FileReader**: Read data files (CSV, Excel, Parquet, JSON)
  - `can_read(file_path)`: Check if reader can handle file
  - `read(file_path, **kwargs)`: Read file and return data with metadata
  - `validate_format(file_path)`: Validate file format

#### 2. Data Cleaning Interfaces
- **DataCleaner**: Clean data according to rules
  - `clean(data, rules, **kwargs)`: Clean data with optional rules
  - `detect_issues(data)`: Auto-detect data quality issues
  - `get_supported_cleaning_types()`: List supported cleaning operations

#### 3. Schema Detection Interfaces
- **SchemaDetector**: Detect data schema and semantic types
  - `detect_schema(data)`: Detect complete schema
  - `detect_semantic_types(data)`: Detect semantic column types
  - `detect_keys(data)`: Detect primary and foreign keys

#### 4. Visualization Interfaces
- **ChartEngine**: Create data visualizations
  - `create_bar_chart(data, x_column, y_column, title, **kwargs)`: Bar chart
  - `create_line_chart(data, x_column, y_column, title, **kwargs)`: Line chart
  - `create_scatter_plot(data, x_column, y_column, title, **kwargs)`: Scatter plot
  - `create_histogram(data, column, title, **kwargs)`: Histogram
  - `create_box_plot(data, column, title, **kwargs)`: Box plot
  - `create_correlation_heatmap(data, title, **kwargs)`: Correlation heatmap

#### 5. Report Rendering Interfaces
- **ReportRenderer**: Generate analysis reports
  - `render_html(data, profile, insights, kpis, visualizations, **kwargs)`: HTML report
  - `render_pdf(html_content, output_path, **kwargs)`: PDF report
  - `render_json(data, profile, insights, kpis, validation_report, **kwargs)`: JSON report
  - `get_supported_formats()`: List supported output formats

#### 6. Storage Interfaces
- **StorageProvider**: Persist analysis results
  - `save(key, data, metadata, **kwargs)`: Save data to storage
  - `load(key, **kwargs)`: Load data from storage
  - `delete(key, **kwargs)`: Delete data from storage
  - `exists(key, **kwargs)`: Check if data exists
  - `list_keys(prefix, **kwargs)`: List all keys with prefix

#### 7. Caching Interfaces
- **CacheProvider**: Cache computation results
  - `get(key, **kwargs)`: Get value from cache
  - `set(key, value, ttl, **kwargs)`: Set value in cache with optional TTL
  - `delete(key, **kwargs)`: Delete value from cache
  - `clear(**kwargs)`: Clear all cache values
  - `exists(key, **kwargs)`: Check if key exists in cache

#### 8. Event Publishing Interfaces
- **EventPublisher**: Publish events for real-time updates
  - `publish(event_type, data, **kwargs)`: Publish an event
  - `subscribe(event_type, callback, **kwargs)`: Subscribe to events
  - `unsubscribe(event_type, callback, **kwargs)`: Unsubscribe from events
  - `get_supported_event_types()`: List supported event types

### Interface Design Principles

1. **Async Support**: All I/O operations are async methods
2. **Type Hints**: Complete type annotations for all parameters and returns
3. **Docstrings**: Comprehensive documentation for each method
4. **Error Handling**: Methods document exceptions they may raise
5. **Framework Independence**: Interfaces don't depend on specific libraries
6. **Return Types**: Use tuples for multiple returns, domain models for structured data

**Consequences:**

### Positive:
- Clear contracts enable dependency injection
- Easy to swap implementations (e.g., Plotly → Matplotlib)
- Testable with mock implementations
- Type safety with comprehensive type hints
- Async support for I/O operations
- Framework independence prevents lock-in
- SOLID principles followed

### Negative:
- Additional abstraction layer adds slight complexity
- Concrete implementations must be created for each interface
- More files to maintain

### Neutral:
- LLMProvider interface already exists in core/llm.py (no changes needed)
- No concrete implementations yet (deferred to future sprints)
- Mock implementations used for testing

**Future Improvements:**

1. **Concrete Implementations**: Create implementations for:
   - CSVReader, ExcelReader, ParquetReader, JSONReader
   - PandasDataCleaner
   - PandasSchemaDetector
   - PlotlyChartEngine
   - Jinja2ReportRenderer, WeasyPrintPDFRenderer
   - LocalStorageProvider, S3StorageProvider
   - InMemoryCacheProvider, RedisCacheProvider
   - InMemoryEventPublisher, RedisEventPublisher

2. **Interface Extensions**: Add methods as needed:
   - FileReader: `get_supported_formats()`
   - ChartEngine: `create_pie_chart()`, `create_area_chart()`
   - StorageProvider: `copy()`, `move()`

3. **Validation**: Add input validation helpers in concrete implementations

4. **Performance**: Add batching support for bulk operations

**References:**

- DataForge AI v2 Architecture: docs/v2/ARCHITECTURE.md
- DataForge AI v2 Tech Stack: docs/v2/TECH_STACK.md
- DataForge AI v2 Sprint Plan: docs/v2/SPRINT_PLAN.md
- ADR-004: Domain Models: docs/adr/004-domain-models.md