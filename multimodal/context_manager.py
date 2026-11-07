"""
404 FOUNDERS — Cross-Modal Context Manager
Preserves, aligns, and indexes multimodal conversational memory across turns.
Resolves cross-modal coreferences and manages bounded cache retention.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class MultimodalContextTurn:
    """A single conversational turn containing text and associated modality artifacts."""
    turn_id: int
    timestamp_utc: str
    user_query: str
    active_modalities: List[str]
    document_summary: Optional[str] = None
    image_caption: Optional[str] = None
    audio_transcript: Optional[str] = None
    video_summary: Optional[str] = None
    fused_features_summary: Optional[str] = None
    assistant_response: Optional[str] = None


class CrossModalContextManager:
    """
    Cross-modal conversational context manager.
    Tracks active media items across interaction turns and resolves cross-modal references.
    """

    MAX_HISTORY_TURNS = 10  # Bounded history buffer to protect memory

    def __init__(self) -> None:
        self.history: List[MultimodalContextTurn] = []
        self._turn_counter = 0

    def add_turn(
        self,
        user_query: str,
        active_modalities: List[str],
        document_summary: Optional[str] = None,
        image_caption: Optional[str] = None,
        audio_transcript: Optional[str] = None,
        video_summary: Optional[str] = None,
        assistant_response: Optional[str] = None,
    ) -> MultimodalContextTurn:
        """Register a new multimodal turn into conversational history."""
        self._turn_counter += 1
        turn = MultimodalContextTurn(
            turn_id=self._turn_counter,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            user_query=user_query,
            active_modalities=active_modalities,
            document_summary=document_summary,
            image_caption=image_caption,
            audio_transcript=audio_transcript,
            video_summary=video_summary,
            assistant_response=assistant_response,
        )
        self.history.append(turn)

        # Evict oldest turn if exceeding memory bound
        if len(self.history) > self.MAX_HISTORY_TURNS:
            self.history.pop(0)

        return turn

    def resolve_cross_modal_reference(self, current_query: str) -> Optional[Dict[str, Any]]:
        """
        Detect cross-modal references (e.g. 'the document', 'the image', 'that video')
        and link to the most recent relevant artifact in conversational memory.
        """
        lower = current_query.lower()
        if not self.history:
            return None

        # Check in reverse chronological order
        for turn in reversed(self.history):
            if any(k in lower for k in ["document", "pdf", "file", "text"]) and turn.document_summary:
                return {
                    "matched_modality": "DOCUMENT",
                    "turn_id": turn.turn_id,
                    "artifact_context": turn.document_summary,
                    "resolution_type": "HISTORICAL_DOCUMENT_REFERENCE",
                }
            if any(k in lower for k in ["image", "picture", "photo"]) and turn.image_caption:
                return {
                    "matched_modality": "IMAGE",
                    "turn_id": turn.turn_id,
                    "artifact_context": turn.image_caption,
                    "resolution_type": "HISTORICAL_IMAGE_REFERENCE",
                }
            if any(k in lower for k in ["audio", "speech", "recording", "voice"]) and turn.audio_transcript:
                return {
                    "matched_modality": "AUDIO",
                    "turn_id": turn.turn_id,
                    "artifact_context": turn.audio_transcript,
                    "resolution_type": "HISTORICAL_AUDIO_REFERENCE",
                }
            if any(k in lower for k in ["video", "clip", "footage"]) and turn.video_summary:
                return {
                    "matched_modality": "VIDEO",
                    "turn_id": turn.turn_id,
                    "artifact_context": turn.video_summary,
                    "resolution_type": "HISTORICAL_VIDEO_REFERENCE",
                }

        return None

    def get_aggregated_context(self) -> str:
        """Return a compact textual representation of recent multimodal turns."""
        if not self.history:
            return "No previous multimodal context."

        lines: List[str] = []
        for t in self.history[-3:]:
            mods = ", ".join(t.active_modalities)
            lines.append(f"Turn {t.turn_id} [{mods}]: Query='{t.user_query}'")
            if t.document_summary:
                lines.append(f"  Doc: {t.document_summary[:100]}...")
            if t.image_caption:
                lines.append(f"  Img: {t.image_caption}")
            if t.video_summary:
                lines.append(f"  Vid: {t.video_summary[:100]}...")
            if t.audio_transcript:
                lines.append(f"  Audio: {t.audio_transcript[:100]}...")

        return "\n".join(lines)
