"""
404 FOUNDERS — Special Tokens Registry
Manages reserved special control tokens, stable ID assignments, and pattern matching
to prevent interference with ordinary BPE merges.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set


# Standard Canonical Special Tokens
PAD_TOKEN = "<pad>"
UNK_TOKEN = "<unk>"
BOS_TOKEN = "<bos>"
EOS_TOKEN = "<eos>"
EOT_TOKEN = "<eot>"
SYS_START_TOKEN = "<sys_start>"
SYS_END_TOKEN = "<sys_end>"
USER_START_TOKEN = "<user_start>"
USER_END_TOKEN = "<user_end>"
ASST_START_TOKEN = "<asst_start>"
ASST_END_TOKEN = "<asst_end>"
THOUGHT_START_TOKEN = "<thought>"
THOUGHT_END_TOKEN = "</thought>"
TOOL_CALL_TOKEN = "<tool_call>"
TOOL_RESULT_TOKEN = "<tool_result>"
IMAGE_START_TOKEN = "<image>"
IMAGE_END_TOKEN = "</image>"
AUDIO_START_TOKEN = "<audio>"
AUDIO_END_TOKEN = "</audio>"
VIDEO_START_TOKEN = "<video>"
VIDEO_END_TOKEN = "</video>"
SPATIAL_START_TOKEN = "<spatial>"
SPATIAL_END_TOKEN = "</spatial>"
CODE_START_TOKEN = "<code_start>"
CODE_END_TOKEN = "<code_end>"

DEFAULT_SPECIAL_TOKENS = [
    PAD_TOKEN,
    UNK_TOKEN,
    BOS_TOKEN,
    EOS_TOKEN,
    EOT_TOKEN,
    SYS_START_TOKEN,
    SYS_END_TOKEN,
    USER_START_TOKEN,
    USER_END_TOKEN,
    ASST_START_TOKEN,
    ASST_END_TOKEN,
    THOUGHT_START_TOKEN,
    THOUGHT_END_TOKEN,
    TOOL_CALL_TOKEN,
    TOOL_RESULT_TOKEN,
    IMAGE_START_TOKEN,
    IMAGE_END_TOKEN,
    AUDIO_START_TOKEN,
    AUDIO_END_TOKEN,
    VIDEO_START_TOKEN,
    VIDEO_END_TOKEN,
    SPATIAL_START_TOKEN,
    SPATIAL_END_TOKEN,
    CODE_START_TOKEN,
    CODE_END_TOKEN,
]


class SpecialTokenRegistry:
    """Registry maintaining unique, collision-free special tokens with immutable IDs."""

    def __init__(self, special_tokens: Optional[List[str]] = None) -> None:
        tokens_to_add = special_tokens if special_tokens is not None else DEFAULT_SPECIAL_TOKENS
        self._token_to_id: Dict[str, int] = {}
        self._id_to_token: Dict[int, str] = {}
        self._pattern: Optional[re.Pattern[str]] = None

        for idx, token in enumerate(tokens_to_add):
            if token in self._token_to_id:
                continue
            self._token_to_id[token] = idx
            self._id_to_token[idx] = token

        self._rebuild_pattern()

    def _rebuild_pattern(self) -> None:
        """Compile regex pattern matching any registered special token, longest first."""
        if not self._token_to_id:
            self._pattern = None
            return
        escaped = [re.escape(tok) for tok in sorted(self._token_to_id.keys(), key=len, reverse=True)]
        self._pattern = re.compile("|".join(escaped))

    @property
    def pattern(self) -> Optional[re.Pattern[str]]:
        """Return compiled regex pattern matching any registered special token."""
        return self._pattern

    def register(self, token: str) -> int:
        """Register a new special token. Returns assigned ID."""
        if not token:
            raise ValueError("Special token cannot be empty")
        if token in self._token_to_id:
            return self._token_to_id[token]
        new_id = len(self._token_to_id)
        self._token_to_id[token] = new_id
        self._id_to_token[new_id] = token
        self._rebuild_pattern()
        return new_id

    def is_special(self, token: str) -> bool:
        """Check if a token string is a registered special token."""
        return token in self._token_to_id

    def get_id(self, token: str) -> int:
        """Get ID of a registered special token. Raises KeyError if not registered."""
        if token not in self._token_to_id:
            raise KeyError(f"Special token '{token}' not registered")
        return self._token_to_id[token]

    def get_token(self, token_id: int) -> str:
        """Get token string for an ID. Raises KeyError if ID not registered."""
        if token_id not in self._id_to_token:
            raise KeyError(f"Special token ID {token_id} not registered")
        return self._id_to_token[token_id]

    def all_tokens(self) -> List[str]:
        """Return list of all registered special tokens ordered by ID."""
        return [self._id_to_token[i] for i in range(len(self._id_to_token))]

    def token_set(self) -> Set[str]:
        """Return set of registered special tokens."""
        return set(self._token_to_id.keys())

    def __len__(self) -> int:
        return len(self._token_to_id)

    def to_dict(self) -> Dict[str, int]:
        """Export mapping of token to ID."""
        return dict(self._token_to_id)

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> SpecialTokenRegistry:
        """Reconstruct registry from dictionary mapping token to ID."""
        registry = cls([])
        sorted_tokens = sorted(data.items(), key=lambda x: x[1])
        for tok, idx in sorted_tokens:
            registry._token_to_id[tok] = idx
            registry._id_to_token[idx] = tok
        registry._rebuild_pattern()
        return registry
