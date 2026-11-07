"""
404 FOUNDERS — Speech Generation (TTS) Pipeline
Provides text-to-speech synthesis interfaces, multi-voice configuration (English, Hindi),
formant acoustic synthesis, and playable WAV audio byte generation.
"""

import base64
from dataclasses import dataclass, field
import io
import math
from pathlib import Path
import struct
from typing import Any, Dict, List, Optional, Tuple
import wave


@dataclass
class VoiceConfig:
    """Configurable voice synthesis parameters."""
    voice_id: str = "default_neutral"
    language: str = "en"           # "en" (English), "hi" (Hindi)
    pitch_hz: float = 220.0        # Baseline pitch frequency in Hz (A3 = 220 Hz)
    speed_factor: float = 1.0      # Speed multiplier (0.5x to 2.0x)
    sample_rate: int = 16000       # Standard 16 kHz sample rate
    volume: float = 0.8            # Amplitude scale in range [0.1, 1.0]


@dataclass
class SpeechSynthesisResult:
    """Complete output schema for text-to-speech synthesis."""
    text: str
    language: str
    voice_id: str
    duration_seconds: float
    sample_rate: int
    audio_bytes: bytes
    audio_base64_uri: str
    summary: str


class SpeechGenerationEngine:
    """
    Speech Generation (TTS) Engine.
    Synthesizes phonemic acoustic waveforms from input text,
    generating valid PCM WAV audio streams and base64 Data URIs for browser playback.
    Operates strictly offline without external cloud dependencies.
    """

    # Phoneme frequency mapping for deterministic formant synthesis
    CHAR_FORMANT_MAP: Dict[str, Tuple[float, float]] = {
        # Vowels (F1, F2 formant frequencies in Hz)
        "a": (730.0, 1090.0),
        "e": (530.0, 1840.0),
        "i": (270.0, 2290.0),
        "o": (570.0, 840.0),
        "u": (300.0, 870.0),
        # Devanagari Vowels (Hindi)
        "अ": (730.0, 1090.0),
        "आ": (850.0, 1200.0),
        "इ": (270.0, 2290.0),
        "ई": (260.0, 2400.0),
        "उ": (300.0, 870.0),
        "ऊ": (280.0, 750.0),
        "ए": (530.0, 1840.0),
        "ओ": (570.0, 840.0),
    }

    def __init__(self, default_config: Optional[VoiceConfig] = None) -> None:
        self.default_config = default_config or VoiceConfig()

    def synthesize_wav_bytes(
        self,
        text: str,
        config: Optional[VoiceConfig] = None,
    ) -> Tuple[bytes, float]:
        """
        Synthesize speech audio into a valid RIFF/WAV byte stream using acoustic formants.
        Returns:
            (wav_bytes, duration_seconds)
        """
        cfg = config or self.default_config
        sr = cfg.sample_rate
        cleaned = text.strip()
        if not cleaned:
            # Generate 0.2s silence
            cleaned = " "

        # Compute durations per character
        base_char_duration = (0.07 / max(0.2, cfg.speed_factor))
        total_samples: List[int] = []

        for char in cleaned.lower():
            if char == " " or char in ".,!?;:":
                # Silence / pause interval
                pause_samples = int(sr * base_char_duration * 1.5)
                total_samples.extend([0] * pause_samples)
                continue

            f1, f2 = self.CHAR_FORMANT_MAP.get(char, (cfg.pitch_hz, cfg.pitch_hz * 2.0))
            f0 = cfg.pitch_hz

            n_samples = int(sr * base_char_duration)
            for i in range(n_samples):
                t = i / float(sr)
                # Formant synthesis equation: pitch carrier + F1 + F2 resonances with envelope
                envelope = math.sin(math.pi * (i / max(1, n_samples)))  # Hanning-like window
                sample_val = (
                    0.50 * math.sin(2.0 * math.pi * f0 * t) +
                    0.30 * math.sin(2.0 * math.pi * f1 * t) +
                    0.20 * math.sin(2.0 * math.pi * f2 * t)
                ) * envelope * cfg.volume

                # Clamp to 16-bit signed integer range [-32767, 32767]
                clamped = int(max(-32767.0, min(32767.0, sample_val * 32767.0)))
                total_samples.append(clamped)

        duration = len(total_samples) / float(sr)

        # Pack into WAV byte buffer
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)           # Mono
            wf.setsampwidth(2)           # 16-bit
            wf.setframerate(sr)
            packed_frames = struct.pack(f"<{len(total_samples)}h", *total_samples)
            wf.writeframes(packed_frames)

        wav_bytes = buf.getvalue()
        return wav_bytes, round(duration, 3)

    def synthesize(
        self,
        text: str,
        voice_config: Optional[VoiceConfig] = None,
    ) -> SpeechSynthesisResult:
        """Execute full speech synthesis pipeline and generate base64 playback URI."""
        cfg = voice_config or self.default_config
        wav_bytes, duration = self.synthesize_wav_bytes(text, cfg)

        b64_str = base64.b64encode(wav_bytes).decode("ascii")
        data_uri = f"data:audio/wav;base64,{b64_str}"

        summary = (
            f"Synthesized '{text[:30]}...' ({cfg.language.upper()}, {cfg.voice_id}) "
            f"into {duration}s audio track ({len(wav_bytes)} bytes at {cfg.sample_rate} Hz)."
        )

        return SpeechSynthesisResult(
            text=text,
            language=cfg.language,
            voice_id=cfg.voice_id,
            duration_seconds=duration,
            sample_rate=cfg.sample_rate,
            audio_bytes=wav_bytes,
            audio_base64_uri=data_uri,
            summary=summary,
        )
