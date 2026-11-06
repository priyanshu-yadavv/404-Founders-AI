"""
404 FOUNDERS — Unit Tests: Data Pipeline Validation
Tests file format checks, encoding verification, corrupted line detection,
schema validation, and file size boundary enforcement.
"""

import tempfile
from pathlib import Path
import pytest

from training.datasets.validation import DataValidator, ValidationReport


def test_valid_jsonl_file_validation():
    """Test 14: Verify validation passes for a properly formatted JSONL file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / "valid_data.jsonl"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write('{"id": "doc_1", "content": "Valid text record 1."}\n')
            f.write('{"id": "doc_2", "content": "Valid text record 2."}\n')
            f.write('{"id": "doc_3", "content": "Valid text record 3."}\n')

        validator = DataValidator()
        report = validator.validate_file(file_path)

        assert report.is_valid is True
        assert report.total_records == 3
        assert report.valid_records == 3
        assert report.invalid_records == 0
        assert len(report.errors) == 0
        assert len(report.file_checksum) == 64  # SHA-256 length


def test_corrupted_jsonl_detection():
    """Test 15: Verify detection of corrupted or malformed JSON lines."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / "corrupted.jsonl"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write('{"id": "1", "content": "Valid line."}\n')
            f.write('{"id": "2", "content": truncated json line\n')
            f.write('{"id": "3", "content": "Another valid line."}\n')

        validator = DataValidator()
        report = validator.validate_file(file_path)

        assert report.is_valid is False
        assert report.total_records == 3
        assert report.valid_records == 2
        assert report.invalid_records == 1
        assert any("Corrupted JSON" in err for err in report.errors)


def test_disallowed_extension_rejected():
    """Test 16: Verify rejection of unapproved file formats (e.g. .exe, .sh)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / "script.sh"
        file_path.write_text("#!/bin/bash\necho hello", encoding="utf-8")

        validator = DataValidator()
        report = validator.validate_file(file_path)

        assert report.is_valid is False
        assert any("Disallowed file extension" in err for err in report.errors)


def test_empty_file_rejected():
    """Test 17: Verify rejection of zero-byte files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / "empty.jsonl"
        file_path.touch()

        validator = DataValidator()
        report = validator.validate_file(file_path)

        assert report.is_valid is False
        assert any("File is completely empty" in err for err in report.errors)


def test_utf8_encoding_error_detection():
    """Test 18: Verify detection of non-UTF-8 corrupted byte sequences."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / "bad_encoding.jsonl"
        # Write invalid UTF-8 byte 0xFF
        with open(file_path, "wb") as f:
            f.write(b'{"id": "1", "content": "hello \xff world"}\n')

        validator = DataValidator()
        report = validator.validate_file(file_path)

        assert report.is_valid is False
        assert any("UTF-8 encoding" in err for err in report.errors)


def test_schema_validation_missing_content():
    """Test 19: Verify rejection of records lacking required 'content' field."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / "missing_field.jsonl"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write('{"id": "1", "other_field": "no content"}\n')

        validator = DataValidator()
        report = validator.validate_file(file_path)

        assert report.is_valid is False
        assert any("Missing or non-string 'content'" in err for err in report.errors)
