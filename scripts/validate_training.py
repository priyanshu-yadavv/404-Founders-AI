#!/usr/bin/env python3
"""
404 FOUNDERS — Pre-Flight Training Validation CLI
Executes the mandatory 10-step preflight verification suite before pretraining workloads.
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training.configs.model_config import EXPERIMENTAL_TINY_CONFIG
from training.validation.preflight_verifier import PreflightVerifier


def main() -> None:
    parser = argparse.ArgumentParser(description="404 FOUNDERS — Pre-Flight Training Verifier")
    parser.parse_args()

    print("[404 FOUNDERS] Starting 10-step Pre-Flight Training Verification Suite...")
    verifier = PreflightVerifier(model_config=EXPERIMENTAL_TINY_CONFIG)
    report = verifier.run_all_checks()

    print("\n" + report.summary())

    if not report.all_passed:
        print("\n[ERROR] Pre-flight verification failed! Check details above before training.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All 10 pre-flight validation checks passed successfully!")


if __name__ == "__main__":
    main()
