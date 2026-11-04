#!/usr/bin/env python3
"""Deterministic gate for build_floor_digest.py (stdlib only, plain asserts).

Builds a throwaway fixture (two synthetic runs + a stub build_graph.py), runs the real
CLI against it, and asserts the digest semantics. If the real ``$BASE/runtime/runs``
exists it is additionally cross-checked. Prints ``SELFTEST <pass>/<total> PASS``, exit 0;
otherwise lists failures and exits 1.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
BUILDER = HERE / "build_floor_digest.py"
TEMPLATE = HERE / "floor.template.html"
REFERENCE = HERE / "reference_digest_scratch.json"

sys.path.insert(0, str(HERE))
import build_floor_digest as bfd

STUB_GRAPH = '''
from langgraph.graph import StateGraph, START, END


def intake_node(state):
    from agents.intake import IntakeAgent
    return IntakeAgent().run(state)


def classify_node(state):
    from agents.sorter import SorterAgent
    return SorterAgent().run(state)


def extract_node(state):
    return _build_specialist_dispatch()[state["doc_type"]](state)


def human_review_node(state):
    return interrupt({"why": "review"})


def archive_node(state):
    return {"stage": "archived"}


def build():
    workflow = StateGraph(dict)
    workflow.add_node("intake", traced_node("intake-document")(_bounded(intake_node)))
    workflow.add_node("classify", traced_node("classify-document")(_bounded(classify_node)))
    workflow.add_node("extract", traced_node("extract-fields")(_bounded(extract_node)))
    workflow.add_node("human_review", traced_node("route-for-review")(_bounded(human_review_node)))
    workflow.add_node("archive", traced_node("archive-document")(_bounded(archive_node)))

    workflow.add_conditional_edges(START, entry_route, {
        "intake": "intake",
        "classify": "classify",
    })
    workflow.add_edge("intake", "classify")
    workflow.add_conditional_edges("classify", after_classify, {
        "classify": "classify",  # transient self-loop: must NOT be drawn
        "extract": "extract",
        "human_review": "human_review",
        "bogus": "not_a_registered_node",  # value is not a graph node: ignored
    })
    workflow.add_conditional_edges("human_review", after_human_review, {
        "extract": "extract",
        "failed": END,
    })
    workflow.add_edge("extract", "archive")
    workflow.add_edge("archive", END)
    return workflow.compile()
'''

EXPECTED_EDGES = {
    ("START", "intake"), ("START", "classify"), ("intake", "classify"), ("classify", "extract"),
    ("classify", "human_review"), ("human_review", "extract"), ("human_review", "failed"),
    ("extract", "archive"), ("archive", "END"),
}
RUN_KEYS = {
    "name", "state", "cursor", "total", "items_attempted", "items_ok", "engine", "profile", "spec_hash",
    "dataset_hash", "prompt_default", "tokens", "node_fires", "edge_fires", "node_agents", "node_ms_p50",
    "aborts_by_last_node", "outcomes", "per_class",
}


# ── fixture ─────────────────────────────────────────────────────────────────────


def _jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join((r if isinstance(r, str) else json.dumps(r)) + "\n" for r in rows), encoding="utf-8")


def _visits(doc, nodes, ms=None, tokens=None):
    """running + done record per visit, like job.node_trace emits."""
    rows = []
    for n in nodes:
        rows.append({"doc": doc, "node": n, "status": "running", "agent": None})
        done = {"doc": doc, "node": n, "status": "done", "agent": "sorter" if n == "classify" else None}
        if ms and n in ms:
            done["ms"] = ms[n]
        if tokens and n in tokens:
            done.update(tokens[n])
        rows.append(done)
    return rows


def make_fixture(root: Path) -> tuple[Path, Path]:
    base = root / "data"
    graph = root / "build_graph.py"
    graph.write_text(STUB_GRAPH, encoding="utf-8")

    # run-a: live, full set of siblings
    a = base / "runtime" / "runs" / "run-a"
    _jsonl(a / "dataset.jsonl", [
        {"id": "d1", "expected_doc_class": "contract"}, {"id": "d2", "expected_doc_class": "contract"},
        {"id": "d3", "expected_doc_class": "letter"}, {"id": "d4", "expected_doc_class": "letter"},
    ])
    _jsonl(a / "items.jsonl", [
        {"item_id": "d1", "ok": True, "pred": {"stage": "archived", "doc_type": "contract"}},
        {"item_id": "d2", "ok": True, "pred": {"stage": "review"}},
        {"item_id": "d3", "ok": False, "pred": {"stage": "failed"}, "error": "boom"},
        {"item_id": "d4", "ok": True, "pred": {"stage": "weird_unknown_stage"}},
    ])
    tok = {"classify": {"prompt_tokens": 100, "completion_tokens": 10}}
    nodes = (
        _visits("d1", ["intake", "classify", "classify", "extract", "archive"], {"intake": 100}, tok)
        + _visits("d2", ["intake", "classify", "human_review"], {"intake": 200}, tok)
        + _visits("d3", ["intake", "classify"], {"intake": 400}, tok)
        + _visits("d4", ["intake", "classify", "extract"], {"intake": 300}, tok)
    )
    _jsonl(a / "nodes.jsonl", nodes[:3] + ['{"doc": "torn", "node"'] + nodes[3:])  # torn line must be skipped
    (a / "checkpoint.json").write_text(json.dumps({"state": "running", "cursor": 4, "total": 4}), encoding="utf-8")
    (a / "spec.lock.json").write_text(json.dumps({
        "spec_hash": "spec-a", "profile": "prof-x", "engine": {"kind": "vllm-remote", "model": "model-x", "junk": 1},
        "dataset": {"sha256": "ds-hash-a"},
    }), encoding="utf-8")
    (a / "prompt.lock.json").write_text(json.dumps({"default": {"source": "code-default", "name": "pdef"}}),
                                        encoding="utf-8")

    # run-b: archived attempt WITHOUT dataset.jsonl / spec.lock / prompt.lock
    b = base / "run-history" / "run-b"
    _jsonl(b / "items.jsonl", [
        {"item_id": "b1", "ok": True, "pred": {"stage": "archived"}},
        {"item_id": "b2", "ok": False},
        {"item_id": "b3", "ok": True, "stage": "something-new"},
    ])
    _jsonl(b / "nodes.jsonl", _visits("b1", ["intake", "classify", "extract"]) + _visits("b2", ["intake"]))
    (b / "checkpoint.json").write_text(json.dumps({"state": "failed", "cursor": 3, "total": 50}), encoding="utf-8")
    return base, graph


def snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns)
            for p in sorted(root.rglob("*")) if p.is_file()}


def run_cli(base: Path, out: Path, graph: Path | None, *extra: str, env_extra: dict | None = None):
    env = {**os.environ}
    env.pop("MAILROOM_BASE_DIR", None)
    if graph is not None:
        env["FLOOR_DIGEST_GRAPH"] = str(graph)
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(BUILDER), "--base", str(base), "--out", str(out), *extra],
                          capture_output=True, text=True, env=env, timeout=120, check=False)


# ── tests ───────────────────────────────────────────────────────────────────────

CTX: dict = {}
TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


@test
def cli_runs_and_prints_summary():
    r = CTX["proc"]
    assert r.returncode == 0, r.stderr
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith("run-")]
    assert len(lines) == 2, r.stdout
    assert "attempted=4" in lines[1] and "ok=3" in lines[1] and "top3=" in lines[1]
    assert (CTX["out"] / "floor_digest.json").is_file() and (CTX["out"] / "floor_digest.js").is_file()


@test
def graph_edges_parsed_from_stub_incl_conditional_map():
    edges = {tuple(e) for e in CTX["d"]["graph_reference"]["edges"]}
    assert edges == EXPECTED_EDGES, edges ^ EXPECTED_EDGES
    assert all(a != b for a, b in edges), "self-loops must be excluded"
    assert "self-loops" in CTX["d"]["graph_reference"]["note"]


@test
def graph_node_boxes_and_agent_attribution():
    na = CTX["d"]["graph_reference"]["node_agents"]
    assert "END" not in na and "START" not in na
    assert na == {"intake": "intake", "classify": "sorter", "extract": bfd.SPECIALIST_LABEL,
                  "human_review": "(tray)", "archive": "(code)", "failed": "(abort terminal)"}, na


@test
def node_fires_count_distinct_docs_not_lines():
    a = CTX["runs"]["run-a"]
    assert a["node_fires"] == {"archive": 1, "classify": 4, "extract": 2, "human_review": 1, "intake": 4}, a["node_fires"]


@test
def edge_fires_count_traversals_and_skip_self_transients():
    a = CTX["runs"]["run-a"]
    assert a["edge_fires"] == {"classify>extract": 2, "classify>human_review": 1, "extract>archive": 1,
                               "intake>classify": 4}, a["edge_fires"]
    assert "classify>classify" not in a["edge_fires"]
    b = CTX["runs"]["run-b"]
    assert b["edge_fires"] == {"classify>extract": 1, "intake>classify": 1}


@test
def outcomes_group_items_by_final_stage():
    o = CTX["runs"]["run-a"]["outcomes"]
    assert o == {"contract": {"ship": 1, "held": 1, "failed": 0, "open": 0, "n": 2},
                 "letter": {"ship": 0, "held": 0, "failed": 1, "open": 1, "n": 2}}, o


@test
def unknown_stage_never_crashes_and_is_open():
    b = CTX["runs"]["run-b"]
    assert b["outcomes"] == {"?": {"ship": 1, "held": 0, "failed": 1, "open": 1, "n": 3}}, b["outcomes"]
    assert bfd._stage_bucket("¯\\_(ツ)_/¯", True) == "open"
    assert bfd._stage_bucket(None, False) == "failed" and bfd._stage_bucket({"x": 1}, None) == "open"


@test
def aborts_attributed_to_last_node():
    assert CTX["runs"]["run-a"]["aborts_by_last_node"] == {"classify": 1}
    assert CTX["runs"]["run-b"]["aborts_by_last_node"] == {"intake": 1}


@test
def per_class_computed_only_when_dataset_present():
    a, b = CTX["runs"]["run-a"], CTX["runs"]["run-b"]
    assert b["per_class"] == {}, "no dataset.jsonl -> honest gap"
    c = a["per_class"]["contract"]
    assert c["nodes"] == {"intake": 2, "classify": 2, "extract": 1, "archive": 1, "human_review": 1}, c["nodes"]
    assert c["edges"] == {"intake>classify": 2, "classify>extract": 1, "extract>archive": 1,
                          "classify>human_review": 1}, c["edges"]
    assert c["outcomes"] == a["outcomes"]["contract"]
    letter = a["per_class"]["letter"]
    assert letter["nodes"] == {"intake": 2, "classify": 2, "extract": 1}
    assert letter["outcomes"]["n"] == 2 and letter["outcomes"]["failed"] == 1


@test
def non_finite_numbers_are_ignored_not_crashing():
    for bad in (float("nan"), float("inf"), float("-inf"), 10 ** 400):
        assert bfd._num(bad) is None, bad
    assert bfd._num(3) == 3.0 and bfd._num(True) is None
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        run = t / "data" / "runtime" / "runs" / "run-nan"
        # raw lines: json.dumps(float("nan")) writes the bare NaN / Infinity tokens json.loads accepts
        _jsonl(run / "items.jsonl", [
            '{"item_id": "n1", "ok": true, "stage": "archived", "prompt_tokens": NaN}',
            '{"item_id": "n2", "ok": true, "stage": "archived", "completion_tokens": Infinity}',
        ])
        _jsonl(run / "nodes.jsonl", [
            '{"doc": "n1", "node": "intake", "status": "done", "ms": NaN, "prompt_tokens": NaN}',
            '{"doc": "n1", "node": "classify", "status": "done", "ms": 50, "prompt_tokens": 9}',
            '{"doc": "n2", "node": "intake", "status": "done", "ms": Infinity, "completion_tokens": -Infinity}',
        ])
        r = run_cli(t / "data", t / "out", CTX["graph"])
        assert r.returncode == 0, r.stderr
        text = (t / "out" / "floor_digest.json").read_text(encoding="utf-8")
        assert "NaN" not in text and "Infinity" not in text, "non-finite value leaked into the digest"
        rr = json.loads(text)["runs"][0]
        assert rr["tokens"] == {"prompt": 9, "completion": 0}, rr["tokens"]
        assert rr["node_ms_p50"] == {"classify": 50, "intake": 0}, rr["node_ms_p50"]


@test
def zero_checkpoint_total_falls_back_to_dataset_rows():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        run = t / "data" / "runtime" / "runs" / "run-zero"
        _jsonl(run / "dataset.jsonl", [{"id": f"z{i}", "expected_doc_class": "letter"} for i in range(3)])
        _jsonl(run / "items.jsonl", [{"item_id": "z0", "ok": True, "stage": "archived"}])
        (run / "checkpoint.json").write_text(json.dumps({"state": "running", "cursor": 1, "total": 0}),
                                             encoding="utf-8")
        r = run_cli(t / "data", t / "out", CTX["graph"])
        assert r.returncode == 0, r.stderr
        rr = json.loads((t / "out" / "floor_digest.json").read_text(encoding="utf-8"))["runs"][0]
        assert rr["total"] == 3, rr["total"]


@test
def classes_sorted_and_run_labels_from_spec_lock():
    d, a, b = CTX["d"], CTX["runs"]["run-a"], CTX["runs"]["run-b"]
    assert d["classes"] == ["contract", "letter"]
    assert a["engine"] == {"kind": "vllm-remote", "model": "model-x"} and a["profile"] == "prof-x"
    assert a["spec_hash"] == "spec-a" and a["dataset_hash"] == "ds-hash-a" and a["prompt_default"] == "pdef"
    assert b["engine"] == {"kind": None, "model": None} and b["profile"] is None and b["prompt_default"] is None


@test
def missing_siblings_degrade_honestly():
    a, b = CTX["runs"]["run-a"], CTX["runs"]["run-b"]
    assert b["total"] is None and a["total"] == 4
    assert (b["state"], b["cursor"], b["items_attempted"], b["items_ok"]) == ("failed", 3, 3, 2)
    assert (a["state"], a["cursor"], a["items_attempted"], a["items_ok"]) == ("running", 4, 4, 3)


@test
def p50_and_tokens():
    a, b = CTX["runs"]["run-a"], CTX["runs"]["run-b"]
    assert a["node_ms_p50"]["intake"] == 250, a["node_ms_p50"]  # median of 100/200/300/400
    assert a["node_ms_p50"]["archive"] == 0, "no duration -> 0 fallback"
    assert a["tokens"] == {"prompt": 500, "completion": 50}, a["tokens"]  # 5 classify visits
    assert b["tokens"] == {"prompt": 0, "completion": 0}
    assert bfd._tokens([], [{"prompt_tokens": 7, "completion_tokens": 3}, {}]) == {"prompt": 7, "completion": 3}
    assert a["node_agents"] == {"classify": {"sorter": 5}}


@test
def digest_schema_is_frozen():
    d = CTX["d"]
    assert set(d) == {"generated_utc", "classes", "graph_reference", "runs"}
    assert set(d["graph_reference"]) == {"edges", "node_agents", "note"}
    assert d["generated_utc"][:16].endswith(("0", "1", "2", "3", "4", "5", "6", "7", "8", "9"))
    for r in d["runs"]:
        assert set(r) == RUN_KEYS, set(r) ^ RUN_KEYS
        assert set(r["tokens"]) == {"prompt", "completion"} and set(r["engine"]) == {"kind", "model"}
    assert [r["name"] for r in d["runs"]] == ["run-b", "run-a"], "history first, then live"


@test
def js_twin_parses_back_to_same_object_byte_identical_payload():
    jbytes = (CTX["out"] / "floor_digest.json").read_bytes()
    sbytes = (CTX["out"] / "floor_digest.js").read_bytes()
    assert sbytes == b"window.DIGEST=" + jbytes + b";\n"
    body = sbytes.decode("utf-8")
    assert body.startswith("window.DIGEST=") and body.rstrip().endswith(";")
    assert json.loads(body[len("window.DIGEST="):body.rindex(";")]) == json.loads(jbytes.decode("utf-8"))


@test
def builder_never_writes_into_the_data_base():
    assert snapshot(CTX["base"]) == CTX["snap_before"]


@test
def unparseable_graph_and_empty_base_fail_loudly():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        for label, text in (("syntax", "def (:\n"), ("no-edges", "x = 1\n"),
                            ("nodes-only", "g.add_node('a', f)\n")):
            bad = t / f"{label}.py"
            bad.write_text(text, encoding="utf-8")
            out = t / f"out-{label}"
            r = run_cli(CTX["base"], out, bad)
            assert r.returncode == bfd.EXIT_GRAPH and "error" in r.stderr, (label, r.returncode, r.stderr)
            assert not (out / "floor_digest.json").exists(), "no partial digest on failure"
        r = run_cli(t / "empty-base", t / "out-empty", CTX["graph"])
        assert r.returncode == bfd.EXIT_NO_RUNS and "no runs found" in r.stderr, (r.returncode, r.stderr)
        blocked = t / "blocked"
        blocked.write_text("a file, not a dir", encoding="utf-8")
        r = run_cli(CTX["base"], blocked / "sub", CTX["graph"])
        assert r.returncode == bfd.EXIT_WRITE, (r.returncode, r.stderr)


@test
def base_dir_resolves_from_env_var():
    with tempfile.TemporaryDirectory() as t:
        env = {**os.environ, "MAILROOM_BASE_DIR": str(CTX["base"]), "FLOOR_DIGEST_GRAPH": str(CTX["graph"])}
        r = subprocess.run([sys.executable, str(BUILDER), "--out", t], capture_output=True, text=True, env=env, cwd=t, check=False)
        assert r.returncode == 0, r.stderr
        assert len(json.loads((Path(t) / "floor_digest.json").read_text(encoding="utf-8"))["runs"]) == 2


@test
def vendored_graph_parses_to_a_sane_topology():
    path = bfd.DEFAULT_GRAPH
    if not path.is_file():
        return
    g = bfd.parse_graph(path)
    edges = {tuple(e) for e in g["edges"]}
    assert any(a == "START" for a, _ in edges) and any(b == "END" for _, b in edges)
    assert all(a != b for a, b in edges)
    nodes = set(g["node_agents"])
    assert all(n in nodes for e in edges for n in e if n not in ("START", "END")), "edge endpoint without a node box"


@test
def template_and_builder_have_no_hard_coded_runs_or_fallbacks():
    html = TEMPLATE.read_text(encoding="utf-8")
    src = BUILDER.read_text(encoding="utf-8")
    assert '<script src="floor_digest.js"></script>' in html
    names = ["shuf2", "even100", "mergers-only", "qwen", "LLMSEATS", "gemooslin", "node_fires.archive",
             "node_fires.boss_escalation"]
    if REFERENCE.is_file():
        names += [r["name"] for r in json.loads(REFERENCE.read_text(encoding="utf-8"))["runs"]]
        names += [(r.get("engine") or {}).get("model") for r in json.loads(REFERENCE.read_text(encoding="utf-8"))["runs"]]
    for needle in filter(None, set(names)):
        assert needle not in html, f"template hard-codes {needle!r}"
        assert needle not in src, f"builder hard-codes {needle!r}"


@test
def real_runs_cross_consistency_when_present():
    base = Path(os.environ.get("MAILROOM_BASE_DIR") or REPO_ROOT / "data")
    if not (base / "runtime" / "runs").is_dir() and not (base / "run-history").is_dir():
        return
    if not bfd.discover_runs(base):
        return
    # No before/after snapshot here: a live run may be appending to its artifacts while the
    # builder reads them. The read-only contract is proven on the fixture by
    # builder_never_writes_into_the_data_base.
    with tempfile.TemporaryDirectory() as t:
        r = run_cli(base, Path(t), None, env_extra={"MAILROOM_BASE_DIR": str(base)})
        assert r.returncode == 0, r.stderr
        d = json.loads((Path(t) / "floor_digest.json").read_text(encoding="utf-8"))
    edges = {f"{a}>{b}" for a, b in d["graph_reference"]["edges"]}
    for run in d["runs"]:
        assert sum(o["n"] for o in run["outcomes"].values()) == run["items_attempted"], run["name"]
        assert set(run["edge_fires"]) <= edges, (run["name"], set(run["edge_fires"]) - edges)


def main() -> int:
    passed, failures = 0, []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        base, graph = make_fixture(root)
        out = root / "out"
        CTX.update(base=base, graph=graph, out=out, snap_before=snapshot(base))
        CTX["proc"] = run_cli(base, out, graph, "--print-summary")
        if CTX["proc"].returncode == 0:
            CTX["d"] = json.loads((out / "floor_digest.json").read_text(encoding="utf-8"))
            CTX["runs"] = {r["name"]: r for r in CTX["d"]["runs"]}
        for fn in TESTS:
            try:
                fn()
                passed += 1
            except Exception:  # noqa: BLE001 — report every failure, not just the first
                failures.append((fn.__name__, traceback.format_exc(limit=3)))
    for name, tb in failures:
        print(f"FAIL {name}\n{tb}", file=sys.stderr)
    verdict = "PASS" if not failures else "FAIL"
    print(f"SELFTEST {passed}/{len(TESTS)} {verdict}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
