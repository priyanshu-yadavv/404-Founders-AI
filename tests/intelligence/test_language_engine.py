"""
404 FOUNDERS — Language and Communication Engine Unit Tests
"""

import pytest
from core.intelligence.language_engine import CommunicationStyle, LanguageCommunicationEngine


@pytest.fixture
def engine() -> LanguageCommunicationEngine:
    return LanguageCommunicationEngine()


def test_syllable_count_and_readability(engine: LanguageCommunicationEngine) -> None:
    text = (
        "The neural architecture implements hierarchical self-attention mechanisms "
        "designed for scalable parallel distributed pretraining across heterogeneous compute clusters."
    )
    metrics = engine.calculate_readability(text)
    assert metrics.total_words > 10
    assert metrics.total_sentences >= 1
    assert metrics.flesch_reading_ease >= 0.0
    assert metrics.flesch_kincaid_grade_level > 8.0  # Technical prose has higher grade level


def test_extractive_summarization(engine: LanguageCommunicationEngine) -> None:
    text = (
        "Distributed data parallel training is the primary scaling approach for deep models. "
        "Each worker maintains a complete replica of parameters while computing gradients on local minibatches. "
        "Critical optimization involves overlapping gradient all-reduce communication with backward computation passes. "
        "Therefore, high bandwidth inter-node networking is required to prevent communication stalls."
    )
    summ = engine.summarize(text, max_points=2)
    assert len(summ.key_takeaways) == 2
    assert summ.compression_ratio < 1.0
    assert "- " in summ.bullet_summary


def test_style_adaptation(engine: LanguageCommunicationEngine) -> None:
    text = "The system completed health checks successfully with zero detected packet drops."

    # Executive
    exec_style = engine.adapt_style(text, CommunicationStyle.EXECUTIVE_CONCISE)
    assert "Executive Summary:" in exec_style

    # Technical
    tech_style = engine.adapt_style(text, CommunicationStyle.TECHNICAL_PRECISE)
    assert "Specification Analysis:" in tech_style

    # System Operational
    sys_style = engine.adapt_style(text, CommunicationStyle.SYSTEM_OPERATIONAL)
    assert "[SYSTEM_OP_LOG]" in sys_style
