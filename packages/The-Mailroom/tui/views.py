"""Rich renderers for the mailroom-tui console.

All renderers are pure functions over payloads — the same shapes the web API
serves (Langfuse-derived for trace views; Hub-derived for the corpus views).
No rendering function ever touches the network; fetch happens in
``mailroom_console`` / ``commands`` and failures render as explicit closed
states.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Optional

from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tui.corpus import SlimRow

# Error ring shared by the fetch helpers; re-exported from
# ``mailroom_console`` so legacy imports keep working.
LAST_ERRORS: "deque[str]" = deque(maxlen=80)

STAGE_ORDER = [
    "inbox", "intake", "classify", "retry_classify", "review_classify",
    "extract", "retry_extract", "judge_verify", "arbiter",
    "boss", "review", "report", "catalog", "archive", "archived", "failed",
]

STAGE_STYLE = {
    "inbox": "grey50", "intake": "grey70", "classify": "cyan",
    "retry_classify": "cyan", "extract": "yellow", "retry_extract": "yellow",
    "judge_verify": "magenta", "arbiter": "magenta",
    "boss": "red", "review": "bright_yellow", "report": "green",
    "catalog": "green", "archive": "green", "archived": "bright_green",
    "failed": "bright_red", "unknown": "grey50",
}

STATION_BY_STAGE = {
    "inbox": "INBOX", "intake": "Sorter", "classify": "Sorter",
    "retry_classify": "Sorter", "review_classify": "Sorter",
    "extract": "Specialist", "retry_extract": "Specialist",
    "judge_verify": "Judge", "arbiter": "Arbiter",
    "boss": "Boss", "review": "Review", "report": "Reporter",
    "catalog": "Archive", "archive": "Archive", "archived": "Archive",
    "failed": "Failed", "unknown": "?",
}


def _fmt(v, spec="{:.2f}") -> str:
    if v is None:
        return "-"
    try:
        return spec.format(float(v))
    except (TypeError, ValueError):
        return str(v)


def _money(v, spec="{:.4f}") -> str:
    if v is None:
        return "-"
    try:
        return "$" + spec.format(float(v))
    except (TypeError, ValueError):
        return str(v)


def banner(station: str, action: str = "Beginning") -> str:
    return f"*** {action} station: {station} ***"


def runs_to_banners(prev: dict[str, dict], runs: list[dict], log: deque) -> None:
    """Emit AgentLab-style banners when runs arrive or advance stages."""
    now = {r["trace_id"]: r for r in runs}
    for tid, run in now.items():
        old = prev.get(tid)
        if old is None:
            log.append(f"{banner(STATION_BY_STAGE.get(run['stage'], '?'), 'Entering')} "
                       f"{run.get('filename') or tid} [{run.get('stage')}]")
        elif old.get("stage") != run.get("stage"):
            log.append(f"{banner(STATION_BY_STAGE.get(run['stage'], '?'), 'Moving to')} "
                       f"{run.get('filename') or tid} [{run.get('stage')}]")
        if run.get("verdict") and old and old.get("verdict") != run.get("verdict"):
            log.append(f"*** Judge verdict: {run['verdict']} — {run.get('filename')} ***")
    gone = set(prev) - set(now)
    for tid in sorted(gone):
        log.append(f"*** Run left the window: {tid} ***")


def _verdict_style(verdict: str) -> str:
    if verdict == "CORRECT":
        return "bright_green"
    if verdict == "PARTIAL":
        return "yellow"
    if verdict == "MISS":
        return "bright_red"
    return "dim"


def floor_table(runs: list[dict]) -> Table:
    table = Table(title=None, box=None, pad_edge=False, expand=True)
    table.add_column("FILE", style="bold white", no_wrap=True, max_width=34)
    table.add_column("STATION", style="grey70", no_wrap=True, min_width=10)
    table.add_column("DOC TYPE", style="dim", no_wrap=True, max_width=16)
    table.add_column("CLS", justify="right")
    table.add_column("EXT", justify="right")
    table.add_column("VERDICT", justify="center", no_wrap=True, min_width=7)
    table.add_column("QUAL", justify="right")
    table.add_column("COST", justify="right", no_wrap=True)
    table.add_column("ROUTE", style="grey35", max_width=30)
    ordered = sorted(runs, key=lambda r: (STAGE_ORDER.index(r.get("stage"))
                                          if r.get("stage") in STAGE_ORDER else 99))
    for r in ordered:
        verdict = r.get("verdict") or "-"
        route = ">".join((r.get("routing_path") or [])[:5])
        table.add_row(
            (r.get("filename") or r["trace_id"])[:34],
            STATION_BY_STAGE.get(r.get("stage"), "?"),
            (r.get("doc_type") or "-").replace("_", " "),
            _fmt(r.get("classification_confidence")),
            _fmt(r.get("extraction_confidence")),
            Text(verdict, style=_verdict_style(verdict)),
            _fmt(r.get("quality")),
            _money(r.get("cost_usd"), "{:.4f}"),
            route,
        )
    return table


def review_table(runs: list[dict]) -> Table:
    table = Table(
        title="REVIEW SIDING — WAITING ON A HUMAN  (resolve: mailroom-tui --resolve TRACE --decision approved)",
        box=None, pad_edge=False, expand=True,
    )
    table.add_column("FILE", style="bold white", no_wrap=True, max_width=34)
    table.add_column("DOC TYPE", style="dim")
    table.add_column("CLS", justify="right")
    table.add_column("EXT", justify="right")
    table.add_column("VERDICT", justify="center", no_wrap=True, min_width=7)
    table.add_column("WHY", style="yellow", max_width=50)
    for r in runs:
        verdict = r.get("verdict") or "-"
        table.add_row(
            (r.get("filename") or r["trace_id"])[:34],
            (r.get("doc_type") or "-").replace("_", " "),
            _fmt(r.get("classification_confidence")),
            _fmt(r.get("extraction_confidence")),
            Text(verdict, style=_verdict_style(verdict)),
            r.get("failure_class")
            or r.get("escalation_reason")
            or (", ".join(r.get("review_causes") or []))
            or r.get("review_decision")
            or r.get("error_message")
            or "-",
        )
    return table


def metrics_table(m: dict) -> Table:
    table = Table(title="METRICS", box=None, pad_edge=False, expand=True)
    table.add_column("METRIC", style="bold")
    table.add_column("VALUE", justify="right")
    rows = [
        ("total docs", m.get("total_docs")),
        ("archived", m.get("archived")),
        ("review", m.get("review")),
        ("reconsider", m.get("reconsideration")),
        ("failed", m.get("failed")),
        ("in flight", m.get("in_flight")),
        ("llm calls", m.get("llm_calls")),
        ("total cost", _money(m.get("total_cost_usd"), "{:.2f}")),
        ("total tokens", m.get("total_tokens")),
        ("avg cost/doc", _money(m.get("avg_cost_usd"), "{:.4f}")),
        ("avg latency", "-" if m.get("avg_latency_s") is None else f"{m['avg_latency_s']:.1f}s"),
        ("p95 gen latency", "-" if m.get("p95_generation_latency_s") is None else f"{m['p95_generation_latency_s']:.1f}s"),
        ("avg quality", "-" if m.get("avg_quality") is None else f"{m['avg_quality']:.2f}"),
    ]
    extra_metrics = (
        ("verified precision", "avg_extraction_verified_precision"),
        ("topic accuracy", "avg_content_topic_accuracy"),
        ("topic f1", "avg_content_topic_f1_macro"),
        ("sentiment accuracy", "avg_sentiment_accuracy"),
        ("sentiment f1", "avg_sentiment_f1_macro"),
        ("maud question acc", "avg_maud_question_accuracy"),
        ("maud question macro", "avg_maud_question_macro_accuracy"),
        ("maud clause", "avg_maud_clause_presence"),
        ("maud valid class", "avg_maud_valid_class_rate"),
        ("maud category", "avg_maud_category_accuracy"),
    )
    for label, key in extra_metrics:
        value = m.get(key)
        if value is not None:
            rows.append((label, f"{value:.4f}" if isinstance(value, float) else value))
    for name, value in rows:
        table.add_row(name, "-" if value is None else str(value))
    verdicts = m.get("verdict_counts") or {}
    if verdicts:
        table.add_section()
        for k, v in sorted(verdicts.items()):
            table.add_row(f"verdict {k}", str(v))
    return table


def inspect_panels(run: dict) -> list[Panel]:
    title = run.get("filename") or run.get("trace_id") or "run"
    head = Text()
    head.append(f"{title}\n", style="bold white")
    head.append(f"trace {run.get('trace_id')} · {run.get('stage')} · "
                f"{run.get('doc_type') or 'no doc type'}"
                f"{(' / ' + (run.get('doc_subclass') or run.get('contract_subtype'))) if (run.get('doc_subclass') or run.get('contract_subtype')) else ''}"
                f" · env {run.get('environment') or '-'}\n",
                style="grey50")
    if run.get("verdict"):
        head.append(f"verdict {run['verdict']} · quality {_fmt(run.get('quality'))}\n", style="bold")
    kv = Table(box=None, pad_edge=False)
    kv.add_column("FIELD", style="dim")
    kv.add_column("VALUE")
    labels = {
        "doc_id": "DOC ID",
        "doc_subclass": "SUBCLASS",
        "contract_subtype": "CONTRACT SUBTYPE",
        "expected_hf_class": "EXPECTED CLASS",
        "expected_subclass": "EXPECTED SUBCLASS",
        "intake_messy": "INTAKE MESSY",
        "intake_changed": "INTAKE CHANGED",
        "intake_method": "INTAKE METHOD",
        "intake_chars": "INTAKE CHARS",
        "failure_class": "FAILURE CLASS",
        "run_aborted": "ABORTED",
    }
    for key in ("doc_id", "session_id", "matter_id", "user_id", "release", "attempt", "environment",
                "doc_subclass", "contract_subtype", "expected_hf_class", "expected_subclass",
                "intake_messy", "intake_changed", "intake_method", "intake_chars",
                "classification_confidence", "extraction_confidence", "latency",
                "llm_call_count", "total_tokens", "cost_usd", "created_at",
                "escalation_reason", "failure_class", "run_aborted", "error_message"):
        value = run.get(key)
        if value is not None:
            kv.add_row(labels.get(key, key), str(value))
    panels = [Panel(Group(head, kv), title="RUN", border_style="blue")]

    spans = run.get("spans") or []
    st = Table(box=None, pad_edge=False)
    st.add_column("SPAN", style="bold")
    st.add_column("TYPE", style="cyan")
    st.add_column("STATUS")
    st.add_column("LATENCY", justify="right")
    st.add_column("ERROR", style="red", max_width=40)
    for s in spans:
        status = s.get("status") or "?"
        style = "bright_green" if status == "SUCCESS" else (
            "bright_red" if status == "ERROR" else "yellow")
        label = s.get("name") or "?"
        if s.get("is_root"):
            label = f"{label} [root]"
        st.add_row(label, (s.get("observation_type") or "SPAN"),
                   Text(status, style=style),
                   _fmt(s.get("latency"), "{:.1f}s"),
                   (s.get("error_message") or "")[:40])
    panels.append(Panel(st, title=f"OBSERVATIONS ({len(spans)})", border_style="blue"))

    gens = run.get("generations") or []
    gt = Table(box=None, pad_edge=False)
    gt.add_column("CALL", style="bold")
    gt.add_column("MODEL")
    gt.add_column("TOKENS IN", justify="right")
    gt.add_column("OUT", justify="right")
    gt.add_column("COST", justify="right")
    gt.add_column("LATENCY", justify="right")
    for g in gens:
        gt.add_row(g.get("name") or "-", g.get("model") or "-",
                   str(g.get("usage_input_tokens") or 0),
                   str(g.get("usage_output_tokens") or 0),
                   _money(g.get("cost_usd"), "{:.4f}"),
                   _fmt(g.get("latency"), "{:.1f}s"))
    panels.append(Panel(gt, title=f"LLM GENERATIONS ({len(gens)})", border_style="blue"))

    scores = run.get("scores") or {}
    entries: list[tuple[str, Any]] = []
    if isinstance(scores, list):
        for s in scores:
            if isinstance(s, dict) and s.get("name") is not None:
                entries.append((str(s.get("name")), s.get("value")))
    elif isinstance(scores, dict):
        entries = sorted(scores.items())
    if entries:
        sct = Table(box=None, pad_edge=False)
        sct.add_column("SCORE", style="bold")
        sct.add_column("VALUE")
        for name, value in entries:
            sct.add_row(name, str(value))
        panels.append(Panel(sct, title="SCORES", border_style="blue"))
    return panels


def sessions_table(payload: dict) -> Table:
    table = Table(title="MATTERS / SESSIONS", box=None, pad_edge=False, expand=True)
    table.add_column("SESSION", style="bold white", no_wrap=True, max_width=28)
    table.add_column("TRACES", justify="right")
    table.add_column("UPDATED", style="dim")
    table.add_column("LATEST", max_width=50)
    for s in payload.get("sessions") or []:
        latest = ""
        runs = s.get("runs") or []
        if runs:
            r = runs[0]
            latest = f"{(r.get('filename') or r.get('trace_id') or '')[:28]} [{r.get('stage') or '-'}]"
        table.add_row(
            str(s.get("name") or s.get("id") or "matter")[:28],
            str(s.get("trace_count") or len(runs)),
            str(s.get("updated_at") or "-")[:19],
            latest or "-",
        )
    return table


def debug_panel(error_lines: Optional[list[str]] = None) -> Panel:
    lines = list(error_lines or LAST_ERRORS)[-18:] or ["(no recorded fetch/WS errors)"]
    body = Group(*[Text(line, style="bright_red" if "Error" in line or "error" in line else "grey70")
                   for line in lines])
    return Panel(body, title=f"DEBUG RING ({len(error_lines or LAST_ERRORS)})",
                 border_style="red")


def status_header(connected: bool, count: int, api_base: str = "",
                  pipeline: Optional[dict] = None) -> Panel:
    state = "MAILROOM LIVE — watching Langfuse" if connected else \
        "MAILROOM CLOSED — no Langfuse connection"
    style = "bright_green" if connected else "bright_red"
    extra = ""
    if pipeline and pipeline.get("configured"):
        extra = (f"   watcher: {pipeline.get('watcher') or '?'} "
                 f"  inbox: {pipeline.get('inbox_pending')}")
        if pipeline.get("watcher") != "live":
            style = "yellow" if connected else style
    return Panel(Text(f"THE MAILROOM TUI   {state}   runs: {count}   "
                      f"source: {api_base}{extra}", style=style),
                 border_style=style)


# ---------------------------------------------------------------------------
# Corpus renderers
# ---------------------------------------------------------------------------

def corpus_table(rows: list[SlimRow], title: str = "MAILROOM-DATASET") -> Table:
    table = Table(title=title, box=None, pad_edge=False, expand=True)
    table.add_column("FILE", style="bold white", no_wrap=True, max_width=40)
    table.add_column("SPLIT", style="dim", no_wrap=True)
    table.add_column("DOC CLASS", style="cyan")
    table.add_column("SUBCLASS", style="yellow")
    table.add_column("SHA256", style="grey50", no_wrap=True, max_width=12)
    table.add_column("CHARS", justify="right")
    for r in rows:
        table.add_row(
            r.filename[:40],
            r.split,
            (r.doc_class or "-").replace("_", " "),
            (r.doc_subclass or "-").replace("_", " "),
            (r.sha256 or "-")[:12],
            "-" if r.chars is None else str(r.chars),
        )
    return table


def corpus_stats_table(split_counts: dict[str, int],
                       class_counts: dict[str, int]) -> Table:
    split_table = Table(title="SPLITS", box=None, pad_edge=False, expand=True)
    split_table.add_column("SPLIT", style="bold")
    split_table.add_column("ROWS", justify="right")
    for split, count in split_counts.items():
        split_table.add_row(split, str(count))
    class_table = Table(title="DOC CLASSES", box=None, pad_edge=False, expand=True)
    class_table.add_column("DOC CLASS", style="cyan")
    class_table.add_column("ROWS", justify="right")
    for cls, count in class_counts.items():
        class_table.add_row(cls.replace("_", " "), str(count))
    return Group(
        split_table,
        class_table,
    )


def corpus_detail_panels(slim: SlimRow, row: Optional[dict],
                         gt: Optional[dict]) -> list[Panel]:
    """doc_text + provenance panel and the ground-truth field panel."""
    head = Text()
    head.append(f"{slim.filename}\n", style="bold white")
    head.append(f"split {slim.split} · index {slim.index} · "
                f"{slim.doc_class or 'no class'}"
                f"{(' / ' + slim.doc_subclass) if slim.doc_subclass else ''}"
                f" · sha256 {slim.sha256 or '-'}\n", style="grey50")
    if row is None:
        body = Panel(
            Text("full row unavailable — Hub unreachable (corpus closed)",
                 style="bright_red"),
            title=f"CORPUS DOC — {slim.filename}", border_style="red")
        return [body]
    doc_text = row.get("doc_text") or ""
    if len(doc_text) > 6000:
        doc_text = doc_text[:6000] + "\n… [truncated — full text lives on the Hub]"
    text_panel = Panel(
        Text(doc_text, style="grey85"),
        title=f"DOC TEXT ({len(row.get('doc_text') or '')} chars)",
        border_style="blue")
    panels: list[Panel] = [Panel(Group(head, text_panel), title="CORPUS DOC",
                                 border_style="blue")]
    if gt:
        kv = Table(box=None, pad_edge=False)
        kv.add_column("FIELD", style="dim")
        kv.add_column("VALUE", max_width=70)
        for key in sorted(gt):
            if key in ("filename",):
                continue
            value = gt[key]
            if value is None or value == "":
                continue
            kv.add_row(key.replace("_", " "), str(value)[:70])
        panels.append(Panel(kv, title="GROUND TRUTH", border_style="green"))
    return panels


# ---------------------------------------------------------------------------
# Constellation repo renderers
# ---------------------------------------------------------------------------

def repos_table(repos: list[dict]) -> Table:
    table = Table(title="LLM-MAILROOM CONSTELLATION", box=None, pad_edge=False,
                  expand=True)
    table.add_column("REPO", style="bold white", no_wrap=True)
    table.add_column("ROLE", style="dim", no_wrap=True)
    table.add_column("DIST", style="grey50", no_wrap=True)
    table.add_column("DESCRIPTION", max_width=70)
    for r in repos:
        desc = r.get("live_description") or r.get("blurb") or ""
        table.add_row(r["name"], r.get("role", "-"), r.get("dist", "-"),
                      desc[:70])
    return table


def repo_panel(repo: dict, meta: Optional[dict]) -> Panel:
    body = Text()
    body.append(f"{repo['name']}\n", style="bold white")
    body.append(f"{repo['url']}\n", style="cyan")
    if meta and meta.get("description"):
        body.append(f"{meta['description']}\n\n", style="grey85")
    else:
        body.append(f"{repo.get('blurb') or ''}\n\n", style="grey85")
    kv = Table(box=None, pad_edge=False)
    kv.add_column("FIELD", style="dim")
    kv.add_column("VALUE")
    kv.add_row("role", repo.get("role", "-"))
    kv.add_row("dist", repo.get("dist", "-"))
    if meta:
        for key, label in (("stars", "stars"), ("language", "language"),
                           ("updated_at", "updated"),
                           ("homepage", "homepage")):
            value = meta.get(key)
            if value:
                kv.add_row(label, str(value))
        if meta.get("archived"):
            kv.add_row("archived", "yes", )
    else:
        kv.add_row("live metadata", "unavailable (offline or rate-limited)")
    return Panel(Group(body, kv), title="REPOSITORY", border_style="blue")


def empty_hint(message: str) -> Panel:
    return Panel(Align.center(Text(message, style="grey50")), border_style="grey35")