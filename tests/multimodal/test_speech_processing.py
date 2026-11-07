"""
Unit tests for Speech Recognition (STT) and Speech Generation (TTS).
Verifies voice activity detection (VAD), speech segment generation,
phoneme formant acoustic synthesis, valid WAV byte generation,
and browser playback Data URI formatting for English and Hindi.
"""

import io
import wave
import pytest
import torch

from multimodal.audio.speech_recognition import SpeechRecognitionEngine, SpeechRecognitionResult
from multimodal.audio.speech_generation import SpeechGenerationEngine, SpeechSynthesisResult, VoiceConfig


@pytest.fixture
def speech_recognizer():
    return SpeechRecognitionEngine()


@pytest.fixture
def speech_generator():
    return SpeechGenerationEngine()


def test_speech_generation_valid_wav_pcm(speech_generator):
    text = "404 FOUNDERS Intelligence"
    wav_bytes, duration = speech_generator.synthesize_wav_bytes(text)

    assert len(wav_bytes) > 44  # WAV header is 44 bytes
    assert duration > 0.1

    # Verify byte stream with standard wave library
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        assert wf.getnchannels() == 1  # Mono
        assert wf.getsampwidth() == 2  # 16-bit
        assert wf.getframerate() == 16000
        frames = wf.readframes(wf.getnframes())
        assert len(frames) > 0


def test_speech_generation_full_result_and_base64_uri(speech_generator):
    text = "नमस्ते भारत"
    cfg = VoiceConfig(language="hi", pitch_hz=250.0, speed_factor=1.2)
    res = speech_generator.synthesize(text, voice_config=cfg)

    assert isinstance(res, SpeechSynthesisResult)
    assert res.language == "hi"
    assert res.audio_base64_uri.startswith("data:audio/wav;base64,")
    assert len(res.audio_base64_uri) > 100
    assert res.duration_seconds > 0.1


def test_voice_activity_detection(speech_recognizer):
    sr = 16000
    # Create 1 second of audio: 0.3s silence + 0.4s loud tone + 0.3s silence
    silence_prefix = torch.zeros(int(0.3 * sr))
    tone = torch.sin(2.0 * 3.14159 * 440.0 * torch.linspace(0, 0.4, int(0.4 * sr))) * 0.8
    silence_suffix = torch.zeros(int(0.3 * sr))
    waveform = torch.cat([silence_prefix, tone, silence_suffix]).unsqueeze(0)

    intervals = speech_recognizer.detect_voice_activity(waveform, sr, frame_duration_ms=50, energy_threshold=0.02)
    assert len(intervals) >= 1
    start, end = intervals[0]
    assert start >= 0.25 and start <= 0.35
    assert end >= 0.65 and end <= 0.75


def test_speech_transcription(speech_recognizer, speech_generator):
    # Synthesize an utterance and pass to recognizer
    wav_bytes, _ = speech_generator.synthesize_wav_bytes("Hello Foundation AI")
    result = speech_recognizer.transcribe(wav_bytes, language_hint="en")

    assert isinstance(result, SpeechRecognitionResult)
    assert result.detected_language == "en"
    assert result.duration_seconds > 0.1
    assert len(result.segments) >= 1
    assert result.overall_confidence > 0.5
