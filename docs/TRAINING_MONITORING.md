# 404 FOUNDERS — Training Monitoring & Telemetry Specification

**Document ID:** `DOC-TRAIN-005`  
**Phase:** Phase 06 Baseline  
**Authors:** Deep Learning Operations Engineer & Infrastructure Architect  

---

## 1. Overview & Privacy Controls

Pretraining tracking requires fine-grained operational visibility into loss convergence, throughput, gradient norms, and hardware resource saturation.
To protect developer privacy and system security:
- **No Secret Leakage:** Prompts, private credentials, and raw dataset contents are never logged.
- **Air-Gapped Logging:** All telemetry is captured in offline machine-readable JSONL streams (`metrics.jsonl`) without external telemetry network beacons.

---

## 2. Telemetry Invariants & Schema

At each logged training step, the `TrainingMonitor` (`training/monitoring/training_monitor.py`) captures:

```json
{
  "step": 15,
  "timestamp": "2026-11-06T17:19:17.822578+00:00",
  "train_loss": 6.17334,
  "perplexity": 480.02,
  "token_accuracy": 0.0425,
  "learning_rate": 0.0003,
  "grad_norm": 2.8614,
  "batch_tokens": 128,
  "total_tokens": 1920,
  "tokens_per_second": 5817.0,
  "step_duration_ms": 22.0,
  "cpu_percent": 0.0,
  "ram_used_gb": 0.33,
  "val_loss": 6.2314,
  "val_perplexity": 508.45
}
```

---

## 3. Metrics Definitions

### 3.1 Step Throughput
Measured empirically as:
$$\text{Tokens / Second} = \frac{\text{Valid Tokens in Batch}}{\Delta t_{\text{step}}}$$
$$\text{Step Latency (ms)} = \Delta t_{\text{step}} \times 1000$$

### 3.2 Gradient Norm
Total $L_2$ norm across all trainable parameter gradients:
$$||\nabla_\theta||_2 = \sqrt{\sum_{p \in \Theta} ||\nabla_p||_2^2}$$
Monitored to detect vanishing gradients ($||\nabla_\theta|| \to 0$) or exploding gradients ($||\nabla_\theta|| \to \infty$).

### 3.3 Hardware Consumption
- **Resident Set Size (RSS):** Tracked via Linux kernel `getrusage(RUSAGE_SELF).ru_maxrss` to continuously monitor workstation RAM usage.
- **VRAM Utilization:** Tracked via `torch.cuda.memory_allocated()` when running on GPU clusters.

---

## 4. Console Format Summary

For interactive terminal runs, the monitor outputs formatted single-line summaries:
```text
[Step 00010] loss: 6.2448 | acc: 4.2% | lr: 3.38e-04 | grad: 2.86 | tok/s: 1581.4 | mem: 0.33GB | val_loss: 6.2314 (ppl: 508.45)
```
