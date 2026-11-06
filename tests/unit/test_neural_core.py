"""
404 FOUNDERS — Unit Tests for Central Neural Core
"""

import pytest
import torch

from core.exceptions import ArchitectureError, ShapeMismatchError
from core.intelligence.neural_core import NeuralCore, NeuralCoreConfig


def test_neural_core_initialization_and_param_count() -> None:
    """Verify NeuralCore initializes with small CPU dimensions and computes parameter count."""
    config = NeuralCoreConfig(
        d_model=64,
        n_layers=2,
        n_heads=2,
        vocab_size=256,
        max_seq_len=64,
        chunk_size=8,
        window_size=16,
    )
    model = NeuralCore(config)
    assert model.backend_type == "pytorch"
    assert model.parameter_count > 0
    # Expected parameter count under small dimensions is ~329k
    assert 100_000 < model.parameter_count < 500_000


def test_deterministic_initialization() -> None:
    """Verify identical seeds produce identical parameters; distinct seeds produce distinct parameters."""
    cfg1 = NeuralCoreConfig(d_model=32, n_layers=1, n_heads=2, vocab_size=128, random_seed=404)
    cfg2 = NeuralCoreConfig(d_model=32, n_layers=1, n_heads=2, vocab_size=128, random_seed=404)
    cfg3 = NeuralCoreConfig(d_model=32, n_layers=1, n_heads=2, vocab_size=128, random_seed=999)

    m1 = NeuralCore(cfg1)
    m2 = NeuralCore(cfg2)
    m3 = NeuralCore(cfg3)

    # m1 and m2 must be bit-for-bit identical
    for p1, p2 in zip(m1.parameters(), m2.parameters()):
        assert torch.equal(p1, p2)

    # m1 and m3 must differ
    diff_found = any(not torch.equal(p1, p3) for p1, p3 in zip(m1.parameters(), m3.parameters()))
    assert diff_found is True


def test_forward_pass_and_hidden_states_cpu() -> None:
    """Verify forward computation pass and intermediate hidden state caching on CPU."""
    config = NeuralCoreConfig(
        d_model=64,
        n_layers=2,
        n_heads=2,
        vocab_size=256,
        max_seq_len=64,
        chunk_size=8,
        window_size=16,
    )
    model = NeuralCore(config)
    model.eval()

    input_ids = torch.randint(0, 256, (2, 16), dtype=torch.long)
    output = model(input_ids, return_hidden_states=True)

    assert output.logits.shape == (2, 16, 256)
    assert output.hidden_states is not None
    # Input projection + 2 layers = 3 intermediate state snapshots
    assert len(output.hidden_states) == 3
    assert output.metadata["parameter_count"] == model.parameter_count


def test_end_to_end_gradient_propagation() -> None:
    """Verify loss calculation and backpropagation across all hierarchical modules."""
    config = NeuralCoreConfig(
        d_model=64,
        n_layers=2,
        n_heads=2,
        vocab_size=256,
        max_seq_len=64,
        chunk_size=8,
        window_size=16,
    )
    model = NeuralCore(config)
    model.train()

    input_ids = torch.randint(0, 256, (2, 8), dtype=torch.long)
    targets = torch.randint(0, 256, (2, 8), dtype=torch.long)

    output = model(input_ids)
    # Cross entropy loss
    loss = torch.nn.functional.cross_entropy(output.logits.view(-1, 256), targets.view(-1))
    loss.backward()

    # Verify gradients computed across all stages
    assert model.input_projection.embedding.weight.grad is not None
    assert model.layers[0].attention.global_branch.q_proj.weight.grad is not None
    assert model.layers[0].ffn.w_gate.weight.grad is not None
    assert model.output_projection.linear.weight.grad is not None
    assert not torch.isnan(model.output_projection.linear.weight.grad).any()


def test_invalid_input_handling() -> None:
    """Verify NeuralCore raises descriptive exceptions on malformed inputs."""
    config = NeuralCoreConfig(d_model=64, n_layers=1, vocab_size=256, max_seq_len=32)
    model = NeuralCore(config)

    # 1. Input exceeding max_seq_len
    with pytest.raises(ArchitectureError):
        model(torch.randint(0, 256, (1, 40)))

    # 2. Input with invalid rank (3D instead of 2D)
    with pytest.raises(ShapeMismatchError):
        model(torch.randint(0, 256, (1, 10, 5)))
