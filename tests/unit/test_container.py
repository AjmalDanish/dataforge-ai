"""Unit tests for the Dependency Injection Container."""

import pytest

from dataforge.shared.container import (
    CircularDependencyError,
    DIContainer,
    ServiceNotFoundError,
)


@pytest.fixture(autouse=True)
def reset_counter_service() -> None:
    """Reset CounterService instance count before each test."""
    CounterService.instance_count = 0
    yield
    CounterService.instance_count = 0


# ============================================================================
# Test Fixtures
# ============================================================================


class SimpleService:
    """A simple service for testing."""

    def __init__(self) -> None:
        self.value = "simple"


class ServiceWithDependency:
    """A service that depends on another service."""

    def __init__(self, dependency: SimpleService) -> None:
        self.dependency = dependency
        self.value = "with_dependency"


class ServiceWithMultipleDependencies:
    """A service with multiple dependencies."""

    def __init__(
        self,
        simple: SimpleService,
        with_dep: ServiceWithDependency,
    ) -> None:
        self.simple = simple
        self.with_dep = with_dep
        self.value = "multiple_dependencies"


class ServiceWithDefault:
    """A service with a default parameter."""

    def __init__(self, dependency: SimpleService, optional: str = "default") -> None:
        self.dependency = dependency
        self.optional = optional
        self.value = "with_default"


class CounterService:
    """A service that counts instances."""

    instance_count = 0

    def __init__(self) -> None:
        CounterService.instance_count += 1
        self.value = f"instance_{CounterService.instance_count}"


class CircularA:
    """Service A that depends on B."""

    def __init__(self, b: CircularB) -> None:
        self.b = b


class CircularB:
    """Service B that depends on A."""

    def __init__(self, a: CircularA) -> None:
        self.a = a


# ============================================================================
# Singleton Registration Tests
# ============================================================================


def test_register_singleton_with_class() -> None:
    """Test registering a singleton service with a class."""
    container = DIContainer()
    container.register_singleton(SimpleService, SimpleService)

    assert container.is_registered(SimpleService)
    assert container.is_registered("SimpleService")


def test_register_singleton_with_factory() -> None:
    """Test registering a singleton service with a factory function."""
    container = DIContainer()

    def factory(c):
        return SimpleService()

    container.register_singleton(SimpleService, factory)
    assert container.is_registered(SimpleService)


def test_register_singleton_duplicate_raises_error() -> None:
    """Test that registering a duplicate service raises ValueError."""
    container = DIContainer()
    container.register_singleton(SimpleService, SimpleService)

    with pytest.raises(ValueError, match="already registered"):
        container.register_singleton(SimpleService, SimpleService)


def test_resolve_singleton_returns_same_instance() -> None:
    """Test that resolving a singleton returns the same instance."""
    container = DIContainer()
    container.register_singleton(CounterService, CounterService)

    instance1 = container.resolve(CounterService)
    instance2 = container.resolve(CounterService)

    assert instance1 is instance2
    assert CounterService.instance_count == 1


def test_resolve_singleton_by_string_name() -> None:
    """Test resolving a singleton by string name."""
    container = DIContainer()
    container.register_singleton(SimpleService, SimpleService)

    service = container.resolve("SimpleService")
    assert isinstance(service, SimpleService)


# ============================================================================
# Factory Registration Tests
# ============================================================================


def test_register_factory_with_class() -> None:
    """Test registering a factory service with a class."""
    container = DIContainer()
    container.register_factory(CounterService, CounterService)

    assert container.is_registered(CounterService)


def test_register_factory_with_factory() -> None:
    """Test registering a factory service with a factory function."""
    container = DIContainer()

    def factory(c):
        return CounterService()

    container.register_factory(CounterService, factory)
    assert container.is_registered(CounterService)


def test_register_factory_duplicate_raises_error() -> None:
    """Test that registering a duplicate factory raises ValueError."""
    container = DIContainer()
    container.register_factory(CounterService, CounterService)

    with pytest.raises(ValueError, match="already registered"):
        container.register_factory(CounterService, CounterService)


def test_resolve_factory_returns_new_instance() -> None:
    """Test that resolving a factory returns a new instance each time."""
    container = DIContainer()
    container.register_factory(CounterService, CounterService)

    instance1 = container.resolve(CounterService)
    instance2 = container.resolve(CounterService)

    assert instance1 is not instance2
    assert CounterService.instance_count == 2


# ============================================================================
# Instance Registration Tests
# ============================================================================


def test_register_instance() -> None:
    """Test registering an existing instance."""
    container = DIContainer()
    instance = SimpleService()

    container.register_instance(SimpleService, instance)

    assert container.is_registered(SimpleService)
    assert container.has_instance(SimpleService)


def test_register_instance_duplicate_raises_error() -> None:
    """Test that registering a duplicate instance raises ValueError."""
    container = DIContainer()
    instance = SimpleService()
    container.register_instance(SimpleService, instance)

    with pytest.raises(ValueError, match="already registered"):
        container.register_instance(SimpleService, SimpleService())


def test_resolve_instance_returns_registered_instance() -> None:
    """Test that resolving a registered instance returns the same instance."""
    container = DIContainer()
    instance = SimpleService()
    container.register_instance(SimpleService, instance)

    resolved = container.resolve(SimpleService)

    assert resolved is instance


# ============================================================================
# Dependency Resolution Tests
# ============================================================================


def test_resolve_service_with_dependency() -> None:
    """Test resolving a service that has a dependency."""
    container = DIContainer()
    container.register_singleton(SimpleService, SimpleService)
    container.register_singleton(ServiceWithDependency, ServiceWithDependency)

    service = container.resolve(ServiceWithDependency)

    assert isinstance(service, ServiceWithDependency)
    assert isinstance(service.dependency, SimpleService)


def test_resolve_service_with_multiple_dependencies() -> None:
    """Test resolving a service with multiple dependencies."""
    container = DIContainer()
    container.register_singleton(SimpleService, SimpleService)
    container.register_singleton(ServiceWithDependency, ServiceWithDependency)
    container.register_singleton(ServiceWithMultipleDependencies, ServiceWithMultipleDependencies)

    service = container.resolve(ServiceWithMultipleDependencies)

    assert isinstance(service, ServiceWithMultipleDependencies)
    assert isinstance(service.simple, SimpleService)
    assert isinstance(service.with_dep, ServiceWithDependency)


def test_resolve_service_with_default_parameter() -> None:
    """Test resolving a service with a default parameter."""
    container = DIContainer()
    container.register_singleton(SimpleService, SimpleService)
    container.register_singleton(ServiceWithDefault, ServiceWithDefault)

    service = container.resolve(ServiceWithDefault)

    assert isinstance(service, ServiceWithDefault)
    assert isinstance(service.dependency, SimpleService)
    assert service.optional == "default"


def test_resolve_singleton_with_factory_dependency() -> None:
    """Test resolving a singleton that depends on a factory service."""
    container = DIContainer()
    container.register_factory(CounterService, CounterService)
    container.register_singleton(ServiceWithDependency, ServiceWithDependency)

    # This should fail because ServiceWithDependency depends on SimpleService, not CounterService
    with pytest.raises(ServiceNotFoundError):
        container.resolve(ServiceWithDependency)


def test_resolve_factory_with_singleton_dependency() -> None:
    """Test resolving a factory service that depends on a singleton."""
    container = DIContainer()
    container.register_singleton(SimpleService, SimpleService)
    container.register_factory(ServiceWithDependency, ServiceWithDependency)

    instance1 = container.resolve(ServiceWithDependency)
    instance2 = container.resolve(ServiceWithDependency)

    # Factory creates new instances
    assert instance1 is not instance2
    # But both share the same singleton dependency
    assert instance1.dependency is instance2.dependency


# ============================================================================
# Circular Dependency Detection Tests
# ============================================================================


def test_circular_dependency_detection() -> None:
    """Test that circular dependencies are detected."""
    container = DIContainer()
    container.register_singleton(CircularA, CircularA)
    container.register_singleton(CircularB, CircularB)

    with pytest.raises(CircularDependencyError, match="Circular dependency detected"):
        container.resolve(CircularA)


def test_circular_dependency_chain_included_in_error() -> None:
    """Test that the circular dependency chain is included in the error."""
    container = DIContainer()
    container.register_singleton(CircularA, CircularA)
    container.register_singleton(CircularB, CircularB)

    with pytest.raises(CircularDependencyError) as exc_info:
        container.resolve(CircularA)

    error_message = str(exc_info.value)
    assert "CircularA" in error_message
    assert "CircularB" in error_message


# ============================================================================
# Service Existence Check Tests
# ============================================================================


def test_is_registered_true() -> None:
    """Test is_registered returns True for registered services."""
    container = DIContainer()
    container.register_singleton(SimpleService, SimpleService)

    assert container.is_registered(SimpleService)
    assert container.is_registered("SimpleService")


def test_is_registered_false() -> None:
    """Test is_registered returns False for unregistered services."""
    container = DIContainer()

    assert not container.is_registered(SimpleService)
    assert not container.is_registered("SimpleService")


def test_has_instance_true_for_resolved_singleton() -> None:
    """Test has_instance returns True for resolved singletons."""
    container = DIContainer()
    container.register_singleton(SimpleService, SimpleService)

    # Before resolution
    assert not container.has_instance(SimpleService)

    # After resolution
    container.resolve(SimpleService)
    assert container.has_instance(SimpleService)


def test_has_instance_false_for_unresolved_singleton() -> None:
    """Test has_instance returns False for unresolved singletons."""
    container = DIContainer()
    container.register_singleton(SimpleService, SimpleService)

    assert not container.has_instance(SimpleService)


def test_has_instance_false_for_factory() -> None:
    """Test has_instance returns False for factory services."""
    container = DIContainer()
    container.register_factory(CounterService, CounterService)

    container.resolve(CounterService)
    assert not container.has_instance(CounterService)


def test_has_instance_false_for_unregistered() -> None:
    """Test has_instance returns False for unregistered services."""
    container = DIContainer()

    assert not container.has_instance(SimpleService)


# ============================================================================
# Lazy Initialization Tests
# ============================================================================


def test_lazy_initialization_singleton() -> None:
    """Test that singletons are lazily initialized."""
    container = DIContainer()
    container.register_singleton(CounterService, CounterService)

    # Service not yet created
    assert CounterService.instance_count == 0
    assert not container.has_instance(CounterService)

    # Resolve creates the instance
    container.resolve(CounterService)
    assert CounterService.instance_count == 1
    assert container.has_instance(CounterService)


def test_lazy_initialization_factory() -> None:
    """Test that factories are lazily initialized."""
    container = DIContainer()
    container.register_factory(CounterService, CounterService)

    # Service not yet created
    assert CounterService.instance_count == 0

    # Resolve creates the instance
    container.resolve(CounterService)
    assert CounterService.instance_count == 1


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_resolve_unregistered_service_raises_error() -> None:
    """Test that resolving an unregistered service raises ServiceNotFoundError."""
    container = DIContainer()

    with pytest.raises(ServiceNotFoundError, match="not registered"):
        container.resolve(SimpleService)


def test_resolve_unregistered_service_by_string_raises_error() -> None:
    """Test that resolving an unregistered service by string raises error."""
    container = DIContainer()

    with pytest.raises(ServiceNotFoundError, match="not registered"):
        container.resolve("NonExistentService")


# ============================================================================
# Container Management Tests
# ============================================================================


def test_get_registered_services() -> None:
    """Test getting a list of registered services."""
    container = DIContainer()
    container.register_singleton(SimpleService, SimpleService)
    container.register_factory(CounterService, CounterService)
    container.register_instance(ServiceWithDependency, ServiceWithDependency(SimpleService()))

    services = container.get_registered_services()

    assert len(services) == 3
    assert "SimpleService" in services
    assert "CounterService" in services
    assert "ServiceWithDependency" in services


def test_clear_container() -> None:
    """Test clearing the container."""
    container = DIContainer()
    container.register_singleton(SimpleService, SimpleService)
    container.register_factory(CounterService, CounterService)

    # Verify services are registered
    assert len(container.get_registered_services()) == 2

    # Clear the container
    container.clear()

    # Verify services are cleared
    assert len(container.get_registered_services()) == 0
    assert not container.is_registered(SimpleService)
    assert not container.is_registered(CounterService)


# ============================================================================
# Integration Tests
# ============================================================================


def test_complex_dependency_tree() -> None:
    """Test resolving a complex dependency tree."""
    container = DIContainer()
    container.register_singleton(SimpleService, SimpleService)
    container.register_singleton(ServiceWithDependency, ServiceWithDependency)
    container.register_singleton(ServiceWithMultipleDependencies, ServiceWithMultipleDependencies)

    # Resolve the top-level service
    service = container.resolve(ServiceWithMultipleDependencies)

    # Verify all dependencies are resolved correctly
    assert isinstance(service, ServiceWithMultipleDependencies)
    assert isinstance(service.simple, SimpleService)
    assert isinstance(service.with_dep, ServiceWithDependency)
    assert isinstance(service.with_dep.dependency, SimpleService)

    # Verify singletons are shared
    assert service.simple is service.with_dep.dependency


def test_mixed_singleton_and_factory() -> None:
    """Test using both singletons and factories together."""
    container = DIContainer()
    container.register_singleton(SimpleService, SimpleService)
    container.register_factory(CounterService, CounterService)

    # Resolve singleton multiple times
    simple1 = container.resolve(SimpleService)
    simple2 = container.resolve(SimpleService)
    assert simple1 is simple2

    # Resolve factory multiple times
    counter1 = container.resolve(CounterService)
    counter2 = container.resolve(CounterService)
    assert counter1 is not counter2


def test_instance_registration_overrides_lazy() -> None:
    """Test that instance registration is not lazy."""
    container = DIContainer()
    instance = SimpleService()

    container.register_instance(SimpleService, instance)

    # Instance should be available immediately
    assert container.has_instance(SimpleService)
    assert container.resolve(SimpleService) is instance


def test_service_name_from_type() -> None:
    """Test that service names are correctly derived from types."""
    container = DIContainer()

    # Register with type
    container.register_singleton(SimpleService, SimpleService)
    assert container.is_registered("SimpleService")

    # Register with string name
    container.register_factory("CustomService", SimpleService)
    assert container.is_registered("CustomService")

    # Resolve both
    simple = container.resolve(SimpleService)
    custom = container.resolve("CustomService")

    assert isinstance(simple, SimpleService)
    assert isinstance(custom, SimpleService)
    assert simple is not custom  # Different instances (one singleton, one factory)