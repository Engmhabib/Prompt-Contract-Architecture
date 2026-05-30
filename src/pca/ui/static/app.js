// PCA Playground — vanilla JS, no build step.

const $  = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => Array.from(el.querySelectorAll(sel));

const state = {
  token: null,
  user: 'alice',
  roles: ['sales_admin', 'analyst', 'admin', 'auditor', 'developer'],
  contracts: [],
  activeTab: 'invoke',
};

const SAMPLES = [
  { label: 'Create customer', text: 'Create a customer named John Doe, john@example.com' },
  { label: 'Customer v1 (pin)', text: 'Add customer Sarah Lee, sarah@acme.com', hint: 'customer.create@1.0.0' },
  { label: 'Bad email', text: 'Create a customer named Jane, email = not-an-email' },
  { label: 'Report', text: 'Generate a monthly report with 500 rows' },
  { label: 'Unknown', text: 'What is the meaning of life?' },
];

// ---------------- API ----------------
async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
  const res = await fetch(path, { ...opts, headers });
  const ct = res.headers.get('content-type') || '';
  const body = ct.includes('application/json') ? await res.json().catch(() => null) : await res.text();
  return { ok: res.ok, status: res.status, body };
}

// ---------------- Identity ----------------
function renderRoles() {
  const wrap = $('#role-chips');
  wrap.innerHTML = '';
  state.roles.forEach((r, i) => {
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.innerHTML = `${r}<button data-i="${i}" title="remove">×</button>`;
    chip.querySelector('button').onclick = () => { state.roles.splice(i, 1); renderRoles(); };
    wrap.appendChild(chip);
  });
}

async function mintToken() {
  state.user = $('#user-sub').value.trim() || 'demo';
  const r = await api('/v1/dev/token', { method: 'POST',
    body: JSON.stringify({ sub: state.user, roles: state.roles }) });
  if (!r.ok) { toast(`Token mint failed: ${r.status}`, 'err'); return; }
  state.token = r.body.token;
  $('#token-preview').textContent = state.token.slice(0, 18) + '…';
  toast(`Token for ${state.user} (${state.roles.join(',') || 'no roles'})`, 'ok');
  // Re-load the active tab so role-gated views (audit, etc.) refresh
  // immediately with the new token.
  if (state.activeTab === 'audit') loadAudit();
}

// ---------------- Health ----------------
async function pollHealth() {
  const r = await api('/healthz');
  const dot = $('#health-dot');
  dot.textContent = r.ok ? '● up' : '● down';
  dot.className = r.ok ? 'text-emerald-400' : 'text-rose-400';
}

// ---------------- Tabs ----------------
function showTab(name) {
  state.activeTab = name;
  $$('.panel').forEach(p => p.classList.toggle('hidden', p.dataset.panel !== name));
  $$('.nav-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  if (name === 'audit') loadAudit();
  if (name === 'docs') loadDocsList();
  if (name === 'tests') loadTestContracts();
  if (name === 'contracts') loadContracts();
}

// ---------------- Invoke ----------------
const STEPS = [
  ['classify',  'Classify intent (LLM)'],
  ['resolve',   'Resolve contract version'],
  ['authz',     'Check permissions'],
  ['extract',   'Extract inputs (LLM)'],
  ['validate',  'Validate schema + rules'],
  ['tool',      'Dispatch tool'],
  ['shape',     'Shape output'],
  ['audit',     'Write audit log'],
];

function renderPipeline(highlight = null) {
  const ol = $('#pipeline');
  ol.innerHTML = '';
  STEPS.forEach(([id, label], i) => {
    const li = document.createElement('li');
    li.className = 'step';
    li.dataset.step = id;
    li.innerHTML = `<span class="step-dot"></span><span class="label">${i + 1}. ${label}</span>`;
    ol.appendChild(li);
  });
  if (highlight) highlight(ol);
}

function markPipeline(result, error) {
  const ol = $('#pipeline');
  const steps = $$('.step', ol);
  // success: mark all done
  if (!error) { steps.forEach(s => s.classList.add('done')); return; }
  // failure: mark steps before failing one done, fail one err, rest skip.
  // Use heuristic from error type / status.
  const idxByName = Object.fromEntries(STEPS.map(([n], i) => [n, i]));
  let failAt = STEPS.length - 1;
  const errStr = (error.detail?.message || error.detail || '').toString().toLowerCase();
  if (error.status === 403 && errStr.includes('forbid')) failAt = idxByName.authz;
  else if (error.status === 403) failAt = idxByName.authz;
  else if (error.status === 422) failAt = idxByName.validate;
  else if (error.status === 400) failAt = idxByName.classify;
  steps.forEach((s, i) => {
    if (i < failAt) s.classList.add('done');
    else if (i === failAt) s.classList.add('err');
    else s.classList.add('skip');
  });
}

async function invoke() {
  if (!state.token) { toast('Mint a token first', 'warn'); return; }
  const prompt = $('#prompt-input').value.trim();
  const hint = $('#hint-input').value.trim() || null;
  if (!prompt) return;
  renderPipeline();
  $('#invoke-status').textContent = 'running…';
  $('#invoke-status').className = 'badge badge-info';
  $('#invoke-result').textContent = '…';

  const r = await api('/v1/invoke', { method: 'POST', body: JSON.stringify({ prompt, hint }) });
  if (r.ok) {
    markPipeline(r.body, null);
    $('#invoke-status').textContent = `${r.body.contract_id}@${r.body.contract_version}`;
    $('#invoke-status').className = 'badge badge-ok';
  } else {
    markPipeline(null, { status: r.status, detail: r.body?.detail });
    $('#invoke-status').textContent = `${r.status}`;
    $('#invoke-status').className = 'badge badge-err';
  }
  $('#invoke-result').textContent = JSON.stringify(r.body, null, 2);
}

function renderSamples() {
  const wrap = $('#samples');
  wrap.innerHTML = '';
  SAMPLES.forEach(s => {
    const b = document.createElement('button');
    b.className = 'chip hover:bg-brand-100 cursor-pointer';
    b.textContent = s.label;
    b.onclick = () => {
      $('#prompt-input').value = s.text;
      $('#hint-input').value = s.hint || '';
    };
    wrap.appendChild(b);
  });
}

// ---------------- Contracts ----------------
async function loadContracts() {
  const r = await api('/v1/contracts');
  state.contracts = r.body || [];
  const list = $('#contract-list');
  list.innerHTML = '';
  // group by id
  const groups = {};
  state.contracts.forEach(c => (groups[c.contract_id] ||= []).push(c));
  Object.entries(groups).forEach(([id, versions]) => {
    versions.sort((a, b) => a.version.localeCompare(b.version));
    versions.forEach(c => {
      const li = document.createElement('li');
      const b = document.createElement('button');
      b.className = 'contract-item';
      b.innerHTML = `<span class="font-mono">${id}</span><span class="badge">v${c.version}</span>`;
      b.onclick = () => {
        $$('.contract-item', list).forEach(x => x.classList.remove('active'));
        b.classList.add('active');
        $('#contract-detail').textContent = JSON.stringify(c, null, 2);
      };
      li.appendChild(b);
      list.appendChild(li);
    });
  });
}

// ---------------- Audit ----------------
async function loadAudit() {
  if (!state.token) { toast('Mint a token first', 'warn'); return; }
  const r = await api('/v1/audit');
  const body = $('#audit-body');
  body.innerHTML = '';
  if (r.status === 401 || r.status === 403) {
    const need = ['admin', 'auditor'];
    const have = state.roles.length ? state.roles.join(', ') : '(none)';
    body.innerHTML = `<tr><td colspan="6" class="text-amber-700 bg-amber-50 p-3">`
      + `Your current token (<b>${escapeHtml(state.user)}</b>) lacks the required role. `
      + `Audit log requires one of: <b>${need.join(' or ')}</b>. `
      + `Current roles: <code>${escapeHtml(have)}</code>. `
      + `Add the missing role above and click <b>Mint Token</b> again.`
      + `</td></tr>`;
    return;
  }
  if (!r.ok) { body.innerHTML = `<tr><td colspan="6" class="text-rose-600">${r.status}: ${escapeHtml(JSON.stringify(r.body))}</td></tr>`; return; }
  r.body.forEach(row => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-50';
    const cls = row.status === 'ok' ? 'badge-ok' : 'badge-err';
    tr.innerHTML = `
      <td class="text-xs text-ink-500 font-mono">${(row.timestamp||'').replace('T',' ').slice(0,19)}</td>
      <td>${row.user}</td>
      <td class="font-mono text-xs">${row.contract_id || '—'}${row.contract_version ? '@' + row.contract_version : ''}</td>
      <td><span class="badge ${cls}">${row.status}</span></td>
      <td class="max-w-md truncate" title="${escapeHtml(row.intent_prompt||'')}">${escapeHtml(row.intent_prompt||'')}</td>
      <td class="text-xs text-rose-600">${escapeHtml(row.error||'')}</td>`;
    body.appendChild(tr);
  });
}

// ---------------- Tests ----------------
async function loadTestContracts() {
  if (state.contracts.length === 0) await loadContracts();
  const sel = $('#test-contract');
  sel.innerHTML = '';
  const ids = [...new Set(state.contracts.map(c => c.contract_id))];
  ids.forEach(id => {
    const o = document.createElement('option');
    o.value = id; o.textContent = id; sel.appendChild(o);
  });
}

async function runTests() {
  if (!state.token) { toast('Mint a token first', 'warn'); return; }
  const id = $('#test-contract').value;
  const r = await api(`/v1/tests/run/${id}`, { method: 'POST' });
  const body = $('#test-body');
  body.innerHTML = '';
  if (!r.ok) { $('#test-summary').textContent = `${r.status}: ${JSON.stringify(r.body)}`; return; }
  const rep = r.body;
  $('#test-summary').innerHTML = `<span class="badge ${rep.failed===0?'badge-ok':'badge-err'}">${rep.passed}/${rep.total} passed</span>`;
  rep.outcomes.forEach(o => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-50';
    tr.innerHTML = `
      <td class="font-mono text-xs">${o.name}</td>
      <td><span class="badge">${o.expected}</span></td>
      <td><span class="badge ${o.expected===o.actual?'badge-ok':'badge-err'}">${o.actual}</span></td>
      <td>${o.passed ? '✅' : '❌'}</td>
      <td class="text-xs text-ink-500 max-w-md truncate">${escapeHtml(o.detail||'')}</td>`;
    body.appendChild(tr);
  });
}

// ---------------- Docs ----------------
async function loadDocsList() {
  if (state.contracts.length === 0) await loadContracts();
  const list = $('#docs-list');
  list.innerHTML = '';
  const ids = [...new Set(state.contracts.map(c => c.contract_id))];
  ids.forEach(id => {
    const li = document.createElement('li');
    const b = document.createElement('button');
    b.className = 'contract-item';
    b.innerHTML = `<span class="font-mono">${id}</span><span class="badge">md</span>`;
    b.onclick = async () => {
      $$('.contract-item', list).forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      const r = await api(`/v1/docs/${id}`);
      $('#docs-view').innerHTML = mdToHtml(r.body || '');
    };
    li.appendChild(b);
    list.appendChild(li);
  });
}

// Minimal markdown renderer (headings, lists, tables, code, bold, inline code).
function mdToHtml(md) {
  if (typeof md !== 'string') md = String(md);
  const esc = s => s.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  const lines = md.split('\n');
  let html = '', inTable = false, inList = false;
  const flushList = () => { if (inList) { html += '</ul>'; inList = false; } };
  for (let i = 0; i < lines.length; i++) {
    let L = lines[i];
    if (/^\|.+\|/.test(L) && /^\|[\s:-]+\|/.test(lines[i+1] || '')) {
      flushList();
      const headers = L.split('|').slice(1, -1).map(s => s.trim());
      html += '<table class="text-sm border-collapse"><thead><tr>' +
        headers.map(h => `<th class="border px-2 py-1 bg-slate-100">${inline(h)}</th>`).join('') +
        '</tr></thead><tbody>';
      i++; // skip separator
      while (i + 1 < lines.length && /^\|.+\|/.test(lines[i+1])) {
        i++;
        const cells = lines[i].split('|').slice(1, -1).map(s => s.trim());
        html += '<tr>' + cells.map(c => `<td class="border px-2 py-1">${inline(c)}</td>`).join('') + '</tr>';
      }
      html += '</tbody></table>';
      continue;
    }
    if (/^# /.test(L))      { flushList(); html += `<h1 class="text-2xl font-bold mt-4 mb-2">${inline(L.slice(2))}</h1>`; }
    else if (/^## /.test(L)){ flushList(); html += `<h2 class="text-lg font-semibold mt-4 mb-2">${inline(L.slice(3))}</h2>`; }
    else if (/^### /.test(L)){flushList();html += `<h3 class="text-base font-semibold mt-3 mb-1">${inline(L.slice(4))}</h3>`; }
    else if (/^- /.test(L))  { if (!inList) { html += '<ul class="list-disc pl-6">'; inList = true; } html += `<li>${inline(L.slice(2))}</li>`; }
    else if (L.trim() === '') { flushList(); html += ''; }
    else                      { flushList(); html += `<p>${inline(L)}</p>`; }
  }
  flushList();
  function inline(s) {
    return esc(s)
      .replace(/`([^`]+)`/g, '<code class="px-1 bg-slate-100 rounded text-xs">$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/_([^_]+)_/g, '<em>$1</em>');
  }
  return html;
}

// ---------------- Utils ----------------
function escapeHtml(s) {
  return (s || '').toString().replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}
function toast(msg, kind = 'ok') {
  const t = $('#toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  t.style.background = kind === 'err' ? '#9f1239' : kind === 'warn' ? '#92400e' : '#0b1020';
  setTimeout(() => t.classList.add('hidden'), 2200);
}

// ---------------- Boot ----------------
document.addEventListener('DOMContentLoaded', async () => {
  renderRoles();
  renderSamples();
  renderPipeline();
  $$('.nav-btn').forEach(b => b.onclick = () => showTab(b.dataset.tab));
  $('#mint-btn').onclick = mintToken;
  $('#invoke-btn').onclick = invoke;
  $('#reload-contracts').onclick = loadContracts;
  $('#reload-audit').onclick = loadAudit;
  $('#run-tests').onclick = runTests;
  $('#role-input').addEventListener('keydown', e => {
    if (e.key === 'Enter' && e.target.value.trim()) {
      state.roles.push(e.target.value.trim()); e.target.value = ''; renderRoles();
    }
  });
  showTab('invoke');
  pollHealth();
  setInterval(pollHealth, 5000);
  await mintToken();
  await loadContracts();
});
