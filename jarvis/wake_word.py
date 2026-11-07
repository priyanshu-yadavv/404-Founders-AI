"""
404 FOUNDERS — Configurable Local Wake-Word Detection Engine
Provides low-resource acoustic energy gating, phonemic subphrase matching,
sensitivity tuning, microphone mute controls, and false-trigger suppression.

DEFAULT WAKE PHRASE: "Hey Founders"
STRICT INVARIANT: Wake-word detection alone NEVER authenticates a user.
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
import re
from typing import Dict, List, Optional, Tuple, Union

import torch
from jarvis.models import WakeWordResult


class WakeWordDetector:
    """
    Configurable local wake-word detector.
    Analyzes streaming audio buffers or transcription hypotheses to identify
    activation phrases with noise suppression and sensitivity gating.
    """

    DEFAULT_WAKE_WORDS = [
        "hey founders",
        "founders",
        "hey 404",
        "404",
        "computer",
        "jarvis",
    ]

    PHONETIC_VARIANTS: Dict[str, List[str]] = {
        "hey founders": ["hey founders", "hey founder", "he founders", "a founders", "hay founders", "हे फाउंडर्स"],
        "founders": ["founders", "founder", "फाउंडर्स"],
        "hey 404": ["hey 404", "hey four o four", "hey four zero four", "हे ४०४"],
        "computer": ["computer", "कंप्यूटर"],
        "jarvis": ["jarvis", "जार्विस"],
    }

    def __init__(
        self,
        wake_words: Optional[List[str]] = None,
        sensitivity: float = 0.8,
        min_energy_threshold: float = 0.008,
        microphone_device_id: Optional[str] = None,
    ) -> None:
        self.wake_words = [w.lower().strip() for w in (wake_words or self.DEFAULT_WAKE_WORDS)]
        self.sensitivity = max(0.1, min(1.0, sensitivity))
        self.min_energy_threshold = min_energy_threshold
        self.microphone_device_id = microphone_device_id
        self._is_enabled = True
        self._is_muted = False
        self._false_trigger_count = 0
        self._detection_count = 0

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    @property
    def is_muted(self) -> bool:
        return self._is_muted

    def enable(self) -> None:
        self._is_enabled = True

    def disable(self) -> None:
        self._is_enabled = False

    def mute(self) -> None:
        self._is_muted = True

    def unmute(self) -> None:
        self._is_muted = False

    def set_sensitivity(self, value: float) -> float:
        self.sensitivity = max(0.1, min(1.0, value))
        return self.sensitivity

    def detect(
        self,
        audio_bytes: Optional[bytes] = None,
        sample_rate: int = 16000,
        transcript_hint: Optional[str] = None,
    ) -> WakeWordResult:
        """Unified wake-word detection entry point for audio or text."""
        now_iso = datetime.now(timezone.utc).isoformat()
        if self._is_muted:
            return WakeWordResult(detected=False, wake_word=None, confidence=0.0, timestamp=now_iso, energy_level=0.0)
        if audio_bytes is not None:
            res = self.detect_from_audio(audio_bytes, sample_rate=sample_rate)
            if transcript_hint and not res.detected and res.energy_level >= self.min_energy_threshold:
                t_res = self.detect_from_transcript(transcript_hint)
                if t_res.detected:
                    t_res.energy_level = res.energy_level
                    return t_res
            return res
        if transcript_hint:
            return self.detect_from_transcript(transcript_hint)
        return WakeWordResult(detected=False, wake_word=None, confidence=0.0, timestamp=now_iso, energy_level=0.0)

    def calculate_audio_energy(self, waveform: Any) -> float:
        """Calculate root-mean-square (RMS) signal energy."""
        if isinstance(waveform, (bytes, bytearray)):
            try:
                from multimodal.audio.audio_processor import AudioProcessor
                _, wf = AudioProcessor().parse_wav(waveform)
                waveform = wf
            except Exception:
                return 0.0
        if not isinstance(waveform, torch.Tensor) or waveform.numel() == 0:
            return 0.0
        return float(torch.sqrt(torch.mean(waveform.float()**2)).item())

    def detect_from_transcript(self, transcript: str) -> WakeWordResult:
        """
        Evaluate wake-word presence in textual transcription stream.
        Applies phonetic normalization and subphrase matching.
        """
        now = datetime.now(timezone.utc).isoformat()

        if not self._is_enabled or self._is_muted:
            return WakeWordResult(
                detected=False,
                wake_word=None,
                confidence=0.0,
                timestamp=now,
                matched_subphrase=None,
            )

        if not transcript or not transcript.strip():
            return WakeWordResult(
                detected=False,
                wake_word=None,
                confidence=0.0,
                timestamp=now,
                matched_subphrase=None,
            )

        clean = transcript.lower().strip()

        # Check configured wake words and phonetic variants
        for canon, variants in self.PHONETIC_VARIANTS.items():
            if canon in self.wake_words or any(w in self.wake_words for w in variants):
                for v in variants:
                    if re.search(r"\b" + re.escape(v) + r"\b", clean, re.IGNORECASE) or v in clean:
                        confidence = round(min(0.99, 0.70 + (0.25 * self.sensitivity)), 2)
                        self._detection_count += 1
                        return WakeWordResult(
                            detected=True,
                            wake_word=canon,
                            confidence=confidence,
                            timestamp=now,
                            matched_subphrase=v,
                        )

        # Fallback check against raw wake word strings
        for ww in self.wake_words:
            if re.search(r"\b" + re.escape(ww) + r"\b", clean, re.IGNORECASE) or ww in clean:
                confidence = round(min(0.99, 0.65 + (0.30 * self.sensitivity)), 2)
                self._detection_count += 1
                return WakeWordResult(
                    detected=True,
                    wake_word=ww,
                    confidence=confidence,
                    timestamp=now,
                    matched_subphrase=ww,
                )

        return WakeWordResult(
            detected=False,
            wake_word=None,
            confidence=0.0,
            timestamp=now,
            matched_subphrase=None,
        )

    def detect_from_audio(
        self,
        waveform: Any,
        sample_rate: int = 16000,
        transcription_hint: Optional[str] = None,
    ) -> WakeWordResult:
        """
        Evaluate audio waveform against acoustic energy threshold and transcript hint.
        Suppresses false triggers on ambient noise and silence.
        """
        now = datetime.now(timezone.utc).isoformat()

        if not self._is_enabled or self._is_muted:
            return WakeWordResult(
                detected=False,
                wake_word=None,
                confidence=0.0,
                timestamp=now,
            )

        if isinstance(waveform, (bytes, bytearray)):
            try:
                from multimodal.audio.audio_processor import AudioProcessor
                _, wf = AudioProcessor().parse_wav(waveform)
                waveform = wf
            except Exception:
                return WakeWordResult(detected=False, wake_word=None, confidence=0.0, timestamp=now)

        energy = self.calculate_audio_energy(waveform)
        # Dynamic energy threshold adjusted by inverse sensitivity
        effective_energy_cutoff = self.min_energy_threshold * (1.2 - 0.5 * self.sensitivity)

        if energy < effective_energy_cutoff:
            # Silence or ambient noise below threshold
            return WakeWordResult(
                detected=False,
                wake_word=None,
                confidence=0.0,
                timestamp=now,
                energy_level=round(energy, 5),
            )

        if transcription_hint:
            res = self.detect_from_transcript(transcription_hint)
            res.energy_level = round(energy, 5)
            return res

        # Without transcription hint, high energy indicates voice activity present but unparsed
        return WakeWordResult(
            detected=False,
            wake_word=None,
            confidence=0.0,
            timestamp=now,
            energy_level=round(energy, 5),
        )
