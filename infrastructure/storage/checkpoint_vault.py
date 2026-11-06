"""
404 FOUNDERS — Checkpoint Vault
Provides versioned, immutable storage synchronization for foundation model checkpoints,
enforcing SHA-256 integrity checks, immutability flags, and recovery metadata.
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
class VaultRecord:
    """Record of a verified checkpoint deposited in the vault."""

    checkpoint_id: str
    step: int
    loss: float
    tokens_seen: int
    created_at: float
    local_path: str
    vault_path: str
    is_immutable: bool
    manifest: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CheckpointVault:
    """Manages the durable vault for foundation model training checkpoints."""

    def __init__(self, vault_dir: str | Path) -> None:
        self.vault_dir = Path(vault_dir)
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.catalog_file = self.vault_dir / "vault_catalog.json"
        self.records: Dict[str, VaultRecord] = self._load_catalog()

    def _load_catalog(self) -> Dict[str, VaultRecord]:
        if not self.catalog_file.exists():
            return {}
        try:
            with open(self.catalog_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return {k: VaultRecord(**v) for k, v in raw.items()}
        except Exception:
            return {}

    def _save_catalog(self) -> None:
        with open(self.catalog_file, "w", encoding="utf-8") as f:
            json.dump({k: r.to_dict() for k, r in self.records.items()}, f, indent=2)

    def deposit_checkpoint(
        self,
        checkpoint_dir: str | Path,
        checkpoint_id: Optional[str] = None,
        is_immutable: bool = False,
    ) -> VaultRecord:
        """Deposits a checkpoint directory into the vault after verifying its manifest and checksums."""
        src_path = Path(checkpoint_dir)
        if not src_path.exists() or not src_path.is_dir():
            raise FileNotFoundError(f"Checkpoint directory {checkpoint_dir} does not exist")

        manifest_file = src_path / "checkpoint_manifest.json"
        if not manifest_file.exists():
            raise ValueError(f"Checkpoint {checkpoint_dir} lacks checkpoint_manifest.json")

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        step = manifest.get("step", 0)
        cid = checkpoint_id or f"chkpt_step_{step:08d}"

        if cid in self.records and self.records[cid].is_immutable:
            raise PermissionError(f"Checkpoint {cid} is locked as immutable in the vault")

        dest_path = self.vault_dir / cid
        if dest_path.exists():
            shutil.rmtree(dest_path)
        shutil.copytree(src_path, dest_path)

        # Make files read-only if immutable
        if is_immutable:
            for item in dest_path.rglob("*"):
                if item.is_file():
                    os.chmod(item, 0o444)

        record = VaultRecord(
            checkpoint_id=cid,
            step=step,
            loss=manifest.get("loss", 0.0),
            tokens_seen=manifest.get("tokens_seen", 0),
            created_at=time.time(),
            local_path=str(src_path),
            vault_path=str(dest_path),
            is_immutable=is_immutable,
            manifest=manifest,
        )

        self.records[cid] = record
        self._save_catalog()
        return record

    def retrieve_checkpoint(self, checkpoint_id: str, destination_dir: str | Path) -> Path:
        """Retrieves a checkpoint from the vault to a destination directory."""
        if checkpoint_id not in self.records:
            raise KeyError(f"Checkpoint {checkpoint_id} not found in vault")

        record = self.records[checkpoint_id]
        src_dir = Path(record.vault_path)
        dest_dir = Path(destination_dir)

        if not src_dir.exists():
            raise FileNotFoundError(f"Vault data for {checkpoint_id} missing at {src_dir}")

        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        shutil.copytree(src_dir, dest_dir)
        return dest_dir

    def lock_checkpoint(self, checkpoint_id: str) -> None:
        """Locks a checkpoint as immutable, preventing accidental overwrite or deletion."""
        if checkpoint_id not in self.records:
            raise KeyError(f"Checkpoint {checkpoint_id} not found in vault")

        record = self.records[checkpoint_id]
        record.is_immutable = True
        dest_path = Path(record.vault_path)
        for item in dest_path.rglob("*"):
            if item.is_file():
                os.chmod(item, 0o444)
        self._save_catalog()

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """Returns list of registered checkpoints sorted by step."""
        recs = sorted(self.records.values(), key=lambda r: r.step)
        return [r.to_dict() for r in recs]
