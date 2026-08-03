"""Infrastructure interfaces for DataForge AI v2.

These interfaces define contracts for external system adapters.
Implementations live in the infrastructure layer and depend only on core models.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from dataforge.core.models import (
    BusinessInsight,
    CleaningRule,
    ColumnProfile,
    DatasetProfile,
    FileMetadata,
    KPI,
    SchemaInfo,
    ValidationReport,
)


__all__ = [
    "FileReader",
    "DataCleaner",
    "SchemaDetector",
    "ChartEngine",
    "ReportRenderer",
    "StorageProvider",
    "CacheProvider",
    "EventPublisher",
]


# ============================================================================
# FILE READING INTERFACES
# ============================================================================


class FileReader(ABC):
    """Abstract interface for reading data files.

    Implementations support different file formats (CSV, Excel, Parquet, JSON).
    All implementations must return pandas DataFrames and FileMetadata.
    """

    @abstractmethod
    def can_read(self, file_path: str | Path) -> bool:
        """Check if this reader can handle the given file.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if this reader can handle the file, False otherwise.
        """
        ...

    @abstractmethod
    async def read(self, file_path: str | Path, **kwargs: Any) -> tuple[Any, FileMetadata]:
        """Read a file and return the data with metadata.

        Args:
            file_path: Path to the file to read.
            **kwargs: Additional format-specific options.

        Returns:
            A tuple of (data, metadata) where data is a pandas DataFrame
            and metadata contains file information.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is invalid.
            IOError: If the file cannot be read.
        """
        ...

    @abstractmethod
    def validate_format(self, file_path: str | Path) -> bool:
        """Validate that the file format is correct.

        Args:
            file_path: Path to the file to validate.

        Returns:
            True if the file format is valid, False otherwise.
        """
        ...


# ============================================================================
# DATA CLEANING INTERFACES
# ============================================================================


class DataCleaner(ABC):
    """Abstract interface for data cleaning operations.

    Implementations provide various cleaning strategies for handling
    missing values, duplicates, outliers, and other data quality issues.
    """

    @abstractmethod
    async def clean(
        self, data: Any, rules: list[CleaningRule] | None = None, **kwargs: Any
    ) -> tuple[Any, list[CleaningRule]]:
        """Clean data according to specified rules.

        Args:
            data: Input data (pandas DataFrame).
            rules: Optional list of cleaning rules to apply.
                  If None, auto-detect and apply appropriate rules.
            **kwargs: Additional cleaning options.

        Returns:
            A tuple of (cleaned_data, applied_rules) where cleaned_data
            is the cleaned pandas DataFrame and applied_rules is a list
            of CleaningRule objects describing what was done.

        Raises:
            ValueError: If the data cannot be cleaned.
        """
        ...

    @abstractmethod
    async def detect_issues(self, data: Any) -> list[CleaningRule]:
        """Detect data quality issues in the data.

        Args:
            data: Input data (pandas DataFrame).

        Returns:
            A list of CleaningRule objects representing detected issues.
        """
        ...

    @abstractmethod
    def get_supported_cleaning_types(self) -> list[str]:
        """Get the list of supported cleaning types.

        Returns:
            A list of cleaning type identifiers (e.g., "missing_values",
            "duplicates", "outliers", "invalid_format").
        """
        ...


# ============================================================================
# SCHEMA DETECTION INTERFACES
# ============================================================================


class SchemaDetector(ABC):
    """Abstract interface for detecting data schema and semantic types.

    Implementations analyze data structure and infer semantic types
    (e.g., identifier, email, URL, age, currency).
    """

    @abstractmethod
    async def detect_schema(self, data: Any) -> SchemaInfo:
        """Detect the schema of the data.

        Args:
            data: Input data (pandas DataFrame).

        Returns:
            A SchemaInfo object containing detected schema information
            including column types, keys, relationships, and semantic types.

        Raises:
            ValueError: If the schema cannot be detected.
        """
        ...

    @abstractmethod
    async def detect_semantic_types(self, data: Any) -> dict[str, str]:
        """Detect semantic types for columns.

        Args:
            data: Input data (pandas DataFrame).

        Returns:
            A dictionary mapping column names to semantic type identifiers
            (e.g., "identifier", "email", "url", "age", "currency").
        """
        ...

    @abstractmethod
    async def detect_keys(self, data: Any) -> dict[str, list[str]]:
        """Detect primary and foreign keys.

        Args:
            data: Input data (pandas DataFrame).

        Returns:
            A dictionary with "primary_keys" and "foreign_keys" keys,
            each containing a list of column names.
        """
        ...


# ============================================================================
# VISUALIZATION INTERFACES
# ============================================================================


class ChartEngine(ABC):
    """Abstract interface for creating data visualizations.

    Implementations generate interactive charts in various formats.
    The interface is framework-agnostic to allow swapping Plotly,
    Matplotlib, or other visualization libraries.
    """

    @abstractmethod
    async def create_bar_chart(
        self,
        data: Any,
        x_column: str,
        y_column: str,
        title: str,
        **kwargs: Any,
    ) -> str:
        """Create a bar chart.

        Args:
            data: Input data (pandas DataFrame).
            x_column: Column name for x-axis.
            y_column: Column name for y-axis.
            title: Chart title.
            **kwargs: Additional chart options.

        Returns:
            HTML string containing the interactive chart.
        """
        ...

    @abstractmethod
    async def create_line_chart(
        self,
        data: Any,
        x_column: str,
        y_column: str,
        title: str,
        **kwargs: Any,
    ) -> str:
        """Create a line chart.

        Args:
            data: Input data (pandas DataFrame).
            x_column: Column name for x-axis (typically temporal).
            y_column: Column name for y-axis.
            title: Chart title.
            **kwargs: Additional chart options.

        Returns:
            HTML string containing the interactive chart.
        """
        ...

    @abstractmethod
    async def create_scatter_plot(
        self,
        data: Any,
        x_column: str,
        y_column: str,
        title: str,
        **kwargs: Any,
    ) -> str:
        """Create a scatter plot.

        Args:
            data: Input data (pandas DataFrame).
            x_column: Column name for x-axis.
            y_column: Column name for y-axis.
            title: Chart title.
            **kwargs: Additional chart options.

        Returns:
            HTML string containing the interactive chart.
        """
        ...

    @abstractmethod
    async def create_histogram(
        self,
        data: Any,
        column: str,
        title: str,
        **kwargs: Any,
    ) -> str:
        """Create a histogram.

        Args:
            data: Input data (pandas DataFrame).
            column: Column name to plot.
            title: Chart title.
            **kwargs: Additional chart options.

        Returns:
            HTML string containing the interactive chart.
        """
        ...

    @abstractmethod
    async def create_box_plot(
        self,
        data: Any,
        column: str,
        title: str,
        **kwargs: Any,
    ) -> str:
        """Create a box plot.

        Args:
            data: Input data (pandas DataFrame).
            column: Column name to plot.
            title: Chart title.
            **kwargs: Additional chart options.

        Returns:
            HTML string containing the interactive chart.
        """
        ...

    @abstractmethod
    async def create_correlation_heatmap(
        self,
        data: Any,
        title: str,
        **kwargs: Any,
    ) -> str:
        """Create a correlation heatmap.

        Args:
            data: Input data (pandas DataFrame).
            title: Chart title.
            **kwargs: Additional chart options.

        Returns:
            HTML string containing the interactive chart.
        """
        ...


# ============================================================================
# REPORT RENDERING INTERFACES
# ============================================================================


class ReportRenderer(ABC):
    """Abstract interface for generating analysis reports.

    Implementations support different output formats (HTML, PDF, JSON).
    Reports include visualizations, insights, KPIs, and recommendations.
    """

    @abstractmethod
    async def render_html(
        self,
        data: Any,
        profile: DatasetProfile,
        insights: list[BusinessInsight],
        kpis: list[KPI],
        visualizations: dict[str, str],
        **kwargs: Any,
    ) -> str:
        """Render an HTML report.

        Args:
            data: Input data (pandas DataFrame).
            profile: Dataset profile information.
            insights: List of business insights.
            kpis: List of KPIs.
            visualizations: Dictionary mapping visualization names to HTML strings.
            **kwargs: Additional rendering options.

        Returns:
            HTML string containing the complete report.
        """
        ...

    @abstractmethod
    async def render_pdf(
        self,
        html_content: str,
        output_path: str | Path,
        **kwargs: Any,
    ) -> Path:
        """Render an HTML report to PDF.

        Args:
            html_content: HTML content to convert.
            output_path: Path where the PDF should be saved.
            **kwargs: Additional PDF generation options.

        Returns:
            Path to the generated PDF file.

        Raises:
            IOError: If the PDF cannot be generated.
        """
        ...

    @abstractmethod
    async def render_json(
        self,
        data: Any,
        profile: DatasetProfile,
        insights: list[BusinessInsight],
        kpis: list[KPI],
        validation_report: ValidationReport | None = None,
        **kwargs: Any,
    ) -> str:
        """Render a JSON report.

        Args:
            data: Input data (pandas DataFrame).
            profile: Dataset profile information.
            insights: List of business insights.
            kpis: List of KPIs.
            validation_report: Optional validation report.
            **kwargs: Additional rendering options.

        Returns:
            JSON string containing the complete report.
        """
        ...

    @abstractmethod
    def get_supported_formats(self) -> list[str]:
        """Get the list of supported output formats.

        Returns:
            A list of format identifiers (e.g., "html", "pdf", "json").
        """
        ...


# ============================================================================
# STORAGE INTERFACES
# ============================================================================


class StorageProvider(ABC):
    """Abstract interface for storing analysis results.

    Implementations support different storage backends (local filesystem,
    S3, database, etc.) for persisting results, checkpoints, and reports.
    """

    @abstractmethod
    async def save(
        self,
        key: str,
        data: Any,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """Save data to storage.

        Args:
            key: Unique identifier for the data.
            data: Data to save (can be bytes, string, or serializable object).
            metadata: Optional metadata to associate with the data.
            **kwargs: Additional storage options.

        Returns:
            A storage URI or identifier for the saved data.

        Raises:
            IOError: If the data cannot be saved.
        """
        ...

    @abstractmethod
    async def load(
        self,
        key: str,
        **kwargs: Any,
    ) -> tuple[Any, dict[str, Any] | None]:
        """Load data from storage.

        Args:
            key: Unique identifier for the data.
            **kwargs: Additional storage options.

        Returns:
            A tuple of (data, metadata) where metadata may be None.

        Raises:
            FileNotFoundError: If the key does not exist.
            IOError: If the data cannot be loaded.
        """
        ...

    @abstractmethod
    async def delete(
        self,
        key: str,
        **kwargs: Any,
    ) -> bool:
        """Delete data from storage.

        Args:
            key: Unique identifier for the data.
            **kwargs: Additional storage options.

        Returns:
            True if the data was deleted, False if it did not exist.

        Raises:
            IOError: If the deletion fails.
        """
        ...

    @abstractmethod
    async def exists(self, key: str, **kwargs: Any) -> bool:
        """Check if data exists in storage.

        Args:
            key: Unique identifier for the data.
            **kwargs: Additional storage options.

        Returns:
            True if the data exists, False otherwise.
        """
        ...

    @abstractmethod
    async def list_keys(self, prefix: str = "", **kwargs: Any) -> list[str]:
        """List all keys in storage.

        Args:
            prefix: Optional prefix to filter keys.
            **kwargs: Additional storage options.

        Returns:
            A list of keys matching the prefix.
        """
        ...


# ============================================================================
# CACHING INTERFACES
# ============================================================================


class CacheProvider(ABC):
    """Abstract interface for caching computation results.

    Implementations support different caching backends (in-memory, Redis,
    filesystem, etc.) for improving performance of expensive operations.
    """

    @abstractmethod
    async def get(
        self,
        key: str,
        **kwargs: Any,
    ) -> Any | None:
        """Get a value from cache.

        Args:
            key: Cache key.
            **kwargs: Additional cache options.

        Returns:
            The cached value, or None if not found.
        """
        ...

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        **kwargs: Any,
    ) -> bool:
        """Set a value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds. None means no expiration.
            **kwargs: Additional cache options.

        Returns:
            True if the value was cached successfully, False otherwise.
        """
        ...

    @abstractmethod
    async def delete(
        self,
        key: str,
        **kwargs: Any,
    ) -> bool:
        """Delete a value from cache.

        Args:
            key: Cache key.
            **kwargs: Additional cache options.

        Returns:
            True if the value was deleted, False if it did not exist.
        """
        ...

    @abstractmethod
    async def clear(self, **kwargs: Any) -> bool:
        """Clear all values from cache.

        Args:
            **kwargs: Additional cache options.

        Returns:
            True if the cache was cleared successfully, False otherwise.
        """
        ...

    @abstractmethod
    async def exists(self, key: str, **kwargs: Any) -> bool:
        """Check if a key exists in cache.

        Args:
            key: Cache key.
            **kwargs: Additional cache options.

        Returns:
            True if the key exists, False otherwise.
        """
        ...


# ============================================================================
# EVENT PUBLISHING INTERFACES
# ============================================================================


class EventPublisher(ABC):
    """Abstract interface for publishing events.

    Implementations support different event backends (in-memory, Redis,
    message queue, etc.) for real-time updates and notifications.
    """

    @abstractmethod
    async def publish(
        self,
        event_type: str,
        data: dict[str, Any],
        **kwargs: Any,
    ) -> bool:
        """Publish an event.

        Args:
            event_type: Type of event (e.g., "agent_completed", "analysis_started").
            data: Event data as a dictionary.
            **kwargs: Additional publishing options.

        Returns:
            True if the event was published successfully, False otherwise.
        """
        ...

    @abstractmethod
    async def subscribe(
        self,
        event_type: str,
        callback: Any,
        **kwargs: Any,
    ) -> bool:
        """Subscribe to events of a given type.

        Args:
            event_type: Type of event to subscribe to.
            callback: Callback function to invoke when events are published.
            **kwargs: Additional subscription options.

        Returns:
            True if the subscription was successful, False otherwise.
        """
        ...

    @abstractmethod
    async def unsubscribe(
        self,
        event_type: str,
        callback: Any,
        **kwargs: Any,
    ) -> bool:
        """Unsubscribe from events of a given type.

        Args:
            event_type: Type of event to unsubscribe from.
            callback: Callback function to remove.
            **kwargs: Additional unsubscription options.

        Returns:
            True if the unsubscription was successful, False otherwise.
        """
        ...

    @abstractmethod
    def get_supported_event_types(self) -> list[str]:
        """Get the list of supported event types.

        Returns:
            A list of event type identifiers (e.g., "agent_completed",
            "analysis_started", "error_occurred").
        """
        ...