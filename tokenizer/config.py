"""
404 FOUNDERS — Tokenizer Configuration
Defines hyperparameters, normalization settings, and special token configurations
for the Custom BPE Tokenizer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TokenizerConfig:
    """Configuration hyperparameters for the Custom BPE Tokenizer.

    Attributes:
        vocab_size: Target vocabulary size (including special tokens and base characters).
        min_frequency: Minimum occurrence frequency for a byte-pair merge candidate.
        normalization: Unicode normalization mode ('NFC', 'NFKC', or 'none').
        whitespace_symbol: Visible character used to represent whitespace boundaries.
        unknown_token: Out-of-vocabulary fallback token.
        pad_token: Padding token.
        bos_token: Beginning-of-sequence token.
        eos_token: End-of-sequence token.
        max_token_length: Optional maximum subword token length.
        preserve_case: Whether to preserve character case during pre-tokenization.
        special_tokens: List of registered special control tokens.
    """

    vocab_size: int = 1000
    min_frequency: int = 2
    normalization: str = "NFC"
    whitespace_symbol: str = " "  # Unicode \u2581 (Lower One Eighth Block)
    unknown_token: str = "<unk>"
    pad_token: str = "<pad>"
    bos_token: str = "<bos>"
    eos_token: str = "<eos>"
    max_token_length: Optional[int] = None
    preserve_case: bool = True
    special_tokens: List[str] = field(
        default_factory=lambda: [
            "<pad>",
            "<unk>",
            "<bos>",
            "<eos>",
            "<eot>",
            "<sys_start>",
            "<sys_end>",
            "<user_start>",
            "<user_end>",
            "<asst_start>",
            "<asst_end>",
            "<thought>",
            "</thought>",
            "<tool_call>",
            "<tool_result>",
            "<image>",
            "</image>",
            "<audio>",
            "</audio>",
            "<video>",
            "</video>",
            "<spatial>",
            "</spatial>",
            "<code_start>",
            "<code_end>",
        ]
    )

    def __post_init__(self) -> None:
        if self.vocab_size < 32:
            raise ValueError(f"vocab_size must be >= 32, got {self.vocab_size}")
        if self.min_frequency < 1:
            raise ValueError(f"min_frequency must be >= 1, got {self.min_frequency}")
        if self.normalization not in ("NFC", "NFKC", "none"):
            raise ValueError(
                f"Invalid normalization '{self.normalization}'. Must be 'NFC', 'NFKC', or 'none'."
            )
        if not self.whitespace_symbol:
            raise ValueError("whitespace_symbol cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TokenizerConfig:
        """Create configuration instance from dictionary."""
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
