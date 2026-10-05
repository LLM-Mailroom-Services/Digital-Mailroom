/* Mailroom Observatory client — same-origin API + WebSocket.
 * Langfuse (or the configured source) remains the only display source. */
const Obs = (() => {
  function dbg(kind, payload) {
    try {
      if (window.ObservatoryDebug) window.ObservatoryDebug.record(kind, payload);
    } catch (_e) { /* debug module optional */ }
  }

  async function get(path) {
    const res = await fetch(path, { headers: { Accept: "application/json" } });
    if (!res.ok) {
      let detail = "";
      try {
        const body = await res.json();
        detail = body && body.detail ? ` — ${body.detail}` : "";
      } catch (e) { /* non-JSON error body */ }
      const err = new Error(`HTTP ${res.status} ${path}${detail}`);
      dbg("fetch-error", { url: path, status: res.status, message: err.message, where: "Obs.get" });
      throw err;
    }
    return res.json();
  }

  async function readError(res, path, where) {
    let detail = "";
    try {
      const payload = await res.json();
      const msg = payload && (payload.detail || payload.error);
      if (msg != null) {
        detail = ` — ${typeof msg === "string" ? msg : JSON.stringify(msg)}`;
      }
    } catch (e) { /* non-JSON error body */ }
    const err = new Error(`HTTP ${res.status} ${path}${detail}`);
    dbg("fetch-error", { url: path, status: res.status, message: err.message, where });
    throw err;
  }

  // Operator auth for producer writes on public hosts: JWT in
  // sessionStorage (per tab), requested only after a 401 from a write.
  const TOKEN_KEY = "mailroom.operatorToken";
  function operatorToken() {
    try { return sessionStorage.getItem(TOKEN_KEY) || ""; } catch (_e) { return ""; }
  }
  function setOperatorToken(tok) {
    try {
      if (tok) sessionStorage.setItem(TOKEN_KEY, tok);
      else sessionStorage.removeItem(TOKEN_KEY);
    } catch (_e) { /* storage blocked */ }
  }
  function authHeaders(base) {
    const tok = operatorToken();
    return tok ? { ...base, Authorization: `Bearer ${tok}` } : base;
  }
  function askCredentials(message) {
    return new Promise((resolve) => {
      const dlg = document.createElement("dialog");
      dlg.className = "operator-login";
      dlg.setAttribute("aria-labelledby", "operator-login-title");
      dlg.innerHTML =
        '<form method="dialog"><h2 id="operator-login-title">Operator login</h2>' +
        '<p class="operator-login-msg"></p>' +
        '<label>Username <input name="u" autocomplete="username" required></label>' +
        '<label>Password <input name="p" type="password" autocomplete="current-password" required></label>' +
        '<menu><button value="cancel" formnovalidate>Cancel</button>' +
        '<button value="ok" class="primary">Log in</button></menu></form>';
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
  async function operatorLogin() {
    const creds = await askCredentials("This host requires an operator login for review and inbox actions.");
    if (!creds) return false;
    const res = await fetch("/v1/auth/login", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(creds),
    });
    if (!res.ok) {
      await readError(res, "/v1/auth/login", "Obs.login").catch((e) => dbg("login-failed", { message: e.message }));
      return false;
    }
    const body = await res.json();
    setOperatorToken(body.access_token || "");
    return !!body.access_token;
  }

  async function sendWrite(path, init, where, retried = false) {
    const res = await fetch(path, { ...init, headers: authHeaders(init.headers) });
    if (res.status === 401 && !retried) {
      setOperatorToken("");
      if (await operatorLogin()) return sendWrite(path, init, where, true);
    }
    if (!res.ok) return readError(res, path, where);
    return res.json();
  }

  async function post(path, body) {
    return sendWrite(path, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    }, "Obs.post");
  }

  async function postForm(path, formData) {
    return sendWrite(path, {
      method: "POST",
      headers: { Accept: "application/json" },
      body: formData,
    }, "Obs.postForm");
  }

  const api = {
    health: () => get("/api/health"),
    meta: () => get("/api/meta"),
    traces: (since = 604800, limit = 200) => get(`/api/traces?since=${since}&limit=${limit}`),
    run: (id) => get(`/api/traces/${encodeURIComponent(id)}`),
    metrics: (since = 604800) => get(`/api/metrics?since=${since}`),
    sessions: (limit = 50) => get(`/api/sessions?limit=${limit}`),
    reviewQueue: (since = 604800) => get(`/api/review-queue?since=${since}`),
    pipeline: () => get("/api/pipeline"),
    reviewContext: (opts = {}) => {
      const q = new URLSearchParams();
      if (opts.trace_id) q.set("trace_id", opts.trace_id);
      if (opts.filename) q.set("filename", opts.filename);
      if (opts.doc_id) q.set("doc_id", opts.doc_id);
      const qs = q.toString();
      return get(`/api/review/context${qs ? `?${qs}` : ""}`);
    },
    reviewResolve: (body) => post("/api/review/resolve", body),
    inboxEnqueue: (formData) => postForm("/api/inbox/enqueue", formData),
    snapshot: () => get("/api/snapshot"),
    reviewAudit: (docId) => get(`/api/review/audit?doc_id=${encodeURIComponent(docId)}`),
    reviewSource: (opts = {}) => {
      const q = new URLSearchParams();
      if (opts.trace_id) q.set("trace_id", opts.trace_id);
      if (opts.filename) q.set("filename", opts.filename);
      if (opts.doc_id) q.set("doc_id", opts.doc_id);
      if (opts.download) q.set("download", "1");
      const qs = q.toString();
      return get(`/api/review/source${qs ? `?${qs}` : ""}`);
    },
    reviewSourceUrl: (opts = {}) => {
      const q = new URLSearchParams();
      if (opts.trace_id) q.set("trace_id", opts.trace_id);
      if (opts.filename) q.set("filename", opts.filename);
      if (opts.doc_id) q.set("doc_id", opts.doc_id);
      q.set("download", "1");
      return `/api/review/source?${q.toString()}`;
    },
  };

  const fmt = {
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
    when: (iso) => {
      if (!iso) return "—";
      const d = new Date(iso);
      return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString(undefined, { hour12: false });
    },
    short: (s, n = 42) => {
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

  function wsURL() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${location.host}/ws`;
  }

  let lastWs = null;

  function wsState() {
    if (!lastWs) return "closed";
    const s = lastWs.readyState;
    if (s === 0) return "connecting";
    if (s === 1) return "open";
    if (s === 2) return "closing";
    return "closed";
  }

  function connectWS(onMessage) {
    let ws = null;
    let retry = 0;
    let timer = null;
    function open() {
      clearTimeout(timer);
      try { if (ws) ws.close(); } catch (e) { /* noop */ }
      ws = new WebSocket(wsURL());
      lastWs = ws;
      dbg("ws", { phase: "connecting", url: wsURL() });
      ws.onopen = () => {
        retry = 0;
        dbg("ws", { phase: "open" });
        onMessage({ type: "status", connected: true });
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          const n = msg && msg.runs ? msg.runs.length : undefined;
          dbg("ws", { phase: "message", type: msg && msg.type, runs: n, stale: !!(msg && msg.stale) });
          onMessage(msg);
        } catch (e) {
          dbg("ws-error", { phase: "bad-json", message: e && e.message ? e.message : String(e) });
        }
      };
      ws.onclose = (ev) => {
        dbg("ws-error", { phase: "close", code: ev.code, reason: ev.reason || "", wasClean: ev.wasClean });
        onMessage({ type: "status", connected: false });
        const delay = Math.min(30000, 1000 * 2 ** retry++);
        timer = setTimeout(open, delay);
      };
      ws.onerror = () => {
        dbg("ws-error", { phase: "error", readyState: ws && ws.readyState });
        try { ws.close(); } catch (e) { /* noop */ }
      };
    }
    open();
    return {
      close: () => { clearTimeout(timer); try { ws && ws.close(); } catch (e) { /* noop */ } },
      state: wsState,
    };
  }

  return { api, fmt, esc, connectWS, wsState };
})();
