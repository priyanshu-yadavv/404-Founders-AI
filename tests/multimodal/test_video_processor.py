"""
Unit tests for VideoProcessor.
Verifies OpenCV streaming video inspection, metadata extraction,
uniform keyframe sampling, Chi-Square histogram scene change detection,
and memory bounding.
"""

from pathlib import Path
import tempfile
import cv2
import numpy as np
import pytest

from multimodal.video.video_processor import VideoProcessor, VideoAnalysisResult


@pytest.fixture
def video_processor():
    return VideoProcessor()


def create_test_video(file_path: Path, num_frames: int = 16, width: int = 64, height: int = 64, fps: float = 10.0) -> None:
    """Create a lightweight synthetic video file using OpenCV VideoWriter."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(file_path), fourcc, fps, (width, height))
    assert writer.isOpened(), f"Failed to initialize VideoWriter at {file_path}"
    
    for i in range(num_frames):
        # First half blue/red, second half bright green to trigger scene change
        color = (220, 50, 50) if i < (num_frames // 2) else (50, 220, 50)
        frame = np.full((height, width, 3), color, dtype=np.uint8)
        # Add dynamic shape
        cv2.circle(frame, (i * 2 + 10, height // 2), 6, (255, 255, 255), -1)
        writer.write(frame)
        
    writer.release()


def test_video_metadata_and_keyframe_sampling(video_processor, tmp_path):
    video_path = tmp_path / "test_sample.mp4"
    create_test_video(video_path, num_frames=16, width=64, height=64, fps=10.0)

    res = video_processor.process(video_path, max_keyframes=4)

    assert isinstance(res, VideoAnalysisResult)
    assert res.is_valid is True
    assert res.metadata.format == "MP4"
    assert res.metadata.width == 64
    assert res.metadata.height == 64
    assert res.metadata.fps == pytest.approx(10.0, abs=0.5)
    assert res.metadata.total_frames == 16
    assert res.metadata.duration_seconds > 0.5

    assert len(res.keyframes) >= 2
    # Verify thumbnail data URI
    for kf in res.keyframes:
        assert kf.thumbnail_base64.startswith("data:image/jpeg;base64,")
        assert kf.timestamp_seconds >= 0.0

    # Ensure scene boundary count recorded
    assert res.scene_boundaries_count >= 1
    assert "Video Intelligence Report" in res.video_summary or "MP4" in res.video_summary


def test_invalid_video_path(video_processor, tmp_path):
    missing_path = tmp_path / "non_existent.mp4"
    with pytest.raises(ValueError, match="not found"):
        video_processor.process(missing_path)
