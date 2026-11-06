#!/usr/bin/env python3
"""
404 FOUNDERS — Resume Training CLI
Resumes an existing training experiment from an atomically verified checkpoint.
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training.configs.model_config import (
    FoundationModelConfig,
    PretrainingConfig,
)
from training.dataloaders.data_loader import FoundationDataLoader
from training.engine.orchestrator import TrainingOrchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="404 FOUNDERS — Resume Pretraining")
    parser.add_argument("checkpoint_path", type=str, help="Path to checkpoint .pt file to resume from")
    parser.add_argument("--additional-steps", type=int, default=15, help="Number of additional steps to run")
    args = parser.parse_args()

    ckpt_path = Path(args.checkpoint_path)
    if not ckpt_path.is_file():
        print(f"[ERROR] Checkpoint file does not exist: {ckpt_path}")
        sys.exit(1)

    import torch
    payload = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    current_step = payload.get("step", 0)
    model_cfg = FoundationModelConfig.from_dict(payload.get("model_config", {}))
    pretrain_cfg_dict = payload.get("pretraining_config", {})
    pretrain_cfg_dict["max_steps"] = current_step + args.additional_steps
    pretrain_cfg = PretrainingConfig.from_dict(pretrain_cfg_dict)

    print(f"[404 FOUNDERS] Resuming from step {current_step} up to step {pretrain_cfg.max_steps}...")

    train_loader = FoundationDataLoader.create_synthetic_loader(
        num_samples=32,
        batch_size=pretrain_cfg.batch_size,
        seq_len=model_cfg.max_seq_len,
        vocab_size=model_cfg.vocab_size,
        seed=pretrain_cfg.seed,
    )

    orchestrator = TrainingOrchestrator(
        model_config=model_cfg,
        pretraining_config=pretrain_cfg,
        run_id=f"resumed_from_step_{current_step}",
        description=f"Resumed training from {ckpt_path.name}",
    )

    summary = orchestrator.train(train_loader=train_loader, resume_from=str(ckpt_path))
    print(f"\n[404 FOUNDERS] Resumption completed: advanced from step {current_step} to {summary.total_steps} (Loss: {summary.final_train_loss:.4f})")


if __name__ == "__main__":
    main()
