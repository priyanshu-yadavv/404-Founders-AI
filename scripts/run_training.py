#!/usr/bin/env python3
"""
404 FOUNDERS — Foundation Model Pretraining CLI
Launches controlled local pretraining experiments on CPU/GPU with live telemetry,
checkpointing, and experiment tracking.
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training.configs.model_config import (
    EXPERIMENTAL_LOCAL_CPU_CONFIG,
    EXPERIMENTAL_TINY_CONFIG,
    PretrainingConfig,
)
from training.dataloaders.data_loader import FoundationDataLoader
from training.engine.compute_readiness import ComputeReadinessGate
from training.engine.orchestrator import TrainingOrchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="404 FOUNDERS — Foundation Model Pretraining")
    parser.add_argument("--profile", choices=["tiny", "local_cpu"], default="tiny", help="Model profile")
    parser.add_argument("--steps", type=int, default=30, help="Number of training steps to execute")
    parser.add_argument("--batch-size", type=int, default=2, help="Batch size per forward pass")
    parser.add_argument("--lr", type=float, default=5e-4, help="Peak learning rate")
    parser.add_argument("--warmup-steps", type=int, default=5, help="Linear warmup steps")
    parser.add_argument("--eval-interval", type=int, default=10, help="Evaluation interval in steps")
    parser.add_argument("--save-interval", type=int, default=15, help="Checkpoint save interval in steps")
    parser.add_argument("--run-id", type=str, default=None, help="Custom experiment run identifier")
    parser.add_argument("--resume", type=str, default=None, help="Path to checkpoint to resume from")
    args = parser.parse_args()

    model_cfg = EXPERIMENTAL_TINY_CONFIG if args.profile == "tiny" else EXPERIMENTAL_LOCAL_CPU_CONFIG
    pretrain_cfg = PretrainingConfig(
        batch_size=args.batch_size,
        max_steps=args.steps,
        learning_rate=args.lr,
        warmup_steps=args.warmup_steps,
        eval_interval=args.eval_interval,
        save_interval=args.save_interval,
        log_interval=5,
        device="cpu",
    )

    print("[404 FOUNDERS] Evaluating compute readiness gate before execution...")
    gate = ComputeReadinessGate()
    readiness = gate.evaluate_readiness(model_cfg, pretrain_cfg)
    print("\n" + readiness.summary() + "\n")

    if not readiness.is_safe_to_execute:
        print("[BLOCKER] Execution halted by Compute Readiness Gate to prevent OOM panic!")
        sys.exit(1)

    # Prepare training and validation data loaders
    print("[404 FOUNDERS] Preparing synthetic pretraining datasets...")
    train_loader = FoundationDataLoader.create_synthetic_loader(
        num_samples=32,
        batch_size=pretrain_cfg.batch_size,
        seq_len=model_cfg.max_seq_len,
        vocab_size=model_cfg.vocab_size,
        seed=pretrain_cfg.seed,
    )
    val_loader = FoundationDataLoader.create_synthetic_loader(
        num_samples=16,
        batch_size=pretrain_cfg.batch_size,
        seq_len=model_cfg.max_seq_len,
        vocab_size=model_cfg.vocab_size,
        seed=pretrain_cfg.seed + 100,
    )

    orchestrator = TrainingOrchestrator(
        model_config=model_cfg,
        pretraining_config=pretrain_cfg,
        run_id=args.run_id,
        description=f"Local pilot pretraining ({args.profile})",
    )

    print(f"[404 FOUNDERS] Starting pretraining loop ({args.steps} steps)...")
    summary = orchestrator.train(train_loader=train_loader, val_loader=val_loader, resume_from=args.resume)

    print("\n=== PRETRAINING RUN COMPLETE ===")
    print(f"Run ID: {summary.run_id}")
    print(f"Status: {summary.status}")
    print(f"Total Steps: {summary.total_steps}")
    print(f"Total Tokens: {summary.total_tokens:,}")
    print(f"Final Train Loss: {summary.final_train_loss:.4f}")
    if summary.best_val_loss is not None:
        print(f"Best Validation Loss: {summary.best_val_loss:.4f}")
    print(f"Duration: {summary.elapsed_seconds:.2f}s")
    print(f"Checkpoints Saved: {summary.checkpoints_saved}")
    print("================================")


if __name__ == "__main__":
    main()
