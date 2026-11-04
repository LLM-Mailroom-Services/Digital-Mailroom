"""Shared service status strip for the board and run watcher (published snapshots only)."""

SERVICES_CSS = r"""
.svc { display: flex; flex-wrap: wrap; gap: 6px 14px; padding: 8px 10px; margin: 0 0 12px; font-size: 12px;
  border: 1px solid var(--teal); border-radius: 4px; background: rgba(14,116,144,0.18); }
.svc .s { white-space: nowrap; } .svc .s.ok::before { content: "● "; color: var(--teal); }
.svc .s.warn::before { content: "● "; color: var(--gold); }
.svc .s.fail { font-weight: 700; color: var(--gold); } .svc .s.fail::before { content: "✖ "; color: var(--gold); }
.svc .s.skipped { color: #b6c8d8; } .svc .s.skipped::before { content: "○ "; }
.svc .note { color: #b6c8d8; width: 100%; } .svc.stale { border-style: dashed; }
"""

SERVICES_JS = r"""
function services(sv) {
  const el = document.getElementById("svc");
  if (!sv) { el.className = "svc"; el.innerHTML = `<span class="note">no service snapshot yet — run <code>sandbox doctor --publish</code></span>`; return; }
  el.className = "svc" + (sv.stale ? " stale" : "");
  const rows = (sv.services || []).map(r => `<span class="s ${esc(r.state)}" title="${esc(r.detail)}${r.hint ? " → " + esc(r.hint) : ""}">${esc(r.name)}</span>`).join("");
  const age = Math.round(sv.age_s || 0);
  const scope = sv.live ? "live probes" : "offline checks";
  const note = (sv.stale ? `STALE (${Math.round(age / 60)}m old) — re-run sandbox doctor --publish · ` : "") + `${esc(sv.profile)} · ${scope} · ${age}s ago`;
  el.innerHTML = rows + `<span class="note">${note}</span>`;
}
"""

SERVICES_HTML = r"""
<div class="svc" id="svc"><span class="note">no service snapshot yet — run <code>sandbox doctor --publish</code></span></div>"""
