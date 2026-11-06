"""
404 FOUNDERS — Data Loaders & Batch Preparation
Provides reproducible tokenized sequence batching, padding, attention masking,
and synthetic dataset generators for preflight and smoke verification.
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Sequence, Union
import json
import random
import torch
from torch.utils.data import DataLoader, Dataset


class TokenizedSequenceDataset(Dataset):
    """
    In-memory dataset of integer token sequences with padding and masking.
    """

    def __init__(
        self,
        sequences: List[List[int]],
        max_seq_len: int = 256,
        pad_token_id: int = 0,
    ) -> None:
        self.sequences = sequences
        self.max_seq_len = max_seq_len
        self.pad_token_id = pad_token_id

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        raw_tokens = self.sequences[idx]

        # Truncate or pad to max_seq_len
        if len(raw_tokens) > self.max_seq_len:
            tokens = raw_tokens[:self.max_seq_len]
            mask = [1.0] * self.max_seq_len
        else:
            pad_len = self.max_seq_len - len(raw_tokens)
            tokens = raw_tokens + [self.pad_token_id] * pad_len
            mask = [1.0] * len(raw_tokens) + [0.0] * pad_len

        input_ids = torch.tensor(tokens, dtype=torch.long)
        attention_mask = torch.tensor(mask, dtype=torch.float32)

        # For standard autoregressive prediction, labels mirror input_ids
        # (shifting is handled cleanly in AutoregressiveLossEngine)
        labels = torch.tensor(tokens, dtype=torch.long)

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


class SyntheticDatasetGenerator:
    """
    Generates deterministic, patterned synthetic datasets for unit testing,
    preflight forward/backward validation, and controlled toy overfitting experiments.
    """

    @staticmethod
    def generate_repetitive_patterns(
        num_samples: int = 16,
        seq_len: int = 32,
        vocab_size: int = 512,
        pattern_len: int = 4,
        seed: int = 404,
    ) -> List[List[int]]:
        """
        Generate sequences containing repeating n-grams.
        e.g. [A, B, C, D, A, B, C, D, A, B, ...]
        A model with autoregressive capacity can easily memorize these patterns
        and drive training loss down rapidly, proving training loop correctness.
        """
        rng = random.Random(seed)
        sequences: List[List[int]] = []

        # Reserve IDs [0..24] for special tokens; patterns use IDs >= 25
        min_token = min(25, vocab_size - 1)
        max_token = vocab_size - 1

        for _ in range(num_samples):
            # Select unique n-gram pattern
            pattern = [rng.randint(min_token, max_token) for _ in range(pattern_len)]
            seq: List[int] = []
            while len(seq) < seq_len:
                seq.extend(pattern)
            sequences.append(seq[:seq_len])

        return sequences

    @staticmethod
    def generate_arithmetic_counting(
        num_samples: int = 16,
        seq_len: int = 32,
        seed: int = 404,
    ) -> List[List[int]]:
        """
        Generate sequential counting sequences: [k, k+1, k+2, k+3, ...]
        """
        rng = random.Random(seed)
        sequences: List[List[int]] = []

        for _ in range(num_samples):
            start = rng.randint(30, 200)
            seq = [(start + i) for i in range(seq_len)]
            sequences.append(seq)

        return sequences


class FoundationDataLoader:
    """
    Builds reproducible PyTorch DataLoaders with deterministic seeding,
    batching, and optional in-memory synthetic fallbacks.
    """

    @staticmethod
    def create_synthetic_loader(
        num_samples: int = 32,
        batch_size: int = 4,
        seq_len: int = 32,
        vocab_size: int = 512,
        seed: int = 404,
        shuffle: bool = True,
    ) -> DataLoader:
        """Create a synthetic DataLoader for CPU smoke testing."""
        sequences = SyntheticDatasetGenerator.generate_repetitive_patterns(
            num_samples=num_samples,
            seq_len=seq_len,
            vocab_size=vocab_size,
            seed=seed,
        )
        dataset = TokenizedSequenceDataset(sequences, max_seq_len=seq_len)

        generator = torch.Generator()
        generator.manual_seed(seed)

        return DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            generator=generator,
            drop_last=False,
        )

    @staticmethod
    def create_from_sequences(
        sequences: List[List[int]],
        batch_size: int = 4,
        max_seq_len: int = 128,
        pad_token_id: int = 0,
        seed: int = 404,
        shuffle: bool = True,
    ) -> DataLoader:
        """Create DataLoader from raw token integer lists."""
        dataset = TokenizedSequenceDataset(
            sequences=sequences,
            max_seq_len=max_seq_len,
            pad_token_id=pad_token_id,
        )

        generator = torch.Generator()
        generator.manual_seed(seed)

        return DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            generator=generator,
            drop_last=False,
        )
