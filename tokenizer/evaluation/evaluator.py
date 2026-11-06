"""
404 FOUNDERS — Tokenizer Evaluation
Calculates compression ratio, tokens-per-word, character fertility, out-of-vocabulary rate,
and round-trip parity across multilingual and code corpora.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from tokenizer.bpe_tokenizer import CustomBPETokenizer


@dataclass
class TokenizerMetrics:
    """Metrics container for a text evaluation sample."""

    language: str
    raw_bytes: int
    raw_chars: int
    raw_words: int
    token_count: int
    compression_ratio: float  # raw_bytes / token_count (higher = better compression)
    tokens_per_word: float    # token_count / raw_words (lower = better subword efficiency)
    fertility: float          # token_count / raw_chars
    roundtrip_exact: bool     # decode(encode(text)) == text
    unk_count: int
    unk_rate: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TokenizerEvaluator:
    """Evaluates tokenizer quality and fertility across multilingual and technical corpora."""

    def __init__(self, tokenizer: CustomBPETokenizer) -> None:
        self.tokenizer = tokenizer

    def evaluate_sample(
        self,
        text: str,
        language: str = "general",
    ) -> TokenizerMetrics:
        """Evaluate a single text sample.

        Args:
            text: Text to evaluate.
            language: Language or domain tag.

        Returns:
            TokenizerMetrics instance.
        """
        raw_bytes = len(text.encode("utf-8"))
        raw_chars = len(text)
        words = text.split()
        raw_words = len(words)

        res = self.tokenizer.encode(text)
        token_count = len(res.ids)
        decoded = self.tokenizer.decode(res.ids, skip_special_tokens=True)

        compression = raw_bytes / max(1, token_count)
        tpw = token_count / max(1, raw_words)
        fertility = token_count / max(1, raw_chars)
        exact = (decoded == text)
        unk_count = res.ids.count(self.tokenizer.unk_token_id)
        unk_rate = unk_count / max(1, token_count)

        return TokenizerMetrics(
            language=language,
            raw_bytes=raw_bytes,
            raw_chars=raw_chars,
            raw_words=raw_words,
            token_count=token_count,
            compression_ratio=round(compression, 3),
            tokens_per_word=round(tpw, 3),
            fertility=round(fertility, 3),
            roundtrip_exact=exact,
            unk_count=unk_count,
            unk_rate=round(unk_rate, 4),
        )

    def evaluate_corpus(
        self,
        corpus_by_domain: Dict[str, List[str]],
    ) -> Dict[str, Dict[str, Any]]:
        """Evaluate a comprehensive corpus grouped by language and domain.

        Args:
            corpus_by_domain: Mapping of domain/language name to list of sample texts.

        Returns:
            Dictionary mapping domain name to aggregated metrics summary.
        """
        results: Dict[str, Dict[str, Any]] = {}

        for domain, samples in corpus_by_domain.items():
            if not samples:
                continue
            metrics_list = [self.evaluate_sample(s, language=domain) for s in samples]

            total_bytes = sum(m.raw_bytes for m in metrics_list)
            total_chars = sum(m.raw_chars for m in metrics_list)
            total_words = sum(m.raw_words for m in metrics_list)
            total_tokens = sum(m.token_count for m in metrics_list)
            all_exact = all(m.roundtrip_exact for m in metrics_list)
            total_unk = sum(m.unk_count for m in metrics_list)

            results[domain] = {
                "samples_count": len(samples),
                "total_bytes": total_bytes,
                "total_chars": total_chars,
                "total_words": total_words,
                "total_tokens": total_tokens,
                "compression_ratio": round(total_bytes / max(1, total_tokens), 3),
                "tokens_per_word": round(total_tokens / max(1, total_words), 3),
                "fertility": round(total_tokens / max(1, total_chars), 3),
                "all_roundtrip_exact": all_exact,
                "total_unk": total_unk,
                "unk_rate": round(total_unk / max(1, total_tokens), 4),
            }

        return results
