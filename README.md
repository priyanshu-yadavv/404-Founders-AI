# 404 FOUNDERS

> **Intelligence Without Boundaries**  
> *Enterprise-Grade Custom Multimodal Foundation AI & Personal Operating Intelligence System*

---

## 1. Project Overview

**404 FOUNDERS** is an enterprise AI ecosystem engineered around:
1. **Custom Multimodal Foundation Architecture:** Built from scratch with **zero pretrained model weights**, featuring a hybrid hierarchical Transformer backbone, sparse Mixture-of-Experts (MoE), multi-mechanism attention, and an independent character-level Custom BPE tokenizer.
2. **Personal Operating Intelligence System:** An autonomous resident copilot for Linux (Kali/Debian) and Windows endpoints, capable of deep systems analysis, defensive cybersecurity, repository intelligence, and workflow automation.

The system operates across two core modes:
- **General Intelligence Mode:** Multi-step reasoning, mathematical theorem proving, scientific research, code synthesis, and unified cross-modal semantic understanding.
- **Personal AI Mode:** Host operating system analysis, hardware telemetry, repository intelligence, defensive vulnerability audits, network diagnostics, task automation, and episodic memory.

---

## 2. Finalized Architectural Decisions

- **Custom Neural Architecture:** Designed from first principles; zero pretrained open-weights.
- **Random Initialization:** All model parameter tensors are initialized from scratch using scaled Gaussian distributions ($\mathcal{N}(0, 1/d_{\text{in}})$).
- **Custom Character-Level BPE Tokenizer:** Native subword BPE avoiding 3-byte fragmentation for Hindi and multilingual text.
- **Unified Multimodal Foundation Model:** Shared latent space across Text, Vision, Audio, Video, and Documents.
- **Hybrid Modular & Hierarchical Backbone:** Hierarchical Transformer blocks with sparse Mixture-of-Experts (MoE).
- **Hybrid Multi-Mechanism Attention (MMA):** Fuses sliding-window local attention, global anchor tokens, and Grouped-Query Attention (GQA).
- **Advanced Multi-Layer Memory:** In-context KV-cache, episodic execution logs, persistent vector stores, factual knowledge graphs, and background consolidation.
- **Hybrid Intelligent Routing:** Dynamic task-directed routing between general reasoning and personal AI tools.
- **Multi-Framework Decoupling:** Strict separation between PyTorch and JAX behind abstract interfaces (`neural_architecture/interfaces.py`).
- **Targeted Polyglot Design:** Python for orchestration and ML core; C++, CUDA, and Rust reserved for performance-critical kernels and tokenization.
- **Tri-Protocol API Gateway:** High-performance REST (FastAPI), real-time bidirectional WebSocket, and binary gRPC.
- **Hybrid Edge-Cloud Infrastructure:** Local laptop execution (Dell Latitude 5400) for agent automation, prototyping, and quantized inference; dedicated high-performance GPU cluster (NVIDIA H100/H200) for large-scale pretraining.

---

## 3. Repository Structure

```
404-FOUNDERS/
├── .env.example              # Environment variable configuration template
├── .gitignore                # Security, Python, Node, weight, and OS exclusions
├── pyproject.toml            # Python build specifications, dependencies, and tool settings
├── README.md                 # Project architecture blueprint and quickstart
├── PHASE_STATUS.md           # Phase governance matrix and gating criteria
├── DEVELOPMENT_LOG.md        # Chronological engineering decision log
├── CHANGELOG.md              # Versioned phase releases (Keep a Changelog)
│
├── core/                     # Foundational orchestration, reasoning & configuration
│   ├── intelligence/         # High-level cognitive synthesis & NeuralCore
│   ├── reasoning/            # Symbolic, math, and deductive reasoning
│   ├── attention/            # Multi-mechanism attention primitives (Global, Sparse, Hierarchical, Fusion)
│   ├── routing/              # Mixture-of-Experts and task routing (Rule-based, Learned, Dynamic)
│   ├── context/              # Infinite-context state tracking
│   └── orchestration/        # Lifecycle coordination and telemetry
│
├── neural_architecture/      # Custom neural topology & framework abstractions
│   ├── interfaces.py         # Framework-agnostic backend engine contracts
│   ├── inference.py          # Autoregressive generation & numerical validation harness
│   ├── jax_interface.py      # Separated functional JAX model interfaces
│   ├── layers/               # Custom layers (RMSNorm, RoPE, SwiGLU, Projections, Residuals)
│   ├── modules/              # Hierarchical Transformer blocks & specialized experts
│   ├── encoders/             # Modality-specific projection layers
│   ├── decoders/             # Autoregressive generation heads
│   ├── fusion/               # Cross-attention & multimodal gating
│   └── research/             # Micro-prototypes and experimental modules
│
├── tokenizer/                # Custom BPE tokenizer engine (non-byte-level)
│   ├── bpe_tokenizer.py      # CustomBPETokenizer unified model interface
│   ├── bpe_trainer.py        # Pair frequency calculation & merge generation
│   ├── config.py             # Hyperparameters & whitespace configuration
│   ├── normalization.py      # Non-destructive Unicode NFC/NFKC normalizer
│   ├── pre_tokenizer.py      # Code operators, Indic scripts, ' ' whitespace
│   ├── encoder.py            # Priority-ranked subword BPE encoder
│   ├── decoder.py            # Exact round-trip detokenizer
│   ├── special_tokens.py     # 25-token isolated special tokens registry
│   ├── serialization.py      # Model JSON & vocab/merges exporter
│   ├── evaluation/           # Compression ratio & fertility benchmark
│   ├── training/             # Training subpackage initializers
│   └── vocabulary/           # Bi-directional token-to-ID mapping
│
├── memory/                   # Multi-layer cognitive memory fabric
│   ├── short_term/           # Working memory & attention KV-cache
│   ├── long_term/            # Semantic vector persistence
│   ├── knowledge/            # Structured factual knowledge graphs
│   ├── episodic/             # Action logs and user interaction trajectories
│   ├── retrieval/            # Hybrid sparse-dense (BM25 + ANN) search
│   └── consolidation/        # Background distillation and salience decay
│
├── multimodal/               # Modality-specific ingestion pipelines
│   ├── text/                 # Text & source code normalization
│   ├── vision/               # High-resolution patch extraction
│   ├── audio/                # Log-mel spectrogram feature extraction
│   ├── video/                # Spatiotemporal 3D patch tubelets
│   └── documents/            # Document layout & coordinate parsing
│
├── training/                 # Distributed training orchestration & dataset pipeline
│   ├── datasets/             # Governed dataset preparation pipeline
│   │   ├── ingestion/        # Ingestors across 9 data domains
│   │   ├── validation/       # Format, encoding, schema, corrupted line audits
│   │   ├── cleaning/         # Sanitization, quality & language heuristics
│   │   ├── deduplication/    # Exact SHA-256 + 32-perm MinHash near-dedup
│   │   ├── governance/       # License whitelist compliance & PII redaction
│   │   ├── splitting/        # Zero-leakage deterministic hash partitioning
│   │   ├── manifests/        # Immutable JSON cryptographic manifests
│   │   └── statistics/       # Corpus metrics & Markdown table reports
│   ├── preprocessing/        # Chunked binary shard packing
│   ├── experiments/          # Metric tracking & manifests
│   ├── checkpoints/          # Atomic checkpoint persistence
│   └── evaluation/           # Benchmark suites & perplexity evaluation
│
├── personal_ai/              # Endpoint intelligence & desktop assistance
│   ├── system_monitor/       # Read-only CPU, RAM, NVMe telemetry
│   ├── coding_assistant/     # AST analysis, diff review, git automation
│   ├── cybersecurity/        # Port auditing, socket check, anomaly detection
│   ├── network_analysis/     # Latency, DNS, and interface diagnostics
│   └── automation/           # Pre-approved task automation scripts
│
├── agent/                    # Autonomous planning & execution guardrails
│   ├── planner/              # Hierarchical goal decomposition (ReAct)
│   ├── tools/                # Permission-controlled tool registry
│   ├── permissions/          # 4-tier security validation engine
│   └── execution/            # Sandboxed subprocess runner
│
├── api/                      # Tri-protocol communication gateway
│   ├── rest/                 # FastAPI REST controllers
│   ├── websocket/            # Real-time token & event streaming
│   └── grpc/                 # High-throughput binary RPC services
│
├── infrastructure/           # Multi-tier deployment definitions
│   ├── local/                # Workstation constraints & memory budgeting
│   ├── cloud/                # Cloud pricing profiles & hybrid workload router
│   ├── gpu_cluster/          # Tier A/B/C cluster configs & rail-optimized topology
│   ├── distributed/          # 4D parallelism, gradient sync & atomic checkpointing
│   ├── storage/              # Hot/Warm/Cold tiering & Checkpoint Vault
│   ├── containers/           # Dockerfiles & Slurm SBATCH job submission generators
│   ├── monitoring/           # DCGM metrics, MFU calculator & air-gapped tracker
│   ├── security/             # Zero-trust RBAC, Ed25519 SSH validator & secret redaction
│   └── deployment/           # Systemd user services & container manifests
│
├── database/                 # SQLite & DuckDB analytical storage
├── security/                 # Zero-trust policy, audit logger & sanitization
├── configs/                  # YAML system configurations, tokenizer & cluster tiers
├── frontend/                 # Client interfaces (React / Next.js / Tauri)
├── scripts/                  # Developer CLI tools (system, gpu, env, storage, tokenizer, training, intelligence)
├── tests/                    # 270 automated tests covering all subsystems
└── docs/                     # 48 exhaustive technical architecture manuals
```

---

## 4. Core AI Foundation Architecture (Phase 03)

The central neural engine (`NeuralCore`) coordinates multi-stage hierarchical processing with full autograd gradient support:

```mermaid
flowchart TD
    Tokens["Input Token IDs: (Batch B, SeqLen T)"] --> InProj["InputProjectionLayer<br/>Embedding / Linear Projector"]

    subgraph STACK ["Hierarchical Transformer Stack (L = 1 .. Layers)"]
        H1["HierarchicalTransformerBlock 1<br/>- Pre-RMSNorm<br/>- AttentionFusionController (Global + Sparse + Hierarchical)<br/>- LayerScale Residual Connection<br/>- Pre-RMSNorm<br/>- Gated SwiGLU Feedforward<br/>- LayerScale Residual Connection"]
        H2["HierarchicalTransformerBlock 2"]
        H1 --> H2
    end

    InProj --> H1

    subgraph ROUTING ["Neural Routing & Specialized Experts"]
        Router["DynamicRouter (Rule-Based + Learned Top-K)"]
        Exp0["General Reasoning Expert (SwiGLU)"]
        Exp1["Personal AI System Expert (SwiGLU)"]
        
        H2 --> Router
        Router -->|Route to Expert 0| Exp0
        Router -->|Route to Expert 1| Exp1
        Exp0 --> ExpMerge["Expert Residual Merge (+)"]
        Exp1 --> ExpMerge
        H2 --> ExpMerge
    end

    ExpMerge --> FinalNorm["CustomRMSNorm (d_model)"]
    FinalNorm --> OutProj["OutputProjectionLayer<br/>(d_model -> vocab_size)"]
    OutProj --> Logits["Output Logits Tensor (B, T, vocab_size)"]
```

---

## 5. Custom BPE Tokenizer & Data Pipeline (Phase 04)

```mermaid
flowchart LR
    Raw["Raw Text & Datasets"] --> Ingest["DatasetIngestor"]
    Ingest --> Val["DataValidator"]
    Val --> Clean["DataCleaner"]
    Clean --> Dedup["Deduplicator<br/>(SHA-256 + MinHash)"]
    Dedup --> Gov["DataGovernanceEngine<br/>(License + PII Redaction)"]
    Gov --> Split["DatasetSplitter<br/>(Zero-Leakage Hash Split)"]
    Split --> TrainShard["Train Shards (80%)"]
    Split --> ValShard["Val Shards (10%)"]
    Split --> TestShard["Test Shards (10%)"]
    
    TrainShard --> BPE["CustomBPETokenizer<br/>Character-level BPE"]
    BPE --> EncDec["Subword Token IDs<br/>Exact Round-Trip Detokenization"]
```

### Key Tokenizer Properties
- **Non-Byte-Level BPE:** Operates at the character and grapheme level, preventing 3-byte fragmentation for Hindi, Sanskrit, and Indic languages.
- **Lossless Whitespace:** Spaces explicitly mapped to ` ` (`\u2581`), guaranteeing exact string reconstruction.
- **25 Special Control Tokens:** Segregated IDs `0` through `24` matching atomically (`<pad>`, `<unk>`, `<bos>`, `<eos>`, `<sys_start>`, `<user_start>`, `<asst_start>`, `<thought>`, `<tool_call>`, etc.).
- **Deterministic Splitting:** Content-hashed partitioning ($\text{SHA256}(x) \pmod{1000}$) guarantees 0% cross-split data leakage.

---

## 6. Training Infrastructure & GPU Cluster Architecture (Phase 05)

The infrastructure decouples local workstation prototyping (Dell Latitude 5400, Kali Linux, Intel i5-8365U, 15.4 GB RAM, 0B swap, Intel UHD 620 UMA) from cloud and dedicated GPU cluster training:

```mermaid
graph TD
    subgraph Local_Workstation ["Local Development (Dell Latitude 5400)"]
        LW1[Local CPU Runtime] --> LW2[Unit & Regression Tests]
        LW1 --> LW3[CPU Tokenizer Verification]
        LW1 --> LW4[Safe Memory Budget: 60% Free RAM]
    end

    subgraph Hybrid_Router ["Hybrid Workload Router"]
        Router[HybridWorkloadRouter]
    end

    subgraph Cluster_Tiers ["Dedicated GPU Cluster Infrastructure"]
        TA["Tier A: Prototyping (1-2x RTX 4090 / L40S PCIe 4.0)"]
        TB["Tier B: Research (1 Node x 8x H100 80GB SXM5 NVLink 4)"]
        TC["Tier C: Foundation Supercluster (8 Nodes x 64x H100/H200 SXM5 3.2 Tbps InfiniBand NDR)"]
    end

    Local_Workstation --> Router
    Router --> TA
    Router --> TB
    Router --> TC
```

### Cluster Tier Specifications
- **Tier A (Development):** 1-2x NVIDIA RTX 4090 24GB or L40S 48GB PCIe Gen 4.0 x16. For module unit verification, synthetic convergence checks, and subword tokenizer evaluation.
- **Tier B (Research):** 1 Node x 8x NVIDIA H100 80GB SXM5 (640 GB VRAM), 4th-Gen NVLink (900 GB/s) + NVSwitch mesh (7.2 TB/s). For attention scaling benchmarks and 1B–7B parameter research models.
- **Tier C (Foundation Supercluster):** 8 Nodes x 8 = 64x NVIDIA H100/H200 SXM5 (5,120 GB VRAM total), NVLink 4 intra-node + 8-way Rail-Optimized InfiniBand NDR 400 Gbps (3.2 Tbps/node). For full-scale foundation pretraining from random initialization across multi-trillion tokens.

### Multi-Tier Storage Hierarchy & Checkpoint Vault
- **Hot Scratch:** Direct-Attached PCIe 5.0 NVMe (15 TB/node, >30 GB/s read, >1M IOPS) with LRU cache eviction at 80% capacity.
- **Warm Shared:** High-speed parallel filesystem (Lustre / WEKA, 500 TB, >100 GB/s throughput) hosting tokenized dataset shards and rolling checkpoints.
- **Cold Vault:** Immutable S3 / Ceph object storage (2 PB, 11 9s durability) preserving milestone checkpoints with SHA-256 verification and read-only locks (`0444`).

---

## 7. Technical Documentation Index

Complete architectural specifications are maintained in [`docs/`](docs/):

### Training Infrastructure & GPU Computing (Phase 05)
1. [**GPU Cluster Architecture**](docs/GPU_CLUSTER_ARCHITECTURE.md) (`DOC-INFRA-001`): Tier A/B/C cluster hardware, rail-optimized InfiniBand NDR fabric, and hardware comparison matrix.
2. [**Distributed Training Architecture**](docs/DISTRIBUTED_TRAINING.md) (`DOC-INFRA-002`): 4D Parallelism ($DP \times TP \times PP \times SP$), FSDP/ZeRO-3, gradient overlap, and fault recovery.
3. [**PyTorch & JAX Infrastructure**](docs/PYTORCH_JAX_INFRASTRUCTURE.md) (`DOC-INFRA-003`): Dual-framework strategy, XLA compilation, FSDP sharding, and bidirectional checkpoint translation.
4. [**CUDA & Hardware Compatibility**](docs/CUDA_COMPATIBILITY.md) (`DOC-INFRA-004`): CUDA 12.4, cuDNN 9.1, NCCL 2.21, Hopper/Ada architecture features, and BF16/FP8 precision policies.
5. [**Storage Architecture & Vault**](docs/STORAGE_ARCHITECTURE.md) (`DOC-INFRA-005`): Hot NVMe scratch, Warm parallel filesystem, Cold object storage, and atomic Checkpoint Vault persistence.
6. [**Infrastructure Security**](docs/INFRASTRUCTURE_SECURITY.md) (`DOC-INFRA-006`): Zero-trust RBAC, Ed25519 SSH enforcement, automated regex credential masking, and audit trails.
7. [**Training Compute Estimation**](docs/TRAINING_COMPUTE_ESTIMATION.md) (`DOC-INFRA-007`): Chinchilla compute laws ($C = 6ND$), token budgets, empirical MFU factors, and duration calculations.
8. [**Infrastructure Cost Analysis**](docs/INFRASTRUCTURE_COST_ANALYSIS.md) (`DOC-INFRA-008`): Reference market pricing (Lambda, RunPod, CoreWeave, AWS), cost-per-run models, and spot optimization.

### Tokenizer & Data Pipeline Architecture (Phase 04)
9. [**Custom BPE Tokenizer**](docs/CUSTOM_BPE_TOKENIZER.md) (`DOC-TOK-001`): Character-level BPE architecture, whitespace handling, and special token registry.
10. [**Tokenizer Training**](docs/TOKENIZER_TRAINING.md) (`DOC-TOK-002`): BPE merge mathematics, pair frequencies, deterministic tie-breaking, and scaling.
11. [**Multilingual Tokenization**](docs/MULTILINGUAL_TOKENIZATION.md) (`DOC-TOK-003`): Devanagari conjuncts, code syntax, mathematical expressions, and fertility metrics.
12. [**Data Pipeline Architecture**](docs/DATA_PIPELINE.md) (`DOC-DATA-001`): Ingestion, validation, cleaning, MinHash deduplication, and hash-partitioned splits.
13. [**Data Governance & Security**](docs/DATA_GOVERNANCE.md) (`DOC-DATA-002`): Provenance tracking, PII/secret regex scanning, canonical redaction, and access control.
14. [**Dataset License Policy**](docs/DATASET_LICENSE_POLICY.md) (`DOC-DATA-003`): Whitelist of approved open licenses, copyleft prohibitions, and copyright compliance.

### Core AI Foundation (Phase 03)
15. [**Core AI Foundation**](docs/CORE_AI_FOUNDATION.md) (`DOC-CORE-001`): Central neural core, custom layers, tensor shape conventions, and inference engine.
16. [**Custom Attention Design**](docs/CUSTOM_ATTENTION_DESIGN.md) (`DOC-ATTN-001`): Global, Sparse, Hierarchical, and Fusion Attention formulations and complexity.
17. [**Neural Routing Design**](docs/NEURAL_ROUTING_DESIGN.md) (`DOC-ROUTE-001`): Rule-based, learned top-$k$ MoE, and dynamic hybrid routing architectures.
18. [**Model Initialization**](docs/MODEL_INITIALIZATION.md) (`DOC-INIT-001`): Pure random Gaussian parameter initialization, deterministic seeding, and parameter census.

### Modular Intelligence Architecture (Phase 07)
19. [**Logical Reasoning Engine**](docs/LOGICAL_REASONING.md) (`DOC-INTEL-001`): Deductive chains, assumption extraction, contradiction detection, and uncertainty scoring.
20. [**Mathematical Reasoning Engine**](docs/MATHEMATICAL_INTELLIGENCE.md) (`DOC-INTEL-002`): Deterministic arithmetic, algebra, calculus, and matrix routines with numerical verification.
21. [**Coding Intelligence Engine**](docs/CODING_INTELLIGENCE.md) (`DOC-INTEL-003`): AST parsing, multi-language detection, complexity analysis, and strict sandbox execution boundaries.
22. [**Cybersecurity Intelligence Engine**](docs/CYBERSECURITY_INTELLIGENCE.md) (`DOC-INTEL-004`): Defensive log analysis, file entropy, CVSS 3.1 scoring, and hardening guidelines.
23. [**Scientific & Research Intelligence**](docs/SCIENTIFIC_RESEARCH_INTELLIGENCE.md) (`DOC-INTEL-005`): Physics laws, hypothesis falsifiability, multi-source synthesis, and citation provenance.
24. [**Planning & Decision-Making Engine**](docs/PLANNING_DECISION_MAKING.md) (`DOC-INTEL-006`): Topological DAG decomposition, risk tiers, and operator approval gating.
25. [**Central Intelligence Router**](docs/CENTRAL_INTELLIGENCE_ROUTER.md) (`DOC-INTEL-007`): Dynamic routing, multi-engine composite execution, and conflict resolution.
26. [**Self-Evaluation & Error Detection**](docs/SELF_EVALUATION_ERROR_DETECTION.md) (`DOC-INTEL-008`): Consistency audits, epistemic modesty ("I don't know"), and offline feedback logging.

### Multimodal Intelligence Architecture (Phase 08)
27. [**Multimodal Intelligence**](docs/MULTIMODAL_INTELLIGENCE.md) (`DOC-MULTI-001`): Unified cross-modal processing across text, vision, audio waveforms, speech, video streams, documents, and multi-stage fusion.
28. [**Vision & Image Processing**](docs/IMAGE_PROCESSING.md) (`DOC-MULTI-002`): Magic byte verification, decompression bomb limits, 224x224 spatial resizing, and ViT 16x16 patch extraction (`196, 768`).
29. [**Audio & Speech Processing**](docs/AUDIO_SPEECH_PROCESSING.md) (`DOC-MULTI-003`): PCM normalization, STFT spectrograms, energy VAD, timestamped speech recognition, and formant speech synthesis generating playable WAV streams.
30. [**Video Intelligence**](docs/VIDEO_INTELLIGENCE.md) (`DOC-MULTI-004`): OpenCV streaming frame ingestion without full video RAM decompression, uniform sampling, Chi-Square histogram scene boundaries, and thumbnails.
31. [**Document Intelligence & Defense**](docs/DOCUMENT_INTELLIGENCE.md) (`DOC-MULTI-005`): Multi-format parsing (PDF, DOCX, CSV, JSON, TXT), structured table extraction, and adversarial prompt injection defense (`inspect_prompt_safety`).
32. [**Multimodal Fusion Engine**](docs/MULTIMODAL_FUSION.md) (`DOC-MULTI-006`): Early (modality embeddings), Intermediate (cross-modal attention + LayerScale), and Late (adaptive softmax gating) fusion layers.
33. [**Cross-Modal Context Manager**](docs/CROSS_MODAL_CONTEXT.md) (`DOC-MULTI-007`): Multi-turn conversational memory, bounded 10-turn ring buffer, and reverse chronological coreference resolution.

### Advanced Memory & Continual Learning Architecture (Phase 09)
34. [**Advanced Multi-Layer Memory Architecture**](docs/ADVANCED_MEMORY_SYSTEM.md) (`DOC-MEM-001`): 8-layer cognitive storage system (Short-Term, Working, Long-Term, Episodic, Knowledge, User Preferences, Contextual, Retrieval) with SQLite WAL and referential integrity.
35. [**Memory Retrieval & Consolidation Engine**](docs/MEMORY_RETRIEVAL_CONSOLIDATION.md) (`DOC-MEM-002`): Hybrid BM25 lexical match, exponential recency decay $e^{-\lambda \cdot \Delta t}$, deterministic fallback, near-duplicate merging, and contradiction flagging without silent overwrites.
36. [**Controlled Continual Learning Pipeline**](docs/CONTINUAL_LEARNING_PIPELINE.md) (`DOC-MEM-003`): 10-stage offline learning lifecycle with human governance approval gates; strict invariant prohibiting direct online weight self-modification.
37. [**Memory Privacy, Security & Secret Sanitization**](docs/MEMORY_PRIVACY_SECURITY.md) (`DOC-MEM-004`): Zero-credential scrubbing pipeline, cross-user tenant boundary enforcement, non-executable data invariant, zero past-event fabrication guard, and append-only audit ledger.

### System Architecture & Governance (Phase 01 & 02)
38. [**System Architecture**](docs/SYSTEM_ARCHITECTURE.md) (`DOC-ARCH-001`): Operating modes, orchestration, and data flow.
39. [**Neural Architecture**](docs/NEURAL_ARCHITECTURE.md) (`DOC-ARCH-002`): Layers, RoPE, SwiGLU, MMA attention, and MoE routing.
40. [**Multimodal Architecture**](docs/MULTIMODAL_ARCHITECTURE.md) (`DOC-ARCH-003`): Vision, audio, video, text, and documents fusion.
41. [**Memory Architecture**](docs/MEMORY_ARCHITECTURE.md) (`DOC-ARCH-004`): Multi-tier memory, infinite context, and consolidation.
38. [**Personal AI Architecture**](docs/PERSONAL_AI_ARCHITECTURE.md) (`DOC-ARCH-005`): OS copilot, telemetry, coding, and defensive cybersecurity.
39. [**API Architecture**](docs/API_ARCHITECTURE.md) (`DOC-ARCH-006`): REST, WebSocket, and gRPC protocol specifications.
40. [**Security Architecture**](docs/SECURITY_ARCHITECTURE.md) (`DOC-ARCH-007`): Threat model, 4-tier permissions, audit logging, and sandbox.
41. [**Data Architecture**](docs/DATA_ARCHITECTURE.md) (`DOC-ARCH-008`): Streaming ETL, MinHash deduplication, and binary sharding.
42. [**Infrastructure Architecture**](docs/INFRASTRUCTURE_ARCHITECTURE.md) (`DOC-ARCH-009`): Hybrid local, cloud, and GPU cluster targets.
43. [**Development Standards**](docs/DEVELOPMENT_STANDARDS.md) (`DOC-STANDARDS-001`): Code formatting, typing, logging, and exceptions.
44. [**Hardware Assessment Report**](docs/phase-01-hardware-assessment.md) (`DOC-PHASE01-SYS-001`): Physical host telemetry on Dell Latitude 5400.

---

## 8. Modular Intelligence System (Phase 07)

The 404 FOUNDERS modular intelligence system integrates 12 specialized engines through the Central Intelligence Router:

```mermaid
flowchart TD
    UserQuery["User / System Query"] --> CIR["Central Intelligence Router<br/>(DynamicRouter + Intent Classifier)"]
    
    subgraph ENGINES ["12 Specialized Intelligence Engines"]
        E1["Logical Reasoning Engine"]
        E2["Mathematical Reasoning Engine"]
        E3["Scientific Reasoning Engine"]
        E4["Coding Intelligence Engine (Sandbox Barricaded)"]
        E5["Cybersecurity Intelligence Engine (Defensive Only)"]
        E6["Critical Thinking Engine"]
        E7["Creative Problem-Solving Engine"]
        E8["Research & Knowledge Analysis Engine"]
        E9["Planning & Decision Engine (Human Gate Checkpoint)"]
        E10["Self-Evaluation & Error Detection Engine"]
        E11["Language & Communication Engine"]
        E12["General Knowledge Processing Engine"]
    end
    
    CIR -->|Dispatch Intent / Composite| ENGINES
    ENGINES --> Merge["Conflict Resolution & Output Reconciler"]
    Merge --> Resp["Structured Multi-Engine Response"]
```

---

## 9. Multimodal Intelligence Architecture (Phase 08)

The Phase 08 multimodal intelligence architecture unifies cross-modal processing across Text, Vision, Audio, Speech, Video, and Documents:

```mermaid
flowchart TD
    UserMedia["User Media Query / Files"] --> MR["ModalityRouter<br/>(Simultaneous Detection & Dispatch)"]

    subgraph PROCESSORS ["Specialized Multimodal Processors"]
        P_TXT["MultimodalTextProcessor<br/>(Devanagari, English, Overlapping Chunking)"]
        P_IMG["ImageProcessor<br/>(Magic Bytes, 224x224, ViT 16x16 Patches)"]
        P_AUD["AudioProcessor<br/>(PCM Normalize, STFT Spectrogram, RMS/SNR)"]
        P_SPK["SpeechEngine<br/>(Energy VAD, STT Segments, Formant TTS)"]
        P_VID["VideoProcessor<br/>(OpenCV Streaming, Chi-Square Keyframes)"]
        P_DOC["DocumentProcessor<br/>(PDF, DOCX, CSV, Injection Scanning)"]
    end

    subgraph FUSION ["Multi-Stage Multimodal Fusion Engine"]
        F_EARLY["Early Fusion (Modality Embeddings & Sequence Concat)"]
        F_INTER["Intermediate Fusion (Cross-Modal Attention + LayerScale)"]
        F_LATE["Late Fusion (Adaptive Softmax Gating)"]
    end

    MR --> PROCESSORS
    PROCESSORS --> FUSION
    FUSION --> FusedOut["Unified Multimodal Representation"]
    FusedOut --> CIR2["Central Intelligence Router"]
```

---

## 10. Advanced Memory & Controlled Learning Architecture (Phase 09)

Phase 09 establishes the 8-layer cognitive memory hierarchy, confidential data sanitization, hybrid retrieval with exponential recency decay, and a 10-stage offline continual learning pipeline.

```mermaid
flowchart TD
    PromptQuery["Prompt Query & User Context"] --> CME["Contextual Memory Engine<br/>Token-Budget Bounded Prompt Synthesis"]
    
    subgraph LAYERS ["Cognitive Memory Layers"]
        STM["Short-Term Memory<br/>Rolling turns & auto-aging summarization"]
        WM["Working Memory<br/>Active tasks & crash recovery"]
        LTM["Long-Term Memory<br/>SHA-256 dedup & version ancestry"]
        EPI["Episodic Memory<br/>ZERO past-event fabrication"]
        KM["Knowledge Memory<br/>Verified facts vs user claims"]
        PREF["User Preferences<br/>Inspectable & editable styles"]
    end

    subgraph RETRIEVAL ["Hybrid Retrieval & Consolidation"]
        HRE["Hybrid Retrieval Engine<br/>S = 0.50·S_lex + 0.20·imp + 0.15·conf + 0.15·e^(-λ·Δt)"]
        MCE["Consolidation & Conflict Detection<br/>Never silently overwrite; flag CONFLICT_DETECTED"]
    end

    subgraph LEARNING ["Continual Learning Architecture (Offline)"]
        FB["Feedback System<br/>Ratings, corrections, & bug reports"]
        CLP["10-Stage Controlled Learning Pipeline<br/>Collection ➔ Validation ➔ Curation ➔ Dataset Prep ➔<br/>Job Config ➔ Baseline Eval ➔ Regression Tests ➔<br/>Versioning ➔ Approval Gate ➔ Deployment"]
    end

    CME --> HRE
    HRE --> LTM
    HRE --> KM
    HRE --> EPI
    CME --> STM
    CME --> WM
    CME --> PREF
    
    FB --> CLP
    CLP -.->|Strictly Offline; Zero Online Weight Mutation| NeuralCore["Neural Core Foundation Checkpoint"]
```

### Core Invariants & Protections
1. **Zero-Credential Scrubbing:** `MemorySecurityManager` synchronously scrubs private keys, tokens (`sk-`, `ghp_`), AWS keys, and passwords before database write operations.
2. **Zero Past-Event Fabrication:** Episodic memory inquiries verify actual entries in `episodic_events`. If unrecorded, `verify_past_occurrence()` strictly reports non-occurrence rather than fabricating history.
3. **No Silent Overwriting:** Contradictory user assertions are flagged as `CONFLICT_DETECTED` with provenance trails rather than silently overwriting past knowledge.
4. **Zero Online Weight Modification:** Continual learning is strictly an offline 10-stage gated process with mandatory human governance sign-off.

---

## 11. Development Roadmap & Phase Status

| Phase | Phase Name | Status |
|---|---|---|
| **Phase 01** | Environment & Hardware Assessment | **Completed** |
| **Phase 02** | Project Architecture & Workspace Design | **Completed** |
| **Phase 03** | Core AI Foundation Development | **Completed** |
| **Phase 04** | Custom BPE Tokenizer & Data Pipeline | **Completed** |
| **Phase 05** | Training Infrastructure & GPU Cluster Architecture | **Completed** |
| **Phase 06** | Foundation Model Pretraining from Random Initialization | **Completed** |
| **Phase 07** | Modular Intelligence Modules | **Completed** |
| **Phase 08** | Multimodal Intelligence & Cross-Modal Fusion | **Completed** |
| **Phase 09** | **Advanced Memory & Controlled Learning Architecture** | **Completed (Review Pending)** |

---

## 12. Quickstart, Localhost Testing & Verification

### Localhost Application Execution

The project runs locally on the developer workstation without GPUs or pretrained weights.

#### Step 1: Launch Backend API Server (FastAPI + Uvicorn)
```bash
# Start FastAPI backend on http://127.0.0.1:8000
.venv/bin/python scripts/run_backend.py

# Or via uvicorn directly:
.venv/bin/uvicorn api.rest.app:app --host 127.0.0.1 --port 8000
```
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Interactive OpenAPI Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc API Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

#### Step 2: Launch Frontend Testing Dashboard
```bash
# In a separate terminal, start frontend on http://localhost:5173
cd frontend && npm start

# Or directly:
node frontend/server.js
```
- **Local Dashboard:** [http://localhost:5173](http://localhost:5173)
- **Features:** Warm neutral design, Light/Dark/System theme selector, Multimodal Studio view, and chat composer attachment tray for images, audio, video, and documents.

---

### Automated Tests & CLI Diagnostics

```bash
# 1. Run complete automated test suite (247 tests) on CPU
.venv/bin/python -m pytest tests/

# 2. Interact with the Unified Multimodal Engine via CLI
.venv/bin/python scripts/run_multimodal.py --list-modalities
.venv/bin/python scripts/run_multimodal.py --text "404 FOUNDERS is an enterprise AI assistant." --speech-tts
.venv/bin/python scripts/run_multimodal.py --fuse --fuse-stage EARLY

# 3. Interact with the 12 Modular Intelligence Engines via CLI
.venv/bin/python scripts/run_intelligence.py --list-modules
.venv/bin/python scripts/run_intelligence.py --query "calculate 42 * (15 + 3)"
.venv/bin/python scripts/run_intelligence.py --query "analyze python code: def factorial(n): return 1 if n<=1 else n*factorial(n-1)"
.venv/bin/python scripts/run_intelligence.py --query "plan production database deployment with subtasks"

# 3. Execute 10-step Pre-Flight Training Verification Suite
.venv/bin/python scripts/validate_training.py

# 3. Model initialization from random weights & parameter auditing
.venv/bin/python scripts/initialize_model.py --profile local_cpu --seed 404

# 4. Run controlled local pilot pretraining with telemetry
.venv/bin/python scripts/run_training.py --profile tiny --steps 15

# 5. Inspect saved checkpoint metadata & verify SHA-256 integrity sidecar
.venv/bin/python scripts/inspect_checkpoint.py training_runs/<run_id>/checkpoints/best_model.pt

# 6. Resume pretraining from a verified checkpoint
.venv/bin/python scripts/resume_training.py training_runs/<run_id>/checkpoints/checkpoint_step_0000015_final.pt --additional-steps 10

# 7. Perform safe host hardware audit & runtime budgeting check
.venv/bin/python scripts/system_check.py

# 8. Perform GPU & CUDA compatibility inspection (reports local host & cluster tiers)
.venv/bin/python scripts/gpu_check.py

# 9. Audit software environment, compiler toolchain, and libraries
.venv/bin/python scripts/environment_check.py

# 10. Run storage tiering capacity and local sequential I/O benchmark
.venv/bin/python scripts/storage_check.py

# 11. Train a Custom BPE Tokenizer model on sample text
.venv/bin/python scripts/train_tokenizer.py \
    --input README.md \
    --output configs/tokenizer/tokenizer_model.json \
    --vocab-size 512

# 12. Encode text with BOS/EOS tags
.venv/bin/python scripts/encode_text.py \
    --model configs/tokenizer/tokenizer_model.json \
    --text "नमस्ते भारत! 404 FOUNDERS is an enterprise AI assistant." \
    --add-bos --add-eos

# 13. Execute prototype inference with greedy token prediction
.venv/bin/python -c "
from neural_architecture.inference import InferenceEngine
engine = InferenceEngine()
prompt = [10, 20, 30]
output = engine.generate_greedy_tokens(prompt, max_new_tokens=5)
print('Prompt:', prompt)
print('Generated sequence:', output)
print('Total parameters:', engine.model.parameter_count)
"
```
