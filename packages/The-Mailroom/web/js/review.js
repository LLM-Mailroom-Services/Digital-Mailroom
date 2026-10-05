/* The-Mailroom review queue: runs waiting on a human (needs_human). */

const ReviewView = (() => {
  const listEl = document.getElementById("review-queue");
  // A reviewer typing notes / editing extracted_data must not lose it to the
  // 30 s background refresh (the old refresh replaced innerHTML wholesale).
  let dirty = false;
  listEl.addEventListener("input", () => { dirty = true; });
  listEl.addEventListener("change", () => { dirty = true; });

  function busy() {
    const active = document.activeElement;
    return dirty || !!(active && listEl.contains(active) &&
      active.matches("input, textarea, select"));
  }

  function chip(run) {
    if (run.needs_reconsideration) return `<span class="chip stage-review">RECONSIDER</span>`;
    if (run.stage === "review") return `<span class="chip stage-review">REVIEW</span>`;
    if (run.stage === "failed") return `<span class="chip stage-failed">FAILED</span>`;
    return `<span class="chip">${Mailroom.esc((run.stage || "unknown").toUpperCase())}</span>`;
  }

  function causeLine(run) {
    const causes = Array.isArray(run.review_causes) ? run.review_causes : [];
    const chips = causes
      .map((c) => `<span class="chip stage-review">${Mailroom.esc(String(c).replaceAll("_", " "))}</span>`)
      .join(" ");
    const why = run.escalation_reason
      ? `<div style="color:var(--amber);margin-top:4px">why: ${Mailroom.esc(run.escalation_reason)}</div>`
      : "";
    return `${chips ? `<div style="margin-top:4px">${chips}</div>` : ""}${why}`;
  }

  function verdictChip(run) {
    if (!run.verdict) return "";
    return `<span class="chip verdict-${Mailroom.esc(run.verdict)}">${Mailroom.esc(run.verdict)}</span>`;
  }

  function render(runs, producerHint) {
    if (!runs.length) {
      listEl.innerHTML = `${producerHint || ""}<div class="hint mono">REVIEW SIDING EMPTY — NO RUNS WAITING ON A HUMAN OR FLAGGED FOR RECONSIDERATION</div>`;
      return;
    }
    listEl.innerHTML = (producerHint || "") + runs
      .map(
        (r) => `<div class="session-card run-row-solo" data-trace="${Mailroom.esc(r.trace_id)}">
        <div class="session-head">
          <span class="ses-id">${Mailroom.esc(r.filename || r.trace_id)}</span>
          ${chip(r)}
          ${verdictChip(r)}
          <span class="ses-count">${Mailroom.fmt.time(r.created_at)}</span>
        </div>
        <div class="session-runs" style="padding:8px 10px">
          <div style="color:var(--paper-dim)">doc: <span style="color:var(--paper)">${Mailroom.esc(r.doc_type || "—")}${r.doc_subclass || r.contract_subtype ? ` / ${Mailroom.esc(r.doc_subclass || r.contract_subtype)}` : ""}</span>${r.doc_id ? ` · id ${Mailroom.esc(r.doc_id)}` : ""}</div>
          ${causeLine(r)}
          ${
            r.failure_class
              ? `<div style="color:var(--red-light);margin-top:4px">fail: ${Mailroom.esc(String(r.failure_class).replaceAll("_", " "))}</div>`
              : ""
          }
          ${
            r.error_message
              ? `<div style="color:var(--red-light);margin-top:4px">error: ${Mailroom.esc(r.error_message)}</div>`
              : ""
          }
          <div style="color:var(--gray-dim);margin-top:4px">
            cls ${Mailroom.fmt.conf(r.classification_confidence)} · ext ${Mailroom.fmt.conf(
              r.extraction_confidence,
            )} · ${r.llm_call_count ?? 0} calls · ${Mailroom.fmt.tokens(r.total_tokens)} tok · ${Mailroom.fmt.cost(r.cost_usd)}
          </div>
          ${Mailroom.reviewPanel(r)}
        </div>
      </div>`,
      )
      .join("");
    for (const card of listEl.querySelectorAll(".session-card")) {
      card.addEventListener("click", () => {
        Inspector.open(card.dataset.trace);
      });
    }
    Mailroom.bindReviewForms(listEl, { onDone: () => { dirty = false; refresh({ force: true }); } });
  }

  async function producerBanner() {
    try {
      const ctx = await Mailroom.api.reviewContext();
      if (ctx && ctx.configured === false) {
        return `<div class="hint mono review-setup">${Mailroom.esc(ctx.error || "Set MAILROOM_PIPELINE_URL + MAILROOM_PIPELINE_TOKEN to resolve reviews.")}</div>`;
      }
    } catch (_err) { /* probe is best-effort */ }
    return "";
  }

  async function refresh(opts = {}) {
    if (!opts.force && opts.background && busy()) return null;
    dirty = false;
    listEl.innerHTML = `<div class="hint mono">LOADING REVIEW QUEUE FROM LANGFUSE…</div>`;
    try {
      const [data, hint] = await Promise.all([Mailroom.api.reviewQueue(), producerBanner()]);
      render(data.runs || [], hint);
      return data;
    } catch (err) {
      const hint = await producerBanner().catch(() => "");
      listEl.innerHTML = `${hint}<div class="insp-error">review queue unavailable — ${Mailroom.esc(err.message || String(err))}</div>`;
      throw err;
    }
  }

  return { refresh };
})();
