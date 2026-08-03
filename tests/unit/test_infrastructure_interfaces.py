"""Unit tests for infrastructure interfaces."""

from pathlib import Path

import pytest

from dataforge.infrastructure.interfaces import (
    CacheProvider,
    ChartEngine,
    DataCleaner,
    EventPublisher,
    FileReader,
    ReportRenderer,
    SchemaDetector,
    StorageProvider,
)


# ============================================================================
# FILE READER TESTS
# ============================================================================


class TestFileReader:
    """Tests for FileReader interface."""

    def test_filereader_is_abstract(self) -> None:
        """Test FileReader is an abstract class."""
        with pytest.raises(TypeError):
            FileReader()

    def test_filereader_has_can_read_method(self) -> None:
        """Test FileReader has can_read abstract method."""
        assert hasattr(FileReader, "can_read")
        assert getattr(FileReader, "can_read").__isabstractmethod__

    def test_filereader_has_read_method(self) -> None:
        """Test FileReader has read abstract method."""
        assert hasattr(FileReader, "read")
        assert getattr(FileReader, "read").__isabstractmethod__

    def test_filereader_has_validate_format_method(self) -> None:
        """Test FileReader has validate_format abstract method."""
        assert hasattr(FileReader, "validate_format")
        assert getattr(FileReader, "validate_format").__isabstractmethod__


# ============================================================================
# DATA CLEANER TESTS
# ============================================================================


class TestDataCleaner:
    """Tests for DataCleaner interface."""

    def test_datacleaner_is_abstract(self) -> None:
        """Test DataCleaner is an abstract class."""
        with pytest.raises(TypeError):
            DataCleaner()

    def test_datacleaner_has_clean_method(self) -> None:
        """Test DataCleaner has clean abstract method."""
        assert hasattr(DataCleaner, "clean")
        assert getattr(DataCleaner, "clean").__isabstractmethod__

    def test_datacleaner_has_detect_issues_method(self) -> None:
        """Test DataCleaner has detect_issues abstract method."""
        assert hasattr(DataCleaner, "detect_issues")
        assert getattr(DataCleaner, "detect_issues").__isabstractmethod__

    def test_datacleaner_has_get_supported_cleaning_types_method(self) -> None:
        """Test DataCleaner has get_supported_cleaning_types abstract method."""
        assert hasattr(DataCleaner, "get_supported_cleaning_types")
        assert getattr(DataCleaner, "get_supported_cleaning_types").__isabstractmethod__


# ============================================================================
# SCHEMA DETECTOR TESTS
# ============================================================================


class TestSchemaDetector:
    """Tests for SchemaDetector interface."""

    def test_schemadetector_is_abstract(self) -> None:
        """Test SchemaDetector is an abstract class."""
        with pytest.raises(TypeError):
            SchemaDetector()

    def test_schemadetector_has_detect_schema_method(self) -> None:
        """Test SchemaDetector has detect_schema abstract method."""
        assert hasattr(SchemaDetector, "detect_schema")
        assert getattr(SchemaDetector, "detect_schema").__isabstractmethod__

    def test_schemadetector_has_detect_semantic_types_method(self) -> None:
        """Test SchemaDetector has detect_semantic_types abstract method."""
        assert hasattr(SchemaDetector, "detect_semantic_types")
        assert getattr(SchemaDetector, "detect_semantic_types").__isabstractmethod__

    def test_schemadetector_has_detect_keys_method(self) -> None:
        """Test SchemaDetector has detect_keys abstract method."""
        assert hasattr(SchemaDetector, "detect_keys")
        assert getattr(SchemaDetector, "detect_keys").__isabstractmethod__


# ============================================================================
# CHART ENGINE TESTS
# ============================================================================


class TestChartEngine:
    """Tests for ChartEngine interface."""

    def test_chartengine_is_abstract(self) -> None:
        """Test ChartEngine is an abstract class."""
        with pytest.raises(TypeError):
            ChartEngine()

    def test_chartengine_has_create_bar_chart_method(self) -> None:
        """Test ChartEngine has create_bar_chart abstract method."""
        assert hasattr(ChartEngine, "create_bar_chart")
        assert getattr(ChartEngine, "create_bar_chart").__isabstractmethod__

    def test_chartengine_has_create_line_chart_method(self) -> None:
        """Test ChartEngine has create_line_chart abstract method."""
        assert hasattr(ChartEngine, "create_line_chart")
        assert getattr(ChartEngine, "create_line_chart").__isabstractmethod__

    def test_chartengine_has_create_scatter_plot_method(self) -> None:
        """Test ChartEngine has create_scatter_plot abstract method."""
        assert hasattr(ChartEngine, "create_scatter_plot")
        assert getattr(ChartEngine, "create_scatter_plot").__isabstractmethod__

    def test_chartengine_has_create_histogram_method(self) -> None:
        """Test ChartEngine has create_histogram abstract method."""
        assert hasattr(ChartEngine, "create_histogram")
        assert getattr(ChartEngine, "create_histogram").__isabstractmethod__

    def test_chartengine_has_create_box_plot_method(self) -> None:
        """Test ChartEngine has create_box_plot abstract method."""
        assert hasattr(ChartEngine, "create_box_plot")
        assert getattr(ChartEngine, "create_box_plot").__isabstractmethod__

    def test_chartengine_has_create_correlation_heatmap_method(self) -> None:
        """Test ChartEngine has create_correlation_heatmap abstract method."""
        assert hasattr(ChartEngine, "create_correlation_heatmap")
        assert getattr(ChartEngine, "create_correlation_heatmap").__isabstractmethod__


# ============================================================================
# REPORT RENDERER TESTS
# ============================================================================


class TestReportRenderer:
    """Tests for ReportRenderer interface."""

    def test_reportrenderer_is_abstract(self) -> None:
        """Test ReportRenderer is an abstract class."""
        with pytest.raises(TypeError):
            ReportRenderer()

    def test_reportrenderer_has_render_html_method(self) -> None:
        """Test ReportRenderer has render_html abstract method."""
        assert hasattr(ReportRenderer, "render_html")
        assert getattr(ReportRenderer, "render_html").__isabstractmethod__

    def test_reportrenderer_has_render_pdf_method(self) -> None:
        """Test ReportRenderer has render_pdf abstract method."""
        assert hasattr(ReportRenderer, "render_pdf")
        assert getattr(ReportRenderer, "render_pdf").__isabstractmethod__

    def test_reportrenderer_has_render_json_method(self) -> None:
        """Test ReportRenderer has render_json abstract method."""
        assert hasattr(ReportRenderer, "render_json")
        assert getattr(ReportRenderer, "render_json").__isabstractmethod__

    def test_reportrenderer_has_get_supported_formats_method(self) -> None:
        """Test ReportRenderer has get_supported_formats abstract method."""
        assert hasattr(ReportRenderer, "get_supported_formats")
        assert getattr(ReportRenderer, "get_supported_formats").__isabstractmethod__


# ============================================================================
# STORAGE PROVIDER TESTS
# ============================================================================


class TestStorageProvider:
    """Tests for StorageProvider interface."""

    def test_storageprovider_is_abstract(self) -> None:
        """Test StorageProvider is an abstract class."""
        with pytest.raises(TypeError):
            StorageProvider()

    def test_storageprovider_has_save_method(self) -> None:
        """Test StorageProvider has save abstract method."""
        assert hasattr(StorageProvider, "save")
        assert getattr(StorageProvider, "save").__isabstractmethod__

    def test_storageprovider_has_load_method(self) -> None:
        """Test StorageProvider has load abstract method."""
        assert hasattr(StorageProvider, "load")
        assert getattr(StorageProvider, "load").__isabstractmethod__

    def test_storageprovider_has_delete_method(self) -> None:
        """Test StorageProvider has delete abstract method."""
        assert hasattr(StorageProvider, "delete")
        assert getattr(StorageProvider, "delete").__isabstractmethod__

    def test_storageprovider_has_exists_method(self) -> None:
        """Test StorageProvider has exists abstract method."""
        assert hasattr(StorageProvider, "exists")
        assert getattr(StorageProvider, "exists").__isabstractmethod__

    def test_storageprovider_has_list_keys_method(self) -> None:
        """Test StorageProvider has list_keys abstract method."""
        assert hasattr(StorageProvider, "list_keys")
        assert getattr(StorageProvider, "list_keys").__isabstractmethod__


# ============================================================================
# CACHE PROVIDER TESTS
# ============================================================================


class TestCacheProvider:
    """Tests for CacheProvider interface."""

    def test_cacheprovider_is_abstract(self) -> None:
        """Test CacheProvider is an abstract class."""
        with pytest.raises(TypeError):
            CacheProvider()

    def test_cacheprovider_has_get_method(self) -> None:
        """Test CacheProvider has get abstract method."""
        assert hasattr(CacheProvider, "get")
        assert getattr(CacheProvider, "get").__isabstractmethod__

    def test_cacheprovider_has_set_method(self) -> None:
        """Test CacheProvider has set abstract method."""
        assert hasattr(CacheProvider, "set")
        assert getattr(CacheProvider, "set").__isabstractmethod__

    def test_cacheprovider_has_delete_method(self) -> None:
        """Test CacheProvider has delete abstract method."""
        assert hasattr(CacheProvider, "delete")
        assert getattr(CacheProvider, "delete").__isabstractmethod__

    def test_cacheprovider_has_clear_method(self) -> None:
        """Test CacheProvider has clear abstract method."""
        assert hasattr(CacheProvider, "clear")
        assert getattr(CacheProvider, "clear").__isabstractmethod__

    def test_cacheprovider_has_exists_method(self) -> None:
        """Test CacheProvider has exists abstract method."""
        assert hasattr(CacheProvider, "exists")
        assert getattr(CacheProvider, "exists").__isabstractmethod__


# ============================================================================
# EVENT PUBLISHER TESTS
# ============================================================================


class TestEventPublisher:
    """Tests for EventPublisher interface."""

    def test_eventpublisher_is_abstract(self) -> None:
        """Test EventPublisher is an abstract class."""
        with pytest.raises(TypeError):
            EventPublisher()

    def test_eventpublisher_has_publish_method(self) -> None:
        """Test EventPublisher has publish abstract method."""
        assert hasattr(EventPublisher, "publish")
        assert getattr(EventPublisher, "publish").__isabstractmethod__

    def test_eventpublisher_has_subscribe_method(self) -> None:
        """Test EventPublisher has subscribe abstract method."""
        assert hasattr(EventPublisher, "subscribe")
        assert getattr(EventPublisher, "subscribe").__isabstractmethod__

    def test_eventpublisher_has_unsubscribe_method(self) -> None:
        """Test EventPublisher has unsubscribe abstract method."""
        assert hasattr(EventPublisher, "unsubscribe")
        assert getattr(EventPublisher, "unsubscribe").__isabstractmethod__

    def test_eventpublisher_has_get_supported_event_types_method(self) -> None:
        """Test EventPublisher has get_supported_event_types abstract method."""
        assert hasattr(EventPublisher, "get_supported_event_types")
        assert getattr(EventPublisher, "get_supported_event_types").__isabstractmethod__


# ============================================================================
# MOCK IMPLEMENTATION TESTS
# ============================================================================


class MockFileReader(FileReader):
    """Mock FileReader implementation for testing."""

    def can_read(self, file_path: str | Path) -> bool:
        return str(file_path).endswith(".csv")

    async def read(self, file_path: str | Path, **kwargs):
        return None, None

    def validate_format(self, file_path: str | Path) -> bool:
        return str(file_path).endswith(".csv")


class TestMockFileReader:
    """Tests for mock FileReader implementation."""

    def test_mock_filereader_can_be_instantiated(self) -> None:
        """Test mock FileReader can be instantiated."""
        reader = MockFileReader()
        assert reader is not None

    def test_mock_filereader_can_read(self) -> None:
        """Test mock FileReader can_read method."""
        reader = MockFileReader()
        assert reader.can_read("test.csv") is True
        assert reader.can_read("test.txt") is False

    def test_mock_filereader_validate_format(self) -> None:
        """Test mock FileReader validate_format method."""
        reader = MockFileReader()
        assert reader.validate_format("test.csv") is True
        assert reader.validate_format("test.txt") is False


class MockStorageProvider(StorageProvider):
    """Mock StorageProvider implementation for testing."""

    def __init__(self):
        self.storage = {}

    async def save(self, key: str, data, metadata=None, **kwargs):
        self.storage[key] = (data, metadata)
        return f"storage://{key}"

    async def load(self, key: str, **kwargs):
        if key not in self.storage:
            raise FileNotFoundError(f"Key not found: {key}")
        return self.storage[key]

    async def delete(self, key: str, **kwargs):
        if key in self.storage:
            del self.storage[key]
            return True
        return False

    async def exists(self, key: str, **kwargs):
        return key in self.storage

    async def list_keys(self, prefix: str = "", **kwargs):
        return [k for k in self.storage.keys() if k.startswith(prefix)]


class TestMockStorageProvider:
    """Tests for mock StorageProvider implementation."""

    @pytest.mark.asyncio
    async def test_mock_storageprovider_save_and_load(self) -> None:
        """Test mock StorageProvider save and load methods."""
        provider = MockStorageProvider()
        uri = await provider.save("test_key", "test_data", {"meta": "data"})
        assert uri == "storage://test_key"

        data, metadata = await provider.load("test_key")
        assert data == "test_data"
        assert metadata == {"meta": "data"}

    @pytest.mark.asyncio
    async def test_mock_storageprovider_delete(self) -> None:
        """Test mock StorageProvider delete method."""
        provider = MockStorageProvider()
        await provider.save("test_key", "test_data")
        assert await provider.exists("test_key") is True

        result = await provider.delete("test_key")
        assert result is True
        assert await provider.exists("test_key") is False

    @pytest.mark.asyncio
    async def test_mock_storageprovider_list_keys(self) -> None:
        """Test mock StorageProvider list_keys method."""
        provider = MockStorageProvider()
        await provider.save("prefix_key1", "data1")
        await provider.save("prefix_key2", "data2")
        await provider.save("other_key", "data3")

        keys = await provider.list_keys("prefix_")
        assert keys == ["prefix_key1", "prefix_key2"]