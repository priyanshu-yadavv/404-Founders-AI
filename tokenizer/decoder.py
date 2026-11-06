"""
404 FOUNDERS — BPE Decoder
Reconstructs original text from subword token IDs, correctly inverting whitespace
representation and handling special control tokens.
"""

from __future__ import annotations

from typing import List, Optional

from tokenizer.config import TokenizerConfig
from tokenizer.special_tokens import SpecialTokenRegistry
from tokenizer.vocabulary import Vocabulary


class BPEDecoder:
    """Decodes token IDs or token strings back into clean, formatted text."""

    def __init__(
        self,
        vocabulary: Vocabulary,
        config: Optional[TokenizerConfig] = None,
        special_tokens: Optional[SpecialTokenRegistry] = None,
    ) -> None:
        self.vocabulary = vocabulary
        self.config = config if config is not None else TokenizerConfig()
        self.special_tokens = (
            special_tokens if special_tokens is not None else SpecialTokenRegistry()
        )

    def decode_tokens(
        self,
        tokens: List[str],
        skip_special_tokens: bool = True,
    ) -> str:
        """Convert a list of token strings back into plain text.

        Args:
            tokens: List of subword and special token strings.
            skip_special_tokens: Whether to omit registered special tokens.

        Returns:
            Decoded text string.
        """
        filtered_pieces: List[str] = []
        for tok in tokens:
            if skip_special_tokens and self.special_tokens.is_special(tok) and tok != self.config.unknown_token:
                continue
            filtered_pieces.append(tok)

        raw = "".join(filtered_pieces)
        return raw.replace(self.config.whitespace_symbol, " ")

    def decode(
        self,
        ids: List[int],
        skip_special_tokens: bool = True,
    ) -> str:
        """Convert a list of token IDs back into plain text.

        Args:
            ids: List of integer token IDs.
            skip_special_tokens: Whether to omit registered special tokens.

        Returns:
            Decoded text string.
        """
        tokens: List[str] = []
        for token_id in ids:
            try:
                tok = self.vocabulary.id_to_token(token_id)
                tokens.append(tok)
            except KeyError:
                # If an invalid ID is provided, map to unknown token string
                tokens.append(self.config.unknown_token)

        return self.decode_tokens(tokens, skip_special_tokens=skip_special_tokens)
