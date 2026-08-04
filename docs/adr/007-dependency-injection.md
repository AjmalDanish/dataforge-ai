# ADR 007: Dependency Injection Container

## Status
Accepted

## Date
2026-08-04

## Context
DataForge AI v2 requires a clean architecture with proper separation of concerns. The architecture document specifies that:

1. All cross-cutting dependencies should be injected, not instantiated inside agents
2. A lightweight DI container should assemble all agents with their dependencies at startup
3. The container should avoid third-party DI frameworks to maintain simplicity

In v1, agents directly imported external libraries (pandas, plotly, scipy), creating tight coupling and making testing difficult. v2 needs a clean dependency injection mechanism that:

- Supports singleton services (e.g., LLMProvider, Logger)
- Supports factory services (e.g., FileReader instances)
- Supports lazy initialization (services created only when needed)
- Supports automatic dependency resolution
- Provides service existence checks

## Decision
Implement a lightweight, custom Dependency Injection (DI) Container in `dataforge/shared/container.py` that provides:

### Core Features

1. **Singleton Registration**: Services registered as singletons are created once and cached
2. **Factory Registration**: Services registered as factories create new instances on each resolution
3. **Lazy Initialization**: Services are instantiated only when first requested
4. **Dependency Resolution**: Constructor dependencies are automatically resolved using type annotations
5. **Service Existence Checks**: Methods to check if services are registered or instantiated

### API Design

```python
container = DIContainer()

# Register a singleton service
container.register_singleton(LLMProvider, OpenAIProvider)

# Register a factory service
container.register_factory(FileReader, CSVReader)

# Register an existing instance
container.register_instance(Config, config_instance)

# Resolve a service
llm = container.resolve(LLMProvider)

# Check service existence
if container.is_registered(LLMProvider):
    llm = container.resolve(LLMProvider)

# Check if singleton is instantiated
if container.has_instance(LLMProvider):
    # Service already created
    pass
```

### Architecture

The container consists of:

1. **ServiceDescriptor**: Data class holding service metadata
   - Factory function
   - Singleton flag
   - Cached instance
   - Lazy initialization flag
   - Dependency list

2. **DIContainer**: Main container class
   - Service registry (dict of service_name → ServiceDescriptor)
   - Resolution tracking (for circular dependency detection)
   - Registration methods (singleton, factory, instance)
   - Resolution method with automatic dependency injection
   - Existence check methods

### Dependency Resolution

The container uses Python's `inspect` module to analyze factory signatures and resolve dependencies:

1. Extract constructor signature
2. Identify type annotations
3. Resolve dependencies recursively
4. Detect circular dependencies
5. Inject resolved dependencies

### Services to Support

The container will support the following services:

- **Configuration**: Application configuration (singleton)
- **LLMProvider**: LLM abstraction (singleton)
- **FileReader**: File reading adapters (factory)
- **DataCleaner**: Data cleaning operations (singleton)
- **SchemaDetector**: Schema detection (singleton)
- **ChartEngine**: Visualization generation (singleton)
- **ReportRenderer**: Report generation (singleton)
- **StorageProvider**: Result storage (singleton)
- **CacheProvider**: Caching backend (singleton)
- **EventPublisher**: Event publishing (singleton)

### Error Handling

The container defines custom exceptions:

- **ServiceNotFoundError**: Raised when resolving an unregistered service
- **CircularDependencyError**: Raised when circular dependencies are detected

## Consequences

### Positive

1. **Clean Separation**: Agents no longer instantiate dependencies directly
2. **Testability**: Dependencies can be easily mocked in tests
3. **Flexibility**: Implementations can be swapped without changing agents
4. **Lazy Loading**: Services only created when needed
5. **No External Dependencies**: Custom implementation avoids third-party DI frameworks
6. **Type Safety**: Uses type annotations for dependency resolution

### Negative

1. **Learning Curve**: Developers need to understand DI patterns
2. **Runtime Errors**: Dependency issues only discovered at runtime
3. **Limited Features**: Lacks advanced features of full-featured DI containers (scopes, decorators, etc.)

### Risks

1. **Circular Dependencies**: Could occur if not carefully managed
   - Mitigation: Container detects and raises CircularDependencyError
2. **Complex Dependencies**: Deep dependency trees could be hard to debug
   - Mitigation: Clear documentation and testing

## Alternatives Considered

### 1. Third-party DI Frameworks (injector, punq, etc.)
**Pros:**
- More features
- Better tested
- Community support

**Cons:**
- Additional dependency
- Overkill for our needs
- Learning curve for framework-specific APIs

**Decision:** Rejected - Keep it lightweight and simple

### 2. Manual Wiring (no container)
**Pros:**
- No container complexity
- Explicit dependencies

**Cons:**
- Boilerplate code
- Hard to test
- No lazy loading
- Difficult to manage as code grows

**Decision:** Rejected - Container provides needed flexibility

### 3. Global Singletons
**Pros:**
- Simple to implement
- No container needed

**Cons:**
- Hard to test
- No lazy loading
- Global state issues
- Can't swap implementations

**Decision:** Rejected - Violates clean architecture principles

## Implementation

The implementation is in `dataforge/shared/container.py` and includes:

- `ServiceDescriptor`: Data class for service metadata
- `DIContainer`: Main container class with all registration and resolution methods
- Custom exceptions: `ServiceNotFoundError`, `CircularDependencyError`

Unit tests are in `tests/unit/test_container.py` covering:

- Singleton registration and resolution
- Factory registration and resolution
- Instance registration
- Lazy initialization
- Dependency resolution
- Circular dependency detection
- Service existence checks
- Error handling

## Future Considerations

1. **Scopes**: Add support for request-scoped services (if needed for web layer)
2. **Decorators**: Add `@inject` decorator for automatic injection
3. **Configuration**: Support configuration-based registration
4. **Lifecycle Hooks**: Add initialization/disposal hooks
5. **Async Resolution**: Add async factory support if needed

## References

- [Architecture Document](../v2/ARCHITECTURE.md)
- [Sprint Plan](../v2/SPRINT_PLAN.md)
- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Dependency Injection Pattern](https://en.wikipedia.org/wiki/Dependency_injection)