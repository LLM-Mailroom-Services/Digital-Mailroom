/* The-Mailroom history view: timeline of all past runs.
 * Click REPLAY to animate a historical run through the pipeline,
 * showing each stage transition based on the actual span timing. */

const HistoryView = (() => {
  const listEl = document.getElementById("history-list");
  const refreshBtn = document.getElementById("history-refresh");
  let runsCache = [];

  function chip(run) {
    if (run.needs_human && run.stage !== "review") {
      return `<span class="chip stage-review">RECONSIDER</span>`;
    }
    let cls = "";
    if (["review"].includes(run.stage)) cls = "stage-review";
    else if (run.stage === "failed") cls = "stage-failed";
    else if (run.stage === "archived") cls = "stage-archived";
    else if (["judge_verify", "arbiter"].includes(run.stage)) cls = "stage-judge";
    else if (["report", "catalog", "archive"].includes(run.stage)) cls = "stage-report";
    else if (["extract", "retry_extract", "boss"].includes(run.stage)) cls = "stage-extract";
    else if (["inbox", "intake", "classify", "retry_classify", "review_classify", "unknown"].includes(run.stage)) cls = "stage-intake";
    return `<span class="chip ${cls}">${Mailroom.esc((run.stage || "unknown").toUpperCase())}</span>`;
  }

  function verdictChip(run) {
    if (!run.verdict) return `<span class="chip">—</span>`;
    return `<span class="chip verdict-${Mailroom.esc(run.verdict)}">${Mailroom.esc(run.verdict)}</span>`;
  }

  function renderHistory(runs) {
    if (!runs.length) {
      listEl.innerHTML = `<div class="hint mono">NO RUNS IN THE RECENT WINDOW</div>`;
      return;
    }
    // Group by hour bucket for the timeline
    const buckets = {};
    for (const r of runs) {
      const ts = r.updated_at || r.created_at;
      if (!ts) continue;
      const d = new Date(ts);
      // V-15: buckets keyed by epoch (numeric) so sort is by TIME, not by
      // string — localeCompare on "M/D HH:00" mis-ordered across days
      // ("8/9 23:00" after "8/10 01:00") and the .slice(0,12) could drop the
      // genuinely newest buckets.
      const epochKey = Math.floor(d.getTime() / 3600000);
      buckets[epochKey] = (buckets[epochKey] || 0) + 1;
    }
    const bucketEntries = Object.entries(buckets)
      .sort((a, b) => Number(b[0]) - Number(a[0]))
      .slice(0, 12)
      .map(([epoch, count]) => {
        const d = new Date(Number(epoch) * 3600000);
        const label = `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,"0")}:00`;
        return [label, count];
      });

    let html = "";
    if (bucketEntries.length) {
      const maxCount = Math.max(1, ...bucketEntries.map(([,v]) => v));
      html += `<div class="tile wide" style="margin-bottom:14px">
        <div class="tile-label" style="margin:0 0 8px">RUNS PER HOUR</div>
        ${bucketEntries.map(([k, v]) =>
          `<div class="bar-row">
            <span class="bar-label">${Mailroom.esc(k)}</span>
            <span class="bar-track"><span class="bar-fill" style="width:${Math.round((v / maxCount) * 100)}%;background:var(--blue-light)"></span></span>
            <span class="bar-num">${v}</span>
          </div>`
        ).join("")}
      </div>`;
    }

    // Per-run rows with REPLAY button
    html += runs.map((r) => {
      const when = Mailroom.fmt.dateTime(r.updated_at || r.created_at);
      const cost = r.cost_usd ? `$${Number(r.cost_usd).toFixed(4)}` : "—";
      const toks = r.total_tokens ? Number(r.total_tokens).toLocaleString() : "—";
      return `<div class="run-row" data-trace="${Mailroom.esc(r.trace_id)}" style="grid-template-columns:minmax(0,2fr) 96px 130px 100px 90px 90px 120px">
        <span class="run-file">${Mailroom.esc(r.filename || r.trace_id)}</span>
        ${chip(r)}
        ${verdictChip(r)}
        <span style="color:var(--paper-dim)">${Mailroom.esc(r.doc_type || "—")}${r.doc_subclass || r.contract_subtype ? ` / ${Mailroom.esc(r.doc_subclass || r.contract_subtype)}` : ""}</span>
        <span style="color:var(--gold)">${cost}</span>
        <span style="color:var(--paper-dim)">${toks}</span>
        <span class="run-when" style="display:flex;gap:6px;align-items:center;justify-content:flex-end">
          <span style="color:var(--gray)">${when}</span>
          <button class="px-btn history-replay" data-trace="${Mailroom.esc(r.trace_id)}" style="padding:2px 8px;font-size:10px">REPLAY</button>
        </span>
      </div>`;
    }).join("");

    listEl.innerHTML = html;

    // Wire replay buttons
    for (const btn of listEl.querySelectorAll(".history-replay")) {
      btn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        replayRun(btn.dataset.trace);
      });
    }
    // Wire inspect on row click
    for (const row of listEl.querySelectorAll(".run-row")) {
      row.addEventListener("click", (ev) => {
        if (ev.target.closest(".history-replay")) return;
        Inspector.open(row.dataset.trace);
      });
    }
  }

  async function replayRun(traceId) {
    try {
      ConsoleView.banner(`REPLAYING ${traceId}`);
      const data = await Mailroom.api.run(traceId);
      if (data && data.error) throw new Error(data.error);
      Floor.replay(data);
      // Switch to floor view
      const tab = document.querySelector('.tab[data-view="floor"]');
      if (tab) tab.click();
    } catch (err) {
      ConsoleView.log(`replay failed: ${err.message || err}`, "c-bad");
      Mailroom.showError(`replay: ${err.message || err}`);
    }
  }

  async function refresh() {
    listEl.innerHTML = `<div class="hint mono">LOADING RUN HISTORY FROM LANGFUSE…</div>`;
    try {
      const data = await Mailroom.api.traces(604800, 200);
      runsCache = data.runs || [];
      renderHistory(runsCache);
      return data;
    } catch (err) {
      listEl.innerHTML = `<div class="insp-error">history unavailable — ${Mailroom.esc(err.message || String(err))}</div>`;
      throw err;
    }
  }

  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      ConsoleView.log("refreshing history…", "c-dim");
      refresh().catch((e) => {
        Mailroom.showError(`history: ${e.message || e}`);
        ConsoleView.log(`history refresh failed: ${e.message || e}`, "c-bad");
      });
    });
  }

  return { refresh, replayRun };
})();