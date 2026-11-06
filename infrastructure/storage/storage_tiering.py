"""
404 FOUNDERS — Storage Tiering & Lifecycle Management
Defines Hot (NVMe scratch), Warm (Parallel Filesystem), and Cold (Object Storage)
data placement, tier transition rules, and quota management.
"""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class StorageTierType(str, Enum):
    """Storage tiers in the 404 FOUNDERS training infrastructure."""

    HOT_SCRATCH = "hot_nvme_scratch"
    WARM_PARALLEL = "warm_parallel_fs"
    COLD_OBJECT = "cold_object_storage"


@dataclass
class TierPolicy:
    """Policy rules for a storage tier."""

    tier_type: StorageTierType
    max_capacity_bytes: int
    eviction_threshold_percent: float = 85.0
    retention_days: int = 7
    allow_compression: bool = False
    min_read_throughput_gbps: float = 1.0


@dataclass
class StoredArtifact:
    """Represents a dataset, checkpoint, or log artifact across tiers."""

    artifact_id: str
    tier: StorageTierType
    path: str
    size_bytes: int
    created_at: float
    last_accessed: float
    is_locked: bool = False
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["tier"] = self.tier.value
        return res


class StorageTierManager:
    """Manages files across Hot, Warm, and Cold storage tiers, enforcing quotas and eviction."""

    def __init__(
        self,
        hot_dir: str | Path,
        warm_dir: str | Path,
        cold_dir: str | Path,
        hot_capacity_bytes: int = 500 * 1024**3,    # 500 GB default
        warm_capacity_bytes: int = 50 * 1024**4,   # 50 TB default
        cold_capacity_bytes: int = 500 * 1024**4,  # 500 TB default
    ) -> None:
        self.hot_dir = Path(hot_dir)
        self.warm_dir = Path(warm_dir)
        self.cold_dir = Path(cold_dir)

        for d in (self.hot_dir, self.warm_dir, self.cold_dir):
            d.mkdir(parents=True, exist_ok=True)

        self.policies = {
            StorageTierType.HOT_SCRATCH: TierPolicy(
                tier_type=StorageTierType.HOT_SCRATCH,
                max_capacity_bytes=hot_capacity_bytes,
                eviction_threshold_percent=80.0,
                retention_days=1,
                allow_compression=False,
                min_read_throughput_gbps=6.0,
            ),
            StorageTierType.WARM_PARALLEL: TierPolicy(
                tier_type=StorageTierType.WARM_PARALLEL,
                max_capacity_bytes=warm_capacity_bytes,
                eviction_threshold_percent=90.0,
                retention_days=30,
                allow_compression=True,
                min_read_throughput_gbps=100.0,
            ),
            StorageTierType.COLD_OBJECT: TierPolicy(
                tier_type=StorageTierType.COLD_OBJECT,
                max_capacity_bytes=cold_capacity_bytes,
                eviction_threshold_percent=95.0,
                retention_days=365,
                allow_compression=True,
                min_read_throughput_gbps=0.5,
            ),
        }

        self.registry: Dict[str, StoredArtifact] = {}

    def get_tier_dir(self, tier: StorageTierType) -> Path:
        if tier == StorageTierType.HOT_SCRATCH:
            return self.hot_dir
        if tier == StorageTierType.WARM_PARALLEL:
            return self.warm_dir
        return self.cold_dir

    def register_artifact(
        self,
        artifact_id: str,
        tier: StorageTierType,
        relative_path: str,
        size_bytes: int,
        is_locked: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StoredArtifact:
        """Registers a managed artifact in the storage registry."""
        full_path = self.get_tier_dir(tier) / relative_path
        artifact = StoredArtifact(
            artifact_id=artifact_id,
            tier=tier,
            path=str(full_path),
            size_bytes=size_bytes,
            created_at=time.time(),
            last_accessed=time.time(),
            is_locked=is_locked,
            metadata=metadata or {},
        )
        self.registry[artifact_id] = artifact
        return artifact

    def get_tier_usage(self, tier: StorageTierType) -> Dict[str, Any]:
        """Calculates current tier usage and capacity limits."""
        tier_artifacts = [a for a in self.registry.values() if a.tier == tier]
        used_bytes = sum(a.size_bytes for a in tier_artifacts)
        max_bytes = self.policies[tier].max_capacity_bytes
        utilization_pct = (used_bytes / max_bytes * 100.0) if max_bytes > 0 else 0.0

        return {
            "tier": tier.value,
            "used_bytes": used_bytes,
            "max_capacity_bytes": max_bytes,
            "utilization_percent": round(utilization_pct, 2),
            "artifact_count": len(tier_artifacts),
        }

    def promote_to_hot(self, artifact_id: str) -> StoredArtifact:
        """Promotes an artifact from warm/cold to hot scratch for active training access."""
        artifact = self.registry.get(artifact_id)
        if not artifact:
            raise KeyError(f"Artifact {artifact_id} not found")

        if artifact.tier == StorageTierType.HOT_SCRATCH:
            artifact.last_accessed = time.time()
            return artifact

        src_path = Path(artifact.path)
        dest_path = self.hot_dir / src_path.name

        if src_path.is_file():
            shutil.copy2(src_path, dest_path)
        elif src_path.is_dir():
            if dest_path.exists():
                shutil.rmtree(dest_path)
            shutil.copytree(src_path, dest_path)

        artifact.tier = StorageTierType.HOT_SCRATCH
        artifact.path = str(dest_path)
        artifact.last_accessed = time.time()
        return artifact

    def demote_to_cold(self, artifact_id: str) -> StoredArtifact:
        """Demotes an inactive artifact to cold archive storage."""
        artifact = self.registry.get(artifact_id)
        if not artifact:
            raise KeyError(f"Artifact {artifact_id} not found")

        if artifact.tier == StorageTierType.COLD_OBJECT:
            return artifact

        src_path = Path(artifact.path)
        dest_path = self.cold_dir / src_path.name

        if src_path.is_file():
            shutil.copy2(src_path, dest_path)
            src_path.unlink()
        elif src_path.is_dir():
            if dest_path.exists():
                shutil.rmtree(dest_path)
            shutil.copytree(src_path, dest_path)
            shutil.rmtree(src_path)

        artifact.tier = StorageTierType.COLD_OBJECT
        artifact.path = str(dest_path)
        artifact.last_accessed = time.time()
        return artifact

    def evict_hot_cache(self, target_free_bytes: int) -> List[str]:
        """Evicts least recently accessed unlocked artifacts from hot scratch."""
        hot_artifacts = [
            a for a in self.registry.values()
            if a.tier == StorageTierType.HOT_SCRATCH and not a.is_locked
        ]
        hot_artifacts.sort(key=lambda a: a.last_accessed)

        freed_bytes = 0
        evicted_ids: List[str] = []

        for art in hot_artifacts:
            if freed_bytes >= target_free_bytes:
                break
            p = Path(art.path)
            if p.is_file():
                p.unlink(missing_ok=True)
            elif p.is_dir():
                shutil.rmtree(p, ignore_errors=True)

            art.tier = StorageTierType.WARM_PARALLEL  # fallback to warm tier reference
            freed_bytes += art.size_bytes
            evicted_ids.append(art.artifact_id)

        return evicted_ids
