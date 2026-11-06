"""
404 FOUNDERS — Deduplicator
Exact duplicate removal (SHA-256) and near-duplicate detection via MinHash
and Jaccard similarity estimation.
"""

from __future__ import annotations

import hashlib
from typing import Dict, Iterable, Iterator, List, Optional, Set, Tuple

from training.datasets.ingestion.dataset_ingestor import DataRecord


class Deduplicator:
    """Detects and filters exact duplicates and near-duplicates in dataset streams."""

    def __init__(
        self,
        near_duplicate_threshold: float = 0.85,
        num_permutations: int = 32,
        shingle_k: int = 5,
        enable_near_dedup: bool = True,
    ) -> None:
        self.near_duplicate_threshold = near_duplicate_threshold
        self.num_permutations = num_permutations
        self.shingle_k = shingle_k
        self.enable_near_dedup = enable_near_dedup

        self._seen_exact_hashes: Set[str] = set()
        self._seen_signatures: List[Tuple[str, List[int]]] = []

        self.exact_duplicates_count: int = 0
        self.near_duplicates_count: int = 0
        self.unique_count: int = 0

    def _compute_minhash(self, text: str) -> List[int]:
        """Compute MinHash signature vector for a text sample."""
        if len(text) < self.shingle_k:
            shingles = {text}
        else:
            shingles = {text[i : i + self.shingle_k] for i in range(len(text) - self.shingle_k + 1)}

        signature: List[int] = []
        for seed in range(self.num_permutations):
            min_val = 0xFFFFFFFF
            prefix = f"{seed}:".encode("ascii")
            for shingle in shingles:
                # Fast 32-bit hash derivation from MD5
                h = int(hashlib.md5(prefix + shingle.encode("utf-8")).hexdigest()[:8], 16)
                if h < min_val:
                    min_val = h
            signature.append(min_val)
        return signature

    @staticmethod
    def estimate_jaccard(sig_a: List[int], sig_b: List[int]) -> float:
        """Estimate Jaccard similarity between two MinHash signatures."""
        if not sig_a or not sig_b or len(sig_a) != len(sig_b):
            return 0.0
        matches = sum(1 for a, b in zip(sig_a, sig_b) if a == b)
        return matches / len(sig_a)

    def is_duplicate(self, record: DataRecord) -> bool:
        """Check whether a record is an exact duplicate or near-duplicate.

        If duplicate, increments corresponding counter and returns True.
        Otherwise records signature, increments unique_count, and returns False.
        """
        exact_hash = record.checksum or hashlib.sha256(record.content.encode("utf-8")).hexdigest()
        if exact_hash in self._seen_exact_hashes:
            self.exact_duplicates_count += 1
            return True

        if self.enable_near_dedup:
            sig = self._compute_minhash(record.content)
            for _, prev_sig in self._seen_signatures:
                sim = self.estimate_jaccard(sig, prev_sig)
                if sim >= self.near_duplicate_threshold:
                    self.near_duplicates_count += 1
                    return True
            self._seen_signatures.append((record.id, sig))

        self._seen_exact_hashes.add(exact_hash)
        self.unique_count += 1
        return False

    def deduplicate(self, records: Iterable[DataRecord]) -> Iterator[DataRecord]:
        """Filter a stream of records, yielding only unique records."""
        for rec in records:
            if not self.is_duplicate(rec):
                yield rec

    def reset(self) -> None:
        """Reset internal deduplication state."""
        self._seen_exact_hashes.clear()
        self._seen_signatures.clear()
        self.exact_duplicates_count = 0
        self.near_duplicates_count = 0
        self.unique_count = 0
