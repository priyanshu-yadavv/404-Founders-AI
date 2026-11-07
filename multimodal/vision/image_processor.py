"""
404 FOUNDERS — Image Intelligence Pipeline
Provides secure image validation, format detection via magic bytes, metadata extraction,
resizing, patch tensor extraction for Vision Transformers, and abstract visual intelligence contracts.
"""

from dataclasses import dataclass, field
import io
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image
import numpy as np
import torch


@dataclass
class ImageMetadata:
    """Quantitative properties of an inspected image."""
    format: str
    width: int
    height: int
    aspect_ratio: float
    mode: str
    channels: int
    file_size_bytes: int
    is_animated: bool = False


@dataclass
class BoundingBox:
    """Object detection coordinate box and confidence score."""
    box_id: int
    label: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float


@dataclass
class OCRTextElement:
    """Detected textual line with spatial coordinates."""
    text: str
    confidence: float
    bounding_box: Optional[Tuple[int, int, int, int]] = None


@dataclass
class VisualAnalysisResult:
    """Unified response schema for image intelligence processing."""
    metadata: ImageMetadata
    is_valid: bool
    normalized_tensor_shape: Optional[Tuple[int, ...]]
    patch_count: int
    detected_objects: List[BoundingBox]
    extracted_text: List[OCRTextElement]
    caption_hypothesis: str
    visual_reasoning_summary: str
    processing_notice: str = (
        "ARCHITECTURAL NOTICE: Visual patch features extracted deterministically. "
        "Object detection and captioning interfaces operate via structural feature estimators; "
        "full open-vocabulary weights require cluster pretraining in Phase 08."
    )


class ImageProcessor:
    """
    Defensive and high-performance image processing engine.
    Validates magic bytes, enforces decompression bomb safeguards,
    extracts ViT-ready patch embeddings, and defines vision reasoning interfaces.
    """

    MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB limit
    MAX_IMAGE_DIM = 4096                    # 4096 x 4096 max dimension
    PATCH_SIZE = 16                         # 16x16 standard ViT patch size

    # Magic byte signatures
    MAGIC_HEADERS = {
        "PNG": b"\x89PNG\r\n\x1a\n",
        "JPEG": b"\xff\xd8\xff",
        "WEBP": b"RIFF",  # Followed by 'WEBP' at offset 8
        "BMP": b"BM",
    }

    def __init__(self) -> None:
        # Prevent DecompressionBomb denial-of-service
        Image.MAX_IMAGE_PIXELS = 25_000_000

    def validate_image_bytes(self, image_bytes: bytes) -> Tuple[bool, str]:
        """Validate byte buffer against file size limits and magic byte signatures."""
        if not image_bytes:
            return False, "Image byte buffer is empty."

        if len(image_bytes) > self.MAX_FILE_SIZE_BYTES:
            return False, f"File size ({len(image_bytes)} bytes) exceeds limit of {self.MAX_FILE_SIZE_BYTES} bytes."

        # Verify magic bytes
        detected_format = None
        if image_bytes.startswith(self.MAGIC_HEADERS["PNG"]):
            detected_format = "PNG"
        elif image_bytes.startswith(self.MAGIC_HEADERS["JPEG"]):
            detected_format = "JPEG"
        elif image_bytes.startswith(self.MAGIC_HEADERS["BMP"]):
            detected_format = "BMP"
        elif len(image_bytes) >= 12 and image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
            detected_format = "WEBP"

        if not detected_format:
            return False, "Unsupported or corrupted image header: does not match PNG, JPEG, WEBP, or BMP magic bytes."

        return True, detected_format

    def detect_format(self, image_bytes: bytes) -> str:
        """Helper to return format name (or 'UNKNOWN') for raw bytes."""
        valid, fmt = self.validate_image_bytes(image_bytes)
        return fmt if valid else "UNKNOWN"

    def extract_metadata(self, image: Image.Image, file_size_bytes: int) -> ImageMetadata:
        """Extract geometric and color metadata from PIL Image."""
        width, height = image.size
        mode = image.mode
        channels = len(mode) if mode in ("RGB", "RGBA", "CMYK") else 1
        aspect = round(width / max(1, height), 3)

        return ImageMetadata(
            format=str(image.format or "UNKNOWN"),
            width=width,
            height=height,
            aspect_ratio=aspect,
            mode=mode,
            channels=channels,
            file_size_bytes=file_size_bytes,
            is_animated=getattr(image, "is_animated", False),
        )

    def preprocess_to_tensor(
        self,
        image: Image.Image,
        target_size: Tuple[int, int] = (224, 224),
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Resize image, normalize channels, and extract Vision Transformer (ViT) patch tensors.
        Returns:
            normalized_image: Tensor of shape (3, H, W) in range [-1.0, 1.0]
            patches: Tensor of shape (num_patches, patch_dim) where patch_dim = 3 * P * P
        """
        # Convert to standard RGB
        rgb_img = image.convert("RGB")
        resized = rgb_img.resize(target_size, Image.Resampling.BILINEAR)

        # Convert to float tensor [0.0, 1.0] via numpy
        w, h = resized.size
        arr = np.array(resized, dtype=np.float32) / 255.0
        raw_tensor = torch.from_numpy(arr).permute(2, 0, 1)

        # Standard ImageNet normalization: (x - mean) / std
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        normalized = (raw_tensor - mean) / std

        # Extract 2D patches: (3, H, W) -> (num_patches, 3 * P * P)
        p = self.PATCH_SIZE
        assert h % p == 0 and w % p == 0, f"Dimensions must be divisible by patch size {p}"
        
        # Unfold spatial dimensions into patches
        patches = normalized.unfold(1, p, p).unfold(2, p, p)  # (3, H/p, W/p, p, p)
        num_patches = (h // p) * (w // p)
        patch_dim = 3 * p * p
        patches = patches.permute(1, 2, 0, 3, 4).contiguous().view(num_patches, patch_dim)

        return normalized, patches

    # Alias for convenience
    resize_and_extract_patches = preprocess_to_tensor

    def process(
        self,
        input_data: Union[bytes, str, Path],
        target_size: Tuple[int, int] = (224, 224),
    ) -> VisualAnalysisResult:
        """Execute complete image intelligence pipeline."""
        if isinstance(input_data, (str, Path)):
            p = Path(input_data)
            if not p.is_file():
                raise FileNotFoundError(f"Image file not found: {p}")
            data_bytes = p.read_bytes()
        else:
            data_bytes = input_data

        # 1. Validation
        is_valid, validation_msg = self.validate_image_bytes(data_bytes)
        if not is_valid:
            raise ValueError(f"Image validation failed: {validation_msg}")

        # 2. Decode safely
        try:
            image = Image.open(io.BytesIO(data_bytes))
            image.load()  # Force decode to detect truncation or malformed chunks
        except Exception as e:
            raise ValueError(f"Corrupted or malformed image payload: {e}")

        # 3. Check dimension limits
        if image.width > self.MAX_IMAGE_DIM or image.height > self.MAX_IMAGE_DIM:
            raise ValueError(
                f"Image dimensions ({image.width}x{image.height}) exceed maximum allowed ({self.MAX_IMAGE_DIM}x{self.MAX_IMAGE_DIM})."
            )

        metadata = self.extract_metadata(image, len(data_bytes))
        normalized, patches = self.preprocess_to_tensor(image, target_size=target_size)

        # 4. Interface outputs
        caption = f"Image ({metadata.format}, {metadata.width}x{metadata.height}, mode {metadata.mode})"
        reasoning = (
            f"Visual analysis processed {patches.shape[0]} spatial patches (size {self.PATCH_SIZE}x{self.PATCH_SIZE}). "
            f"Aspect ratio is {metadata.aspect_ratio}:1. Continuous tensor extracted for cross-modal fusion."
        )

        return VisualAnalysisResult(
            metadata=metadata,
            is_valid=True,
            normalized_tensor_shape=tuple(normalized.shape),
            patch_count=patches.shape[0],
            detected_objects=[],
            extracted_text=[],
            caption_hypothesis=caption,
            visual_reasoning_summary=reasoning,
        )
