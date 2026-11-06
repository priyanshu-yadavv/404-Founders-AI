# 404 FOUNDERS

> **Enterprise-Grade Custom Multimodal Foundation AI & Personal Computer Intelligence Assistant**

---

## Overview

**404 FOUNDERS** is an enterprise AI ecosystem engineered to deliver:
1. **Custom Multimodal Foundation Architecture:** Engineered and trained from scratch across text, visual, and systems data.
2. **Personal Computer Intelligence Assistant:** A locally integrated, privacy-centric autonomous agent for Linux endpoints.
3. **Hybrid Edge-Cloud Fabric:** Latency-critical local inference and desktop automation orchestrated alongside large-scale distributed training on dedicated GPU clusters.

The project follows a rigorous, phase-gated engineering methodology maintained in a single unified repository (`404-FOUNDERS`).

---

## Architectural Principles

1. **Strict Phase Governance:** Development progresses sequentially through verified phases. No phase is initiated without explicit verification and review.
2. **Unified Single-Repository Model:** All models, tokenizer tools, data pipelines, agent engines, and documentation reside in this repository.
3. **Hardware-Aware Design:** Clean decoupling between local laptop capabilities (Dell Latitude 5400) and dedicated remote GPU cluster architectures.
4. **Zero-Trust Security:** Strict exclusion of `.env` files, API keys, credentials, tokens, and sensitive customer data from version control.
5. **Full Engineering Traceability:** Every decision, empirical benchmark, and system telemetry record is tracked in [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md) and [PHASE_STATUS.md](PHASE_STATUS.md).

---

## Host Hardware & Environment Baseline

Empirically inspected in **Phase 01** ([docs/phase-01-hardware-assessment.md](docs/phase-01-hardware-assessment.md)):

- **Workstation:** Dell Latitude 5400 Laptop
- **Operating System:** Kali GNU/Linux Rolling 2026.3 (Kernel `7.1.5+kali-amd64` x86_64)
- **Processor:** Intel(R) Core(TM) i5-8365U CPU @ 1.60GHz (4 physical cores, 8 logical threads, Max Turbo 4.10 GHz)
  - *Vector Extensions:* `AVX`, `AVX2`, `FMA3`, `F16C`
  - *Virtualization:* Intel VT-x enabled (`/dev/kvm` active)
- **System Memory:** 15.4 GiB Total RAM (~5.17 GiB available, 0B swap)
- **Storage:** NVMe PCIe SSD (110 GB partition, 43 GB available capacity)
- **GPU & VRAM:** Integrated Intel UHD Graphics 620 (Shared UMA memory, 0 dedicated VRAM, no NVIDIA/CUDA)
- **Networking:** Intel I219-LM 1 Gbps Gigabit Ethernet + Intel Wireless-AC 9560 Wi-Fi 5 / Bluetooth 5.0
- **Base Toolchains:** Python `3.14.8`, pip `26.1.2`, GCC `16.2.0`, G++ `16.2.0`, Node.js `v24.21.0`, npm `12.2.0`, Git `2.53.0`

---

## Compute Allocation & GPU Cluster Strategy

### Local Laptop Scope (Dell Latitude 5400)
- Core neural architecture prototyping & autograd shape verification (1M–15M parameter models).
- Tokenizer vocabulary engineering & training (BPE/WordPiece).
- Streaming dataset preprocessing, sanitization, and token packing.
- Local personal AI agent orchestration & system automation.
- Quantized CPU inference (1B–3B models at 4-bit quantization, ~10–18 tokens/sec via AVX2).

### Dedicated GPU Cluster Infrastructure (For Foundation Pretraining)
- **Scenario A (Entry-Level Development):** 4x–8x NVIDIA RTX 4090 24GB (96–192 GB VRAM, 128–256 GB RAM, ~$1.20–$2.50/hr).
- **Scenario B (Professional Research):** 8x NVIDIA H100 SXM5 80GB (640 GB VRAM, 1.5–2.0 TB RAM, 400G InfiniBand, ~$20–$30/hr).
- **Scenario C (Enterprise Multimodal Pretraining):** 32x–64x NVIDIA H100/H200 SXM5 (2.5–9.0 TB VRAM, 3.2 Tbps InfiniBand fabric, 500TB+ parallel storage, ~$80–$180/hr).

For comprehensive technical specifications and cost analyses, see [`docs/phase-01-hardware-assessment.md`](docs/phase-01-hardware-assessment.md).

---

## Repository Structure

```
.
├── .gitignore                          # Security and build exclusions
├── README.md                           # Project blueprint and environment overview
├── PHASE_STATUS.md                     # Governance matrix and phase tracking
├── DEVELOPMENT_LOG.md                  # Detailed chronological engineering log
├── CHANGELOG.md                        # Versioned phase releases
└── docs/
    └── phase-01-hardware-assessment.md # Comprehensive hardware & cluster report
```

---

## Development Roadmap

| Phase | Phase Name | Status |
|---|---|---|
| **Phase 01** | **Environment & Hardware Assessment** | **Review Pending** |
| Phase 02 | Core Neural Architecture & Tokenizer Design | Planned |
| Phase 03 | Configuration Framework & Data Streaming Pipeline | Planned |
| Phase 04 | AI Model Prototyping & Distributed Training Harness | Planned |
| Phase 05 | Personal AI Assistant Core & Agent Framework | Planned |
| Phase 06 | API Services & Client Interface | Planned |
| Phase 07 | Testing, Verification & Performance Benchmarking | Planned |
| Phase 08 | Production Deployment & Hybrid Cluster CI/CD | Planned |

---

## Git & Security Governance

- **Branching Policy:** All development lives on `main`. No separate repositories for individual phases.
- **Commit Format:** `phase-XX: <description>` (e.g. `phase-01: complete environment and hardware assessment`).
- **No Force Push:** `git push --force` is strictly prohibited.
- **Zero Secrets:** No passwords, tokens, private keys, or `.env` files are ever committed.
