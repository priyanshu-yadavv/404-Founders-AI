"""
404 FOUNDERS — Unit Tests: Cleaning & Deduplication
Tests text sanitization, quality filtering, exact SHA-256 deduplication, and MinHash near-dedup.
"""

import pytest

from training.datasets.cleaning import DataCleaner
from training.datasets.deduplication import Deduplicator
from training.datasets.ingestion import DataRecord, DOMAIN_CODE, DOMAIN_GENERAL_TEXT


def test_text_cleaning_and_normalization():
    """Test 20: Verify null byte removal, newline reduction, and whitespace cleaning."""
    cleaner = DataCleaner()
    dirty_text = "Hello\x00 world!\r\n\r\n\r\n\r\n\r\nLine 2.\u00a0With non-breaking space."
    cleaned = cleaner.clean_text(dirty_text)

    assert "\x00" not in cleaned
    assert "\r" not in cleaned
    assert "\u00a0" not in cleaned
    assert "Line 2." in cleaned


def test_language_identification():
    """Test 21: Verify heuristic language and code identification."""
    cleaner = DataCleaner()

    assert cleaner.detect_language("def solve(x: int) -> int: return x * 2") == "code"
    assert cleaner.detect_language("SELECT id, name FROM users WHERE active = 1") == "code"
    assert cleaner.detect_language("नमस्ते भारत! यह एक सुंदर दिन है और हम काम कर रहे हैं।") == "hi"
    assert cleaner.detect_language("Это предложение на русском языке для проверки языка.") == "ru"
    assert cleaner.detect_language("The quick brown fox jumps over the lazy dog.") == "en"


def test_quality_filter_rejection():
    """Test 22: Verify rejection of low-quality, gibberish, or looping text."""
    cleaner = DataCleaner()

    # Too short
    short_pass, _ = cleaner.is_high_quality("Hi.")
    assert short_pass is False

    # Symbol-heavy gibberish
    gibberish = "&&&&&%%%%$$$$####@@@@!!!!~~~~^^^^"
    gibberish_pass, _ = cleaner.is_high_quality(gibberish)
    assert gibberish_pass is False

    # Repetition loop
    loop_text = "Repetitive sentence.\nRepetitive sentence.\nRepetitive sentence.\nRepetitive sentence."
    loop_pass, _ = cleaner.is_high_quality(loop_text)
    assert loop_pass is False

    # High quality sample
    good_text = "404 FOUNDERS is developing an autonomous intelligence system from scratch."
    good_pass, _ = cleaner.is_high_quality(good_text)
    assert good_pass is True


def test_exact_duplicate_deduplication():
    """Test 23: Verify exact duplicate removal using content SHA-256 hashes."""
    records = [
        DataRecord(id="1", content="Exact unique record one."),
        DataRecord(id="2", content="Exact unique record two."),
        DataRecord(id="3", content="Exact unique record one."),  # Exact duplicate
        DataRecord(id="4", content="Exact unique record three."),
    ]
    deduplicator = Deduplicator(enable_near_dedup=False)
    unique = list(deduplicator.deduplicate(records))

    assert len(unique) == 3
    assert deduplicator.exact_duplicates_count == 1
    assert deduplicator.unique_count == 3


def test_near_duplicate_minhash_deduplication():
    """Test 24: Verify near-duplicate filtering via MinHash signature matching."""
    records = [
        DataRecord(id="1", content="The quick brown fox jumps over the lazy dog in the sunny park."),
        DataRecord(id="2", content="The quick brown fox jumps over the lazy dog in the sunny park!"),  # Near duplicate
        DataRecord(id="3", content="A completely different and independent sentence about quantum computing."),
    ]
    deduplicator = Deduplicator(near_duplicate_threshold=0.85, enable_near_dedup=True)
    unique = list(deduplicator.deduplicate(records))

    assert len(unique) == 2
    assert deduplicator.near_duplicates_count == 1
    assert unique[0].id == "1"
    assert unique[1].id == "3"
