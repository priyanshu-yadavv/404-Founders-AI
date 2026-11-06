"""
404 FOUNDERS — Language and Communication Engine
Provides multi-style communication adaptation, extractive & executive summarization,
clarity analysis, and readability scoring (Flesch-Kincaid grade level).
"""

from dataclasses import dataclass, field
from enum import Enum
import math
import re
from typing import Any, Dict, List, Optional


class CommunicationStyle(str, Enum):
    TECHNICAL_PRECISE = "TECHNICAL_PRECISE"
    EXECUTIVE_CONCISE = "EXECUTIVE_CONCISE"
    TUTORIAL_EDUCATIONAL = "TUTORIAL_EDUCATIONAL"
    SYSTEM_OPERATIONAL = "SYSTEM_OPERATIONAL"
    CASUAL_DIRECT = "CASUAL_DIRECT"


@dataclass
class ReadabilityMetrics:
    """Quantitative readability and textual complexity metrics."""
    total_words: int
    total_sentences: int
    avg_words_per_sentence: float
    estimated_syllables_per_word: float
    flesch_reading_ease: float
    flesch_kincaid_grade_level: float
    complexity_label: str  # "EASY", "STANDARD", "DIFFICULT", "VERY_COMPLEX"


@dataclass
class SummaryResult:
    """Summarization output conforming to length and structural constraints."""
    original_word_count: int
    summary_word_count: int
    compression_ratio: float
    key_takeaways: List[str]
    bullet_summary: str


@dataclass
class LanguageProcessingResult:
    """Complete language and communication transformation report."""
    input_text: str
    target_style: CommunicationStyle
    styled_text: str
    readability: ReadabilityMetrics
    summary: Optional[SummaryResult]


class LanguageCommunicationEngine:
    """
    Language and communication engine.
    Adapts text to targeted operational audiences, computes readability scores,
    and extracts structured executive summaries.
    """

    def count_syllables(self, word: str) -> int:
        """Heuristic syllable counter for English words."""
        w = word.lower().strip(".,!?:;\"'()[]{}")
        if not w:
            return 0
        if len(w) <= 3:
            return 1
        w = re.sub(r"(?:[^laeiouy]|ed|es|e)$", "", w)
        w = re.sub(r"^y", "", w)
        syllables = len(re.findall(r"[aeiouy]{1,2}", w))
        return max(1, syllables)

    def calculate_readability(self, text: str) -> ReadabilityMetrics:
        """Compute Flesch Reading Ease and Flesch-Kincaid Grade Level."""
        words = re.findall(r"\b[a-zA-Z0-9_\-']+\b", text)
        sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]

        n_words = max(1, len(words))
        n_sentences = max(1, len(sentences))

        total_syllables = sum(self.count_syllables(w) for w in words)
        words_per_sentence = n_words / n_sentences
        syllables_per_word = total_syllables / n_words

        # Flesch Reading Ease: 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
        reading_ease = 206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
        reading_ease = round(max(0.0, min(100.0, reading_ease)), 1)

        # Flesch-Kincaid Grade: 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
        grade_level = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59
        grade_level = round(max(0.0, grade_level), 1)

        if reading_ease >= 70.0:
            label = "EASY"
        elif reading_ease >= 50.0:
            label = "STANDARD"
        elif reading_ease >= 30.0:
            label = "DIFFICULT"
        else:
            label = "VERY_COMPLEX"

        return ReadabilityMetrics(
            total_words=n_words,
            total_sentences=n_sentences,
            avg_words_per_sentence=round(words_per_sentence, 2),
            estimated_syllables_per_word=round(syllables_per_word, 2),
            flesch_reading_ease=reading_ease,
            flesch_kincaid_grade_level=grade_level,
            complexity_label=label,
        )

    def summarize(self, text: str, max_points: int = 3) -> SummaryResult:
        """Produce an extractive structured executive summary and key takeaways."""
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 15]
        if not sentences:
            sentences = [text.strip()]

        # Score sentences by keyword salience and position
        scored = []
        for idx, s in enumerate(sentences):
            score = 1.0 / (idx + 1)  # Favor early topic sentences
            if any(k in s.lower() for k in ["important", "key", "result", "critical", "therefore", "conclusion"]):
                score += 1.5
            scored.append((score, s))

        scored.sort(key=lambda item: item[0], reverse=True)
        takeaways = [s for _, s in scored[:max_points]]

        bullet_str = "\n".join(f"- {pt}" for pt in takeaways)
        orig_words = len(text.split())
        summ_words = len(bullet_str.split())
        ratio = round(summ_words / max(1, orig_words), 2)

        return SummaryResult(
            original_word_count=orig_words,
            summary_word_count=summ_words,
            compression_ratio=ratio,
            key_takeaways=takeaways,
            bullet_summary=bullet_str,
        )

    def adapt_style(self, text: str, style: CommunicationStyle) -> str:
        """Reframe text into designated communication style."""
        cleaned = text.strip()
        if not cleaned:
            return ""

        if style == CommunicationStyle.EXECUTIVE_CONCISE:
            summ = self.summarize(cleaned, max_points=3)
            return f"**Executive Summary:**\n{summ.bullet_summary}\n\n**Bottom Line:** Implementation proceeds per target specifications."

        elif style == CommunicationStyle.TECHNICAL_PRECISE:
            return (
                f"**Specification Analysis:**\n{cleaned}\n\n"
                f"**Invariants & Constraints:** All operations must adhere strictly to typed parameters and zero-allocation constraints."
            )

        elif style == CommunicationStyle.TUTORIAL_EDUCATIONAL:
            return (
                f"Let's break this down step-by-step:\n\n{cleaned}\n\n"
                f"💡 **Key Concept:** Notice how each step builds upon the previous principle."
            )

        elif style == CommunicationStyle.SYSTEM_OPERATIONAL:
            return (
                f"[SYSTEM_OP_LOG]\n"
                f"EVENT_PAYLOAD={cleaned}\n"
                f"STATUS=PROCESSED_NOMINAL\n"
                f"AUDIT_FLAG=VERIFIED"
            )

        else:  # CASUAL_DIRECT
            return f"Here is the straightforward breakdown: {cleaned}"

    def process(
        self,
        text: str,
        target_style: CommunicationStyle = CommunicationStyle.TECHNICAL_PRECISE,
        generate_summary: bool = True,
    ) -> LanguageProcessingResult:
        """Transform text, compute readability, and generate summaries."""
        metrics = self.calculate_readability(text)
        styled = self.adapt_style(text, target_style)
        summ = self.summarize(text) if generate_summary else None

        return LanguageProcessingResult(
            input_text=text,
            target_style=target_style,
            styled_text=styled,
            readability=metrics,
            summary=summ,
        )
