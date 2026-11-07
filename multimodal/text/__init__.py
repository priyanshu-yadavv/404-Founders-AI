"""
404 FOUNDERS — Multimodal/Text
Text processing pipelines, unicode normalization, code syntax parsing,
long-document chunking, and contextual question answering.
"""

from multimodal.text.text_processor import (
    DocumentChunk,
    MultimodalTextProcessor,
    TextClassificationResult,
    TextProcessingResult,
)

__all__ = [
    "MultimodalTextProcessor",
    "DocumentChunk",
    "TextClassificationResult",
    "TextProcessingResult",
]
