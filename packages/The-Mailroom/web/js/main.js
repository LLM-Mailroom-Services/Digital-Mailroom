/* The-Mailroom app shell: boot, tabs, source light, live snapshot wiring
 * (WebSocket with polling fallback), closed-state handling. */

const Main = (() => {
  const lightEl = document.getElementById("source-light");
  const sourceLabelEl = document.getElementById("source-label");
  const clockEl = document.getElementById("clock");
  const statusLeftEl = document.getElementById("status-left");
  const statusRightEl = document.getElementById("status-right");
  const hintEl = document.getElementById("floor-hint");
  const closedEl = document.getElementById("closed");
  const tabEls = Array.from(document.querySelectorAll(".tab"));

  let langfuseOk = false;
  let wsOk = false;
  let lastSnapshot = [];
  let lastIds = new Set();
  let byId = new Map();
  let lastPipeline = { configured: false };
  let lastFetchedAt = null;
  let pollIntervalMs = 3000;
  let pollTimer = null;
  let fallbackTimer = null;
  let activeTab = "floor";
  let demoMode = false;
  let demoTimer = null;
  let demoRuns = [];

  function p2(n) { return String(n).padStart(2, "0"); }

  function tick() {
    const d = new Date();
    clockEl.textContent = `${p2(d.getHours())}:${p2(d.getMinutes())}:${p2(d.getSeconds())}`;
  }

  function setLamp(state) {
    lightEl.className = `light light-${state}`;
    floorSetSource(state);
  }

  function floorSetSource(state) {
    if (langfuseOk && wsOk) Floor.setSource("green");
    else if (!langfuseOk) Floor.setSource("red");
    else Floor.setSource("gold");
  }

  function applySource() {
    if (Mailroom.staticMode) {
      setLamp("gold");
      sourceLabelEl.textContent = "SOURCE: SNAPSHOT";
      sourceLabelEl.className = "st-warn mono";
      statusLeftEl.textContent = "MAILROOM SNAPSHOT — BUNDLED DATA (NO LIVE API)";
      statusLeftEl.className = "st-warn mono";
      closedEl.hidden = true;
      Floor.setSource("gold");
      stopDemo();
      return;
    }
    if (!langfuseOk && !demoMode) {
      setLamp("red");
      sourceLabelEl.textContent = "SOURCE: OFFLINE";
      sourceLabelEl.className = "st-bad mono";
      statusLeftEl.textContent = "MAILROOM CLOSED — NO LANGFUSE CONNECTION";
      statusLeftEl.className = "st-bad mono";
      closedEl.hidden = false;
      Floor.reset();
      Floor.setSource("red");
    } else if (demoMode && !langfuseOk) {
      setLamp("gold");
      sourceLabelEl.textContent = "SOURCE: DEMO MODE";
      sourceLabelEl.className = "st-warn mono";
      statusLeftEl.textContent = "MAILROOM DEMO — SIMULATED PIPELINE RUNNING";
      statusLeftEl.className = "st-warn mono";
      closedEl.hidden = true;
      Floor.setSource("gold");
      startDemo();
    } else if (demoMode && langfuseOk) {
      setLamp("gold");
      sourceLabelEl.textContent = "SOURCE: DEMO MODE (LANGFUSE UP)";
      sourceLabelEl.className = "st-warn mono";
      statusLeftEl.textContent = "MAILROOM DEMO — SIMULATED PIPELINE (LANGFUSE AVAILABLE)";
      statusLeftEl.className = "st-warn mono";
      closedEl.hidden = true;
      Floor.setSource("gold");
      startDemo();
    } else {
      setLamp(wsOk ? "green" : "gold");
      sourceLabelEl.textContent = "SOURCE: LANGFUSE";
      sourceLabelEl.className = wsOk ? "st-good mono" : "st-warn mono";
      statusLeftEl.textContent = "MAILROOM LIVE — WATCHING LANGFUSE";
      statusLeftEl.className = "st-good mono";
      closedEl.hidden = true;
      Floor.setSource(wsOk ? "green" : "gold");
      stopDemo();
    }
  }

  function pipelineStrip(ops) {
    if (!ops || !ops.configured) return "";
    const w = ops.watcher === "live" ? "WATCHER LIVE"
      : ops.watcher === "stale" ? "WATCHER STALE"
      : ops.watcher === "missing" ? "WATCHER DOWN"
      : "WATCHER ?";
    const inbox = ops.inbox_pending == null ? "?" : String(ops.inbox_pending);
    const paused = ops.ingestion_paused ? " · PAUSED" : "";
    return ` · ${w} · INBOX ${inbox}${paused}`;
  }

  function startDemo() {
    if (demoTimer) return;
    demoRuns = generateDemoRuns();
    window.Mailroom = window.Mailroom || {};
    window.Mailroom.demoRuns = demoRuns;
    window.Mailroom.demoMode = true;
    Floor.update(demoRuns);
    let idx = 0;
    demoTimer = setInterval(() => {
      if (!demoMode) return stopDemo();
      const run = demoRuns[idx % demoRuns.length];
      run.updated_at = new Date().toISOString();
      ConsoleView.log(`DEMO ${run.filename} → ${run.stage}${run.verdict ? ` · ${run.verdict}` : ""}`, "c-blue");
      idx++;
    }, 3000);
    ConsoleView.banner("DEMO MODE ACTIVE — SIMULATED PIPELINE");
  }

  function stopDemo() {
    if (demoTimer) {
      clearInterval(demoTimer);
      demoTimer = null;
    }
    // V-10: the demo flag leaked into live mode — window.Mailroom.demoMode was
    // set in startDemo() but never reset, so metrics.js kept rendering
    // fabricated demo numbers after Langfuse came up. Single source of truth:
    // clear the global flag and drop demo runs whenever demo mode ends.
    if (window.Mailroom) {
      window.Mailroom.demoMode = false;
      delete window.Mailroom.demoRuns;
    }
    if (!langfuseOk) Floor.reset();
  }

  function generateDemoRuns() {
    const stages = [
      { stage: "archived", phase: "terminal", doc_type: "contract", filename: "contract_service_agreement_03.pdf", verdict: "CORRECT", quality: 0.96, classification_confidence: 0.98, extraction_confidence: 0.94 },
      { stage: "archived", phase: "terminal", doc_type: "merger_agreement", filename: "maud_merger_agreement_all_stock_42.pdf", verdict: "CORRECT", quality: 0.93, classification_confidence: 0.97, extraction_confidence: 0.91 },
      { stage: "archived", phase: "terminal", doc_type: "corporate_record", filename: "corporate_bylaws_amendment_04.pdf", verdict: "CORRECT", quality: 0.95, classification_confidence: 0.99, extraction_confidence: 0.97 },
      { stage: "archived", phase: "terminal", doc_type: "contract", filename: "contract_master_services_agreement_05.pdf", verdict: "PARTIAL", quality: 0.72, classification_confidence: 0.93, extraction_confidence: 0.68 },
      { stage: "archived", phase: "terminal", doc_type: "correspondence", filename: "correspondence_demand_letter_09.pdf", verdict: "CORRECT", quality: 0.88, classification_confidence: 0.95, extraction_confidence: 0.84 },
      { stage: "archived", phase: "terminal", doc_type: "insurance_claim", filename: "insurance_claim_fnol_package_01.pdf", verdict: "CORRECT", quality: 0.94, classification_confidence: 0.97, extraction_confidence: 0.95 },
      { stage: "judge_verify", phase: "extraction", doc_type: "insurance_claim", filename: "insurance_claim_coverage_determination_07.pdf", classification_confidence: 0.96, extraction_confidence: 0.78 },
      { stage: "arbiter", phase: "extraction", doc_type: "merger_agreement", filename: "maud_merger_agreement_mixed_cash_stock_117.pdf", verdict: "PARTIAL", quality: 0.66, classification_confidence: 0.97, extraction_confidence: 0.74 },
      { stage: "review", phase: "review", doc_type: "correspondence", filename: "correspondence_internal_memo_04.pdf", review_decision: "human review", escalation_reason: "low extraction confidence on meeting request" },
      { stage: "failed", phase: "terminal", doc_type: "corporate_record", filename: "corporate_articles_of_incorporation_02.pdf", error_message: "extraction failed: LLM output not valid JSON" },
      { stage: "classify", phase: "intake_sort", doc_type: "contract", filename: "contract_consulting_agreement_06.pdf", classification_confidence: 0.91 },
      { stage: "extract", phase: "extraction", doc_type: "corporate_record", filename: "corporate_rights_instrument_08.pdf", extraction_confidence: 0.82 },
      { stage: "report", phase: "reporting", doc_type: "insurance_claim", filename: "insurance_claim_fnol_package_11.pdf" },
    ];
    return stages.map((s, i) => ({
      trace_id: `demo-run-${i}`,
      filename: s.filename,
      matter_id: "DEMO-MATTER",
      session_id: "DEMO-MATTER",
      environment: "demo",
      tags: ["mailroom", "demo", "demo-mode"],
      attempt: 1,
      stage: s.stage,
      phase: s.phase,
      doc_type: s.doc_type,
      classification_confidence: s.classification_confidence,
      extraction_confidence: s.extraction_confidence,
      review_decision: s.review_decision,
      escalation_reason: s.escalation_reason,
      error_message: s.error_message,
      verdict: s.verdict,
      quality: s.quality,
      latency: 8 + Math.random() * 15,
      llm_call_count: 2 + Math.floor(Math.random() * 4),
      total_tokens: 3000 + Math.floor(Math.random() * 4000),
      cost_usd: 0.001 + Math.random() * 0.003,
      retried: Math.random() > 0.7,
      needs_human: s.stage === "review",
      created_at: new Date(Date.now() - i * 60000).toISOString(),
      updated_at: new Date().toISOString(),
      routing_path: [],
    }));
  }

  function applySnapshot(runs, stale = false) {
    // V-27: a non-empty FRESH snapshot proves the backend is serving even when
    // the async health check hasn't resolved yet. A stale one (source down,
    // last-good floor) must not flip the lamp back on — that made the screen
    // alternate OPEN/CLOSED every health tick.
    if (runs && runs.length && !stale && !langfuseOk) {
      langfuseOk = true;
      applySource();
    }
    if (!langfuseOk && !demoMode) return;
    lastSnapshot = runs;
    const ids = new Set(runs.map((r) => r.trace_id));
    const added = [...ids].filter((id) => !lastIds.has(id));
    const removed = [...lastIds].filter((id) => !ids.has(id));
    const changed = runs.filter((r) => {
      const prev = byId.get(r.trace_id);
      return prev && (prev.stage !== r.stage || prev.verdict !== r.verdict);
    });
    lastIds = ids;
    byId = new Map(runs.map((r) => [r.trace_id, r]));

    if (added.length) {
      for (const r of runs.filter((x) => added.includes(x.trace_id)).slice(0, 5)) {
        ConsoleView.log(`NEW ${r.filename || r.trace_id} → ${r.stage}`, "c-ok");
      }
      if (added.length > 5) ConsoleView.log(`… ${added.length - 5} more new runs`, "c-dim");
    }
    for (const r of changed.slice(0, 5)) {
      ConsoleView.log(`${r.filename || r.trace_id} → ${r.stage}${r.verdict ? ` · ${r.verdict}` : ""}`, "c-blue");
    }
    if (removed.length) ConsoleView.log(`${removed.length} run(s) left the window`, "c-dim");

    Floor.update(runs);
    renderStatus();
  }

  function applyPipeline(ops) {
    if (!ops) return;
    const prev = lastPipeline || {};
    lastPipeline = ops;
    if (ops.configured && prev.watcher && prev.watcher !== ops.watcher) {
      ConsoleView.log(`watcher ${prev.watcher} → ${ops.watcher}`, ops.watcher === "live" ? "c-ok" : "c-warn");
    }
    const prevInbox = prev.inbox_pending;
    if (ops.configured && typeof ops.inbox_pending === "number"
        && ops.inbox_pending !== prevInbox) {
      if (ops.inbox_pending > 0) {
        ConsoleView.log(`inbox pending: ${ops.inbox_pending}`, "c-dim");
      } else if (typeof prevInbox === "number" && prevInbox > 0) {
        ConsoleView.log("inbox empty", "c-dim");
      }
    }
    renderStatus();
  }

  function renderStatus() {
    const envs = new Set();
    for (const r of lastSnapshot) {
      const env = Mailroom.envFromTags(r.tags);
      if (env) envs.add(env);
    }
    const envTxt = envs.size ? ` · ENV: ${[...envs].sort().join(",")}` : "";
    const pipe = pipelineStrip(lastPipeline);
    let updated = "";
    if (lastFetchedAt) {
      const t = new Date(lastFetchedAt);
      if (!Number.isNaN(t.getTime())) updated = ` · UPDATED ${t.toLocaleTimeString()}`;
    }
    statusRightEl.textContent = `RUNS: ${lastSnapshot.length}${envTxt}${pipe}${updated}`;
  }

  async function loadMeta() {
    try {
      Mailroom.meta = await Mailroom.api.meta();
      const poll = Mailroom.meta && Mailroom.meta.poll_interval_s;
      if (typeof poll === "number" && poll > 0) {
        pollIntervalMs = Math.max(1000, Math.round(poll * 1000));
        if (fallbackTimer) startFallbackPolling();
      }
    } catch (e) {
      Mailroom.showError(`meta: ${e.message || e}`);
    }
  }

  async function loadSnapshotFloor() {
    try {
      await loadMeta();
      applySnapshot((await Mailroom.api.traces(604800, 200)).runs || []);
    } catch (e2) {
      Mailroom.showError(`snapshot load: ${e2.message || e2}`);
    }
  }

  let liveSeen = false;
  let liveStarted = false;

  // Start WS + polling fallback the first time health is ok — including
  // when the FIRST probe failed (the page used to stay blank until reload).
  function startLive() {
    if (liveStarted || Mailroom.staticMode) return;
    liveStarted = true;
    setTimeout(() => {
      if (!wsOk && !Mailroom.staticMode) startFallbackPolling();
    }, 8000);
    Mailroom.connectWS(onMessage);
  }

  async function checkHealth() {
    if (Mailroom.staticMode) { applySource(); return true; }
    try {
      const h = await Mailroom.api.health();
      liveSeen = true;
      // Source-agnostic "ok" (multi/phoenix sources) with langfuse fallback.
      langfuseOk = !!(h.ok ?? h.langfuse);
      if (langfuseOk && !Mailroom.meta) await loadMeta();
    } catch (err) {
      // GH Pages / no live API: fall back to bundled snapshots. A missing
      // /api/health is expected here — do NOT paint it as an error banner
      // or red console line; that was the Pages boot flash. Once a live API
      // has answered, a transient failure is an outage (MAILROOM CLOSED),
      // never a permanent switch to static mode.
      const enabled = !liveSeen && await Mailroom.enableStaticMode();
      if (enabled) {
        langfuseOk = true;
        ConsoleView.log(`no live API (${err.message || err}) — serving bundled snapshot`, "c-dim");
        ConsoleView.banner("SNAPSHOT MODE — SERVING BUNDLED DATA");
        await loadSnapshotFloor();
        applySource();
        return true;
      }
      ConsoleView.log(`health check failed: ${err.message || err}`, "c-bad");
      langfuseOk = false;
    }
    applySource();
    return langfuseOk;
  }

  function onMessage(msg) {
    if (msg.type === "status") {
      if (msg.connected) {
        wsOk = true;
        ConsoleView.banner("MAILROOM ONLINE — WATCHING LANGFUSE");
      } else {
        wsOk = false;
        ConsoleView.log("connection lost — reconnecting…", "c-warn");
      }
      applySource();
    } else if (msg.type === "snapshot") {
      applySnapshot(msg.runs || [], !!msg.stale);
      if (msg.pipeline) applyPipeline(msg.pipeline);
      if (msg.fetched_at) lastFetchedAt = msg.fetched_at;
      if (typeof msg.poll_interval_s === "number" && msg.poll_interval_s > 0) {
        pollIntervalMs = Math.max(1000, Math.round(msg.poll_interval_s * 1000));
        if (fallbackTimer) startFallbackPolling();
      }
      // V-14: surface staleness + last-updated so a frozen floor with a green
      // lamp is distinguishable from a live one.
      if (msg.stale) {
        sourceLabelEl.textContent = "SOURCE: LANGFUSE (STALE)";
        sourceLabelEl.className = "st-warn mono";
      }
      renderStatus();
    }
  }

  let fallbackPollMs = 0;

  function startFallbackPolling() {
    const tick = async () => {
      if (!langfuseOk || wsOk) return;
      try {
        const data = await Mailroom.api.traces(604800, 200);
        applySnapshot(data.runs || [], data.source === "langfuse-cache");
        try {
          applyPipeline(await Mailroom.api.pipeline());
        } catch (_e) { /* pipeline URL optional */ }
      } catch (err) {
        const msg = err.message || String(err);
        ConsoleView.log(`poll fallback failed: ${msg}`, "c-warn");
        Mailroom.showError(`fallback poll: ${msg}`);
      }
    };
    if (fallbackTimer && fallbackPollMs === pollIntervalMs) return;
    if (fallbackTimer) clearInterval(fallbackTimer);
    fallbackPollMs = pollIntervalMs;
    fallbackTimer = setInterval(tick, pollIntervalMs);
    ConsoleView.log(`polling /api/traces as fallback (${pollIntervalMs}ms)`, "c-dim");
  }

  function switchView(name) {
    activeTab = name;
    for (const t of tabEls) t.classList.toggle("active", t.dataset.view === name);
    for (const v of document.querySelectorAll(".view")) v.hidden = v.id !== `view-${name}`;
    // V-18: these refreshes were silently swallowed — failures now surface on
    // the error banner AND the console.
    if (name === "review") {
      ReviewView.refresh()
        .then(() => ConsoleView.log("review queue refreshed", "c-dim"))
        .catch((e) => { Mailroom.showError(`review: ${e.message || e}`); ConsoleView.log(`review refresh failed: ${e.message || e}`, "c-bad"); });
    } else if (name === "sessions") {
      SessionsView.refresh()
        .then(() => ConsoleView.log("sessions refreshed", "c-dim"))
        .catch((e) => { Mailroom.showError(`sessions: ${e.message || e}`); ConsoleView.log(`sessions refresh failed: ${e.message || e}`, "c-bad"); });
    } else if (name === "history") {
      HistoryView.refresh()
        .then(() => ConsoleView.log("history refreshed", "c-dim"))
        .catch((e) => { Mailroom.showError(`history: ${e.message || e}`); ConsoleView.log(`history refresh failed: ${e.message || e}`, "c-bad"); });
    } else if (name === "metrics") {
      MetricsView.refresh()
        .then(() => ConsoleView.log("metrics refreshed", "c-dim"))
        .catch((e) => { Mailroom.showError(`metrics: ${e.message || e}`); ConsoleView.log(`metrics refresh failed: ${e.message || e}`, "c-bad"); });
    }
  }

  function boot() {
    tick();
    setInterval(tick, 1000);

    ConsoleView.banner("THE MAILROOM — LLM-MAILROOM VISUAL ENGINE");

    // Deep-linkable tab state: ?view=review|sessions|history|metrics|console
    const requestedView = new URLSearchParams(location.search).get("view");

    Floor.onSelect((traceId, run) => {
      ConsoleView.log(`INSPECT ${run && run.filename ? run.filename : traceId}`, "c-blue");
      Inspector.open(traceId);
    });
    Floor.onHover((run) => {
      if (!run) {
        hintEl.textContent = "click an envelope to inspect its run";
        return;
      }
      const bits = [run.filename || run.trace_id, run.stage];
      if (run.doc_type) bits.push(run.doc_type);
      if (run.verdict) bits.push(run.verdict);
      hintEl.textContent = bits.join(" · ");
    });

    for (const t of tabEls) {
      t.addEventListener("click", () => switchView(t.dataset.view));
    }
    setInterval(() => {
      if (activeTab === "review") {
        ReviewView.refresh({ background: true }).catch((e) => Mailroom.showError(`review: ${e.message || e}`));
      }
      if (activeTab === "sessions") {
        SessionsView.refresh().catch((e) => Mailroom.showError(`sessions: ${e.message || e}`));
      }
      if (activeTab === "history") {
        HistoryView.refresh().catch((e) => Mailroom.showError(`history: ${e.message || e}`));
      }
      if (activeTab === "metrics") {
        MetricsView.refresh().catch((e) => Mailroom.showError(`metrics: ${e.message || e}`));
      }
    }, 30000);

    document.getElementById("closed-retry").addEventListener("click", () => {
      ConsoleView.log("retrying connection…", "c-dim");
      checkHealth().then((ok) => { if (ok) startLive(); });
    });

    // Demo envelopes are opt-in via ?demo=1 and only when Langfuse is down.
    // The D key used to fabricate a live floor (and collided with Debug).
    const demoRequested = new URLSearchParams(location.search).get("demo") === "1";
    document.addEventListener("keydown", (ev) => {
      if (ev.target && ["INPUT", "TEXTAREA", "SELECT"].includes(ev.target.tagName)) return;
      if (demoRequested && (ev.key === "d" || ev.key === "D") && !langfuseOk) {
        demoMode = !demoMode;
        ConsoleView.log(`DEMO MODE ${demoMode ? "ON" : "OFF"}`, demoMode ? "c-ok" : "c-warn");
        applySource();
      }
    });

    // WS starts only once a health probe succeeds: in snapshot mode there is
    // no /ws endpoint to hold open (GH Pages), so don't spin a reconnect loop
    // against static hosting.
    const probe = () => checkHealth().then((ok) => { if (ok) startLive(); });
    setInterval(probe, 5000);
    probe();

    if (requestedView && tabEls.some((t) => t.dataset.view === requestedView)) {
      switchView(requestedView);
    }
  }

  document.addEventListener("DOMContentLoaded", boot);
  return {};
})();
