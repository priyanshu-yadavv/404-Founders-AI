#!/usr/bin/env python3
"""
404 FOUNDERS — Checkpoint Inspector CLI
Inspects saved checkpoint state, metadata, hyperparameters, and validates cryptographic SHA-256 sidecars.
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training.checkpoints.checkpoint_manager import CheckpointManager


def main() -> None:
    parser = argparse.ArgumentParser(description="404 FOUNDERS — Checkpoint Inspector")
    parser.add_argument("checkpoint_path", type=str, help="Path to .pt checkpoint file to inspect")
    parser.add_argument("--skip-integrity", action="store_true", help="Skip SHA-256 sidecar validation")
    args = parser.parse_args()

    path = Path(args.checkpoint_path)
    if not path.is_file():
        print(f"[ERROR] Checkpoint file does not exist: {path}")
        sys.exit(1)

    print(f"[404 FOUNDERS] Inspecting checkpoint: {path}")
    ckpt_mgr = CheckpointManager(checkpoint_dir=str(path.parent))

    try:
        payload = ckpt_mgr.load_checkpoint(
            path,
            verify_integrity=not args.skip_integrity,
            restore_rng=False,
        )
    except Exception as e:
        print(f"[ERROR] Failed to load checkpoint: {str(e)}")
        sys.exit(1)

    print("\n=== CHECKPOINT METADATA ===")
    print(f"Step: {payload.get('step')}")
    print(f"Timestamp: {payload.get('timestamp')}")
    print(f"Dataset Version: {payload.get('dataset_version')}")
    print(f"Tokenizer Version: {payload.get('tokenizer_version')}")
    print(f"Is Best Model: {payload.get('is_best')}")

    metrics = payload.get("metrics", {})
    if metrics:
        print("\nRecorded Metrics:")
        for k, v in metrics.items():
            print(f"  • {k}: {v}")

    model_cfg = payload.get("model_config", {})
    print(f"\nModel Configuration: d_model={model_cfg.get('d_model')}, layers={model_cfg.get('n_layers')}, heads={model_cfg.get('n_heads')}, vocab={model_cfg.get('vocab_size')}")

    state_dict = payload.get("model_state_dict", {})
    total_params = sum(p.numel() for p in state_dict.values())
    print(f"Serialized Tensors: {len(state_dict)} ({total_params:,} parameters)")

    sidecar = path.with_suffix(".pt.sha256")
    if sidecar.is_file():
        with open(sidecar, "r") as f:
            print(f"Cryptographic SHA-256: {f.read().strip()}")
    print("===========================\n")


if __name__ == "__main__":
    main()
