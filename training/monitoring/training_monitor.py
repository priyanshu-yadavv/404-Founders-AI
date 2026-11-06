"""
404 FOUNDERS — Training Monitor & Telemetry Tracker
Tracks step metrics, loss curves, gradient norms, throughput (tokens/sec),
and resource consumption with structured JSONL and console output.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import os
import time
import torch


@dataclass
class StepMetrics:
    """Telemetry captured at a single training step."""
    step: int
    timestamp: str
    train_loss: float
    perplexity: float
    token_accuracy: float
    learning_rate: float
    grad_norm: float
    batch_tokens: int
    total_tokens: int
    tokens_per_second: float
    step_duration_ms: float
    cpu_percent: float
    ram_used_gb: float
    val_loss: Optional[float] = None
    val_perplexity: Optional[float] = None


class TrainingMonitor:
    """
    Structured metrics logger writing machine-readable JSONL streams
    and reporting real-time step statistics.
    """

    def __init__(self, output_dir: str = "training_runs/default", log_filename: str = "metrics.jsonl") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / log_filename
        self.total_tokens_processed = 0
        self.start_time = time.time()
        self.last_step_time = time.time()

    def record_step(
        self,
        step: int,
        train_loss: float,
        perplexity: float,
        token_accuracy: float,
        learning_rate: float,
        grad_norm: float,
        batch_tokens: int,
        val_loss: Optional[float] = None,
        val_perplexity: Optional[float] = None,
    ) -> StepMetrics:
        """
        Record step metrics, append to JSONL log, and return StepMetrics dataclass.
        """
        now = time.time()
        step_duration = max(now - self.last_step_time, 1e-6)
        self.last_step_time = now

        self.total_tokens_processed += batch_tokens
        tokens_per_sec = float(batch_tokens) / step_duration

        # Estimate memory usage
        ram_used_gb = 0.0
        try:
            import resource
            rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            ram_used_gb = round(rss_kb / (1024.0 * 1024.0), 3)  # Linux ru_maxrss is in KB
        except Exception:
            pass

        metrics = StepMetrics(
            step=step,
            timestamp=datetime.now(timezone.utc).isoformat(),
            train_loss=round(train_loss, 5),
            perplexity=round(perplexity, 3),
            token_accuracy=round(token_accuracy, 4),
            learning_rate=learning_rate,
            grad_norm=round(grad_norm, 4),
            batch_tokens=batch_tokens,
            total_tokens=self.total_tokens_processed,
            tokens_per_second=round(tokens_per_sec, 1),
            step_duration_ms=round(step_duration * 1000.0, 2),
            cpu_percent=0.0,
            ram_used_gb=ram_used_gb,
            val_loss=round(val_loss, 5) if val_loss is not None else None,
            val_perplexity=round(val_perplexity, 3) if val_perplexity is not None else None,
        )

        # Append to JSONL log
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(metrics)) + "\n")

        return metrics

    def format_log_line(self, m: StepMetrics) -> str:
        """Format metrics into a clean single-line terminal summary."""
        val_str = f" | val_loss: {m.val_loss:.4f} (ppl: {m.val_perplexity:.2f})" if m.val_loss is not None else ""
        return (
            f"[Step {m.step:05d}] "
            f"loss: {m.train_loss:.4f} | "
            f"acc: {m.token_accuracy*100:.1f}% | "
            f"lr: {m.learning_rate:.2e} | "
            f"grad: {m.grad_norm:.2f} | "
            f"tok/s: {m.tokens_per_second:.1f} | "
            f"mem: {m.ram_used_gb:.2f}GB"
            f"{val_str}"
        )
