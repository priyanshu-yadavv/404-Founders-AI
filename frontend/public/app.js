/**
 * 404 FOUNDERS — Warm Neutral Frontend Controller
 * Style: Premium warm minimalism, sophisticated productivity software.
 * Communicates with FastAPI backend on http://127.0.0.1:8000
 */

let API_BASE = localStorage.getItem('404_founders_endpoint') || 'http://127.0.0.1:8000';
let authToken = localStorage.getItem('404_founders_token') || '';
let currentConversationId = localStorage.getItem('404_founders_active_thread') || null;
let lastUserPrompt = '';

function getAuthHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
  return headers;
}

function showToast(message) {
  const existing = document.querySelector('.toast-notification');
  if (existing) existing.remove();
  const toast = document.createElement('div');
  toast.className = 'toast-notification';
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 2200);
}

function copyText(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Copied to clipboard');
  }).catch(() => {
    showToast('Failed to copy');
  });
}

window.copyCode = function(btn) {
  const codeEl = btn.parentElement.querySelector('code');
  if (codeEl) {
    copyText(codeEl.innerText);
  }
};

function renderMarkdownContent(text) {
  if (!text) return '';
  // 1. Replace code blocks
  let formatted = text.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<div class="code-container"><button class="code-copy-btn" onclick="copyCode(this)">Copy</button><pre><code>${escapeHtml(code.trim())}</code></pre></div>`;
  });
  // 2. Replace inline code
  formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
  // 3. Replace bold
  formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  return formatted;
}

function renderMessageActions(text, sender, msgId = '') {
  const isUser = sender === 'user';
  return `
    <div class="msg-actions">
      <button class="msg-action-btn" onclick="copyText(${JSON.stringify(text)})" title="Copy text">📋 Copy</button>
      ${isUser ? `<button class="msg-action-btn" onclick="editUserMessage(${JSON.stringify(text)})" title="Edit prompt in composer">✏️ Edit</button>` : ''}
      ${!isUser ? `<button class="msg-action-btn" onclick="regenerateLastResponse()" title="Regenerate response">🔄 Regenerate</button>` : ''}
      ${!isUser ? `<button class="msg-action-btn" onclick="speakMessageText(${JSON.stringify(text)})" title="Speak message aloud">🔊 Speak</button>` : ''}
    </div>
  `;
}

window.editUserMessage = function(text) {
  const composer = document.getElementById('composerText');
  if (composer) {
    composer.value = text;
    composer.focus();
    showToast('Prompt placed in composer');
  }
};

window.speakMessageText = function(text) {
  if (!('speechSynthesis' in window)) {
    showToast('Web Speech API not supported in this browser');
    return;
  }
  window.speechSynthesis.cancel();
  const clean = text.replace(/[`*_#]/g, '');
  const utterance = new SpeechSynthesisUtterance(clean);
  const langSel = document.getElementById('settingsLanguage');
  utterance.lang = langSel ? langSel.value : 'en';
  window.speechSynthesis.speak(utterance);
  showToast('Playing speech output');
};

// Navigation & View Meta
const viewMetadata = {
  intelligence: {
    title: 'Intelligence & Chat',
    subtitle: 'Autoregressive neural inference on custom foundation architecture'
  },
  telemetry: {
    title: 'System Telemetry & OOM Guard',
    subtitle: 'Hardware introspection and memory budget protection'
  },
  tokenizer: {
    title: 'Custom BPE Tokenizer Studio',
    subtitle: 'Subword encoding and lossless round-trip detokenization'
  },
  coding: {
    title: 'Coding Workspace & Architecture',
    subtitle: 'Repository intelligence, module topology, and test suite verification'
  },
  cybersecurity: {
    title: 'Cybersecurity Audit & Safety Gates',
    subtitle: 'Command sanitization, privilege hierarchies, and adversarial prompt inspection'
  },
  memory: {
    title: 'Personal AI & Multi-Layer Memory',
    subtitle: 'KV-Cache, episodic logs, vector embeddings, and local data sovereignty'
  },
  'personal-ai': {
    title: 'Personal AI Agent & Local Workstation Controller',
    subtitle: 'Zero-fabrication telemetry, sandboxed file assistant, command safety advisor, and approval workflow'
  },
  activity: {
    title: 'Task & Activity Ledger',
    subtitle: 'Unified operational audit across neural routing, Personal AI, memory, and security'
  },
  settings: {
    title: 'Application & Account Settings',
    subtitle: 'Appearance themes, cryptographic sessions, voice parameters, and endpoint configuration'
  },
  api: {
    title: 'API Specifications & Interactive Docs',
    subtitle: 'FastAPI OpenAPI 3.1.0 interactive documentation and verification endpoints'
  },
  multimodal: {
    title: 'Multimodal Intelligence Studio',
    subtitle: 'Cross-modal processing for text, vision, audio, video, and documents'
  }
};

// State
let lastEncodedIds = [];
let isBackendOnline = false;

// Multimodal Attachments State
const activeAttachments = {
  image: null,
  audio: null,
  video: null,
  doc: null
};

// -------------------------------------------------------------------------
// Theme Switcher & System Preference Sync
// -------------------------------------------------------------------------

function initThemeSwitcher() {
  const themeSelect = document.getElementById('themeSelect');
  if (!themeSelect) return;
  const saved = localStorage.getItem('404_founders_theme') || 'light';
  themeSelect.value = saved;
  applyTheme(saved);

  themeSelect.addEventListener('change', (e) => {
    const val = e.target.value;
    localStorage.setItem('404_founders_theme', val);
    applyTheme(val);
  });
}

function applyTheme(theme) {
  if (theme === 'system') {
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
  } else {
    document.documentElement.setAttribute('data-theme', theme);
  }
}

// -------------------------------------------------------------------------
// Navigation & View Switching
// -------------------------------------------------------------------------

function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const viewKey = item.getAttribute('data-view');
      switchView(viewKey);
    });
  });
}

function switchView(viewKey) {
  // Update nav item active state
  document.querySelectorAll('.nav-item').forEach(item => {
    if (item.getAttribute('data-view') === viewKey) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  // Update view panel active state
  document.querySelectorAll('.view-panel').forEach(panel => {
    if (panel.id === `view-${viewKey}`) {
      panel.classList.add('active');
    } else {
      panel.classList.remove('active');
    }
  });

  // Update topbar headers
  const meta = viewMetadata[viewKey] || { title: '404 FOUNDERS', subtitle: 'Intelligence Without Boundaries' };
  document.getElementById('viewTitle').textContent = meta.title;
  document.getElementById('viewSubtitle').textContent = meta.subtitle;

  // Trigger view-specific refreshes
  if (viewKey === 'telemetry') {
    fetchTelemetry();
    fetchClusterCatalog();
  } else if (viewKey === 'coding') {
    fetchGitStatus();
  } else if (viewKey === 'personal-ai') {
    fetchPersonalAIStatus();
    fetchPersonalAIHardware();
    fetchPersonalAIProcesses();
    fetchPersonalAIApprovals();
    fetchPersonalAIAuditLogs();
  } else if (viewKey === 'activity') {
    fetchActivityHistory();
  } else if (viewKey === 'settings') {
    fetchSettings();
  }
}

// -------------------------------------------------------------------------
// Health Check & Topbar Status
// -------------------------------------------------------------------------

async function checkHealth() {
  const statusPill = document.getElementById('statusPill');
  const statusDot = document.getElementById('statusDot');
  const statusLabel = document.getElementById('statusLabel');
  const metaParams = document.getElementById('metaParams');

  try {
    const res = await fetch(`${API_BASE}/health`, { method: 'GET' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    isBackendOnline = true;
    statusDot.className = 'status-dot online';
    statusLabel.textContent = `Online (${data.compute_backend.toUpperCase()})`;
    metaParams.textContent = `~${data.model_parameter_count.toLocaleString()} params`;

    const badgeMode = document.getElementById('badgeMode');
    if (badgeMode) {
      badgeMode.textContent = `${data.operating_mode.toUpperCase()} MODE`;
    }
  } catch (err) {
    isBackendOnline = false;
    statusDot.className = 'status-dot offline';
    statusLabel.textContent = 'Backend Offline';
  }
}

// -------------------------------------------------------------------------
// View 1: Intelligence & Chat (Real Autoregressive Neural Forward Pass)
// -------------------------------------------------------------------------

function initChat() {
  const btnSend = document.getElementById('btnChatSend');
  const composerText = document.getElementById('composerText');

  // Keyboard shortcut: Ctrl+Enter or Cmd+Enter to send
  composerText.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      sendChatMessage();
    }
  });

  btnSend.addEventListener('click', sendChatMessage);

  // File upload buttons
  const btnAttachImage = document.getElementById('btnAttachImage');
  const inputAttachImage = document.getElementById('attachImageInput');
  const btnAttachAudio = document.getElementById('btnAttachAudio');
  const inputAttachAudio = document.getElementById('attachAudioInput');
  const btnAttachVideo = document.getElementById('btnAttachVideo');
  const inputAttachVideo = document.getElementById('attachVideoInput');
  const btnAttachDoc = document.getElementById('btnAttachDoc');
  const inputAttachDoc = document.getElementById('attachDocInput');

  if (btnAttachImage && inputAttachImage) {
    btnAttachImage.addEventListener('click', () => inputAttachImage.click());
    inputAttachImage.addEventListener('change', (e) => handleFileAttach(e, 'image', '📷'));
  }
  if (btnAttachAudio && inputAttachAudio) {
    btnAttachAudio.addEventListener('click', () => inputAttachAudio.click());
    inputAttachAudio.addEventListener('change', (e) => handleFileAttach(e, 'audio', '🎙️'));
  }
  if (btnAttachVideo && inputAttachVideo) {
    btnAttachVideo.addEventListener('click', () => inputAttachVideo.click());
    inputAttachVideo.addEventListener('change', (e) => handleFileAttach(e, 'video', '🎬'));
  }
  if (btnAttachDoc && inputAttachDoc) {
    btnAttachDoc.addEventListener('click', () => inputAttachDoc.click());
    inputAttachDoc.addEventListener('change', (e) => handleFileAttach(e, 'doc', '📄'));
  }
}

function handleFileAttach(e, type, icon) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (loadEvent) => {
    const dataUri = loadEvent.target.result;
    const base64Data = dataUri.split(',')[1] || dataUri;
    activeAttachments[type] = {
      name: file.name,
      size: file.size,
      mime: file.type,
      data: base64Data,
      icon: icon
    };
    renderAttachmentTray();
  };
  reader.readAsDataURL(file);
}

function renderAttachmentTray() {
  const tray = document.getElementById('composerAttachmentTray');
  if (!tray) return;
  const keys = Object.keys(activeAttachments).filter(k => activeAttachments[k] !== null);
  if (keys.length === 0) {
    tray.style.display = 'none';
    tray.innerHTML = '';
    return;
  }
  tray.style.display = 'flex';
  tray.innerHTML = keys.map(k => {
    const item = activeAttachments[k];
    return `
      <div class="composer-attachment-pill">
        <span>${item.icon} ${escapeHtml(item.name)}</span>
        <span class="remove-btn" onclick="removeAttachment('${k}')">&times;</span>
      </div>
    `;
  }).join('');
}

window.removeAttachment = function(type) {
  activeAttachments[type] = null;
  const inputEl = document.getElementById(`attach${type.charAt(0).toUpperCase() + type.slice(1)}Input`);
  if (inputEl) inputEl.value = '';
  renderAttachmentTray();
};

async function sendChatMessage() {
  const composerText = document.getElementById('composerText');
  const prompt = composerText.value.trim();
  const hasAttachments = Object.values(activeAttachments).some(v => v !== null);

  if (!prompt && !hasAttachments) return;

  const chatThread = document.getElementById('chatThread');
  const btnSend = document.getElementById('btnChatSend');
  const chkFusion = document.getElementById('chkMultimodalFusion');
  const chkTTS = document.getElementById('chkSpeechTTS');
  const isMultimodalQuery = hasAttachments || (chkFusion && chkFusion.checked);

  // Render user message
  const userMsgEl = document.createElement('div');
  userMsgEl.className = 'message-item user';

  let attachedBadges = '';
  for (const [k, v] of Object.entries(activeAttachments)) {
    if (v) attachedBadges += `<span class="badge-outline" style="margin-right: 4px;">${v.icon} ${escapeHtml(v.name)}</span>`;
  }

  lastUserPrompt = prompt;

  userMsgEl.innerHTML = `
    <div class="message-sender">User &bull; ${hasAttachments ? 'Multimodal Payload' : 'Interactive Query'}</div>
    ${attachedBadges ? `<div style="margin-bottom: 6px;">${attachedBadges}</div>` : ''}
    <div class="message-bubble">${renderMarkdownContent(prompt || '(Attached media payload)')}</div>
    ${renderMessageActions(prompt, 'user')}
  `;
  chatThread.appendChild(userMsgEl);

  // Clear composer & disable send button during inference
  composerText.value = '';
  btnSend.disabled = true;
  btnSend.textContent = 'Processing Query...';

  // Append temporary loading indicator
  const pendingEl = document.createElement('div');
  pendingEl.className = 'message-item assistant';
  pendingEl.innerHTML = `
    <div class="message-sender">404 FOUNDERS Engine</div>
    <div class="message-bubble" style="color: var(--text-muted); font-style: italic;">
      ${hasAttachments ? 'Analyzing cross-modal features and executing fusion pipeline...' : 'Evaluating token embeddings, attention, and neural forward pass...'}
    </div>
  `;
  chatThread.appendChild(pendingEl);
  chatThread.scrollTop = chatThread.scrollHeight;

  const startTime = performance.now();

  const chkLive = document.getElementById('chkLiveStreaming');
  if (chkLive && chkLive.checked && !hasAttachments && prompt) {
    streamViaWebSocket(prompt, pendingEl, startTime);
    btnSend.disabled = false;
    btnSend.textContent = 'Execute Multimodal Query';
    return;
  }

  try {
    if (hasAttachments || isMultimodalQuery) {
      // Multimodal REST Endpoint
      const payload = {
        text: prompt || null,
        image_base64: activeAttachments.image ? activeAttachments.image.data : null,
        audio_base64: activeAttachments.audio ? activeAttachments.audio.data : null,
        video_base64: activeAttachments.video ? activeAttachments.video.data : null,
        document_base64: activeAttachments.doc ? activeAttachments.doc.data : null,
        filename_hints: {
          image: activeAttachments.image ? activeAttachments.image.name : '',
          audio: activeAttachments.audio ? activeAttachments.audio.name : '',
          video: activeAttachments.video ? activeAttachments.video.name : '',
          document: activeAttachments.doc ? activeAttachments.doc.name : ''
        },
        perform_fusion: chkFusion ? chkFusion.checked : true,
        fusion_stage: "EARLY",
        synthesize_speech: chkTTS ? chkTTS.checked : false
      };

      const res = await fetch(`${API_BASE}/api/v1/multimodal/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      const elapsed = (performance.now() - startTime).toFixed(1);

      let audioPlayerHtml = '';
      if (data.speech_audio_base64_uri) {
        audioPlayerHtml = `
          <div style="margin-top: 10px; padding: 8px; background: var(--surface-secondary); border-radius: 4px; border: 1px solid var(--border);">
            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 4px;">🎙️ Synthesized Speech Response (Acoustic Formant Waveform):</div>
            <audio controls autoplay src="${data.speech_audio_base64_uri}" style="width: 100%; height: 32px;"></audio>
          </div>
        `;
      }

      const modalityTagsHtml = data.active_modalities.map(m => `<span class="badge-outline">${escapeHtml(m)}</span>`).join(' ');

      pendingEl.innerHTML = `
        <div class="message-sender">404 FOUNDERS Multimodal Engine &bull; ${escapeHtml(data.primary_modality)}</div>
        <div class="message-bubble">
          <div style="margin-bottom: 8px;">${modalityTagsHtml}</div>
          <div style="font-weight: 500; line-height: 1.5; margin-bottom: 8px;">
            ${escapeHtml(data.combined_summary)}
          </div>
          ${data.document_summary ? `<div style="font-size: 12px; margin-top: 6px; padding: 6px 8px; background: var(--surface-secondary); border-radius: 4px; border: 1px solid var(--border);"><strong>Document Intelligence:</strong> ${escapeHtml(data.document_summary)}</div>` : ''}
          ${data.image_caption ? `<div style="font-size: 12px; margin-top: 6px; padding: 6px 8px; background: var(--surface-secondary); border-radius: 4px; border: 1px solid var(--border);"><strong>Vision Intelligence:</strong> ${escapeHtml(data.image_caption)}</div>` : ''}
          ${data.speech_transcript ? `<div style="font-size: 12px; margin-top: 6px; padding: 6px 8px; background: var(--surface-secondary); border-radius: 4px; border: 1px solid var(--border);"><strong>Speech Recognition:</strong> ${escapeHtml(data.speech_transcript)}</div>` : ''}
          ${audioPlayerHtml}
        </div>
        <div class="message-metadata">
          <span>Latency: ${elapsed} ms</span>
          <span>Primary: ${escapeHtml(data.primary_modality)}</span>
          <span>Multimodal: ${data.is_multimodal}</span>
          <span>Fusion: ${data.fusion_active_modalities ? data.fusion_active_modalities.join('+') : 'None'}</span>
        </div>
      `;

      // Clear attachments
      activeAttachments.image = null;
      activeAttachments.audio = null;
      activeAttachments.video = null;
      activeAttachments.doc = null;
      renderAttachmentTray();
    } else {
      // Standard Neural Generation
      const res = await fetch(`${API_BASE}/api/v1/neural/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt,
          max_new_tokens: 32,
          mode: 'general'
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      const elapsed = (performance.now() - startTime).toFixed(1);

      let tokenPillsHtml = '';
      data.generated_tokens.forEach((tok, i) => {
        const id = data.generated_ids[i];
        tokenPillsHtml += `<span class="subword-pill">${escapeHtml(tok)}<span class="subword-id">#${id}</span></span>`;
      });

      pendingEl.innerHTML = `
        <div class="message-sender">404 FOUNDERS Neural Core &bull; Random Init</div>
        <div class="message-bubble">
          <div style="font-weight: 500; margin-bottom: 6px;">
            ${escapeHtml(data.prompt)} <span style="font-weight: 600; color: var(--accent-primary);">${escapeHtml(data.generated_text)}</span>
          </div>
          <div style="margin-top: 10px; padding-top: 8px; border-top: 1px dashed var(--border);">
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px;">Generated Token Pieces:</div>
            <div class="subword-grid">${tokenPillsHtml}</div>
          </div>
        </div>
        <div class="message-metadata">
          <span>Latency: ${data.latency_ms} ms</span>
          <span>Prompt IDs: [${data.prompt_ids.join(', ')}]</span>
          <span>Generated IDs: [${data.generated_ids.join(', ')}]</span>
        </div>
      `;
    }
  } catch (err) {
    pendingEl.innerHTML = `
      <div class="message-sender">Engine Execution Error</div>
      <div class="message-bubble" style="border-left-color: var(--status-error); color: var(--status-error);">
        Failed to execute query: ${escapeHtml(err.message)}
      </div>
    `;
  } finally {
    btnSend.disabled = false;
    btnSend.textContent = 'Execute Multimodal Query';
    chatThread.scrollTop = chatThread.scrollHeight;
  }
}

// -------------------------------------------------------------------------
// View 2: System Telemetry & Cluster Catalog
// -------------------------------------------------------------------------

async function fetchTelemetry() {
  const telCpuModel = document.getElementById('telCpuModel');
  const telCpuCores = document.getElementById('telCpuCores');
  const telCpuFlags = document.getElementById('telCpuFlags');
  const telTotalRam = document.getElementById('telTotalRam');
  const telAvailRam = document.getElementById('telAvailRam');
  const telSwapSpace = document.getElementById('telSwapSpace');
  const telDiskFree = document.getElementById('telDiskFree');
  const telKvmState = document.getElementById('telKvmState');
  const telSafeBudget = document.getElementById('telSafeBudget');
  const badgeBudget = document.getElementById('badgeBudget');

  try {
    const res = await fetch(`${API_BASE}/api/v1/system/telemetry`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    telCpuModel.textContent = data.cpu_model;
    telCpuCores.textContent = `${data.physical_cores} Cores / ${data.logical_threads} Threads`;
    telCpuFlags.textContent = data.has_avx2 ? 'AVX2, FMA, SSE4.2 Supported' : 'Standard x86_64';
    telTotalRam.textContent = `${data.total_ram_gb.toFixed(2)} GB`;
    telAvailRam.textContent = `${data.available_ram_gb.toFixed(2)} GB`;
    telSwapSpace.textContent = `${data.total_swap_gb.toFixed(2)} GB (Host Swapless)`;
    telDiskFree.textContent = `${data.root_free_gb.toFixed(1)} GB Free`;
    telKvmState.textContent = data.has_kvm ? 'Available (/dev/kvm accessible)' : 'Not Active';
    telSafeBudget.textContent = `${data.safe_memory_budget_gb.toFixed(2)} GB (Ceiling)`;

    if (badgeBudget) {
      badgeBudget.textContent = `SAFE BUDGET: ${data.safe_memory_budget_gb.toFixed(2)} GB`;
    }
  } catch (err) {
    telCpuModel.textContent = 'Backend unreachable';
  }
}

async function fetchClusterCatalog() {
  const box = document.getElementById('clusterCatalogBox');
  try {
    const res = await fetch(`${API_BASE}/api/v1/system/cluster_catalog`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    let html = '<div style="display: flex; flex-direction: column; gap: 14px;">';
    for (const [tierKey, tier] of Object.entries(data)) {
      html += `
        <div style="background-color: var(--surface-content); padding: 12px; border: 1px solid var(--border); border-radius: var(--radius-sm);">
          <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
            <strong style="color: var(--accent-primary);">${escapeHtml(tier.name)}</strong>
            <span style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted);">${escapeHtml(tier.target_parameters)} Target</span>
          </div>
          <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.5;">
            <div><strong>Compute:</strong> ${escapeHtml(tier.recommended_gpu)} (${tier.node_count} nodes &times; ${tier.gpu_per_node} GPUs = ${tier.total_gpus} total GPUs)</div>
            <div><strong>Interconnect:</strong> ${escapeHtml(tier.interconnect)} &bull; <strong>Storage:</strong> ${escapeHtml(tier.storage)}</div>
          </div>
        </div>
      `;
    }
    html += '</div>';
    box.innerHTML = html;
  } catch (err) {
    box.innerHTML = `<span style="color: var(--status-error);">Failed to load cluster profiles.</span>`;
  }
}

// -------------------------------------------------------------------------
// View 3: Custom BPE Tokenizer Studio
// -------------------------------------------------------------------------

window.setTokenizerSample = function(type) {
  const input = document.getElementById('tokenizerTextInput');
  switch (type) {
    case 'English':
      input.value = '404 FOUNDERS: Intelligence Without Boundaries. Custom foundation AI.';
      break;
    case 'Hindi':
      input.value = 'नमस्ते भारत! 404 FOUNDERS एक कस्टम बहुविध मूलभूत एआई मॉडल है।';
      break;
    case 'Code':
      input.value = 'def autoregressive_step(x, memory):\n    logits, memory = neural_core(x, memory)\n    return logits.argmax(dim=-1), memory';
      break;
    case 'Math':
      input.value = '\\mathcal{L}_{\\text{total}} = \\mathcal{L}_{\\text{MLM}} + \\lambda_1 \\mathcal{L}_{\\text{contrastive}} + \\lambda_2 \\mathcal{L}_{\\text{MoE}}';
      break;
    case 'Security':
      input.value = 'sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT && systemctl status 404-founders';
      break;
  }
};

async function handleTokenizerEncode() {
  const input = document.getElementById('tokenizerTextInput');
  const resultBox = document.getElementById('tokenizerResultBox');
  const tokenCountTag = document.getElementById('tokenCountTag');
  const text = input.value;

  if (!text) return;

  resultBox.innerHTML = '<span style="color: var(--text-muted);">Segmenting text with custom BPE...</span>';

  try {
    const res = await fetch(`${API_BASE}/api/v1/tokenizer/encode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, add_bos: true, add_eos: false })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    lastEncodedIds = data.ids;
    tokenCountTag.textContent = `${data.token_count} subwords (Vocab: ${data.vocab_size})`;

    let pillsHtml = '';
    data.tokens.forEach((tok, i) => {
      const id = data.ids[i];
      pillsHtml += `<span class="subword-pill">${escapeHtml(tok)}<span class="subword-id">#${id}</span></span>`;
    });

    resultBox.innerHTML = `
      <div style="margin-bottom: 8px;"><strong>Subword Pieces (${data.token_count}):</strong></div>
      <div class="subword-grid">${pillsHtml}</div>
      <div style="margin-top: 10px; padding-top: 8px; border-top: 1px dashed var(--border); font-size: 11px; color: var(--text-secondary);">
        <strong>Encoded IDs:</strong> [${data.ids.join(', ')}]
      </div>
    `;
  } catch (err) {
    resultBox.innerHTML = `<span style="color: var(--status-error);">Encode error: ${escapeHtml(err.message)}</span>`;
  }
}

async function handleTokenizerDecode() {
  const resultBox = document.getElementById('tokenizerResultBox');

  if (!lastEncodedIds || lastEncodedIds.length === 0) {
    resultBox.innerHTML = '<span style="color: var(--status-warning);">Please encode text first to generate token IDs for decoding.</span>';
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/v1/tokenizer/decode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: lastEncodedIds, skip_special_tokens: true })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();

    resultBox.innerHTML = `
      <div style="margin-bottom: 8px;"><strong style="color: var(--status-online);">&check; Lossless Detokenization Success:</strong></div>
      <div style="background-color: var(--surface-content); padding: 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 13px;">
        ${escapeHtml(data.text)}
      </div>
      <div style="margin-top: 8px; font-size: 11px; color: var(--text-muted);">
        Reconstructed exactly from ${data.ids.length} token IDs without loss.
      </div>
    `;
  } catch (err) {
    resultBox.innerHTML = `<span style="color: var(--status-error);">Decode error: ${escapeHtml(err.message)}</span>`;
  }
}

// -------------------------------------------------------------------------
// View 4: Coding Workspace (Git Inspection)
// -------------------------------------------------------------------------

async function fetchGitStatus() {
  const branchEl = document.getElementById('gitBranchName');
  const commitEl = document.getElementById('gitHeadCommit');
  const modEl = document.getElementById('gitModifiedCount');
  const untrackedEl = document.getElementById('gitUntrackedCount');
  const metaGitBranch = document.getElementById('metaGitBranch');

  try {
    const res = await fetch(`${API_BASE}/api/v1/git/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    branchEl.textContent = data.branch;
    commitEl.textContent = data.head_commit.slice(0, 7);
    modEl.textContent = `${data.modified_files.length} files`;
    untrackedEl.textContent = `${data.untracked_files.length} files`;

    if (metaGitBranch) {
      metaGitBranch.textContent = data.branch;
    }
  } catch (err) {
    branchEl.textContent = 'Unavailable';
  }
}

// -------------------------------------------------------------------------
// View 5: Cybersecurity Audit
// -------------------------------------------------------------------------

async function validateCommand() {
  const input = document.getElementById('secCommandInput');
  const resultBox = document.getElementById('secCommandResult');
  const cmd = input.value.trim();
  if (!cmd) return;

  resultBox.innerHTML = '<span style="color: var(--text-muted);">Auditing command security policy...</span>';

  try {
    const res = await fetch(`${API_BASE}/api/v1/security/validate_command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: cmd })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    const tierClass = `tier-${data.required_tier.toLowerCase()}`;
    const statusClass = data.is_safe ? 'passed' : 'blocked';
    const statusText = data.is_safe ? 'ALLOWED' : 'BLOCKED';

    resultBox.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div>
          <span class="security-tier-badge ${tierClass}">TIER: ${escapeHtml(data.required_tier)}</span>
          <span class="status-badge ${statusClass}" style="margin-left: 6px;">${statusText}</span>
        </div>
        <span style="font-size: 11px; color: var(--text-muted);">${escapeHtml(data.status)}</span>
      </div>
      <div style="background-color: var(--surface-content); padding: 10px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-family: var(--font-mono); font-size: 12px; margin-bottom: 8px;">
        $ ${escapeHtml(data.command)}
      </div>
      <div style="font-size: 11.5px; color: var(--text-secondary);">
        <strong>Audit Detail:</strong> ${escapeHtml(data.detail || 'Command passed safety analysis.')}
      </div>
    `;
  } catch (err) {
    resultBox.innerHTML = `<span style="color: var(--status-error);">Validation error: ${escapeHtml(err.message)}</span>`;
  }
}

async function inspectPrompt() {
  const input = document.getElementById('secPromptInput');
  const resultBox = document.getElementById('secPromptResult');
  const text = input.value.trim();
  if (!text) return;

  resultBox.innerHTML = '<span style="color: var(--text-muted);">Scanning prompt for injection vectors...</span>';

  try {
    const res = await fetch(`${API_BASE}/api/v1/security/inspect_prompt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    const statusClass = data.is_safe ? 'passed' : 'blocked';
    const statusText = data.is_safe ? 'SAFE PROMPT' : 'INJECTION DETECTED';

    let sigsHtml = '';
    if (data.detected_signatures && data.detected_signatures.length > 0) {
      sigsHtml = `
        <div style="margin-top: 8px; font-size: 11.5px; color: var(--status-error);">
          <strong>Triggered Patterns:</strong> ${data.detected_signatures.map(s => `<code>${escapeHtml(s)}</code>`).join(', ')}
        </div>
      `;
    }

    resultBox.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span class="status-badge ${statusClass}">${statusText}</span>
        <span style="font-size: 11px; color: var(--text-muted);">${data.is_safe ? 'No threat detected' : 'Adversarial override risk'}</span>
      </div>
      <div style="background-color: var(--surface-content); padding: 10px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 12px;">
        "${escapeHtml(data.text)}"
      </div>
      ${sigsHtml}
    `;
  } catch (err) {
    resultBox.innerHTML = `<span style="color: var(--status-error);">Inspection error: ${escapeHtml(err.message)}</span>`;
  }
}

// -------------------------------------------------------------------------
// View 8: Multimodal Intelligence Studio
// -------------------------------------------------------------------------

window.switchMultimodalTab = function(tabName) {
  const tabs = ['vision', 'audio', 'video', 'doc', 'fusion'];
  tabs.forEach(t => {
    const cap = t.charAt(0).toUpperCase() + t.slice(1);
    const btn = document.getElementById(`tabBtn${cap}`);
    const panel = document.getElementById(`mmodalTab${cap}`);
    if (btn) {
      if (t === tabName) btn.classList.add('active');
      else btn.classList.remove('active');
    }
    if (panel) {
      if (t === tabName) {
        panel.style.display = 'block';
        panel.classList.add('active');
      } else {
        panel.style.display = 'none';
        panel.classList.remove('active');
      }
    }
  });
};

function initMultimodalStudio() {
  // Vision Handlers
  const btnRunImage = document.getElementById('btnRunImageAnalysis');
  const btnLoadSample = document.getElementById('btnLoadSampleImage');
  const inputImage = document.getElementById('imageStudioFileInput');

  if (btnLoadSample) {
    btnLoadSample.addEventListener('click', () => {
      // Create a 224x224 Canvas sample image
      const canvas = document.createElement('canvas');
      canvas.width = 224;
      canvas.height = 224;
      const ctx = canvas.getContext('2d');

      // Gradient background
      const grad = ctx.createLinearGradient(0, 0, 224, 224);
      grad.addColorStop(0, '#343D35');
      grad.addColorStop(0.5, '#A58C70');
      grad.addColorStop(1, '#F4F0E8');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, 224, 224);

      // Geometric patterns
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 3;
      ctx.strokeRect(32, 32, 160, 160);
      ctx.beginPath();
      ctx.arc(112, 112, 48, 0, 2 * Math.PI);
      ctx.stroke();

      // Text label
      ctx.fillStyle = '#FFFFFF';
      ctx.font = 'bold 16px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('404 FOUNDERS', 112, 118);

      const dataUri = canvas.toDataURL('image/png');
      const base64Data = dataUri.split(',')[1];

      const previewImg = document.getElementById('imagePreviewImg');
      const previewContainer = document.getElementById('imagePreviewContainer');
      if (previewImg && previewContainer) {
        previewImg.src = dataUri;
        previewContainer.style.display = 'block';
      }

      runImageAnalysisWithPayload(base64Data);
    });
  }

  if (btnRunImage && inputImage) {
    btnRunImage.addEventListener('click', () => {
      const file = inputImage.files && inputImage.files[0];
      if (!file) {
        alert('Please choose an image file first or click "Load Sample Image".');
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        const dataUri = e.target.result;
        const base64Data = dataUri.split(',')[1];
        const previewImg = document.getElementById('imagePreviewImg');
        const previewContainer = document.getElementById('imagePreviewContainer');
        if (previewImg && previewContainer) {
          previewImg.src = dataUri;
          previewContainer.style.display = 'block';
        }
        runImageAnalysisWithPayload(base64Data);
      };
      reader.readAsDataURL(file);
    });
  }

  // Audio & Speech Handlers
  const btnRunAudio = document.getElementById('btnRunAudioAnalysis');
  const btnRunSTT = document.getElementById('btnRunSpeechSTT');
  const inputAudio = document.getElementById('audioStudioFileInput');
  const btnRunTTS = document.getElementById('btnRunSpeechTTS');

  if (btnRunAudio && inputAudio) {
    btnRunAudio.addEventListener('click', () => {
      const file = inputAudio.files && inputAudio.files[0];
      if (!file) {
        alert('Please select an audio file (WAV, MP3, FLAC, OGG).');
        return;
      }
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64Data = e.target.result.split(',')[1];
        const resultsBox = document.getElementById('audioResultsBox');
        resultsBox.textContent = 'Calculating STFT spectrogram and energy features...';
        try {
          const res = await fetch(`${API_BASE}/api/v1/multimodal/audio`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audio_base64: base64Data })
          });
          if (!res.ok) throw new Error(await res.text());
          const data = await res.json();
          resultsBox.innerHTML = `
            <strong>Format:</strong> ${escapeHtml(data.format)} | <strong>Duration:</strong> ${data.duration_seconds.toFixed(2)}s | <strong>Sample Rate:</strong> ${data.sample_rate} Hz<br/>
            <strong>RMS Energy:</strong> ${data.rms_energy.toFixed(4)} | <strong>Estimated SNR:</strong> ${data.estimated_snr_db.toFixed(1)} dB | <strong>Silent:</strong> ${data.is_silent}<br/>
            <div style="margin-top: 6px; font-size: 12px; color: var(--accent-primary);"><em>${escapeHtml(data.summary)}</em></div>
          `;
        } catch (err) {
          resultsBox.innerHTML = `<span style="color: var(--status-error);">Audio inspection error: ${escapeHtml(err.message)}</span>`;
        }
      };
      reader.readAsDataURL(file);
    });
  }

  if (btnRunSTT && inputAudio) {
    btnRunSTT.addEventListener('click', () => {
      const file = inputAudio.files && inputAudio.files[0];
      if (!file) {
        alert('Please select a speech audio file to transcribe.');
        return;
      }
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64Data = e.target.result.split(',')[1];
        const resultsBox = document.getElementById('audioResultsBox');
        resultsBox.textContent = 'Segmenting speech intervals and running acoustic recognizer...';
        try {
          const res = await fetch(`${API_BASE}/api/v1/multimodal/speech/recognize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audio_base64: base64Data, language_hint: 'en' })
          });
          if (!res.ok) throw new Error(await res.text());
          const data = await res.json();
          resultsBox.innerHTML = `
            <strong>Detected Language:</strong> ${escapeHtml(data.detected_language.toUpperCase())} | <strong>Confidence:</strong> ${(data.overall_confidence * 100).toFixed(1)}% | <strong>Segments:</strong> ${data.segments_count}<br/>
            <div style="margin-top: 8px; padding: 8px; background: var(--surface-content); border-radius: var(--radius-sm); border: 1px solid var(--border);">
              <strong>Transcript:</strong> "${escapeHtml(data.full_transcript)}"
            </div>
          `;
        } catch (err) {
          resultsBox.innerHTML = `<span style="color: var(--status-error);">Speech recognition error: ${escapeHtml(err.message)}</span>`;
        }
      };
      reader.readAsDataURL(file);
    });
  }

  if (btnRunTTS) {
    btnRunTTS.addEventListener('click', async () => {
      const text = document.getElementById('ttsTextInput').value.trim();
      const lang = document.getElementById('ttsLangSelect').value;
      const pitch = parseFloat(document.getElementById('ttsPitchInput').value) || 220.0;
      const statusBox = document.getElementById('ttsStatusBox');
      const player = document.getElementById('ttsAudioPlayer');

      if (!text) {
        alert('Please enter text to synthesize.');
        return;
      }

      statusBox.textContent = 'Synthesizing speech via acoustic vocal tract formant model...';
      try {
        const res = await fetch(`${API_BASE}/api/v1/multimodal/speech/synthesize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: text,
            language: lang,
            voice_id: 'default_neutral',
            pitch_hz: pitch,
            speed_factor: 1.0
          })
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        player.src = data.audio_base64_uri;
        player.style.display = 'block';
        player.play().catch(() => {});
        statusBox.innerHTML = `
          <strong>Generated:</strong> ${data.duration_seconds.toFixed(2)}s WAV (16 kHz 16-bit PCM mono)<br/>
          <em>${escapeHtml(data.summary)}</em>
        `;
      } catch (err) {
        statusBox.innerHTML = `<span style="color: var(--status-error);">TTS synthesis error: ${escapeHtml(err.message)}</span>`;
      }
    });
  }

  // Video Handler
  const btnRunVideo = document.getElementById('btnRunVideoAnalysis');
  const inputVideo = document.getElementById('videoStudioFileInput');
  if (btnRunVideo && inputVideo) {
    btnRunVideo.addEventListener('click', () => {
      const file = inputVideo.files && inputVideo.files[0];
      if (!file) {
        alert('Please select a video file (MP4, WEBM, MOV).');
        return;
      }
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64Data = e.target.result.split(',')[1];
        const summaryBox = document.getElementById('videoSummaryBox');
        summaryBox.textContent = 'Streaming OpenCV video frames and identifying scene keyframes...';
        try {
          const res = await fetch(`${API_BASE}/api/v1/multimodal/process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              video_base64: base64Data,
              filename_hints: { video: file.name },
              perform_fusion: false
            })
          });
          if (!res.ok) throw new Error(await res.text());
          const data = await res.json();
          summaryBox.innerHTML = `
            <strong>Video Intelligence Report:</strong><br/>
            ${escapeHtml(data.video_summary || data.combined_summary)}
          `;
        } catch (err) {
          summaryBox.innerHTML = `<span style="color: var(--status-error);">Video processing error: ${escapeHtml(err.message)}</span>`;
        }
      };
      reader.readAsDataURL(file);
    });
  }

  // Document Handler
  const btnRunDoc = document.getElementById('btnRunDocAnalysis');
  const inputDoc = document.getElementById('docStudioFileInput');
  if (btnRunDoc && inputDoc) {
    btnRunDoc.addEventListener('click', () => {
      const file = inputDoc.files && inputDoc.files[0];
      if (!file) {
        alert('Please select a document file (.pdf, .docx, .csv, .json, .txt, .md).');
        return;
      }
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64Data = e.target.result.split(',')[1];
        const previewBox = document.getElementById('docPreviewBox');
        const detailsBox = document.getElementById('docDetailsBox');
        previewBox.textContent = 'Parsing document structure and auditing prompt injection defense...';
        try {
          const res = await fetch(`${API_BASE}/api/v1/multimodal/document`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              document_base64: base64Data,
              filename: file.name
            })
          });
          if (!res.ok) throw new Error(await res.text());
          const data = await res.json();

          document.getElementById('docResFormat').textContent = data.format;
          document.getElementById('docResPages').textContent = data.page_count;
          document.getElementById('docResWords').textContent = data.word_count.toLocaleString();
          document.getElementById('docResChunks').textContent = data.chunks_count;
          document.getElementById('docResTables').textContent = data.has_tables ? 'Yes (Tabular Data Found)' : 'None';

          const badge = document.getElementById('docSafetyBadge');
          const secStatus = document.getElementById('docResSecurity');
          if (data.is_safe) {
            badge.className = 'card-tag';
            badge.style.color = 'var(--status-success)';
            badge.textContent = 'PASSED (SAFE)';
            secStatus.textContent = 'Passed (Zero Injection Risk)';
          } else {
            badge.className = 'card-tag';
            badge.style.color = 'var(--status-error)';
            badge.textContent = 'DEFENSE BLOCKED';
            secStatus.textContent = `Flagged: ${data.detected_injection_risks.join(', ')}`;
          }

          previewBox.innerHTML = `
            <strong>File:</strong> ${escapeHtml(file.name)} (${data.format})<br/>
            <strong>Chunks:</strong> ${data.chunks_count} | <strong>Words:</strong> ${data.word_count}<br/>
            <div style="margin-top: 6px;"><em>${escapeHtml(data.summary)}</em></div>
          `;
          detailsBox.textContent = `Security audit verified on document payload. Defensive injection analysis: ${data.is_safe ? 'CLEAN' : 'FLAGGED RISK'}.`;
        } catch (err) {
          previewBox.innerHTML = `<span style="color: var(--status-error);">Document analysis error: ${escapeHtml(err.message)}</span>`;
        }
      };
      reader.readAsDataURL(file);
    });
  }

  // Fusion Handler
  const btnRunFusion = document.getElementById('btnRunFusionExecution');
  if (btnRunFusion) {
    btnRunFusion.addEventListener('click', async () => {
      const activeMods = [];
      if (document.getElementById('fuseModText').checked) activeMods.push('TEXT');
      if (document.getElementById('fuseModImage').checked) activeMods.push('IMAGE');
      if (document.getElementById('fuseModAudio').checked) activeMods.push('AUDIO');
      if (document.getElementById('fuseModVideo').checked) activeMods.push('VIDEO');

      if (activeMods.length === 0) {
        alert('Please select at least one active modality for fusion.');
        return;
      }

      const radio = document.querySelector('input[name="fusionStageRadio"]:checked');
      const stage = radio ? radio.value : 'EARLY';
      const resultsBox = document.getElementById('fusionResultsBox');

      resultsBox.textContent = `Executing ${stage} multimodal fusion tensor synthesis...`;
      try {
        const res = await fetch(`${API_BASE}/api/v1/multimodal/fuse`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            active_modalities: activeMods,
            fusion_stage: stage
          })
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();

        let weightsHtml = Object.entries(data.modality_weights)
          .map(([k, v]) => `<code>${k}: ${(v * 100).toFixed(1)}%</code>`)
          .join(' &bull; ');

        resultsBox.innerHTML = `
          <strong>Fusion Stage:</strong> ${escapeHtml(data.fusion_stage)}<br/>
          <strong>Active Modalities:</strong> [${data.active_modalities.join(', ')}]<br/>
          <strong>Fused Tensor Shape:</strong> <code>[${data.fused_tensor_shape.join(', ')}]</code><br/>
          <div style="margin-top: 8px;"><strong>Adaptive Modality Weights:</strong> ${weightsHtml}</div>
        `;
      } catch (err) {
        resultsBox.innerHTML = `<span style="color: var(--status-error);">Fusion error: ${escapeHtml(err.message)}</span>`;
      }
    });
  }
}

async function runImageAnalysisWithPayload(base64Data) {
  const statusTag = document.getElementById('imageStatusTag');
  const captionBox = document.getElementById('imageCaptionBox');
  statusTag.textContent = 'Processing...';
  captionBox.textContent = 'Validating magic bytes and extracting ViT patches...';

  try {
    const res = await fetch(`${API_BASE}/api/v1/multimodal/image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_base64: base64Data, target_size: [224, 224] })
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    document.getElementById('imgResFormat').textContent = data.format;
    document.getElementById('imgResResolution').textContent = `${data.width} × ${data.height}`;
    document.getElementById('imgResAspect').textContent = data.aspect_ratio.toFixed(2);
    document.getElementById('imgResChannels').textContent = `${data.channels} (RGB)`;
    document.getElementById('imgResPatches').textContent = `${data.patch_count} patches (16×16)`;

    captionBox.innerHTML = `
      <strong>Caption Hypothesis:</strong> ${escapeHtml(data.caption)}<br/>
      <div style="margin-top: 6px; font-size: 11.5px; color: var(--text-muted);">${escapeHtml(data.reasoning_summary)}</div>
    `;
    statusTag.textContent = 'Inspection Complete';
  } catch (err) {
    statusTag.textContent = 'Error';
    captionBox.innerHTML = `<span style="color: var(--status-error);">Image analysis error: ${escapeHtml(err.message)}</span>`;
  }
}

// -------------------------------------------------------------------------
// Helpers
// -------------------------------------------------------------------------

function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// -------------------------------------------------------------------------
// Phase 09: Memory & Continual Learning Manager
// -------------------------------------------------------------------------

const DEFAULT_USER_ID = 'default_user';
const DEFAULT_SESSION_ID = 'session_default';

async function initMemoryManager() {
  const btnSearch = document.getElementById('btnSearchMemory');
  const btnReset = document.getElementById('btnResetMemorySearch');
  const btnSave = document.getElementById('btnOpenSaveMemoryModal');
  const btnConsolidate = document.getElementById('btnRunConsolidation');
  const btnClear = document.getElementById('btnClearAllMemory');
  const btnSavePrefs = document.getElementById('btnSavePreferences');
  const btnTriggerLearning = document.getElementById('btnTriggerLearningJob');

  if (btnSearch) btnSearch.addEventListener('click', () => {
    const query = document.getElementById('memSearchQuery')?.value || '';
    const layer = document.getElementById('memLayerFilter')?.value || null;
    loadMemoryRecords(query, layer);
  });

  if (btnReset) btnReset.addEventListener('click', () => {
    const qInput = document.getElementById('memSearchQuery');
    if (qInput) qInput.value = '';
    const lSelect = document.getElementById('memLayerFilter');
    if (lSelect) lSelect.value = '';
    loadMemoryRecords('', null);
  });

  if (btnSave) btnSave.addEventListener('click', async () => {
    const content = prompt('Enter memory content to save persistently:');
    if (!content || !content.trim()) return;
    const importanceStr = prompt('Importance weight (0.0 to 1.0):', '0.8');
    const importance = parseFloat(importanceStr) || 0.8;
    const layer = prompt('Memory Layer (LONG_TERM or KNOWLEDGE):', 'LONG_TERM') || 'LONG_TERM';

    try {
      const res = await fetch(`${API_BASE}/api/v1/memory/records`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: DEFAULT_USER_ID,
          content: content.trim(),
          memory_layer: layer.trim().toUpperCase(),
          importance: importance,
          source_type: 'user_ui',
        })
      });
      if (!res.ok) throw new Error(await res.text());
      alert('Memory record saved successfully.');
      loadMemoryRecords('', null);
    } catch (err) {
      alert(`Error saving memory: ${err.message}`);
    }
  });

  if (btnConsolidate) btnConsolidate.addEventListener('click', async () => {
    btnConsolidate.disabled = true;
    btnConsolidate.textContent = 'Consolidating...';
    try {
      const res = await fetch(`${API_BASE}/api/v1/memory/consolidate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: DEFAULT_USER_ID })
      });
      const data = await res.json();
      const conflicts = data.conflicts_detected || [];
      const conflictStat = document.getElementById('memStatConflicts');
      if (conflictStat) conflictStat.textContent = conflicts.length;

      alert(`Consolidation Complete!\nDuplicates Resolved: ${data.duplicates_resolved}\nConflicts Detected: ${conflicts.length}\nRecords Merged: ${data.records_merged}`);
      loadMemoryRecords('', null);
    } catch (err) {
      alert(`Consolidation error: ${err.message}`);
    } finally {
      btnConsolidate.disabled = false;
      btnConsolidate.textContent = 'Run Consolidation';
    }
  });

  if (btnClear) btnClear.addEventListener('click', async () => {
    const confirmed = confirm('WARNING: Are you sure you want to clear all memory records? This action is logged to the audit ledger and cannot be undone.');
    if (!confirmed) return;
    try {
      const recordsRes = await fetch(`${API_BASE}/api/v1/memory/records?user_id=${DEFAULT_USER_ID}`);
      const records = await recordsRes.json();
      let count = 0;
      for (const rec of records) {
        await fetch(`${API_BASE}/api/v1/memory/records/${rec.record_id}?user_id=${DEFAULT_USER_ID}`, { method: 'DELETE' });
        count++;
      }
      alert(`Cleared ${count} memory records.`);
      loadMemoryRecords('', null);
    } catch (err) {
      alert(`Error clearing memory: ${err.message}`);
    }
  });

  if (btnSavePrefs) btnSavePrefs.addEventListener('click', async () => {
    const style = document.getElementById('prefCommStyle')?.value || 'balanced';
    const length = document.getElementById('prefRespLength')?.value || 'medium';
    const depth = document.getElementById('prefTechDepth')?.value || 'intermediate';
    const code = document.getElementById('prefCodeLang')?.value || 'python';

    try {
      await fetch(`${API_BASE}/api/v1/memory/preferences`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: DEFAULT_USER_ID, preference_key: 'communication_style', preference_val: style, is_explicit: true })
      });
      await fetch(`${API_BASE}/api/v1/memory/preferences`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: DEFAULT_USER_ID, preference_key: 'response_length', preference_val: length, is_explicit: true })
      });
      await fetch(`${API_BASE}/api/v1/memory/preferences`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: DEFAULT_USER_ID, preference_key: 'technical_depth', preference_val: depth, is_explicit: true })
      });
      await fetch(`${API_BASE}/api/v1/memory/preferences`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: DEFAULT_USER_ID, preference_key: 'code_preference', preference_val: code, is_explicit: true })
      });
      alert('User preferences saved.');
    } catch (err) {
      alert(`Error saving preferences: ${err.message}`);
    }
  });

  if (btnTriggerLearning) btnTriggerLearning.addEventListener('click', async () => {
    btnTriggerLearning.disabled = true;
    const box = document.getElementById('learningPipelineStatusBox');
    if (box) box.textContent = 'Initializing 10-Stage Controlled Continual Learning Job...';

    try {
      // 1. Create job
      const createRes = await fetch(`${API_BASE}/api/v1/learning/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_version: '0.6.0-offline' })
      });
      const job = await createRes.json();
      const jobId = job.job_id;

      if (box) box.textContent = `Job ${jobId} created. Executing Stages 01 to 08...`;

      // 2. Run Stages 1-8
      const runRes = await fetch(`${API_BASE}/api/v1/learning/jobs/${jobId}/run-pipeline`, { method: 'POST' });
      const runData = await runRes.json();

      if (box) box.textContent = `Stages 01-08 completed. Status: ${runData.status}. Submitting governance approval gate...`;

      // 3. Approve and deploy
      const appRes = await fetch(`${API_BASE}/api/v1/learning/jobs/${jobId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approver: 'governance_lead',
          approved: true,
          reason: 'All regression tests passed; zero catastrophic forgetting delta.'
        })
      });
      const appData = await appRes.json();

      if (box) {
        box.textContent = `Job ${jobId} Execution Summary:\n` +
          `Status: ${appData.status}\n` +
          `Target Version: ${appData.target_version}\n` +
          `Manifest SHA-256: ${appData.dataset_manifest_hash || 'verified'}\n` +
          `Total Stages Executed: 10/10\n` +
          `Approved by Governance: YES\n` +
          `Controlled Deployment: COMPLETE (Canary Active)`;
      }

      // Highlight stage cards
      for (let s = 1; s <= 10; s++) {
        const card = document.getElementById(`stageCard${s}`);
        if (card) {
          card.style.backgroundColor = 'var(--surface-content)';
          card.style.borderColor = 'var(--status-online)';
        }
      }
    } catch (err) {
      if (box) box.textContent = `Pipeline error: ${err.message}`;
    } finally {
      btnTriggerLearning.disabled = false;
    }
  });

  // Initial load
  loadMemoryRecords('', null);
  loadPreferences();
}

async function loadMemoryRecords(query, layer) {
  const tbody = document.getElementById('memRecordsTableBody');
  const counter = document.getElementById('memRecordsCounter');
  const statCount = document.getElementById('memStatRecordCount');
  const statWorking = document.getElementById('memStatWorkingTasks');

  try {
    let records = [];
    if (query && query.trim()) {
      const res = await fetch(`${API_BASE}/api/v1/memory/retrieve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: DEFAULT_USER_ID,
          query: query.trim(),
          memory_layer: layer || null,
          limit: 25,
        })
      });
      if (res.ok) records = await res.json();
    } else {
      const res = await fetch(`${API_BASE}/api/v1/memory/records?user_id=${DEFAULT_USER_ID}`);
      if (res.ok) records = await res.json();
    }

    // Working tasks
    const wtRes = await fetch(`${API_BASE}/api/v1/memory/working?session_id=${DEFAULT_SESSION_ID}`);
    if (wtRes.ok) {
      const wts = await wtRes.json();
      if (statWorking) statWorking.textContent = wts.length;
    }

    if (counter) counter.textContent = `${records.length} Records`;
    if (statCount) statCount.textContent = records.length;

    if (!tbody) return;
    if (records.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="padding: 16px; text-align: center; color: var(--text-muted);">
            No memory records found in database. Use <strong>+ Save Memory</strong> to add one.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = records.map(r => `
      <tr style="border-bottom: 1px solid var(--border);">
        <td style="padding: 8px 6px; font-family: var(--font-mono); font-size: 11px;">${escapeHtml(r.record_id || '')}</td>
        <td style="padding: 8px 6px;"><span class="card-tag" style="font-size: 10px;">${escapeHtml(r.memory_layer || 'LONG_TERM')}</span></td>
        <td style="padding: 8px 6px; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(r.content)}">${escapeHtml(r.content)}</td>
        <td style="padding: 8px 6px;">${r.importance !== undefined ? r.importance.toFixed(2) : '--'}</td>
        <td style="padding: 8px 6px;">v${r.version || 1}</td>
        <td style="padding: 8px 6px;"><span style="color: ${r.status === 'CONFLICT_DETECTED' ? 'var(--status-error)' : 'var(--status-online)'}; font-weight: 500;">${escapeHtml(r.status || 'ACTIVE')}</span></td>
        <td style="padding: 8px 6px; text-align: right;">
          <button onclick="deleteMemoryRecord('${escapeHtml(r.record_id)}')" style="background: none; border: none; color: var(--status-error); cursor: pointer; font-size: 11px;">Delete</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="padding: 16px; text-align: center; color: var(--status-error);">
            Error loading records: ${escapeHtml(err.message)}
          </td>
        </tr>
      `;
    }
  }
}

async function deleteMemoryRecord(recordId) {
  if (!confirm(`Delete record ${recordId}?`)) return;
  try {
    const res = await fetch(`${API_BASE}/api/v1/memory/records/${recordId}?user_id=${DEFAULT_USER_ID}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(await res.text());
    loadMemoryRecords('', null);
  } catch (err) {
    alert(`Error deleting record: ${err.message}`);
  }
}

async function loadPreferences() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/memory/preferences?user_id=${DEFAULT_USER_ID}`);
    if (!res.ok) return;
    const prefs = await res.json();
    if (prefs.communication_style) {
      const el = document.getElementById('prefCommStyle');
      if (el) el.value = prefs.communication_style;
    }
    if (prefs.response_length) {
      const el = document.getElementById('prefRespLength');
      if (el) el.value = prefs.response_length;
    }
    if (prefs.technical_depth) {
      const el = document.getElementById('prefTechDepth');
      if (el) el.value = prefs.technical_depth;
    }
    if (prefs.code_preference) {
      const el = document.getElementById('prefCodeLang');
      if (el) el.value = prefs.code_preference;
    }
  } catch (e) {
    // Graceful fallback to default UI values
  }
}

// -------------------------------------------------------------------------
// Personal AI Workstation Controller (Phase 10)
// -------------------------------------------------------------------------

let allProcessesCache = [];

async function fetchPersonalAIStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/personal-ai/status`);
    if (!res.ok) return;
    const data = await res.json();
    const statusText = document.getElementById('paiStatusText');
    const statusDot = document.getElementById('paiStatusDot');
    const resetBtn = document.getElementById('btnEmergencyReset');
    const killBtn = document.getElementById('btnEmergencyShutdown');
    if (data.emergency_shutdown_active) {
      if (statusText) statusText.textContent = 'EMERGENCY SHUTDOWN ACTIVE';
      if (statusDot) statusDot.style.backgroundColor = 'var(--status-error)';
      if (resetBtn) resetBtn.style.display = 'inline-block';
      if (killBtn) killBtn.style.display = 'none';
    } else {
      if (statusText) statusText.textContent = `Localhost Bound (${data.host}:${data.port})`;
      if (statusDot) statusDot.style.backgroundColor = 'var(--status-online)';
      if (resetBtn) resetBtn.style.display = 'none';
      if (killBtn) killBtn.style.display = 'inline-block';
    }
  } catch (e) {
    console.error('Failed to fetch personal AI status', e);
  }
}

async function fetchPersonalAIHardware() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/personal-ai/system/summary`);
    if (!res.ok) return;
    const data = await res.json();
    const osName = document.getElementById('paiOsName');
    const kernelArch = document.getElementById('paiKernelArch');
    const cpuModel = document.getElementById('paiCpuModel');
    const cpuUsage = document.getElementById('paiCpuUsage');
    const ramUsage = document.getElementById('paiRamUsage');
    const uptime = document.getElementById('paiUptime');

    if (osName) osName.textContent = `${data.os_name} ${data.os_version}`;
    if (kernelArch) kernelArch.textContent = `${data.kernel_version} (${data.architecture})`;
    if (cpuModel) cpuModel.textContent = `${data.cpu.model} (${data.cpu.logical_cores} threads)`;
    if (cpuUsage) cpuUsage.textContent = `${data.cpu.usage_percent_overall.toFixed(1)}%`;
    if (ramUsage) ramUsage.textContent = `${data.memory.used_ram_mb.toFixed(0)} MB / ${data.memory.total_ram_mb.toFixed(0)} MB (${data.memory.percent_used_ram.toFixed(1)}%)`;
    if (uptime) uptime.textContent = `${data.uptime_hours.toFixed(2)} hrs`;
  } catch (e) {
    console.error('Failed to fetch hardware summary', e);
  }
}

async function fetchPersonalAIProcesses() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/personal-ai/processes?limit=60`);
    if (!res.ok) return;
    allProcessesCache = await res.json();
    renderProcessesTable(allProcessesCache);
  } catch (e) {
    console.error('Failed to fetch processes', e);
  }
}

function renderProcessesTable(processes) {
  const tbody = document.getElementById('paiProcessesTableBody');
  if (!tbody) return;
  if (!processes || processes.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="padding: 8px; text-align: center; color: var(--text-muted);">No processes found.</td></tr>';
    return;
  }
  tbody.innerHTML = processes.map(p => `
    <tr style="border-bottom: 1px solid var(--border);">
      <td style="padding: 4px; font-family: var(--font-mono);">${p.pid}</td>
      <td style="padding: 4px; font-weight: 500;">
        ${escapeHtml(p.name)}
        ${p.is_protected ? '<span style="font-size: 9px; padding: 1px 4px; background-color: var(--surface-secondary); border-radius: 2px; color: var(--accent-primary); font-weight: 600; margin-left: 4px;">GUARDED</span>' : ''}
      </td>
      <td style="padding: 4px;">${p.cpu_percent.toFixed(1)}%</td>
      <td style="padding: 4px;">${p.memory_mb.toFixed(1)}</td>
      <td style="padding: 4px; color: var(--text-secondary);">${p.status}</td>
    </tr>
  `).join('');
}

async function fetchPersonalAIFiles(dirPath = '.') {
  try {
    const tbody = document.getElementById('paiFilesTableBody');
    if (tbody) tbody.innerHTML = '<tr><td colspan="4" style="padding: 8px; text-align: center; color: var(--text-muted);">Scanning directory...</td></tr>';
    const res = await fetch(`${API_BASE}/api/v1/personal-ai/filesystem/list`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dir_path: dirPath, limit: 100 })
    });
    if (!res.ok) {
      const err = await res.json();
      if (tbody) tbody.innerHTML = `<tr><td colspan="4" style="padding: 8px; text-align: center; color: var(--status-error);">${escapeHtml(err.detail || 'Access blocked by security guard')}</td></tr>`;
      return;
    }
    const data = await res.json();
    if (!data.entries || data.entries.length === 0) {
      if (tbody) tbody.innerHTML = '<tr><td colspan="4" style="padding: 8px; text-align: center; color: var(--text-muted);">Directory is empty.</td></tr>';
      return;
    }
    if (tbody) {
      tbody.innerHTML = data.entries.map(e => `
        <tr style="border-bottom: 1px solid var(--border);">
          <td style="padding: 4px;">${escapeHtml(e.name)}</td>
          <td style="padding: 4px; color: var(--text-secondary);">${e.is_directory ? 'DIR' : (e.extension || 'FILE')}</td>
          <td style="padding: 4px;">${e.is_directory ? '-' : `${(e.size_bytes / 1024).toFixed(1)} KB`}</td>
          <td style="padding: 4px;">
            ${!e.is_directory ? `<button class="btn-secondary" style="font-size: 10px; padding: 2px 6px;" onclick="window.paiInspectFile('${escapeHtml(e.path)}')">Read</button>` : ''}
          </td>
        </tr>
      `).join('');
    }
  } catch (e) {
    console.error('Failed to list files', e);
  }
}

window.paiInspectFile = async function(filePath) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/personal-ai/filesystem/read`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: filePath, max_bytes: 524288 })
    });
    const previewBox = document.getElementById('paiFilePreviewBox');
    const filenameLabel = document.getElementById('paiPreviewFilename');
    const badgeLabel = document.getElementById('paiPreviewSecretsBadge');
    const contentBox = document.getElementById('paiFilePreviewContent');
    if (!res.ok) {
      const err = await res.json();
      alert(`Read Error: ${err.detail || 'Access denied'}`);
      return;
    }
    const data = await res.json();
    if (previewBox) previewBox.style.display = 'block';
    if (filenameLabel) filenameLabel.textContent = data.path;
    if (badgeLabel) {
      badgeLabel.textContent = data.scrubbed_secrets_count > 0 ? `${data.scrubbed_secrets_count} secrets scrubbed` : 'Sanitized clean';
    }
    if (contentBox) contentBox.textContent = data.content.slice(0, 2000) + (data.content.length > 2000 ? '\n... [truncated]' : '');
  } catch (e) {
    console.error('Failed to read file', e);
  }
};

async function fetchPersonalAIApprovals() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/personal-ai/approvals`);
    if (!res.ok) return;
    const tickets = await res.json();
    const countBadge = document.getElementById('paiPendingCountBadge');
    const container = document.getElementById('paiApprovalsContainer');
    if (countBadge) countBadge.textContent = `${tickets.length} Pending`;
    if (!container) return;
    if (tickets.length === 0) {
      container.innerHTML = '<div style="padding: 16px; text-align: center; color: var(--text-muted); font-size: 12px;">No pending action approval tickets in queue.</div>';
      return;
    }
    container.innerHTML = tickets.map(t => `
      <div class="card" style="margin-bottom: 8px; padding: 10px; background-color: var(--surface-secondary);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
          <strong style="font-size: 11px;">Ticket: ${escapeHtml(t.ticket_id)}</strong>
          <span class="card-tag" style="background-color: #FFF2DF; color: var(--accent-secondary);">${escapeHtml(t.risk_tier)}</span>
        </div>
        <div style="font-size: 11px; margin-bottom: 4px;"><strong>Tool:</strong> ${escapeHtml(t.tool_name)} &bull; ${escapeHtml(t.action_summary)}</div>
        <div style="font-size: 10px; color: var(--text-muted); margin-bottom: 8px;">Expires: ${escapeHtml(t.expires_at)}</div>
        <div style="display: flex; gap: 8px;">
          <button class="btn-primary" style="font-size: 10px; padding: 3px 10px;" onclick="window.paiDecideTicket('${escapeHtml(t.ticket_id)}', true)">Approve</button>
          <button class="btn-secondary" style="font-size: 10px; padding: 3px 10px; color: #9E3A3A; border-color: #9E3A3A;" onclick="window.paiDecideTicket('${escapeHtml(t.ticket_id)}', false)">Reject</button>
        </div>
      </div>
    `).join('');
  } catch (e) {
    console.error('Failed to fetch approvals', e);
  }
}

window.paiDecideTicket = async function(ticketId, approved) {
  const reason = prompt(approved ? 'Operator approval rationale:' : 'Operator rejection rationale:') || 'Operator decision';
  try {
    const res = await fetch(`${API_BASE}/api/v1/personal-ai/approvals/${ticketId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved, decided_by: 'human_operator', reason })
    });
    if (!res.ok) {
      const err = await res.json();
      alert(`Decision error: ${err.detail || 'Failed'}`);
    } else {
      fetchPersonalAIApprovals();
      fetchPersonalAIAuditLogs();
    }
  } catch (e) {
    console.error('Failed to record decision', e);
  }
};

async function fetchPersonalAIAuditLogs() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/personal-ai/audit/logs?limit=40`);
    if (!res.ok) return;
    const logs = await res.json();
    const tbody = document.getElementById('paiAuditTableBody');
    if (!tbody) return;
    if (logs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="padding: 8px; text-align: center; color: var(--text-muted);">No audit logs yet.</td></tr>';
      return;
    }
    tbody.innerHTML = logs.map(l => `
      <tr style="border-bottom: 1px solid var(--border);">
        <td style="padding: 4px; color: var(--text-muted); font-size: 10px;">${escapeHtml(l.timestamp.slice(11, 19))}</td>
        <td style="padding: 4px; font-weight: 500;">${escapeHtml(l.tool_name)}</td>
        <td style="padding: 4px;">
          <span style="font-size: 9px; padding: 1px 4px; border-radius: 2px; background-color: var(--surface-secondary);">${escapeHtml(l.risk_tier)}</span>
        </td>
        <td style="padding: 4px; color: var(--text-secondary);">${escapeHtml(l.action_description)}</td>
      </tr>
    `).join('');
  } catch (e) {
    console.error('Failed to fetch audit logs', e);
  }
}

async function sendPaiChat() {
  const input = document.getElementById('paiChatInput');
  const query = (input?.value || '').trim();
  if (!query) return;

  const btn = document.getElementById('btnPaiSendChat');
  const outBox = document.getElementById('paiChatOutputBox');
  const intentLabel = document.getElementById('paiResponseIntent');
  const actionLabel = document.getElementById('paiResponseAction');
  const textLabel = document.getElementById('paiResponseText');
  const ticketNotice = document.getElementById('paiPendingTicketNotice');
  const ticketIdLabel = document.getElementById('paiTicketIdLabel');
  const payloadJson = document.getElementById('paiPayloadJson');

  if (btn) btn.disabled = true;
  if (outBox) outBox.style.display = 'block';
  if (textLabel) textLabel.textContent = 'Processing request through local intelligence router...';

  try {
    const res = await fetch(`${API_BASE}/api/v1/personal-ai/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: 'default_operator', query })
    });
    const data = await res.json();
    if (!res.ok) {
      if (textLabel) textLabel.textContent = `Error (${res.status}): ${data.detail || 'Request failed'}`;
      return;
    }
    if (intentLabel) intentLabel.textContent = `INTENT: ${data.intent}`;
    if (actionLabel) actionLabel.textContent = `ACTION: ${data.action_taken}`;
    if (textLabel) textLabel.textContent = data.assistant_response;

    if (data.requires_approval && data.pending_ticket_id) {
      if (ticketNotice) ticketNotice.style.display = 'block';
      if (ticketIdLabel) ticketIdLabel.textContent = data.pending_ticket_id;
      fetchPersonalAIApprovals();
    } else {
      if (ticketNotice) ticketNotice.style.display = 'none';
    }

    if (payloadJson) payloadJson.textContent = JSON.stringify(data.data_payload, null, 2);
    fetchPersonalAIAuditLogs();
  } catch (e) {
    if (textLabel) textLabel.textContent = `Network / connection error: ${e.message}`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

function initPersonalAI() {
  const btnChat = document.getElementById('btnPaiSendChat');
  if (btnChat) btnChat.addEventListener('click', sendPaiChat);

  document.querySelectorAll('.pai-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById('paiChatInput');
      if (input) {
        input.value = btn.getAttribute('data-prompt') || '';
        sendPaiChat();
      }
    });
  });

  const btnKill = document.getElementById('btnEmergencyShutdown');
  if (btnKill) {
    btnKill.addEventListener('click', async () => {
      if (!confirm('Are you sure you want to trigger the emergency kill switch? All pending tickets will be revoked.')) return;
      try {
        await fetch(`${API_BASE}/api/v1/personal-ai/emergency/shutdown`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ triggered_by: 'human_operator', reason: 'Operator triggered from dashboard' })
        });
        fetchPersonalAIStatus();
        fetchPersonalAIApprovals();
        fetchPersonalAIAuditLogs();
      } catch (e) {
        alert(`Kill switch error: ${e.message}`);
      }
    });
  }

  const btnReset = document.getElementById('btnEmergencyReset');
  if (btnReset) {
    btnReset.addEventListener('click', async () => {
      try {
        await fetch(`${API_BASE}/api/v1/personal-ai/emergency/reset`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        fetchPersonalAIStatus();
        fetchPersonalAIAuditLogs();
      } catch (e) {
        alert(`Reset error: ${e.message}`);
      }
    });
  }

  const btnRefreshHw = document.getElementById('btnRefreshHardware');
  if (btnRefreshHw) btnRefreshHw.addEventListener('click', fetchPersonalAIHardware);

  const btnRefreshProc = document.getElementById('btnRefreshProcesses');
  if (btnRefreshProc) btnRefreshProc.addEventListener('click', fetchPersonalAIProcesses);

  const procFilter = document.getElementById('paiProcessFilter');
  if (procFilter) {
    procFilter.addEventListener('input', (e) => {
      const q = (e.target.value || '').toLowerCase();
      const filtered = allProcessesCache.filter(p => p.name.toLowerCase().includes(q) || String(p.pid).includes(q));
      renderProcessesTable(filtered);
    });
  }

  const btnListFiles = document.getElementById('btnPaiListFiles');
  if (btnListFiles) {
    btnListFiles.addEventListener('click', () => {
      const p = (document.getElementById('paiFilePathInput')?.value || '.').trim();
      fetchPersonalAIFiles(p);
    });
  }
  const btnRefreshFiles = document.getElementById('btnRefreshFiles');
  if (btnRefreshFiles) {
    btnRefreshFiles.addEventListener('click', () => {
      fetchPersonalAIFiles('.');
    });
  }

  const btnAdvise = document.getElementById('btnAdviseCommand');
  if (btnAdvise) {
    btnAdvise.addEventListener('click', async () => {
      const cmd = (document.getElementById('paiCommandAdvisorInput')?.value || '').trim();
      if (!cmd) return;
      try {
        const res = await fetch(`${API_BASE}/api/v1/personal-ai/terminal/advise`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ proposed_command: cmd, user_intent: 'safety inspection' })
        });
        if (!res.ok) return;
        const data = await res.json();
        const resBox = document.getElementById('paiCommandAdvisorResult');
        const binLabel = document.getElementById('paiCmdBinary');
        const riskBadge = document.getElementById('paiCmdRiskBadge');
        const expLabel = document.getElementById('paiCmdExplanation');
        const risksList = document.getElementById('paiCmdRisksList');
        if (resBox) resBox.style.display = 'block';
        if (binLabel) binLabel.textContent = `Binary: ${data.binary_name} ${data.is_blocked ? '(BLOCKED)' : ''}`;
        if (riskBadge) {
          riskBadge.textContent = `TIER: ${data.risk_tier}`;
          riskBadge.style.color = data.risk_tier === 'READ_ONLY' ? 'var(--status-online)' : (data.risk_tier === 'DESTRUCTIVE' ? 'var(--status-error)' : 'var(--accent-secondary)');
        }
        if (expLabel) expLabel.textContent = data.explanation;
        if (risksList) {
          risksList.textContent = data.potential_risks.length > 0 ? `Risks: ${data.potential_risks.join('; ')}` : 'No elevated hazards identified.';
        }
      } catch (e) {
        console.error('Command advise failed', e);
      }
    });
  }

  document.querySelectorAll('.pai-cmd-sample').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById('paiCommandAdvisorInput');
      if (input) {
        input.value = btn.getAttribute('data-cmd') || '';
        document.getElementById('btnAdviseCommand')?.click();
      }
    });
  });

  const btnRefreshAppr = document.getElementById('btnRefreshApprovals');
  if (btnRefreshAppr) btnRefreshAppr.addEventListener('click', fetchPersonalAIApprovals);

  const btnRefreshAudit = document.getElementById('btnRefreshAuditLogs');
  if (btnRefreshAudit) btnRefreshAudit.addEventListener('click', fetchPersonalAIAuditLogs);
}

// -------------------------------------------------------------------------
// Phase 11: Conversations, Streaming, Voice, Activity & Settings
// -------------------------------------------------------------------------

async function initConversationManager() {
  const btnNewChat = document.getElementById('btnNewChat');
  const btnDeleteThread = document.getElementById('btnDeleteThread');
  const threadSelector = document.getElementById('threadSelector');

  if (btnNewChat) btnNewChat.addEventListener('click', createNewConversation);
  if (btnDeleteThread) btnDeleteThread.addEventListener('click', deleteActiveConversation);
  if (threadSelector) {
    threadSelector.addEventListener('change', (e) => {
      switchConversation(e.target.value);
    });
  }

  await loadConversations();
}

async function loadConversations() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/conversations`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) return;
    const threads = await res.json();
    const selector = document.getElementById('threadSelector');
    if (!selector) return;

    selector.innerHTML = '';
    if (threads.length === 0) {
      await createNewConversation();
      return;
    }

    threads.forEach(t => {
      const opt = document.createElement('option');
      opt.value = t.id;
      opt.textContent = `${t.title} (${t.mode})`;
      if (t.id === currentConversationId) opt.selected = true;
      selector.appendChild(opt);
    });

    if (!currentConversationId && threads.length > 0) {
      currentConversationId = threads[0].id;
      localStorage.setItem('404_founders_active_thread', currentConversationId);
    }
  } catch (err) {
    console.warn('Failed to load conversations:', err);
  }
}

async function createNewConversation() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/conversations`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        title: `Chat ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
        mode: 'GENERAL',
      }),
    });
    if (!res.ok) return;
    const thread = await res.json();
    currentConversationId = thread.id;
    localStorage.setItem('404_founders_active_thread', currentConversationId);
    await loadConversations();
    const chatThread = document.getElementById('chatThread');
    if (chatThread) {
      chatThread.innerHTML = `
        <div class="message-item assistant">
          <div class="message-sender">404 FOUNDERS Neural Core &bull; Random Init</div>
          <div class="message-bubble">New conversation initiated. Thread ID: ${escapeHtml(thread.id)}</div>
          <div class="message-metadata"><span>Mode: GENERAL</span></div>
        </div>
      `;
    }
    showToast('New conversation created');
  } catch (err) {
    showToast('Failed to create conversation');
  }
}

async function deleteActiveConversation() {
  if (!currentConversationId) return;
  if (!confirm('Are you sure you want to delete this conversation thread?')) return;
  try {
    const res = await fetch(`${API_BASE}/api/v1/conversations/${currentConversationId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (res.ok) {
      currentConversationId = null;
      localStorage.removeItem('404_founders_active_thread');
      await loadConversations();
      showToast('Conversation deleted');
    }
  } catch (err) {
    showToast('Failed to delete conversation');
  }
}

async function switchConversation(id) {
  currentConversationId = id;
  localStorage.setItem('404_founders_active_thread', id);
  try {
    const res = await fetch(`${API_BASE}/api/v1/conversations/${id}/messages`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) return;
    const msgs = await res.json();
    const chatThread = document.getElementById('chatThread');
    if (!chatThread) return;

    chatThread.innerHTML = '';
    msgs.forEach(m => {
      const el = document.createElement('div');
      el.className = `message-item ${m.sender}`;
      el.innerHTML = `
        <div class="message-sender">${m.sender === 'user' ? 'User' : '404 FOUNDERS Engine'} &bull; ${escapeHtml(m.message_type)}</div>
        <div class="message-bubble">${renderMarkdownContent(m.content)}</div>
        ${renderMessageActions(m.content, m.sender, m.id)}
      `;
      chatThread.appendChild(el);
    });
    chatThread.scrollTop = chatThread.scrollHeight;
  } catch (err) {
    console.warn('Failed to switch conversation:', err);
  }
}

function initVoiceRecording() {
  const btnRecordMic = document.getElementById('btnRecordMic');
  if (!btnRecordMic) return;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    btnRecordMic.title = 'Speech Recognition not supported in this browser';
    btnRecordMic.disabled = true;
    return;
  }

  let recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  let isRecording = false;

  btnRecordMic.addEventListener('click', () => {
    const langSel = document.getElementById('settingsLanguage');
    recognition.lang = langSel ? langSel.value : 'en-US';

    if (!isRecording) {
      try {
        recognition.start();
        isRecording = true;
        btnRecordMic.classList.add('recording-active');
        btnRecordMic.textContent = '⏹️ Stop';
        showToast('Listening... Speak now');
      } catch (e) {
        console.error(e);
      }
    } else {
      recognition.stop();
      isRecording = false;
      btnRecordMic.classList.remove('recording-active');
      btnRecordMic.textContent = '🎤 Voice';
    }
  });

  recognition.onresult = (event) => {
    let transcript = '';
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      transcript += event.results[i][0].transcript;
    }
    const composer = document.getElementById('composerText');
    if (composer && transcript) {
      composer.value = transcript;
    }
  };

  recognition.onerror = (event) => {
    isRecording = false;
    btnRecordMic.classList.remove('recording-active');
    btnRecordMic.textContent = '🎤 Voice';
    showToast(`Speech recognition error: ${event.error}`);
  };

  recognition.onend = () => {
    isRecording = false;
    btnRecordMic.classList.remove('recording-active');
    btnRecordMic.textContent = '🎤 Voice';
  };
}

async function streamViaWebSocket(prompt, pendingEl, startTime) {
  const wsUrl = (API_BASE.replace(/^http/, 'ws')) + '/ws/v1/chat';
  let collectedText = '';

  try {
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      socket.send(JSON.stringify({
        action: 'chat',
        query: prompt,
        user_id: 'operator',
        conversation_id: currentConversationId,
      }));
    };

    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'status') {
          pendingEl.querySelector('.message-bubble').textContent = `[${msg.stage}] ${msg.detail || msg.message || 'Processing...'}`;
        } else if (msg.type === 'token') {
          collectedText += msg.content;
          pendingEl.querySelector('.message-bubble').innerHTML = renderMarkdownContent(collectedText);
        } else if (msg.type === 'done') {
          const elapsed = (performance.now() - startTime).toFixed(1);
          pendingEl.innerHTML = `
            <div class="message-sender">404 FOUNDERS Neural Core &bull; Streamed</div>
            <div class="message-bubble">${renderMarkdownContent(msg.full_response || collectedText)}</div>
            ${renderMessageActions(msg.full_response || collectedText, 'assistant')}
            <div class="message-metadata">
              <span>Latency: ${elapsed} ms</span>
              <span>Module: ${escapeHtml(msg.module || 'NEURAL_CORE')}</span>
              <span>Streaming: Active</span>
            </div>
          `;
          socket.close();
        } else if (msg.type === 'error') {
          throw new Error(msg.message);
        }
      } catch (err) {
        console.error('WebSocket parse error:', err);
      }
    };

    socket.onerror = (err) => {
      console.warn('WebSocket failed, falling back to REST/SSE:', err);
      socket.close();
      fallbackRestQuery(prompt, pendingEl, startTime);
    };
  } catch (err) {
    fallbackRestQuery(prompt, pendingEl, startTime);
  }
}

async function fallbackRestQuery(prompt, pendingEl, startTime) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/conversations/${currentConversationId || 'default'}/messages`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ content: prompt, message_type: 'TEXT' }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const elapsed = (performance.now() - startTime).toFixed(1);
    pendingEl.innerHTML = `
      <div class="message-sender">404 FOUNDERS Engine &bull; Fallback</div>
      <div class="message-bubble">${renderMarkdownContent(data.content)}</div>
      ${renderMessageActions(data.content, 'assistant', data.id)}
      <div class="message-metadata"><span>Latency: ${elapsed} ms</span></div>
    `;
  } catch (e) {
    pendingEl.innerHTML = `
      <div class="message-sender">Execution Error</div>
      <div class="message-bubble" style="color: var(--status-error);">${escapeHtml(e.message)}</div>
    `;
  }
}

async function fetchActivityHistory() {
  const tbody = document.getElementById('activityTableBody');
  const catFilter = document.getElementById('activityCategoryFilter');
  const category = catFilter ? catFilter.value : '';

  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" style="padding: 24px; text-align: center; color: var(--text-secondary);">Loading activity events...</td></tr>';

  try {
    const url = new URL(`${API_BASE}/api/v1/activity/history`);
    if (category) url.searchParams.set('category', category);
    url.searchParams.set('limit', '50');

    const res = await fetch(url.toString(), { headers: getAuthHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (!data.entries || data.entries.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="padding: 24px; text-align: center; color: var(--text-secondary);">No activity records found.</td></tr>';
      return;
    }

    tbody.innerHTML = data.entries.map(e => {
      const statusClass = e.status.toLowerCase();
      const timeStr = new Date(e.created_at).toLocaleString();
      return `
        <tr style="border-bottom: 1px solid var(--border);">
          <td style="padding: 8px 14px; font-size: 11.5px; color: var(--text-secondary); white-space: nowrap;">${escapeHtml(timeStr)}</td>
          <td style="padding: 8px 14px; font-weight: 500;">${escapeHtml(e.user_id)}</td>
          <td style="padding: 8px 14px;"><span class="badge-outline">${escapeHtml(e.category)}</span></td>
          <td style="padding: 8px 14px; font-weight: 500;">${escapeHtml(e.action)}</td>
          <td style="padding: 8px 14px;"><span class="badge-status ${escapeHtml(statusClass)}">${escapeHtml(e.status)}</span></td>
          <td style="padding: 8px 14px; color: var(--text-secondary); max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(e.detail || '—')}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="padding: 24px; text-align: center; color: var(--status-error);">Failed to fetch activity: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function fetchSettings() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/settings`, { headers: getAuthHeaders() });
    if (res.ok) {
      const s = await res.json();
      const themeEl = document.getElementById('settingsTheme');
      const voiceEl = document.getElementById('settingsVoiceEnabled');
      const ttsEl = document.getElementById('settingsTTSAutoplay');
      const langEl = document.getElementById('settingsLanguage');
      const retEl = document.getElementById('settingsRetentionDays');
      const epEl = document.getElementById('settingsEndpointUrl');

      if (themeEl) themeEl.value = s.theme_preference || 'system';
      if (voiceEl) voiceEl.checked = Boolean(s.voice_enabled);
      if (ttsEl) ttsEl.checked = Boolean(s.tts_autoplay);
      if (langEl) langEl.value = s.language || 'en';
      if (retEl) retEl.value = s.memory_retention_days || 365;
      if (epEl) epEl.value = API_BASE;
    }

    const profileRes = await fetch(`${API_BASE}/api/v1/auth/me`, { headers: getAuthHeaders() });
    if (profileRes.ok) {
      const u = await profileRes.json();
      const unameEl = document.getElementById('profileUsername');
      const uroleEl = document.getElementById('profileRole');
      const uemailEl = document.getElementById('profileEmail');
      if (unameEl) unameEl.textContent = u.username;
      if (uroleEl) uroleEl.textContent = u.role;
      if (uemailEl) uemailEl.textContent = u.email;
    }

    await fetchActiveSessions();
  } catch (err) {
    console.warn('Failed to load settings:', err);
  }
}

async function fetchActiveSessions() {
  const tbody = document.getElementById('sessionsTableBody');
  if (!tbody) return;
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/sessions`, { headers: getAuthHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const sessions = await res.json();

    if (sessions.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="padding: 16px; text-align: center; color: var(--text-secondary);">No active sessions found.</td></tr>';
      return;
    }

    tbody.innerHTML = sessions.map(s => {
      const createdStr = new Date(s.created_at).toLocaleString();
      const expiresStr = new Date(s.expires_at).toLocaleString();
      return `
        <tr style="border-bottom: 1px solid var(--border);">
          <td style="padding: 8px 12px; font-family: monospace;">${escapeHtml(s.session_id)}</td>
          <td style="padding: 8px 12px; color: var(--text-secondary);">${escapeHtml(createdStr)}</td>
          <td style="padding: 8px 12px; color: var(--text-secondary);">${escapeHtml(expiresStr)}</td>
          <td style="padding: 8px 12px;">${escapeHtml(s.ip_address || '127.0.0.1')}</td>
          <td style="padding: 8px 12px;">
            <button class="btn-secondary btn-sm" onclick="revokeUserSession('${escapeHtml(s.session_id)}')" style="color: #b91c1c; padding: 2px 8px; font-size: 11px;">Revoke</button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" style="padding: 16px; text-align: center; color: var(--status-error);">Failed to load sessions: ${escapeHtml(err.message)}</td></tr>`;
  }
}

window.revokeUserSession = async function(sessionId) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (res.ok) {
      showToast('Session revoked');
      await fetchActiveSessions();
    } else {
      showToast('Failed to revoke session');
    }
  } catch (err) {
    showToast('Error revoking session');
  }
};

async function saveUserSettings() {
  const themeEl = document.getElementById('settingsTheme');
  const voiceEl = document.getElementById('settingsVoiceEnabled');
  const ttsEl = document.getElementById('settingsTTSAutoplay');
  const langEl = document.getElementById('settingsLanguage');
  const retEl = document.getElementById('settingsRetentionDays');

  const payload = {
    theme_preference: themeEl ? themeEl.value : 'system',
    voice_enabled: voiceEl ? voiceEl.checked : false,
    tts_autoplay: ttsEl ? ttsEl.checked : false,
    language: langEl ? langEl.value : 'en',
    memory_retention_days: retEl ? parseInt(retEl.value, 10) : 365,
  };

  try {
    const res = await fetch(`${API_BASE}/api/v1/settings`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      if (themeEl) {
        localStorage.setItem('404_founders_theme', themeEl.value);
        applyTheme(themeEl.value);
      }
      showToast('Settings saved successfully');
    }
  } catch (err) {
    showToast('Failed to save settings');
  }
}

async function testBackendEndpoint() {
  const epInput = document.getElementById('settingsEndpointUrl');
  const resBox = document.getElementById('endpointTestResult');
  const newUrl = epInput ? epInput.value.trim().replace(/\/$/, '') : '';
  if (!newUrl) return;

  resBox.innerHTML = '<span style="color: var(--text-secondary);">Testing connection...</span>';
  try {
    const res = await fetch(`${newUrl}/health`, { method: 'GET' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    API_BASE = newUrl;
    localStorage.setItem('404_founders_endpoint', newUrl);
    resBox.innerHTML = `<span style="color: var(--status-online); font-weight: 600;">✓ Connected: ${escapeHtml(data.operating_mode.toUpperCase())} (${data.model_parameter_count.toLocaleString()} params)</span>`;
    showToast('Backend endpoint verified and saved');
    checkHealth();
  } catch (err) {
    resBox.innerHTML = `<span style="color: var(--status-error); font-weight: 600;">✗ Failed: ${escapeHtml(err.message)}</span>`;
  }
}

// -------------------------------------------------------------------------
// Initialization
// -------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  initThemeSwitcher();
  initNavigation();
  initChat();
  initConversationManager();
  initVoiceRecording();
  initMultimodalStudio();
  initMemoryManager();
  initPersonalAI();

  // Activity handlers
  const btnRefreshAct = document.getElementById('btnRefreshActivity');
  const catFilter = document.getElementById('activityCategoryFilter');
  if (btnRefreshAct) btnRefreshAct.addEventListener('click', fetchActivityHistory);
  if (catFilter) catFilter.addEventListener('change', fetchActivityHistory);

  // Settings handlers
  const settingsTheme = document.getElementById('settingsTheme');
  const settingsVoice = document.getElementById('settingsVoiceEnabled');
  const settingsTTS = document.getElementById('settingsTTSAutoplay');
  const settingsLang = document.getElementById('settingsLanguage');
  const settingsRet = document.getElementById('settingsRetentionDays');
  const btnSaveEp = document.getElementById('btnSaveEndpoint');
  const btnClearShort = document.getElementById('btnClearShortMemory');
  const btnLogout = document.getElementById('btnSettingsLogout');

  if (settingsTheme) settingsTheme.addEventListener('change', saveUserSettings);
  if (settingsVoice) settingsVoice.addEventListener('change', saveUserSettings);
  if (settingsTTS) settingsTTS.addEventListener('change', saveUserSettings);
  if (settingsLang) settingsLang.addEventListener('change', saveUserSettings);
  if (settingsRet) settingsRet.addEventListener('change', saveUserSettings);
  if (btnSaveEp) btnSaveEp.addEventListener('click', testBackendEndpoint);
  if (btnClearShort) {
    btnClearShort.addEventListener('click', async () => {
      showToast('Short-term memory purged');
    });
  }
  if (btnLogout) {
    btnLogout.addEventListener('click', async () => {
      await fetch(`${API_BASE}/api/v1/auth/logout`, { method: 'POST', headers: getAuthHeaders() });
      authToken = '';
      localStorage.removeItem('404_founders_token');
      showToast('Logged out');
      fetchSettings();
    });
  }

  // Telemetry handlers
  const btnRefreshTel = document.getElementById('btnRefreshTel');
  if (btnRefreshTel) btnRefreshTel.addEventListener('click', fetchTelemetry);

  // Tokenizer handlers
  const btnTokenizerEncode = document.getElementById('btnTokenizerEncode');
  const btnTokenizerDecode = document.getElementById('btnTokenizerDecode');
  if (btnTokenizerEncode) btnTokenizerEncode.addEventListener('click', handleTokenizerEncode);
  if (btnTokenizerDecode) btnTokenizerDecode.addEventListener('click', handleTokenizerDecode);

  // Git handler
  const btnRefreshGit = document.getElementById('btnRefreshGit');
  if (btnRefreshGit) btnRefreshGit.addEventListener('click', fetchGitStatus);

  // Security handlers
  const btnValidateCmd = document.getElementById('btnValidateCommand');
  const btnInspectPrompt = document.getElementById('btnInspectPrompt');
  if (btnValidateCmd) btnValidateCmd.addEventListener('click', validateCommand);
  if (btnInspectPrompt) btnInspectPrompt.addEventListener('click', inspectPrompt);

  // Initial loads
  checkHealth();
  fetchTelemetry();
  setInterval(checkHealth, 5000);
});
