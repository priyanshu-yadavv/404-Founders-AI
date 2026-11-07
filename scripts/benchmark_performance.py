#!/usr/bin/env python3
"""
404 FOUNDERS — Performance Benchmarking & Profiling Suite
Empirically measures and records:
1. End-to-end REST API endpoint response latencies (min, avg, p50, p95, p99).
2. Neural core inference latency and CPU generation throughput (tokens/sec).
3. Memory consumption (RSS MB) before, during, and after forward passes.
4. SQLite database query execution times under Migration Level 2 indexed schemas.
Outputs structured JSON results to benchmarks/performance_results.json.
"""

from __future__ import annotations

import gc
import json
import os
import resource
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import torch
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from api.rest.app import create_app, initialize_runtime_services
from core.conversation_manager import ConversationManager
from database.connection import DatabaseManager
from security.auth import AuthManager


def get_rss_memory_mb() -> float:
    """Returns current process Resident Set Size (RSS) in Megabytes."""
    rusage = resource.getrusage(resource.RUSAGE_SELF)
    # On Linux, ru_maxrss is in kilobytes
    return rusage.ru_maxrss / 1024.0


def calculate_percentiles(latencies_ms: List[float]) -> Dict[str, float]:
    """Calculates min, avg, p50, p95, p99, and max from a list of latencies in ms."""
    if not latencies_ms:
        return {"min_ms": 0.0, "avg_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "max_ms": 0.0}
    sorted_l = sorted(latencies_ms)
    n = len(sorted_l)
    return {
        "min_ms": round(sorted_l[0], 3),
        "avg_ms": round(statistics.mean(sorted_l), 3),
        "p50_ms": round(statistics.median(sorted_l), 3),
        "p95_ms": round(sorted_l[int(n * 0.95)] if n > 1 else sorted_l[-1], 3),
        "p99_ms": round(sorted_l[int(n * 0.99)] if n > 1 else sorted_l[-1], 3),
        "max_ms": round(sorted_l[-1], 3),
    }


def benchmark_api_endpoints(client: TestClient, iterations: int = 50) -> Dict[str, Any]:
    """Benchmark key REST API endpoints for response latency."""
    print(f"\n[1/3] Benchmarking REST API Latencies ({iterations} iterations per endpoint)...")
    results = {}

    endpoints = [
        ("GET /health", lambda: client.get("/health")),
        ("GET /api/v1/system/telemetry", lambda: client.get("/api/v1/system/telemetry")),
        ("POST /api/v1/tokenizer/encode", lambda: client.post("/api/v1/tokenizer/encode", json={"text": "Intelligence Without Boundaries 404 FOUNDERS"})),
        ("POST /api/v1/neural/generate", lambda: client.post("/api/v1/neural/generate", json={"prompt": "Architecture test", "max_new_tokens": 10})),
        ("POST /api/v1/intelligence/query", lambda: client.post("/api/v1/intelligence/query", json={"query": "Calculate factorial of 5", "context_hints": {}})),
    ]

    for label, call_fn in endpoints:
        latencies = []
        # Warmup call
        try:
            resp = call_fn()
            assert resp.status_code in (200, 201), f"Unexpected status {resp.status_code}: {resp.text}"
        except Exception as e:
            print(f"  Warmup failed for {label}: {e}")
            results[label] = {"error": str(e)}
            continue

        for _ in range(iterations):
            start = time.perf_counter()
            resp = call_fn()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latencies.append(elapsed_ms)

        stats = calculate_percentiles(latencies)
        results[label] = {
            "iterations": iterations,
            **stats,
        }
        print(f"  ✓ {label:<35} | avg: {stats['avg_ms']:>6.2f} ms | p50: {stats['p50_ms']:>6.2f} ms | p95: {stats['p95_ms']:>6.2f} ms | max: {stats['max_ms']:>6.2f} ms")

    return results


def benchmark_neural_inference(services: Dict[str, Any], runs: int = 30) -> Dict[str, Any]:
    """Benchmark neural core forward pass latency, generation speed, and memory usage."""
    print("\n[2/3] Benchmarking Neural Core Inference & Memory...")
    neural_model = services["neural_model"]
    neural_model.eval()

    initial_rss = get_rss_memory_mb()
    gc.collect()

    seq_lengths = [32, 64, 128]
    forward_results = {}

    for seq_len in seq_lengths:
        latencies = []
        dummy_input = torch.randint(0, neural_model.config.vocab_size, (1, seq_len), dtype=torch.long)
        
        # Warmup
        with torch.no_grad():
            _ = neural_model(dummy_input)

        for _ in range(runs):
            t0 = time.perf_counter()
            with torch.no_grad():
                _ = neural_model(dummy_input)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)

        stats = calculate_percentiles(latencies)
        forward_results[f"seq_len_{seq_len}"] = stats
        print(f"  ✓ Forward Pass (seq_len={seq_len:<3})        | avg: {stats['avg_ms']:>6.2f} ms | p50: {stats['p50_ms']:>6.2f} ms | p95: {stats['p95_ms']:>6.2f} ms")

    # Generation Throughput
    inference_engine = services["inference_engine"]
    tokenizer = services["tokenizer"]
    prompt_res = tokenizer.encode("Autonomous intelligent system benchmark")
    prompt_ids = prompt_res.ids if hasattr(prompt_res, "ids") else [1, 2, 3]

    gen_tokens = 20
    gen_latencies = []
    
    # Warmup
    _ = inference_engine.generate_greedy_tokens(prompt_ids=prompt_ids, max_new_tokens=5)

    for _ in range(10):
        t0 = time.perf_counter()
        _ = inference_engine.generate_greedy_tokens(prompt_ids=prompt_ids, max_new_tokens=gen_tokens)
        elapsed_sec = time.perf_counter() - t0
        gen_latencies.append(elapsed_sec)

    avg_gen_time = statistics.mean(gen_latencies)
    tokens_per_sec = gen_tokens / avg_gen_time if avg_gen_time > 0 else 0.0
    peak_rss = get_rss_memory_mb()

    print(f"  ✓ Autoregressive Generation ({gen_tokens} tokens) | avg time: {avg_gen_time*1000:>6.2f} ms | throughput: {tokens_per_sec:>6.2f} tokens/sec")
    print(f"  ✓ Memory RSS: baseline={initial_rss:.2f} MB, peak={peak_rss:.2f} MB, delta={peak_rss - initial_rss:.2f} MB")

    return {
        "forward_pass_latencies": forward_results,
        "generation_tokens": gen_tokens,
        "avg_generation_time_ms": round(avg_gen_time * 1000.0, 3),
        "throughput_tokens_per_sec": round(tokens_per_sec, 2),
        "initial_rss_mb": round(initial_rss, 2),
        "peak_rss_mb": round(peak_rss, 2),
        "memory_delta_mb": round(peak_rss - initial_rss, 2),
    }


def benchmark_database_performance(db_mgr: DatabaseManager) -> Dict[str, Any]:
    """Benchmark SQLite database operations under indexed schema."""
    print("\n[3/3] Benchmarking SQLite Database & Index Performance...")
    conv_mgr = ConversationManager(db_mgr)
    auth_mgr = AuthManager(db_mgr)

    # Setup benchmark user
    bench_user = auth_mgr.get_user_by_username("benchmark_user")
    if not bench_user:
        bench_user = auth_mgr.register_user("benchmark_user", "bench@test.local", "BenchPassword123!")

    # 1. Thread creation
    t0 = time.perf_counter()
    thread = conv_mgr.create_thread(bench_user.id, title="Performance Benchmark Thread")
    thread_creation_ms = (time.perf_counter() - t0) * 1000.0

    # 2. Bulk Message Insertion (500 items)
    num_messages = 500
    insert_latencies = []
    t_bulk_start = time.perf_counter()
    for i in range(num_messages):
        t0 = time.perf_counter()
        conv_mgr.add_message(
            conversation_id=thread.id,
            sender="user" if i % 2 == 0 else "assistant",
            content=f"Benchmark message payload {i} for latency profiling.",
        )
        insert_latencies.append((time.perf_counter() - t0) * 1000.0)
    total_bulk_insert_ms = (time.perf_counter() - t_bulk_start) * 1000.0
    insert_stats = calculate_percentiles(insert_latencies)

    # 3. Indexed Query (fetch all messages for thread)
    query_latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        msgs = conv_mgr.list_messages(conversation_id=thread.id, limit=600)
        query_latencies.append((time.perf_counter() - t0) * 1000.0)
    query_stats = calculate_percentiles(query_latencies)

    # 4. Cleanup benchmark thread
    conv_mgr.delete_thread(thread.id, bench_user.id)

    print(f"  ✓ Thread Creation Latency                 | {thread_creation_ms:>6.2f} ms")
    print(f"  ✓ Bulk Insert (500 messages total)        | {total_bulk_insert_ms:>6.2f} ms total | avg/msg: {insert_stats['avg_ms']:>6.2f} ms | p95: {insert_stats['p95_ms']:>6.2f} ms")
    print(f"  ✓ Indexed Thread Retrieval (500 items)    | avg: {query_stats['avg_ms']:>6.2f} ms | p50: {query_stats['p50_ms']:>6.2f} ms | p95: {query_stats['p95_ms']:>6.2f} ms")

    return {
        "thread_creation_ms": round(thread_creation_ms, 3),
        "bulk_insert_500_messages": {
            "total_duration_ms": round(total_bulk_insert_ms, 3),
            **insert_stats,
        },
        "indexed_thread_retrieval_500_items": query_stats,
    }


def main():
    print("=" * 70)
    print("404 FOUNDERS — PHASE 12 PERFORMANCE & BENCHMARKING ENGINE")
    print("=" * 70)

    services = initialize_runtime_services()
    app = create_app(services=services)
    client = TestClient(app)

    db_mgr = services["db_manager"]

    api_results = benchmark_api_endpoints(client, iterations=50)
    neural_results = benchmark_neural_inference(services, runs=30)
    db_results = benchmark_database_performance(db_mgr)

    final_report = {
        "phase": "Phase 12 — Testing, Optimization & Release",
        "timestamp_epoch": time.time(),
        "environment": {
            "os": sys.platform,
            "python_version": sys.version.split()[0],
            "torch_version": torch.__version__,
            "cpu_cores": os.cpu_count(),
        },
        "api_benchmarks": api_results,
        "neural_inference_benchmarks": neural_results,
        "database_benchmarks": db_results,
    }

    out_file = REPO_ROOT / "benchmarks/performance_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)

    print("\n" + "=" * 70)
    print(f"✓ Performance benchmarks successfully completed and recorded to:")
    print(f"  {out_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
