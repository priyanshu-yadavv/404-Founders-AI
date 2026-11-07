# 404 FOUNDERS — Frontend Architecture Specification
**Document ID:** `DOC-FRONT-001`  
**Brand:** 404 FOUNDERS  
**Tagline:** *Intelligence Without Boundaries.*  
**Design System:** Warm Neutral Minimalism  
**Phase:** 11 — API, Frontend & Deployment  

---

## 1. Executive Overview

The 404 FOUNDERS frontend application is a modern, responsive single-page application (SPA) built using vanilla JavaScript (ES6+), semantic HTML5, and custom CSS3 variables without bulky framework overhead. It serves as the primary visual interface for the custom multimodal foundation AI and local workstation intelligence agent.

### Core Visual Principles
- **Aesthetic:** Premium warm minimalism, natural editorial design, and distraction-free developer ergonomics.
- **Theme Palette:**
  - Main Background: `#F4F0E8` (Light) / `#1E1C18` (Dark)
  - Content Surfaces: `#FFFFFF` (Light) / `#262420` (Dark)
  - Secondary Surfaces: `#E9E3D8` (Light) / `#312E29` (Dark)
  - Borders: `#DCD5C9` (Light) / `#3D3933` (Dark)
  - Primary Text: `#292720` (Light) / `#EDE8DE` (Dark)
  - Secondary Text: `#777064` (Light) / `#A39C90` (Dark)
  - Primary Accent: `#343D35` (Deep Forest Sage)
  - Secondary Accent: `#A58C70` (Warm Sandstone)
- **Strict Invariants:** No neon colors, no purple or cyan AI gradients, no glowing pseudo-futuristic borders, and zero fabricated telemetry metrics.

---

## 2. Nine Unified Primary Workspaces

The application interface organizes complex multi-phase AI subsystems into 9 distinct workspaces selectable via the left navigation bar:

| # | Workspace Name | Identifier | Primary Purpose |
|---|---|---|---|
| 1 | **General Intelligence** | `intelligence` | Multi-turn autoregressive text inference, thread management, progressive live token streaming, and markdown formatting. |
| 2 | **Personal AI Agent** | `personal-ai` | Local workstation controller, real-time process monitoring, sandboxed filesystem navigation, and human-in-the-loop approval tickets. |
| 3 | **Coding Assistant** | `coding` | Repository topology inspection, automated git status analysis, test suite verification, and code syntax generation. |
| 4 | **Cybersecurity Intelligence** | `cybersecurity` | Adversarial prompt security auditing, shell command validation with privilege tiering, and security posture scoring. |
| 5 | **Multimodal Studio** | `multimodal` | Unified cross-modal fusion (Early, Intermediate, Late) across Vision (ViT patches), Audio (Spectrograms), Video (Keyframes), and Documents (PDF/DOCX extraction). |
| 6 | **Memory & Continual Learning** | `memory` | Multi-layer memory inspection (Short-Term, Working, Episodic, Knowledge, Preferences) and supervised continual learning fine-tuning jobs. |
| 7 | **System Intelligence** | `telemetry` | Zero-fabrication hardware introspection, CPU/Memory telemetry, GPU cluster catalog overview, and safe OOM budget allocation. |
| 8 | **Task & Activity History** | `activity` | Unified, filterable operational audit ledger recording all intelligence queries, Personal AI actions, learning jobs, and authentication events. |
| 9 | **Settings & Sessions** | `settings` | Appearance theme toggle, voice assistant speech synthesis parameters, memory retention windows, active session revocation, and backend endpoint configuration. |

---

## 3. Real-Time Streaming & Audio Architecture

### 3.1 Dual-Channel Streaming Client
- **Primary:** WebSocket streaming (`ws://127.0.0.1:8000/ws/v1/chat`). As the foundation model processes tokens, progressive JSON chunks are received:
  - `{"type": "status", "stage": "ANALYZING"}`
  - `{"type": "token", "content": "..."}`
  - `{"type": "done", "tokens_generated": 16}`
- **Fallback:** Server-Sent Events (`POST /api/v1/chat/stream`) yielding standard `text/event-stream` lines or direct asynchronous REST polling.

### 3.2 Speech & Audio Capabilities
- **Voice Input (Speech-to-Text):** Integrated via browser Web Speech API (`webkitSpeechRecognition` / `SpeechRecognition`), allowing real-time speech transcription directly into the composer with visual microphone pulsation indicators.
- **Speech Synthesis (TTS):** Dual-mode audio output supporting client-side `window.speechSynthesis` and backend acoustic formant synthesis (`/api/v1/multimodal/speech/synthesize`).

---

## 4. Conversation & Thread Lifecycle

- **Thread Persistence:** Threads are stored in SQLite `conversation_threads` via `POST /api/v1/conversations`.
- **Message Trajectory:** Every user prompt and assistant response is logged with timestamp, sender role, token piece metadata, and audit trace.
- **Message Controls:**
  - One-click markdown code block copy buttons.
  - Message prompt editing (re-populates the composer).
  - One-click response regeneration.
  - Text-to-speech audio playback.
