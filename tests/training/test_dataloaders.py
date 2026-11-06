"""
404 FOUNDERS — Unit Tests for Data Loaders & Batch Preparation
"""

import torch

from training.dataloaders.data_loader import (
    FoundationDataLoader,
    SyntheticDatasetGenerator,
    TokenizedSequenceDataset,
)


def test_tokenized_sequence_dataset_padding_and_truncation() -> None:
    """Verify sequence truncation and padding with attention masks."""
    sequences = [
        [1, 2, 3],                  # needs padding (pad_token_id=0)
        [10, 20, 30, 40, 50, 60],   # needs truncation to max_seq_len=4
    ]
    ds = TokenizedSequenceDataset(sequences, max_seq_len=4, pad_token_id=0)
    assert len(ds) == 2

    # Sample 0: [1, 2, 3, 0]
    s0 = ds[0]
    assert s0["input_ids"].tolist() == [1, 2, 3, 0]
    assert s0["attention_mask"].tolist() == [1.0, 1.0, 1.0, 0.0]

    # Sample 1: [10, 20, 30, 40]
    s1 = ds[1]
    assert s1["input_ids"].tolist() == [10, 20, 30, 40]
    assert s1["attention_mask"].tolist() == [1.0, 1.0, 1.0, 1.0]


def test_synthetic_dataset_generator() -> None:
    """Verify deterministic repetitive n-gram pattern generation."""
    patterns1 = SyntheticDatasetGenerator.generate_repetitive_patterns(
        num_samples=4,
        seq_len=16,
        pattern_len=4,
        seed=404,
    )
    patterns2 = SyntheticDatasetGenerator.generate_repetitive_patterns(
        num_samples=4,
        seq_len=16,
        pattern_len=4,
        seed=404,
    )
    assert patterns1 == patterns2
    assert len(patterns1) == 4
    assert len(patterns1[0]) == 16

    # Verify periodicity: token at index i equals token at index i + 4
    for seq in patterns1:
        assert seq[0] == seq[4] == seq[8] == seq[12]
        assert seq[1] == seq[5] == seq[9] == seq[13]


def test_foundation_dataloader_batching() -> None:
    """Verify batch collation and generator reproducibility."""
    loader = FoundationDataLoader.create_synthetic_loader(
        num_samples=8,
        batch_size=2,
        seq_len=12,
        seed=404,
        shuffle=False,
    )
    batches = list(loader)
    assert len(batches) == 4
    for b in batches:
        assert b["input_ids"].shape == (2, 12)
        assert b["attention_mask"].shape == (2, 12)
        assert b["labels"].shape == (2, 12)
