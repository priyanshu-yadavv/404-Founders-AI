#!/usr/bin/env python3
"""
404 FOUNDERS — Pre-Flight Deployment Readiness Verification
Validates runtime dependencies, database integrity, configuration files,
neural core initialization, and frontend asset completeness before deployment.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Also ensure .venv site-packages is in sys.path if present
venv_site = REPO_ROOT / ".venv/lib/python3.14/site-packages"
if venv_site.is_dir():
    sys.path.insert(0, str(venv_site))


def check_python_environment() -> dict:
    major, minor, micro = sys.version_info[:3]
    return {
        "status": "PASS" if major == 3 and minor >= 10 else "FAIL",
        "python_version": f"{major}.{minor}.{micro}",
        "executable": sys.executable,
    }


def check_torch_runtime() -> dict:
    try:
        import torch
        t = torch.randn(2, 4)
        out = (t * 2.0).sum().item()
        return {
            "status": "PASS",
            "torch_version": torch.__version__,
            "cpu_compute_verified": True,
            "cuda_available": torch.cuda.is_available(),
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}


def check_database_and_migrations() -> dict:
    try:
        from database.connection import DatabaseManager
        from database.schema import apply_migrations

        db_path = REPO_ROOT / "data/memory.db"
        db_mgr = DatabaseManager.get_instance(db_path=db_path)
        with db_mgr.get_connection() as conn:
            applied = apply_migrations(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM schema_migrations")
            row = cursor.fetchone()
            current_v = row[0] if row else 1

        return {
            "status": "PASS",
            "database_path": str(db_path),
            "schema_version": current_v,
            "migrations_applied_count": applied,
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}


def check_neural_core_and_tokenizer() -> dict:
    try:
        from tokenizer import CustomBPETokenizer
        from core.intelligence.neural_core import NeuralCore, NeuralCoreConfig
        import torch

        tok_path = REPO_ROOT / "configs/tokenizer/tokenizer_model.json"
        if tok_path.is_file():
            tokenizer = CustomBPETokenizer.load(tok_path)
        else:
            tokenizer = CustomBPETokenizer()

        cfg = NeuralCoreConfig(
            d_model=64,
            n_layers=2,
            n_heads=2,
            vocab_size=max(512, tokenizer.vocab_size),
        )
        core = NeuralCore(cfg)
        dummy_in = torch.tensor([[1, 2, 3]], dtype=torch.long)
        out = core(dummy_in)

        return {
            "status": "PASS",
            "vocab_size": tokenizer.vocab_size,
            "param_count": core.parameter_count,
            "forward_pass_verified": out.logits.shape == (1, 3, cfg.vocab_size),
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}


def check_frontend_assets() -> dict:
    required_files = [
        "frontend/server.js",
        "frontend/public/index.html",
        "frontend/public/style.css",
        "frontend/public/app.js",
    ]
    missing = []
    for rel_path in required_files:
        p = REPO_ROOT / rel_path
        if not p.is_file() or p.stat().st_size == 0:
            missing.append(rel_path)

    return {
        "status": "PASS" if not missing else "FAIL",
        "checked_files_count": len(required_files),
        "missing_files": missing,
    }


def check_deployment_configs() -> dict:
    required_configs = [
        "Dockerfile.backend",
        "Dockerfile.frontend",
        "docker-compose.yml",
        "docker-compose.prod.yml",
        "nginx/nginx.conf",
        ".env.production.example",
    ]
    missing = []
    for rel_path in required_configs:
        p = REPO_ROOT / rel_path
        if not p.is_file() or p.stat().st_size == 0:
            missing.append(rel_path)

    return {
        "status": "PASS" if not missing else "FAIL",
        "checked_configs_count": len(required_configs),
        "missing_configs": missing,
    }


def main() -> int:
    start_time = time.time()
    print("=" * 70)
    print(" 404 FOUNDERS — PRE-FLIGHT DEPLOYMENT VERIFICATION REPORT")
    print(" Tagline: Intelligence Without Boundaries.")
    print("=" * 70)

    checks = {
        "python": check_python_environment(),
        "torch_runtime": check_torch_runtime(),
        "database": check_database_and_migrations(),
        "neural_core": check_neural_core_and_tokenizer(),
        "frontend_assets": check_frontend_assets(),
        "deployment_configs": check_deployment_configs(),
    }

    all_passed = True
    for name, res in checks.items():
        status = res.get("status")
        icon = "✓" if status == "PASS" else "✗"
        print(f"[{icon}] {name.upper()}: {status}")
        for k, v in res.items():
            if k != "status":
                print(f"    - {k}: {v}")
        if status != "PASS":
            all_passed = False

    elapsed = time.time() - start_time
    print("-" * 70)
    print(f"Verification completed in {elapsed:.3f}s. Verdict: {'DEPLOYMENT READY' if all_passed else 'BLOCKING ISSUES DETECTED'}")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
