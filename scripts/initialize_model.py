#!/usr/bin/env python3
"""
404 FOUNDERS — Model Initialization CLI
Initializes NeuralCore from random weights, validates parameter finiteness,
prints parameter shapes and counts, and outputs an auditable initialization report.
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training.configs.model_config import (
    EXPERIMENTAL_LOCAL_CPU_CONFIG,
    EXPERIMENTAL_TINY_CONFIG,
    RESEARCH_PILOT_CONFIG,
)
from training.initialization.initializer import ModelInitializer


def main() -> None:
    parser = argparse.ArgumentParser(description="404 FOUNDERS — Model Initialization Auditor")
    parser.add_argument(
        "--profile",
        choices=["tiny", "local_cpu", "pilot"],
        default="local_cpu",
        help="Model architecture profile to initialize",
    )
    parser.add_argument("--seed", type=int, default=404, help="Random initialization seed")
    parser.add_argument("--export-json", type=str, default=None, help="Path to export initialization report JSON")
    args = parser.parse_args()

    profiles = {
        "tiny": EXPERIMENTAL_TINY_CONFIG,
        "local_cpu": EXPERIMENTAL_LOCAL_CPU_CONFIG,
        "pilot": RESEARCH_PILOT_CONFIG,
    }
    cfg = profiles[args.profile]
    cfg.random_seed = args.seed

    print(f"[404 FOUNDERS] Initializing model with profile '{args.profile}' (seed={args.seed})...")
    initializer = ModelInitializer(cfg)
    model, report = initializer.initialize_model(seed=args.seed)

    print("\n" + report.summary())

    print("\nParameter Layer Breakdown:")
    for summary in report.layers:
        print(
            f"  • {summary.name:<45} {str(summary.shape):<20} "
            f"numel: {summary.numel:<10} mean: {summary.mean:+.4f} std: {summary.std:.4f}"
        )

    if args.export_json:
        out_path = Path(args.export_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"\n[404 FOUNDERS] Initialization report exported to {out_path}")

    # Verify reproducibility
    print("\nVerifying initialization reproducibility...")
    is_reproducible = initializer.verify_reproducibility(seed=args.seed)
    if is_reproducible:
        print("  ✓ Verification passed: identical seeds produce bitwise identical weights, different seeds diverge.")
    else:
        print("  ✗ Verification failed: initialization is not deterministic!")
        sys.exit(1)


if __name__ == "__main__":
    main()
