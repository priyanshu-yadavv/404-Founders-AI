#!/usr/bin/env python3
"""
404 FOUNDERS — Storage & I/O Benchmark CLI
Inspects storage availability across filesystems, tests sequential write/read throughput,
and verifies storage tiering quotas and checkpoint vault configuration.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from infrastructure.storage import StorageTierManager, StorageTierType


def benchmark_io(test_dir: Path, block_size_mb: int = 16, num_blocks: int = 2) -> tuple[float, float]:
    """Measures sequential write and read throughput in MB/s."""
    test_file = test_dir / ".bench_io_test.tmp"
    total_bytes = block_size_mb * num_blocks * 1024 * 1024
    payload = b"0" * (block_size_mb * 1024 * 1024)

    # Sequential write
    start_w = time.perf_counter()
    with open(test_file, "wb") as f:
        for _ in range(num_blocks):
            f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    write_time = max(time.perf_counter() - start_w, 1e-6)
    write_mb_per_s = (total_bytes / (1024 * 1024)) / write_time

    # Sequential read
    start_r = time.perf_counter()
    with open(test_file, "rb") as f:
        while f.read(1024 * 1024):
            pass
    read_time = max(time.perf_counter() - start_r, 1e-6)
    read_mb_per_s = (total_bytes / (1024 * 1024)) / read_time

    test_file.unlink(missing_ok=True)
    return write_mb_per_s, read_mb_per_s


def main() -> int:
    print("=" * 65)
    print(" 404 FOUNDERS — Storage Architecture & I/O Speed Audit")
    print("=" * 65)

    workspace = Path.cwd()
    root_stat = shutil.disk_usage("/")
    ws_stat = shutil.disk_usage(workspace)

    print(f"\n[Filesystem Capacities]")
    print(f"  Root (/)         : Free {root_stat.free / (1024**3):.2f} GB / Total {root_stat.total / (1024**3):.2f} GB")
    print(f"  Workspace ({workspace.name}) : Free {ws_stat.free / (1024**3):.2f} GB / Total {ws_stat.total / (1024**3):.2f} GB")

    print(f"\n[Local I/O Throughput Benchmark]")
    try:
        w_mb_s, r_mb_s = benchmark_io(workspace, block_size_mb=8, num_blocks=2)
        print(f"  Sequential Write : {w_mb_s:.2f} MB/s")
        print(f"  Sequential Read  : {r_mb_s:.2f} MB/s")
    except Exception as e:
        print(f"  I/O Benchmark skipped: {e}")

    print(f"\n[Storage Tiering Architecture Configuration]")
    with tempfile.TemporaryDirectory() as tmp_root:
        p_root = Path(tmp_root)
        mgr = StorageTierManager(
            hot_dir=p_root / "hot_nvme",
            warm_dir=p_root / "warm_fs",
            cold_dir=p_root / "cold_s3",
        )
        for tier in StorageTierType:
            usage = mgr.get_tier_usage(tier)
            policy = mgr.policies[tier]
            print(f"  [{policy.tier_type.value.upper()}]")
            print(f"    Capacity Limit : {policy.max_capacity_bytes / (1024**3):.1f} GB")
            print(f"    Eviction Mark  : {policy.eviction_threshold_percent}%")
            print(f"    Target Throughput: {policy.min_read_throughput_gbps} GB/s")
            print(f"    Retention Days : {policy.retention_days} days")

    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
