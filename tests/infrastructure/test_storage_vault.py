"""
404 FOUNDERS — Storage Tiering & Checkpoint Vault Tests
Validates Hot/Warm/Cold tier management, quota enforcement, LRU cache eviction,
and Checkpoint Vault immutability locks.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import pytest

from infrastructure.storage import (
    CheckpointVault,
    StorageTierManager,
    StorageTierType,
)


def test_storage_tier_registration_and_usage() -> None:
    """Verify artifacts are registered and tier usage metrics are computed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        p_root = Path(tmp_dir)
        mgr = StorageTierManager(
            hot_dir=p_root / "hot",
            warm_dir=p_root / "warm",
            cold_dir=p_root / "cold",
            hot_capacity_bytes=100 * 1024**2,  # 100 MB
        )

        # Create dummy file in hot tier
        hot_file = mgr.hot_dir / "batch_001.bin"
        hot_file.write_bytes(b"x" * (10 * 1024**2))  # 10 MB

        art = mgr.register_artifact(
            artifact_id="batch_001",
            tier=StorageTierType.HOT_SCRATCH,
            relative_path="batch_001.bin",
            size_bytes=10 * 1024**2,
        )

        assert art.artifact_id == "batch_001"
        assert art.tier == StorageTierType.HOT_SCRATCH

        usage = mgr.get_tier_usage(StorageTierType.HOT_SCRATCH)
        assert usage["used_bytes"] == 10 * 1024**2
        assert usage["utilization_percent"] == 10.0
        assert usage["artifact_count"] == 1


def test_tier_promotion_and_demotion() -> None:
    """Verify promoting warm artifacts to hot scratch and demoting to cold."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        p_root = Path(tmp_dir)
        mgr = StorageTierManager(
            hot_dir=p_root / "hot",
            warm_dir=p_root / "warm",
            cold_dir=p_root / "cold",
        )

        warm_file = mgr.warm_dir / "corpus_shard_0.bin"
        warm_file.write_bytes(b"token_stream_content")

        art = mgr.register_artifact(
            artifact_id="shard_0",
            tier=StorageTierType.WARM_PARALLEL,
            relative_path="corpus_shard_0.bin",
            size_bytes=len(b"token_stream_content"),
        )

        # Promote to Hot
        promoted = mgr.promote_to_hot("shard_0")
        assert promoted.tier == StorageTierType.HOT_SCRATCH
        assert Path(promoted.path).exists()
        assert Path(promoted.path).parent == mgr.hot_dir

        # Demote to Cold
        demoted = mgr.demote_to_cold("shard_0")
        assert demoted.tier == StorageTierType.COLD_OBJECT
        assert Path(demoted.path).exists()
        assert Path(demoted.path).parent == mgr.cold_dir


def test_hot_cache_lru_eviction() -> None:
    """Verify least recently accessed unlocked items are evicted from hot scratch."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        p_root = Path(tmp_dir)
        mgr = StorageTierManager(
            hot_dir=p_root / "hot",
            warm_dir=p_root / "warm",
            cold_dir=p_root / "cold",
        )

        # File 1: older access time, unlocked
        f1 = mgr.hot_dir / "old_batch.bin"
        f1.write_bytes(b"old")
        a1 = mgr.register_artifact("old_art", StorageTierType.HOT_SCRATCH, "old_batch.bin", 1000)
        a1.last_accessed = 100.0

        # File 2: locked item
        f2 = mgr.hot_dir / "locked_batch.bin"
        f2.write_bytes(b"locked")
        a2 = mgr.register_artifact("locked_art", StorageTierType.HOT_SCRATCH, "locked_batch.bin", 1000, is_locked=True)
        a2.last_accessed = 50.0  # Even older, but locked!

        # File 3: newer access time
        f3 = mgr.hot_dir / "new_batch.bin"
        f3.write_bytes(b"new")
        a3 = mgr.register_artifact("new_art", StorageTierType.HOT_SCRATCH, "new_batch.bin", 1000)
        a3.last_accessed = 200.0

        evicted = mgr.evict_hot_cache(target_free_bytes=500)
        assert "old_art" in evicted
        assert "locked_art" not in evicted  # Locked must not be evicted
        assert not f1.exists()
        assert f2.exists()


def test_checkpoint_vault_lifecycle_and_immutability() -> None:
    """Verify CheckpointVault deposits checkpoints, enforces immutability, and retrieves."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        p_root = Path(tmp_dir)
        vault = CheckpointVault(vault_dir=p_root / "vault")

        # Create valid checkpoint folder with manifest
        src_dir = p_root / "src_chkpt"
        src_dir.mkdir()
        (src_dir / "model.pt").write_bytes(b"weights")
        manifest_data = {
            "step": 5000,
            "epoch": 1,
            "loss": 2.45,
            "tokens_seen": 1000000,
            "shards": {"model.pt": "fake_sha"},
        }
        (src_dir / "checkpoint_manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

        # Deposit into vault with immutability
        record = vault.deposit_checkpoint(
            checkpoint_dir=src_dir,
            checkpoint_id="chkpt_5000",
            is_immutable=True,
        )

        assert record.checkpoint_id == "chkpt_5000"
        assert record.is_immutable is True
        assert record.step == 5000
        assert record.loss == 2.45

        # Re-depositing over an immutable checkpoint must raise PermissionError
        with pytest.raises(PermissionError, match="locked as immutable"):
            vault.deposit_checkpoint(src_dir, checkpoint_id="chkpt_5000")

        # Retrieval
        dest_dir = p_root / "retrieved_chkpt"
        vault.retrieve_checkpoint(checkpoint_id="chkpt_5000", destination_dir=dest_dir)
        assert (dest_dir / "model.pt").exists()
        assert (dest_dir / "checkpoint_manifest.json").exists()
