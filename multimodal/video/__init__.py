"""
404 FOUNDERS — Multimodal/Video
Spatiotemporal video frame sampling, keyframe selection, and scene change detection.
"""

from multimodal.video.video_processor import (
    VideoAnalysisResult,
    VideoKeyframe,
    VideoMetadata,
    VideoProcessor,
)

__all__ = [
    "VideoProcessor",
    "VideoMetadata",
    "VideoKeyframe",
    "VideoAnalysisResult",
]
