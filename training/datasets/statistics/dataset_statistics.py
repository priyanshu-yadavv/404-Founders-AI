"""
404 FOUNDERS — Dataset Statistics
Computes record volume, token counts, language distributions, and domain breakdowns,
producing structured summaries and Markdown audit reports.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, Optional

from training.datasets.ingestion.dataset_ingestor import DataRecord


class DatasetStatistics:
    """Computes descriptive statistical metrics across dataset records."""

    @staticmethod
    def compute(
        records: Iterable[DataRecord],
        tokenizer: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Compute statistical breakdown for a collection of DataRecords.

        Args:
            records: Iterable of DataRecord instances.
            tokenizer: Optional CustomBPETokenizer instance to compute token counts.

        Returns:
            Dictionary containing descriptive statistical metrics.
        """
        total_records = 0
        total_words = 0
        total_chars = 0
        total_bytes = 0
        domain_counts: Counter[str] = Counter()
        lang_counts: Counter[str] = Counter()

        token_count = 0
        has_tokenizer = tokenizer is not None

        for rec in records:
            total_records += 1
            content = rec.content
            c_len = len(content)
            words = content.split()
            w_len = len(words)
            b_len = len(content.encode("utf-8"))

            total_chars += c_len
            total_words += w_len
            total_bytes += b_len

            domain_counts[rec.domain] += 1
            lang_counts[rec.language] += 1

            if has_tokenizer:
                enc = tokenizer.encode(content)
                token_count += len(enc.ids)

        avg_chars = round(total_chars / max(1, total_records), 2)
        avg_words = round(total_words / max(1, total_records), 2)
        avg_bytes = round(total_bytes / max(1, total_records), 2)

        stats: Dict[str, Any] = {
            "total_records": total_records,
            "total_words": total_words,
            "total_characters": total_chars,
            "total_bytes": total_bytes,
            "avg_chars_per_record": avg_chars,
            "avg_words_per_record": avg_words,
            "avg_bytes_per_record": avg_bytes,
            "domain_breakdown": dict(domain_counts),
            "language_breakdown": dict(lang_counts),
        }

        if has_tokenizer:
            stats["total_tokens"] = token_count
            stats["tokens_per_word"] = round(token_count / max(1, total_words), 3)
            stats["compression_ratio"] = round(total_bytes / max(1, token_count), 3)

        return stats

    @staticmethod
    def to_markdown_table(stats: Dict[str, Any]) -> str:
        """Format statistics dictionary as a clean Markdown table."""
        lines = [
            "### Dataset Descriptive Statistics Report",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| **Total Records** | {stats.get('total_records', 0):,} |",
            f"| **Total Words** | {stats.get('total_words', 0):,} |",
            f"| **Total Characters** | {stats.get('total_characters', 0):,} |",
            f"| **Total Bytes** | {stats.get('total_bytes', 0):,} bytes |",
            f"| **Avg Chars / Record** | {stats.get('avg_chars_per_record', 0.0)} |",
            f"| **Avg Words / Record** | {stats.get('avg_words_per_record', 0.0)} |",
        ]

        if "total_tokens" in stats:
            lines.append(f"| **Total Subword Tokens** | {stats['total_tokens']:,} |")
            lines.append(f"| **Tokens / Word** | {stats['tokens_per_word']} |")
            lines.append(f"| **Compression Ratio** | {stats['compression_ratio']} bytes/token |")

        lines.extend(["", "#### Domain Breakdown", "", "| Domain | Record Count |", "|---|---|"])
        for dom, cnt in sorted(stats.get("domain_breakdown", {}).items()):
            lines.append(f"| `{dom}` | {cnt:,} |")

        lines.extend(["", "#### Language Breakdown", "", "| Language | Record Count |", "|---|---|"])
        for lang, cnt in sorted(stats.get("language_breakdown", {}).items()):
            lines.append(f"| `{lang}` | {cnt:,} |")

        return "\n".join(lines)
