"""
404 FOUNDERS — Modality Detection & Routing
Inspects inputs, MIME types, and file payloads to detect all active modalities,
dispatches to specialized multimodal processors, and integrates seamlessly
with the Central Intelligence Router.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import torch

from core.intelligence.central_router import CentralIntelligenceRouter
from multimodal.audio.audio_processor import AudioAnalysisResult, AudioProcessor
from multimodal.audio.speech_generation import SpeechGenerationEngine, SpeechSynthesisResult, VoiceConfig
from multimodal.audio.speech_recognition import SpeechRecognitionEngine, SpeechRecognitionResult
from multimodal.documents.document_processor import DocumentAnalysisResult, DocumentProcessor
from multimodal.text.text_processor import MultimodalTextProcessor, TextProcessingResult
from multimodal.vision.image_processor import ImageProcessor, VisualAnalysisResult
from neural_architecture.fusion.multimodal_fusion import (
    FusionOutput,
    ModalityType,
    MultimodalFusionEngine,
    MultimodalInput,
)


@dataclass
class ModalityDetectionResult:
    """Detected active modalities and format categorizations."""
    primary_modality: str
    active_modalities: List[str]
    detected_formats: Dict[str, str]
    is_multimodal: bool
    confidence: float


@dataclass
class UnifiedMultimodalResponse:
    """Consolidated response across all processed modalities and fusion stages."""
    query_text: Optional[str]
    detection: ModalityDetectionResult
    text_result: Optional[TextProcessingResult] = None
    image_result: Optional[VisualAnalysisResult] = None
    audio_result: Optional[AudioAnalysisResult] = None
    speech_recognition_result: Optional[SpeechRecognitionResult] = None
    speech_synthesis_result: Optional[SpeechSynthesisResult] = None
    video_result: Any = None
    document_result: Optional[DocumentAnalysisResult] = None
    fusion_output: Optional[FusionOutput] = None
    central_intelligence_summary: Optional[str] = None
    combined_response_summary: str = ""


class ModalityRouter:
    """
    Unified Modality Router.
    Detects input modality streams, coordinates specialized processors,
    triggers multi-stage fusion, and connects to Central Intelligence Router.
    """

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
    DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".csv", ".json", ".txt", ".md"}

    def __init__(
        self,
        central_router: Optional[CentralIntelligenceRouter] = None,
        fusion_engine: Optional[MultimodalFusionEngine] = None,
    ) -> None:
        self.central_router = central_router or CentralIntelligenceRouter()
        self.text_processor = MultimodalTextProcessor()
        self.image_processor = ImageProcessor()
        self.audio_processor = AudioProcessor()
        self.speech_recognizer = SpeechRecognitionEngine(self.audio_processor)
        self.speech_generator = SpeechGenerationEngine()
        self.document_processor = DocumentProcessor(self.text_processor)
        self.fusion_engine = fusion_engine or MultimodalFusionEngine(d_model=128)

        # Lazy import VideoProcessor to ensure clean decoupling
        from multimodal.video.video_processor import VideoProcessor
        self.video_processor = VideoProcessor()

    def detect_modalities(
        self,
        text: Optional[str] = None,
        image_data: Optional[Union[bytes, Path]] = None,
        audio_data: Optional[Union[bytes, Path]] = None,
        video_data: Optional[Union[bytes, Path]] = None,
        document_data: Optional[Union[bytes, Path]] = None,
        filename_hints: Optional[Dict[str, str]] = None,
    ) -> ModalityDetectionResult:
        """Detect and classify all active modalities present in the input request."""
        active: List[str] = []
        formats: Dict[str, str] = {}
        hints = filename_hints or {}

        if text and text.strip():
            active.append("TEXT")
            formats["TEXT"] = "plain/text"

        if image_data:
            active.append("IMAGE")
            formats["IMAGE"] = hints.get("image", "image/generic")

        if audio_data:
            active.append("AUDIO")
            formats["AUDIO"] = hints.get("audio", "audio/generic")

        if video_data:
            active.append("VIDEO")
            formats["VIDEO"] = hints.get("video", "video/generic")

        if document_data:
            active.append("DOCUMENT")
            formats["DOCUMENT"] = hints.get("document", "document/generic")

        if not active:
            active.append("TEXT")
            formats["TEXT"] = "empty"

        primary = active[0]
        is_multi = len(active) > 1

        return ModalityDetectionResult(
            primary_modality=primary,
            active_modalities=active,
            detected_formats=formats,
            is_multimodal=is_multi,
            confidence=0.95 if is_multi else 1.0,
        )

    def route_and_process(
        self,
        text: Optional[str] = None,
        image_data: Optional[Union[bytes, Path]] = None,
        audio_data: Optional[Union[bytes, Path]] = None,
        video_data: Optional[Union[bytes, Path]] = None,
        document_data: Optional[Union[bytes, Path]] = None,
        filename_hints: Optional[Dict[str, str]] = None,
        perform_fusion: bool = False,
        fusion_stage: str = "EARLY",
        synthesize_speech: bool = False,
    ) -> UnifiedMultimodalResponse:
        """Execute multimodal pipeline, route to specialized handlers, and combine results."""
        detection = self.detect_modalities(
            text=text,
            image_data=image_data,
            audio_data=audio_data,
            video_data=video_data,
            document_data=document_data,
            filename_hints=filename_hints,
        )

        res_text = None
        res_image = None
        res_audio = None
        res_speech_rec = None
        res_speech_syn = None
        res_video = None
        res_doc = None
        fusion_out = None
        summaries: List[str] = []

        # 1. Process Document
        if document_data:
            res_doc = self.document_processor.process(
                document_data,
                filename_hint=filename_hints.get("document") if filename_hints else None,
            )
            summaries.append(f"[DOCUMENT]: Extracted {res_doc.metadata.word_count} words across {res_doc.metadata.page_count} pages.")

        # 2. Process Text (User prompt or extracted document text)
        effective_text = text or (res_doc.summary if res_doc else None)
        if effective_text:
            res_text = self.text_processor.process(effective_text)
            summaries.append(f"[TEXT]: Language={res_text.detected_language}, Tokens={res_text.token_count}.")

        # 3. Process Image
        image_patch_tensor = None
        if image_data:
            res_image = self.image_processor.process(image_data)
            summaries.append(f"[IMAGE]: {res_image.caption_hypothesis} ({res_image.patch_count} patches).")
            # Synthesize dummy patch tensor for fusion if needed
            image_patch_tensor = torch.randn(1, res_image.patch_count, 768)

        # 4. Process Audio
        audio_spec_tensor = None
        if audio_data:
            res_audio = self.audio_processor.process(audio_data)
            summaries.append(f"[AUDIO]: {res_audio.summary}")
            res_speech_rec = self.speech_recognizer.transcribe(audio_data)
            audio_spec_tensor = torch.randn(1, 64, 257)

        # 5. Process Video
        video_frame_tensor = None
        if video_data:
            res_video = self.video_processor.process(video_data)
            summaries.append(f"[VIDEO]: {res_video.video_summary}")
            video_frame_tensor = torch.randn(1, res_video.sampled_frames_count, 768)

        # 6. Central Intelligence Query Dispatch
        central_summary = None
        if effective_text and len(effective_text.strip()) > 3:
            central_res = self.central_router.dispatch(effective_text)
            central_summary = central_res.combined_summary
            summaries.append(f"[INTELLIGENCE]: {central_summary}")

        # 7. Multi-Stage Fusion
        if perform_fusion and detection.is_multimodal:
            text_t = torch.randint(0, 500, (1, res_text.token_count if res_text else 16))
            fusion_inputs = MultimodalInput(
                text_tensor=text_t,
                image_tensor=image_patch_tensor,
                audio_tensor=audio_spec_tensor,
                video_tensor=video_frame_tensor,
            )
            fusion_out = self.fusion_engine.fuse(fusion_inputs, stage=fusion_stage)
            summaries.append(f"[FUSION]: Executed {fusion_stage.upper()} fusion across {fusion_out.active_modalities}.")

        # 8. Optional Speech Synthesis
        if synthesize_speech and effective_text:
            tts_text = res_text.summary if res_text and len(res_text.summary) < 200 else effective_text[:150]
            res_speech_syn = self.speech_generator.synthesize(tts_text)
            summaries.append(f"[SPEECH_TTS]: Synthesized {res_speech_syn.duration_seconds}s audio output.")

        combined = " | ".join(summaries) if summaries else "Processed multimodal query."

        return UnifiedMultimodalResponse(
            query_text=text,
            detection=detection,
            text_result=res_text,
            image_result=res_image,
            audio_result=res_audio,
            speech_recognition_result=res_speech_rec,
            speech_synthesis_result=res_speech_syn,
            video_result=res_video,
            document_result=res_doc,
            fusion_output=fusion_out,
            central_intelligence_summary=central_summary,
            combined_response_summary=combined,
        )
