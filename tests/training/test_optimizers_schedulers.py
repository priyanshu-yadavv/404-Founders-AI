"""
404 FOUNDERS — Unit Tests for Optimizers & Learning Rate Schedulers
"""

import torch
import torch.nn as nn

from training.configs.model_config import EXPERIMENTAL_TINY_CONFIG, PretrainingConfig
from training.initialization.initializer import ModelInitializer
from training.optimizers.optimization_engine import OptimizationEngine
from training.schedulers.lr_scheduler import CosineWarmupScheduler


def test_parameter_grouping_and_weight_decay() -> None:
    """Verify 2D parameters have weight decay and 1D parameters have 0.0 weight decay."""
    model, _ = ModelInitializer(EXPERIMENTAL_TINY_CONFIG).initialize_model()
    cfg = PretrainingConfig(weight_decay=0.05, learning_rate=1e-3)
    engine = OptimizationEngine(model, cfg)

    param_groups = engine.optimizer.param_groups
    assert len(param_groups) == 2

    decay_group = param_groups[0]
    no_decay_group = param_groups[1]

    assert decay_group["weight_decay"] == 0.05
    assert no_decay_group["weight_decay"] == 0.0

    # Ensure all decay parameters have dimension >= 2
    for p in decay_group["params"]:
        assert p.dim() >= 2

    # Ensure all no-decay parameters have dimension < 2
    for p in no_decay_group["params"]:
        assert p.dim() < 2


def test_cosine_warmup_scheduler_dynamics() -> None:
    """Verify linear warmup and cosine decay transitions."""
    lin = nn.Linear(10, 10)
    opt = torch.optim.SGD(lin.parameters(), lr=1.0)
    warmup_steps = 10
    max_steps = 50
    min_lr = 0.1

    scheduler = CosineWarmupScheduler(
        opt,
        warmup_steps=warmup_steps,
        max_steps=max_steps,
        min_lr=min_lr,
    )

    # Initial step 0: ratio = 1/10 -> lr = 0.1 + (1.0 - 0.1) * 0.1 = 0.19
    init_lr = scheduler.get_last_lr()[0]
    assert 0.1 < init_lr < 1.0

    # Step through warmup
    for _ in range(warmup_steps - 1):
        scheduler.step()

    # At warmup end (step 9 -> 10/10), lr should reach peak 1.0
    assert abs(scheduler.get_last_lr()[0] - 1.0) < 1e-5

    # Step to max_steps
    for _ in range(max_steps - warmup_steps + 1):
        scheduler.step()

    # At or after max_steps, lr should floor at min_lr
    assert abs(scheduler.get_last_lr()[0] - min_lr) < 1e-5


def test_scheduler_state_dict_roundtrip() -> None:
    """Verify state serialization and restoration."""
    lin = nn.Linear(5, 5)
    opt = torch.optim.Adam(lin.parameters(), lr=1e-3)
    s1 = CosineWarmupScheduler(opt, warmup_steps=5, max_steps=20, min_lr=1e-5)

    for _ in range(7):
        s1.step()

    state = s1.state_dict()
    assert state["current_step"] == 7

    s2 = CosineWarmupScheduler(opt, warmup_steps=5, max_steps=20, min_lr=1e-5)
    s2.load_state_dict(state)
    assert s2.current_step == 7
    assert s2.get_last_lr() == s1.get_last_lr()
