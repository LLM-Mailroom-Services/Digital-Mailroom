/* The-Mailroom floor: canvas conveyor renderer.
 * Clean, bright pixel envelopes flowing through stations.
 * Archived items leave the floor entirely. */

const Floor = (() => {
  const canvas = document.getElementById("floor");
  const ctx = canvas.getContext("2d");
  const W = 1440;
  const H = 480;

  // 7 stations: sorter → extract → JUDGE (judge_verify/arbiter) → boss →
  // report → archive, plus the review siding. Evenly distributed across the
  // 1440px canvas; desks extend x-20..x+100, labels sit at x+40.
  const STATIONS = [
    { key: "sorter", x: 80, label: "SORTER", color: "#7d97b5" },
    { key: "extract", x: 285, label: "EXTRACT", color: "#d9a866" },
    { key: "judge", x: 490, label: "JUDGE", color: "#9b7fb8" },
    { key: "boss", x: 695, label: "BOSS", color: "#95272e" },
    { key: "report", x: 900, label: "REPORT", color: "#659099" },
    { key: "archive", x: 1105, label: "ARCHIVE", color: "#5f9e6e" },
    { key: "review", x: 1310, label: "REVIEW", color: "#f7d156" },
  ];

  const ENV_Y = 240;       // y position for envelopes on conveyor
  const ENV_W = 32;        // envelope width in pixels
  const ENV_H = 22;        // envelope height in pixels

  const envs = new Map();
  // V-9: tombstones — archived/failed runs stay in the 6 h WS payload, and
  // without a tombstone the next 3 s snapshot re-creates the envelope right
  // after it slid off, causing a perpetual pop-in/slide-off loop. Keyed by
  // trace_id -> last updated_at seen; a genuinely NEW run on the same
  // deterministic trace id (pilot re-run) clears the tombstone.
  const gone = new Map();
  const MAX_TOMBSTONES = 2000;
  let hoveredId = null;
  let sourceState = "gold";

    function targetFor(run) {
    const st = run.stage;
    // Failed items leave the floor. Archived items leave unless objective
    // misses pulled them back onto the REVIEW siding (reconsideration).
    if (st === "failed") {
      return { x: 1500, y: 440, remove: true };
    }
    if (st === "review" || run.needs_human) {
      return { x: STATIONS[6].x, y: ENV_Y };
    }
    if (st === "archived") {
      return { x: 1500, y: 440, remove: true };
    }
    if (st === "inbox") {
      return { x: 24, y: ENV_Y };
    }
    if (st === "classify" || st === "retry_classify" || st === "review_classify"
        || st === "intake" || st === "unknown") {
      return { x: STATIONS[0].x, y: ENV_Y };
    }
    if (st === "extract" || st === "retry_extract") {
      return { x: STATIONS[1].x, y: ENV_Y };
    }
    // KANBAN-063 quality gate: judge_verify + arbiter share the JUDGE station
    if (st === "judge_verify" || st === "arbiter") {
      return { x: STATIONS[2].x, y: ENV_Y };
    }
    if (st === "boss") {
      return { x: STATIONS[3].x, y: ENV_Y };
    }
    if (st === "report") {
      return { x: STATIONS[4].x, y: ENV_Y };
    }
    if (st === "catalog" || st === "archive") {
      return { x: STATIONS[5].x, y: ENV_Y };
    }
    return { x: STATIONS[0].x, y: ENV_Y };
  }

  function tintFor(run) {
    const colors = {
      contract: "#7d97b5",
      merger_agreement: "#8aa3c0",
      corporate_record: "#659099",
      correspondence: "#e8b478",
      insurance_claim: "#b18ec2",
      court_opinion: "#c47a7a",
      due_diligence: "#9aa87a",
      compliance_filing: "#7a8fb0",
    };
    return colors[run.doc_type] || "#a09f9f";
  }

  function drawEnvelope(x, y, tint) {
    // Border (black)
    ctx.fillStyle = "#000000";
    ctx.fillRect(x, y, ENV_W, ENV_H);
    // Paper body (cream)
    ctx.fillStyle = "#faf3e6";
    ctx.fillRect(x + 1, y + 1, ENV_W - 2, ENV_H - 2);
    // Color stripe at top-left
    ctx.fillStyle = tint;
    ctx.fillRect(x + 2, y + 2, 6, 6);
    // Fold lines
    ctx.fillStyle = "#e8dcc3";
    ctx.fillRect(x + 2, y + ENV_H / 2 - 1, ENV_W - 4, 2);
    ctx.fillRect(x + 2, y + ENV_H / 2 + 3, ENV_W - 4, 2);
    // Re-draw border
    ctx.fillStyle = "#000000";
    ctx.fillRect(x, y, ENV_W, 1);
    ctx.fillRect(x, y + ENV_H - 1, ENV_W, 1);
    ctx.fillRect(x, y, 1, ENV_H);
    ctx.fillRect(x + ENV_W - 1, y, 1, ENV_H);
  }

  function drawInboxHopper() {
    // Files that have a Langfuse trace at stage=inbox sit in this hopper
    // before the SORTER desk (uploads without a trace show on the ops strip).
    ctx.fillStyle = "#3a2f22";
    ctx.fillRect(4, ENV_Y + ENV_H + 4, 56, 4);
    ctx.fillStyle = "#a48c6d";
    ctx.fillRect(4, ENV_Y + ENV_H + 4, 56, 1);
    ctx.fillStyle = "#7d97b5";
    ctx.fillRect(8, ENV_Y - 20, 48, 4);
    ctx.font = "bold 10px 'Courier New', monospace";
    ctx.fillStyle = "#7d97b5";
    ctx.textAlign = "center";
    ctx.fillText("INBOX", 32, ENV_Y - 26);
  }

  function drawStation(s) {
    // Station desk/marker
    ctx.fillStyle = "#3a2f22";
    ctx.fillRect(s.x - 20, ENV_Y + ENV_H + 4, 120, 4);
    ctx.fillStyle = "#a48c6d";
    ctx.fillRect(s.x - 20, ENV_Y + ENV_H + 4, 120, 1);
    // Station color bar above
    ctx.fillStyle = s.color;
    ctx.fillRect(s.x - 10, ENV_Y - 20, 100, 4);
    // Label
    ctx.font = "bold 10px 'Courier New', monospace";
    ctx.fillStyle = s.color;
    ctx.textAlign = "center";
    ctx.fillText(s.label, s.x + 40, ENV_Y - 26);
  }

  function drawConveyor() {
    // Conveyor belt
    ctx.fillStyle = "#2a2a2e";
    ctx.fillRect(0, ENV_Y + ENV_H + 10, W, 24);
    ctx.fillStyle = "#3a3a3e";
    ctx.fillRect(0, ENV_Y + ENV_H + 10, W, 2);
    // Belt segments
    ctx.fillStyle = "#1a1a1d";
    for (let x = 0; x < W; x += 32) {
      ctx.fillRect(x, ENV_Y + ENV_H + 10, 1, 24);
    }
  }

  function drawBackground() {
    ctx.fillStyle = "#141416";
    ctx.fillRect(0, 0, W, H);
    // Room labels (phase bands over the stations beneath them)
    ctx.font = "bold 9px 'Courier New', monospace";
    ctx.fillStyle = "#7d97b5";
    ctx.textAlign = "center";
    ctx.fillText("INTAKE & SORT", 160, 30);
    ctx.fillText("EXTRACTION & ADJUDICATION", 600, 30);
    ctx.fillText("REPORTING & ARCHIVE", 1072, 30);
    ctx.fillText("REVIEW SIDING", 1350, 30);
  }

  function update(runs) {
    // A live snapshot must not yank a replay in progress (it reset the
    // replayed envelope's target and resurrected every envelope the replay
    // had cleared). Hold the latest snapshot and apply it afterwards.
    if (replayState && Date.now() < replayState.until) {
      pendingRuns = runs;
      return;
    }
    const seen = new Set();
    for (const run of runs) {
      if (!run || !run.trace_id) continue;
      seen.add(run.trace_id);
      const t = targetFor(run);
      // V-9: tombstoned archived/failed runs must NOT respawn. Clear the
      // tombstone only when the same trace id carries a NEW run (updated_at
      // changed — deterministic trace ids are reused by re-runs).
      const tomb = gone.get(run.trace_id);
      if (t.remove && tomb !== undefined && tomb === run.updated_at) {
        continue;
      }
      if (tomb !== undefined && tomb !== run.updated_at) {
        gone.delete(run.trace_id);
      }
      let e = envs.get(run.trace_id);
      if (!e) {
        e = {
          id: run.trace_id,
          x: -50,
          y: ENV_Y,
          seed: Math.random() * 1000,
          alpha: 1,
          run: run,
        };
        envs.set(run.trace_id, e);
      }
      e.run = run;
      e.tx = t.x;
      e.ty = t.y;
      e.remove = !!t.remove;
      e.tint = tintFor(run);
      if (e.dying) e.alpha = 1; // revived mid-fade: fully visible/clickable again
      e.dying = false;
      kickLoop(); // V-17: ensure the animation loop runs when envelopes exist
    }
    for (const [id, e] of envs) {
      if (!seen.has(id)) e.dying = true;
    }
  }

  function reset() {
    clearReplayTimers();
    replayState = null;
    pendingRuns = null;
    envs.clear();
    gone.clear();
  }

  function setSource(state) {
    sourceState = state;
  }

  function posFromEvent(ev) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((ev.clientX - rect.left) / rect.width) * W,
      y: ((ev.clientY - rect.top) / rect.height) * H,
    };
  }

  function hitTest(p) {
    for (const e of [...envs.values()].reverse()) {
      if (e.dying || e.alpha <= 0.3) continue;
      if (p.x >= e.x && p.x <= e.x + ENV_W && p.y >= e.y && p.y <= e.y + ENV_H) {
        return e;
      }
    }
    return null;
  }

  function onSelect(cb) { callbacks.select = cb; }
  function onHover(cb) { callbacks.hover = cb; }
  const callbacks = { select: null, hover: null };

  canvas.addEventListener("click", (ev) => {
    const e = hitTest(posFromEvent(ev));
    if (e && callbacks.select) callbacks.select(e.id, e.run);
  });

  canvas.addEventListener("mousemove", (ev) => {
    const e = hitTest(posFromEvent(ev));
    const id = e ? e.id : null;
    if (id !== hoveredId) {
      hoveredId = id;
      canvas.style.cursor = e ? "pointer" : "default";
      if (callbacks.hover) callbacks.hover(e ? e.run : null);
    }
  });

  canvas.addEventListener("mouseleave", () => {
    hoveredId = null;
    canvas.style.cursor = "default";
    if (callbacks.hover) callbacks.hover(null);
  });

  function assignLanes() {
    // Several runs park at the same station x; without a lane offset they
    // stack on one pixel and only the top envelope is clickable.
    const groups = new Map();
    for (const e of envs.values()) {
      if (e.dying || e.remove || e.alpha <= 0) continue;
      const key = Math.round((e.tx ?? 0) / 5);
      let list = groups.get(key);
      if (!list) { list = []; groups.set(key, list); }
      list.push(e);
    }
    for (const list of groups.values()) {
      list.sort((a, b) => String(a.id).localeCompare(String(b.id)));
      list.forEach((e, i) => {
        const col = i % 3;
        const row = Math.floor(i / 3);
        e.laneDx = (col - 1) * 16;
        e.laneDy = row * 16;
      });
    }
  }

  function drawEnvelopes(t) {
    for (const e of envs.values()) {
      if (e.alpha <= 0) continue;
      const y = e.y;
      ctx.globalAlpha = e.alpha;
      drawEnvelope(e.x, y, e.tint);
      if (e.id === hoveredId && !e.dying) {
        ctx.strokeStyle = "#f7d156";
        ctx.lineWidth = 2;
        ctx.strokeRect(e.x - 2, y - 2, ENV_W + 4, ENV_H + 4);
      }
    }
    ctx.globalAlpha = 1;
  }

  function drawStatus(t) {
    const active = [...envs.values()].filter((e) => !e.dying && e.alpha > 0.3).length;
    ctx.font = "bold 11px 'Courier New', monospace";
    ctx.fillStyle = "#7d97b5";
    ctx.textAlign = "left";
    ctx.fillText(`ACTIVE: ${active}`, 20, 460);
    const statusColor = sourceState === "red" ? "#e26863" :
                        sourceState === "green" ? "#5f9e6e" : "#f7d156";
    ctx.fillStyle = statusColor;
    ctx.fillText(`SOURCE: ${sourceState.toUpperCase()}`, 20, 475);
  }

  function draw(t) {
    ctx.clearRect(0, 0, W, H);
    drawBackground();
    drawInboxHopper();
    for (const s of STATIONS) drawStation(s);
    drawConveyor();
    drawEnvelopes(t);
    drawStatus(t);
  }

  function frame(t) {
    assignLanes();
    for (const e of [...envs.values()]) {
      if (!e.dying) {
        const tx = (e.tx ?? 0) + (e.remove ? 0 : (e.laneDx || 0));
        const ty = (e.ty ?? 0) + (e.remove ? 0 : (e.laneDy || 0));
        e.x += (tx - e.x) * 0.08;
        e.y += (ty - e.y) * 0.08;
        // Remove archived/failed items that reach offscreen
        if (e.remove && Math.abs(e.x - e.tx) < 5) {
          e.dying = true;
        }
      } else {
        e.alpha -= 0.06;
        if (e.alpha <= 0) {
          // V-9: record the tombstone when an archived/failed envelope is
          // fully gone so the next snapshot can't respawn it.
          if (e.remove && e.run && e.run.trace_id) {
            gone.delete(e.run.trace_id); // re-insert = newest (Map order)
            gone.set(e.run.trace_id, e.run.updated_at);
            // Bound the tombstones: a long-lived tab saw every run ever.
            while (gone.size > MAX_TOMBSTONES) gone.delete(gone.keys().next().value);
          }
          envs.delete(e.id);
          if (hoveredId === e.id) hoveredId = null;
        }
      }
    }
    draw(t);
  }

  // V-17: the 60 fps full-canvas redraw ran unconditionally forever, even
  // when the tab/document was hidden and when there was nothing to animate —
  // a permanent CPU burn. Pause the loop while hidden or idle (no envelopes),
  // and resume on visibilitychange so the floor stays live when visible.
  let rafId = null;
  let lastFrame = null;
  let idleTimer = null;
  function loop(t) {
    rafId = null;
    idleTimer = null;
    if (document.hidden) {
      return;
    }
    frame(t);
    if (envs.size > 0) {
      rafId = requestAnimationFrame(loop);
    } else {
      // V-27: an empty room must STILL render (stations, labels, belt) or the
      // floor looks dead during boot and whenever the window empties out —
      // but throttle to ~8fps so an idle floor doesn't burn 60fps like the
      // pre-V-17 bug.
      idleTimer = setTimeout(() => kickLoop(), 125);
    }
  }
  function kickLoop() {
    if (idleTimer !== null) {
      clearTimeout(idleTimer);
      idleTimer = null;
    }
    if (rafId === null) {
      rafId = requestAnimationFrame(loop);
    }
  }
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) kickLoop();
  });
  // Paint immediately on load — don't wait for the first snapshot.
  kickLoop();

  /* ---- replay ---- */

  let replayTimers = [];
  let replayState = null;
  let pendingRuns = null;

  function clearReplayTimers() {
    for (const t of replayTimers) clearTimeout(t);
    replayTimers = [];
  }

  function replay(runData) {
    clearReplayTimers();
    // Clear any current envelopes except the one being replayed
    const replayId = runData.trace_id;
    // V-9: a manual replay must bypass the tombstone for this run.
    gone.delete(replayId);
    for (const [id, e] of envs) {
      if (id !== replayId) e.dying = true;
    }
    replayState = { id: replayId, startTime: Date.now(), steps: [] };

    // Build the stage sequence from routing_path (most accurate) or spans
    const routingPath = runData.routing_path || [];

    // V-16: build the stage sequence from the actual spans (chronological),
    // keeping RETRY stages — the old code mapped only the 8 base span names,
    // so whenever timings existed the retries vanished from the replay. Each
    // step is paced by its real span latency (capped) instead of a fixed
    // 600/700 ms.
    const spanToStage = {
      "intake-document": "ingest",
      "normalize-intake": "ingest",
      "intake-ml-triage": "ingest",
      "transcribe-pdf": "ingest",
      "extract-image-text": "ingest",
      // LangGraph node ids (traces recorded from the graph, not traced_node)
      intake: "ingest",
      classify: "classify",
      retry_classify: "classify",
      review_classify: "classify",
      extract: "extract",
      retry_extract: "extract",
      judge_verify: "judge_verify",
      arbiter: "arbiter",
      boss_escalation: "boss",
      human_review: "review",
      compile_report: "report",
      catalog_write: "catalog",
      archive: "archive",
      "classify-document": "classify",
      "judge-verify": "judge_verify",
      "arbitrate-verdict": "arbiter",
      "extract-fields": "extract",
      "adjudicate-conflict": "boss",
      "route-for-review": "review",
      "compile-report": "report",
      "write-catalog": "catalog",
      "archive-document": "archive",
    };
    const spans = (runData.spans || [])
      .filter((s) => s && spanToStage[s.name])
      .slice()
      .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

    const steps = [];
    let prev = null;
    for (const s of spans) {
      let st = spanToStage[s.name];
      if (prev && st === prev) {
        // Repeat pass -> retry variant, once per base stage (a third
        // classify-document from the reviewer pass must not re-add it).
        if (st === "classify") st = "retry_classify";
        else if (st === "extract") st = "retry_extract";
        if (steps.length && steps[steps.length - 1].stage === st) continue;
      }
      prev = spanToStage[s.name];
      // Pace by the span's real latency, clamped to 250 ms..4 s so very fast
      // or very slow runs stay watchable.
      const d = s.latency != null && s.latency > 0
        ? Math.min(Math.max(s.latency * 1000, 250), 4000)
        : 600;
      steps.push({ stage: st, delay: d });
    }
    // Fall back to the routing path (already includes retries + final stages)
    // when spans carry no timing, or a minimal sequence when neither exists.
    let sequence = steps.map((x) => x.stage);
    if (!sequence.length) {
      sequence = (runData.routing_path && runData.routing_path.length)
        ? runData.routing_path
        : ["classify", "extract", "archived"];
    }
    const stageDelay = (st) => {
      for (const x of steps) if (x.stage === st) return x.delay;
      return 700;
    };

    // Create the envelope at the start
    const stageToTarget = {
      inbox: 0, ingest: 0, classify: 0, retry_classify: 0, review_classify: 0, unknown: 0,
      extract: 1, retry_extract: 1,
      judge_verify: 2, arbiter: 2,
      boss: 3,
      report: 4,
      catalog: 5, archive: 5, archived: 5,
      review: 6, failed: 6,
    };
    const stationIdx = (st) => {
      const idx = stageToTarget[st];
      return idx != null ? idx : 0;
    };

    const baseRun = {
      trace_id: replayId,
      filename: runData.filename,
      doc_type: runData.doc_type,
      verdict: runData.verdict,
      quality: runData.quality,
      stage: "archived", // start neutral; will animate through stages
      needs_human: false,
      retried: false,
    };
    // Create envelope at the first station
    let e = envs.get(replayId);
    if (!e) {
      e = {
        id: replayId,
        x: STATIONS[0].x,
        y: ENV_Y,
        seed: Math.random() * 1000,
        alpha: 1,
        run: { ...baseRun, stage: sequence[0] },
      };
      envs.set(replayId, e);
    } else {
      e.x = STATIONS[0].x;
      e.y = ENV_Y;
      e.run = { ...baseRun, stage: sequence[0] };
      e.dying = false;
    }
    e.tint = tintFor(baseRun);
    e.tx = STATIONS[0].x;
    e.ty = ENV_Y;
    e.remove = false;
    kickLoop();

    // Animate through each stage in sequence
    let cumulativeDelay = 600; // initial pause so user sees the envelope appear
    for (let i = 0; i < sequence.length; i++) {
      const stg = sequence[i];
      const idx = stationIdx(stg);
      const t = cumulativeDelay;
      const timer = setTimeout(() => {
        const current = envs.get(replayId);
        if (!current || current.dying) return;
        current.tx = STATIONS[idx].x;
        current.ty = ENV_Y;
        current.run.stage = stg;
        current.tint = tintFor(current.run);
        ConsoleView.log(`REPLAY → ${stg}`, "c-blue");
      }, t);
      replayTimers.push(timer);
      cumulativeDelay += stageDelay(stg);
    }

    // After the sequence finishes, archive it (slide off the floor)
    const endTimer = setTimeout(() => {
      const current = envs.get(replayId);
      if (!current) return;
      current.run.stage = "archived";
      // V-9: carry the real updated_at so the tombstone written when this
      // envelope dies matches the WS payload and it won't respawn.
      current.run.updated_at = runData.updated_at;
      current.tx = 1500;
      current.ty = 440;
      current.remove = true;
      ConsoleView.banner(`REPLAY COMPLETE — ${runData.filename || replayId}`);
    }, cumulativeDelay + 800);
    replayTimers.push(endTimer);
    // Hold live updates until the envelope has slid off, then catch up.
    replayState.until = Date.now() + cumulativeDelay + 3000;
    replayTimers.push(setTimeout(() => {
      replayState = null;
      if (pendingRuns) {
        const runs = pendingRuns;
        pendingRuns = null;
        update(runs);
      }
    }, cumulativeDelay + 3100));
  }

  return { update, reset, setSource, onSelect, onHover, replay };
})();