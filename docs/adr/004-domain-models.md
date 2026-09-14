# ADR-004: Domain Models Architecture

**Status:** Accepted

**Date:** 2025-08-03

**Context:**

DataForge AI v2 requires a comprehensive set of domain models to represent business concepts, data profiles, validation results, and insights. These models serve as the business layer of the architecture and must remain independent from infrastructure concerns (LangGraph, FastAPI, Plotly, UI, database).

The v1 implementation lacked structured domain models, relying primarily on dictionaries and raw data structures. This led to:
- Type safety issues
- Lack of validation
- Poor documentation of business concepts
- Difficulty in maintaining consistency across agents
- No clear separation between business logic and infrastructure

**Problem:**

How should we design and implement domain models for DataForge AI v2 that:
1. Provide type safety and validation
2. Remain independent of infrastructure frameworks
3. Support the full range of business concepts needed by agents
4. Enable clear documentation of business semantics
5. Support serialization/deserialization for checkpoints
6. Maintain immutability for state consistency

**Alternatives Considered:**

### Alternative 1: Dataclasses
- **Pros:** Built-in Python, no dependencies, simple
- **Cons:** No built-in validation, limited serialization support, no JSON schema generation
- **Decision:** Rejected - insufficient validation and serialization capabilities

### Alternative 2: Pydantic v1 Models
- **Pros:** Mature, well-tested, good validation
- **Cons:** v1 is deprecated, slower than v2, less type inference
- **Decision:** Rejected - v2 is the current standard

### Alternative 3: attrs + cattrs
- **Pros:** Fast, flexible, good for data structures
- **Cons:** Separate validation library needed, less ecosystem support
- **Decision:** Rejected - Pydantic provides better all-in-one solution

### Alternative 4: Pydantic v2 Models (Chosen)
- **Pros:** Fast, excellent validation, JSON schema generation, serialization support, type inference, mature ecosystem
- **Cons:** Additional dependency
- **Decision:** Accepted - best fit for our requirements

**Decision:**

Use Pydantic v2 BaseModel for all domain models with the following conventions:

1. **All models are frozen** (`model_config = {"frozen": True}`) to ensure immutability
2. **Use Field() for all fields** with descriptions for documentation
3. **Provide sensible defaults** where appropriate
4. **Include type hints** for all fields
5. **Add comprehensive docstrings** for each model
6. **Use factory functions** (default_factory) for mutable defaults (lists, dicts)
7. **Use lambda functions** for timestamp defaults
8. **Include validation constraints** (ge, le, etc.) where appropriate

**Model Categories:**

### Business Intelligence Models
- `BusinessDomain`: Industry vertical enumeration
- `BusinessObjective`: Business question to answer
- `BusinessInsight`: Key finding from analysis
- `KPI`: Key Performance Indicator
- `KPIMetric`: Individual metric within a KPI

### Data Quality Models
- `CleaningRule`: Data cleaning action
- `ValidationIssue`: Single validation problem
- `ValidationReport`: Complete validation report

### Data Profiling Models
- `SchemaInfo`: Dataset schema information
- `ColumnProfile`: Single column profile
- `DatasetProfile`: Overall dataset profile
- `FileMetadata`: Source file information

### Analysis Output Models
- `Recommendation`: Actionable recommendation
- `InsightEvidence`: Evidence supporting insights
- `BusinessGlossaryTerm`: Domain-specific term definition
- `FeatureDefinition`: Engineered feature definition
- `BusinessRule`: Business constraint or rule

**Consequences:**

### Positive:
- Type safety across the codebase
- Automatic validation of business concepts
- Clear documentation through Field descriptions
- JSON schema generation for API documentation
- Serialization support for checkpoints
- Immutability prevents accidental state mutations
- Easy to extend with new models as needed

### Negative:
- Additional dependency on Pydantic (already used by v2)
- Learning curve for team members unfamiliar with Pydantic
- Potential performance overhead (minimal for our use case)

### Neutral:
- Models must be imported from `dataforge.core.models`
- Models are immutable, requiring `.model_copy(update={...})` for updates
- Serialization uses Pydantic's `model_dump()` method

**Future Improvements:**

1. **Custom Validators:** Add domain-specific validators (e.g., email validation, business rule validation)
2. **Helper Methods:** Add business logic methods to models (e.g., `KPI.is_on_track()`)
3. **Serialization Strategies:** Implement custom serializers for complex types if needed
4. **Model Relationships:** Add forward references for related models if needed
5. **Pydantic Extensions:** Consider Pydantic plugins for additional validation rules

**References:**

- Pydantic v2 Documentation: https://docs.pydantic.dev/latest/
- DataForge AI v2 Architecture: docs/v2/ARCHITECTURE.md
- DataForge AI v2 Sprint Plan: docs/v2/SPRINT_PLAN.md