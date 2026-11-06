"""
404 FOUNDERS — Custom BPE Tokenizer
Main tokenizer interface uniting training, encoding, decoding, vocabulary management,
and artifact serialization.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union

from tokenizer.bpe_trainer import BPETrainer
from tokenizer.config import TokenizerConfig
from tokenizer.decoder import BPEDecoder
from tokenizer.encoder import BPEEncoder, EncodingResult
from tokenizer.special_tokens import SpecialTokenRegistry
from tokenizer.vocabulary import Vocabulary


class CustomBPETokenizer:
    """Unified Custom BPE Tokenizer for the 404 FOUNDERS foundation model.

    Features:
    - Independent character-level Byte Pair Encoding (non-byte-level BPE).
    - Lossless Unicode preservation and non-destructive symbol parsing.
    - Native multilingual support (Devanagari, Cyrillic, Arabic, CJK, Latin).
    - Code syntax, mathematical notation, and scientific expression preservation.
    - Isolated special-token registry preventing merge interference.
    """

    def __init__(
        self,
        config: Optional[TokenizerConfig] = None,
        special_tokens: Optional[SpecialTokenRegistry] = None,
        vocabulary: Optional[Vocabulary] = None,
        merges: Optional[List[Tuple[str, str]]] = None,
        merge_ranks: Optional[Dict[Tuple[str, str], int]] = None,
    ) -> None:
        self.config = config if config is not None else TokenizerConfig()
        self.special_tokens = (
            special_tokens if special_tokens is not None else SpecialTokenRegistry()
        )
        self.vocabulary = (
            vocabulary
            if vocabulary is not None
            else Vocabulary(
                special_tokens=self.special_tokens,
                unknown_token=self.config.unknown_token,
                pad_token=self.config.pad_token,
            )
        )
        self.merges: List[Tuple[str, str]] = merges if merges is not None else []
        self.merge_ranks: Dict[Tuple[str, str], int] = (
            merge_ranks if merge_ranks is not None else {}
        )

        self._encoder = BPEEncoder(
            vocabulary=self.vocabulary,
            merge_ranks=self.merge_ranks,
            config=self.config,
            special_tokens=self.special_tokens,
        )
        self._decoder = BPEDecoder(
            vocabulary=self.vocabulary,
            config=self.config,
            special_tokens=self.special_tokens,
        )

    @property
    def vocab_size(self) -> int:
        """Return total vocabulary size."""
        return len(self.vocabulary)

    @property
    def pad_token_id(self) -> int:
        """Return ID for padding token."""
        return self.vocabulary.pad_id

    @property
    def unk_token_id(self) -> int:
        """Return ID for unknown token fallback."""
        return self.vocabulary.unk_id

    @property
    def bos_token_id(self) -> int:
        """Return ID for beginning-of-sequence token."""
        return self.vocabulary.token_to_id(self.config.bos_token)

    @property
    def eos_token_id(self) -> int:
        """Return ID for end-of-sequence token."""
        return self.vocabulary.token_to_id(self.config.eos_token)

    def train_from_iterator(
        self,
        corpus: Iterable[str],
        vocab_size: Optional[int] = None,
        min_frequency: Optional[int] = None,
    ) -> CustomBPETokenizer:
        """Train tokenizer on an iterator of text documents.

        Args:
            corpus: Iterable of text strings.
            vocab_size: Optional override for target vocabulary size.
            min_frequency: Optional override for pair frequency cutoff.

        Returns:
            self after training.
        """
        if vocab_size is not None:
            self.config.vocab_size = vocab_size
        if min_frequency is not None:
            self.config.min_frequency = min_frequency

        trainer = BPETrainer(config=self.config, special_tokens=self.special_tokens)
        self.vocabulary, self.merges, self.merge_ranks = trainer.train(corpus)

        # Re-initialize encoder and decoder with trained vocabulary and merges
        self._encoder = BPEEncoder(
            vocabulary=self.vocabulary,
            merge_ranks=self.merge_ranks,
            config=self.config,
            special_tokens=self.special_tokens,
        )
        self._decoder = BPEDecoder(
            vocabulary=self.vocabulary,
            config=self.config,
            special_tokens=self.special_tokens,
        )
        return self

    def encode(
        self,
        text: Optional[str],
        add_bos: bool = False,
        add_eos: bool = False,
        allowed_special: Optional[Set[str]] = None,
    ) -> EncodingResult:
        """Encode raw text into subword tokens and IDs."""
        return self._encoder.encode(
            text=text,
            add_bos=add_bos,
            add_eos=add_eos,
            allowed_special=allowed_special,
        )

    def encode_batch(
        self,
        texts: List[str],
        add_bos: bool = False,
        add_eos: bool = False,
    ) -> List[EncodingResult]:
        """Encode a list of text strings into subword results."""
        return [self.encode(t, add_bos=add_bos, add_eos=add_eos) for t in texts]

    def decode(
        self,
        ids: List[int],
        skip_special_tokens: bool = True,
    ) -> str:
        """Decode integer token IDs back into clean text."""
        return self._decoder.decode(ids=ids, skip_special_tokens=skip_special_tokens)

    def decode_batch(
        self,
        batch_ids: List[List[int]],
        skip_special_tokens: bool = True,
    ) -> List[str]:
        """Decode a batch of token ID sequences."""
        return [self.decode(ids, skip_special_tokens=skip_special_tokens) for ids in batch_ids]

    def get_vocab(self) -> Dict[str, int]:
        """Return vocabulary mapping of token string to integer ID."""
        return self.vocabulary.get_token_to_id()

    def token_to_id(self, token: str) -> int:
        """Return integer ID for a token."""
        return self.vocabulary.token_to_id(token)

    def id_to_token(self, token_id: int) -> str:
        """Return token string for an integer ID."""
        return self.vocabulary.id_to_token(token_id)

    def save(self, path: Union[str, Path]) -> Path:
        """Save tokenizer artifact to a JSON file."""
        from tokenizer.serialization import TokenizerSerializer

        return TokenizerSerializer.save_to_json(self, path)

    @classmethod
    def load(cls, path: Union[str, Path]) -> CustomBPETokenizer:
        """Load tokenizer artifact from a JSON file."""
        from tokenizer.serialization import TokenizerSerializer

        return TokenizerSerializer.load_from_json(path)
