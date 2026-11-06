"""
404 FOUNDERS — Unit Tests for Structured Logging
"""

import json
import logging
from core.logging import JSONFormatter, ConsoleFormatter, setup_logger


def test_json_formatter() -> None:
    """Validate JSONFormatter output contains required structured fields."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Sample log message",
        args=(),
        exc_info=None,
    )
    setattr(record, "trace_id", "trace-12345")
    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert parsed["message"] == "Sample log message"
    assert parsed["trace_id"] == "trace-12345"
    assert "timestamp" in parsed


def test_console_formatter() -> None:
    """Validate ConsoleFormatter formats readable text output."""
    formatter = ConsoleFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.WARNING,
        pathname="test.py",
        lineno=25,
        msg="Warning message",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "[WARNING ]" in formatted
    assert "Warning message" in formatted


def test_setup_logger_instance() -> None:
    """Validate logger instantiation and configuration."""
    logger = setup_logger("test_instance", level="DEBUG", format_type="json")
    assert logger.name == "test_instance"
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) >= 1
