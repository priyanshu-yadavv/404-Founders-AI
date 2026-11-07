# 404 FOUNDERS — Voice Biometric Enrollment Guide
**Tagline:** Intelligence Without Boundaries.  
**System:** "Only My Voice" Acoustic Enrollment Protocol  
**Classification:** Operational Security & Onboarding Guide

---

## 1. Overview

The 404 FOUNDERS "Only My Voice" architecture ensures the voice assistant accepts commands exclusively from authorized operators. To maintain high fidelity without storing private raw recordings, the enrollment protocol processes three distinct phonetic calibration utterances, extracts a 32-dimensional spectral vector, and encrypts it locally using AES-256-GCM.

---

## 2. Enrollment Prerequisites

- **Microphone:** Built-in laptop microphone, USB desktop microphone, or headset.
- **Environment:** Quiet room with low ambient background noise (SNR $\ge 12\text{ dB}$).
- **Audio Format:** 16,000 Hz, 16-bit Mono Linear PCM WAV.

---

## 3. The 3-Step Utterance Calibration Protocol

Operators speak three distinct sentences designed to excite diverse fundamental frequencies, vowel formants, and unvoiced consonants:

| Step | Utterance Phrasing | Phonetic Purpose |
|---|---|---|
| **Sample 1** | *"Hey Founders, verify my voice profile"* | Calibrates wake-word phonemes, leading aspirates, and initial vocal inflection. |
| **Sample 2** | *"Intelligence Without Boundaries"* | Calibrates high-vowel formants ($/i/$, $/u/$) and dental/alveolar transitions. |
| **Sample 3** | *"Activate secure workstation assistant"* | Calibrates command cadence, consonant stops ($/k/$, $/t/$, $/p/$), and chest resonance. |

---

## 4. Acoustic Quality Verification Gates

Every audio sample submitted to `POST /api/v1/jarvis/enroll/sample` must satisfy four deterministic quality gates:

1. **Duration Gate:** Minimum $0.8\text{ seconds}$, maximum $10.0\text{ seconds}$.
2. **Silence Gate:** Root-Mean-Square (RMS) signal energy must exceed $0.005$.
3. **Signal-to-Noise Ratio (SNR) Gate:** Estimated SNR must exceed $10.0\text{ dB}$.
4. **Clipping Gate:** No more than $1.0\%$ of audio samples may reach the $\pm 32,767$ full-scale amplitude ceiling.

If any check fails, the sample is rejected with an actionable operational message (e.g., *"Audio is too quiet. Please speak closer to the microphone"*).

---

## 5. UI Enrollment Procedure

1. Navigate to the **JARVIS Voice** workspace (`data-view="jarvis"`).
2. Under the **Voice Biometrics ("Only My Voice")** panel, click **Enroll Speaker Voice**.
3. In the modal, click **Record (3s)** for Utterance 1 and speak the displayed text.
4. Once validated (green checkmark and SNR score), repeat for Utterance 2 and Utterance 3.
5. Click **Generate & Encrypt Profile**.
6. The profile is saved to SQLite, cached in memory, and the status updates to **Only My Voice: Verified**.

---

## 6. Profile Revocation

To revoke your voice profile:
- Click **Revoke Profile** in the UI, or execute `DELETE /api/v1/jarvis/profile`.
- The profile is immediately expunged from memory and deactivated (`is_active = 0`) in the database.
- An immutable revocation event is logged to `voice_audit_log`.
