"""
404 FOUNDERS — Experiment Tracking & Telemetry Interface
Provides offline air-gapped JSONL logging, hyperparameter tracking, and unified
experiment recording compatible with TensorBoard and remote metric collectors.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RunConfig:
    """Configuration metadata for an experiment run."""

    run_id: str
    experiment_name: str
    model_name: str
    num_parameters: int
    batch_size: int
    learning_rate: float
    optimizer: str
    mixed_precision: str
    cluster_tier: str
    tags: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExperimentTracker:
    """Unified experiment tracker with offline air-gapped JSONL logging and

    optional TensorBoard integration.
    """

    def __init__(
        self,
        experiment_name: str,
        run_id: Optional[str] = None,
        log_dir: str | Path = "logs/experiments",
        enable_tensorboard: bool = False,
    ) -> None:
        self.experiment_name = experiment_name
        self.run_id = run_id or f"{experiment_name}_{int(time.time())}"
        self.log_dir = Path(log_dir) / self.run_id
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.metrics_file = self.log_dir / "metrics.jsonl"
        self.config_file = self.log_dir / "run_config.json"
        self.is_active = True

        self.tb_writer = None
        if enable_tensorboard:
            try:
                from torch.utils.tensorboard import SummaryWriter  # type: ignore

                self.tb_writer = SummaryWriter(log_dir=str(self.log_dir))
            except ImportError:
                pass

    def log_config(self, run_config: RunConfig | Dict[str, Any]) -> None:
        """Saves experiment configuration parameters."""
        data = run_config.to_dict() if isinstance(run_config, RunConfig) else run_config
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def log_metrics(self, step: int, metrics: Dict[str, float], step_time: Optional[float] = None) -> None:
        """Logs step metrics to JSONL and optional TensorBoard."""
        entry = {
            "step": step,
            "timestamp": time.time(),
            "step_time": step_time,
            **metrics,
        }

        # Thread-safe atomic line write
        with open(self.metrics_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        if self.tb_writer is not None:
            for k, v in metrics.items():
                self.tb_writer.add_scalar(k, v, step)

    def log_artifact_reference(self, artifact_name: str, path: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Records an artifact link in the experiment log."""
        artifacts_file = self.log_dir / "artifacts.jsonl"
        entry = {
            "timestamp": time.time(),
            "artifact_name": artifact_name,
            "path": path,
            "metadata": metadata or {},
        }
        with open(artifacts_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def read_metrics(self) -> List[Dict[str, Any]]:
        """Reads all logged metrics from the JSONL log."""
        if not self.metrics_file.exists():
            return []
        records = []
        with open(self.metrics_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records

    def close(self) -> None:
        """Closes any active writers."""
        if self.tb_writer is not None:
            self.tb_writer.close()
            self.tb_writer = None
        self.is_active = False
