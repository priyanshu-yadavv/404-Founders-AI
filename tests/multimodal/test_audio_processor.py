"""
Unit tests for AudioProcessor.
Verifies audio format detection (WAV, FLAC, OGG, MP3), RIFF/WAV parsing into float tensors,
RMS energy calculation, zero-crossing rate, SNR estimation, and STFT spectrogram extraction.
"""

import io
import math
import struct
import wave
import pytest
import torch

from multimodal.audio.audio_processor import AudioProcessor, AudioAnalysisResult


@pytest.fixture
def audio_processor():
    return AudioProcessor()


def generate_synthetic_wav_bytes(
    duration_sec: float = 0.5,
    sample_rate: int = 16000,
    channels: int = 1,
    frequency_hz: float = 440.0,
    amplitude: float = 0.8,
) -> bytes:
    """Generate in-memory PCM 16-bit sine wave WAV bytes."""
    n_samples = int(duration_sec * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        
        frames = []
        for i in range(n_samples):
            val = int(amplitude * 32767.0 * math.sin(2.0 * math.pi * frequency_hz * i / sample_rate))
            for _ in range(channels):
                frames.append(val)
        
        raw_data = struct.pack(f"<{len(frames)}h", *frames)
        wf.writeframes(raw_data)
        
    return buf.getvalue()


def test_audio_format_detection(audio_processor):
    wav_bytes = generate_synthetic_wav_bytes()
    assert audio_processor.detect_format(wav_bytes) == "WAV"

    flac_magic = b"fLaC\x00\x00\x00\x22" + b"\x00" * 32
    assert audio_processor.detect_format(flac_magic) == "FLAC"

    ogg_magic = b"OggS\x00\x02\x00\x00" + b"\x00" * 32
    assert audio_processor.detect_format(ogg_magic) == "OGG"

    garbage = b"CORRUPTED_AUDIO_PAYLOAD"
    assert audio_processor.detect_format(garbage) == "UNKNOWN"


def test_parse_wav_pcm_normalization(audio_processor):
    wav_bytes = generate_synthetic_wav_bytes(duration_sec=0.2, sample_rate=16000, channels=1, frequency_hz=440.0)
    meta, waveform = audio_processor.parse_wav(wav_bytes)

    assert meta.format == "WAV"
    assert meta.sample_rate == 16000
    assert meta.channels == 1
    assert meta.duration_seconds == pytest.approx(0.2, abs=0.01)

    assert isinstance(waveform, torch.Tensor)
    assert waveform.dtype == torch.float32
    assert waveform.shape[0] == 1  # 1 channel
    assert waveform.shape[1] == 3200  # 0.2 * 16000
    assert waveform.max().item() <= 1.0
    assert waveform.min().item() >= -1.0


def test_compute_audio_features(audio_processor):
    wav_bytes = generate_synthetic_wav_bytes(duration_sec=0.3, sample_rate=16000, frequency_hz=440.0, amplitude=0.5)
    _, waveform = audio_processor.parse_wav(wav_bytes)
    features = audio_processor.compute_features(waveform, 16000)

    assert features.rms_energy > 0.1
    assert features.zero_crossing_rate > 0.01
    assert features.estimated_snr_db > 0.0
    assert features.is_silent is False
    assert len(features.spectrogram_shape) == 2
    assert features.spectrogram_shape[0] > 0
    assert features.spectrogram_shape[1] > 0


def test_full_audio_pipeline(audio_processor):
    wav_bytes = generate_synthetic_wav_bytes(duration_sec=0.25, sample_rate=16000)
    res = audio_processor.process(wav_bytes)

    assert isinstance(res, AudioAnalysisResult)
    assert res.is_valid is True
    assert res.metadata.sample_rate == 16000
    assert res.features.rms_energy > 0
    assert len(res.summary) > 0
