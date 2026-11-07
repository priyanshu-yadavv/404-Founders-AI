"""
404 FOUNDERS — Multimodal Text Intelligence Processor
Integrates custom BPE tokenization, English/Hindi language detection,
long-document chunking, summarization, QA, and structured information extraction.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Tuple

from core.intelligence.knowledge_engine import GeneralKnowledgeEngine
from core.intelligence.language_engine import CommunicationStyle, LanguageCommunicationEngine
from tokenizer import CustomBPETokenizer


@dataclass
class DocumentChunk:
    """A bounded segment of a long text document with character offset tracking."""
    chunk_id: int
    text: str
    token_count: int
    start_char: int
    end_char: int


@dataclass
class TextClassificationResult:
    """Classification of text content across academic, technical, or operational domains."""
    primary_category: str
    confidence: float
    domain_tags: List[str]


@dataclass
class TextProcessingResult:
    """Comprehensive output schema for text intelligence analysis."""
    original_text: str
    detected_language: str
    character_count: int
    word_count: int
    token_count: int
    chunks: List[DocumentChunk]
    summary: str
    entities: List[Dict[str, str]]
    classification: TextClassificationResult


class MultimodalTextProcessor:
    """
    Multimodal Text Intelligence Processor.
    Processes English, Hindi (Devanagari), code, and multilingual corpora,
    enforcing bounded chunking, extractive summarization, and contextual question answering.
    """

    DEVANAGARI_RANGE = re.compile(r"[\u0900-\u097F]")

    def __init__(
        self,
        tokenizer: Optional[CustomBPETokenizer] = None,
        language_engine: Optional[LanguageCommunicationEngine] = None,
        knowledge_engine: Optional[GeneralKnowledgeEngine] = None,
    ) -> None:
        self.tokenizer = tokenizer or CustomBPETokenizer()
        self.language_engine = language_engine or LanguageCommunicationEngine()
        self.knowledge_engine = knowledge_engine or GeneralKnowledgeEngine()

    def detect_language(self, text: str) -> str:
        """Detect language, with native recognition for Hindi (Devanagari) and English."""
        cleaned = text.strip()
        if not cleaned:
            return "unknown"

        # Check for Devanagari script characters
        devanagari_chars = len(self.DEVANAGARI_RANGE.findall(cleaned))
        total_letters = len(re.findall(r"\w", cleaned))

        if total_letters > 0 and (devanagari_chars / total_letters) > 0.20:
            return "hi"  # Hindi / Devanagari

        # Fallback to English / Roman script heuristic
        latin_chars = len(re.findall(r"[a-zA-Z]", cleaned))
        if total_letters > 0 and (latin_chars / total_letters) > 0.50:
            return "en"

        return "multilingual"

    def chunk_text(
        self,
        text: str,
        max_chunk_chars: int = 1000,
        overlap_chars: int = 150,
    ) -> List[DocumentChunk]:
        """Split long text into sentence-aware overlapping chunks."""
        cleaned = text.strip()
        if not cleaned:
            return []

        if len(cleaned) <= max_chunk_chars:
            toks = self.tokenizer.encode(cleaned)
            return [DocumentChunk(chunk_id=0, text=cleaned, token_count=len(toks), start_char=0, end_char=len(cleaned))]

        # Split on sentence boundaries
        sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", cleaned) if s.strip()]
        chunks: List[DocumentChunk] = []
        current_chunk_sentences: List[str] = []
        current_len = 0
        current_start = 0
        chunk_idx = 0

        for sentence in sentences:
            sentence_len = len(sentence)
            if current_len + sentence_len > max_chunk_chars and current_chunk_sentences:
                chunk_str = " ".join(current_chunk_sentences)
                toks = self.tokenizer.encode(chunk_str)
                chunks.append(DocumentChunk(
                    chunk_id=chunk_idx,
                    text=chunk_str,
                    token_count=len(toks),
                    start_char=current_start,
                    end_char=current_start + len(chunk_str),
                ))
                chunk_idx += 1

                # Retain overlapping tail
                overlap_accum: List[str] = []
                overlap_len = 0
                for s in reversed(current_chunk_sentences):
                    if overlap_len + len(s) <= overlap_chars:
                        overlap_accum.insert(0, s)
                        overlap_len += len(s)
                    else:
                        break

                current_start = current_start + len(chunk_str) - overlap_len
                current_chunk_sentences = overlap_accum + [sentence]
                current_len = overlap_len + sentence_len
            else:
                current_chunk_sentences.append(sentence)
                current_len += sentence_len

        if current_chunk_sentences:
            chunk_str = " ".join(current_chunk_sentences)
            toks = self.tokenizer.encode(chunk_str)
            chunks.append(DocumentChunk(
                chunk_id=chunk_idx,
                text=chunk_str,
                token_count=len(toks),
                start_char=current_start,
                end_char=current_start + len(chunk_str),
            ))

        return chunks

    def summarize(self, text: str, max_sentences: int = 3) -> str:
        """Produce structured executive summary using LanguageCommunicationEngine."""
        summ_res = self.language_engine.summarize(text, max_points=max_sentences)
        return summ_res.bullet_summary

    def classify(self, text: str) -> TextClassificationResult:
        """Classify domain using GeneralKnowledgeEngine."""
        domain_res = self.knowledge_engine.classify_domain(text)
        return TextClassificationResult(
            primary_category=domain_res.primary_domain,
            confidence=domain_res.confidence,
            domain_tags=domain_res.domain_tags,
        )

    def answer_question(self, context: str, question: str) -> Dict[str, Any]:
        """Answer a question grounded in the provided context without hallucinating."""
        cleaned_ctx = context.strip()
        cleaned_q = question.strip()
        if not cleaned_ctx:
            return {"answer": "I do not know. The context provided is empty.", "confidence": 0.0, "found_in_context": False}

        # Extract search keywords from question
        q_words = set(re.findall(r"\b[a-zA-Z0-9_\-]{3,}\b", cleaned_q.lower()))
        stopwords = {
            "the", "is", "are", "was", "were", "a", "an", "and", "or", "in", "on", "at",
            "to", "for", "of", "with", "from", "by", "that", "this", "these", "those",
            "what", "when", "where", "which", "who", "whom", "whose", "why", "how", "does", "have", "been"
        }
        keywords = q_words - stopwords

        if not keywords:
            keywords = q_words

        # Score sentences in context by keyword density
        sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", cleaned_ctx) if len(s.strip()) > 10]
        scored_sentences: List[Tuple[float, str]] = []

        for s in sentences:
            s_lower = s.lower()
            matches = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", s_lower))
            if matches > 0:
                score = matches / max(1, len(keywords))
                scored_sentences.append((score, s))

        scored_sentences.sort(key=lambda x: x[0], reverse=True)

        if not scored_sentences or scored_sentences[0][0] < 0.20:
            return {
                "answer": f"I do not know based on the provided context. No matching details found for: '{cleaned_q}'",
                "confidence": 0.05,
                "found_in_context": False,
                "salient_context": "",
            }

        top_score, top_sentence = scored_sentences[0]
        confidence = min(0.95, top_score * 0.9)

        return {
            "answer": top_sentence,
            "confidence": round(confidence, 2),
            "found_in_context": True,
            "salient_context": top_sentence,
        }

    def extract_structured_info(self, text: str) -> Dict[str, Any]:
        """Extract structured entities, email addresses, URLs, and key numbers."""
        emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
        raw_urls = re.findall(r"https?://[^\s<>\"']+", text)
        urls = [u.rstrip(".,;!?:)\"']") for u in raw_urls]
        metrics = re.findall(r"\b\d+(?:\.\d+)?\s*(?:MB|GB|TB|ms|sec|GHz|MHz|TFLOPS|%)\b", text)

        # Entity extraction via knowledge engine
        entities_raw = self.knowledge_engine.extract_entities(text)
        entities = [{"text": e.text, "category": e.category, "hint": e.disambiguation_hint} for e in entities_raw]

        return {
            "emails": emails,
            "urls": urls,
            "metrics": metrics,
            "entities": entities,
        }

    def process(self, text: str) -> TextProcessingResult:
        """Execute full text intelligence pipeline on input text."""
        lang = self.detect_language(text)
        char_count = len(text)
        word_count = len(text.split())
        toks = self.tokenizer.encode(text)

        chunks = self.chunk_text(text)
        summary = self.summarize(text) if len(text.split()) > 30 else text.strip()
        classification = self.classify(text)
        structured = self.extract_structured_info(text)

        return TextProcessingResult(
            original_text=text,
            detected_language=lang,
            character_count=char_count,
            word_count=word_count,
            token_count=len(toks),
            chunks=chunks,
            summary=summary,
            entities=structured["entities"],
            classification=classification,
        )
