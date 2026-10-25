/* The-Mailroom API client: Langfuse-backed fetch endpoints + WebSocket
 * with reconnect. All display data flows through this module; nothing is
 * fabricated client-side.
 *
 * GH Pages edition additions:
 *  - Configurable API base URL: ?api=<url> (persisted to localStorage)
 *    -> lets the static site talk to any reachable Mailroom API server,
 *       including one running locally next to Phoenix.
 *  - Static snapshot mode: when no live API answers, bundled JSON under
 *    ./data/ (built by scripts/export_snapshot.py) is served instead.
 *  - Debug capture ring buffer exposed to agents at
 *    window.__MAILROOM_DEBUG__ ({ dump(), export(), clear(), setVerbose() }).
 */

const Mailroom = (() => {
  const qs = new URLSearchParams(location.search);

  // ---- API base resolution ---------------------------------------------
  // ?api= wins and persists so a Pages visitor only configures once.
  // ?api= (empty) CLEARS a stale persisted base — previously qs.get("api")
  // was falsy for "" so localStorage could never be unset, and a dead
  // localhost base blanked the GH Pages snapshot fallback.
  //
  // A crafted link could otherwise point this console — and its review
  // POSTs — at someone else's server for good. Loopback/same-origin bases
  // persist silently; any other host needs an explicit confirmation.
  function trustedBase(base) {
    if (!base) return true;
    try {
      const u = new URL(base, location.href);
      if (u.origin === location.origin) return true;
      return ["localhost", "127.0.0.1", "[::1]", "::1"].includes(u.hostname);
    } catch (e) {
      return false;
    }
  }
  let BASE = "";
  if (qs.has("api")) {
    const requested = (qs.get("api") || "").trim().replace(/\/+$/, "");
    if (trustedBase(requested) ||
        window.confirm(`Connect this console to the API server at ${requested}?\n` +
                       "Review decisions you make will be sent there.")) {
      BASE = requested;
      try { localStorage.setItem("mailroom.api", BASE); } catch (e) { /* private mode */ }
    }
  } else {
    try {
      BASE = (localStorage.getItem("mailroom.api") || "").trim().replace(/\/+$/, "");
    } catch (e) { BASE = ""; }
  }
  const url = (path) => {
    if (!BASE) return path;
    const p = path.startsWith("/") ? path : `/${path}`;
    return `${BASE}${p}`;
  };
  // Bundled snapshots live in the site's data/ dir (GH Pages docs/ or a local
  // export). Never prefix them with the live API BASE. On Pages the console
  // is staged under /pixel/ while data/ sits at the site root, so resolve
  // one level up there (a <meta name="mailroom-snapshot-root"> overrides).
  const SNAP_ROOT = (() => {
    const meta = document.querySelector('meta[name="mailroom-snapshot-root"]');
    if (meta && meta.content) return meta.content.replace(/\/?$/, "/");
    return /\/pixel\/(index\.html)?$/.test(location.pathname) ? "../" : "";
  })();
  const snapUrl = (path) => SNAP_ROOT + String(path).replace(/^\/+/, "");
  const safeId = (id) => String(id).replace(/[^A-Za-z0-9._-]/g, "_");

  // ---- debug capture -----------------------------------------------------
  const MAX_DEBUG_EVENTS = 500;
  const dbgEvents = [];
  let debugVerbose = qs.has("debug");
  try { debugVerbose = debugVerbose || localStorage.getItem("mailroom.debug") === "1"; } catch (e) { /* storage blocked */ }

  // ---- review-tray probe limiter -----------------------------------------
  // Every REVIEW card fires context + source probes on render; a long queue
  // fired ~50 in parallel and saturated the server threadpool (producer
  // probes can take seconds), starving /api/health. Cap probe concurrency.
  const PROBE_LIMIT = 4;
  const probeQueue = [];
  let probeActive = 0;
  function drainProbes() {
    while (probeActive < PROBE_LIMIT && probeQueue.length) {
      const { fn, resolve, reject } = probeQueue.shift();
      probeActive += 1;
      Promise.resolve().then(fn).then(resolve, reject).finally(() => {
        probeActive -= 1;
        drainProbes();
      });
    }
  }
  function probe(fn) {
    return new Promise((resolve, reject) => {
      probeQueue.push({ fn, resolve, reject });
      drainProbes();
    });
  }

  function capture(kind, fields) {
    dbgEvents.push({ t: new Date().toISOString(), kind, ...fields });
    while (dbgEvents.length > MAX_DEBUG_EVENTS) dbgEvents.shift();
    if (debugVerbose) console.debug(`[mailroom:${kind}]`, fields);
  }
  function dumpDebug(pretty = true) {
    const payload = {
      generated_at: new Date().toISOString(),
      href: location.href,
      location: location.href,
      api_base: BASE,
      static_mode: staticMode,
      debug_verbose: debugVerbose,
      eventCount: dbgEvents.length,
      user_agent: navigator.userAgent,
      events: dbgEvents.slice(),
    };
    return pretty ? JSON.stringify(payload, null, 2) : JSON.stringify(payload);
  }
  function exportDebug() {
    const text = dumpDebug();
    try { navigator.clipboard.writeText(text); } catch (e) { /* clipboard denied */ }
    const blob = new Blob([text], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "mailroom-debug.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    capture("debug-export", {});
  }

  async function pullServer() {
    const r = await fetch(url("/api/debug/bundle"), { headers: { Accept: "application/json" } });
    let body = null;
    try { body = await r.json(); } catch (e) { body = { error: String(e) }; }
    capture("server-bundle", { status: r.status, logs: ((body && body.server_logs) || []).length });
    return body;
  }
  async function pushClient() {
    const payload = JSON.parse(dumpDebug(false));
    const r = await fetch(url("/api/debug/client"), {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify(payload),
    });
    let body = null;
    try { body = await r.json(); } catch (e) { body = { error: String(e) }; }
    capture("client-push", { status: r.status });
    return body;
  }

  window.__MAILROOM_DEBUG__ = {
    events: dbgEvents,
    dump: dumpDebug,
    export: exportDebug,
    pullServer,
    pushClient,
    clear: () => { dbgEvents.length = 0; },
    setVerbose: (v) => {
      debugVerbose = !!v;
      try { localStorage.setItem("mailroom.debug", v ? "1" : "0"); } catch (e) {}
    },
    get verbose() { return debugVerbose; },
    get apiBase() { return BASE; },
  };

  // ---- static snapshot mode ----------------------------------------------
  let staticMode = false;
  const snapCache = new Map();

  async function enableStaticMode() {
    if (staticMode) return true;
    try {
      const res = await fetch(snapUrl("data/meta.json"), { cache: "no-store" });
      if (!res.ok) return false;
      snapCache.set("meta", { data: await res.json(), fetched: Date.now() });
      staticMode = true;
      capture("static-mode", { enabled: true });
      return true;
    } catch (e) {
      capture("static-mode", { enabled: false, error: String(e) });
      return false;
    }
  }

  async function snap(name) {
    if (snapCache.has(name)) {
      const hit = snapCache.get(name);
      // Static files can be refreshed by a re-deploy or local exporter run —
      // serve from memory briefly, then re-fetch.
      if (Date.now() - hit.fetched < 30000) return hit.data;
    }
    const t0 = performance.now();
    const path = snapUrl(`data/${name}.json`);
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status} data/${name}.json`);
    const data = await res.json();
    snapCache.set(name, { data, fetched: Date.now() });
    capture("fetch", { url: path, status: res.status, ms: Math.round(performance.now() - t0), mode: "static" });
    return data;
  }

  async function snapRun(id) {
    // Must match scripts/export_snapshot.py _safe_id, NOT encodeURIComponent
    // (a slug with ':' would 404 the sanitized filename on Pages).
    return snap(`runs/${safeId(id)}`);
  }

  // ---- remote API calls ---------------------------------------------------
  async function get(path) {
    const t0 = performance.now();
    let res;
    try {
      res = await fetch(url(path), { headers: { "Accept": "application/json" } });
    } catch (err) {
      capture("fetch", { url: path, error: String(err), ms: Math.round(performance.now() - t0) });
      throw err;
    }
    capture("fetch", { url: path, status: res.status, ms: Math.round(performance.now() - t0) });
    if (!res.ok) {
      // V-18: the server's 503/500 bodies carry a `detail` the SPA silently
      // discarded before — surface it in the error so screens can show why.
      let detail = "";
      try {
        const body = await res.json();
        detail = body && body.detail ? ` — ${body.detail}` : "";
      } catch (e) { /* non-JSON error body */ }
      throw new Error(`HTTP ${res.status} ${path}${detail}`);
    }
    return res.json();
  }

  // ---- operator auth (public binds) ---------------------------------------
  // On a hosted/public server, producer writes need an operator JWT. The
  // token lives in sessionStorage (per tab, never localStorage) and is only
  // requested after the server answers 401 to a write.
  const TOKEN_KEY = "mailroom.operatorToken";
  function operatorToken() {
    try { return sessionStorage.getItem(TOKEN_KEY) || ""; } catch (e) { return ""; }
  }
  function setOperatorToken(tok) {
    try {
      if (tok) sessionStorage.setItem(TOKEN_KEY, tok);
      else sessionStorage.removeItem(TOKEN_KEY);
    } catch (e) { /* storage blocked: token lives for this call only */ }
  }
  function askCredentials(message) {
    return new Promise((resolve) => {
      const dlg = document.createElement("dialog");
      dlg.className = "operator-login";
      dlg.innerHTML =
        '<form method="dialog"><p class="operator-login-msg"></p>' +
        '<label>USER <input name="u" autocomplete="username" required></label>' +
        '<label>PASS <input name="p" type="password" autocomplete="current-password" required></label>' +
        '<menu><button value="cancel" formnovalidate>CANCEL</button>' +
        '<button value="ok">LOG IN</button></menu></form>';
      dlg.querySelector(".operator-login-msg").textContent = message;
      document.body.appendChild(dlg);
      dlg.addEventListener("close", () => {
        const ok = dlg.returnValue === "ok";
        const u = dlg.querySelector('[name="u"]').value.trim();
        const p = dlg.querySelector('[name="p"]').value;
        dlg.remove();
        resolve(ok && u && p ? { username: u, password: p } : null);
      });
      dlg.showModal();
    });
  }
  async function operatorLogin(message) {
    const creds = await askCredentials(message || "Operator login required on this host.");
    if (!creds) return false;
    const res = await fetch(url("/v1/auth/login"), {
      method: "POST",
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(creds),
    });
    if (!res.ok) {
      let detail = "";
      try { const b = await res.json(); detail = b && b.detail ? ` — ${b.detail}` : ""; } catch (e) { /* ignore */ }
      showError(`Operator login failed (HTTP ${res.status})${detail}`);
      return false;
    }
    const body = await res.json();
    setOperatorToken(body.access_token || "");
    return !!body.access_token;
  }

  async function post(path, body, _retried = false) {
    const t0 = performance.now();
    const headers = { "Accept": "application/json", "Content-Type": "application/json" };
    const tok = operatorToken();
    if (tok) headers.Authorization = `Bearer ${tok}`;
    let res;
    try {
      res = await fetch(url(path), {
        method: "POST",
        headers,
        body: JSON.stringify(body || {}),
      });
    } catch (err) {
      capture("fetch", { url: path, error: String(err), ms: Math.round(performance.now() - t0), method: "POST" });
      throw err;
    }
    capture("fetch", { url: path, status: res.status, ms: Math.round(performance.now() - t0), method: "POST" });
    if (res.status === 401 && !_retried) {
      setOperatorToken("");
      if (await operatorLogin()) return post(path, body, true);
    }
    if (!res.ok) {
      let detail = "";
      try {
        const payload = await res.json();
        const msg = payload && (payload.detail || payload.error);
        if (msg != null) {
          detail = ` — ${typeof msg === "string" ? msg : JSON.stringify(msg)}`;
        }
      } catch (e) { /* non-JSON error body */ }
      throw new Error(`HTTP ${res.status} ${path}${detail}`);
    }
    return res.json();
  }

  function reviewContextQs(opts = {}) {
    const q = new URLSearchParams();
    if (opts.trace_id) q.set("trace_id", opts.trace_id);
    if (opts.filename) q.set("filename", opts.filename);
    if (opts.doc_id) q.set("doc_id", opts.doc_id);
    const qs = q.toString();
    return `/api/review/context${qs ? `?${qs}` : ""}`;
  }

  function reviewSourceQs(opts = {}) {
    const q = new URLSearchParams();
    if (opts.trace_id) q.set("trace_id", opts.trace_id);
    if (opts.filename) q.set("filename", opts.filename);
    if (opts.doc_id) q.set("doc_id", opts.doc_id);
    if (opts.download) q.set("download", "1");
    const qs = q.toString();
    return `/api/review/source${qs ? `?${qs}` : ""}`;
  }

  const remote = {
    health: () => get("/api/health"),
    meta: () => get("/api/meta"),
    traces: (since = 604800, limit = 200) => get(`/api/traces?since=${since}&limit=${limit}`),
    run: (id) => get(`/api/traces/${encodeURIComponent(id)}`),
    metrics: (since = 604800) => get(`/api/metrics?since=${since}`),
    sessions: (limit = 50) => get(`/api/sessions?limit=${limit}`),
    reviewQueue: (since = 604800) => get(`/api/review-queue?since=${since}`),
    pipeline: () => get("/api/pipeline"),
    reviewContext: (opts) => get(reviewContextQs(opts)),
    reviewResolve: (body) => post("/api/review/resolve", body),
    reviewAudit: (docId) => get(`/api/review/audit?doc_id=${encodeURIComponent(docId)}`),
    reviewSource: (opts) => get(reviewSourceQs(opts)),
    reviewSourceUrl: (opts) => url(reviewSourceQs(opts)),
  };

  const snapshots = {
    health: async () => ({
      ok: true, langfuse: true, mode: "snapshot", source: "snapshot",
      generated_at: (await snap("meta")).generated_at,
    }),
    meta: () => snap("meta"),
    traces: () => snap("traces"),
    run: (id) => snapRun(id),
    metrics: () => snap("metrics"),
    sessions: () => snap("sessions"),
    reviewQueue: () => snap("review-queue"),
    pipeline: async () => ({ configured: false, watcher: "snapshot", ok: null }),
    reviewContext: async () => ({
      configured: false, snapshot: true,
      error: "snapshot mode is read-only — review resolve needs a live API",
    }),
    reviewResolve: async () => {
      throw new Error("snapshot mode is read-only — review resolve needs a live API");
    },
    reviewAudit: async () => {
      throw new Error("snapshot mode is read-only — review audit needs a live API");
    },
    reviewSource: async () => ({
      configured: false, snapshot: true,
      error: "snapshot mode is read-only — document source needs a live API",
    }),
    reviewSourceUrl: () => "",
  };

  function dispatch(name, ...args) {
    return staticMode ? snapshots[name](...args) : remote[name](...args);
  }

  const api = {
    health: (...a) => dispatch("health", ...a),
    meta: (...a) => dispatch("meta", ...a),
    traces: (...a) => dispatch("traces", ...a),
    run: (...a) => dispatch("run", ...a),
    metrics: (...a) => dispatch("metrics", ...a),
    sessions: (...a) => dispatch("sessions", ...a),
    reviewQueue: (...a) => dispatch("reviewQueue", ...a),
    pipeline: (...a) => dispatch("pipeline", ...a),
    reviewContext: (...a) => dispatch("reviewContext", ...a),
    reviewResolve: (...a) => dispatch("reviewResolve", ...a),
    reviewAudit: (...a) => dispatch("reviewAudit", ...a),
    reviewSource: (...a) => dispatch("reviewSource", ...a),
    reviewSourceUrl: (opts) => staticMode ? "" : remote.reviewSourceUrl(opts),
  };

  const fmt = {
    // Pipeline costs are sub-cent at qwen/deepseek pricing — 2 decimals
    // rendered every run as "$0.00". Show 4 decimals below a cent.
    cost: (v) => {
      if (v == null) return "—";
      const n = Number(v);
      if (n !== 0 && Math.abs(n) < 0.01) return `$${n.toFixed(4)}`;
      return `$${n.toFixed(2)}`;
    },
    tokens: (v) => (v == null ? "—" : Number(v).toLocaleString("en-US")),
    latency: (v) => {
      if (v == null) return "—";
      const s = Number(v);
      if (s < 60) return `${s.toFixed(1)}s`;
      return `${Math.floor(s / 60)}m ${(s % 60).toFixed(0)}s`;
    },
    conf: (v) => (v == null ? "—" : `${(Number(v) * 100).toFixed(0)}%`),
    time: (iso) => {
      if (!iso) return "—";
      const d = new Date(iso);
      return isNaN(d) ? "—" : d.toLocaleTimeString("en-US", { hour12: false });
    },
    dateTime: (iso) => {
      if (!iso) return "—";
      const d = new Date(iso);
      return isNaN(d) ? "—" : d.toLocaleString("en-US", { month: "short", day: "2-digit", hour12: false });
    },
    short: (s, n = 26) => {
      if (s == null) return "—";
      s = String(s);
      return s.length > n ? `${s.slice(0, n - 1)}…` : s;
    },
  };

  const esc = (s) => {
    if (s == null) return "";
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  };

  function needsReviewActions(run) {
    if (!run) return false;
    return run.stage === "review" || !!run.needs_human || !!run.needs_reconsideration;
  }

  function defaultDisposition(run) {
    return run && run.stage === "review" ? "resume" : "record";
  }

  function reviewClassMap() {
    const meta = window.Mailroom && window.Mailroom.meta;
    const classes = (meta && meta.doc_classes) || {
      contract: "Contract / Agreement",
      corporate_record: "Corporate Record",
      correspondence: "Correspondence",
      insurance_claim: "Insurance Claim",
      merger_agreement: "Merger Agreement",
      unknown: "Unknown",
    };
    return classes;
  }

  function reviewSubclassMap() {
    const meta = window.Mailroom && window.Mailroom.meta;
    return (meta && meta.doc_subclasses) || {};
  }

  function classSelectHtml(selected) {
    const classes = reviewClassMap();
    const current = selected || "";
    const keys = Object.keys(classes);
    if (current && !keys.includes(current)) keys.unshift(current);
    const opts = [`<option value="">(keep current)</option>`]
      .concat(keys.map((k) => {
        const sel = k === current ? " selected" : "";
        return `<option value="${esc(k)}"${sel}>${esc(classes[k] || k)}</option>`;
      }));
    return opts.join("");
  }

  function subclassSelectHtml(docType, selected) {
    const catalog = reviewSubclassMap()[docType] || [];
    const current = selected || "";
    const opts = [`<option value="">(none / keep)</option>`];
    const seen = new Set();
    for (const k of catalog) {
      seen.add(k);
      const sel = k === current ? " selected" : "";
      opts.push(`<option value="${esc(k)}"${sel}>${esc(k)}</option>`);
    }
    if (current && !seen.has(current)) {
      opts.splice(1, 0, `<option value="${esc(current)}" selected>${esc(current)}</option>`);
    }
    return opts.join("");
  }

  function reviewPanel(run) {
    if (!needsReviewActions(run)) return "";
    const parked = run.stage === "review";
    const disp = defaultDisposition(run);
    const hint = parked
      ? "Correct the class if the sorter missed. Resume re-extracts with that class. Record appends an audit row only. Requeue copies the file to the inbox. Complete archives operator extracted_data without another LLM pass."
      : "This run is not parked in the review bin — Resume and Complete are disabled. Record writes an audit row; Requeue copies the file back to the inbox.";
    const currentType = run.doc_type || "";
    const currentSub = run.doc_subclass || run.contract_subtype || "";
    const hasSubs = (reviewSubclassMap()[currentType] || []).length > 0 || !!currentSub;
    const sourceQs = {
      trace_id: run.trace_id || "",
      filename: run.filename || "",
      doc_id: run.doc_id || "",
      download: true,
    };
    const openHref = staticMode ? "" : remote.reviewSourceUrl(sourceQs);
    return `<form class="review-resolve" data-trace="${esc(run.trace_id || "")}" data-filename="${esc(run.filename || "")}" data-doc-id="${esc(run.doc_id || "")}">
      <div class="review-resolve-head">HUMAN REVIEW</div>
      <p class="review-resolve-hint">${esc(hint)}</p>
      <div class="review-source">
        <div class="review-source-toolbar">
          <span class="review-source-label">DOCUMENT</span>
          ${openHref ? `<a class="review-source-open" href="${esc(openHref)}" target="_blank" rel="noopener">Open original</a>` : `<span class="review-source-open" hidden>Open original</span>`}
          <span class="review-source-badge" hidden>truncated</span>
        </div>
        <pre class="review-source-text">loading document text…</pre>
      </div>
      <label class="review-disp-label">doc type
        <select name="doc_type" class="review-disp review-doc-type">${classSelectHtml(currentType)}</select>
      </label>
      <label class="review-disp-label review-subclass-label"${hasSubs ? "" : " hidden"}>subtype
        <select name="doc_subclass" class="review-disp review-doc-subclass">${subclassSelectHtml(currentType, currentSub)}</select>
      </label>
      <textarea name="notes" class="review-notes" rows="2" placeholder="reviewer notes (stored on the producer audit chain)"></textarea>
      <label class="review-disp-label">disposition
        <select name="disposition" class="review-disp">
          <option value="resume" ${disp === "resume" ? "selected" : ""} ${parked ? "" : "disabled"}>Resume pipeline</option>
          <option value="record" ${disp === "record" ? "selected" : ""}>Record only (audit)</option>
          <option value="requeue">Requeue to inbox</option>
          <option value="complete" ${parked ? "" : "disabled"}>Complete (human extraction)</option>
        </select>
      </label>
      <label class="review-disp-label review-extracted-wrap"${parked ? "" : " hidden"}>extracted_data (JSON, required for Complete)
        <textarea name="extracted_data" class="review-notes review-extracted" rows="4" placeholder='{"claim_number": "…"}'></textarea>
      </label>
      <div class="review-resolve-btns">
        <button type="submit" class="px-btn mono review-approve" data-decision="approved">Approve</button>
        <button type="submit" class="px-btn mono review-reject" data-decision="rejected">Reject</button>
        <button type="submit" class="px-btn mono review-requeue" data-decision="approved" data-disposition="requeue">Requeue</button>
        <button type="submit" class="px-btn mono review-complete" data-decision="approved" data-disposition="complete" ${parked ? "" : "disabled"}>Complete</button>
      </div>
      <div class="review-resolve-status" aria-live="polite"></div>
    </form>`;
  }

  function fillSubclassSelect(select, docType, selected) {
    if (!select) return;
    select.innerHTML = subclassSelectHtml(docType, selected || "");
    const label = select.closest(".review-subclass-label");
    const catalog = reviewSubclassMap()[docType] || [];
    if (label) label.hidden = catalog.length === 0 && !selected;
  }

  function bindReviewSource(form) {
    const pane = form.querySelector(".review-source-text");
    const badge = form.querySelector(".review-source-badge");
    const open = form.querySelector(".review-source-open");
    if (!pane) return;
    probe(() => api.reviewSource({
      trace_id: form.dataset.trace,
      filename: form.dataset.filename,
      doc_id: form.dataset.docId,
    })).then((src) => {
      if (!src || src.configured === false) {
        pane.textContent = (src && src.error) || "live producer required to view the parked file";
        if (open) open.hidden = true;
        return;
      }
      // `readable` is optional on producer payloads — real text counts.
      if (src.readable === false || !src.text) {
        pane.textContent = src.error || "(empty document text)";
        if (open) open.hidden = true;
        return;
      }
      pane.textContent = src.text || "(empty document text)";
      if (badge) badge.hidden = !src.truncated;
      if (open) open.hidden = src.source === "lookup" || !src.filename;
    }).catch((err) => {
      pane.textContent = err.message || String(err);
    });
  }

  function bindReviewForms(root, { onDone } = {}) {
    if (!root) return;
    for (const form of root.querySelectorAll(".review-resolve")) {
      if (form.dataset.bound === "1") continue;
      form.dataset.bound = "1";
      form.addEventListener("click", (ev) => ev.stopPropagation());
      const typeSel = form.querySelector("select[name='doc_type']");
      const subSel = form.querySelector("select[name='doc_subclass']");
      if (typeSel) {
        typeSel.addEventListener("change", () => fillSubclassSelect(subSel, typeSel.value, ""));
      }
      bindReviewSource(form);
      probe(() => api.reviewContext({
        trace_id: form.dataset.trace,
        filename: form.dataset.filename,
        doc_id: form.dataset.docId,
      })).then((ctx) => {
        const extracted = ctx && ctx.document && ctx.document.extracted_data;
        const ta = form.querySelector("textarea[name='extracted_data']");
        if (ta && extracted && !ta.value) {
          ta.value = typeof extracted === "string" ? extracted : JSON.stringify(extracted, null, 2);
        }
      }).catch(() => { /* catalog probe is best-effort */ });
      form.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        const status = form.querySelector(".review-resolve-status");
        const btn = ev.submitter;
        const decision = (btn && btn.dataset.decision) || "approved";
        const disposition = (btn && btn.dataset.disposition)
          || (form.disposition && form.disposition.value)
          || "resume";
        const notes = (form.notes && form.notes.value) || "";
        const docType = (form.doc_type && form.doc_type.value) || "";
        const docSubclass = (form.doc_subclass && form.doc_subclass.value) || "";
        let extractedData;
        const rawExtracted = (form.extracted_data && form.extracted_data.value) || "";
        if (disposition === "complete" || rawExtracted.trim()) {
          try {
            extractedData = rawExtracted.trim() ? JSON.parse(rawExtracted) : undefined;
          } catch (err) {
            if (status) status.textContent = "extracted_data is not valid JSON";
            return;
          }
          if (disposition === "complete" && (!extractedData || typeof extractedData !== "object" || Array.isArray(extractedData))) {
            if (status) status.textContent = "Complete needs an extracted_data JSON object";
            return;
          }
        }
        if (status) status.textContent = "submitting…";
        try {
          const payload = {
            trace_id: form.dataset.trace,
            filename: form.dataset.filename,
            doc_id: form.dataset.docId,
            decision,
            disposition,
            notes,
            doc_type: docType,
            doc_subclass: docSubclass,
          };
          if (extractedData) payload.extracted_data = extractedData;
          const result = await api.reviewResolve(payload);
          const msg = `ok — ${result.disposition || disposition} ${result.decision || decision}${result.doc_id ? ` · ${result.doc_id}` : ""}`;
          if (status) status.textContent = msg;
          if (typeof onDone === "function") onDone(result, form);
        } catch (err) {
          if (status) status.textContent = err.message || String(err);
        }
      });
    }
  }

  let ws = null;
  let wsTimer = null;
  let wsRetry = 0;
  let connected = false;
  let errTimer = null;

  // V-18: one global error banner. Every silent `.catch(() => {})` across the
  // SPA is routed here, plus window.onerror for unhandled exceptions.
  function showError(msg) {
    const el = document.getElementById("error-banner");
    const text = msg && msg.message ? msg.message : String(msg || "unknown error");
    capture("error", { message: text });
    if (!el) {
      console.error(`[mailroom] ${text}`);
      return;
    }
    el.textContent = `ERROR — ${text}`;
    el.hidden = false;
    clearTimeout(errTimer);
    errTimer = setTimeout(() => { el.hidden = true; }, 8000);
  }

  window.addEventListener("error", (ev) => {
    const msg = ev.message || "unhandled script error";
    // Browser-noise that used to paint the error banner on an otherwise
    // healthy floor (ResizeObserver loop, cross-origin "Script error.").
    if (/ResizeObserver|Script error\.?$/i.test(msg)) return;
    showError(msg);
  });
  window.addEventListener("unhandledrejection", (ev) => {
    if (ev && ev.reason) showError(ev.reason);
  });

  function wsURL() {
    if (BASE) {
      const u = new URL(BASE, location.href);
      const proto = u.protocol === "https:" ? "wss" : "ws";
      return `${proto}://${u.host}/ws`;
    }
    const proto = location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${location.host}/ws`;
  }

  function connectWS(onMessage) {
    clearTimeout(wsTimer);
    try {
      if (ws) ws.close();
    } catch (e) { /* noop */ }
    capture("ws", { event: "connect-attempt", url: wsURL() });
    ws = new WebSocket(wsURL());
    ws.onopen = () => {
      wsRetry = 0;
      connected = true;
      capture("ws", { event: "open" });
      onMessage({ type: "status", connected: true });
    };
    ws.onmessage = (ev) => {
      capture("ws-frame", { bytes: ev.data ? ev.data.length : 0 });
      try {
        const parsed = JSON.parse(ev.data);
        onMessage(parsed);
      } catch (e) {
        // V-18: non-JSON WS frames were dropped silently — log them so protocol
        // drift from the server is visible instead of an unexplained stall.
        console.error(`[mailroom] non-JSON WS frame dropped: ${String(ev.data).slice(0, 200)}`);
        capture("ws-frame", { event: "non-json-dropped" });
      }
    };
    ws.onclose = () => {
      connected = false;
      capture("ws", { event: "close", retry: wsRetry });
      onMessage({ type: "status", connected: false });
      const delay = Math.min(30000, 1000 * 2 ** wsRetry++);
      wsTimer = setTimeout(() => connectWS(onMessage), delay);
    };
    ws.onerror = () => {
      try { ws.close(); } catch (e) { /* noop */ }
    };
  }

  function envFromTags(tags) {
    if (!Array.isArray(tags)) return null;
    const known = new Set(["live", "pilot", "dev", "test", "demo", "prod", "staging"]);
    for (const t of tags) if (known.has(t)) return t;
    return null;
  }

  const exports = {
    api, fmt, esc, connectWS, envFromTags, showError,
    reviewPanel, bindReviewForms, needsReviewActions,
    get wsConnected() { return connected; },
    get staticMode() { return staticMode; },
    enableStaticMode,
    get apiBase() { return BASE; },
    get debugVerbose() { return debugVerbose; },
    capture,
  };
  // Publish to window explicitly: a top-level `const` does NOT attach to
  // window, so window.Mailroom stayed undefined and any code touching it
  // (metrics.js demo-mode flag set by main.js) crashed in live mode.
  window.Mailroom = exports;
  return exports;
})();
