"""
Unit tests for ImageProcessor.
Validates magic-byte format detection (PNG, JPEG, WEBP, BMP), dimension resizing,
ViT patch extraction (196 patches of 768 dims), aspect ratio computation,
and rejection of corrupted or malformed byte sequences.
"""

import io
from PIL import Image
import pytest

from multimodal.vision.image_processor import ImageProcessor, VisualAnalysisResult


@pytest.fixture
def image_processor():
    return ImageProcessor()


def create_test_image_bytes(fmt="PNG", size=(100, 80), color=(100, 150, 200)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_magic_bytes_detection_png(image_processor):
    png_bytes = create_test_image_bytes("PNG")
    fmt = image_processor.detect_format(png_bytes)
    assert fmt == "PNG"


def test_magic_bytes_detection_jpeg(image_processor):
    jpeg_bytes = create_test_image_bytes("JPEG")
    fmt = image_processor.detect_format(jpeg_bytes)
    assert fmt == "JPEG"


def test_magic_bytes_detection_bmp(image_processor):
    bmp_bytes = create_test_image_bytes("BMP")
    fmt = image_processor.detect_format(bmp_bytes)
    assert fmt == "BMP"


def test_magic_bytes_detection_webp(image_processor):
    webp_bytes = create_test_image_bytes("WEBP")
    fmt = image_processor.detect_format(webp_bytes)
    assert fmt == "WEBP"


def test_malformed_bytes_rejected(image_processor):
    garbage = b"NOT_AN_IMAGE_PAYLOAD_1234567890"
    fmt = image_processor.detect_format(garbage)
    assert fmt == "UNKNOWN"

    with pytest.raises(ValueError, match="Unsupported or corrupted"):
        image_processor.process(garbage)


def test_image_processing_and_vit_patch_extraction(image_processor):
    png_bytes = create_test_image_bytes("PNG", size=(320, 240))
    result = image_processor.process(png_bytes, target_size=(224, 224))

    assert isinstance(result, VisualAnalysisResult)
    assert result.is_valid is True
    assert result.metadata.format == "PNG"
    assert result.metadata.width == 320
    assert result.metadata.height == 240
    assert round(result.metadata.aspect_ratio, 2) == round(320 / 240, 2)
    assert result.patch_count == 196  # (224/16) * (224/16) = 14 * 14 = 196

    # Verify tensor shape
    assert result.normalized_tensor_shape == (3, 224, 224)
    assert len(result.caption_hypothesis) > 0

    # Also test low-level patch extraction helper
    img = Image.open(io.BytesIO(png_bytes))
    norm_tensor, patch_tensor = image_processor.resize_and_extract_patches(img, target_size=(224, 224))
    assert norm_tensor.shape == (3, 224, 224)
    assert patch_tensor.shape == (196, 768)
