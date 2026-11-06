"""
404 FOUNDERS — Vocabulary Management
Bi-directional mapping between string tokens and integer IDs with stable special-token
offsets, unknown-token fallback, and serialization.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from tokenizer.special_tokens import PAD_TOKEN, UNK_TOKEN, SpecialTokenRegistry


class Vocabulary:
    """Manages token-to-ID and ID-to-token mappings for the Custom BPE Tokenizer."""

    def __init__(
        self,
        special_tokens: Optional[SpecialTokenRegistry] = None,
        unknown_token: str = UNK_TOKEN,
        pad_token: str = PAD_TOKEN,
    ) -> None:
        self._token_to_id: Dict[str, int] = {}
        self._id_to_token: Dict[int, str] = {}
        self.unknown_token = unknown_token
        self.pad_token = pad_token

        # Initialize with special tokens
        if special_tokens is not None:
            for idx, token in enumerate(special_tokens.all_tokens()):
                self._token_to_id[token] = idx
                self._id_to_token[idx] = token
            self._special_count = len(special_tokens)
        else:
            self._special_count = 0

    @property
    def special_count(self) -> int:
        """Return count of registered special tokens."""
        return self._special_count

    @property
    def unk_id(self) -> int:
        """Return token ID for unknown token fallback."""
        if self.unknown_token in self._token_to_id:
            return self._token_to_id[self.unknown_token]
        return 1  # Default fallback ID

    @property
    def pad_id(self) -> int:
        """Return token ID for padding token."""
        if self.pad_token in self._token_to_id:
            return self._token_to_id[self.pad_token]
        return 0

    def add_token(self, token: str) -> int:
        """Add a token to the vocabulary if not already present. Returns token ID."""
        if not token:
            raise ValueError("Token cannot be empty")
        if token in self._token_to_id:
            return self._token_to_id[token]

        new_id = len(self._token_to_id)
        self._token_to_id[token] = new_id
        self._id_to_token[new_id] = token
        return new_id

    def add_tokens(self, tokens: Iterable[str]) -> List[int]:
        """Add multiple tokens to the vocabulary in order. Returns assigned IDs."""
        return [self.add_token(tok) for tok in tokens]

    def token_to_id(self, token: str) -> int:
        """Return integer ID for given token. Returns unk_id if token not found."""
        return self._token_to_id.get(token, self.unk_id)

    def id_to_token(self, token_id: int) -> str:
        """Return token string for given ID. Raises KeyError if ID not present."""
        if token_id not in self._id_to_token:
            raise KeyError(f"Token ID {token_id} not found in vocabulary")
        return self._id_to_token[token_id]

    def contains(self, token: str) -> bool:
        """Check if token exists in vocabulary."""
        return token in self._token_to_id

    def contains_id(self, token_id: int) -> bool:
        """Check if token ID exists in vocabulary."""
        return token_id in self._id_to_token

    def __len__(self) -> int:
        """Return total vocabulary size."""
        return len(self._token_to_id)

    def __contains__(self, item: str) -> bool:
        return item in self._token_to_id

    def get_token_to_id(self) -> Dict[str, int]:
        """Return a copy of the token-to-ID dictionary."""
        return dict(self._token_to_id)

    def get_id_to_token(self) -> Dict[int, str]:
        """Return a copy of the ID-to-token dictionary."""
        return dict(self._id_to_token)

    def to_dict(self) -> Dict[str, int]:
        """Export vocabulary mapping to dictionary for serialization."""
        return dict(self._token_to_id)

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, int],
        special_count: int = 0,
        unknown_token: str = UNK_TOKEN,
        pad_token: str = PAD_TOKEN,
    ) -> Vocabulary:
        """Reconstruct Vocabulary from dictionary mapping token to ID."""
        vocab = cls(special_tokens=None, unknown_token=unknown_token, pad_token=pad_token)
        vocab._special_count = special_count
        sorted_items = sorted(data.items(), key=lambda x: x[1])
        for tok, idx in sorted_items:
            vocab._token_to_id[tok] = idx
            vocab._id_to_token[idx] = tok
        return vocab
