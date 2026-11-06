/**
 * 404 FOUNDERS — Warm Neutral Frontend Controller
 * Style: Premium warm minimalism, sophisticated productivity software.
 * Communicates with FastAPI backend on http://127.0.0.1:8000
 */

const API_BASE = 'http://127.0.0.1:8000';

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
  api: {
    title: 'API Specifications & Interactive Docs',
    subtitle: 'FastAPI OpenAPI 3.1.0 interactive documentation and verification endpoints'
  }
};

// State
let lastEncodedIds = [];
let isBackendOnline = false;

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
  const slider = document.getElementById('composerTokensSlider');
  const sliderVal = document.getElementById('composerTokensVal');

  slider.addEventListener('input', (e) => {
    sliderVal.textContent = e.target.value;
  });

  // Keyboard shortcut: Ctrl+Enter or Cmd+Enter to send
  composerText.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      sendChatMessage();
    }
  });

  btnSend.addEventListener('click', sendChatMessage);
}

async function sendChatMessage() {
  const composerText = document.getElementById('composerText');
  const prompt = composerText.value.trim();
  if (!prompt) return;

  const mode = document.getElementById('composerMode').value;
  const maxTokens = parseInt(document.getElementById('composerTokensSlider').value, 10);
  const chatThread = document.getElementById('chatThread');
  const btnSend = document.getElementById('btnChatSend');

  // Append user message
  const userMsgEl = document.createElement('div');
  userMsgEl.className = 'message-item user';
  userMsgEl.innerHTML = `
    <div class="message-sender">User &bull; ${escapeHtml(mode.toUpperCase())}</div>
    <div class="message-bubble">${escapeHtml(prompt)}</div>
  `;
  chatThread.appendChild(userMsgEl);

  // Clear composer & disable send button during inference
  composerText.value = '';
  btnSend.disabled = true;
  btnSend.textContent = 'Forward Pass...';

  // Append temporary loading indicator
  const pendingEl = document.createElement('div');
  pendingEl.className = 'message-item assistant';
  pendingEl.innerHTML = `
    <div class="message-sender">404 FOUNDERS Neural Core</div>
    <div class="message-bubble" style="color: var(--text-muted); font-style: italic;">
      Evaluating token embeddings, multi-head attention, and MoE routing...
    </div>
  `;
  chatThread.appendChild(pendingEl);
  chatThread.scrollTop = chatThread.scrollHeight;

  const startTime = performance.now();

  try {
    const res = await fetch(`${API_BASE}/api/v1/neural/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: prompt,
        max_new_tokens: maxTokens,
        mode: mode
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    const elapsed = (performance.now() - startTime).toFixed(1);

    // Build token pills
    let tokenPillsHtml = '';
    data.generated_tokens.forEach((tok, i) => {
      const id = data.generated_ids[i];
      tokenPillsHtml += `<span class="subword-pill">${escapeHtml(tok)}<span class="subword-id">#${id}</span></span>`;
    });

    // Replace pending element with response
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
  } catch (err) {
    pendingEl.innerHTML = `
      <div class="message-sender">Neural Core Error</div>
      <div class="message-bubble" style="border-left-color: var(--status-error); color: var(--status-error);">
        Failed to execute forward pass: ${escapeHtml(err.message)}
      </div>
    `;
  } finally {
    btnSend.disabled = false;
    btnSend.textContent = 'Generate Next Tokens';
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
// Initialization
// -------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initChat();

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
