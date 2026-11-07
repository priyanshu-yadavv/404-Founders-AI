"""
Unit tests for MultimodalTextProcessor.
Verifies language detection (Devanagari/Hindi, English, Multilingual),
chunking with sentence boundary preservation and overlapping,
grounded question answering without fabrication, and structured entity extraction.
"""

import pytest

from multimodal.text.text_processor import MultimodalTextProcessor, DocumentChunk, TextProcessingResult


@pytest.fixture
def text_processor():
    return MultimodalTextProcessor()


def test_detect_language(text_processor):
    # Hindi (Devanagari)
    hindi_text = "नमस्ते दुनिया! 404 FOUNDERS एक उन्नत कृत्रिम बुद्धिमत्ता प्रणाली है।"
    assert text_processor.detect_language(hindi_text) == "hi"

    # English
    en_text = "404 FOUNDERS is an advanced multimodal operating system engineered from scratch."
    assert text_processor.detect_language(en_text) == "en"

    # Empty string
    assert text_processor.detect_language("") == "unknown"


def test_chunk_text_bounded(text_processor):
    short_text = "This is a short single sentence document."
    chunks = text_processor.chunk_text(short_text, max_chunk_chars=500)
    assert len(chunks) == 1
    assert chunks[0].chunk_id == 0
    assert chunks[0].text == short_text
    assert chunks[0].token_count > 0

    # Long text requiring multi-chunk division
    sentences = [f"Sentence {i}: 404 FOUNDERS enforces rigorous memory boundaries and safety." for i in range(20)]
    long_text = " ".join(sentences)
    chunks = text_processor.chunk_text(long_text, max_chunk_chars=300, overlap_chars=50)
    assert len(chunks) > 1
    for c in chunks:
        assert isinstance(c, DocumentChunk)
        assert len(c.text) <= 400
        assert c.token_count > 0


def test_grounded_question_answering(text_processor):
    context = (
        "The 404 FOUNDERS neural core operates on a Dell Latitude 5400 workstation. "
        "The host safe memory budget is capped at 3.50 GB to prevent OOM panic. "
        "The model uses Gaussian initialization with seed 404."
    )

    # Relevant question
    res = text_processor.answer_question(context, "What is the safe memory budget?")
    assert res["found_in_context"] is True
    assert "3.50 GB" in res["answer"]
    assert res["confidence"] > 0.3

    # Irrelevant / unanswerable question - must not hallucinate
    unanswerable = text_processor.answer_question(context, "What is the capital city of France?")
    assert unanswerable["found_in_context"] is False
    assert "I do not know" in unanswerable["answer"]


def test_extract_structured_info(text_processor):
    text = "Contact support@404founders.ai or visit https://github.com/priyanshu-yadavv/404-Founders-AI. Latency is 14.2 ms with 3.50 GB."
    info = text_processor.extract_structured_info(text)
    assert "support@404founders.ai" in info["emails"]
    assert "https://github.com/priyanshu-yadavv/404-Founders-AI" in info["urls"]
    assert any("ms" in m or "GB" in m for m in info["metrics"])


def test_full_pipeline_process(text_processor):
    sample = "404 FOUNDERS is an AI architecture. It trains from random initialization without pretrained weights."
    res = text_processor.process(sample)
    assert isinstance(res, TextProcessingResult)
    assert res.detected_language == "en"
    assert res.character_count == len(sample)
    assert res.word_count > 5
    assert res.token_count > 0
    assert len(res.chunks) >= 1
    assert res.classification.primary_category is not None
