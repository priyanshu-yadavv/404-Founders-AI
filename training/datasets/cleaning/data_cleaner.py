"""
404 FOUNDERS — Data Cleaner
Performs non-destructive text cleaning, control-character sanitization,
heuristic language detection, and low-quality/spam filtering.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional, Tuple

from training.datasets.ingestion.dataset_ingestor import DOMAIN_CODE, DataRecord


class DataCleaner:
    """Cleans and filters records for dataset preparation pipelines."""

    # Regex for excessive consecutive newlines
    _RE_CONSECUTIVE_NEWLINES = re.compile(r"\n{4,}")

    # Script character ranges
    _RE_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
    _RE_CYRILLIC = re.compile(r"[\u0400-\u04FF]")
    _RE_ARABIC = re.compile(r"[\u0600-\u06FF]")
    _RE_CJK = re.compile(r"[\u4E00-\u9FFF]")

    # Code signatures
    _RE_CODE_SIGS = re.compile(
        r"(?:def\s+\w+\(|class\s+\w+|import\s+\w+|from\s+\w+\s+import|fn\s+\w+\(|pub\s+fn|"
        r"function\s+\w+\(|const\s+\w+\s*=|SELECT\s+.*FROM|#include\s*<|#!/bin/)",
        re.IGNORECASE,
    )

    def __init__(
        self,
        min_words: int = 3,
        max_symbol_ratio: float = 0.50,
        max_repetition_ratio: float = 0.40,
    ) -> None:
        self.min_words = min_words
        self.max_symbol_ratio = max_symbol_ratio
        self.max_repetition_ratio = max_repetition_ratio

    def clean_text(self, text: Optional[str]) -> str:
        """Sanitize text by removing null bytes, fixing line endings, and normalizing newlines."""
        if not text:
            return ""

        # Remove null bytes
        text = text.replace("\x00", "")

        # Unify newlines
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Normalize non-breaking and thin spaces
        text = text.replace("\u00a0", " ").replace("\u2009", " ").replace("\u202f", " ")

        # Reduce excessive blank line runs
        text = self._RE_CONSECUTIVE_NEWLINES.sub("\n\n\n", text)

        # Unicode NFC normalization
        text = unicodedata.normalize("NFC", text)

        return text.strip()

    def detect_language(self, text: str) -> str:
        """Detect language or code domain heuristically based on script character frequencies."""
        if not text:
            return "unknown"

        # Check for code first
        if self._RE_CODE_SIGS.search(text):
            return "code"

        # Count script occurrences
        sample = text[:1000]
        devanagari_count = len(self._RE_DEVANAGARI.findall(sample))
        if devanagari_count > 5:
            return "hi"

        arabic_count = len(self._RE_ARABIC.findall(sample))
        if arabic_count > 5:
            return "ar"

        cjk_count = len(self._RE_CJK.findall(sample))
        if cjk_count > 5:
            return "zh"

        cyrillic_count = len(self._RE_CYRILLIC.findall(sample))
        if cyrillic_count > 5:
            return "ru"

        return "en"

    def is_high_quality(self, text: str, is_code: bool = False) -> Tuple[bool, str]:
        """Assess whether a text sample meets minimum data quality criteria.

        Args:
            text: Text to evaluate.
            is_code: Whether the sample is source code (relaxes symbol ratio).

        Returns:
            Tuple of (passes: bool, reason: str).
        """
        words = text.split()
        if len(words) < self.min_words:
            return False, f"Word count {len(words)} is below minimum {self.min_words}"

        chars = len(text)
        if chars == 0:
            return False, "Empty text"

        # Check symbol-to-character ratio (except for code)
        if not is_code:
            symbols = sum(
                1 for c in text if not (c.isalnum() or c.isspace() or c in ".,!?'\"-")
            )
            ratio = symbols / chars
            if ratio > self.max_symbol_ratio:
                return False, f"Symbol ratio {ratio:.2f} exceeds threshold {self.max_symbol_ratio:.2f}"

        # Check repetition loops (e.g. repeated identical lines)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(lines) >= 4:
            unique_lines = set(lines)
            rep_ratio = 1.0 - (len(unique_lines) / len(lines))
            if rep_ratio > self.max_repetition_ratio:
                return False, f"Line repetition ratio {rep_ratio:.2f} exceeds threshold {self.max_repetition_ratio:.2f}"

        return True, "Passed quality checks"

    def clean_record(self, record: DataRecord) -> Optional[DataRecord]:
        """Clean record content and evaluate quality. Returns updated record or None if rejected."""
        cleaned_content = self.clean_text(record.content)
        if not cleaned_content:
            return None

        is_code = record.domain == DOMAIN_CODE or self._RE_CODE_SIGS.search(cleaned_content) is not None
        passes, reason = self.is_high_quality(cleaned_content, is_code=is_code)
        if not passes:
            return None

        lang = record.language
        if lang in ("en", "unknown") and not is_code:
            detected = self.detect_language(cleaned_content)
            if detected != "unknown":
                lang = detected

        record.content = cleaned_content
        record.language = lang
        record.metadata["cleaner_status"] = "verified"
        return record
