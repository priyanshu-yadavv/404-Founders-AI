"""
404 FOUNDERS — Structured Logging System
Supports JSON formatted logs for machine parsing and colorized console logs for interactive sessions.
"""

import json
import logging
import sys
import time
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON dictionaries."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "lineno": record.lineno,
        }
        if hasattr(record, "trace_id") and getattr(record, "trace_id"):
            log_obj["trace_id"] = getattr(record, "trace_id")
        if hasattr(record, "extra_data") and getattr(record, "extra_data"):
            log_obj["data"] = getattr(record, "extra_data")
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


class ConsoleFormatter(logging.Formatter):
    """Clean console formatter with timestamp and level prefix."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = time.strftime("%H:%M:%S", time.localtime(record.created))
        trace = f" [{getattr(record, 'trace_id')}]" if hasattr(record, "trace_id") else ""
        return f"[{timestamp}] [{record.levelname:<8}] {record.name}{trace}: {record.getMessage()}"


def setup_logger(
    name: str = "founders404",
    level: str = "INFO",
    format_type: str = "json",
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Configure and return an enterprise logger instance."""
    logger = logging.getLogger(name)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers if re-initialized
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        if format_type.lower() == "json":
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(ConsoleFormatter())
        logger.addHandler(console_handler)

        if log_file:
            import os
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)

    return logger
