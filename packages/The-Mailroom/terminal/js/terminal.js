/* THE MAILROOM terminal site — shell core.
   A TTY emulation: persistent prompt at the bottom, output above, ghost-text
   Tab completion, command history, opt-in keypress sound, CRT overlay.
   Reads exported snapshots (../data/*.json) + the live Hub datasets-server
   for corpus rows. Never fabricates data. */
'use strict';

const D = (typeof window !== 'undefined' && window.MAILROOM_DATA) ? window.MAILROOM_DATA : null;

const DATA_DIR = '../data/';
const HF_ROWS = 'https://datasets-server.huggingface.co/rows';

/* =================== ARTWORK =================== */
const BANNER = (D ? D.banner : '').replace(/^\n/, '').split('\n');
const ENVELOPE = [
  '   ______________',
  '  /             /|',
  ' /_____________/ |',
  '|  <span class="flap">\\\\___________/</span>  |',
  '|______________|  |',
  '|  /     \\      | /',
  '|_/_______\\_____|/',
];

const STAGE_ORDER = [
  'inbox', 'intake', 'classify', 'retry_classify', 'review_classify',
  'extract', 'retry_extract', 'judge_verify', 'arbiter',
  'boss', 'review', 'report', 'catalog', 'archive', 'archived', 'failed',
];
const STAGE_NAME = {
  inbox: 'INBOX', intake: 'Sorter', classify: 'Sorter', retry_classify: 'Sorter',
  review_classify: 'Sorter', extract: 'Specialist', retry_extract: 'Specialist',
  judge_verify: 'Judge', arbiter: 'Arbiter', boss: 'Boss', review: 'Review',
  report: 'Reporter', catalog: 'Archive', archive: 'Archive', archived: 'Archive',
  failed: 'Failed',
};
const DOC_CLASS_ALIASES = {
  contract: 'contract', contracts: 'contract',
  corporate: 'corporate_record', corporate_record: 'corporate_record',
  insurance: 'insurance_claim', insurance_claim: 'insurance_claim',
  correspondence: 'correspondence', email: 'correspondence',
  merger: 'merger_agreement', merger_agreement: 'merger_agreement',
  unknown: 'unknown',
};

/* =================== STATE =================== */
const state = {
  cwd: '~',
  history: [],
  historyIndex: -1,
  sound: false,
  crt: true,
  skyline: true,
  theme: 'amber',
  bootTime: Date.now(),
};
const cache = {};       // url -> promise of parsed JSON
const corpusCache = { rows: null, meta: null };   // bundled catalog
const runsCache = [];   // floor runs from traces.json

try {
  const prefs = JSON.parse(localStorage.getItem('mailroomTerminalPrefs') || '{}');
  if (['amber', 'green', 'cyan'].includes(prefs.theme)) state.theme = prefs.theme;
  if (typeof prefs.crt === 'boolean') state.crt = prefs.crt;
  if (typeof prefs.sound === 'boolean') state.sound = prefs.sound;
  if (typeof prefs.skyline === 'boolean') state.skyline = prefs.skyline;
  const stored = JSON.parse(localStorage.getItem('mailroomTerminalHistory') || '[]');
  if (Array.isArray(stored)) state.history = stored.slice(-100);
} catch (e) {}

function savePrefs() {
  try {
    localStorage.setItem('mailroomTerminalPrefs', JSON.stringify({
      theme: state.theme, crt: state.crt, sound: state.sound, skyline: state.skyline,
    }));
  } catch (e) {}
}

/* =================== THEMES =================== */
const THEMES = {
  amber: { phosphor: '#ffb86c', bright: '#ffd09b' },
  green: { phosphor: '#a3e635', bright: '#d4f881' },
  cyan:  { phosphor: '#67e8f9', bright: '#a5f3fc' },
};
function applyTheme(name, quiet) {
  const t = THEMES[name];
  if (!t) return;
  document.documentElement.style.setProperty('--amber', t.phosphor);
  document.documentElement.style.setProperty('--amber-bright', t.bright);
  state.theme = name;
  document.getElementById('statusTheme').textContent = name;
  if (!quiet) {
    document.body.classList.remove('theme-flash');
    void document.body.offsetWidth;
    document.body.classList.add('theme-flash');
  }
  savePrefs();
}

/* =================== DOM =================== */
const $ = (id) => document.getElementById(id);
const output = $('output');
const cmdInput = $('cmdInput');
const typedText = $('typedText');
const ghostText = $('ghostText');
const promptText = $('promptText');
const statusPath = $('statusPath');

/* =================== AUDIO (opt-in, subtle) =================== */
let audioCtx;
function ensureAudio() {
  if (!audioCtx) {
    try { audioCtx = new (window.AudioContext || window.webkitAudioContext)(); }
    catch (e) { audioCtx = null; }
  }
  if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
}
function playClick() {
  if (!state.sound) return;
  ensureAudio();
  if (!audioCtx) return;
  const now = audioCtx.currentTime;
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.type = 'square';
  osc.frequency.setValueAtTime(1700 + Math.random() * 500, now);
  gain.gain.setValueAtTime(0.018, now);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.025);
  osc.connect(gain); gain.connect(audioCtx.destination);
  osc.start(now); osc.stop(now + 0.03);
}
function playBell() {
  if (!state.sound) return;
  ensureAudio();
  if (!audioCtx) return;
  const now = audioCtx.currentTime;
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.type = 'sine';
  osc.frequency.setValueAtTime(660, now);
  osc.frequency.exponentialRampToValueAtTime(880, now + 0.05);
  gain.gain.setValueAtTime(0.04, now);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.4);
  osc.connect(gain); gain.connect(audioCtx.destination);
  osc.start(now); osc.stop(now + 0.4);
}

/* =================== UTIL =================== */
function escapeHtml(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
function reduced() { return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches; }
function scrollBottom() { output.scrollTop = output.scrollHeight; }
function print(html, cls = '') {
  const div = document.createElement('div');
  div.className = 'line' + (cls ? ' ' + cls : '');
  div.innerHTML = html || '&nbsp;';
  output.appendChild(div);
  scrollBottom();
  return div;
}
function printRaw(html) { return print(html); }
function printBlank() { print('&nbsp;'); }
function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
function money(v) {
  if (v === null || v === undefined || v === '') return '-';
  const n = Number(v);
  return Number.isFinite(n) ? '$' + n.toFixed(4) : String(v);
}
function fmt(v, spec) {
  if (v === null || v === undefined || v === '') return '-';
  const n = Number(v);
  if (Number.isFinite(n)) return spec ? spec(n) : n.toFixed(2);
  return String(v);
}

function sweepFx() {
  if (reduced()) return;
  const term = document.querySelector('.terminal');
  const s = document.createElement('div');
  s.className = 'crt-sweep';
  term.appendChild(s);
  setTimeout(() => s.remove(), 520);
}

/* =================== DATA FETCH =================== */
function getJSON(url) {
  if (!(url in cache)) {
    cache[url] = fetch(url).then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status + ' ' + url);
      return r.json();
    });
  }
  return cache[url];
}
async function loadRuns() {
  if (runsCache.length) return runsCache;
  try {
    const data = await getJSON(DATA_DIR + 'traces.json');
    const runs = (data && data.runs) || [];
    runs.forEach(r => runsCache.push(r));
  } catch (e) { /* snapshot missing — floor stays closed */ }
  return runsCache;
}
async function loadCorpusCatalog() {
  if (corpusCache.rows) return corpusCache;
  try {
    const data = await getJSON(DATA_DIR + 'corpus.json');
    corpusCache.rows = data.rows || [];
    corpusCache.meta = data.meta || {};
    $('statusCorpus').textContent = corpusCache.rows.length ? corpusCache.rows.length + ' rows' : 'n/a';
  } catch (e) {
    corpusCache.rows = [];
    $('statusCorpus').textContent = 'offline';
  }
  return corpusCache;
}
function hfRowUrl(config, split, index) {
  const meta = corpusCache.meta || {};
  const q = new URLSearchParams({
    dataset: meta.dataset || 'Lucius-Morningstar/mailroom-dataset',
    config, split, offset: String(index), length: '1',
  });
  if (meta.revision) q.set('revision', meta.revision);
  return HF_ROWS + '?' + q.toString();
}
async function hfRow(config, split, index) {
  const data = await getJSON(hfRowUrl(config, split, index));
  const rows = (data && data.rows) || [];
  return rows.length ? rows[0].row : null;
}
function findCatalogRow(filename) {
  return (corpusCache.rows || []).find(r => r.filename === filename) || null;
}

/* =================== MARKDOWN =================== */
function inlineMd(text) {
  return text
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
}
function renderMarkdown(md) {
  const lines = escapeHtml(md).split('\n');
  const out = [];
  let inUl = false, inOl = false, inCode = false, inTable = false;
  let paraBuf = [];
  let tableBuf = [];
  const flushPara = () => { if (paraBuf.length) { out.push('<p>' + paraBuf.join(' ') + '</p>'); paraBuf = []; } };
  const closeLists = () => {
    if (inUl) { out.push('</ul>'); inUl = false; }
    if (inOl) { out.push('</ol>'); inOl = false; }
  };
  const closeTable = () => {
    if (inTable) {
      const cells = tableBuf.map(row => '<tr>' + row.map(c => '<td>' + c + '</td>').join('') + '</tr>').join('');
      out.push('<table class="mr"><tbody>' + cells + '</tbody></table>');
      inTable = false; tableBuf = [];
    }
  };

  for (const line of lines) {
    if (line.match(/^```/)) {
      if (inCode) { out.push('</code></pre>'); inCode = false; }
      else { flushPara(); closeLists(); closeTable(); out.push('<pre><code>'); inCode = true; }
      continue;
    }
    if (inCode) { out.push(line + '\n'); continue; }
    if (line.trim() === '') { flushPara(); closeLists(); closeTable(); continue; }
    let m;
    if (m = line.match(/^\|(.+)\|$/)) {
      flushPara(); closeLists();
      if (!inTable) inTable = true;
      const cells = m[1].split('|').map(c => inlineMd(c.trim()));
      if (cells.every(c => /^:?-{2,}:?$/.test(c.replace(/<[^>]+>/g, '')))) continue; // separator row
      tableBuf.push(cells);
    }
    else if (m = line.match(/^### (.+)$/)) { flushPara(); closeLists(); closeTable(); out.push('<h3>' + inlineMd(m[1]) + '</h3>'); }
    else if (m = line.match(/^## (.+)$/)) { flushPara(); closeLists(); closeTable(); out.push('<h2>' + inlineMd(m[1]) + '</h2>'); }
    else if (m = line.match(/^# (.+)$/)) { flushPara(); closeLists(); closeTable(); out.push('<h1>' + inlineMd(m[1]) + '</h1>'); }
    else if (m = line.match(/^&gt; ?(.+)$/)) { flushPara(); closeLists(); closeTable(); out.push('<blockquote>' + inlineMd(m[1]) + '</blockquote>'); }
    else if (m = line.match(/^(\d+)\. (.+)$/)) {
      flushPara(); closeTable();
      if (inUl) { out.push('</ul>'); inUl = false; }
      if (!inOl) { out.push('<ol>'); inOl = true; }
      out.push('<li>' + inlineMd(m[2]) + '</li>');
    } else if (m = line.match(/^[-*] (.+)$/)) {
      flushPara(); closeTable();
      if (inOl) { out.push('</ol>'); inOl = false; }
      if (!inUl) { out.push('<ul>'); inUl = true; }
      out.push('<li>' + inlineMd(m[1]) + '</li>');
    } else if (line.match(/^---+$/)) {
      flushPara(); closeLists(); closeTable();
      out.push('<div class="divider">' + '─'.repeat(72) + '</div>');
    } else {
      paraBuf.push(inlineMd(line));
    }
  }
  flushPara(); closeLists(); closeTable();
  if (inCode) {
    if (out.length && out[out.length - 1].endsWith('\n')) out[out.length - 1] = out[out.length - 1].replace(/\n$/, '');
    out.push('</code></pre>');
  }
  return out.join('');
}

/* =================== FILESYSTEM =================== */
function normalizePath(base, rel) {
  const parts = base === '~' ? [] : base.slice(2).split('/');
  for (const seg of rel.split('/')) {
    if (!seg || seg === '.') continue;
    if (seg === '..') parts.pop();
    else if (seg === '~') parts.length = 0;
    else parts.push(seg);
  }
  return parts.length ? '~/' + parts.join('/') : '~';
}
function resolvePath(input) {
  if (!input || input === '~') return '~';
  if (input === '.') return state.cwd;
  let base = state.cwd;
  let rest = input;
  if (input.startsWith('~/')) { base = '~'; rest = input.slice(2); }
  else if (input.startsWith('/')) { base = '~'; rest = input.slice(1); }
  return normalizePath(base, rest);
}
async function topics() {
  await loadCorpusCatalog();
  const counts = {};
  for (const r of corpusCache.rows) {
    const k = r.doc_class || 'unknown';
    counts[k] = (counts[k] || 0) + 1;
  }
  return Object.keys(counts).sort();
}
function isDir(path) {
  if (path === '~' || path === '~/runs' || path === '~/corpus' || path === '~/repos' || path === '~/topics') return true;
  if (path.startsWith('~/runs/')) return false;
  if (path.startsWith('~/topics/')) return true;   // topic tags act as dirs
  return false;
}
async function listDir(path) {
  if (path === '~') return [
    { name: 'runs', type: 'dir' },
    { name: 'corpus', type: 'dir' },
    { name: 'repos', type: 'dir' },
    { name: 'topics', type: 'dir' },
    { name: 'README.md', type: 'file', cls: 'md' },
    { name: '.plan', type: 'file', cls: 'hidden' },
    { name: '.about', type: 'file', cls: 'hidden' },
    { name: '.contact', type: 'file', cls: 'hidden' },
  ];
  if (path === '~/runs') {
    const runs = await loadRuns();
    return runs.map(r => ({ name: r.filename || r.trace_id || 'run', type: 'file', cls: 'md' }));
  }
  if (path === '~/corpus') {
    await loadCorpusCatalog();
    return corpusCache.rows.slice(0, 200).map(r => ({ name: r.filename, type: 'file', cls: 'md' }));
  }
  if (path === '~/repos') return (D.repos || []).map(r => ({ name: r.name, type: 'file', cls: 'md' }));
  if (path === '~/topics') return (await topics()).map(t => ({ name: t, type: 'dir' }));
  if (path.startsWith('~/topics/')) {
    const tag = path.split('/').pop();
    await loadCorpusCatalog();
    return corpusCache.rows
      .filter(r => (r.doc_class || 'unknown') === tag)
      .map(r => ({ name: r.filename, type: 'file', cls: 'md' }));
  }
  return null;
}
function resolveFile(input) {
  const path = resolvePath(input);
  const last = path.split('/').pop();
  if (last === 'README.md') return { kind: 'readme' };
  if (last === '.about') return { kind: 'about' };
  if (last === '.plan') return { kind: 'plan' };
  if (last === '.contact') return { kind: 'contact' };
  if (path.startsWith('~/runs/')) return { kind: 'run', id: last };
  if (state.cwd === '~/runs') return { kind: 'run', id: last };
  if (path.startsWith('~/repos/') || state.cwd === '~/repos') return { kind: 'repo', name: last };
  if (path.startsWith('~/corpus/') || state.cwd === '~/corpus' || state.cwd.startsWith('~/topics/')) {
    return { kind: 'corpus', filename: last };
  }
  return null;
}

/* =================== COMPLETION =================== */
function getCurrentWord() {
  const val = cmdInput.value;
  const words = val.split(' ');
  return { word: words[words.length - 1], isFirst: words.length === 1, cmd: words[0], words };
}
async function fileCandidates(cmd) {
  if (state.cwd === '~/runs') return (await loadRuns()).map(r => r.filename || r.trace_id || '');
  if (state.cwd === '~/repos') return (D.repos || []).map(r => r.name);
  if (state.cwd === '~/topics') return await topics();
  if (state.cwd.startsWith('~/topics/')) {
    const tag = state.cwd.split('/').pop();
    await loadCorpusCatalog();
    return corpusCache.rows.filter(r => (r.doc_class || 'unknown') === tag).map(r => r.filename);
  }
  if (state.cwd === '~/corpus') {
    await loadCorpusCatalog();
    return corpusCache.rows.slice(0, 200).map(r => r.filename);
  }
  const fromRoot = ['runs/', 'corpus/', 'repos/', 'topics/']
    .concat((await loadRuns()).slice(0, 40).map(r => 'runs/' + (r.filename || r.trace_id)))
    .concat((await topics()).map(t => 'topics/' + t + '/'))
    .concat(['README.md', '.about', '.plan', '.contact']);
  return fromRoot;
}
async function getCandidates(word, isFirst, cmd) {
  let candidates = [];
  if (isFirst) candidates = Object.keys(COMMANDS).sort();
  else if (cmd === 'cat' || cmd === 'ls') candidates = await fileCandidates(cmd);
  else if (cmd === 'cd') candidates = [...new Set((await fileCandidates('cd')).concat(['..', '~']))];
  else if (cmd === 'open') candidates = (D.repos || []).map(r => r.name);
  else if (cmd === 'man' || cmd === 'help') candidates = [...new Set(Object.keys(MAN_PAGES).concat(Object.keys(COMMANDS)))];
  else if (cmd === 'corpus') candidates = ['ls', 'show', 'search', 'stats'];
  else if (cmd === 'theme') candidates = Object.keys(THEMES);
  else if (cmd === 'crt' || cmd === 'sound' || cmd === 'skyline') candidates = ['on', 'off'];
  else if (cmd === 'inspect') candidates = (await loadRuns()).map(r => r.trace_id || r.filename || '');
  return candidates;
}
async function updateGhost() {
  const { word, isFirst, cmd } = getCurrentWord();
  if (!word) { ghostText.textContent = ''; return; }
  const candidates = await getCandidates(word, isFirst, cmd);
  const matches = candidates.filter(c => c && c.toLowerCase().startsWith(word.toLowerCase()));
  if (matches.length === 0) ghostText.textContent = '';
  else if (matches.length === 1) ghostText.textContent = matches[0].slice(word.length);
  else {
    let prefix = matches[0];
    for (const m of matches) while (m && !m.toLowerCase().startsWith(prefix.toLowerCase())) prefix = prefix.slice(0, -1);
    ghostText.textContent = prefix.length > word.length ? prefix.slice(word.length) : '';
  }
}
function acceptCompletion() {
  if (ghostText.textContent) {
    cmdInput.value += ghostText.textContent;
    typedText.textContent = cmdInput.value;
    ghostText.textContent = '';
    updateGhost();
    playClick();
    return;
  }
  const { word, isFirst, cmd } = getCurrentWord();
  if (word) {
    getCandidates(word, isFirst, cmd).then(candidates => {
      const matches = candidates.filter(c => c && c.toLowerCase().startsWith(word.toLowerCase()));
      if (matches.length > 1) {
        print('<span class="dim">' + matches.map(escapeHtml).join('    ') + '</span>');
      }
    });
    return;
  }
  playBell();
}

/* =================== HISTORY =================== */
function navigateHistory(dir) {
  if (state.history.length === 0) return;
  if (dir === -1) {
    if (state.historyIndex === -1) state.historyIndex = state.history.length - 1;
    else if (state.historyIndex > 0) state.historyIndex--;
    else return;
  } else {
    if (state.historyIndex === -1) return;
    if (state.historyIndex < state.history.length - 1) state.historyIndex++;
    else { state.historyIndex = -1; cmdInput.value = ''; typedText.textContent = ''; ghostText.textContent = ''; return; }
  }
  cmdInput.value = state.history[state.historyIndex];
  typedText.textContent = cmdInput.value;
  ghostText.textContent = '';
  updateGhost();
}
function saveHistory(cmd) {
  if (state.history[state.history.length - 1] !== cmd) state.history.push(cmd);
  if (state.history.length > 100) state.history.shift();
  state.historyIndex = -1;
  try { localStorage.setItem('mailroomTerminalHistory', JSON.stringify(state.history)); } catch (e) {}
}

/* =================== PROMPT =================== */
function updatePrompt() {
  if (composeState) {
    promptText.innerHTML = '<span class="compose">mail</span>(<span style="color:var(--cyan)">' + composeState.mode + '</span>)<span class="path">▸</span>';
    statusPath.textContent = '~ (composing)';
    return;
  }
  const p = state.cwd === '~' ? ':~' : ':' + state.cwd.replace(/^~\//, '~/');
  promptText.innerHTML = '<span style="color:var(--green)">mailroom@floor</span><span class="path">' + p + '</span>$';
  statusPath.textContent = state.cwd;
}

/* =================== TYPED OUTPUT =================== */
let typingCancelled = false;
async function typeOutText(text, targetEl, delay = 1.4, pre = true) {
  typingCancelled = false;
  targetEl.innerHTML = '';
  const wrap = (buf) => pre ? '<pre>' + buf.replace(/\n/g, '<br>') + '</pre>' : buf.replace(/\n/g, '<br>');
  let buf = '';
  for (let i = 0; i < text.length; i++) {
    if (typingCancelled) {
      targetEl.innerHTML = wrap(escapeHtml(text));
      scrollBottom();
      return;
    }
    buf += escapeHtml(text[i]);
    targetEl.innerHTML = wrap(buf);
    if (i % 6 === 0) scrollBottom();
    if (text[i] !== ' ' && text[i] !== '\n' && i % 2 === 0) await sleep(reduced() ? 0 : delay);
    else if (text[i] === '\n') await sleep(reduced() ? 0 : delay * 2);
  }
  scrollBottom();
}
/* man-style animated scroll for help/man */
function printManPage(text) {
  const div = document.createElement('div');
  div.className = 'line man-page';
  output.appendChild(div);
  scrollBottom();
  typeOutText(text, div, 1.4);
}

/* =================== AMBIENT SKYLINE =================== */
function buildSkyline(svg, fill) {
  const W = 1440, H = 120;
  let d = 'M0 ' + H + ' L0 60';
  let x = 0;
  while (x < W) {
    const w = 30 + Math.random() * 46;
    const h = 22 + Math.random() * 52;
    d += ' L' + (x + w / 2).toFixed(1) + ' ' + (60 - h).toFixed(1)
       + ' L' + (x + w).toFixed(1) + ' ' + 60;
    x += w * 0.55;
  }
  d += ' L' + W + ' 60 L' + W + ' ' + H + ' Z';
  svg.innerHTML = '<path d="' + d + '" fill="' + fill + '"/>';
}
function spawnConveyorDots(container, count) {
  if (reduced()) return;
  for (let i = 0; i < count; i++) {
    const f = document.createElement('div');
    f.className = 'conveyor-dot';
    f.style.left = (4 + Math.random() * 92) + '%';
    f.style.top = (8 + Math.random() * 80) + '%';
    f.style.setProperty('--dx', ((Math.random() * 60) - 30).toFixed(0) + 'px');
    f.style.setProperty('--dy', ((Math.random() * 40) - 20).toFixed(0) + 'px');
    f.style.animationDuration = (4 + Math.random() * 6).toFixed(2) + 's, ' + (2.5 + Math.random() * 4).toFixed(2) + 's';
    f.style.animationDelay = (Math.random() * 6).toFixed(2) + 's, ' + (Math.random() * 4).toFixed(2) + 's';
    container.appendChild(f);
  }
}
function initSkyline() {
  const root = $('ambientSkyline');
  if (!root) return;
  root.classList.toggle('off', !state.skyline);
  buildSkyline($('skylineBack'), 'var(--sky-2)');
  buildSkyline($('skylineFront'), 'var(--sky-1)');
  spawnConveyorDots($('ambientConveyor'), 9);
}
function setSkyline(on) {
  state.skyline = on;
  const root = $('ambientSkyline');
  if (root) root.classList.toggle('off', !on);
  savePrefs();
}

/* =================== RENDERERS =================== */
function verdictClass(v) {
  if (v === 'CORRECT') return 'success';
  if (v === 'PARTIAL') return 'warn';
  if (v === 'MISS') return 'error';
  return 'dim';
}
async function floorListing() {
  const runs = await loadRuns();
  if (!runs.length) {
    print('<span class="warn">floor closed — no snapshot data (../data/traces.json).</span>');
    print('<span class="dim">run the server + scripts/export_snapshot.py to populate the Pages snapshot.</span>');
    return;
  }
  const sorted = runs.slice().sort((a, b) => {
    const ia = STAGE_ORDER.indexOf(a.stage); const ib = STAGE_ORDER.indexOf(b.stage);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
  });
  const rows = sorted.map(r => {
    const v = r.verdict || '-';
    return '<tr><td>' + escapeHtml((r.filename || r.trace_id || '').slice(0, 34)) + '</td>'
      + '<td>' + escapeHtml(STAGE_NAME[r.stage] || r.stage || '?') + '</td>'
      + '<td>' + escapeHtml((r.doc_type || '-').replace(/_/g, ' ')) + '</td>'
      + '<td>' + fmt(r.classification_confidence) + '</td>'
      + '<td>' + fmt(r.extraction_confidence) + '</td>'
      + '<td class="' + verdictClass(v) + '">' + escapeHtml(v) + '</td>'
      + '<td>' + fmt(r.quality) + '</td>'
      + '<td>' + money(r.cost_usd) + '</td>'
      + '<td>' + escapeHtml(((r.routing_path || []).slice(0, 5)).join('>')) + '</td></tr>';
  }).join('');
  print('<div class="run-story"><h1>FLOOR — runs in the window</h1>'
    + '<table class="mr"><thead><tr><th>FILE</th><th>STATION</th><th>DOC TYPE</th><th>CLS</th><th>EXT</th><th>VERDICT</th><th>QUAL</th><th>COST</th><th>ROUTE</th></tr></thead>'
    + '<tbody>' + rows + '</tbody></table>'
    + '<p class="post-footer">' + sorted.length + ' runs · snapshot export · <span class="dim">live floor: mailroom-tui or the server</span></p></div>');
}
async function runStory(run) {
  const head = '<div class="run-story"><h1>' + escapeHtml(run.filename || run.trace_id || 'run') + '</h1>'
    + '<div class="kv">'
    + '<b>trace</b><span>' + escapeHtml(run.trace_id || '-') + '</span>'
    + '<b>stage</b><span>' + escapeHtml(run.stage || '-') + '</span>'
    + '<b>doc type</b><span>' + escapeHtml((run.doc_type || '-').replace(/_/g, ' ')) + '</span>'
    + '<b>environment</b><span>' + escapeHtml(run.environment || '-') + '</span>'
    + (run.verdict ? '<b>verdict</b><span class="' + verdictClass(run.verdict) + '">' + escapeHtml(run.verdict) + '</span>' : '')
    + (run.quality !== undefined && run.quality !== null ? '<b>quality</b><span>' + fmt(run.quality) + '</span>' : '')
    + '</div>';
  const stages = (run.routing_path || []).map((s, i) =>
    '<div class="stage-line"><span class="st">' + (i + 1) + '.</span> '
    + escapeHtml(String(s)) + (STAGE_NAME[s] ? ' <span class="dim">(' + STAGE_NAME[s] + ')</span>' : '') + '</div>').join('');
  return head + (stages ? '<h2>routing</h2>' + stages : '')
    + (run.failure_class ? '<p class="error">failure: ' + escapeHtml(run.failure_class) + (run.error_message ? ' — ' + escapeHtml(String(run.error_message)) : '') + '</p>' : '')
    + '</div>';
}
async function catRun(id) {
  const runs = await loadRuns();
  const run = runs.find(r => (r.trace_id === id) || (r.filename === id));
  if (!run) { print('<span class="warn">run not found: ' + escapeHtml(id) + '</span>'); return; }
  print(await runStory(run));
  const detailUrl = DATA_DIR + 'runs/' + encodeURIComponent(run.trace_id) + '.json';
  try {
    const detail = await getJSON(detailUrl);
    const spans = detail.spans || [];
    if (spans.length) {
      const rows = spans.map(s =>
        '<tr><td>' + escapeHtml(s.name || '?') + (s.is_root ? ' <span class="dim">[root]</span>' : '') + '</td>'
        + '<td>' + escapeHtml(s.observation_type || 'SPAN') + '</td>'
        + '<td class="' + (s.status === 'SUCCESS' ? 'success' : s.status === 'ERROR' ? 'error' : 'warn') + '">' + escapeHtml(s.status || '?') + '</td>'
        + '<td>' + fmt(s.latency, n => n.toFixed(1) + 's') + '</td>'
        + '<td>' + escapeHtml((s.error_message || '').slice(0, 40)) + '</td></tr>').join('');
      print('<div class="run-story"><h2>OBSERVATIONS (' + spans.length + ')</h2>'
        + '<table class="mr"><thead><tr><th>SPAN</th><th>TYPE</th><th>STATUS</th><th>LATENCY</th><th>ERROR</th></tr></thead>'
        + '<tbody>' + rows + '</tbody></table></div>');
    }
    const gens = detail.generations || [];
    if (gens.length) {
      const rows = gens.map(g =>
        '<tr><td>' + escapeHtml(g.name || '-') + '</td><td>' + escapeHtml(g.model || '-') + '</td>'
        + '<td>' + (g.usage_input_tokens || 0) + '</td><td>' + (g.usage_output_tokens || 0) + '</td>'
        + '<td>' + money(g.cost_usd) + '</td><td>' + fmt(g.latency, n => n.toFixed(1) + 's') + '</td></tr>').join('');
      print('<div class="run-story"><h2>LLM GENERATIONS (' + gens.length + ')</h2>'
        + '<table class="mr"><thead><tr><th>CALL</th><th>MODEL</th><th>IN</th><th>OUT</th><th>COST</th><th>LATENCY</th></tr></thead>'
        + '<tbody>' + rows + '</tbody></table></div>');
    }
    const scores = detail.scores || {};
    const entries = Array.isArray(scores) ? scores : Object.entries(scores).map(([k, v]) => ({ name: k, value: v }));
    if (entries.length) {
      const rows = entries.filter(s => s && s.name !== undefined)
        .map(s => '<tr><td>' + escapeHtml(String(s.name)) + '</td><td>' + escapeHtml(String(s.value)) + '</td></tr>').join('');
      print('<div class="run-story"><h2>SCORES</h2><table class="mr"><tbody>' + rows + '</tbody></table></div>');
    }
  } catch (e) {
    print('<span class="dim">(no detail snapshot for this run)</span>');
  }
}
async function metricsView() {
  try {
    const m = await getJSON(DATA_DIR + 'metrics.json');
    const rows = [
      ['total docs', m.total_docs], ['archived', m.archived], ['review', m.review],
      ['reconsider', m.reconsideration], ['failed', m.failed], ['in flight', m.in_flight],
      ['llm calls', m.llm_calls], ['total cost', money(m.total_cost_usd)],
      ['total tokens', m.total_tokens], ['avg cost/doc', money(m.avg_cost_usd)],
      ['avg latency', m.avg_latency_s !== undefined && m.avg_latency_s !== null ? m.avg_latency_s.toFixed(1) + 's' : '-'],
      ['p95 gen latency', m.p95_generation_latency_s !== undefined && m.p95_generation_latency_s !== null ? m.p95_generation_latency_s.toFixed(1) + 's' : '-'],
      ['avg quality', m.avg_quality !== undefined && m.avg_quality !== null ? m.avg_quality.toFixed(2) : '-'],
    ];
    const vc = m.verdict_counts || {};
    Object.keys(vc).sort().forEach(k => rows.push(['verdict ' + k, vc[k]]));
    print('<div class="run-story"><h1>METRICS</h1><table class="mr"><tbody>'
      + rows.map(([k, v]) => '<tr><td><b>' + escapeHtml(String(k)) + '</b></td><td>' + escapeHtml(String(v === undefined || v === null ? '-' : v)) + '</td></tr>').join('')
      + '</tbody></table></div>');
  } catch (e) {
    print('<span class="warn">metrics unavailable — no snapshot (../data/metrics.json).</span>');
  }
}
async function reviewView() {
  try {
    const data = await getJSON(DATA_DIR + 'review-queue.json');
    const runs = (data.runs || data) || [];
    const list = Array.isArray(runs) ? runs : [];
    if (!list.length) { print('<span class="dim">review siding is empty — nothing waiting on a human.</span>'); return; }
    const rows = list.map(r => {
      const v = r.verdict || '-';
      const why = r.failure_class || r.escalation_reason || (r.review_causes || []).join(', ') || r.review_decision || r.error_message || '-';
      return '<tr><td>' + escapeHtml((r.filename || r.trace_id || '').slice(0, 34)) + '</td>'
        + '<td>' + escapeHtml((r.doc_type || '-').replace(/_/g, ' ')) + '</td>'
        + '<td>' + fmt(r.classification_confidence) + '</td><td>' + fmt(r.extraction_confidence) + '</td>'
        + '<td class="' + verdictClass(v) + '">' + escapeHtml(v) + '</td>'
        + '<td class="warn">' + escapeHtml(String(why).slice(0, 50)) + '</td></tr>';
    }).join('');
    print('<div class="run-story"><h1>REVIEW SIDING — waiting on a human</h1>'
      + '<table class="mr"><thead><tr><th>FILE</th><th>DOC TYPE</th><th>CLS</th><th>EXT</th><th>VERDICT</th><th>WHY</th></tr></thead>'
      + '<tbody>' + rows + '</tbody></table>'
      + '<p class="post-footer"><span class="dim">resolve via mailroom-tui --resolve, the Observatory, or the pixel console.</span></p></div>');
  } catch (e) {
    print('<span class="warn">review queue unavailable — no snapshot (../data/review-queue.json).</span>');
  }
}
async function sessionsView() {
  try {
    const data = await getJSON(DATA_DIR + 'sessions.json');
    const sessions = (data.sessions || data) || [];
    const list = Array.isArray(sessions) ? sessions : [];
    if (!list.length) { print('<span class="dim">no matters/sessions in the snapshot.</span>'); return; }
    const rows = list.map(s => {
      const runs = s.runs || [];
      const latest = runs.length ? ((runs[0].filename || runs[0].trace_id || '').slice(0, 28) + ' [' + (runs[0].stage || '-') + ']') : '-';
      return '<tr><td>' + escapeHtml(String(s.name || s.id || 'matter').slice(0, 28)) + '</td>'
        + '<td>' + (s.trace_count || runs.length) + '</td>'
        + '<td>' + escapeHtml(String(s.updated_at || '-').slice(0, 19)) + '</td>'
        + '<td>' + escapeHtml(latest) + '</td></tr>';
    }).join('');
    print('<div class="run-story"><h1>MATTERS / SESSIONS</h1>'
      + '<table class="mr"><thead><tr><th>SESSION</th><th>TRACES</th><th>UPDATED</th><th>LATEST</th></tr></thead>'
      + '<tbody>' + rows + '</tbody></table></div>');
  } catch (e) {
    print('<span class="warn">sessions unavailable — no snapshot (../data/sessions.json).</span>');
  }
}

/* =================== CORPUS =================== */
async function corpusLs(args) {
  await loadCorpusCatalog();
  if (!corpusCache.rows.length) {
    print('<span class="warn">corpus catalog unavailable — ../data/corpus.json missing. run scripts/export_corpus_catalog.py.</span>');
    return;
  }
  const cls = flag(args, '--class');
  const split = flag(args, '--split');
  const page = parseInt(flag(args, '--page', '0') || '0', 10);
  const limit = parseInt(flag(args, '--limit', '25') || '25', 10);
  let rows = corpusCache.rows;
  if (cls) rows = rows.filter(r => (r.doc_class || 'unknown') === cls);
  if (split) rows = rows.filter(r => r.split === split);
  const start = page * limit;
  const pageRows = rows.slice(start, start + limit);
  if (!pageRows.length) {
    print('<span class="warn">no corpus rows on page ' + page + ' (filtered to ' + rows.length + ').</span>');
    return;
  }
  const body = pageRows.map(r =>
    '<tr><td>' + escapeHtml(r.filename.slice(0, 40)) + '</td>'
    + '<td>' + escapeHtml(r.split) + '</td>'
    + '<td>' + escapeHtml((r.doc_class || '-').replace(/_/g, ' ')) + '</td>'
    + '<td>' + escapeHtml((r.doc_subclass || '-').replace(/_/g, ' ')) + '</td>'
    + '<td>' + escapeHtml(String(r.sha256 || '-').slice(0, 12)) + '</td>'
    + '<td>' + (r.chars || '-') + '</td></tr>').join('');
  print('<div class="run-story"><h1>MAILROOM-CORPUS — ' + rows.length + ' rows (page ' + page + ')</h1>'
    + '<table class="mr"><thead><tr><th>FILE</th><th>SPLIT</th><th>DOC CLASS</th><th>SUBCLASS</th><th>SHA256</th><th>CHARS</th></tr></thead>'
    + '<tbody>' + body + '</tbody></table>'
    + '<p class="post-footer"><span class="dim">' + (corpusCache.meta.dataset || 'Lucius-Morningstar/mailroom-dataset') + ' · catalog export · '
    + '<span class="amber">corpus show &lt;filename&gt;</span> fetches the full row live from the Hub.</span></p></div>');
}
async function corpusShow(filename) {
  await loadCorpusCatalog();
  const row = findCatalogRow(filename);
  if (!row) {
    print('<span class="warn">' + escapeHtml(filename) + ' not in the catalog. try: corpus ls</span>');
    return;
  }
  print('<div class="run-story"><h1>' + escapeHtml(filename) + '</h1>'
    + '<div class="kv">'
    + '<b>split</b><span>' + escapeHtml(row.split) + '</span>'
    + '<b>index</b><span>' + row.index + '</span>'
    + '<b>class</b><span>' + escapeHtml((row.doc_class || '-').replace(/_/g, ' ')) + '</span>'
    + '<b>subclass</b><span>' + escapeHtml((row.doc_subclass || '-').replace(/_/g, ' ')) + '</span>'
    + '<b>sha256</b><span>' + escapeHtml(row.sha256 || '-') + '</span>'
    + '</div></div>');
  print('<span class="dim">fetching full row from the Hub…</span>');
  try {
    const full = await hfRow('default', row.split, row.index);
    const text = (full && full.doc_text) || '';
    const clipped = text.length > 6000 ? text.slice(0, 6000) + '\n\n… [truncated — the full text lives on the Hub]' : text;
    print('<div class="post"><h2>DOC TEXT (' + text.length + ' chars)</h2>' + renderMarkdown(clipped) + '</div>');
  } catch (e) {
    print('<span class="error">hub unreachable — live row fetch failed (corpus closed).</span>');
  }
  if (row.gt_index >= 0) {
    try {
      const gt = await hfRow('ground_truth', row.split, row.gt_index);
      const body = Object.keys(gt || {}).filter(k => k !== 'filename')
        .filter(k => gt[k] !== null && gt[k] !== undefined && gt[k] !== '')
        .sort()
        .map(k => '<tr><td><b>' + escapeHtml(k.replace(/_/g, ' ')) + '</b></td><td>' + escapeHtml(String(gt[k]).slice(0, 70)) + '</td></tr>').join('');
      if (body) print('<div class="post"><h2>GROUND TRUTH</h2><table class="mr"><tbody>' + body + '</tbody></table></div>');
    } catch (e) { /* GT row optional */ }
  } else {
    print('<span class="dim">(no ground-truth index for this file)</span>');
  }
}
async function corpusSearch(term, split, limit) {
  await loadCorpusCatalog();
  const needle = term.toLowerCase();
  let hits = corpusCache.rows.filter(r =>
    [r.filename, r.doc_class, r.doc_subclass].filter(Boolean).join(' ').toLowerCase().includes(needle));
  if (split) hits = hits.filter(r => r.split === split);
  hits = hits.slice(0, limit);
  if (!hits.length) {
    print('<span class="warn">no corpus matches for "' + escapeHtml(term) + '" (filename/class/subclass).</span>');
    return;
  }
  const body = hits.map(r =>
    '<tr><td>' + escapeHtml(r.filename.slice(0, 40)) + '</td>'
    + '<td>' + escapeHtml(r.split) + '</td>'
    + '<td>' + escapeHtml((r.doc_class || '-').replace(/_/g, ' ')) + '</td>'
    + '<td>' + escapeHtml((r.doc_subclass || '-').replace(/_/g, ' ')) + '</td></tr>').join('');
  print('<div class="run-story"><h1>CORPUS SEARCH — ' + escapeHtml(term) + ' (' + hits.length + ')</h1>'
    + '<table class="mr"><thead><tr><th>FILE</th><th>SPLIT</th><th>DOC CLASS</th><th>SUBCLASS</th></tr></thead>'
    + '<tbody>' + body + '</tbody></table></div>');
}
async function corpusStats() {
  await loadCorpusCatalog();
  if (!corpusCache.rows.length) {
    print('<span class="warn">corpus catalog unavailable.</span>');
    return;
  }
  const splits = {};
  const classes = {};
  for (const r of corpusCache.rows) {
    splits[r.split] = (splits[r.split] || 0) + 1;
    const k = r.doc_class || 'unknown';
    classes[k] = (classes[k] || 0) + 1;
  }
  const splitRows = Object.keys(splits).map(k => '<tr><td><b>' + escapeHtml(k) + '</b></td><td>' + splits[k] + '</td></tr>').join('');
  const classRows = Object.keys(classes).sort((a, b) => classes[b] - classes[a])
    .map(k => '<tr><td><b>' + escapeHtml(k.replace(/_/g, ' ')) + '</b></td><td>' + classes[k] + '</td></tr>').join('');
  print('<div class="run-story"><h1>CORPUS STATS — ' + escapeHtml(corpusCache.meta.dataset || 'Lucius-Morningstar/mailroom-dataset') + '</h1>'
    + '<h2>splits</h2><table class="mr"><tbody>' + splitRows + '</tbody></table>'
    + '<h2>doc classes</h2><table class="mr"><tbody>' + classRows + '</tbody></table>'
    + '<p class="post-footer"><span class="dim">revision ' + escapeHtml(String(corpusCache.meta.revision || '').slice(0, 12)) + ' · generated ' + escapeHtml(String(corpusCache.meta.generated_at || '').slice(0, 19)) + 'Z</span></p></div>');
}

/* =================== REPOS =================== */
function reposListing(name) {
  const repos = D.repos || [];
  if (name) {
    const repo = repos.find(r => r.name.toLowerCase() === name.toLowerCase());
    if (!repo) { print('<span class="warn">no constellation repo "' + escapeHtml(name) + '" — try: repos</span>'); return; }
    print('<div class="run-story"><h1>' + escapeHtml(repo.name) + '</h1>'
      + '<div class="kv">'
      + '<b>role</b><span>' + escapeHtml(repo.role) + '</span>'
      + '<b>dist</b><span>' + escapeHtml(repo.dist) + '</span>'
      + '<b>url</b><span><a href="' + repo.url + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(repo.url) + '</a></span>'
      + (repo.homepage ? '<b>site</b><span><a href="' + repo.homepage + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(repo.homepage) + '</a></span>' : '')
      + '</div><p>' + escapeHtml(repo.blurb) + '</p>'
      + '<p class="post-footer"><span class="amber">open ' + escapeHtml(repo.name) + '</span> jumps there in a new tab.</p></div>');
    return;
  }
  const items = repos.map(r =>
    '<span class="file md">' + escapeHtml(r.name) + '</span>').join('  ');
  print('<div class="run-story"><h1>LLM-MAILROOM CONSTELLATION (' + repos.length + ' repos)</h1>'
    + '<div class="listing">' + items + '</div>'
    + '<p class="post-footer"><span class="dim">repos &lt;name&gt; for details · open &lt;name&gt; for the GitHub page.</span></p></div>');
}

/* =================== COMMANDS =================== */
function flag(args, name, def) {
  for (let i = 0; i < args.length; i++) {
    if (args[i] === name) return args[i + 1] !== undefined ? args[i + 1] : def;
    if (args[i].startsWith(name + '=')) return args[i].split('=')[1];
  }
  return def;
}
function stripFlags(args, names) {
  const out = [];
  for (let i = 0; i < args.length; i++) {
    if (names.includes(args[i])) { i++; continue; }
    if (names.some(n => args[i].startsWith(n + '='))) continue;
    out.push(args[i]);
  }
  return out;
}

const COMMANDS = {};
COMMANDS.help = (args) => {
  if (args[0]) {
    if (MAN_PAGES[args[0]]) printManPage(MAN_PAGES[args[0]]);
    else if (COMMANDS[args[0]]) printManPage(args[0].toUpperCase() + '(1)\n\n    No detailed manual. Try \'' + args[0] + '\' directly.');
    else print('<span class="error">man: no manual entry for \'' + escapeHtml(args[0]) + '\'</span>');
    return;
  }
  printManPage(D ? D.help : 'no help text');
};
COMMANDS.man = (args) => { if (args[0] && MAN_PAGES[args[0]]) printManPage(MAN_PAGES[args[0]]); else COMMANDS.help(args); };
COMMANDS.ls = async (args) => {
  const target = args[0] ? resolvePath(args[0]) : state.cwd;
  if (!isDir(target)) { print('<span class="error">ls: ' + escapeHtml(target) + ': not a directory</span>'); return; }
  const items = await listDir(target);
  if (items === null || !items.length) { print('<span class="dim">(empty)</span>'); return; }
  const html = items.map(i =>
    '<span class="file ' + (i.type === 'dir' ? 'dir' : i.cls || '') + '">' + escapeHtml(i.name) + '</span>').join('  ');
  print('<div class="listing">' + html + '</div>');
};
COMMANDS.cat = async (args) => {
  if (!args[0]) { print('usage: cat <file>'); return; }
  const file = resolveFile(args[0]);
  if (!file) {
    print('<span class="error">cat: ' + escapeHtml(args[0]) + ': no such file</span>');
    return;
  }
  if (file.kind === 'readme') print(renderMarkdown((D.about || []).join('\n').split('## whoami')[0] || 'THE MAILROOM terminal.'));
  if (file.kind === 'about') print(renderMarkdown((D.about || []).join('\n')));
  if (file.kind === 'plan') print(renderMarkdown((D.plan || []).join('\n')));
  if (file.kind === 'contact') print(renderMarkdown((D.contact || []).join('\n')));
  if (file.kind === 'run') await catRun(file.id);
  if (file.kind === 'repo') reposListing(file.name);
  if (file.kind === 'corpus') await corpusShow(file.filename);
};
COMMANDS.cd = async (args) => {
  const target = resolvePath(args[0] || '~');
  if (target === '~' || isDir(target)) {
    state.cwd = target;
    updatePrompt();
    return;
  }
  print('<span class="error">cd: ' + escapeHtml(args[0]) + ': no such directory</span>');
};
COMMANDS.pwd = () => print('<span class="amber">' + escapeHtml(state.cwd) + '</span>');
COMMANDS.tree = async () => {
  await loadCorpusCatalog();
  const topicsN = (await topics()).length;
  print('<pre class="tree">~/\n├── runs/          pipeline runs in the window\n├── corpus/        the mailroom-dataset corpus (' + (corpusCache.rows.length || '?') + ' rows)\n├── repos/         the LLM-Mailroom constellation (' + ((D.repos || []).length) + ' repos)\n└── topics/        doc-class tags (' + topicsN + ')\n    README.md  .about  .plan  .contact</pre>');
};
COMMANDS.floor = async () => { await floorListing(); };
COMMANDS.inspect = async (args) => {
  if (!args[0]) { print('usage: inspect <trace-id>'); return; }
  await catRun(args[0]);
};
COMMANDS.review = async () => { await reviewView(); };
COMMANDS.metrics = async () => { await metricsView(); };
COMMANDS.sessions = async () => { await sessionsView(); };
COMMANDS.corpus = async (args) => {
  const sub = args[0] || 'ls';
  const rest = stripFlags(args.slice(1), ['--class', '--split', '--page', '--limit']);
  if (sub === 'ls') { await corpusLs(args.slice(1)); }
  else if (sub === 'show') { if (rest[0]) await corpusShow(rest[0]); else print('usage: corpus show <filename>'); }
  else if (sub === 'search') {
    const split = flag(args.slice(1), '--split');
    const limit = parseInt(flag(args.slice(1), '--limit', '20') || '20', 10);
    if (!rest[0]) { print('usage: corpus search <term> [--split X] [--limit N]'); return; }
    await corpusSearch(rest.join(' '), split, limit);
  }
  else if (sub === 'stats') { await corpusStats(); }
  else print('<span class="error">corpus: unknown subcommand \'' + escapeHtml(sub) + '\' — ls|show|search|stats</span>');
};
COMMANDS.repos = (args) => { reposListing(args[0] ? args[0] : ''); };
COMMANDS.open = (args) => {
  if (!args[0]) { print('usage: open <repo-name|url>'); return; }
  if (args[0].startsWith('http://') || args[0].startsWith('https://')) {
    window.open(args[0], '_blank', 'noopener');
    print('opened ' + escapeHtml(args[0]));
    return;
  }
  const repo = (D.repos || []).find(r => r.name.toLowerCase() === args[0].toLowerCase());
  if (!repo) { print('<span class="warn">no constellation repo "' + escapeHtml(args[0]) + '"</span>'); return; }
  window.open(repo.url, '_blank', 'noopener');
  print('opened <span class="cyan">' + escapeHtml(repo.name) + '</span> → ' + escapeHtml(repo.url));
};
COMMANDS.search = async (args) => {
  const term = args.join(' ');
  if (!term) { print('usage: search <terms>'); return; }
  let found = 0;
  const runs = await loadRuns();
  const runHits = runs.filter(r => ((r.filename || '') + ' ' + (r.trace_id || '') + ' ' + (r.doc_type || '')).toLowerCase().includes(term.toLowerCase()));
  runHits.slice(0, 10).forEach(r => {
    found++;
    print('<span class="amber">runs/' + escapeHtml(r.filename || r.trace_id || '') + '</span> <span class="dim">[' + escapeHtml(r.stage || '-') + ']</span>');
  });
  await loadCorpusCatalog();
  const corpusHits = corpusCache.rows.filter(r => r.filename.toLowerCase().includes(term.toLowerCase())).slice(0, 10);
  corpusHits.forEach(r => {
    found++;
    print('<span class="cyan">corpus/' + escapeHtml(r.filename) + '</span> <span class="dim">[' + escapeHtml((r.doc_class || '-').replace(/_/g, ' ')) + ']</span>');
  });
  if (!found) print('<span class="dim">no matches for "' + escapeHtml(term) + '".</span>');
  else print('<span class="dim">' + found + ' result(s).</span>');
};
COMMANDS.whoami = () => print('<div class="post">' + renderMarkdown((D.about || []).join('\n')) + '</div>');
COMMANDS.neofetch = () => {
  const art = D.banner ? '<span class="banner"><pre>' + escapeHtml(D.banner) + '</pre></span>' : '';
  print('<div class="neofetch">' + art
    + '<div>mailroom@floor — llm-mailroom visual engine</div>'
    + '<div>terminal edition · snapshot + live Hub corpus</div>'
    + '<div>sources: Langfuse traces (snapshot) · mailroom-dataset (Hub)</div>'
    + '<div>constellation: ' + (D.repos || []).length + ' repos · dataset: 3,302 rows</div></div>');
};
COMMANDS.mail = (args) => {
  const addr = args[0] || 'axios337@gmail.com';
  startCompose(addr);
};
COMMANDS.history = () => {
  if (!state.history.length) { print('<span class="dim">(no history yet)</span>'); return; }
  state.history.slice(-40).forEach((c, i) => print('  ' + (state.history.length - 40 + i + 1 > 0 ? state.history.length - 40 + i + 1 : i + 1) + '  ' + escapeHtml(c), 'dim'));
};
COMMANDS.clear = () => { clearScreen(); };
COMMANDS.date = () => print('<span class="cyan">' + new Date().toString() + '</span>');
COMMANDS.echo = (args) => print(escapeHtml(args.join(' ')));
COMMANDS.uname = () => print('<span class="green">mailroom-terminal — the llm-mailroom visual engine (static edition)</span>');
COMMANDS.theme = (args) => {
  if (!args[0]) { print('current theme: <span class="amber">' + state.theme + '</span> (amber | green | cyan)'); return; }
  if (!THEMES[args[0]]) { print('<span class="error">theme: unknown \'' + escapeHtml(args[0]) + '\' — amber | green | cyan</span>'); return; }
  applyTheme(args[0]);
  print('theme: <span class="amber">' + args[0] + '</span>');
};
COMMANDS.crt = (args) => {
  if (args[0] && ['on', 'off'].includes(args[0])) state.crt = args[0] === 'on';
  else if (args[0]) { print('<span class="error">crt: on|off</span>'); return; }
  $('crtOverlay').classList.toggle('off', !state.crt);
  $('statusCrt').textContent = state.crt ? 'on' : 'off';
  savePrefs();
  print('crt: ' + (state.crt ? '<span class="success">on</span>' : '<span class="dim">off</span>'));
};
COMMANDS.sound = (args) => {
  if (args[0] && ['on', 'off'].includes(args[0])) state.sound = args[0] === 'on';
  else if (args[0]) { print('<span class="error">sound: on|off</span>'); return; }
  $('statusSound').textContent = state.sound ? 'on' : 'off';
  savePrefs();
  if (state.sound) playClick();
  print('sound: ' + (state.sound ? '<span class="success">on</span>' : '<span class="dim">off</span>'));
};
COMMANDS.skyline = (args) => {
  if (args[0] && ['on', 'off'].includes(args[0])) setSkyline(args[0] === 'on');
  else if (args[0]) { print('<span class="error">skyline: on|off</span>'); return; }
  print('skyline: ' + (state.skyline ? '<span class="success">on</span>' : '<span class="dim">off</span>'));
};
COMMANDS.pixel = () => { window.open('../pixel/', '_blank', 'noopener'); print('opening the <span class="amber">pixel console</span>…'); };
COMMANDS.observatory = () => { window.open('/', '_blank', 'noopener'); print('opening the <span class="cyan">observatory</span> (terminal root)…'); };
COMMANDS.hub = () => { window.open('https://huggingface.co/datasets/Lucius-Morningstar/mailroom-dataset', '_blank', 'noopener'); print('opening the <span class="phosphor">mailroom-dataset</span> corpus on the Hub…'); };
COMMANDS.tui = () => {
  print('<div class="post"><h2>mailroom-tui — the same console in your own terminal</h2>'
    + '<pre><code>pip install -e "packages/The-Mailroom[dev]"\nmailroom-tui</code></pre>'
    + '<p>Then: <code>floor</code> live desk · <code>corpus ls</code> · <code>repos</code> · '
    + '<code>inspect &lt;trace&gt;</code> · <code>--resolve</code> for the review workflow.</p></div>');
};

const MAN_PAGES = D ? (D.manPages || {}) : {};

/* =================== COMPOSE (mail) =================== */
let composeState = null;
function startCompose(addr) {
  composeState = { addr: addr, subject: '', body: '', mode: 'addr' };
  updatePrompt();
  print('<span class="dim">composing to ' + escapeHtml(addr) + ' — the operator email.</span>');
  print('<span class="dim">enter a subject:</span>');
}
function composeLine(line) {
  if (composeState.mode === 'addr') {
    if (line) composeState.addr = line;
    composeState.mode = 'subject';
    print('<span class="dim">subject: ' + escapeHtml(line) + '</span>');
    print('<span class="dim">enter the body — a single "." on its own line sends:</span>');
    return;
  }
  if (composeState.mode === 'subject') {
    composeState.subject = line;
    composeState.mode = 'body';
    print('<span class="dim">body — end with "." on its own line:</span>');
    return;
  }
  if (line === '.') {
    finishCompose();
    return;
  }
  composeState.body += (composeState.body ? '\n' : '') + line;
}
function finishCompose() {
  const to = composeState.addr;
  const subject = composeState.subject || '(no subject)';
  const body = composeState.body || '(no body)';
  const mailto = 'mailto:' + encodeURIComponent(to)
    + '?subject=' + encodeURIComponent(subject)
    + '&body=' + encodeURIComponent(body);
  print('<div class="mail-summary"><b>message ready</b> — '
    + '<a href="' + mailto + '">open in your mail client</a><br>'
    + '<span class="dim">to: ' + escapeHtml(to) + ' · subject: ' + escapeHtml(subject) + ' · '
    + body.split('\n').length + ' line(s)</span></div>');
  composeState = null;
  updatePrompt();
}

/* =================== SHELL LOOP =================== */
async function execute(line) {
  if (composeState) { composeLine(line); return; }
  if (!line.trim()) return;
  print('<span class="cmd-echo">' + escapeHtml(state.cwd) + ' $ ' + escapeHtml(line) + '</span>');
  saveHistory(line);
  const words = line.trim().split(/\s+/);
  const cmd = words[0].toLowerCase();
  const args = words.slice(1);
  const fn = COMMANDS[cmd];
  if (!fn) { print('<span class="error shake">' + escapeHtml(cmd) + ': command not found</span> — try <span class="amber">help</span>'); return; }
  try { await fn(args); }
  catch (e) { print('<span class="error">' + escapeHtml(cmd) + ': ' + escapeHtml(String(e && e.message || e)) + '</span>'); }
}
function clearScreen() {
  output.innerHTML = '';
  sweepFx();
}
function boot() {
  applyTheme(state.theme, true);
  $('crtOverlay').classList.toggle('off', !state.crt);
  $('statusCrt').textContent = state.crt ? 'on' : 'off';
  $('statusSound').textContent = state.sound ? 'on' : 'off';
  setSkyline(state.skyline);
  initSkyline();
  updatePrompt();
  print('<div class="title-card"><pre class="banner">' + escapeHtml(D ? D.banner : '') + '</pre></div>');
  print('<div class="neofetch">mailroom@floor — llm-mailroom visual engine'
    + '<br><span class="dim">boot: tty · crt ' + (state.crt ? 'on' : 'off') + ' · theme ' + state.theme + ' · window 7d</span></div>');
  (D.motd || []).forEach(l => print('<div class="motd-line' + (l.startsWith('type') ? ' amber' : '') + '">' + escapeHtml(l) + '</div>'));
  print('<span class="dim">corpus: loading…</span>');
  loadCorpusCatalog().then(() => {
    if (corpusCache.rows.length) print('<span class="success">corpus catalog loaded — ' + corpusCache.rows.length + ' rows (train ' + (corpusCache.meta.splits || {}).train + ' / test ' + (corpusCache.meta.splits || {}).test + ').</span>');
    else print('<span class="warn">corpus catalog offline — ../data/corpus.json missing.</span>');
  });
  print('<span class="lore-line">' + pick(D.lore || ['the floor is live.']) + '</span>');
  print('<span class="dim">type help to begin — tab completes, arrows recall history.</span>');
  printBlank();
}

/* =================== INPUT WIRING =================== */
cmdInput.addEventListener('input', () => {
  typedText.textContent = cmdInput.value;
  updateGhost();
});
cmdInput.addEventListener('keydown', (e) => {
  if (e.key === 'Tab') {
    e.preventDefault();
    acceptCompletion();
    return;
  }
  if (e.key === 'ArrowUp') { e.preventDefault(); navigateHistory(-1); return; }
  if (e.key === 'ArrowDown') { e.preventDefault(); navigateHistory(1); return; }
  if (e.key === 'ArrowRight' || e.key === 'End') {
    if (e.key === 'End' || ghostText.textContent) { acceptCompletion(); e.preventDefault(); return; }
    return;
  }
  if (e.key === 'Enter') {
    e.preventDefault();
    const line = cmdInput.value;
    cmdInput.value = '';
    typedText.textContent = '';
    ghostText.textContent = '';
    execute(line);
    return;
  }
  if ((e.ctrlKey || e.metaKey) && (e.key === 'l' || e.key === 'L')) {
    e.preventDefault();
    clearScreen();
    return;
  }
  if (e.ctrlKey && (e.key === 'c' || e.key === 'C')) {
    e.preventDefault();
    if (composeState) { composeState = null; updatePrompt(); print('<span class="dim">compose cancelled.</span>'); return; }
    cmdInput.value = '';
    typedText.textContent = '';
    ghostText.textContent = '';
    return;
  }
  playClick();
});
document.addEventListener('click', () => cmdInput.focus());
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') cmdInput.focus();
});
setInterval(() => {
  $('statusTime').textContent = new Date().toLocaleTimeString([], { hour12: false });
}, 1000);

boot();
cmdInput.focus();