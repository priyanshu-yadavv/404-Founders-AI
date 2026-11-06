# 404 FOUNDERS — Infrastructure Security & Zero-Trust Governance

## 1. Executive Summary

The computational resources, intellectual property (custom neural architecture and tokenizer algorithms), and pretraining checkpoints of **404 FOUNDERS** represent critical assets. The infrastructure security model implements a zero-trust architecture governing node access, distributed inter-process communication, secret lifecycle, and container sandboxing.

---

## 2. Zero-Trust Access & SSH Policy

```mermaid
flowchart LR
    subgraph Client ["Client Access"]
        U[Authorized Engineer]
    end

    subgraph Perimeter ["Cluster Perimeter (Bastion Gateway)"]
        B[Hardened Bastion Host]
        MFA[Hardware MFA / FIDO2]
        K[SSH Ed25519 Key Validator]
    end

    subgraph Internal_VPC ["Isolated GPU Supercluster VPC"]
        N1[Head Node / Slurm Controller]
        N2[GPU Compute Nodes 1-8]
        S[Parallel Filesystem / Storage Vault]
    end

    U -->|SSH + Ed25519 + MFA| B
    B --> MFA
    B --> K
    K -->|Approved Key & Role| N1
    N1 --> N2
    N1 --> S
```

### Mandatory Access Policies:
1. **Public Key Cryptography**: Access to cluster nodes is restricted strictly to **Ed25519** public keys (`ssh-ed25519`) or ECDSA (>= 384 bits). Legacy RSA keys ($\le$ 2048 bits) and password-based authentication (`PasswordAuthentication no`) are explicitly rejected.
2. **Bastion Host Gateway**: Compute nodes inhabit private, non-routable subnets. All interactive engineering sessions pass through an audited bastion gateway requiring hardware token MFA.
3. **Network Boundary Isolation**: Control plane REST/gRPC endpoints communicate strictly over internal VPC interfaces protected by mutual TLS (mTLS) with TLS 1.3 cipher suites.

---

## 3. Role-Based Access Control (RBAC)

Cluster operations are partitioned into four distinct roles enforcing least-privilege principles:

| Role | Permitted Actions | Prohibited Actions | Typical Assignee |
| :--- | :--- | :--- | :--- |
| **`cluster_admin`** | Node reboot/drain, fabric config, key rotation, Slurm QoS, full checkpoint read/write/delete | Direct production checkpoint deletion without dual-signoff | Lead Infrastructure Architect |
| **`ml_engineer`** | Distributed job submission, own job cancellation, storage mount, checkpoint read/write | Node draining, InfiniBand fabric changes, key rotation | AI Systems & Training Engineers |
| **`researcher`** | Standard job submission, own job cancellation, checkpoint read, metrics read | Storage administrative modifications, write to production vault | NLP & Architecture Researchers |
| **`auditor_observer`**| Telemetry read, metric collection, audit log inspection | Job submission, script execution, checkpoint access | Security & Compliance Officers |

---

## 4. Secret Sanitization & Audit Trails

### Automated Credential Masking
The `ClusterSecurityManager` inspects all terminal outputs, Slurm standard logs, and telemetry pipelines using automated regular expression filters. Sensitive strings matching patterns for:
- HuggingFace tokens (`hf_*`)
- GitHub personal access tokens (`ghp_*`)
- OpenAI / Anthropic API keys (`sk-*`)
- AWS access keys (`AKIA*`)
- PEM private keys (`-----BEGIN PRIVATE KEY-----`)

are instantly substituted with `[REDACTED_SECRET]` prior to disk persistence or remote forwarding.

### Immutable Audit Logging
All privileged cluster actions (e.g. node drain, permission grant, checkpoint immutability toggle) generate a cryptographically verifiable JSONL audit record stored in `logs/security_audit.jsonl`:

```json
{
  "timestamp": 1730913600.0,
  "user": "lead_engineer",
  "role": "cluster_admin",
  "action": "checkpoint:lock_milestone",
  "target": "chkpt_step_00050000",
  "status": "GRANTED",
  "details": {"reason": "Validation loss nadir (2.1485)"}
}
```

---

## 5. Container & Runtime Sandboxing

Distributed training jobs execute inside non-privileged container containers (Docker / Enroot / Pyxis):
- **User Namespace**: Container processes run as non-root user `uid=1000(founder) gid=1000(founder)`.
- **Read-Only Root Filesystem**: The base OS image is mounted read-only (`read_only: true`); writes are restricted strictly to designated `/scratch` and `/checkpoints` mount points.
- **Linux Capability Drop**: All standard Linux capabilities (`CAP_SYS_ADMIN`, `CAP_NET_ADMIN`, `CAP_DAC_OVERRIDE`) are dropped by default.
