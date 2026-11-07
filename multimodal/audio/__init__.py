"""
404 FOUNDERS — Multimodal/Audio
Audio spectrogram parsing, mel-filterbank feature extraction, speech recognition (STT),
and speech generation (TTS).
"""

from multimodal.audio.audio_processor import (
    AudioAnalysisResult,
    AudioFeatures,
    AudioMetadata,
    AudioProcessor,
)
from multimodal.audio.speech_generation import (
    SpeechGenerationEngine,
    SpeechSynthesisResult,
    VoiceConfig,
)
from multimodal.audio.speech_recognition import (
    SpeechRecognitionEngine,
    SpeechRecognitionResult,
    SpeechSegment,
)

__all__ = [
    "AudioProcessor",
    "AudioMetadata",
    "AudioFeatures",
    "AudioAnalysisResult",
    "SpeechRecognitionEngine",
    "SpeechSegment",
    "SpeechRecognitionResult",
    "SpeechGenerationEngine",
    "VoiceConfig",
    "SpeechSynthesisResult",
]
