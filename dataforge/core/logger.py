"""Structured logging for DataForge AI."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = ["StructuredLogger"]


class StructuredLogger:
    """Centralized structured logging for all agents.

    Provides:
    - Consistent log format across all agents
    - Beautiful colored console output
    - Machine-readable JSON log files
    - Automatic log export
    """

    # Console colors
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    # Icons (using ASCII-compatible characters for Windows console compatibility)
    ICONS = {
        "DEBUG": "[DEBUG]",
        "INFO": "[INFO]",
        "WARNING": "[WARN]",
        "ERROR": "[ERROR]",
        "CRITICAL": "[CRIT]",
    }

    def __init__(self, execution_id: str, output_dir: str | Path):
        """Initialize the structured logger.

        Args:
            execution_id: Unique execution identifier.
            output_dir: Output directory for logs.
        """
        self.execution_id = execution_id
        self.output_dir = Path(output_dir)
        self.logs: list[dict[str, Any]] = []
        self.log_file = self.output_dir / f"execution_{execution_id}.log"

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format.

        Returns:
            ISO formatted timestamp.
        """
        return datetime.now(timezone.utc).isoformat()

    def _log(self, level: str, **kwargs: Any) -> None:
        """Internal log method.

        Args:
            level: Log level.
            **kwargs: Log fields.
        """
        entry = {
            "timestamp": self._get_timestamp(),
            "level": level,
            "execution_id": self.execution_id,
            **kwargs,
        }
        self.logs.append(entry)

        self._console_log(level, entry)
        self._file_log(entry)

    def _console_log(self, level: str, entry: dict[str, Any]) -> None:
        """Pretty console output with colors.

        Args:
            level: Log level.
            entry: Log entry.
        """
        color = self.COLORS.get(level, "")
        icon = self.ICONS.get(level, "•")
        message = entry.get("message", "")
        agent = entry.get("agent", "")

        # Build output string
        output = f"{color}{icon} [{level}]{self.RESET} {message}"
        if agent:
            output += f" [{agent}]"

        try:
            print(output)
        except UnicodeEncodeError:
            # Fallback for Windows console encoding issues
            plain_output = f"{icon} [{level}] {message}"
            if agent:
                plain_output += f" [{agent}]"
            print(plain_output, errors="replace")

    def _file_log(self, entry: dict[str, Any]) -> None:
        """Write to log file.

        Args:
            entry: Log entry.
        """
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError as e:
            # If file logging fails, at least console logging worked
            print(f"Warning: Failed to write to log file: {e}")

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message.

        Args:
            message: Log message.
            **kwargs: Additional log fields.
        """
        self._log("DEBUG", message=message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message.

        Args:
            message: Log message.
            **kwargs: Additional log fields.
        """
        self._log("INFO", message=message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message.

        Args:
            message: Log message.
            **kwargs: Additional log fields.
        """
        self._log("WARNING", message=message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message.

        Args:
            message: Log message.
            **kwargs: Additional log fields.
        """
        self._log("ERROR", message=message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message.

        Args:
            message: Log message.
            **kwargs: Additional log fields.
        """
        self._log("CRITICAL", message=message, **kwargs)

    def export_logs(self) -> Path:
        """Export logs to JSON file.

        Returns:
            Path to exported log file.
        """
        export_path = self.output_dir / f"logs_{self.execution_id}.json"
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(self.logs, f, indent=2)
        except OSError as e:
            self.error(f"Failed to export logs: {e}")
            raise
        return export_path

    def get_logs(self) -> list[dict[str, Any]]:
        """Get all log entries.

        Returns:
            List of log entries.
        """
        return self.logs.copy()

    def get_logs_by_level(self, level: str) -> list[dict[str, Any]]:
        """Get logs filtered by level.

        Args:
            level: Log level to filter by.

        Returns:
            Filtered list of log entries.
        """
        return [log for log in self.logs if log.get("level") == level]

    def get_logs_by_agent(self, agent: str) -> list[dict[str, Any]]:
        """Get logs filtered by agent.

        Args:
            agent: Agent name to filter by.

        Returns:
            Filtered list of log entries.
        """
        return [log for log in self.logs if log.get("agent") == agent]

    def clear_logs(self) -> None:
        """Clear all log entries from memory."""
        self.logs.clear()
