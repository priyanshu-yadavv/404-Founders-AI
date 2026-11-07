"""
404 FOUNDERS — Multimodal REST API Endpoints Integration Tests
Verifies FastAPI routes under /api/v1/multimodal/ for text, vision, audio, speech, documents, and fusion.
"""

import base64
import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from api.rest.app import create_app, initialize_runtime_services
from tests.multimodal.test_audio_processor import generate_synthetic_wav_bytes


@pytest.fixture(scope="module")
def client() -> TestClient:
    services = initialize_runtime_services()
    app = create_app(services=services)
    with TestClient(app) as test_client:
        yield test_client


def get_base64_png(width: int = 64, height: int = 64) -> str:
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=(60, 120, 180))
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def test_get_supported_modalities(client: TestClient) -> None:
    resp = client.get("/api/v1/multimodal/modalities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    mod_ids = [m["id"] for m in data["supported_modalities"]]
    assert "text" in mod_ids
    assert "image" in mod_ids
    assert "audio" in mod_ids
    assert "speech_stt" in mod_ids
    assert "speech_tts" in mod_ids
    assert "video" in mod_ids
    assert "document" in mod_ids


def test_post_multimodal_process_text(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/multimodal/process",
        json={"text": "404 FOUNDERS is an AI system.", "perform_fusion": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["primary_modality"] == "TEXT"
    assert data["is_multimodal"] is False
    assert len(data["combined_summary"]) > 0


def test_post_multimodal_process_with_image_and_tts(client: TestClient) -> None:
    b64_img = get_base64_png()
    resp = client.post(
        "/api/v1/multimodal/process",
        json={
            "text": "Inspect this image.",
            "image_base64": b64_img,
            "filename_hints": {"image": "test.png"},
            "perform_fusion": True,
            "fusion_stage": "EARLY",
            "synthesize_speech": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_multimodal"] is True
    assert "IMAGE" in data["active_modalities"]
    assert data["speech_audio_base64_uri"] is not None
    assert data["speech_audio_base64_uri"].startswith("data:audio/wav;base64,")


def test_post_image_processing(client: TestClient) -> None:
    b64_img = get_base64_png(320, 240)
    resp = client.post(
        "/api/v1/multimodal/image",
        json={"image_base64": b64_img, "target_size": [224, 224]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "PNG"
    assert data["width"] == 320
    assert data["height"] == 240
    assert data["patch_count"] == 196
    assert len(data["caption"]) > 0


def test_post_audio_processing(client: TestClient) -> None:
    wav_bytes = generate_synthetic_wav_bytes(duration_sec=0.2)
    b64_audio = base64.b64encode(wav_bytes).decode("ascii")

    resp = client.post(
        "/api/v1/multimodal/audio",
        json={"audio_base64": b64_audio},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "WAV"
    assert data["sample_rate"] == 16000
    assert data["rms_energy"] > 0.0


def test_post_speech_recognize(client: TestClient) -> None:
    wav_bytes = generate_synthetic_wav_bytes(duration_sec=0.2)
    b64_audio = base64.b64encode(wav_bytes).decode("ascii")

    resp = client.post(
        "/api/v1/multimodal/speech/recognize",
        json={"audio_base64": b64_audio, "language_hint": "en"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["detected_language"] == "en"
    assert data["overall_confidence"] > 0.0


def test_post_speech_synthesize(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/multimodal/speech/synthesize",
        json={"text": "404 FOUNDERS Online", "language": "en", "pitch_hz": 220.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "en"
    assert data["sample_rate"] == 16000
    assert data["audio_base64_uri"].startswith("data:audio/wav;base64,")


def test_post_document_processing(client: TestClient) -> None:
    csv_bytes = b"ColA,ColB\nVal1,Val2\nVal3,Val4\n"
    b64_doc = base64.b64encode(csv_bytes).decode("ascii")

    resp = client.post(
        "/api/v1/multimodal/document",
        json={"document_base64": b64_doc, "filename": "metrics.csv"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "CSV"
    assert data["has_tables"] is True
    assert data["is_safe"] is True


def test_post_multimodal_fuse(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/multimodal/fuse",
        json={"active_modalities": ["TEXT", "IMAGE"], "fusion_stage": "EARLY"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["fusion_stage"] == "EARLY"
    assert "TEXT" in data["active_modalities"]
    assert "IMAGE" in data["active_modalities"]
    assert len(data["fused_tensor_shape"]) == 3
