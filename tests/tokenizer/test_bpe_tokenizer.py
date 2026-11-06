"""
404 FOUNDERS — Unit Tests: Custom BPE Tokenizer Core
Covers BPE merge correctness, vocabulary construction, roundtrips, special tokens,
unknown token handling, deterministic training, and serialization.
"""

import tempfile
from pathlib import Path
import pytest

from tokenizer import (
    CustomBPETokenizer,
    TokenizerConfig,
    SpecialTokenRegistry,
    Vocabulary,
)
from tokenizer.special_tokens import (
    PAD_TOKEN,
    UNK_TOKEN,
    BOS_TOKEN,
    EOS_TOKEN,
    SYS_START_TOKEN,
    SYS_END_TOKEN,
    USER_START_TOKEN,
    USER_END_TOKEN,
)


@pytest.fixture
def sample_corpus():
    return [
        "The quick brown fox jumps over the lazy dog.",
        "404 FOUNDERS is an enterprise AI assistant.",
        "Deep reasoning, math, and code intelligence without boundaries.",
        "The model must learn representations from scratch without pretrained weights.",
        "Quick brown foxes are jumping high.",
        "Hello, You are developing custom AI systems.",
    ]


def test_bpe_merge_correctness(sample_corpus):
    """Test 1: Verify that high-frequency character pairs are correctly merged into subwords."""
    config = TokenizerConfig(vocab_size=100, min_frequency=2)
    tokenizer = CustomBPETokenizer(config=config)
    tokenizer.train_from_iterator(sample_corpus)

    assert len(tokenizer.merges) > 0
    # Every merge rule must consist of two non-empty tokens
    for p0, p1 in tokenizer.merges:
        assert len(p0) > 0
        assert len(p1) > 0
        merged = p0 + p1
        assert tokenizer.vocabulary.contains(merged)

    # Priority ranks must be sequentially ordered from 0 to N-1
    assert len(tokenizer.merge_ranks) == len(tokenizer.merges)
    for idx, pair in enumerate(tokenizer.merges):
        assert tokenizer.merge_ranks[pair] == idx


def test_vocabulary_construction(sample_corpus):
    """Test 2: Verify special tokens and base characters are present in vocabulary."""
    config = TokenizerConfig(vocab_size=120, min_frequency=1)
    tokenizer = CustomBPETokenizer(config=config)
    tokenizer.train_from_iterator(sample_corpus)

    # Special tokens must occupy the lowest IDs (0 to 24)
    assert tokenizer.vocabulary.token_to_id(PAD_TOKEN) == 0
    assert tokenizer.vocabulary.token_to_id(UNK_TOKEN) == 1
    assert tokenizer.vocabulary.token_to_id(BOS_TOKEN) == 2
    assert tokenizer.vocabulary.token_to_id(EOS_TOKEN) == 3

    # All characters in corpus must be in vocabulary
    for doc in sample_corpus:
        for char in doc:
            if char != " ":
                assert tokenizer.vocabulary.contains(char), f"Missing base char: {char}"

    assert tokenizer.vocab_size <= config.vocab_size


def test_encoding_decoding_round_trip(sample_corpus):
    """Test 3: Verify exact string reconstruction after encode -> decode."""
    config = TokenizerConfig(vocab_size=150, min_frequency=1)
    tokenizer = CustomBPETokenizer(config=config)
    tokenizer.train_from_iterator(sample_corpus)

    for text in sample_corpus:
        encoded = tokenizer.encode(text)
        assert len(encoded.ids) > 0
        assert len(encoded.tokens) == len(encoded.ids)

        decoded = tokenizer.decode(encoded.ids, skip_special_tokens=True)
        assert decoded == text, f"Mismatch: expected '{text}', got '{decoded}'"


def test_special_token_handling(sample_corpus):
    """Test 4: Verify special tokens are matched atomically and omitted or preserved properly."""
    config = TokenizerConfig(vocab_size=120, min_frequency=1)
    tokenizer = CustomBPETokenizer(config=config)
    tokenizer.train_from_iterator(sample_corpus)

    prompt = f"{SYS_START_TOKEN}You are 404 FOUNDERS.{SYS_END_TOKEN}\n{USER_START_TOKEN}Hello{USER_END_TOKEN}"
    encoded = tokenizer.encode(prompt, add_bos=True, add_eos=True)

    # Verify BOS at index 0 and EOS at the end
    assert encoded.ids[0] == tokenizer.bos_token_id
    assert encoded.ids[-1] == tokenizer.eos_token_id

    # Verify special tokens are in the token sequence as atomic entities
    assert SYS_START_TOKEN in encoded.tokens
    assert SYS_END_TOKEN in encoded.tokens
    assert USER_START_TOKEN in encoded.tokens
    assert USER_END_TOKEN in encoded.tokens

    # Decoding with skip_special_tokens=True must strip them
    decoded_clean = tokenizer.decode(encoded.ids, skip_special_tokens=True)
    assert SYS_START_TOKEN not in decoded_clean
    assert USER_START_TOKEN not in decoded_clean
    assert "You are 404 FOUNDERS." in decoded_clean

    # Decoding with skip_special_tokens=False must preserve them
    decoded_raw = tokenizer.decode(encoded.ids, skip_special_tokens=False)
    assert SYS_START_TOKEN in decoded_raw
    assert USER_START_TOKEN in decoded_raw


def test_unknown_token_behavior(sample_corpus):
    """Test 5: Verify that characters never seen in training fall back to UNK token."""
    config = TokenizerConfig(vocab_size=80, min_frequency=2)
    tokenizer = CustomBPETokenizer(config=config)
    tokenizer.train_from_iterator(sample_corpus)

    # Text containing unobserved emoji and math symbol
    unseen_text = "The quick brown fox 🚀 ∮"
    encoded = tokenizer.encode(unseen_text)

    # UNK ID is 1
    assert tokenizer.unk_token_id in encoded.ids
    assert UNK_TOKEN in encoded.tokens


def test_deterministic_training(sample_corpus):
    """Test 6: Verify training is 100% deterministic given identical corpus."""
    config = TokenizerConfig(vocab_size=120, min_frequency=1)
    tok1 = CustomBPETokenizer(config=config).train_from_iterator(sample_corpus)
    tok2 = CustomBPETokenizer(config=config).train_from_iterator(sample_corpus)

    assert tok1.merges == tok2.merges
    assert tok1.get_vocab() == tok2.get_vocab()

    enc1 = tok1.encode("The quick brown fox jumps over.")
    enc2 = tok2.encode("The quick brown fox jumps over.")
    assert enc1.ids == enc2.ids


def test_vocabulary_serialization(sample_corpus):
    """Test 7: Verify saving and loading tokenizer JSON preserves all functionality."""
    config = TokenizerConfig(vocab_size=120, min_frequency=1)
    tokenizer = CustomBPETokenizer(config=config)
    tokenizer.train_from_iterator(sample_corpus)

    with tempfile.TemporaryDirectory() as tmp_dir:
        model_path = Path(tmp_dir) / "test_tokenizer.json"
        saved = tokenizer.save(model_path)
        assert saved.is_file()

        loaded_tok = CustomBPETokenizer.load(model_path)
        assert loaded_tok.vocab_size == tokenizer.vocab_size
        assert loaded_tok.merges == tokenizer.merges
        assert loaded_tok.get_vocab() == tokenizer.get_vocab()

        test_str = "Deep reasoning from scratch."
        assert tokenizer.encode(test_str).ids == loaded_tok.encode(test_str).ids


def test_invalid_input_handling(sample_corpus):
    """Test 8: Verify robust handling of empty text, None, and invalid parameters."""
    with pytest.raises(ValueError):
        TokenizerConfig(vocab_size=10)  # Min is 32

    with pytest.raises(ValueError):
        TokenizerConfig(min_frequency=0)

    tokenizer = CustomBPETokenizer(TokenizerConfig(vocab_size=50))
    tokenizer.train_from_iterator(sample_corpus)

    # Empty string handling
    empty_enc = tokenizer.encode("")
    assert empty_enc.ids == []
    assert empty_enc.tokens == []
    assert tokenizer.decode([]) == ""

    # None handling
    none_enc = tokenizer.encode(None)
    assert none_enc.ids == []
    assert none_enc.tokens == []
