"""
404 FOUNDERS — Dataset Manifest
Generates, serializes, and cryptographically verifies immutable dataset manifests
with per-file SHA-256 checksums, domain distributions, and license metadata.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass
class ManifestFileEntry:
    """Metadata entry for an individual dataset file in the manifest."""

    split: str
    path: str
    sha256: str
    record_count: int
    size_bytes: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DatasetManifest:
    """Cryptographic manifest detailing dataset composition, provenance, and checksums."""

    name: str
    version: str = "1.0.0"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    license: str = "Apache-2.0"
    total_records: int = 0
    total_bytes: int = 0
    domain_distribution: Dict[str, int] = field(default_factory=dict)
    language_distribution: Dict[str, int] = field(default_factory=dict)
    files: List[ManifestFileEntry] = field(default_factory=list)
    pii_scan_clean: bool = True
    manifest_checksum: str = ""

    def add_file_entry(
        self,
        split: str,
        file_path: Union[str, Path],
        record_count: int,
    ) -> None:
        """Add a dataset split file to the manifest with its SHA-256 checksum."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Split file does not exist: {path}")

        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        sha = hasher.hexdigest()
        size = path.stat().st_size

        entry = ManifestFileEntry(
            split=split,
            path=str(path.name),
            sha256=sha,
            record_count=record_count,
            size_bytes=size,
        )
        self.files.append(entry)
        self.total_records += record_count
        self.total_bytes += size
        self._recompute_manifest_checksum()

    def _recompute_manifest_checksum(self) -> None:
        """Compute top-level SHA-256 checksum of manifest contents."""
        content = f"{self.name}:{self.version}:{self.total_records}:{self.total_bytes}:"
        for f in sorted(self.files, key=lambda x: x.path):
            content += f"{f.path}:{f.sha256}:"
        self.manifest_checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to serializable dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "created_at": self.created_at,
            "license": self.license,
            "total_records": self.total_records,
            "total_bytes": self.total_bytes,
            "domain_distribution": self.domain_distribution,
            "language_distribution": self.language_distribution,
            "files": [f.to_dict() for f in self.files],
            "pii_scan_clean": self.pii_scan_clean,
            "manifest_checksum": self.manifest_checksum,
        }

    def save(self, dest_path: Union[str, Path]) -> Path:
        """Save manifest to JSON file."""
        self._recompute_manifest_checksum()
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return dest

    @classmethod
    def load(cls, source_path: Union[str, Path]) -> DatasetManifest:
        """Load manifest from JSON file."""
        source = Path(source_path)
        with open(source, "r", encoding="utf-8") as f:
            data = json.load(f)

        files = [ManifestFileEntry(**item) for item in data.get("files", [])]
        return cls(
            name=data["name"],
            version=data.get("version", "1.0.0"),
            created_at=data.get("created_at", ""),
            license=data.get("license", "Apache-2.0"),
            total_records=data.get("total_records", 0),
            total_bytes=data.get("total_bytes", 0),
            domain_distribution=data.get("domain_distribution", {}),
            language_distribution=data.get("language_distribution", {}),
            files=files,
            pii_scan_clean=data.get("pii_scan_clean", True),
            manifest_checksum=data.get("manifest_checksum", ""),
        )

    def verify(self, base_dir: Union[str, Path]) -> Tuple[bool, List[str]]:
        """Verify that all files in manifest exist and their SHA-256 checksums match."""
        base = Path(base_dir)
        errors: List[str] = []

        for entry in self.files:
            file_path = base / entry.path
            if not file_path.is_file():
                errors.append(f"Missing file: {file_path}")
                continue

            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            actual_sha = hasher.hexdigest()

            if actual_sha != entry.sha256:
                errors.append(
                    f"Checksum mismatch for {entry.path}: expected {entry.sha256}, got {actual_sha}"
                )

            actual_size = file_path.stat().st_size
            if actual_size != entry.size_bytes:
                errors.append(
                    f"Size mismatch for {entry.path}: expected {entry.size_bytes}B, got {actual_size}B"
                )

        return len(errors) == 0, errors
