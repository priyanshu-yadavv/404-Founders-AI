"""
404 FOUNDERS — Pre-Tokenizer
Splits normalized text into word-like chunks, preserving whitespace with the
visible symbol \u2581 (' '), keeping code operators, mathematical notation,
and multilingual scripts (Devanagari, Arabic, CJK, Cyrillic) intact.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from tokenizer.special_tokens import SpecialTokenRegistry


# Multi-character programming operators
MULTI_CHAR_OPERATORS = [
    r"===",
    r"!==",
    r"==",
    r"!=",
    r"<=",
    r">=",
    r"->",
    r"=>",
    r"::",
    r":=",
    r"\+\+",
    r"--",
    r"\+=",
    r"-=",
    r"\*=",
    r"/=",
    r"//=",
    r"%=",
    r"&&",
    r"\|\|",
    r"//",
    r"\*\*",
    r"<<",
    r">>",
]

_OPERATOR_PATTERN = "|".join(MULTI_CHAR_OPERATORS)

# Unicode word character class including Latin, Greek, Cyrillic, Hebrew, Arabic,
# Devanagari, Bengali, Gurmukhi, Gujarati, Oriya, Tamil, Telugu, Kannada, Malayalam,
# Thai, CJK Unified Ideographs, and combining marks (matras, viramas).
_MULTILINGUAL_LETTERS = (
    r"[a-zA-Z_"
    r"\u00C0-\u024F"  # Latin extended
    r"\u0370-\u03FF"  # Greek
    r"\u0400-\u04FF"  # Cyrillic
    r"\u0590-\u05FF"  # Hebrew
    r"\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF"  # Arabic & combining marks
    r"\u0900-\u0D7F"  # Indic scripts (Devanagari, Bengali, Tamil, Telugu, etc.)
    r"\u0E00-\u0E7F"  # Thai
    r"\u4E00-\u9FFF"  # CJK Unified Ideographs
    r"]"
)


class PreTokenizer:
    """Pre-tokenizes text into discrete candidate words or symbol clusters."""

    def __init__(self, whitespace_symbol: str = " ") -> None:
        self.whitespace_symbol = whitespace_symbol
        ws = re.escape(self.whitespace_symbol)

        # Regex matching:
        # 1. Newlines / carriage returns
        # 2. Tabs
        # 3. Operators (optionally preceded by whitespace symbol)
        # 4. Numbers, floats, scientific notation (optionally preceded by whitespace symbol)
        # 5. Multilingual words (optionally preceded by whitespace symbol)
        # 6. Any run of whitespace symbols
        # 7. Any other single non-whitespace character
        self._pattern = re.compile(
            rf"\n+"
            rf"|\t+"
            rf"|(?:{ws})?(?:{_OPERATOR_PATTERN})"
            rf"|(?:{ws})?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
            rf"|(?:{ws})?{_MULTILINGUAL_LETTERS}+"
            rf"|{ws}+"
            rf"|[^\s]"
        )

    def pre_tokenize_text(self, text: str) -> List[str]:
        """Pre-tokenize a text string that has had spaces replaced with whitespace_symbol.

        Args:
            text: Text with standard spaces replaced by self.whitespace_symbol.

        Returns:
            List of pre-tokenized string tokens.
        """
        if not text:
            return []
        return self._pattern.findall(text)

    def pre_tokenize(
        self,
        text: str,
        special_tokens: Optional[SpecialTokenRegistry] = None,
    ) -> List[Tuple[str, bool]]:
        """Pre-tokenize input text, returning list of (token_chunk, is_special) tuples.

        Special tokens are extracted atomically and preserved without character splitting.

        Args:
            text: Raw or normalized text.
            special_tokens: Optional registry of special tokens to match atomically.

        Returns:
            List of (chunk, is_special) tuples.
        """
        if not text:
            return []

        if special_tokens is None or special_tokens.pattern is None:
            # No special tokens: replace space with whitespace symbol and pre-tokenize
            transformed = text.replace(" ", self.whitespace_symbol)
            return [(chunk, False) for chunk in self.pre_tokenize_text(transformed)]

        pattern = special_tokens.pattern
        segments: List[Tuple[str, bool]] = []
        pos = 0

        for match in pattern.finditer(text):
            start, end = match.span()
            if start > pos:
                non_special = text[pos:start].replace(" ", self.whitespace_symbol)
                for chunk in self.pre_tokenize_text(non_special):
                    segments.append((chunk, False))
            segments.append((match.group(0), True))
            pos = end

        if pos < len(text):
            remaining = text[pos:].replace(" ", self.whitespace_symbol)
            for chunk in self.pre_tokenize_text(remaining):
                segments.append((chunk, False))

        return segments

    @staticmethod
    def split_to_characters(word: str) -> Tuple[str, ...]:
        """Split a pre-tokenized word into individual Unicode code-point characters."""
        return tuple(word)
