"""
404 FOUNDERS — Natural Speech Generation (TTS) Engine
Provides natural-sounding conversational speech synthesis for English, Hindi, and Hinglish.
Features configurable speaking speed, baseline pitch, natural pauses, sentence pacing,
interruptible audio synthesis, and base64 Data URI generation for instant browser playback.

STRICT INVARIANTS:
1. Original 404 FOUNDERS voice identity (calm, intelligent, clear).
2. Never clones a real individual's voice without explicit authorization.
3. Operates entirely offline without cloud speech dependencies.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
import io
import math
import re
import struct
from typing import Any, Dict, List, Optional, Tuple
import wave

from multimodal.audio.speech_generation import SpeechGenerationEngine, SpeechSynthesisResult, VoiceConfig


@dataclass
class JarvisSpeechOutput:
    """Consolidated speech synthesis output for JARVIS verbal responses."""
    text: str
    language: str
    voice_id: str
    duration_seconds: float
    sample_rate: int
    audio_bytes: bytes
    audio_base64_uri: str
    sentence_count: int
    is_interrupted: bool = False
    audio_format: str = "audio/wav"

    @property
    def audio_base64(self) -> str:
        return base64.b64encode(self.audio_bytes).decode("utf-8")


class JarvisTTSEngine:
    """
    JARVIS Conversational Speech Synthesis Engine.
    Coordinates language-aware acoustic formant generation, sentence-level pauses,
    and instantaneous barge-in interruption.
    """

    VOICE_PRESETS: Dict[str, VoiceConfig] = {
        "founders_calm": VoiceConfig(
            voice_id="founders_calm",
            language="en",
            pitch_hz=210.0,
            speed_factor=1.0,
            sample_rate=16000,
            volume=0.85,
        ),
        "founders_hindi": VoiceConfig(
            voice_id="founders_hindi",
            language="hi",
            pitch_hz=215.0,
            speed_factor=1.0,
            sample_rate=16000,
            volume=0.85,
        ),
        "founders_fast": VoiceConfig(
            voice_id="founders_fast",
            language="en",
            pitch_hz=220.0,
            speed_factor=1.25,
            sample_rate=16000,
            volume=0.85,
        ),
    }

    def __init__(self, base_engine: Optional[SpeechGenerationEngine] = None) -> None:
        self.base_engine = base_engine or SpeechGenerationEngine()
        self._is_interrupted = False

    def reset_interrupt(self) -> None:
        self._is_interrupted = False

    def interrupt(self) -> None:
        """Trigger immediate barge-in interrupt, stopping active audio synthesis."""
        self._is_interrupted = True

    def split_sentences(self, text: str) -> List[str]:
        """Split input response into clean sentences for natural acoustic pacing."""
        raw_parts = re.split(r"([.!?।\n]+)", text)
        sentences: List[str] = []
        current = ""

        for part in raw_parts:
            current += part
            if re.search(r"[.!?।\n]+", part):
                stripped = current.strip()
                if stripped:
                    sentences.append(stripped)
                current = ""

        if current.strip():
            sentences.append(current.strip())

        return sentences if sentences else [text.strip()]

    def generate_silence_bytes(self, duration_sec: float = 0.15, sample_rate: int = 16000) -> bytes:
        """Generate silent PCM frames for natural inter-sentence pauses."""
        num_frames = int(duration_sec * sample_rate)
        return struct.pack(f"<{num_frames}h", *([0] * num_frames))

    def synthesize_response(
        self,
        text: str,
        voice_id: str = "founders_calm",
        speed_factor: float = 1.0,
        pitch_hz: Optional[float] = None,
        language: Optional[str] = None,
        speed: Optional[float] = None,
        pitch: Optional[float] = None,
    ) -> JarvisSpeechOutput:
        """
        Synthesize assistant response text into spoken audio.
        Supports multi-sentence pauses, language adaptation (EN / HI / Hinglish),
        and graceful interruption.
        """
        self.reset_interrupt()

        if speed is not None:
            speed_factor = speed
        if pitch is not None and pitch_hz is None:
            pitch_hz = 200.0 * pitch

        if not text or not text.strip():
            empty_wav, dur = self.base_engine.synthesize_wav_bytes("")
            b64_uri = f"data:audio/wav;base64,{base64.b64encode(empty_wav).decode('utf-8')}"
            return JarvisSpeechOutput(
                text="",
                language="en",
                voice_id=voice_id,
                duration_seconds=0.0,
                sample_rate=16000,
                audio_bytes=empty_wav,
                audio_base64_uri=b64_uri,
                sentence_count=0,
            )

        # Detect language if not specified
        effective_lang = language or ("hi" if any(0x0900 <= ord(c) <= 0x097F for c in text) else "en")
        preset_key = "founders_hindi" if effective_lang == "hi" else voice_id
        config = self.VOICE_PRESETS.get(preset_key, self.VOICE_PRESETS["founders_calm"])

        # Override speed and pitch if requested
        cfg = VoiceConfig(
            voice_id=config.voice_id,
            language=effective_lang,
            pitch_hz=pitch_hz if pitch_hz is not None else config.pitch_hz,
            speed_factor=speed_factor if speed_factor != 1.0 else config.speed_factor,
            sample_rate=config.sample_rate,
            volume=config.volume,
        )

        sentences = self.split_sentences(text)
        pcm_chunks: List[bytes] = []
        total_duration = 0.0

        for s_idx, sentence in enumerate(sentences):
            if self._is_interrupted:
                break

            wav_bytes, dur = self.base_engine.synthesize_wav_bytes(sentence, config=cfg)
            # Strip WAV header (first 44 bytes) to concatenate raw PCM
            if len(wav_bytes) > 44:
                pcm_chunks.append(wav_bytes[44:])
                total_duration += dur

            # Insert brief natural pause between sentences
            if s_idx < len(sentences) - 1 and not self._is_interrupted:
                pause_bytes = self.generate_silence_bytes(duration_sec=0.12, sample_rate=cfg.sample_rate)
                pcm_chunks.append(pause_bytes)
                total_duration += 0.12

        # Package combined PCM into final WAV
        combined_pcm = b"".join(pcm_chunks)
        num_samples = len(combined_pcm) // 2

        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + len(combined_pcm),
            b"WAVE",
            b"fmt ",
            16,
            1,  # PCM
            1,  # mono
            cfg.sample_rate,
            cfg.sample_rate * 2,
            2,  # block align
            16,  # 16-bit
            b"data",
            len(combined_pcm),
        )
        final_wav = header + combined_pcm
        b64_uri = f"data:audio/wav;base64,{base64.b64encode(final_wav).decode('utf-8')}"

        return JarvisSpeechOutput(
            text=text,
            language=effective_lang,
            voice_id=cfg.voice_id,
            duration_seconds=round(total_duration, 3),
            sample_rate=cfg.sample_rate,
            audio_bytes=final_wav,
            audio_base64_uri=b64_uri,
            sentence_count=len(sentences),
            is_interrupted=self._is_interrupted,
        )

    synthesize = synthesize_response
