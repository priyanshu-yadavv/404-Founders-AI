"""
404 FOUNDERS — Dataset Ingestion
Ingests multi-domain, multi-format datasets (JSONL, CSV, Plain Text, Code, JSON)
into structured, schema-validated DataRecords.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

# Approved Domain Constants
DOMAIN_GENERAL_TEXT = "general_text"
DOMAIN_CODE = "code"
DOMAIN_MATH = "mathematics"
DOMAIN_SCIENTIFIC = "scientific"
DOMAIN_CYBERSECURITY = "cybersecurity"
DOMAIN_MULTILINGUAL = "multilingual"
DOMAIN_INSTRUCTION = "instruction"
DOMAIN_SYNTHETIC = "synthetic"
DOMAIN_MULTIMODAL_METADATA = "multimodal_metadata"

ALL_DOMAINS = {
    DOMAIN_GENERAL_TEXT,
    DOMAIN_CODE,
    DOMAIN_MATH,
    DOMAIN_SCIENTIFIC,
    DOMAIN_CYBERSECURITY,
    DOMAIN_MULTILINGUAL,
    DOMAIN_INSTRUCTION,
    DOMAIN_SYNTHETIC,
    DOMAIN_MULTIMODAL_METADATA,
}


@dataclass
class DataRecord:
    """Standardized internal representation of an ingested dataset record."""

    id: str
    content: str
    domain: str = DOMAIN_GENERAL_TEXT
    language: str = "en"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    checksum: str = ""

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        if self.domain not in ALL_DOMAINS:
            self.domain = DOMAIN_GENERAL_TEXT

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DataRecord:
        """Create record from dictionary."""
        return cls(
            id=str(data.get("id", "")),
            content=str(data.get("content", "")),
            domain=data.get("domain", DOMAIN_GENERAL_TEXT),
            language=data.get("language", "en"),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            checksum=data.get("checksum", ""),
        )


class DatasetIngestor:
    """Ingests records from various file formats into standardized DataRecord streams."""

    @staticmethod
    def ingest_jsonl(
        file_path: Union[str, Path],
        domain: str = DOMAIN_GENERAL_TEXT,
        default_lang: str = "en",
    ) -> Iterator[DataRecord]:
        """Ingest JSON Lines (.jsonl) file."""
        path = Path(file_path)
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    rec_id = str(obj.get("id", f"{path.stem}_{idx}"))
                    content = str(obj.get("content", obj.get("text", "")))
                    lang = str(obj.get("language", default_lang))
                    meta = obj.get("metadata", {})
                    yield DataRecord(
                        id=rec_id,
                        content=content,
                        domain=domain,
                        language=lang,
                        metadata=meta,
                    )
                except json.JSONDecodeError:
                    continue

    @staticmethod
    def ingest_csv(
        file_path: Union[str, Path],
        content_column: str = "content",
        id_column: Optional[str] = "id",
        domain: str = DOMAIN_GENERAL_TEXT,
        default_lang: str = "en",
    ) -> Iterator[DataRecord]:
        """Ingest CSV file."""
        path = Path(file_path)
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                content = row.get(content_column, "")
                if not content:
                    continue
                rec_id = row.get(id_column, f"{path.stem}_{idx}") if id_column else f"{path.stem}_{idx}"
                yield DataRecord(
                    id=str(rec_id),
                    content=content,
                    domain=domain,
                    language=row.get("language", default_lang),
                    metadata={k: v for k, v in row.items() if k not in (content_column, id_column)},
                )

    @staticmethod
    def ingest_plain_text(
        file_path: Union[str, Path],
        domain: str = DOMAIN_GENERAL_TEXT,
        default_lang: str = "en",
    ) -> DataRecord:
        """Ingest an entire single text or code file as a DataRecord."""
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        return DataRecord(
            id=path.name,
            content=content,
            domain=domain,
            language=default_lang,
            metadata={"filename": path.name, "size_bytes": len(content.encode("utf-8"))},
        )
