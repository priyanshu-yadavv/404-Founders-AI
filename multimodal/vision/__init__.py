"""
404 FOUNDERS — Multimodal/Vision
Visual tokenization, patch extraction, continuous feature projection,
and defensive image inspection.
"""

from multimodal.vision.image_processor import (
    BoundingBox,
    ImageMetadata,
    ImageProcessor,
    OCRTextElement,
    VisualAnalysisResult,
)

__all__ = [
    "ImageProcessor",
    "ImageMetadata",
    "BoundingBox",
    "OCRTextElement",
    "VisualAnalysisResult",
]
