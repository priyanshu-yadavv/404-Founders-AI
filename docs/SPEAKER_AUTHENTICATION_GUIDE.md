# 404 FOUNDERS — Speaker Authentication & Anti-Spoofing Guide
**Tagline:** Intelligence Without Boundaries.  
**System:** "Only My Voice" Acoustic Verification & Anti-Spoofing Architecture  
**Classification:** Technical Security Reference

---

## 1. Probabilistic Biometrics vs. Hard Gates

> [!IMPORTANT]
> Voice biometrics is probabilistic. Never claim 100% voice recognition accuracy. Voice verification alone **never** overrides the 5-tier permission manager; destructive or privileged actions (e.g., file deletion, process termination) require an additional approval ticket or operator PIN.

---

## 2. Verification Outcomes

When an incoming utterance is analyzed against an enrolled voice profile, the system yields one of five structured outcomes:

| Outcome | Metric Condition | System Action |
|---|---|---|
| `VERIFIED` | Similarity $\ge \tau$ (Default: $0.75$) AND Liveness $\ge 0.50$ | Unlocks natural language interaction and read-only tools. |
| `UNCERTAIN` | $(\tau - 0.12) \le$ Similarity $< \tau$ | Requests repetition with ambient noise reduction or PIN. |
| `REJECTED` | Similarity $< (\tau - 0.12)$ | Access denied; suppresses command execution. |
| `SPOOF_SUSPECTED` | Liveness $< 0.50$ (Replay / Synthetic detected) | Immediately halts turn, logs security audit alert. |
| `ENROLLMENT_REQUIRED` | No active profile exists for user account | Prompts operator to complete initial 3-sample calibration. |

---

## 3. Mathematical Verification Model

The 32-dimensional embedding vector $\mathbf{e} \in \mathbb{R}^{32}$ is normalized to unit length:

$$\hat{\mathbf{e}} = \frac{\mathbf{e}}{\|\mathbf{e}\|_2}$$

Given enrolled template $\hat{\mathbf{e}}_{\text{ref}}$ and candidate utterance $\hat{\mathbf{e}}_{\text{cand}}$, the biometric similarity score $S$ is defined as:

$$S = \max\left(0, \min\left(1, \hat{\mathbf{e}}_{\text{cand}} \cdot \hat{\mathbf{e}}_{\text{ref}}\right)\right)$$

Threshold $\tau$ is operator-configurable between $0.60$ and $0.90$ (factory default: $0.75$).

---

## 4. Acoustic Anti-Spoofing & Liveness Guard

The anti-spoofing engine detects replay attacks, synthetic voice generation, and flat recorded samples through three complementary acoustic markers:

1. **High-Frequency Harmonic Decay ($H_D$):** Synthetic audio or low-quality playback speakers exhibit abnormal roll-off above $4,000\text{ Hz}$.
2. **Spectral Smoothness ($S_M$):** Linear Predictive Coding (LPC) residual energy variance verifies human vocal tract physical resonances.
3. **Pitch Envelope Micro-Tremor ($T_P$):** Natural human vocal folds vibrate with involuntary fundamental pitch tremor ($4\text{ Hz}$–$8\text{ Hz}$). Perfect steady-state frequencies flag algorithmic generation.

---

## 5. Security Invariants

1. **Zero Raw Audio Retention:** Inbound audio buffers are discarded from RAM immediately upon feature extraction.
2. **Local Cryptographic Storage:** Biometric templates are stored as AES-256-GCM ciphertexts with 96-bit random nonces in SQLite.
3. **Immutable Audit Ledger:** Every verification and revocation event is recorded with millisecond timestamps in `voice_audit_log`.
