"""Utility functions for DataForge AI."""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def generate_execution_id() -> str:
    """Generate a unique execution ID.

    Returns:
        Unique execution ID string.
    """
    return str(uuid.uuid4())


def get_timestamp() -> str:
    """Get current UTC timestamp in ISO format.

    Returns:
        ISO formatted timestamp.
    """
    return datetime.now(timezone.utc).isoformat()


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename.

    Args:
        name: String to sanitize.

    Returns:
        Sanitized filename-safe string.
    """
    # Replace invalid characters with underscore
    valid_chars = "-_.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(c if c in valid_chars else "_" for c in name)


def ensure_directory(path: Path) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to the directory.

    Returns:
        The Path object.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_bytes(bytes_size: int) -> str:
    """Format bytes into human-readable string.

    Args:
        bytes_size: Size in bytes.

    Returns:
        Formatted string (e.g., "1.5 MB").
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted string (e.g., "1m 30s").
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.0f}s"


def truncate_string(text: str, max_length: int = 100) -> str:
    """Truncate a string to a maximum length.

    Args:
        text: String to truncate.
        max_length: Maximum length.

    Returns:
        Truncated string with ellipsis if needed.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def deep_update(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    """Deep update dict1 with dict2.

    Args:
        dict1: Base dictionary.
        dict2: Dictionary with updates.

    Returns:
        Updated dictionary.
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_update(result[key], value)
        else:
            result[key] = value
    return result


def is_identifier_column(name: object) -> bool:
    """Whether a column name looks like a record identifier (``id``, ``order_id``...).

    Identifier columns are numeric but carry no measurement, so statistics,
    charts and KPIs over them are noise.
    """
    lowered = str(name).strip().lower()
    return lowered == "id" or lowered.endswith(("_id", " id", "-id")) or lowered.startswith("id_")


def analytic_columns(columns: list) -> list:
    """Drop identifier columns from a list of numeric column names."""
    return [c for c in columns if not is_identifier_column(c)]


def parse_dates_if_mostly_dates(series, threshold: float = 0.8, sample_size: int = 200):
    """Parse ``series`` as datetimes when at least ``threshold`` of non-null values parse.

    Checks a small sample first so non-date text columns are rejected without
    parsing every value (per-element dateutil parsing is very slow on large
    frames). Returns the parsed series, or None when the column is not dates.
    """
    import warnings

    import pandas as pd

    non_null = series.dropna()
    if non_null.empty:
        return None
    with warnings.catch_warnings():
        # Mixed/unknown formats fall back to per-element parsing; expected here.
        warnings.simplefilter("ignore", UserWarning)
        sample = non_null.head(sample_size)
        if pd.to_datetime(sample, errors="coerce").notna().mean() < threshold:
            return None
        parsed = pd.to_datetime(series, errors="coerce")
    if parsed[series.notna()].notna().mean() < threshold:
        return None
    return parsed
