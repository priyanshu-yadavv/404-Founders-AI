"""
404 FOUNDERS — Infrastructure & Training Configuration Tests
Validates YAML schemas, accelerator definitions, FSDP rules, and environment specifications.
"""

from __future__ import annotations

from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_cluster_tier_configs_exist_and_parse() -> None:
    """Verify Tier A, B, and C YAML configs parse cleanly and contain required keys."""
    tier_files = [
        "configs/infrastructure/cluster_tier_a_dev.yaml",
        "configs/infrastructure/cluster_tier_b_research.yaml",
        "configs/infrastructure/cluster_tier_c_training.yaml",
    ]

    for rel_path in tier_files:
        cfg_file = REPO_ROOT / rel_path
        assert cfg_file.is_file(), f"Missing config file: {rel_path}"
        with open(cfg_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert "tier" in data
        assert "accelerators" in data
        assert "storage" in data
        assert data["accelerators"]["gpu_count"] >= 1


def test_fsdp_config_structure() -> None:
    """Verify PyTorch FSDP configuration keys and sharding strategy."""
    fsdp_file = REPO_ROOT / "configs/training/fsdp_config.yaml"
    assert fsdp_file.is_file()

    with open(fsdp_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["fsdp"]["sharding_strategy"] in ("FULL_SHARD", "SHARD_GRAD_OP", "NO_SHARD")
    assert data["mixed_precision"]["param_dtype"] == "bfloat16"
    assert data["activation_checkpointing"]["enabled"] is True
    assert data["state_dict_config"]["state_dict_type"] == "SHARDED_STATE_DICT"


def test_distributed_mesh_config() -> None:
    """Verify distributed device mesh dimensions multiply to total_gpus."""
    mesh_file = REPO_ROOT / "configs/training/distributed_mesh.yaml"
    assert mesh_file.is_file()

    with open(mesh_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    mesh = data["device_mesh"]
    total = mesh["total_gpus"]
    shape = mesh["mesh_shape"]

    product = 1
    for dim in shape:
        product *= dim
    assert product == total, f"Mesh shape {shape} product {product} != total_gpus {total}"
    assert data["communication"]["gpu_backend"] == "nccl"


def test_environments_specs() -> None:
    """Verify PyTorch and JAX environment configuration schemas."""
    pytorch_env_file = REPO_ROOT / "configs/environments/pytorch_cuda_env.yaml"
    jax_env_file = REPO_ROOT / "configs/environments/jax_cluster_env.yaml"

    assert pytorch_env_file.is_file()
    assert jax_env_file.is_file()

    with open(pytorch_env_file, "r", encoding="utf-8") as f:
        pt_data = yaml.safe_load(f)
    assert "runtime_matrix" in pt_data
    assert pt_data["runtime_matrix"]["cuda_version"].startswith("12.")

    with open(jax_env_file, "r", encoding="utf-8") as f:
        jax_data = yaml.safe_load(f)
    assert "xla_flags" in jax_data
    assert len(jax_data["xla_flags"]) > 0
