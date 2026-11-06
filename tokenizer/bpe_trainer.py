"""
404 FOUNDERS — Custom BPE Trainer
Trains an independent character-level Byte-Pair Encoding (BPE) model from scratch
using configurable target vocabulary size, min-frequency cutoffs, and deterministic tie-breaking.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List, Optional, Set, Tuple

from tokenizer.config import TokenizerConfig
from tokenizer.normalization import TextNormalizer
from tokenizer.pre_tokenizer import PreTokenizer
from tokenizer.special_tokens import SpecialTokenRegistry
from tokenizer.vocabulary import Vocabulary


class BPETrainer:
    """Trainer implementing custom character-based Byte Pair Encoding."""

    def __init__(
        self,
        config: Optional[TokenizerConfig] = None,
        special_tokens: Optional[SpecialTokenRegistry] = None,
    ) -> None:
        self.config = config if config is not None else TokenizerConfig()
        self.special_tokens = (
            special_tokens if special_tokens is not None else SpecialTokenRegistry()
        )
        self.normalizer = TextNormalizer(mode=self.config.normalization)
        self.pre_tokenizer = PreTokenizer(whitespace_symbol=self.config.whitespace_symbol)

    def train(
        self,
        corpus: Iterable[str],
    ) -> Tuple[Vocabulary, List[Tuple[str, str]], Dict[Tuple[str, str], int]]:
        """Train BPE merge rules and construct vocabulary from input text corpus.

        Args:
            corpus: Iterable of text documents/lines.

        Returns:
            Tuple of:
                - Vocabulary containing special tokens, base characters, and learned merges.
                - Ordered list of merge rules (pair_a, pair_b).
                - Dictionary mapping merge pair tuple to its priority rank index.
        """
        # Step 1: Normalize and pre-tokenize corpus to collect word frequencies
        word_freqs: Dict[Tuple[str, ...], int] = Counter()
        base_chars: Set[str] = set()

        for doc in corpus:
            if not doc:
                continue
            normalized = self.normalizer.normalize(doc)
            segments = self.pre_tokenizer.pre_tokenize(normalized, special_tokens=self.special_tokens)

            for chunk, is_special in segments:
                if is_special:
                    continue  # Special tokens are handled via registry
                if not chunk:
                    continue
                char_tuple = self.pre_tokenizer.split_to_characters(chunk)
                word_freqs[char_tuple] += 1
                for ch in char_tuple:
                    base_chars.add(ch)

        # Step 2: Initialize Vocabulary with Special Tokens and Base Characters
        vocab = Vocabulary(
            special_tokens=self.special_tokens,
            unknown_token=self.config.unknown_token,
            pad_token=self.config.pad_token,
        )

        # Add base characters observed in corpus in deterministic order (sorted by code point)
        for ch in sorted(base_chars):
            vocab.add_token(ch)

        # Step 3: Iteratively identify most frequent pairs and generate merge rules
        merges: List[Tuple[str, str]] = []
        merge_ranks: Dict[Tuple[str, str], int] = {}

        target_merges = self.config.vocab_size - len(vocab)
        if target_merges <= 0:
            return vocab, merges, merge_ranks

        for rank in range(target_merges):
            pair_freqs: Dict[Tuple[str, str], int] = Counter()
            for word_tuple, count in word_freqs.items():
                w_len = len(word_tuple)
                if w_len < 2:
                    continue
                for i in range(w_len - 1):
                    pair_freqs[(word_tuple[i], word_tuple[i + 1])] += count

            if not pair_freqs:
                break

            # Find pair with maximum frequency (deterministic tie-breaking)
            best_pair, best_freq = max(
                pair_freqs.items(),
                key=lambda item: (item[1], item[0][0], item[0][1]),
            )

            if best_freq < self.config.min_frequency:
                break

            new_token = best_pair[0] + best_pair[1]
            merges.append(best_pair)
            merge_ranks[best_pair] = rank
            vocab.add_token(new_token)

            # Update word frequencies by merging best_pair in all words
            new_word_freqs: Dict[Tuple[str, ...], int] = {}
            p0, p1 = best_pair

            for word_tuple, count in word_freqs.items():
                w_len = len(word_tuple)
                if w_len < 2:
                    new_word_freqs[word_tuple] = count
                    continue

                new_word: List[str] = []
                i = 0
                while i < w_len:
                    if i < w_len - 1 and word_tuple[i] == p0 and word_tuple[i + 1] == p1:
                        new_word.append(new_token)
                        i += 2
                    else:
                        new_word.append(word_tuple[i])
                        i += 1
                new_word_freqs[tuple(new_word)] = count

            word_freqs = new_word_freqs

        return vocab, merges, merge_ranks
