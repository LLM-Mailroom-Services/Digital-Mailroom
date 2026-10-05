/* Observatory debug suite — ring buffer + hooks for agents and humans.

  Browser:
    window.__OBSERVATORY_DEBUG__.dump()
    window.__OBSERVATORY_DEBUG__.export()   // dump + GET /api/debug/bundle + POST /api/debug/client
    window.__OBSERVATORY_DEBUG__.pullServer()
    window.__OBSERVATORY_DEBUG__.pushClient()
    window.__OBSERVATORY_DEBUG__.clear()
    window.__OBSERVATORY_DEBUG__.setVerbose(true)
    window.__OBSERVATORY_DEBUG__.explain(event)  // human-readable one event

  Server (curl from anywhere CORS allows):
    GET  /api/debug/bundle   one pull: health + source + server logs + last client reports
    GET  /api/debug/logs
    GET  /api/debug/source
    POST /api/debug/client   store a browser dump so the next agent can read it

  Open the Debug view (#debug) or append ?debug=1
*/
const ObservatoryDebug = (() => {
  const MAX = 400;
  const events = [];
  let verbose = false;
  let lastHealth = null;
  let lastMeta = null;
  let lastWs = null;
  let lastError = null;
  let lastBundle = null;
  let lastPush = null;
  let fetchWrapped = false;

  const KINDS = {
    boot: "App started and bound listeners.",
    view: "Observer switched desk (pipeline / review / history / matters / metrics / debug).",
    health: "GET /api/health result. ok=false means Langfuse/Phoenix is unreachable.",
    meta: "GET /api/meta (schema, edition, UI paths). Failure is non-fatal for the board.",
    traces: "Floor snapshot loaded (list of light runs).",
    "traces-error": "Floor list failed. The board stays empty rather than inventing envelopes.",
    "detail-error": "GET /api/traces/{id} failed. Inspector cannot show spans/scores.",
    "review-error": "GET /api/review-queue failed. Review desk shows the error string.",
    "history-error": "History list failed (same traces endpoint as the floor).",
    "matters-error": "GET /api/sessions failed.",
    "metrics-error": "GET /api/metrics failed.",
    fetch: "Any HTTP request the page made (status + duration).",
    "fetch-error": "A fetch threw (network down, CORS, aborted) or returned HTTP status >= 400.",
    ws: "WebSocket lifecycle or a parsed snapshot.",
    "ws-error": "WebSocket onerror / bad JSON / unexpected close.",
    replay: "Replay overlay applied a stage to one run.",
    "window-error": "window.onerror — a thrown exception the UI did not catch.",
    unhandledrejection: "Unhandled promise rejection (async throw with no .catch).",
    "server-bundle": "This browser pulled GET /api/debug/bundle.",
    "client-push": "This browser POSTed its dump to /api/debug/client.",
    visual: "A layout or render guard fired (missing node, unexpected payload shape).",
    announce: "Screen-reader live region was updated.",
  };

  function now() {
    return new Date().toISOString();
  }

  function record(kind, payload) {
    const ev = Object.assign({ t: now(), kind }, payload || {});
    events.push(ev);
    if (events.length > MAX) events.splice(0, events.length - MAX);
    if (kind === "health") lastHealth = ev;
    if (kind === "meta") lastMeta = ev;
    if (kind === "ws" || kind === "ws-error") lastWs = ev;
    if (kind === "window-error" || kind === "unhandledrejection" || (kind && String(kind).endsWith("-error"))) {
      lastError = ev;
    }
    if (verbose) {
      const fn = String(kind).includes("error") ? "error" : "info";
      console[fn]("[observatory]", kind, payload || {});
    }
    try {
      window.dispatchEvent(new CustomEvent("obs-debug", { detail: ev }));
    } catch (_e) { /* CustomEvent missing in ancient browsers — ignore */ }
    return ev;
  }

  function explain(ev) {
    if (!ev) return "";
    const gloss = KINDS[ev.kind] || "Unclassified event. Inspect the raw fields.";
    const bits = [ev.t || "", ev.kind || "", gloss];
    if (ev.message) bits.push("message: " + ev.message);
    if (ev.status != null) bits.push("status: " + ev.status);
    if (ev.url) bits.push("url: " + ev.url);
    if (ev.where) bits.push("where: " + ev.where);
    return bits.join(" — ");
  }

  function dump() {
    return {
      generated_at: now(),
      href: location.href,
      hash: location.hash,
      userAgent: navigator.userAgent,
      viewport: {
        w: window.innerWidth,
        h: window.innerHeight,
        dpr: window.devicePixelRatio || 1,
      },
      reducedMotion: !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches),
      colorScheme: window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light",
      visibility: document.visibilityState,
      lastHealth,
      lastMeta,
      lastWs,
      lastError,
      lastBundleAt: lastBundle && lastBundle.generated_at,
      lastPush,
      eventCount: events.length,
      events: events.slice(),
      glossary: KINDS,
    };
  }

  function wrapFetch() {
    if (fetchWrapped || typeof window.fetch !== "function") return;
    fetchWrapped = true;
    const native = window.fetch.bind(window);
    window.fetch = async function (input, init) {
      const url = typeof input === "string" ? input : (input && input.url) || "";
      const method = (init && init.method) || (typeof input !== "string" && input && input.method) || "GET";
      const t0 = (typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now();
      try {
        const res = await native(input, init);
        const ms = Math.round(((typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now()) - t0);
        record("fetch", { url: String(url).slice(0, 240), method, status: res.status, ms });
        if (res.status >= 400) {
          record("fetch-error", {
            url: String(url).slice(0, 240),
            method,
            status: res.status,
            message: "HTTP " + res.status,
            ms,
          });
        }
        return res;
      } catch (err) {
        const ms = Math.round(((typeof performance !== "undefined" && performance.now) ? performance.now() : Date.now()) - t0);
        record("fetch-error", {
          url: String(url).slice(0, 240),
          method,
          message: err && err.message ? err.message : String(err),
          ms,
        });
        throw err;
      }
    };
  }

  async function pullServer() {
    const r = await fetch("/api/debug/bundle", { headers: { accept: "application/json" } });
    const body = await r.json();
    lastBundle = body;
    record("server-bundle", {
      status: r.status,
      serverEvents: ((body && body.server_logs) || []).length,
      clientReports: ((body && body.client_reports) || []).length,
    });
    return body;
  }

  async function pushClient() {
    const body = dump();
    const r = await fetch("/api/debug/client", {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify(body),
    });
    let parsed = null;
    try { parsed = await r.json(); } catch (_e) { parsed = { ok: false, parse: "non-json" }; }
    lastPush = { t: now(), status: r.status, body: parsed };
    record("client-push", lastPush);
    return parsed;
  }

  async function exportAll() {
    const client = dump();
    let server = null;
    let push = null;
    try { server = await pullServer(); } catch (e) {
      record("error", { where: "export.pullServer", message: e && e.message ? e.message : String(e) });
    }
    try { push = await pushClient(); } catch (e) {
      record("error", { where: "export.pushClient", message: e && e.message ? e.message : String(e) });
    }
    return { client: dump(), server, push };
  }

  function install() {
    wrapFetch();
    window.addEventListener("error", (e) => {
      lastError = {
        type: "error",
        message: e.message,
        file: e.filename,
        line: e.lineno,
        col: e.colno,
      };
      record("window-error", lastError);
    });
    window.addEventListener("unhandledrejection", (e) => {
      lastError = {
        type: "unhandledrejection",
        message: e.reason && e.reason.message ? e.reason.message : String(e.reason),
      };
      record("unhandledrejection", lastError);
    });
    window.__OBSERVATORY_DEBUG__ = {
      dump,
      export: exportAll,
      pullServer,
      pushClient,
      clear() {
        events.length = 0;
        lastError = null;
        record("cleared", {});
      },
      setVerbose(v) { verbose = !!v; record("verbose", { on: verbose }); },
      events: () => events.slice(),
      explain,
      glossary: KINDS,
    };
    record("boot", { href: location.href });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install, { once: true });
  } else {
    install();
  }

  return { record, dump, exportAll, pullServer, pushClient, explain, install };
})();

// A top-level `const` is not a window property: app.js / client.js guard on
// window.ObservatoryDebug, so without this every dbg() call was a no-op.
window.ObservatoryDebug = ObservatoryDebug;
