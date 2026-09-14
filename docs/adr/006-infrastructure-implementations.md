# ADR-006: Infrastructure Implementations

**Status:** Accepted

**Date:** 2025-08-04

**Context:**

Sprint 1 Task 5 created abstract infrastructure interfaces for external system adapters. Sprint 1 Task 6 requires concrete implementations of critical interfaces to enable visualization and report generation capabilities.

The v1 implementation had tight coupling between agents and external libraries (Plotly, Jinja2). v2 requires concrete implementations that satisfy the interface contracts while maintaining framework independence.

**Problem:**

How should we implement concrete infrastructure adapters that:
1. Satisfy the interface contracts created in Sprint 1 Task 5
2. Enable visualization and report generation for agents
3. Maintain framework independence for future swapping
4. Provide clear, testable implementations
5. Handle edge cases and errors gracefully

**Alternatives Considered:**

### Alternative 1: Implement All Interfaces Now
- **Pros:** Complete infrastructure layer
- **Cons:** Overkill for Sprint 1 scope, delays agent development
- **Decision:** Rejected - Sprint 1 scope focuses on critical implementations only

### Alternative 2: Use v1 Implementations Directly
- **Pros:** Reuse existing code
- **Cons:** v1 code has tight coupling, doesn't follow v2 architecture
- **Decision:** Rejected - v1 architecture violates Clean Architecture principles

### Alternative 3: Implement Only Critical Interfaces (Chosen)
- **Pros:** Focused scope, enables visualization and reporting, faster delivery
- **Cons:** Other implementations deferred to future sprints
- **Decision:** Accepted - Sprint 1 focuses on PlotlyChartEngine and Jinja2HTMLRenderer

**Decision:**

Implement concrete implementations for the two most critical infrastructure interfaces:

1. **PlotlyChartEngine** - Enables visualization for VisualizationAgent
2. **Jinja2HTMLRenderer** - Enables report generation for ExecutiveReportAgent

### Implementation Details

#### PlotlyChartEngine

**Framework:** Plotly ^6.9.0 (interactive HTML charts)

**Implemented Methods:**
- `create_bar_chart()` - Bar charts with optional color grouping
- `create_line_chart()` - Line charts with optional markers and grouping
- `create_scatter_plot()` - Scatter plots with optional trendlines
- `create_histogram()` - Histograms with optional marginal plots
- `create_box_plot()` - Box plots with optional notched display
- `create_correlation_heatmap()` - Correlation heatmaps with numeric data filtering

**Design Decisions:**
- Returns HTML fragments (not full documents) for embedding
- Uses Plotly CDN for JavaScript inclusion
- Supports kwargs for Plotly-specific options
- Filters numeric columns for correlation matrix
- Configurable color scales and layouts

#### Jinja2HTMLRenderer

**Framework:** Jinja2 ^3.1.6 (HTML templating)

**Implemented Methods:**
- `render_html()` - HTML report generation with fallback
- `render_json()` - JSON report for API consumption
- `get_supported_formats()` - Lists "html" and "json" formats
- `render_pdf()` - Raises NotImplementedError (deferred to future sprint)

**Design Decisions:**
- Simple HTML generation without complex templates (deferred to future)
- Fallback mechanism if templates fail to load
- JSON includes data sample (limited to 100 rows) for API responses
- PDF rendering deferred (requires WeasyPrint or similar)
- Modular structure for future template expansion

**HTML Templates Created:**
- `base.html` - Base template with styling and layout
- `summary.html` - Dataset summary section
- `kpi.html` - KPI cards section
- `insights.html` - Business insights section
- `charts.html` - Visualizations section
- `recommendations.html` - Recommendations section

**Template Design:**
- Modern, responsive design with CSS grid layouts
- Color-coded badges for impact/priority levels
- Emoji icons for visual appeal
- Clean, professional styling
- Modular sections for flexibility

**Consequences:**

### Positive:
- VisualizationAgent can now generate interactive charts
- ExecutiveReportAgent can generate HTML and JSON reports
- Clear separation between business logic and presentation
- Testable implementations with comprehensive coverage
- Foundation for future template expansion
- Framework independence maintained (can swap Plotly for Matplotlib)

### Negative:
- PDF rendering not yet implemented (deferred to future sprint)
- Templates not yet used (simple HTML fallback active)
- No concrete implementations for FileReader, DataCleaner, SchemaDetector, StorageProvider, CacheProvider, EventPublisher (deferred)

### Neutral:
- Simple HTML generation sufficient for MVP
- Templates ready for future enhancement
- PDF rendering can be added when needed
- Other infrastructure implementations can follow same pattern

**Future Improvements:**

1. **PDF Rendering:** Add WeasyPrint integration for PDF report generation
2. **Template Enhancement:** Use Jinja2 templates for more sophisticated reports
3. **Additional Implementations:**
   - CSVReader, ExcelReader, ParquetReader, JSONReader
   - PandasDataCleaner
   - PandasSchemaDetector
   - LocalStorageProvider, S3StorageProvider
   - InMemoryCacheProvider, RedisCacheProvider
   - InMemoryEventPublisher, RedisEventPublisher
4. **Chart Enhancements:** Add more chart types (pie, area, radar, etc.)
5. **Report Customization:** Add theme options, branding, custom CSS

**References:**

- DataForge AI v2 Architecture: docs/v2/ARCHITECTURE.md
- DataForge AI v2 Tech Stack: docs/v2/TECH_STACK.md
- DataForge AI v2 Sprint Plan: docs/v2/SPRINT_PLAN.md
- ADR-005: Infrastructure Interfaces: docs/adr/005-infrastructure-interfaces.md
- Plotly Documentation: https://plotly.com/python/
- Jinja2 Documentation: https://jinja.palletsprojects.com/