"""Lightweight Dependency Injection Container for DataForge AI v2.

This container provides dependency injection capabilities without third-party DI frameworks.
Supports singleton registration, factory registration, lazy initialization,
dependency resolution, and service existence checks.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

from dataforge.shared.errors import DataForgeError

__all__ = ["DIContainer", "ServiceNotFoundError", "CircularDependencyError"]

T = TypeVar("T")


class ServiceNotFoundError(DataForgeError):
    """Raised when a requested service is not registered in the container."""

    def __init__(self, service_type: str | type) -> None:
        service_name = service_type if isinstance(service_type, str) else service_type.__name__
        super().__init__(f"Service '{service_name}' not registered in container")


class CircularDependencyError(DataForgeError):
    """Raised when a circular dependency is detected during resolution."""

    def __init__(self, dependency_chain: list[str]) -> None:
        chain = " -> ".join(dependency_chain)
        super().__init__(f"Circular dependency detected: {chain}")


@dataclass
class ServiceDescriptor:
    """Descriptor for a registered service.

    Attributes:
        factory: Factory function to create the service instance.
        is_singleton: Whether the service should be a singleton.
        instance: Cached singleton instance (if resolved).
        is_lazy: Whether the service should be lazily initialized.
    """

    factory: Callable[..., T]
    is_singleton: bool = True
    instance: T | None = None
    is_lazy: bool = True
    dependencies: list[str] = field(default_factory=list)


class DIContainer:
    """Lightweight Dependency Injection Container.

    This container manages service registration and resolution with support for:
    - Singleton services (cached after first creation)
    - Factory services (new instance each time)
    - Lazy initialization (created only when first requested)
    - Dependency resolution (automatic injection of constructor dependencies)
    - Service existence checks

    Example:
        ```python
        container = DIContainer()

        # Register a singleton
        container.register_singleton(LLMProvider, OpenAIProvider)

        # Register a factory
        container.register_factory(FileReader, CSVReader)

        # Register with dependencies
        container.register_singleton(
            DataCleaner,
            lambda c: DataCleaner(c.resolve(StorageProvider))
        )

        # Resolve a service
        llm = container.resolve(LLMProvider)
        ```
    """

    def __init__(self) -> None:
        """Initialize the DI container."""
        self._services: dict[str, ServiceDescriptor] = {}
        self._resolving: set[str] = set()

    def register_singleton(
        self,
        service_type: type[T] | str,
        factory: Callable[..., T] | type[T],
        is_lazy: bool = True,
    ) -> None:
        """Register a singleton service.

        Singleton services are created once and cached for subsequent resolutions.

        Args:
            service_type: Type or name of the service.
            factory: Factory function or class to create the service.
            is_lazy: Whether to initialize lazily (default: True).

        Raises:
            ValueError: If the service is already registered.
        """
        service_name = self._get_service_name(service_type)
        if service_name in self._services:
            raise ValueError(f"Service '{service_name}' is already registered")

        # If factory is a class, wrap it in a lambda that accepts the container
        if inspect.isclass(factory):
            original_factory = factory
            factory = lambda c, f=original_factory: f(**self._resolve_dependencies(f))

        self._services[service_name] = ServiceDescriptor(
            factory=factory,
            is_singleton=True,
            is_lazy=is_lazy,
            dependencies=self._get_dependency_names(factory),
        )

    def register_factory(
        self,
        service_type: type[T] | str,
        factory: Callable[..., T] | type[T],
        is_lazy: bool = True,
    ) -> None:
        """Register a factory service.

        Factory services create a new instance on each resolution.

        Args:
            service_type: Type or name of the service.
            factory: Factory function or class to create the service.
            is_lazy: Whether to initialize lazily (default: True).

        Raises:
            ValueError: If the service is already registered.
        """
        service_name = self._get_service_name(service_type)
        if service_name in self._services:
            raise ValueError(f"Service '{service_name}' is already registered")

        # If factory is a class, wrap it in a lambda that accepts the container
        if inspect.isclass(factory):
            original_factory = factory
            factory = lambda c, f=original_factory: f(**self._resolve_dependencies(f))

        self._services[service_name] = ServiceDescriptor(
            factory=factory,
            is_singleton=False,
            is_lazy=is_lazy,
            dependencies=self._get_dependency_names(factory),
        )

    def register_instance(
        self,
        service_type: type[T] | str,
        instance: T,
    ) -> None:
        """Register an existing instance as a singleton.

        This is useful for pre-configured instances or when you want to
        share a specific instance across the application.

        Args:
            service_type: Type or name of the service.
            instance: The instance to register.

        Raises:
            ValueError: If the service is already registered.
        """
        service_name = self._get_service_name(service_type)
        if service_name in self._services:
            raise ValueError(f"Service '{service_name}' is already registered")

        # Create a factory that returns the instance
        factory = lambda c: instance

        self._services[service_name] = ServiceDescriptor(
            factory=factory,
            is_singleton=True,
            instance=instance,
            is_lazy=False,
        )

    def resolve(self, service_type: type[T] | str) -> T:
        """Resolve a service from the container.

        Args:
            service_type: Type or name of the service to resolve.

        Returns:
            The resolved service instance.

        Raises:
            ServiceNotFoundError: If the service is not registered.
            CircularDependencyError: If a circular dependency is detected.
        """
        service_name = self._get_service_name(service_type)

        if service_name not in self._services:
            raise ServiceNotFoundError(service_type)

        descriptor = self._services[service_name]

        # Return cached instance for singletons
        if descriptor.is_singleton and descriptor.instance is not None:
            return descriptor.instance

        # Check for circular dependencies
        if service_name in self._resolving:
            raise CircularDependencyError(list(self._resolving) + [service_name])

        # Resolve the service
        self._resolving.add(service_name)
        try:
            instance = descriptor.factory(self)
        finally:
            self._resolving.remove(service_name)

        # Cache singleton instances
        if descriptor.is_singleton:
            descriptor.instance = instance

        return instance

    def is_registered(self, service_type: type[T] | str) -> bool:
        """Check if a service is registered in the container.

        Args:
            service_type: Type or name of the service to check.

        Returns:
            True if the service is registered, False otherwise.
        """
        service_name = self._get_service_name(service_type)
        return service_name in self._services

    def has_instance(self, service_type: type[T] | str) -> bool:
        """Check if a singleton service has been instantiated.

        Args:
            service_type: Type or name of the service to check.

        Returns:
            True if the service is a registered singleton and has been instantiated,
            False otherwise.
        """
        service_name = self._get_service_name(service_type)
        if service_name not in self._services:
            return False

        descriptor = self._services[service_name]
        return descriptor.is_singleton and descriptor.instance is not None

    def clear(self) -> None:
        """Clear all registered services and instances.

        This is primarily useful for testing scenarios.
        """
        self._services.clear()
        self._resolving.clear()

    def get_registered_services(self) -> list[str]:
        """Get a list of all registered service names.

        Returns:
            List of registered service names.
        """
        return list(self._services.keys())

    def _get_service_name(self, service_type: type[T] | str) -> str:
        """Get the service name from a type or string.

        Args:
            service_type: Type or name of the service.

        Returns:
            The service name as a string.
        """
        if isinstance(service_type, str):
            return service_type
        return service_type.__name__

    def _resolve_dependencies(self, factory: Callable[..., T]) -> dict[str, Any]:
        """Resolve constructor dependencies for a factory.

        Args:
            factory: Factory function or class.

        Returns:
            Dictionary of resolved dependencies keyed by parameter name.
        """
        sig = inspect.signature(factory)
        dependencies = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            if param.annotation != inspect.Parameter.empty:
                # Use type annotation to resolve dependency
                dep_type = param.annotation
                try:
                    dependencies[param_name] = self.resolve(dep_type)
                except ServiceNotFoundError:
                    # If dependency not found and has default, skip
                    if param.default != inspect.Parameter.empty:
                        continue
                    raise
            elif param.default != inspect.Parameter.empty:
                # Use default value if no annotation
                dependencies[param_name] = param.default

        return dependencies

    def _get_dependency_names(self, factory: Callable[..., T]) -> list[str]:
        """Get the names of dependencies for a factory.

        Args:
            factory: Factory function or class.

        Returns:
            List of dependency type names.
        """
        sig = inspect.signature(factory)
        dependencies = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            if param.annotation != inspect.Parameter.empty:
                dependencies.append(self._get_service_name(param.annotation))

        return dependencies