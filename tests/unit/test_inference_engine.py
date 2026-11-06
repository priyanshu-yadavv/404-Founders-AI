"""
404 FOUNDERS — Unit Tests for Inference Engine
"""

import pytest
import torch

from core.exceptions import ArchitectureError
from core.intelligence.neural_core import NeuralCoreConfig
from neural_architecture.inference import InferenceEngine


def test_inference_engine_execution() -> None:
    """Verify InferenceEngine validated forward pass on Python list inputs."""
    config = NeuralCoreConfig(d_model=32, n_layers=1, n_heads=2, vocab_size=128, max_seq_len=32)
    engine = InferenceEngine(config=config)

    # Pass raw Python list
    raw_prompt = [10, 20, 30, 40]
    output = engine.infer(raw_prompt)

    assert output.logits.shape == (1, 4, 128)
    assert not torch.isnan(output.logits).any()


def test_inference_input_validation_errors() -> None:
    """Verify InferenceEngine catches malformed inputs, out-of-bounds tokens, and empty sequences."""
    config = NeuralCoreConfig(d_model=32, n_layers=1, n_heads=2, vocab_size=128, max_seq_len=16)
    engine = InferenceEngine(config=config)

    # 1. Empty sequence
    with pytest.raises(ArchitectureError):
        engine.infer([])

    # 2. Sequence exceeding max_seq_len
    with pytest.raises(ArchitectureError):
        engine.infer([1] * 20)

    # 3. Out-of-bounds token ID (token 200 >= vocab_size 128)
    with pytest.raises(ArchitectureError):
        engine.infer([10, 200, 30])


def test_greedy_token_generation() -> None:
    """Verify greedy autoregressive token prediction appends new tokens."""
    config = NeuralCoreConfig(d_model=32, n_layers=1, n_heads=2, vocab_size=128, max_seq_len=32)
    engine = InferenceEngine(config=config)

    prompt = [5, 12, 19]
    generated = engine.generate_greedy_tokens(prompt, max_new_tokens=3)

    assert len(generated) == len(prompt) + 3
    assert generated[: len(prompt)] == prompt
    # All generated tokens must be within vocabulary range
    assert all(0 <= t < 128 for t in generated)
