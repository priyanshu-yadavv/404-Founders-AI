"""
404 FOUNDERS — Tokenizer Serialization
Saves and loads trained Custom BPE Tokenizer artifacts (vocabulary, merge rules,
special tokens, and configuration) to and from disk in structured JSON format.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, Union

from tokenizer.config import TokenizerConfig
from tokenizer.special_tokens import SpecialTokenRegistry
from tokenizer.vocabulary import Vocabulary

if TYPE_CHECKING:
    from tokenizer.bpe_tokenizer import CustomBPETokenizer


class TokenizerSerializer:
    """Serializes and deserializes Custom BPE Tokenizer models."""

    VERSION = "1.0.0"
    TOKENIZER_TYPE = "CustomBPE"

    @classmethod
    def to_dict(cls, tokenizer: CustomBPETokenizer) -> Dict[str, Any]:
        """Convert tokenizer state into a serializable dictionary."""
        return {
            "version": cls.VERSION,
            "tokenizer_type": cls.TOKENIZER_TYPE,
            "config": tokenizer.config.to_dict(),
            "special_tokens": tokenizer.special_tokens.to_dict(),
            "vocabulary": tokenizer.vocabulary.to_dict(),
            "merges": [list(pair) for pair in tokenizer.merges],
        }

    @classmethod
    def save_to_json(cls, tokenizer: CustomBPETokenizer, path: Union[str, Path]) -> Path:
        """Save complete tokenizer model to a single JSON file.

        Args:
            tokenizer: CustomBPETokenizer instance to save.
            path: Destination file path.

        Returns:
            Path object of the saved file.
        """
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = cls.to_dict(tokenizer)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return dest

    @classmethod
    def load_from_json(cls, path: Union[str, Path]) -> CustomBPETokenizer:
        """Load and reconstruct CustomBPETokenizer model from a JSON file.

        Args:
            path: Source file path.

        Returns:
            Instantiated CustomBPETokenizer with loaded state.
        """
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"Tokenizer artifact not found: {source}")

        with open(source, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get("tokenizer_type") != cls.TOKENIZER_TYPE:
            raise ValueError(
                f"Unsupported tokenizer type: {data.get('tokenizer_type')}. Expected '{cls.TOKENIZER_TYPE}'."
            )

        config = TokenizerConfig.from_dict(data["config"])
        special_tokens = SpecialTokenRegistry.from_dict(data["special_tokens"])
        vocabulary = Vocabulary.from_dict(
            data["vocabulary"],
            special_count=len(special_tokens),
            unknown_token=config.unknown_token,
            pad_token=config.pad_token,
        )

        raw_merges: List[List[str]] = data.get("merges", [])
        merges: List[Tuple[str, str]] = [tuple(m) for m in raw_merges]  # type: ignore[misc]
        merge_ranks: Dict[Tuple[str, str], int] = {pair: rank for rank, pair in enumerate(merges)}

        from tokenizer.bpe_tokenizer import CustomBPETokenizer

        return CustomBPETokenizer(
            config=config,
            special_tokens=special_tokens,
            vocabulary=vocabulary,
            merges=merges,
            merge_ranks=merge_ranks,
        )

    @classmethod
    def export_vocab_and_merges(
        cls,
        tokenizer: CustomBPETokenizer,
        vocab_path: Union[str, Path],
        merges_path: Union[str, Path],
    ) -> Tuple[Path, Path]:
        """Export vocab.json and merges.txt separately for standard ecosystem tooling."""
        v_dest = Path(vocab_path)
        m_dest = Path(merges_path)
        v_dest.parent.mkdir(parents=True, exist_ok=True)
        m_dest.parent.mkdir(parents=True, exist_ok=True)

        with open(v_dest, "w", encoding="utf-8") as f:
            json.dump(tokenizer.vocabulary.to_dict(), f, ensure_ascii=False, indent=2)

        with open(m_dest, "w", encoding="utf-8") as f:
            f.write(f"#version: {cls.VERSION}\n")
            for p0, p1 in tokenizer.merges:
                f.write(f"{p0} {p1}\n")

        return v_dest, m_dest
