"""Base utilities and decorators for file readers.

This module provides shared functionality for all file reader implementations,
including error handling decorators and encoding detection utilities.
"""

from functools import wraps
from pathlib import Path
from typing import Any, Callable

from dataforge.shared.errors import DataIngestionError


def handle_file_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch and convert file reading errors to DataIngestionError.

    This decorator wraps file reading methods to ensure all exceptions are
    caught and converted to DataForgeError with appropriate error details.

    Args:
        func: The function to wrap.

    Returns:
        The wrapped function that catches and converts errors.
    """

    @wraps(func)
    async def wrapper(self: Any, file_path: str | Path, *args: Any, **kwargs: Any) -> Any:
        path = Path(file_path)

        try:
            return await func(self, path, *args, **kwargs)
        except FileNotFoundError as e:
            raise DataIngestionError(
                f"File not found: {file_path}",
                details={
                    "error_type": "missing_file",
                    "file_path": str(path),
                },
            ) from e
        except PermissionError as e:
            raise DataIngestionError(
                f"Permission denied: {file_path}",
                details={
                    "error_type": "permission_denied",
                    "file_path": str(path),
                },
            ) from e
        except IsADirectoryError as e:
            raise DataIngestionError(
                f"Expected a file, got a directory: {file_path}",
                details={
                    "error_type": "invalid_path",
                    "file_path": str(path),
                },
            ) from e
        except UnicodeDecodeError as e:
            raise DataIngestionError(
                f"Unsupported encoding: {file_path}",
                details={
                    "error_type": "unsupported_encoding",
                    "file_path": str(path),
                    "encoding": e.encoding,
                    "reason": str(e.reason),
                },
            ) from e
        except Exception as e:
            # Check for pandas-specific errors
            error_msg = str(e).lower()
            if "empty" in error_msg or "no columns" in error_msg:
                raise DataIngestionError(
                    f"Empty file or no data: {file_path}",
                    details={
                        "error_type": "empty_file",
                        "file_path": str(path),
                    },
                ) from e
            if "corrupted" in error_msg or "invalid" in error_msg:
                raise DataIngestionError(
                    f"Corrupted or invalid file: {file_path}",
                    details={
                        "error_type": "corrupted_file",
                        "file_path": str(path),
                    },
                ) from e

            # Generic error
            raise DataIngestionError(
                f"Failed to read file: {file_path}",
                details={
                    "error_type": "read_error",
                    "file_path": str(path),
                    "error_message": str(e),
                },
            ) from e

    return wrapper


def detect_encoding(file_path: Path) -> str:
    """Detect file encoding with fallback chain.

    Attempts to detect encoding using chardet, then falls back to a chain
    of common encodings (UTF-8 → Latin-1 → CP1252).

    Args:
        file_path: Path to the file to detect encoding for.

    Returns:
        Detected encoding string (defaults to 'utf-8').
    """
    # Try chardet first
    try:
        import chardet

        with open(file_path, "rb") as f:
            raw = f.read(10000)  # Sample first 10KB
        result = chardet.detect(raw)
        if result["confidence"] > 0.7:
            return result["encoding"]
    except Exception:
        pass

    # Fallback chain
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                f.read(1000)
            return encoding
        except UnicodeDecodeError:
            continue

    return "utf-8"  # Final fallback


def detect_json_format(file_path: Path) -> str:
    """Detect if file is JSON or JSON Lines format.

    JSON Lines files often have .json extension (not .jsonl).
    This method auto-detects the format by checking if every line is valid JSON.

    Args:
        file_path: Path to the JSON file.

    Returns:
        'jsonl' if JSON Lines format, 'json' if standard JSON.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            second_line = f.readline().strip()

        # If second line exists and both are valid JSON objects
        if second_line:
            import json

            json.loads(first_line)
            json.loads(second_line)
            return "jsonl"

        return "json"
    except Exception:
        return "json"