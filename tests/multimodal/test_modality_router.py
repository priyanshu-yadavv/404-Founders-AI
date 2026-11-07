"""
Unit tests for ModalityRouter.
Verifies multi-modality simultaneous detection, dispatching to specialized processors,
multi-stage fusion orchestration, and Central Intelligence Router integration.
"""

import io
from PIL import Image
import pytest

from multimodal.modality_router import ModalityRouter, ModalityDetectionResult, UnifiedMultimodalResponse
from tests.multimodal.test_audio_processor import generate_synthetic_wav_bytes


@pytest.fixture
def router():
    return ModalityRouter()


def create_tiny_png_bytes():
    buf = io.BytesIO()
    img = Image.new("RGB", (64, 64), color=(50, 100, 150))
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_detect_modalities_text_only(router):
    det = router.detect_modalities(text="Explain quantum mechanics.")
    assert isinstance(det, ModalityDetectionResult)
    assert det.primary_modality == "TEXT"
    assert det.active_modalities == ["TEXT"]
    assert det.is_multimodal is False


def test_detect_modalities_multimodal_simultaneous(router):
    png_bytes = create_tiny_png_bytes()
    wav_bytes = generate_synthetic_wav_bytes(duration_sec=0.1)

    det = router.detect_modalities(
        text="Analyze this architectural diagram and audio recording.",
        image_data=png_bytes,
        audio_data=wav_bytes,
        filename_hints={"image": "diagram.png", "audio": "sample.wav"},
    )

    assert det.is_multimodal is True
    assert "TEXT" in det.active_modalities
    assert "IMAGE" in det.active_modalities
    assert "AUDIO" in det.active_modalities
    assert det.detected_formats["IMAGE"] == "diagram.png"
    assert det.detected_formats["AUDIO"] == "sample.wav"


def test_route_and_process_text_and_image(router):
    png_bytes = create_tiny_png_bytes()
    res = router.route_and_process(
        text="What is displayed in this image?",
        image_data=png_bytes,
        filename_hints={"image": "test.png"},
        perform_fusion=True,
        fusion_stage="EARLY",
    )

    assert isinstance(res, UnifiedMultimodalResponse)
    assert res.text_result is not None
    assert res.image_result is not None
    assert res.fusion_output is not None
    assert res.fusion_output.fusion_stage == "EARLY"
    assert "IMAGE" in res.fusion_output.active_modalities
    assert len(res.combined_response_summary) > 0


def test_route_and_process_with_tts_synthesis(router):
    res = router.route_and_process(
        text="404 FOUNDERS operates strictly on authorized host boundaries.",
        synthesize_speech=True,
    )

    assert res.speech_synthesis_result is not None
    assert res.speech_synthesis_result.audio_base64_uri.startswith("data:audio/wav;base64,")
    assert res.speech_synthesis_result.duration_seconds > 0.1
