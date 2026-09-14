"""File reader registration for DI Container.

This module provides a function to register all file readers with the DI Container.
"""

from dataforge.infrastructure.readers import CSVReader, ExcelReader, JSONReader, ParquetReader
from dataforge.shared.container import DIContainer


def register_file_readers(container: DIContainer) -> None:
    """Register all file readers with the DI Container.

    File readers are registered as factories (new instance per request)
    since they are stateless and lightweight.

    Args:
        container: The DI Container instance to register readers with.
    """
    # Register CSVReader as factory
    container.register_factory(CSVReader, CSVReader, is_lazy=True)

    # Register ExcelReader as factory
    container.register_factory(ExcelReader, ExcelReader, is_lazy=True)

    # Register ParquetReader as factory
    container.register_factory(ParquetReader, ParquetReader, is_lazy=True)

    # Register JSONReader as factory
    container.register_factory(JSONReader, JSONReader, is_lazy=True)


def get_reader_for_file(container: DIContainer, file_path: str) -> CSVReader | ExcelReader | ParquetReader | JSONReader | None:
    """Get the appropriate reader for a file based on its extension.

    Args:
        container: The DI Container instance.
        file_path: Path to the file to find a reader for.

    Returns:
        The appropriate reader instance, or None if no reader supports the file.
    """
    from pathlib import Path

    path = Path(file_path)

    # Try each reader to see if it can read the file
    readers = [CSVReader, ExcelReader, ParquetReader, JSONReader]

    for reader_class in readers:
        reader = container.resolve(reader_class)
        if reader.can_read(path):
            return reader

    return None