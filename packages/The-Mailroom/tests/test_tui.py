"""TUI console tests: banner/table building from payloads (no live server)."""

import json
from collections import deque
from pathlib import Path

import pytest
from rich.console import Console

from tui import commands as cmds
from tui import repos as repos_mod
from tui.corpus import CorpusClosed, CorpusClient
from tui.mailroom_console import (
    LAST_ERRORS,
    STATION_BY_STAGE,
    WINDOW_S,
    banner,
    debug_panel,
    fetch_floor_runs,
    fetch_list,
    floor_table,
    inspect_panels,
    metrics_table,
    post_json,
    review_table,
    runs_to_banners,
    sessions_table,
)
from tui.views import corpus_stats_table, corpus_table, repos_table

ROOT = Path(__file__).resolve().parent.parent

RUN = {
    "trace_id": "demo-x",
    "filename": "contract_03_service_agreement.pdf",
    "stage": "archived",
    "doc_type": "contract",
    "classification_confidence": 0.98,
    "extraction_confidence": 0.96,
    "verdict": "CORRECT",
    "quality": 0.97,
    "cost_usd": 0.0496,
    "routing_path": ["intake", "classify", "extract", "report", "catalog", "archive"],
}


def render(renderable) -> str:
    console = Console(width=120, force_terminal=True, record=True)
    console.print(renderable)
    return console.export_text()


def test_banner_format():
    assert banner("Sorter") == "*** Beginning station: Sorter ***"
    assert banner("Review siding", "Moving to") == "*** Moving to station: Review siding ***"


def test_runs_to_banners_arrival_and_advance():
    log = deque()
    runs_to_banners({}, [RUN], log)
    assert any("Entering station: Archive" in line for line in log)

    advanced = dict(RUN, stage="review", verdict="PARTIAL")
    runs_to_banners({RUN["trace_id"]: RUN}, [advanced], log)
    assert any("Moving to station: Review" in line for line in log)
    assert any("Judge verdict: PARTIAL" in line for line in log)


def test_floor_table_renders():
    table = floor_table([RUN])
    text = render(table)
    assert "contract_03_service_agreement.pdf" in text
    assert "CORRECT" in text
    assert "$0.0496" in text


def test_review_table_shows_reconsider_causes():
    table = review_table([
        dict(
            RUN,
            stage="archived",
            needs_human=True,
            needs_reconsideration=True,
            review_causes=["judge_miss"],
            escalation_reason="reconsider: judge verdict MISS",
        )
    ])
    text = render(table)
    assert "reconsider:" in text
    assert "MISS" in text
    assert "mailroom-tui --resolve" in text


def test_review_table_shows_failure_class():
    table = review_table([
        dict(
            RUN,
            stage="failed",
            needs_human=True,
            failure_class="llm_timeout",
            error_message="run aborted [llm_timeout]: TimeoutError",
        )
    ])
    text = render(table)
    assert "llm_timeout" in text


def test_tui_resolve_flags_include_class_and_source():
    from pathlib import Path

    src = (Path(__file__).resolve().parent.parent / "tui" / "mailroom_console.py").read_text()
    assert "--doc-type" in src
    assert "--doc-subclass" in src
    assert "--extracted-data" in src
    assert '"complete"' in src
    assert 'help="print parked document text via GET /api/review/source"' in src
    assert "doc_type" in src and "doc_subclass" in src



def test_metrics_table_renders():
    table = metrics_table({"total_docs": 10, "verdict_counts": {"CORRECT": 3, "PARTIAL": 1}})
    text = render(table)
    assert "10" in text
    assert "verdict CORRECT" in text


def test_inspect_panels_build():
    run = dict(
        RUN,
        spans=[{"name": "intake-document", "status": "SUCCESS", "latency": 3.2,
                "observation_type": "SPAN"},
               {"name": "classify-document", "status": "SUCCESS", "latency": 4.1,
                "observation_type": "AGENT"},
               {"name": "judge-verify", "status": "SUCCESS", "latency": 1.0,
                "observation_type": "EVALUATOR"}],
        generations=[{"name": "classify-document", "model": "gpt-4o-mini",
                      "usage_input_tokens": 400, "usage_output_tokens": 700,
                      "cost_usd": 0.0005, "latency": 6.1}],
        scores={"mailroom-pipeline-judge": "CORRECT"},
    )
    panels = inspect_panels(run)
    assert len(panels) == 4
    text = "\n".join(render(p) for p in panels)
    assert "intake-document" in text
    assert "AGENT" in text
    assert "EVALUATOR" in text
    assert "OBSERVATIONS" in text
    assert "gpt-4o-mini" in text
    assert "mailroom-pipeline-judge" in text


def test_inspect_panels_show_subclass_and_intake():
    run = dict(
        RUN,
        doc_subclass="license",
        expected_subclass="license",
        intake_messy=True,
        intake_changed=True,
        intake_method="deterministic",
        intake_chars=120,
        scores={"maud_question_accuracy": 0.8},
    )
    text = "\n".join(render(p) for p in inspect_panels(run))
    assert "SUBCLASS" in text
    assert "license" in text
    assert "INTAKE MESSY" in text
    assert "deterministic" in text


def test_inspect_panels_show_doc_id():
    text = "\n".join(render(p) for p in inspect_panels(dict(RUN, doc_id="doc-abc")))
    assert "DOC ID" in text
    assert "doc-abc" in text


def test_inspect_panels_show_failure_class():
    text = "\n".join(render(p) for p in inspect_panels(dict(
        RUN, failure_class="llm_timeout", run_aborted=True,
        error_message="run aborted [llm_timeout]: TimeoutError",
    )))
    assert "FAILURE CLASS" in text
    assert "llm_timeout" in text
    assert "ABORTED" in text


def test_post_json_is_exported():
    assert callable(post_json)


def test_station_map_covers_stages():
    for stage in ("intake", "classify", "retry_classify", "review_classify",
                  "extract", "judge_verify", "arbiter", "boss", "review",
                  "report", "catalog", "archive", "archived", "failed"):
        assert stage in STATION_BY_STAGE


def test_metrics_table_survives_null_cost():
    table = metrics_table({"total_docs": 0, "total_cost_usd": None, "avg_latency_s": None})
    text = render(table)
    assert "total docs" in text
    assert "None" not in text


def test_inspect_panels_accept_score_list():
    run = dict(
        RUN,
        scores=[{"name": "mailroom-pipeline-judge", "value": "CORRECT"}],
    )
    text = "\n".join(render(p) for p in inspect_panels(run))
    assert "mailroom-pipeline-judge" in text


def test_sessions_table_renders():
    table = sessions_table({
        "sessions": [{
            "id": "MATTER-001",
            "name": "MATTER-001",
            "trace_count": 1,
            "updated_at": "2026-08-25T01:00:00",
            "runs": [RUN],
        }],
    })
    assert "MATTER-001" in render(table)


def test_fetch_floor_runs_none_means_closed(monkeypatch):
    monkeypatch.setattr("tui.mailroom_console.fetch_snapshot", lambda: None)
    monkeypatch.setattr("tui.mailroom_console.fetch_list", lambda path: None)
    assert fetch_floor_runs() is None


def test_fetch_list_empty_is_not_closed(monkeypatch):
    monkeypatch.setattr("tui.mailroom_console.fetch", lambda path, timeout=15.0: {"runs": []})
    assert fetch_list("/api/traces") == []


def test_debug_panel_shows_ring():
    LAST_ERRORS.clear()
    LAST_ERRORS.append("GET /api/health: URLError: connection refused")
    assert "connection refused" in render(debug_panel())


def test_live_window_matches_web_clients():
    assert WINDOW_S == 604800


# ---------------------------------------------------------------------------
# REPL command registry
# ---------------------------------------------------------------------------

def make_ctx(monkeypatch, rows=None):
    ctx = cmds.CommandContext()
    ctx.api_base = "http://127.0.0.1:8001"
    ctx.window_s = WINDOW_S
    if rows is not None:
        monkeypatch.setattr("tui.corpus.hf_corpus.fetch_rows", lambda **kw: rows)
    return ctx


def test_command_registry_basic():
    ctx = cmds.CommandContext()
    assert cmds.run_command(ctx, "uname")[0].plain == \
        "mailroom-tui — the llm-mailroom visual engine"
    assert cmds.run_command(ctx, "echo hi there")[0].plain == "hi there"
    assert cmds.run_command(ctx, "") == []
    unknown = cmds.run_command(ctx, "definitely-not-a-command")
    assert "command not found" in unknown[0].plain
    assert cmds.run_command(ctx, "help")[0].plain.startswith("Available commands")
    assert "corpus" in cmds.run_command(ctx, "help")[0].plain


def test_man_pages_cover_registry():
    for name in cmds.command_names():
        assert name in cmds.MAN_PAGES, f"missing man page for {name}"


def test_completion_candidates():
    ctx = cmds.CommandContext()
    assert "corpus" in cmds.completion_candidates(ctx, "cor")
    assert {"ls", "show", "search", "stats"} <= set(cmds.completion_candidates(ctx, "corpus "))
    assert cmds.completion_candidates(ctx, "corpus l")[0] == "ls"
    names = cmds.completion_candidates(ctx, "open ")
    assert "llm-mailroom" in names
    assert "llm-mailroom" in cmds.completion_candidates(ctx, "repos ")


def test_filter_command_sets_and_clears():
    ctx = cmds.CommandContext()
    cmds.run_command(ctx, "filter stage=archived")
    assert ctx.filters["stage"] == "archived"
    cmds.run_command(ctx, "filter clear")
    assert ctx.filters["stage"] is None
    bad = cmds.run_command(ctx, "filter bogus=1")
    assert "unknown filter" in bad[0].plain


def test_sentinels():
    ctx = cmds.CommandContext()
    assert cmds.run_command(ctx, "quit") == [cmds.QUIT]
    assert cmds.run_command(ctx, "clear") == [cmds.CLEAR]
    assert cmds.run_command(ctx, "floor") == [cmds.DESK_FLOOR]


# ---------------------------------------------------------------------------
# Corpus browser (mocked Hub, no network)
# ---------------------------------------------------------------------------

GT_ROW = {"filename": "a.txt", "expected": "contract",
          "expected_subclass": "license", "content_sha256": "ab" * 32}
DEFAULT_ROW = {"filename": "a.txt", "doc_text": "hello corpus", "metadata": {}}


def _fake_fetch(split_rows: dict[str, list[dict]]):
    """fetch_rows fake: split_rows maps split -> default rows; the GT config
    mirrors the same filenames with GT_ROW fields."""
    def fake(**kw):
        split = kw["split"]
        rows = split_rows.get(split, [])
        if kw["config"] == "ground_truth":
            return [dict(GT_ROW, filename=r["filename"]) for r in rows]
        return [dict(DEFAULT_ROW, filename=r["filename"]) for r in rows]
    return fake


def test_corpus_catalog_uses_gt_for_class_and_sha(monkeypatch):
    monkeypatch.setattr("tui.corpus.hf_corpus.fetch_rows",
                        _fake_fetch({"train": [DEFAULT_ROW]}))
    client = CorpusClient()
    rows = client.catalog()
    assert len(rows) == 1
    assert rows[0].filename == "a.txt"
    assert rows[0].doc_class == "contract"
    assert rows[0].doc_subclass == "license"
    assert rows[0].sha256 == "ab" * 32
    assert rows[0].chars == len("hello corpus")


def test_corpus_find_search_counts(monkeypatch):
    monkeypatch.setattr(
        "tui.corpus.hf_corpus.fetch_rows",
        _fake_fetch({"train": [
            {"filename": "f1.htm", "doc_text": "", "metadata": {}},
            {"filename": "f2.htm", "doc_text": "", "metadata": {}},
        ]}))
    client = CorpusClient()
    assert client.find("f2.htm").doc_subclass == "license"
    assert [r.filename for r in client.search("contract")] == ["f1.htm", "f2.htm"]
    assert client.split_counts()["train"] == 2
    assert client.split_counts()["test"] == 0
    assert client.class_counts()["contract"] == 2


def test_corpus_row_fetches_with_offset(monkeypatch):
    seen = []

    def fake_fetch_rows(**kw):
        seen.append((kw["config"], kw.get("offset", 0)))
        return [{"filename": "a.txt", "doc_text": "the document", "metadata": {}}]

    monkeypatch.setattr("tui.corpus.hf_corpus.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("tui.corpus.hf_corpus.GT_CONFIG", "ground_truth")
    monkeypatch.setattr("tui.corpus.hf_corpus.DEFAULT_CONFIG", "default")
    client = CorpusClient(page_size=100)
    row = client.row("a.txt")
    assert row["doc_text"] == "the document"
    assert seen[0] == ("default", 0)
    gt = client.gt_row("a.txt")
    assert gt is not None
    assert seen[-1] == ("ground_truth", 0)


def test_corpus_closed_state(monkeypatch):
    def boom(**kw):
        raise RuntimeError("hub down")

    monkeypatch.setattr("tui.corpus.hf_corpus.fetch_rows", boom)
    client = CorpusClient()
    with pytest.raises(CorpusClosed):
        client.catalog()


def test_corpus_command_ls_with_mock(monkeypatch):
    monkeypatch.setattr("tui.corpus.hf_corpus.fetch_rows",
                        _fake_fetch({"train": [DEFAULT_ROW]}))
    ctx = make_ctx(monkeypatch)
    out = cmds.run_command(ctx, "corpus ls")
    text = render(out[0])
    assert "contract" in text
    assert "a.txt" in text


# ---------------------------------------------------------------------------
# Constellation repo manifest (completeness contract)
# ---------------------------------------------------------------------------

def _sync_packages():
    path = ROOT.parents[1] / "scripts" / "packages_sync.json"
    if not path.is_file():
        pytest.skip("packages_sync.json lives in the Digital-Mailroom monorepo only")
    sync = json.loads(path.read_text())
    return {k.lower() for k in sync["packages"].keys()}


def test_repos_manifest_covers_every_synced_package():
    """Every package the monorepo mirrors upstream must appear in the TUI
    constellation manifest (the 'browse the other repositories' surface)."""
    names = {r["name"].lower() for r in repos_mod.all_repos()}
    missing = _sync_packages() - names
    assert not missing, f"manifest missing synced packages: {sorted(missing)}"


def test_repos_manifest_covers_hub_and_derived():
    names = {r["name"] for r in repos_mod.all_repos()}
    for expected in ("mailroom-dev", "mailroom-hub", "LLM-Postal",
                     "mailroom-dev-graph", "llm-entity-extraction-graph",
                     "llm-mailroom-graph"):
        assert expected in names


def test_repos_urls_consistent():
    for r in repos_mod.all_repos():
        repo = repos_mod.CONSTELLATION[r["name"]].get("repo", r["name"])
        assert r["url"] == f"https://github.com/Exios66/{repo}"
        assert r["role"] in ("pipeline", "visualizer", "scoring", "eval",
                             "sandbox", "corpus", "derived", "hub")
        assert r["blurb"]


def test_repos_lookup_and_render():
    assert repos_mod.lookup("llm-mailroom")["name"] == "llm-mailroom"
    assert repos_mod.lookup("Exios66/llm-mailroom")["name"] == "llm-mailroom"
    assert repos_mod.lookup("nope") is None
    text = render(repos_table(repos_mod.all_repos()[:3]))
    assert "llm-mailroom" in text
    assert "CONSTELLATION" in text


def test_repos_live_meta_offline_is_none(monkeypatch):
    monkeypatch.setattr("tui.repos._fetch_gh", lambda name: None)
    assert repos_mod.live_meta("llm-mailroom") is None


# ---------------------------------------------------------------------------
# New renderers
# ---------------------------------------------------------------------------

def test_corpus_table_and_stats_render():
    from tui.corpus import SlimRow
    rows = [SlimRow(filename="a.htm", split="train", index=0, doc_class="contract",
                    doc_subclass="license", sha256="ab" * 32, chars=100)]
    text = render(corpus_table(rows))
    assert "a.htm" in text and "license" in text and "ab" in text
    stats = corpus_stats_table({"train": 1, "test": 0}, {"contract": 1})
    text = render(stats)
    assert "train" in text and "contract" in text


def test_line_editor_history_and_enter():
    from tui.mailroom_console import LineEditor
    from rich.console import Console as RC
    editor = LineEditor(RC(force_terminal=True, width=120))
    pending = deque()
    assert editor.handle("h", pending) is False
    assert editor.handle("i", pending) is False
    assert editor.handle("\r", pending) is True
    assert editor.text() == ""
    # The REPL dispatches `submitted` — reading text() after Enter got "".
    assert editor.submitted == "hi"
    assert editor.history == ["hi"]
    # backspace
    editor.handle("x", pending)
    editor.handle("y", pending)
    editor.handle("\x7f", pending)
    assert editor.text() == "x"
    # Ctrl+C cancels the line
    editor.handle("z", pending)
    editor.handle("\x03", pending)
    assert editor.text() == ""


def test_line_editor_arrow_keys_recall_history_not_typed_text():
    from tui.mailroom_console import LineEditor
    from rich.console import Console as RC
    editor = LineEditor(RC(force_terminal=True, width=120))
    pending = deque()
    for ch in "help\r":
        editor.handle(ch, pending)
    pending.extend("[A")          # tail collected by _collect_escape
    editor.handle("\x1b", pending)
    assert editor.text() == "help"
    pending.extend("[C")          # right arrow: ignored, never typed
    editor.handle("\x1b", pending)
    assert editor.text() == "help"
    editor.handle("\x0c", pending)  # Ctrl+L requests a screen clear
    assert editor.clear_requested and editor.text() == "help"


def test_rich_markup_in_trace_strings_is_literal():
    from rich.console import Console as RC
    from tui.views import floor_table

    run = {"trace_id": "t1", "filename": "weird[/bold] [x].pdf", "stage": "review",
           "doc_type": "contract", "routing_path": ["[/oops]"]}
    console = RC(record=True, width=200)
    console.print(floor_table([run]))  # raised MarkupError before
    assert "[x].pdf" in console.export_text()


def test_corpus_bad_page_flag_is_a_usage_message():
    from tui import commands as cmds

    ctx = cmds.CommandContext()
    out = cmds.run_command(ctx, "corpus ls --page nope")
    assert "expects a number" in str(out[0])


def test_inline_flag_does_not_swallow_next_arg():
    from tui.commands import _clean_args, _flag

    consumed: set = set()
    assert _flag(["--page=2", "extra"], "--page", consumed=consumed) == "2"
    assert _clean_args(["--page=2", "extra"], consumed) == ["extra"]
