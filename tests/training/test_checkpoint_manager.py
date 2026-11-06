"""
404 FOUNDERS — Unit Tests for Secure Checkpoint Management
"""

import tempfile
from pathlib import Path
import pytest
import torch

from training.checkpoints.checkpoint_manager import (
    CheckpointCorruptedError,
    CheckpointManager,
)
from training.configs.model_config import EXPERIMENTAL_TINY_CONFIG, PretrainingConfig
from training.initialization.initializer import ModelInitializer
from training.optimizers.optimization_engine import OptimizationEngine
from training.schedulers.lr_scheduler import CosineWarmupScheduler


def test_atomic_checkpoint_persistence_and_recovery() -> None:
    """Verify atomic write, SHA-256 sidecar generation, and full state restoration."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ckpt_mgr = CheckpointManager(checkpoint_dir=tmp_dir, keep_last_n=3)

        model, _ = ModelInitializer(EXPERIMENTAL_TINY_CONFIG).initialize_model()
        opt = OptimizationEngine(model, PretrainingConfig())
        sched = CosineWarmupScheduler(opt.optimizer, warmup_steps=5, max_steps=20)

        # Save checkpoint
        ckpt_path, sha256 = ckpt_mgr.save_checkpoint(
            step=10,
            model=model,
            optimizer_engine=opt,
            scheduler=sched,
            model_config=EXPERIMENTAL_TINY_CONFIG,
            pretraining_config=PretrainingConfig(),
            metrics={"train_loss": 5.42},
            is_best=True,
        )

        assert ckpt_path.is_file()
        assert ckpt_path.with_suffix(".pt.sha256").is_file()

        # Load checkpoint into new model instance
        new_model, _ = ModelInitializer(EXPERIMENTAL_TINY_CONFIG).initialize_model(seed=999)
        new_opt = OptimizationEngine(new_model, PretrainingConfig())
        new_sched = CosineWarmupScheduler(new_opt.optimizer, warmup_steps=5, max_steps=20)

        payload = ckpt_mgr.load_checkpoint(
            ckpt_path,
            model=new_model,
            optimizer_engine=new_opt,
            scheduler=new_sched,
            verify_integrity=True,
        )

        assert payload["step"] == 10
        assert payload["metrics"]["train_loss"] == 5.42

        # Assert parameters match exactly
        for p_orig, p_loaded in zip(model.parameters(), new_model.parameters()):
            assert torch.allclose(p_orig, p_loaded, atol=1e-6)


def test_checkpoint_tamper_detection() -> None:
    """Verify CheckpointCorruptedError when payload bytes are tampered with."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        ckpt_mgr = CheckpointManager(checkpoint_dir=tmp_dir)
        model, _ = ModelInitializer(EXPERIMENTAL_TINY_CONFIG).initialize_model()
        opt = OptimizationEngine(model, PretrainingConfig())
        sched = CosineWarmupScheduler(opt.optimizer, warmup_steps=5, max_steps=20)

        ckpt_path, _ = ckpt_mgr.save_checkpoint(
            step=5,
            model=model,
            optimizer_engine=opt,
            scheduler=sched,
            model_config=EXPERIMENTAL_TINY_CONFIG,
            pretraining_config=PretrainingConfig(),
        )

        # Tamper with checkpoint file on disk (corrupting bytes)
        with open(ckpt_path, "ab") as f:
            f.write(b"\x00\xffCORRUPTED_BYTES")

        # Loading must raise CheckpointCorruptedError
        with pytest.raises(CheckpointCorruptedError, match="integrity failure"):
            ckpt_mgr.load_checkpoint(ckpt_path, verify_integrity=True)
