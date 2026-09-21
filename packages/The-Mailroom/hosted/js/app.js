/* Mailroom Observatory app shell: views, live board, replay, inspector, debug. */
const App = (() => {
  /* Review-tray probe limiter: the queue renders every parked run at once and
     each row fires context + source fetches. Firing ~50 in parallel saturated
     the server threadpool (producer probes can take seconds), starving
     /api/health. Cap the probe concurrency instead. */
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

  const STATIONS = [
    { key: "inbox", label: "Inbox", stages: ["inbox"] },
    { key: "sorter", label: "Sorter", stages: ["intake", "classify", "retry_classify", "review_classify", "unknown"] },
    { key: "extract", label: "Extract", stages: ["extract", "retry_extract"] },
    { key: "judge", label: "Judge", stages: ["judge_verify", "arbiter"] },
    { key: "boss", label: "Boss", stages: ["boss"] },
    { key: "report", label: "Report", stages: ["report"] },
    { key: "archive", label: "Archive", stages: ["catalog", "archive"] },
    { key: "review", label: "Review", stages: ["review"] },
    { key: "done", label: "Completed", stages: ["archived", "failed"] },
  ];

  const SPAN_STAGE = {
    "intake-document": "ingest",
    "normalize-intake": "intake",
    "transcribe-pdf": "intake",
    "extract-image-text": "intake",
    "classify-document": "classify",
    "judge-verify": "judge_verify",
    "arbitrate-verdict": "arbiter",
    "extract-fields": "extract",
    "adjudicate-conflict": "boss",
    "route-for-review": "review",
    "compile-report": "report",
    "write-catalog": "catalog",
    "archive-document": "archive",
    intake: "intake",
    classify: "classify",
    retry_classify: "retry_classify",
    review_classify: "retry_classify",
    extract: "extract",
    retry_extract: "retry_extract",
    judge_verify: "judge_verify",
    arbiter: "arbiter",
    human_review: "review",
    boss_escalation: "boss",
    compile_report: "report",
    catalog_write: "catalog",
    archive: "archive",
  };

  const views = ["pipeline", "review", "history", "matters", "metrics", "debug"];
  let runs = [];
  let meta = null;
  let filter = "all";
  let replay = null;
  let replayTimers = [];
  let lastFocus = null;
  let socketLive = false;
  let pollIntervalMs = 3000;
  let fallbackTimer = null;
  let fallbackPollMs = 0;
  let pipelineOps = null;

  const $ = (id) => document.getElementById(id);

  function dbg(kind, payload) {
    try {
      if (window.ObservatoryDebug) window.ObservatoryDebug.record(kind, payload);
    } catch (_e) { /* debug module optional */ }
  }

  function need(id) {
    const el = $(id);
    if (!el) dbg("visual", { where: "need", message: "missing #" + id });
    return el;
  }

  function announce(msg) {
    const el = $("announce");
    if (el) el.textContent = msg;
    dbg("announce", { message: msg });
  }

  function stationFor(run) {
    const st = run && run.stage;
    if (run && run.needs_human && st !== "failed") return "review";
    for (const s of STATIONS) {
      if (s.stages.includes(st)) return s.key;
    }
    return "sorter";
  }

  function verdictClass(v) {
    if (v === "CORRECT") return "badge-ok";
    if (v === "PARTIAL") return "badge-warn";
    if (v === "MISS") return "badge-bad";
    return "badge-info";
  }

  function setSource(kind, text) {
    const el = need("source-status");
    if (!el) return;
    el.className = `source-status is-${kind}`;
    el.textContent = text;
  }

  function showAlert(msg) {
    const el = need("alert-region");
    if (!el) return;
    if (!msg) { el.hidden = true; el.textContent = ""; return; }
    el.hidden = false;
    el.textContent = msg;
    dbg("visual", { where: "alert", message: msg });
  }

  function applyEditionNote() {
    const el = $("edition-note");
    if (!el || !meta || !meta.ui) return;
    if (meta.edition === "hosted" || meta.edition === "live" || meta.edition === "observatory") {
      el.innerHTML = `This process is the Observatory (<code>${Obs.esc(meta.ui.default || "/")}</code>). The pixel console is not on <code>/</code> here — start <code>mailroom-web</code> for that surface. GitHub Pages is a separate static snapshot.`;
    } else {
      el.innerHTML = `<a href="${Obs.esc(meta.ui.console || "/")}">Local pixel console</a> (this host) · GitHub Pages is a separate static snapshot and is not this site.`;
    }
  }

  function switchView(name) {
    if (!views.includes(name)) name = "pipeline";
    for (const v of views) {
      const sec = $(`view-${v}`);
      if (sec) sec.hidden = v !== name;
    }
    for (const a of document.querySelectorAll(".view-nav a")) {
      const on = a.dataset.view === name;
      if (on) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    }
    if (location.hash.replace("#", "") !== name) {
      history.replaceState(null, "", `#${name}`);
    }
    dbg("view", { name });
    if (name === "review") refreshReview();
    if (name === "history") refreshHistory();
    if (name === "matters") refreshMatters();
    if (name === "metrics") refreshMetrics();
    if (name === "debug") renderDebug();
  }

  function outcomeClass(outcome) {
    if (outcome === "hit") return "badge-ok";
    if (outcome === "miss") return "badge-bad";
    if (outcome === "pending") return "badge-warn";
    return "badge-info";
  }

  function outcomeWord(outcome) {
    if (outcome === "hit") return "hit";
    if (outcome === "miss") return "miss";
    if (outcome === "pending") return "pending";
    return "n/a";
  }

  function cardTitle(run) {
    const archived = run.stage === "archive" || run.stage === "archived" || run.stage === "catalog";
    if (archived && run.archive_name) return run.archive_name;
    return run.filename || run.trace_id;
  }

  function cardHTML(run, { replayId } = {}) {
    const title = Obs.esc(cardTitle(run));
    const replayCls = replayId && run.trace_id === replayId ? " is-replay" : "";
    const verdict = run.verdict
      ? `<span class="badge ${verdictClass(run.verdict)}">${Obs.esc(run.verdict)}</span>`
      : "";
    const stage = `<span class="badge badge-info">${Obs.esc((run.stage || "unknown").replaceAll("_", " "))}</span>`;
    const primary = `<span class="badge ${outcomeClass(run.primary_outcome)}">Primary ${Obs.esc(run.primary_label || "untyped")} · ${outcomeWord(run.primary_outcome)}</span>`;
    const secondary = `<span class="badge ${outcomeClass(run.secondary_outcome)}">Secondary ${Obs.esc(run.secondary_label || "no subclass")} · ${outcomeWord(run.secondary_outcome)}</span>`;
    let extra = "";
    if (run.failure_class || run.run_aborted) {
      extra = `<span class="card-meta">${Obs.esc(run.failure_class ? String(run.failure_class).replaceAll("_", " ") : "aborted")}</span>`;
    } else if (run.needs_reconsideration && Array.isArray(run.review_causes) && run.review_causes.length) {
      extra = `<span class="card-meta">${Obs.esc(run.review_causes.join(", "))}</span>`;
    }
    return `<button type="button" class="card${replayCls}" data-trace="${Obs.esc(run.trace_id)}">
      <span class="card-title">${title}</span>
      <span class="card-meta card-class">${primary} ${secondary}</span>
      <span class="card-meta">${stage} ${verdict}</span>
      ${extra}
    </button>`;
  }

  function renderHeadlines(list, ops) {
    const el = need("headline-strip");
    if (!el) return;
    const rows = Array.isArray(list) ? list : [];
    let inflight = 0, review = 0, archived = 0, failed = 0;
    let primaryHit = 0, primaryN = 0, secondaryHit = 0, secondaryN = 0;
    let correct = 0, miss = 0, judged = 0;
    for (const r of rows) {
      const tray = stationFor(r);
      if (tray === "review") review += 1;
      else if (tray === "done" && r.stage === "failed") failed += 1;
      else if (tray === "done" || tray === "archive") archived += 1;
      else inflight += 1;
      if (r.primary_outcome && r.primary_outcome !== "n_a") {
        primaryN += 1;
        if (r.primary_outcome === "hit") primaryHit += 1;
      }
      if (r.secondary_outcome && r.secondary_outcome !== "n_a") {
        secondaryN += 1;
        if (r.secondary_outcome === "hit") secondaryHit += 1;
      }
      if (r.verdict) {
        judged += 1;
        if (r.verdict === "CORRECT") correct += 1;
        if (r.verdict === "MISS") miss += 1;
      }
    }
    const frac = (n, d) => (d ? `${n}/${d}` : "—");
    const tiles = [
      ["In flight", inflight],
      ["Review", review],
      ["Archived", archived],
      ["Failed", failed],
      ["Primary classified", frac(primaryHit, primaryN)],
      ["Secondary classified", frac(secondaryHit, secondaryN)],
    ];
    if (judged) {
      tiles.push(["Judge CORRECT", correct]);
      tiles.push(["Judge MISS", miss]);
    }
    if (ops && ops.configured && ops.inbox_pending != null) {
      tiles.push(["Inbox pending", ops.inbox_pending]);
    }
    el.innerHTML = tiles.map(([k, v]) => `<div class="headline"><dt>${Obs.esc(k)}</dt><dd>${Obs.esc(String(v))}</dd></div>`).join("");
  }

  function matchesFilter(run) {
    if (filter === "all") return true;
    const tray = stationFor(run);
    if (filter === "review") return tray === "review";
    if (filter === "done") return tray === "done";
    if (filter === "inflight") return tray !== "done" && tray !== "review";
    return true;
  }

  function renderBoard() {
    const board = need("pipeline-board");
    if (!board) return;
    const replayId = replay && replay.id;
    const shown = runs.filter(matchesFilter);
    const groups = Object.fromEntries(STATIONS.map((s) => [s.key, []]));
    for (const r of shown) groups[stationFor(r)].push(r);
    board.innerHTML = STATIONS.map((s) => {
      const items = groups[s.key] || [];
      const body = items.length
        ? items.map((r) => cardHTML(r, { replayId })).join("")
        : `<p class="empty">Empty tray</p>`;
      return `<section class="tray" aria-labelledby="tray-${s.key}">
        <h3 id="tray-${s.key}">${s.label} <span class="tray-count">(${items.length})</span></h3>
        ${body}
      </section>`;
    }).join("");
    bindCards(board);
    const count = need("run-count");
    if (count) count.textContent = `${runs.length} run${runs.length === 1 ? "" : "s"} in the live window`;
    renderHeadlines(runs, pipelineOps);
  }

  function applyPipelineOps(ops) {
    pipelineOps = ops || null;
    renderHeadlines(runs, pipelineOps);
    bindInboxQueue(ops);
    const el = need("pipeline-ops");
    if (!el) return;
    if (!ops || !ops.configured) {
      el.hidden = true;
      return;
    }
    el.hidden = false;
    const w = ops.watcher === "live" ? "Watcher live"
      : ops.watcher === "stale" ? "Watcher stale"
      : "Watcher down";
    const inbox = ops.inbox_pending == null ? "?" : ops.inbox_pending;
    const paused = ops.ingestion_paused ? " · ingestion paused" : "";
    el.textContent = `${w} · inbox ${inbox}${paused}`;
  }

  function bindCards(root) {
    for (const btn of root.querySelectorAll("[data-trace]")) {
      btn.addEventListener("click", () => openInspect(btn.dataset.trace));
    }
  }

  function overlayReplay(list) {
    if (!replay || !replay.stage) return list;
    const next = list.slice();
    const idx = next.findIndex((r) => r.trace_id === replay.id);
    const overlay = {
      ...(idx >= 0 ? next[idx] : { trace_id: replay.id, filename: replay.filename, doc_type: replay.doc_type }),
      stage: replay.stage,
      needs_human: replay.stage === "review",
    };
    if (idx >= 0) next[idx] = overlay;
    else next.unshift(overlay);
    return next;
  }

  // #111: BERT lane panels — reductions over the same live run list the
  // trays render. The module is DOM-free and optional: if bert_panels.js
  // failed to load the section says so instead of guessing numbers.
  function renderBertPanels(list) {
    const el = need("bert-panels-body");
    if (!el) return;
    const P = window.BERTPanels;
    if (!P || typeof P.render !== "function") {
      el.innerHTML = `<p class="empty">BERT lane panels unavailable — bert_panels.js did not load.</p>`;
      return;
    }
    el.innerHTML = P.render(Array.isArray(list) ? list : []);
  }

  function applyRuns(next) {
    runs = overlayReplay(Array.isArray(next) ? next : []);
    renderBoard();
    renderBertPanels(runs);
  }

  function table(caption, headers, rows) {
    if (!rows.length) return `<p class="empty">Nothing in this view.</p>`;
    return `<div class="table-wrap"><table class="data">
      <caption>${Obs.esc(caption)}</caption>
      <thead><tr>${headers.map((h) => `<th scope="col">${Obs.esc(h)}</th>`).join("")}</tr></thead>
      <tbody>${rows.join("")}</tbody>
    </table></div>`;
  }

  function classOptions(selected) {
    const classes = (meta && meta.doc_classes) || {
      contract: "Contract / Agreement",
      corporate_record: "Corporate Record",
      correspondence: "Correspondence",
      compliance_filing: "Compliance Filing",
      insurance_claim: "Insurance Claim",
      merger_agreement: "Merger Agreement",
      unknown: "Unknown",
    };
    const current = selected || "";
    const keys = Object.keys(classes);
    if (current && !keys.includes(current)) keys.unshift(current);
    return [`<option value="">(keep current)</option>`].concat(keys.map((k) => {
      const sel = k === current ? " selected" : "";
      return `<option value="${Obs.esc(k)}"${sel}>${Obs.esc(classes[k] || k)}</option>`;
    })).join("");
  }

  function subclassOptions(docType, selected) {
    const catalog = ((meta && meta.doc_subclasses) || {})[docType] || [];
    const current = selected || "";
    const opts = [`<option value="">(none / keep)</option>`];
    const seen = new Set();
    for (const k of catalog) {
      seen.add(k);
      const sel = k === current ? " selected" : "";
      opts.push(`<option value="${Obs.esc(k)}"${sel}>${Obs.esc(k)}</option>`);
    }
    if (current && !seen.has(current)) {
      opts.splice(1, 0, `<option value="${Obs.esc(current)}" selected>${Obs.esc(current)}</option>`);
    }
    return { html: opts.join(""), has: catalog.length > 0 || !!current };
  }

  function reviewForm(run) {
    if (!run || !(run.stage === "review" || run.needs_human || run.needs_reconsideration)) return "";
    const parked = run.stage === "review";
    const disp = parked ? "resume" : "record";
    const hint = parked
      ? "Correct the class if the sorter missed. Resume re-extracts with that class. Record writes an audit row only. Requeue copies the file to the inbox. Complete archives operator extracted_data without another LLM pass."
      : "Not parked in the review bin — Resume and Complete are disabled. Record or requeue instead.";
    const currentType = run.doc_type || "";
    const currentSub = run.doc_subclass || run.contract_subtype || "";
    const subs = subclassOptions(currentType, currentSub);
    const openHref = Obs.api.reviewSourceUrl({
      trace_id: run.trace_id || "",
      filename: run.filename || "",
      doc_id: run.doc_id || "",
    });
    return `<form class="review-resolve" data-trace="${Obs.esc(run.trace_id || "")}" data-filename="${Obs.esc(run.filename || "")}" data-doc-id="${Obs.esc(run.doc_id || "")}">
      <p class="hint">${Obs.esc(hint)}</p>
      <div class="review-source">
        <div class="review-source-toolbar">
          <span>Document</span>
          <a class="review-source-open" href="${Obs.esc(openHref)}" target="_blank" rel="noopener">Open original</a>
          <span class="review-source-badge" hidden>truncated</span>
        </div>
        <pre class="review-source-text">Loading document text…</pre>
      </div>
      <label>Doc type
        <select name="doc_type">${classOptions(currentType)}</select>
      </label>
      <label class="review-subclass-label"${subs.has ? "" : " hidden"}>Subtype
        <select name="doc_subclass">${subs.html}</select>
      </label>
      <label>Notes <textarea name="notes" rows="2"></textarea></label>
      <label>Disposition
        <select name="disposition">
          <option value="resume" ${disp === "resume" ? "selected" : ""} ${parked ? "" : "disabled"}>Resume pipeline</option>
          <option value="record" ${disp === "record" ? "selected" : ""}>Record only (audit)</option>
          <option value="requeue">Requeue to inbox</option>
          <option value="complete" ${parked ? "" : "disabled"}>Complete (human extraction)</option>
        </select>
      </label>
      <label class="review-extracted-wrap"${parked ? "" : " hidden"}>extracted_data (JSON)
        <textarea name="extracted_data" rows="4" placeholder='{"claim_number": "…"}'></textarea>
      </label>
      <div class="toolbar" role="group" aria-label="Review decision">
        <button type="submit" class="btn" data-decision="approved">Approve</button>
        <button type="submit" class="btn btn-quiet" data-decision="rejected">Reject</button>
        <button type="submit" class="btn btn-quiet" data-decision="approved" data-disposition="requeue">Requeue</button>
        <button type="submit" class="btn" data-decision="approved" data-disposition="complete" ${parked ? "" : "disabled"}>Complete</button>
      </div>
      <p class="review-status" role="status"></p>
    </form>`;
  }

  function fillHostedSubclass(form) {
    const typeSel = form.querySelector("select[name='doc_type']");
    const subSel = form.querySelector("select[name='doc_subclass']");
    const label = form.querySelector(".review-subclass-label");
    if (!typeSel || !subSel) return;
    const next = subclassOptions(typeSel.value, "");
    subSel.innerHTML = next.html;
    if (label) label.hidden = !next.has;
  }

  function bindReviewSource(form) {
    const pane = form.querySelector(".review-source-text");
    const badge = form.querySelector(".review-source-badge");
    const open = form.querySelector(".review-source-open");
    if (!pane) return;
    probe(() => Obs.api.reviewSource({
      trace_id: form.dataset.trace,
      filename: form.dataset.filename,
      doc_id: form.dataset.docId,
    })).then((src) => {
      if (!src || src.configured === false) {
        pane.textContent = (src && src.error) || "Live producer required to view the parked file.";
        if (open) open.hidden = true;
        return;
      }
      if (!src.readable || !src.text) {
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
      if (typeSel) typeSel.addEventListener("change", () => fillHostedSubclass(form));
      bindReviewSource(form);
      probe(() => Obs.api.reviewContext({
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
        const status = form.querySelector(".review-status");
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
          } catch (_err) {
            if (status) status.textContent = "extracted_data is not valid JSON";
            return;
          }
          if (disposition === "complete" && (!extractedData || typeof extractedData !== "object" || Array.isArray(extractedData))) {
            if (status) status.textContent = "Complete needs an extracted_data JSON object";
            return;
          }
        }
        if (status) status.textContent = "Submitting…";
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
          const result = await Obs.api.reviewResolve(payload);
          if (status) {
            status.textContent = `Saved — ${result.disposition || disposition} ${result.decision || decision}`;
          }
          if (typeof onDone === "function") onDone(result);
        } catch (err) {
          if (status) status.textContent = err.message || String(err);
        }
      });
    }
  }

  async function refreshReview() {
    const el = need("review-list");
    if (!el) return;
    el.innerHTML = `<p class="empty">Loading review queue…</p>`;
    try {
      const [data, ctx] = await Promise.all([
        Obs.api.reviewQueue(),
        Obs.api.reviewContext().catch(() => null),
      ]);
      const setup = ctx && ctx.configured === false
        ? `<p class="empty" role="status">${Obs.esc(ctx.error || "Set MAILROOM_PIPELINE_URL to resolve reviews.")}</p>`
        : "";
      const rows = (data.runs || []).map((r) => `<tr>
        <th scope="row"><button type="button" class="row-btn" data-trace="${Obs.esc(r.trace_id)}">${Obs.esc(r.filename || r.trace_id)}</button></th>
        <td>${Obs.esc((r.doc_type || "—").replaceAll("_", " "))}${r.doc_subclass || r.contract_subtype ? ` / ${Obs.esc(r.doc_subclass || r.contract_subtype)}` : ""}</td>
        <td>${Obs.esc(r.failure_class ? String(r.failure_class).replaceAll("_", " ") : (r.escalation_reason || r.review_decision || "—"))}${
          Array.isArray(r.review_causes) && r.review_causes.length
            ? ` (${r.review_causes.join(", ")})`
            : ""
        }</td>
        <td>${r.verdict ? `<span class="badge ${verdictClass(r.verdict)}">${Obs.esc(r.verdict)}</span>` : "—"}</td>
        <td>${reviewForm(r)}</td>
      </tr>`);
      el.innerHTML = setup + table("Runs waiting on a human", ["Document", "Type", "Why", "Verdict", "Resolve"], rows);
      bindCards(el);
      bindReviewForms(el, { onDone: () => refreshReview() });
      dbg("traces", { where: "review", count: (data.runs || []).length });
    } catch (err) {
      dbg("review-error", { message: err.message });
      let setup = "";
      try {
        const ctx = await Obs.api.reviewContext();
        if (ctx && ctx.configured === false) {
          setup = `<p class="empty" role="status">${Obs.esc(ctx.error || "Set MAILROOM_PIPELINE_URL to resolve reviews.")}</p>`;
        }
      } catch (_e) { /* producer probe is best-effort */ }
      el.innerHTML = `${setup}<p class="empty" role="alert">Review queue unavailable — ${Obs.esc(err.message)}</p>`;
    }
  }

  async function refreshHistory() {
    const el = need("history-list");
    if (!el) return;
    el.innerHTML = `<p class="empty">Loading history…</p>`;
    try {
      const data = await Obs.api.traces(604800, 200);
      const rows = (data.runs || []).map((r) => `<tr>
        <th scope="row"><button type="button" class="row-btn" data-trace="${Obs.esc(r.trace_id)}">${Obs.esc(r.filename || r.trace_id)}</button></th>
        <td>${Obs.esc((r.stage || "—").replaceAll("_", " "))}</td>
        <td>${Obs.esc((r.doc_type || "—").replaceAll("_", " "))}${r.doc_subclass || r.contract_subtype ? ` / ${Obs.esc(r.doc_subclass || r.contract_subtype)}` : ""}</td>
        <td>${r.verdict ? `<span class="badge ${verdictClass(r.verdict)}">${Obs.esc(r.verdict)}</span>` : "—"}</td>
        <td>${Obs.fmt.when(r.updated_at || r.created_at)}</td>
        <td><button type="button" class="btn" data-replay="${Obs.esc(r.trace_id)}">Replay</button></td>
      </tr>`);
      el.innerHTML = table("Recent runs", ["Document", "Stage", "Type", "Verdict", "Updated", "Replay"], rows);
      bindCards(el);
      for (const btn of el.querySelectorAll("[data-replay]")) {
        btn.addEventListener("click", () => startReplay(btn.dataset.replay));
      }
      dbg("traces", { where: "history", count: (data.runs || []).length });
    } catch (err) {
      dbg("history-error", { message: err.message });
      el.innerHTML = `<p class="empty" role="alert">History unavailable — ${Obs.esc(err.message)}</p>`;
    }
  }

  async function refreshMatters() {
    const el = need("matters-list");
    if (!el) return;
    el.innerHTML = `<p class="empty">Loading matters…</p>`;
    try {
      const data = await Obs.api.sessions(50);
      const sessions = data.sessions || [];
      if (!sessions.length) { el.innerHTML = `<p class="empty">No sessions in the recent window.</p>`; return; }
      el.innerHTML = sessions.map((s) => {
        const runsHtml = (s.runs || []).map((r) =>
          `<li><button type="button" class="row-btn" data-trace="${Obs.esc(r.trace_id)}">${Obs.esc(r.filename || r.trace_id)}</button>
           — ${Obs.esc((r.stage || "").replaceAll("_", " "))} ${r.verdict ? `· ${Obs.esc(r.verdict)}` : ""}</li>`).join("");
        return `<article class="matter">
          <h3>${Obs.esc(s.name || s.id || "matter")}</h3>
          <p>${s.trace_count || 0} traces · updated ${Obs.esc(Obs.fmt.when(s.updated_at))}</p>
          <ul>${runsHtml || "<li>No run detail on this session</li>"}</ul>
        </article>`;
      }).join("");
      bindCards(el);
      dbg("traces", { where: "matters", count: sessions.length });
    } catch (err) {
      dbg("matters-error", { message: err.message });
      el.innerHTML = `<p class="empty" role="alert">Matters unavailable — ${Obs.esc(err.message)}</p>`;
    }
  }

  function metricTile(label, value) {
    return `<div class="metric"><dt>${Obs.esc(label)}</dt><dd>${value}</dd></div>`;
  }

  async function refreshMetrics() {
    const el = need("metrics-grid");
    if (!el) return;
    el.innerHTML = `<p class="empty">Loading metrics…</p>`;
    try {
      const m = await Obs.api.metrics(604800);
      const verdicts = Object.entries(m.verdict_counts || {});
      const docs = Object.entries(m.per_doc_type || {});
      const maxV = Math.max(1, ...verdicts.map(([, v]) => v));
      const maxD = Math.max(1, ...docs.map(([, v]) => v));
      const palette = { CORRECT: "var(--ok)", PARTIAL: "var(--warn)", MISS: "var(--bad)" };
      const bars = (title, entries, max, useVerdictColors) => {
        if (!entries.length) return "";
        return `<div class="bar-list"><h3>${Obs.esc(title)}</h3>${entries.map(([k, v]) => {
          const label = (meta && meta.doc_classes && meta.doc_classes[k]) || k;
          const pct = Math.round((v / max) * 100);
          const fill = useVerdictColors ? (palette[k] || "var(--info)") : "var(--info)";
          return `<div class="bar"><span>${Obs.esc(label)}</span>
            <span class="bar-track"><span class="bar-fill" style="width:${pct}%;background:${fill}"></span></span>
            <span>${v}</span></div>`;
        }).join("")}</div>`;
      };
      const pct = (v) => (v == null ? "—" : `${(Number(v) * 100).toFixed(1)}%`);
      const extraTiles = [
        m.avg_extraction_verified_precision != null ? metricTile("Verified precision", pct(m.avg_extraction_verified_precision)) : "",
        m.avg_content_topic_accuracy != null ? metricTile("Topic accuracy", pct(m.avg_content_topic_accuracy)) : "",
        m.avg_content_topic_f1_macro != null ? metricTile("Topic F1", pct(m.avg_content_topic_f1_macro)) : "",
        m.avg_sentiment_accuracy != null ? metricTile("Sentiment accuracy", pct(m.avg_sentiment_accuracy)) : "",
        m.avg_sentiment_f1_macro != null ? metricTile("Sentiment F1", pct(m.avg_sentiment_f1_macro)) : "",
        m.avg_maud_question_accuracy != null ? metricTile("MAUD question acc", pct(m.avg_maud_question_accuracy)) : "",
        m.avg_maud_question_macro_accuracy != null ? metricTile("MAUD question macro", pct(m.avg_maud_question_macro_accuracy)) : "",
        m.avg_maud_clause_presence != null ? metricTile("MAUD clause", pct(m.avg_maud_clause_presence)) : "",
        m.avg_maud_valid_class_rate != null ? metricTile("MAUD valid class", pct(m.avg_maud_valid_class_rate)) : "",
        m.avg_maud_category_accuracy != null ? metricTile("MAUD category", pct(m.avg_maud_category_accuracy)) : "",
      ].join("");
      const subclasses = Object.entries(m.per_doc_subclass || {});
      const maxS = Math.max(1, ...subclasses.map(([, v]) => v));
      el.innerHTML = `<dl class="metrics">${
        metricTile("Documents", m.total_docs ?? "—")
        + metricTile("Archived", m.archived ?? "—")
        + metricTile("Review", m.review ?? "—")
        + (m.reconsideration ? metricTile("Reconsider", m.reconsideration) : "")
        + metricTile("Failed", m.failed ?? "—")
        + metricTile("In flight", m.in_flight ?? "—")
        + metricTile("Total cost", Obs.fmt.cost(m.total_cost_usd))
        + metricTile("Tokens", Obs.fmt.tokens(m.total_tokens))
        + metricTile("LLM calls", Obs.fmt.tokens(m.llm_calls))
        + metricTile("Avg quality", m.avg_quality == null ? "—" : Number(m.avg_quality).toFixed(2))
        + extraTiles
      }</dl>${bars("Judge verdicts", verdicts, maxV, true)}${bars("Document types", docs, maxD, false)}${bars("Document subclasses", subclasses, maxS, false)}`;
      dbg("traces", { where: "metrics", docs: m.total_docs });
    } catch (err) {
      dbg("metrics-error", { message: err.message });
      el.innerHTML = `<p class="empty" role="alert">Metrics unavailable — ${Obs.esc(err.message)}</p>`;
    }
  }

  function scoreEntries(scores) {
    if (!scores) return [];
    if (Array.isArray(scores)) {
      return scores.filter((s) => s && s.name != null && s.value != null).map((s) => [s.name, s.value]);
    }
    if (typeof scores === "object") return Object.entries(scores).filter(([, v]) => v != null);
    return [];
  }

  function fmtScore(v) {
    if (v == null) return "—";
    if (typeof v === "object") {
      try { return JSON.stringify(v); } catch (e) { return String(v); }
    }
    return String(v);
  }

  async function openInspect(traceId) {
    lastFocus = document.activeElement;
    const dlg = need("inspect-dialog");
    const title = need("inspect-title");
    const body = need("inspect-body");
    if (!dlg || !title || !body) return;
    title.textContent = "Loading trace…";
    body.innerHTML = `<p>Fetching ${Obs.esc(traceId)} from the live source…</p>`;
    dlg.showModal();
    try {
      const run = await Obs.api.run(traceId);
      if (run && run.error) throw new Error(run.error);
      title.textContent = run.filename || run.trace_id;
      const rows = [
        ["Trace", run.trace_id],
        ["Stage", run.stage],
        ["Phase", run.phase],
        ["Type", run.doc_type],
        ["Subclass", run.doc_subclass || run.contract_subtype || "—"],
        ["Primary", `${run.primary_label || run.doc_type || "untyped"} · ${outcomeWord(run.primary_outcome)}`],
        ["Secondary", `${run.secondary_label || "no subclass"} · ${outcomeWord(run.secondary_outcome)}`],
        ["Archive name", run.archive_name || "—"],
        ["Expected class", run.expected_hf_class || "—"],
        ["Expected subclass", run.expected_subclass || "—"],
        ["Intake", [
          run.intake_method,
          run.intake_messy ? "messy" : null,
          run.intake_changed ? "changed" : null,
          run.intake_chars != null ? `${run.intake_chars} chars` : null,
        ].filter(Boolean).join(" · ") || "—"],
        ["Matter", run.session_id || run.matter_id],
        ["Producer doc id", run.doc_id || "—"],
        ["User", run.user_id || "—"],
        ["Release", run.release || "—"],
        ["Verdict", run.verdict || "—"],
        ["Quality", run.quality == null ? "—" : Number(run.quality).toFixed(2)],
        ["Latency", Obs.fmt.latency(run.latency)],
        ["Tokens", Obs.fmt.tokens(run.total_tokens)],
        ["Cost", Obs.fmt.cost(run.cost_usd)],
        ["Created", Obs.fmt.when(run.created_at)],
      ];
      if (run.escalation_reason) rows.push(["Escalation", run.escalation_reason]);
      if (run.failure_class) rows.push(["Failure class", String(run.failure_class).replaceAll("_", " ")]);
      if (run.run_aborted) rows.push(["Aborted", "yes"]);
      if (Array.isArray(run.review_causes) && run.review_causes.length) {
        rows.push(["Reconsider", run.review_causes.join(", ")]);
      }
      if (run.error_message) rows.push(["Error", run.error_message]);
      const spans = (run.spans || []).map((s) =>
        `<div class="span"><strong>${Obs.esc(s.name)}</strong>
         ${s.observation_type ? `<span class="obs-type">${Obs.esc(s.observation_type)}</span>` : ""}
         ${s.is_root ? `<span class="obs-type">ROOT</span>` : ""}
         — ${Obs.esc(s.status || "")} · ${Obs.fmt.latency(s.latency)}
         ${s.error_message ? `<div>${Obs.esc(s.error_message)}</div>` : ""}</div>`).join("")
        || `<p class="empty">No observation detail on this trace</p>`;
      const gens = (run.generations || []).map((g) =>
        `<div class="gen"><strong>${Obs.esc(g.name || g.model || g.agent || "generation")}</strong>
         ${g.observation_type ? `<span class="obs-type">${Obs.esc(g.observation_type)}</span>` : ""}
         · ${Obs.fmt.latency(g.latency)}
         ${g.usage_total_tokens != null ? ` · ${Obs.fmt.tokens(g.usage_total_tokens)} tok` : ""}
         ${g.cost_usd ? ` · ${Obs.fmt.cost(g.cost_usd)}` : ""}</div>`).join("")
        || `<p class="empty">No generations on this trace</p>`;
      const scores = scoreEntries(run.scores);
      const SUITE_EXTRA_SCORES = new Set([
        "content_topic_accuracy", "content_topic_f1_macro",
        "sentiment_accuracy", "sentiment_f1_macro",
        "maud_question_accuracy", "maud_question_macro_accuracy",
        "maud_clause_presence", "maud_valid_class_rate", "maud_category_accuracy",
      ]);
      const suite = scores.filter(([k]) => SUITE_EXTRA_SCORES.has(k));
      const rest = scores.filter(([k]) => !SUITE_EXTRA_SCORES.has(k));
      const scoreHtml = (entries) => entries.map(([k, v]) =>
        `<div class="span"><strong>${Obs.esc(k)}</strong> · ${Obs.esc(fmtScore(v))}</div>`).join("");
      const scoresBlock = rest.length
        ? scoreHtml(rest)
        : (suite.length ? "" : `<p class="empty">No scores attached</p>`);
      const suiteBlock = suite.length
        ? `<h3>Suite extras</h3><div class="stack">${scoreHtml(suite)}</div>`
        : "";
      body.innerHTML = `
        ${reviewForm(run)}
        <dl class="kv">${rows.map(([k, v]) => `<dt>${Obs.esc(k)}</dt><dd>${Obs.esc(v == null ? "—" : v)}</dd>`).join("")}</dl>
        <h3>Observations</h3><div class="stack">${spans}</div>
        <h3>LLM generations</h3><div class="stack">${gens}</div>
        ${scoresBlock ? `<h3>Scores</h3><div class="stack">${scoresBlock}</div>` : ""}
        ${suiteBlock}`;
      bindReviewForms(body, { onDone: () => refreshReview() });
      dbg("traces", { where: "inspect", id: traceId, spans: (run.spans || []).length });
    } catch (err) {
      dbg("detail-error", { id: traceId, message: err.message });
      title.textContent = "Trace unavailable";
      body.innerHTML = `<p role="alert">${Obs.esc(err.message)}</p>`;
    }
  }

  function closeInspect() {
    if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
  }

  function clearReplayTimers() {
    for (const t of replayTimers) clearTimeout(t);
    replayTimers = [];
  }

  function setReplayBar(visible) {
    const bar = need("replay-bar");
    if (!bar) return;
    bar.hidden = !visible;
    bar.classList.toggle("is-on", !!visible);
    if (visible) bar.removeAttribute("hidden");
    else bar.setAttribute("hidden", "");
  }

  function setReplayButtons(on) {
    const play = need("replay-play");
    const step = need("replay-step");
    const stop = need("replay-stop");
    if (play) play.disabled = !on;
    if (step) step.disabled = !on;
    if (stop) stop.disabled = !on;
  }

  function setReplayStatus(text) {
    const el = need("replay-status");
    if (el) el.textContent = text;
  }

  function terminalStage(run) {
    if (!run) return "archived";
    if (run.needs_human && run.stage !== "failed") return "review";
    if (run.stage) return run.stage;
    return "archived";
  }

  function sequenceFrom(run) {
    const spans = (run.spans || [])
      .filter((s) => s && SPAN_STAGE[s.name])
      .slice()
      .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
    const steps = [];
    let prev = null;
    for (const s of spans) {
      let st = SPAN_STAGE[s.name];
      if (prev && st === prev) {
        if (st === "classify") st = "retry_classify";
        else if (st === "extract") st = "retry_extract";
        if (steps.length && steps[steps.length - 1].stage === st) continue;
      }
      prev = SPAN_STAGE[s.name];
      const d = s.latency != null && s.latency > 0
        ? Math.min(Math.max(s.latency * 1000, 250), 4000)
        : 700;
      steps.push({ stage: st, delay: d });
    }
    if (!steps.length) {
      const path = run.routing_path && run.routing_path.length
        ? run.routing_path
        : ["classify", "extract", "archived"];
      return path.map((stage) => ({ stage, delay: 700 }));
    }
    return steps;
  }

  function applyReplayStage(stage) {
    if (!replay) return;
    replay.stage = stage;
    const idx = runs.findIndex((r) => r.trace_id === replay.id);
    const overlay = {
      ...(idx >= 0 ? runs[idx] : { trace_id: replay.id, filename: replay.filename, doc_type: replay.doc_type }),
      stage,
      needs_human: stage === "review",
    };
    if (idx >= 0) runs[idx] = overlay;
    else runs = [overlay, ...runs];
    renderBoard();
    setReplayStatus(`Replay · ${replay.filename} · ${stage.replaceAll("_", " ")}`);
    announce(`Replay moved to ${stage.replaceAll("_", " ")}`);
    dbg("replay", { id: replay.id, stage, index: replay.index });
  }

  function reducedMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  async function startReplay(traceId) {
    clearReplayTimers();
    setReplayBar(true);
    setReplayStatus("Loading replay…");
    try {
      const run = await Obs.api.run(traceId);
      if (run && run.error) throw new Error(run.error);
      replay = {
        id: run.trace_id,
        filename: run.filename || run.trace_id,
        doc_type: run.doc_type,
        steps: sequenceFrom(run),
        index: 0,
        playing: false,
        terminal: terminalStage(run),
      };
      setReplayButtons(true);
      switchView("pipeline");
      setReplayBar(true);
      applyReplayStage(replay.steps[0] ? replay.steps[0].stage : "classify");
      if (!reducedMotion()) playReplay();
    } catch (err) {
      dbg("detail-error", { where: "replay", id: traceId, message: err.message });
      setReplayStatus(`Replay failed — ${err.message}`);
      showAlert(`Replay failed — ${err.message}`);
    }
  }

  function playReplay() {
    if (!replay || !replay.steps.length) return;
    replay.playing = true;
    const play = $("replay-play");
    if (play) play.textContent = "Pause replay";
    scheduleReplay();
  }

  function pauseReplay() {
    if (!replay) return;
    replay.playing = false;
    clearReplayTimers();
    const play = $("replay-play");
    if (play) play.textContent = "Play replay";
  }

  function scheduleReplay() {
    clearReplayTimers();
    if (!replay || !replay.playing) return;
    const next = replay.index + 1;
    if (next >= replay.steps.length) {
      finishReplay();
      return;
    }
    const delay = reducedMotion() ? 0 : replay.steps[replay.index].delay;
    replayTimers.push(setTimeout(() => {
      replay.index = next;
      applyReplayStage(replay.steps[next].stage);
      scheduleReplay();
    }, delay));
  }

  function stepReplay() {
    if (!replay) return;
    pauseReplay();
    const next = Math.min(replay.index + 1, replay.steps.length - 1);
    replay.index = next;
    applyReplayStage(replay.steps[next].stage);
    if (next === replay.steps.length - 1) finishReplay();
  }

  function finishReplay() {
    pauseReplay();
    const end = replay && replay.terminal ? replay.terminal : "archived";
    if (replay) applyReplayStage(end);
    setReplayStatus(replay ? `Replay complete — ${replay.filename}` : "Replay complete");
    announce("Replay complete");
    setReplayButtons(true);
    const play = $("replay-play");
    if (play) play.textContent = "Play replay";
    dbg("replay", { phase: "complete", terminal: end });
  }

  function stopReplay() {
    pauseReplay();
    replay = null;
    setReplayButtons(false);
    setReplayBar(false);
    const play = $("replay-play");
    if (play) play.textContent = "Play replay";
    setReplayStatus("No replay loaded");
    refreshTraces();
  }

  function applyPollInterval(seconds) {
    if (typeof seconds === "number" && seconds > 0) {
      pollIntervalMs = Math.max(1000, Math.round(seconds * 1000));
    }
  }

  async function refreshTraces() {
    try {
      const data = await Obs.api.traces(604800, 200);
      applyRuns(data.runs || []);
      showAlert("");
      if (data.source === "langfuse-cache") {
        const age = data.cached_at ? ` · ${data.cached_at}` : "";
        setSource("stale", `SOURCE: CACHE${age}`);
      }
      dbg("traces", { where: "floor", count: (data.runs || []).length });
      try {
        applyPipelineOps(await Obs.api.pipeline());
      } catch (_e) { /* producer URL optional */ }
    } catch (err) {
      dbg("traces-error", { message: err.message });
      showAlert(`Could not load traces — ${err.message}`);
    }
  }

  function startFallbackPolling() {
    const tick = async () => {
      if (socketLive) return;
      await refreshTraces();
    };
    if (fallbackTimer && fallbackPollMs === pollIntervalMs) return;
    if (fallbackTimer) clearInterval(fallbackTimer);
    fallbackPollMs = pollIntervalMs;
    fallbackTimer = setInterval(tick, pollIntervalMs);
    dbg("poll", { where: "fallback", ms: pollIntervalMs });
  }

  async function checkHealth() {
    try {
      const h = await Obs.api.health();
      const ok = !!(h.ok ?? h.langfuse);
      dbg("health", { ok, source: h.source, raw: h });
      if (ok) {
        showAlert("");
        if (h.source === "langfuse-cache") {
          const age = h.cached_at ? ` · ${h.cached_at}` : "";
          setSource("stale", `SOURCE: CACHE${age}`);
        } else if (!socketLive) {
          setSource("live", `Live · source ${h.source || "langfuse"}`);
        }
        if (!meta) {
          try {
            meta = await Obs.api.meta();
            applyPollInterval(meta.poll_interval_s);
            dbg("meta", { edition: meta.edition, version: meta.version });
            applyEditionNote();
          } catch (e) {
            dbg("error", { where: "meta", message: e && e.message ? e.message : String(e) });
          }
        }
        return true;
      }
      socketLive = false;
      setSource("down", "Trace source reported offline");
      return false;
    } catch (err) {
      socketLive = false;
      dbg("error", { where: "health", message: err.message });
      setSource("down", `No live connection — ${err.message}`);
      if (!runs.length) {
        showAlert("The Observatory needs the Mailroom API (Langfuse-backed) on this host. This is not the GitHub Pages snapshot.");
      }
      return false;
    }
  }

  function onMessage(msg) {
    if (msg.type === "status") {
      socketLive = !!msg.connected;
      if (msg.connected) setSource("live", "Live · WebSocket connected");
      else setSource("stale", "Socket disconnected — reconnecting");
    } else if (msg.type === "snapshot") {
      applyRuns(msg.runs || []);
      applyPipelineOps(msg.pipeline);
      applyPollInterval(msg.poll_interval_s);
      if (!socketLive) startFallbackPolling();
      if (msg.stale) setSource("stale", "Live · last snapshot is stale");
    }
  }

  function tick() {
    const el = $("clock");
    if (!el) return;
    el.textContent = new Date().toLocaleTimeString(undefined, { hour12: false });
  }

  function renderDebug() {
    const D = window.__OBSERVATORY_DEBUG__;
    const summary = $("dbg-summary");
    const list = $("dbg-events");
    const note = $("dbg-note");
    if (!summary || !list) return;
    if (!D) {
      summary.textContent = "Debug module failed to load (hosted/js/debug.js).";
      list.innerHTML = "";
      return;
    }
    const dump = D.dump();
    const errors = dump.events.filter((e) => /error|unhandled/i.test(e.kind));
    const lines = [
      `generated_at: ${dump.generated_at}`,
      `href: ${dump.href}`,
      `viewport: ${dump.viewport.w}×${dump.viewport.h} @${dump.viewport.dpr}`,
      `reducedMotion: ${dump.reducedMotion}  colorScheme: ${dump.colorScheme}`,
      `events: ${dump.eventCount}  errors: ${errors.length}`,
      dump.lastError ? `lastError: ${JSON.stringify(dump.lastError)}` : "lastError: none",
      dump.lastWs ? `lastWs: ${JSON.stringify(dump.lastWs)}` : "lastWs: none",
      "",
      "Pull this from another session:",
      "  GET  /api/debug/bundle",
      "  POST /api/debug/client   (this page's Export / Push)",
      "  window.__OBSERVATORY_DEBUG__.export()",
    ];
    summary.textContent = lines.join("\n");
    const newest = dump.events.slice().reverse();
    list.innerHTML = newest.map((ev) => {
      const cls = /error|unhandled/i.test(ev.kind) ? "is-err" : "";
      const gloss = D.explain(ev);
      return `<li class="${cls}"><code>${Obs.esc(ev.t)}</code> <strong>${Obs.esc(ev.kind)}</strong>
        <span>${Obs.esc(gloss)}</span></li>`;
    }).join("") || "<li>Ring is empty.</li>";
    if (note) {
      note.textContent = errors.length
        ? `${errors.length} error-class event${errors.length === 1 ? "" : "s"} in the ring — read the red rows.`
        : "No error-class events in the ring.";
    }
  }

  function bindInboxQueue(ops) {
    const form = $("inbox-form");
    const setup = $("inbox-setup");
    const ready = !!(ops && ops.configured);
    if (setup) {
      setup.hidden = ready;
      if (!ready) {
        setup.textContent = "Set MAILROOM_PIPELINE_URL and MAILROOM_PIPELINE_TOKEN to queue documents into llm-mailroom.";
      }
    }
    if (!form) return;
    form.hidden = !ready;
    for (const field of form.querySelectorAll("input, button")) {
      field.disabled = !ready;
    }
  }

  async function submitInbox(ev) {
    ev.preventDefault();
    const form = $("inbox-form");
    const status = $("inbox-status");
    if (!form) return;
    const file = form.file && form.file.files && form.file.files[0];
    const matter = (form.matter_id && form.matter_id.value) || "";
    if (!file) {
      if (status) status.textContent = "Choose a file to queue.";
      return;
    }
    if (status) status.textContent = "Submitting…";
    try {
      const fd = new FormData();
      fd.append("file", file, file.name);
      if (matter) fd.append("matter_id", matter);
      const result = await Obs.api.inboxEnqueue(fd);
      const queued = result && (result.file || file.name);
      const uploadId = result && result.upload_id ? ` (${result.upload_id})` : "";
      if (status) status.textContent = queued ? `Queued ${queued}${uploadId}.` : "Queued.";
      form.reset();
    } catch (err) {
      if (status) status.textContent = err.message || String(err);
    }
  }

  async function exportSnapshot() {
    try {
      const snap = await Obs.api.snapshot();
      const blob = new Blob([JSON.stringify(snap, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "mailroom-snapshot.json";
      a.click();
      URL.revokeObjectURL(a.href);
      announce("Snapshot exported");
    } catch (err) {
      showAlert(`Snapshot export failed — ${err.message}`);
    }
  }

  function bindDebug() {
    const D = () => window.__OBSERVATORY_DEBUG__;
    const note = (msg) => { const el = $("dbg-note"); if (el) el.textContent = msg; };
    const on = (id, fn) => { const el = $(id); if (el) el.addEventListener("click", fn); };
    on("dbg-refresh", () => renderDebug());
    on("dbg-pull", async () => {
      if (!D()) return;
      try {
        const b = await D().pullServer();
        note(`Pulled server bundle — ${((b && b.server_logs) || []).length} server events, ${((b && b.client_reports) || []).length} client reports.`);
        renderDebug();
      } catch (e) { note("Pull failed — " + (e.message || e)); }
    });
    on("dbg-push", async () => {
      if (!D()) return;
      try {
        const r = await D().pushClient();
        note(r && r.ok ? `Pushed client dump. Stored reports: ${r.stored}.` : "Push returned " + JSON.stringify(r));
        renderDebug();
      } catch (e) { note("Push failed — " + (e.message || e)); }
    });
    on("dbg-export", async () => {
      if (!D()) return;
      try {
        await D().export();
        note("Exported: server bundle pulled and client dump posted. Copy dump if you need the JSON locally.");
        renderDebug();
      } catch (e) { note("Export failed — " + (e.message || e)); }
    });
    on("dbg-copy", async () => {
      if (!D()) return;
      const text = JSON.stringify(D().dump(), null, 2);
      try {
        await navigator.clipboard.writeText(text);
        note("Copied client dump to clipboard.");
      } catch (_e) {
        const sum = $("dbg-summary");
        if (sum) {
          sum.textContent = text;
          sum.focus();
          document.execCommand("selectAll");
        }
        note("Clipboard blocked — dump is in the summary box; copy manually.");
      }
    });
    on("dbg-clear", () => { if (D()) { D().clear(); renderDebug(); } });
    const verbose = $("dbg-verbose");
    if (verbose) {
      verbose.addEventListener("change", () => {
        if (D()) D().setVerbose(verbose.checked);
      });
    }
    window.addEventListener("obs-debug", () => {
      if (!$("view-debug") || $("view-debug").hidden) return;
      renderDebug();
    });
  }

  function boot() {
    tick();
    setInterval(tick, 1000);
    bindDebug();
    bindInboxQueue(null);
    const inboxForm = $("inbox-form");
    if (inboxForm) inboxForm.addEventListener("submit", submitInbox);
    const exportBtn = $("export-snapshot");
    if (exportBtn) exportBtn.addEventListener("click", exportSnapshot);

    const params = new URLSearchParams(location.search);
    if (params.get("debug") === "1" && window.__OBSERVATORY_DEBUG__) {
      window.__OBSERVATORY_DEBUG__.setVerbose(true);
      const box = $("dbg-verbose");
      if (box) box.checked = true;
    }

    for (const a of document.querySelectorAll(".view-nav a")) {
      a.addEventListener("click", (ev) => {
        ev.preventDefault();
        switchView(a.dataset.view);
      });
    }
    for (const radio of document.querySelectorAll("input[name=pipe-filter]")) {
      radio.addEventListener("change", () => {
        if (radio.checked) { filter = radio.value; renderBoard(); }
      });
    }
    const play = $("replay-play");
    if (play) {
      play.addEventListener("click", () => {
        if (!replay) return;
        if (replay.playing) pauseReplay();
        else playReplay();
      });
    }
    const step = $("replay-step");
    if (step) step.addEventListener("click", stepReplay);
    const stop = $("replay-stop");
    if (stop) stop.addEventListener("click", stopReplay);
    const dlg = $("inspect-dialog");
    if (dlg) dlg.addEventListener("close", closeInspect);

    window.addEventListener("hashchange", () => {
      switchView(location.hash.replace("#", "") || "pipeline");
    });

    document.addEventListener("keydown", (ev) => {
      if (ev.target && ["INPUT", "TEXTAREA", "SELECT"].includes(ev.target.tagName)) return;
      const map = { "1": "pipeline", "2": "review", "3": "history", "4": "matters", "5": "metrics", "6": "debug" };
      if (map[ev.key]) switchView(map[ev.key]);
    });

    const initial = params.get("debug") === "1"
      ? "debug"
      : (location.hash.replace("#", "") || "pipeline");
    switchView(initial);

    checkHealth().then((ok) => {
      if (!ok) return;
      applyPollInterval(meta && meta.poll_interval_s);
      refreshTraces();
      Obs.connectWS(onMessage);
      setTimeout(() => {
        if (!socketLive) startFallbackPolling();
      }, 8000);
    });
    setInterval(checkHealth, 10000);
  }

  document.addEventListener("DOMContentLoaded", boot);
  return { openInspect, startReplay, switchView };
})();
