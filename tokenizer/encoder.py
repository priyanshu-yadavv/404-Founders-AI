"""
404 FOUNDERS — BPE Encoder
Applies trained BPE merge rules and special-token handling to encode raw text
into subword tokens and integer IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from tokenizer.config import TokenizerConfig
from tokenizer.normalization import TextNormalizer
from tokenizer.pre_tokenizer import PreTokenizer
from tokenizer.special_tokens import BOS_TOKEN, EOS_TOKEN, SpecialTokenRegistry
from tokenizer.vocabulary import Vocabulary


@dataclass
class EncodingResult:
    """Container for the output of tokenizer encoding."""

    tokens: List[str]
    ids: List[int]
    text: str

    def __len__(self) -> int:
        return len(self.ids)


class BPEEncoder:
    """Encodes text using learned BPE merge ranks and vocabulary mapping."""

    def __init__(
        self,
        vocabulary: Vocabulary,
        merge_ranks: Dict[Tuple[str, str], int],
        config: Optional[TokenizerConfig] = None,
        special_tokens: Optional[SpecialTokenRegistry] = None,
    ) -> None:
        self.vocabulary = vocabulary
        self.merge_ranks = merge_ranks
        self.config = config if config is not None else TokenizerConfig()
        self.special_tokens = (
            special_tokens if special_tokens is not None else SpecialTokenRegistry()
        )
        self.normalizer = TextNormalizer(mode=self.config.normalization)
        self.pre_tokenizer = PreTokenizer(whitespace_symbol=self.config.whitespace_symbol)

    def _bpe_segment_word(self, word_chars: Tuple[str, ...]) -> List[str]:
        """Apply BPE merge rules iteratively to a single word."""
        if len(word_chars) <= 1:
            return list(word_chars)

        word = word_chars
        while len(word) >= 2:
            # Find all candidate pairs in current word that exist in merge_ranks
            min_rank = float("inf")
            best_pair: Optional[Tuple[str, str]] = None

            for i in range(len(word) - 1):
                pair = (word[i], word[i + 1])
                rank = self.merge_ranks.get(pair)
                if rank is not None and rank < min_rank:
                    min_rank = rank
                    best_pair = pair

            if best_pair is None:
                # No more merges apply
                break

            # Apply the highest-priority merge
            p0, p1 = best_pair
            merged_token = p0 + p1
            new_word: List[str] = []
            i = 0
            w_len = len(word)
            while i < w_len:
                if i < w_len - 1 and word[i] == p0 and word[i + 1] == p1:
                    new_word.append(merged_token)
                    i += 2
                else:
                    new_word.append(word[i])
                    i += 1
            word = tuple(new_word)

        return list(word)

    def encode(
        self,
        text: Optional[str],
        add_bos: bool = False,
        add_eos: bool = False,
        allowed_special: Optional[Set[str]] = None,
    ) -> EncodingResult:
        """Encode text into subwords and IDs.

        Args:
            text: Input string to tokenize.
            add_bos: Whether to prepend the <bos> token.
            add_eos: Whether to append the <eos> token.
            allowed_special: Optional set of special tokens allowed. If None, all registered are allowed.

        Returns:
            EncodingResult with tokens, ids, and original text.
        """
        if text is None:
            text = ""

        tokens: List[str] = []
        ids: List[int] = []

        if add_bos:
            bos_id = self.vocabulary.token_to_id(self.config.bos_token)
            tokens.append(self.config.bos_token)
            ids.append(bos_id)

        if text:
            # Normalize text
            normalized = self.normalizer.normalize(text)

            # Special tokens registry filter if custom set is provided
            registry = self.special_tokens
            if allowed_special is not None:
                registry = SpecialTokenRegistry([t for t in self.special_tokens.all_tokens() if t in allowed_special])

            # Pre-tokenize text into special and non-special segments
            segments = self.pre_tokenizer.pre_tokenize(normalized, special_tokens=registry)

            for chunk, is_special in segments:
                if is_special:
                    tokens.append(chunk)
                    ids.append(self.vocabulary.token_to_id(chunk))
                else:
                    char_tuple = self.pre_tokenizer.split_to_characters(chunk)
                    subwords = self._bpe_segment_word(char_tuple)
                    for subword in subwords:
                        tok_id = self.vocabulary.token_to_id(subword)
                        if not self.vocabulary.contains(subword):
                            tokens.append(self.config.unknown_token)
                        else:
                            tokens.append(subword)
                        ids.append(tok_id)

        if add_eos:
            eos_id = self.vocabulary.token_to_id(self.config.eos_token)
            tokens.append(self.config.eos_token)
            ids.append(eos_id)

        return EncodingResult(tokens=tokens, ids=ids, text=text)
