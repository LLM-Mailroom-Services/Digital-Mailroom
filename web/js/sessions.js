/* The-Mailroom sessions view: matters (Langfuse sessions) with their runs. */

const SessionsView = (() => {
  const listEl = document.getElementById("sessions-list");

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

  function renderSessions(sessions) {
    if (!sessions.length) {
      listEl.innerHTML = `<div class="hint mono">NO SESSIONS IN THE RECENT WINDOW</div>`;
      return;
    }
    listEl.innerHTML = sessions
      .map((s) => {
        const runs = s.runs || [];
        const rows = runs
          .map((r) => `<div class="run-row" data-trace="${Mailroom.esc(r.trace_id)}">
            <span class="run-file">${Mailroom.esc(r.filename || r.trace_id)}</span>
            ${chip(r)}
            <span style="color:var(--paper-dim)">${Mailroom.esc(r.doc_type || "—")}</span>
            ${verdictChip(r)}
            <span class="run-when">${Mailroom.fmt.time(r.created_at)}</span>
          </div>`)
          .join("");
        const extra = runs.length < (s.trace_count || 0)
          ? `<div class="hint mono">… ${s.trace_count - runs.length} more traces</div>`
          : "";
        return `<div class="session-card">
          <div class="session-head">
            <span class="ses-id">${Mailroom.esc(s.id || "session")}</span>
            <span style="color:var(--paper-dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${Mailroom.esc(s.name || "matter")}</span>
            <span class="ses-count">${s.trace_count} traces · ${Mailroom.fmt.dateTime(s.updated_at)}</span>
          </div>
          <div class="session-runs">${rows}</div>
          ${extra}
        </div>`;
      })
      .join("");

    for (const row of listEl.querySelectorAll(".run-row")) {
      row.addEventListener("click", () => {
        Inspector.open(row.dataset.trace);
      });
    }
  }

  async function refresh() {
    listEl.innerHTML = `<div class="hint mono">LOADING SESSIONS FROM LANGFUSE…</div>`;
    try {
      const data = await Mailroom.api.sessions(50);
      renderSessions(data.sessions || []);
      return data;
    } catch (err) {
      listEl.innerHTML = `<div class="insp-error">sessions unavailable — ${Mailroom.esc(err.message || String(err))}</div>`;
      throw err;
    }
  }

  return { refresh };
})();
