"""
404 FOUNDERS — Text Normalization
Handles Unicode canonical normalization (NFC/NFKC), newline unification,
whitespace cleaning, and non-destructive symbol preservation.
"""

from __future__ import annotations

import unicodedata
from typing import Optional


class TextNormalizer:
    """Non-destructive Unicode and whitespace text normalizer.

    Guarantees that programming syntax, mathematical symbols, indentation,
    and multilingual scripts (Devanagari, Cyrillic, Arabic, CJK) are strictly preserved.
    """

    def __init__(self, mode: str = "NFC", strip_null_bytes: bool = True) -> None:
        if mode not in ("NFC", "NFKC", "none"):
            raise ValueError(f"Invalid normalization mode '{mode}'. Must be 'NFC', 'NFKC', or 'none'.")
        self.mode = mode
        self.strip_null_bytes = strip_null_bytes

    def normalize(self, text: Optional[str]) -> str:
        """Apply Unicode normalization and canonical newline cleanup.

        Args:
            text: Input string to normalize.

        Returns:
            Normalized string. Returns empty string if input is None or empty.
        """
        if text is None:
            return ""
        if not text:
            return ""

        # Remove null bytes if enabled
        if self.strip_null_bytes and "\x00" in text:
            text = text.replace("\x00", "")

        # Unify line breaks to standard Unix format (\r\n and \r -> \n)
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Replace non-breaking space and thin space with standard ASCII space
        # while preserving intentional tabs (\t) and newlines (\n)
        text = text.replace("\u00a0", " ").replace("\u2009", " ").replace("\u202f", " ")

        # Apply canonical Unicode normalization
        if self.mode != "none":
            text = unicodedata.normalize(self.mode, text)

        return text
