"""
404 FOUNDERS — Distributed Parallelism & Checkpointing Tests
Validates 4D parallelism grids, gradient synchronization policies, and atomic sharded checkpointing.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from infrastructure.distributed import (
    DistributedCheckpointManager,
    GradientSyncManager,
    GradientSyncPolicy,
    ParallelismConfig,
    ParallelismEngine,
)


def test_parallelism_config_validation() -> None:
    """Verify 4D parallelism grid constraint DP * TP * PP * SP == total_gpus."""
    # Valid 64-GPU grid: 8 * 4 * 2 * 1 = 64
    valid_cfg = ParallelismConfig(
        total_gpus=64,
        data_parallel_size=8,
        tensor_parallel_size=4,
        pipeline_parallel_size=2,
        sequence_parallel_size=1,
    )
    assert valid_cfg.total_gpus == 64

    # Invalid grid: 8 * 4 * 4 * 1 = 128 != 64
    with pytest.raises(ValueError, match="Invalid 4D Parallelism grid"):
        ParallelismConfig(
            total_gpus=64,
            data_parallel_size=8,
            tensor_parallel_size=4,
            pipeline_parallel_size=4,
            sequence_parallel_size=1,
        )


def test_parallelism_engine_recommendations() -> None:
    """Verify engine proposes valid 4D distributions matching cluster hardware."""
    # Tier A (2 GPUs, small model)
    cfg_a = ParallelismEngine.recommend_topology(
        parameter_count=1_000_000_000,
        total_gpus=2,
        context_length=2048,
    )
    assert cfg_a.total_gpus == 2
    assert cfg_a.data_parallel_size * cfg_a.tensor_parallel_size * cfg_a.pipeline_parallel_size * cfg_a.sequence_parallel_size == 2

    # Tier B (8 GPUs, 7B model)
    cfg_b = ParallelismEngine.recommend_topology(
        parameter_count=7_000_000_000,
        total_gpus=8,
        context_length=4096,
    )
    assert cfg_b.total_gpus == 8
    assert cfg_b.tensor_parallel_size in (1, 2, 4, 8)

    # Tier C (64 GPUs, 16B model)
    cfg_c = ParallelismEngine.recommend_topology(
        parameter_count=16_000_000_000,
        total_gpus=64,
        context_length=8192,
    )
    assert cfg_c.total_gpus == 64
    assert cfg_c.data_parallel_size * cfg_c.tensor_parallel_size * cfg_c.pipeline_parallel_size * cfg_c.sequence_parallel_size == 64


def test_gradient_sync_manager() -> None:
    """Verify gradient synchronization bucket management and policy derivation."""
    policy_single = GradientSyncManager.get_optimized_policy(total_gpus=8, is_multinode=False)
    assert policy_single.bucket_cap_mb == 25.0
    assert policy_single.allreduce_precision == "bfloat16"
    assert policy_single.overlap_backward_communication is True

    policy_multi = GradientSyncManager.get_optimized_policy(total_gpus=64, is_multinode=True)
    assert policy_multi.bucket_cap_mb == 50.0
    assert policy_multi.gradient_accumulation_steps == 4


def test_atomic_sharded_checkpoint_persistence() -> None:
    """Verify checkpoint manager saves atomic shards, generates SHA-256 manifest, and verifies integrity."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = DistributedCheckpointManager(
            checkpoint_dir=tmp_dir,
            max_to_keep=3,
            milestone_interval_steps=1000,
        )

        shards = {
            "shard_rank_0.bin": b"rank_0_weights_and_optimizer_state_12345",
            "shard_rank_1.bin": b"rank_1_weights_and_optimizer_state_67890",
        }

        # Save checkpoint step 100
        saved_dir = manager.save_checkpoint(
            step=100,
            epoch=1,
            tokens_seen=500_000,
            loss=2.85,
            shard_payloads=shards,
        )

        assert saved_dir.exists()
        manifest_file = saved_dir / "checkpoint_manifest.json"
        assert manifest_file.exists()

        # Verify integrity
        is_valid, errors = manager.verify_checkpoint(saved_dir)
        assert is_valid is True
        assert len(errors) == 0

        # Tamper with a shard to verify integrity failure
        tampered_shard = saved_dir / "shard_rank_0.bin"
        tampered_shard.write_bytes(b"corrupted_tampered_bytes")

        is_valid_after_tamper, tamper_errors = manager.verify_checkpoint(saved_dir)
        assert is_valid_after_tamper is False
        assert any("SHA-256 mismatch" in err for err in tamper_errors)


def test_checkpoint_retention_and_milestones() -> None:
    """Verify retention policy rotates non-milestone checkpoints while preserving milestones."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = DistributedCheckpointManager(
            checkpoint_dir=tmp_dir,
            max_to_keep=2,
            milestone_interval_steps=500,
        )

        dummy_shards = {"model.bin": b"weights"}

        # Step 100 (regular)
        manager.save_checkpoint(step=100, epoch=1, tokens_seen=1000, loss=3.0, shard_payloads=dummy_shards)
        # Step 200 (regular)
        manager.save_checkpoint(step=200, epoch=1, tokens_seen=2000, loss=2.9, shard_payloads=dummy_shards)
        # Step 500 (milestone due to interval)
        manager.save_checkpoint(step=500, epoch=1, tokens_seen=5000, loss=2.5, shard_payloads=dummy_shards)
        # Step 600 (regular)
        manager.save_checkpoint(step=600, epoch=1, tokens_seen=6000, loss=2.4, shard_payloads=dummy_shards)
        # Step 700 (regular)
        manager.save_checkpoint(step=700, epoch=1, tokens_seen=7000, loss=2.3, shard_payloads=dummy_shards)

        all_checkpoints = [p.name for p in Path(tmp_dir).iterdir() if p.is_dir() and p.name.startswith("checkpoint_step_")]

        # Milestone step 500 MUST be preserved even though max_to_keep=2
        assert "checkpoint_step_00000500" in all_checkpoints
        # The latest regular checkpoints (600, 700) should exist
        assert "checkpoint_step_00000700" in all_checkpoints
        # The oldest regular checkpoint (100) should have been pruned
        assert "checkpoint_step_00000100" not in all_checkpoints
