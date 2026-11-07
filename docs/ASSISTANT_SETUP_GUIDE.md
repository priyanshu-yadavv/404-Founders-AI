# 404 FOUNDERS — JARVIS Assistant Setup & Operator Guide
**Tagline:** Intelligence Without Boundaries.  
**System:** Conversational Voice Assistant Setup & Operation  
**Classification:** Operator Manual

---

## 1. Quick Start

### 1.1 Running the Unified Backend & Frontend
1. Start the FastAPI backend:
   ```bash
   PYTHONPATH="./.venv/lib/python3.14/site-packages:." uvicorn api.rest.app:app --host 127.0.0.1 --port 8000
   ```
2. In a second terminal, serve the frontend:
   ```bash
   node frontend/server.js
   ```
3. Open `http://127.0.0.1:3000` in Google Chrome or Microsoft Edge.
4. Select **JARVIS Voice** in the left navigation sidebar.

---

## 2. Voice Assistant Configuration

### 2.1 Microphone Activation
- **Push-to-Talk:** Click the central circular microphone button or press the **Spacebar** while in the JARVIS workspace.
- **Wake-Word Mode:** Ensure the **Wake Word: Hey Founders** checkbox is active. Speak *"Hey Founders"* into your microphone.

### 2.2 Voice Identity Selection
- **404 Founders Calm:** Composed, authoritative English cadence. Recommended for daily operations.
- **404 Founders Hindi:** Native acoustic modeling for Hindi and Devanagari utterances.
- **404 Founders Fast:** Higher tempo ($1.25\times$) optimized for rapid code reviews and test summaries.

### 2.3 Barge-In Interrupts
When JARVIS is speaking:
- Tap the central button or click **🛑 Barge-In (Stop)** to immediately halt speech synthesis.
- Alternatively, begin speaking. The Voice Activity Detector (VAD) will cancel the ongoing audio stream.

---

## 3. Example Natural Language Interactions

### System Introspection
- *"What are the current hardware vitals?"*
- *"RAM aur CPU kitna use ho raha hai?"*
- *"सिस्टम स्थिति की जाँच करें"*

### Workstation Tool Execution
- *"Review modified files on git"*
- *"Run network latency ping test"*
- *"Launch application radare2"* (Prompts for one-time approval ticket)

---

## 4. Proactive Assistant Settings
The hardware watchdog operates quietly in the background:
- **Quiet Hours:** Default `22:00` to `08:00`. Spoken audio alerts are suppressed; warnings are delivered via subtle UI notifications.
- **Adjusting Thresholds:** Use `POST /api/v1/jarvis/proactive/config` to adjust CPU, RAM, or disk thresholds.
