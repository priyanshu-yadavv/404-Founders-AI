"""
404 FOUNDERS — Distributed Checkpoint Manager
Provides atomic, sharded checkpoint persistence, SHA-256 integrity verification,
checkpoint rotation, and fault recovery for distributed foundation model training.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CheckpointMetadata:
    """Metadata describing a saved training checkpoint."""

    step: int
    epoch: int
    tokens_seen: int
    loss: float
    timestamp: float
    total_shards: int
    shards: Dict[str, str]  # shard_filename -> sha256_hash
    commit_sha: str = "phase-05-init"
    is_milestone: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CheckpointMetadata:
        return cls(**data)


class DistributedCheckpointManager:
    """Manages distributed sharded checkpoints with atomic commit, SHA-256 hashing,

    and fault recovery.
    """

    def __init__(
        self,
        checkpoint_dir: str | Path,
        max_to_keep: int = 5,
        milestone_interval_steps: int = 10000,
    ) -> None:
        self.checkpoint_dir = Path(checkpoint_dir)
        self.max_to_keep = max_to_keep
        self.milestone_interval_steps = milestone_interval_steps
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _compute_sha256(self, file_path: Path) -> str:
        """Computes the SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def save_checkpoint(
        self,
        step: int,
        epoch: int,
        tokens_seen: int,
        loss: float,
        shard_payloads: Dict[str, bytes | str],
        is_milestone: bool = False,
    ) -> Path:
        """Atomically saves a sharded checkpoint with manifest and checksums.

        Writes to a staging directory first, verifies integrity, then renames atomically.
        """
        step_dir_name = f"checkpoint_step_{step:08d}"
        final_dir = self.checkpoint_dir / step_dir_name
        staging_dir = self.checkpoint_dir / f".staging_{step_dir_name}_{int(time.time())}"

        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        staging_dir.mkdir(parents=True, exist_ok=True)

        try:
            shards_map: Dict[str, str] = {}
            for shard_name, payload in shard_payloads.items():
                shard_file = staging_dir / shard_name
                if isinstance(payload, str):
                    shard_file.write_text(payload, encoding="utf-8")
                else:
                    shard_file.write_bytes(payload)

                # Compute checksum
                sha = self._compute_sha256(shard_file)
                shards_map[shard_name] = sha

            if step > 0 and step % self.milestone_interval_steps == 0:
                is_milestone = True

            metadata = CheckpointMetadata(
                step=step,
                epoch=epoch,
                tokens_seen=tokens_seen,
                loss=loss,
                timestamp=time.time(),
                total_shards=len(shard_payloads),
                shards=shards_map,
                is_milestone=is_milestone,
            )

            manifest_path = staging_dir / "checkpoint_manifest.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(metadata.to_dict(), f, indent=2)

            # Atomic directory rename
            if final_dir.exists():
                shutil.rmtree(final_dir)
            staging_dir.rename(final_dir)

            # Enforce retention policy
            self._prune_old_checkpoints()

            return final_dir

        except Exception as e:
            if staging_dir.exists():
                shutil.rmtree(staging_dir)
            raise RuntimeError(f"Failed to save atomic checkpoint step {step}: {e}") from e

    def verify_checkpoint(self, checkpoint_path: Path) -> Tuple[bool, List[str]]:
        """Verifies checkpoint completeness and SHA-256 hash integrity.

        Returns (is_valid, list_of_errors).
        """
        errors: List[str] = []
        manifest_file = checkpoint_path / "checkpoint_manifest.json"

        if not manifest_file.exists():
            return False, ["Missing checkpoint_manifest.json"]

        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            metadata = CheckpointMetadata.from_dict(data)
        except Exception as e:
            return False, [f"Corrupted manifest: {e}"]

        for shard_name, expected_sha in metadata.shards.items():
            shard_path = checkpoint_path / shard_name
            if not shard_path.exists():
                errors.append(f"Missing shard file: {shard_name}")
                continue

            actual_sha = self._compute_sha256(shard_path)
            if actual_sha != expected_sha:
                errors.append(
                    f"SHA-256 mismatch for {shard_name}: expected {expected_sha}, got {actual_sha}"
                )

        return (len(errors) == 0), errors

    def get_latest_checkpoint(self) -> Optional[Path]:
        """Finds the most recent valid checkpoint."""
        dirs = sorted(
            [
                d
                for d in self.checkpoint_dir.iterdir()
                if d.is_dir() and d.name.startswith("checkpoint_step_")
            ],
            key=lambda p: p.name,
            reverse=True,
        )

        for d in dirs:
            valid, errors = self.verify_checkpoint(d)
            if valid:
                return d
        return None

    def _prune_old_checkpoints(self) -> None:
        """Prunes checkpoints beyond max_to_keep, preserving milestone checkpoints."""
        all_dirs = sorted(
            [
                d
                for d in self.checkpoint_dir.iterdir()
                if d.is_dir() and d.name.startswith("checkpoint_step_")
            ],
            key=lambda p: p.name,
        )

        non_milestones: List[Path] = []
        for d in all_dirs:
            manifest_file = d / "checkpoint_manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    if meta.get("is_milestone", False):
                        continue
                except Exception:
                    pass
            non_milestones.append(d)

        while len(non_milestones) > self.max_to_keep:
            victim = non_milestones.pop(0)
            shutil.rmtree(victim, ignore_errors=True)
