"""
404 FOUNDERS — Dataset Splitter
Deterministic, zero-leakage dataset partitioning into Train, Validation, and Test sets
using content hashing and reproducible seeded sampling.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from training.datasets.ingestion.dataset_ingestor import DataRecord


@dataclass
class SplitResult:
    """Container for partitioned dataset splits."""

    train: List[DataRecord]
    val: List[DataRecord]
    test: List[DataRecord]

    @property
    def total_count(self) -> int:
        return len(self.train) + len(self.val) + len(self.test)

    def counts(self) -> Dict[str, int]:
        return {
            "train": len(self.train),
            "val": len(self.val),
            "test": len(self.test),
            "total": self.total_count,
        }


class DatasetSplitter:
    """Partitions datasets into train, val, and test splits with zero data leakage."""

    def __init__(
        self,
        train_ratio: float = 0.80,
        val_ratio: float = 0.10,
        test_ratio: float = 0.10,
        random_seed: int = 404,
    ) -> None:
        total = round(train_ratio + val_ratio + test_ratio, 4)
        if total != 1.0:
            raise ValueError(
                f"Split ratios must sum to 1.0, got {train_ratio} + {val_ratio} + {test_ratio} = {total}"
            )
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_seed = random_seed

    def split_by_hash(self, records: Iterable[DataRecord]) -> SplitResult:
        """Partition records deterministically using content SHA-256 hashes.

        Guarantees:
        1. Zero data leakage: identical text content is guaranteed to land in the same split.
        2. Order-independent reproducibility across distributed workers.
        """
        train_list: List[DataRecord] = []
        val_list: List[DataRecord] = []
        test_list: List[DataRecord] = []

        train_threshold = int(self.train_ratio * 1000)
        val_threshold = int((self.train_ratio + self.val_ratio) * 1000)

        for rec in records:
            # Deterministic bucket in [0, 999] derived from content checksum
            raw_hash = rec.checksum or hashlib.sha256(rec.content.encode("utf-8")).hexdigest()
            bucket = int(raw_hash[:8], 16) % 1000

            if bucket < train_threshold:
                train_list.append(rec)
            elif bucket < val_threshold:
                val_list.append(rec)
            else:
                test_list.append(rec)

        return SplitResult(train=train_list, val=val_list, test=test_list)

    def split_random(self, records: List[DataRecord], shuffle: bool = True) -> SplitResult:
        """Partition records using reproducible random shuffling."""
        items = list(records)
        if shuffle:
            rng = random.Random(self.random_seed)
            rng.shuffle(items)

        n = len(items)
        n_train = int(n * self.train_ratio)
        n_val = int(n * self.val_ratio)

        train_part = items[:n_train]
        val_part = items[n_train : n_train + n_val]
        test_part = items[n_train + n_val :]

        return SplitResult(train=train_part, val=val_part, test=test_part)
