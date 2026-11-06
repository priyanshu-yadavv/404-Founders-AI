"""
404 FOUNDERS — Unit Tests: Governance, Manifests & Splitting
Tests licensing validation, PII/secret scanning/redaction, hash-partitioned zero-leakage splits,
and manifest cryptographic verification.
"""

import tempfile
from pathlib import Path
import pytest

from training.datasets.governance import DataGovernanceEngine
from training.datasets.ingestion import DataRecord, DOMAIN_GENERAL_TEXT
from training.datasets.manifests import DatasetManifest
from training.datasets.splitting import DatasetSplitter
from training.datasets.statistics import DatasetStatistics


def test_license_compliance_validation():
    """Test 25: Verify license governance (approved vs. restrictive licenses)."""
    gov = DataGovernanceEngine()

    # Approved licenses
    ok1, _ = gov.validate_license("Apache-2.0")
    ok2, _ = gov.validate_license("MIT")
    ok3, _ = gov.validate_license("CC-BY-4.0")
    assert ok1 is True
    assert ok2 is True
    assert ok3 is True

    # Restrictive licenses
    bad1, msg1 = gov.validate_license("AGPL-3.0")
    bad2, msg2 = gov.validate_license("CC-BY-NC-4.0")
    assert bad1 is False
    assert "restrictive" in msg1
    assert bad2 is False


def test_pii_and_secret_redaction():
    """Test 26: Verify detection and redaction of credentials, API keys, and personal data."""
    gov = DataGovernanceEngine(redact_pii=True)

    text_with_secrets = (
        "Contact me at developer@founders404.ai or phone.\n"
        "Here is my test key: sk-abcdef1234567890abcdef123456\n"
        "AWS root key: AKIAIOSFODNN7EXAMPLE\n"
        "Internal router: 192.168.1.1\n"
        "SSN record: 123-45-6789"
    )

    res = gov.scan_and_redact_pii(text_with_secrets)
    assert res.has_pii is True
    assert res.findings_count >= 5
    assert "email" in res.pii_types
    assert "openai_key" in res.pii_types
    assert "aws_key" in res.pii_types
    assert "private_ip" in res.pii_types
    assert "ssn" in res.pii_types

    assert "[REDACTED_EMAIL]" in res.redacted_text
    assert "[REDACTED_OPENAI_KEY]" in res.redacted_text
    assert "[REDACTED_AWS_KEY]" in res.redacted_text
    assert "[REDACTED_PRIVATE_IP]" in res.redacted_text
    assert "[REDACTED_SSN]" in res.redacted_text


def test_dataset_splitter_zero_leakage():
    """Test 27: Verify hash partitioning guarantees identical content lands in the exact same split."""
    records = [
        DataRecord(id="1", content="Text entry alpha."),
        DataRecord(id="2", content="Text entry beta."),
        DataRecord(id="3", content="Text entry gamma."),
        DataRecord(id="4", content="Text entry alpha."),  # Identical content to 1
    ]

    splitter = DatasetSplitter(train_ratio=0.8, val_ratio=0.1, test_ratio=0.1)
    splits = splitter.split_by_hash(records)

    # Identical content must be in the same split (no cross-split leakage)
    rec1_split = "train" if any(r.id == "1" for r in splits.train) else ("val" if any(r.id == "1" for r in splits.val) else "test")
    rec4_split = "train" if any(r.id == "4" for r in splits.train) else ("val" if any(r.id == "4" for r in splits.val) else "test")

    assert rec1_split == rec4_split, f"Data leakage: rec 1 in {rec1_split}, rec 4 in {rec4_split}"


def test_dataset_manifest_verification():
    """Test 28: Verify manifest creation and cryptographic checksum verification."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        train_file = base / "train.jsonl"
        val_file = base / "val.jsonl"

        train_file.write_text('{"id": "t1", "content": "train data"}\n', encoding="utf-8")
        val_file.write_text('{"id": "v1", "content": "val data"}\n', encoding="utf-8")

        manifest = DatasetManifest(name="test_dataset", license="Apache-2.0")
        manifest.add_file_entry("train", train_file, record_count=1)
        manifest.add_file_entry("val", val_file, record_count=1)

        manifest_path = base / "manifest.json"
        manifest.save(manifest_path)

        loaded_manifest = DatasetManifest.load(manifest_path)
        valid, errors = loaded_manifest.verify(base)
        assert valid is True
        assert len(errors) == 0

        # Tamper with file
        train_file.write_text("tampered content", encoding="utf-8")
        valid_tampered, errors_tampered = loaded_manifest.verify(base)
        assert valid_tampered is False
        assert any("Checksum mismatch" in e for e in errors_tampered)


def test_dataset_statistics_reporting():
    """Test 29: Verify statistics calculations and Markdown table generation."""
    records = [
        DataRecord(id="1", content="One two three four five.", domain=DOMAIN_GENERAL_TEXT, language="en"),
        DataRecord(id="2", content="Six seven eight nine ten.", domain=DOMAIN_GENERAL_TEXT, language="en"),
    ]
    stats = DatasetStatistics.compute(records)

    assert stats["total_records"] == 2
    assert stats["total_words"] == 10
    assert stats["domain_breakdown"][DOMAIN_GENERAL_TEXT] == 2
    assert stats["language_breakdown"]["en"] == 2

    md_table = DatasetStatistics.to_markdown_table(stats)
    assert "| **Total Records** | 2 |" in md_table
    assert "| **Total Words** | 10 |" in md_table
