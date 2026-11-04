#!/usr/bin/env python3
"""Rebuild the pipeline-floor digest of ALL previous runs from on-disk artifacts.

Reads (never writes) run directories under ``$BASE/runtime/runs/*`` (live) and
``$BASE/run-history/*`` (archived attempts), plus the vendored LangGraph wiring in
``vendor/llm-mailroom/src/graph/build_graph.py``, and emits:

* ``floor_digest.json`` — the frozen digest contract consumed by ``floor.template.html``
* ``floor_digest.js``   — ``window.DIGEST=<same json>;`` twin for file:// viewing

Usage::

    python build_floor_digest.py [--base DIR] [--out DIR] [--print-summary]

``$BASE`` is ``--base``, else ``$MAILROOM_BASE_DIR``, else ``./data``. ``--out`` defaults
to this script's directory. ``$FLOOR_DIGEST_GRAPH`` overrides the build_graph.py path
(used by the selftest to point at a stub).

Exit codes: 0 ok, 2 no runs found, 3 build_graph.py unparseable, 4 write failure.
Stdlib only.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
DEFAULT_GRAPH = REPO_ROOT / "vendor" / "llm-mailroom" / "src" / "graph" / "build_graph.py"

EXIT_NO_RUNS, EXIT_GRAPH, EXIT_WRITE = 2, 3, 4

# Terminal stage vocabulary -> outcome bucket. Anything else is "open" (mid-graph),
# never an error: an unknown stage must not crash the build.
SHIP_STAGES = {"archived", "archive", "ship", "shipped", "done"}
HELD_STAGES = {"review", "human_review", "pending", "pending_review", "held"}
FAIL_STAGES = {"failed", "fail", "error", "aborted"}

TRAY_LABEL = "(tray)"
CODE_LABEL = "(code)"
LANE_LABEL = "(abort terminal)"
SPECIALIST_LABEL = "specialists (fan inside node)"

GRAPH_NOTE = (
    "Parsed from build_graph.py (read-only): add_edge pairs plus add_conditional_edges route "
    "maps whose values name registered nodes; START entry routes are included. Transient "
    "self-loops (edges where source==target) are EXCLUDED from the drawn set; their fires "
    "still count toward the node, never toward an edge. A route key that maps to END (e.g. "
    "human_review -> {'failed': END}) is drawn as a terminal lane node named after the key; "
    "a literal END target is the graph terminal and is not a node box. Run-budget aborts are "
    "additionally attributed by aborts_by_last_node."
)


class DigestError(Exception):
    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


# ── graph topology ──────────────────────────────────────────────────────────────


def _sym(node: ast.AST | None) -> str | None:
    """A graph symbol: a string constant or the START/END names."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        value = node.value
        return {"__start__": "START", "__end__": "END"}.get(value, value)
    if isinstance(node, ast.Name) and node.id in ("START", "END"):
        return node.id
    return None


def _snake(class_name: str) -> str:
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()
    return re.sub(r"_agent$", "", snake)


def _call_name(call: ast.Call) -> str | None:
    f = call.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return None


def _handler_name(expr: ast.AST, funcs: dict[str, ast.AST]) -> str | None:
    """The node handler inside wrap calls like traced_node("x")(_bounded(handler))."""
    wrappers = {id(n.func) for n in ast.walk(expr) if isinstance(n, ast.Call)}
    for n in ast.walk(expr):
        if isinstance(n, ast.Name) and id(n) not in wrappers and n.id in funcs:
            return n.id
    return None


def _attribute(func: ast.AST | None) -> str:
    """Agent/role behind a handler, read from its body; pure-code handlers keep (code)."""
    if func is None:
        return CODE_LABEL
    agents: list[str] = []
    calls: set[str] = set()
    for n in ast.walk(func):
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                if re.search(r"(Agent|Judge)$", alias.name):
                    role = _snake(alias.name)
                    if role not in agents:
                        agents.append(role)
        elif isinstance(n, ast.Call):
            name = _call_name(n)
            if name:
                calls.add(name)
    if agents:
        return "+".join(agents)
    if any("specialist" in c.lower() for c in calls):
        return SPECIALIST_LABEL
    if "interrupt" in calls:
        return TRAY_LABEL
    return CODE_LABEL


def parse_graph(path: Path) -> dict:
    """Derive ``graph_reference`` from build_graph.py; fail loudly on an unknown shape."""
    try:
        source = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise DigestError(f"cannot read {path}: {exc}", EXIT_GRAPH) from exc
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise DigestError(f"{path} is not parseable Python: {exc}", EXIT_GRAPH) from exc

    funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    calls = sorted(
        (n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)),
        key=lambda n: (n.lineno, n.col_offset),
    )

    registered: dict[str, str | None] = {}
    for c in calls:
        if c.func.attr == "add_node" and c.args and _sym(c.args[0]):
            handler = _handler_name(c.args[1], funcs) if len(c.args) > 1 else None
            registered[_sym(c.args[0])] = handler

    edges: list[tuple[str, str]] = []
    lanes: list[str] = []

    def add(a: str | None, b: str | None) -> None:
        if not a or not b or a == b:  # transient self-loops are not drawn
            return
        if (a, b) not in edges:
            edges.append((a, b))

    def known_source(s: str | None) -> bool:
        return s == "START" or s in registered

    for c in calls:
        kind = c.func.attr
        if kind == "add_edge" and len(c.args) >= 2:
            a, b = _sym(c.args[0]), _sym(c.args[1])
            if known_source(a) and (b == "END" or b in registered):
                add(a, b)
        elif kind == "add_conditional_edges" and c.args:
            src = _sym(c.args[0])
            mapping = c.args[2] if len(c.args) > 2 else next(
                (k.value for k in c.keywords if k.arg == "path_map"), None)
            if not known_source(src) or not isinstance(mapping, ast.Dict):
                continue
            for k, v in zip(mapping.keys, mapping.values):
                key, val = _sym(k), _sym(v)
                if val in registered:
                    add(src, val)
                elif val == "END":
                    if key and key not in registered and key not in ("END", "START"):
                        if key not in lanes:
                            lanes.append(key)
                        add(src, key)
                    else:
                        add(src, "END")

    if not registered or not edges:
        raise DigestError(
            f"{path}: could not derive a topology (found {len(registered)} add_node and "
            f"{len(edges)} edge calls); refusing to emit a partial graph — the file shape "
            "changed, update build_floor_digest.parse_graph",
            EXIT_GRAPH,
        )
    for a, b in edges:
        for n in (a, b):
            if n not in ("START", "END") and n not in registered and n not in lanes:
                raise DigestError(f"{path}: edge endpoint {n!r} is not a registered node", EXIT_GRAPH)

    node_agents = {n: _attribute(funcs.get(h)) for n, h in registered.items()}
    node_agents.update({lane: LANE_LABEL for lane in lanes})
    return {"edges": [list(e) for e in edges], "node_agents": node_agents, "note": GRAPH_NOTE}


# ── artifact readers (tolerant: missing / torn files degrade, never fabricate) ──


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        pass
    return rows


def read_json(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _num(value) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _int_if_whole(x: float):
    x = round(x, 1)
    return int(x) if x == int(x) else x


def discover_runs(base: Path) -> list[tuple[str, Path]]:
    """(source, dir) for every dir containing items.jsonl; history first, names sorted."""
    found: list[tuple[str, Path]] = []
    for source, parent in (("history", base / "run-history"), ("live", base / "runtime" / "runs")):
        if not parent.is_dir():
            continue
        for child in sorted(parent.iterdir(), key=lambda p: p.name):
            if child.is_dir() and (child / "items.jsonl").is_file():
                found.append((source, child))
    return found


# ── per-run digest ──────────────────────────────────────────────────────────────


def _stage_bucket(stage, ok) -> str:
    s = str(stage or "").strip().lower()
    if s in SHIP_STAGES:
        return "ship"
    if s in HELD_STAGES:
        return "held"
    if s in FAIL_STAGES:
        return "failed"
    # unknown / missing stage: an item that errored is failed, anything else is still open
    return "failed" if ok is False else "open"


def _item_stage(item: dict):
    for holder in (item, item.get("pred"), item.get("prediction")):
        if isinstance(holder, dict) and holder.get("stage"):
            return holder["stage"]
    return None


def _empty_outcome() -> dict:
    return {"ship": 0, "held": 0, "failed": 0, "open": 0, "n": 0}


def _tokens(nodes: list[dict], items: list[dict]) -> dict:
    prompt = completion = 0
    seen = False
    for r in nodes:
        nested = r.get("tokens") if isinstance(r.get("tokens"), dict) else r.get("usage")
        nested = nested if isinstance(nested, dict) else {}
        p = _num(r.get("prompt_tokens", nested.get("prompt", nested.get("prompt_tokens"))))
        c = _num(r.get("completion_tokens", nested.get("completion", nested.get("completion_tokens"))))
        if p is not None or c is not None:
            seen = True
            prompt += int(p or 0)
            completion += int(c or 0)
    if not seen:  # node records carry no usage: fall back to the per-item usage block
        for it in items:
            prompt += int(_num(it.get("prompt_tokens")) or 0)
            completion += int(_num(it.get("completion_tokens")) or 0)
    return {"prompt": prompt, "completion": completion}


def build_run(name: str, path: Path, edge_set: set[tuple[str, str]]) -> tuple[dict, set[str]]:
    items_raw = read_jsonl(path / "items.jsonl")
    nodes = [r for r in read_jsonl(path / "nodes.jsonl") if r.get("node") and r.get("doc") is not None]
    checkpoint = read_json(path / "checkpoint.json")
    lock = read_json(path / "spec.lock.json")
    prompt_lock = read_json(path / "prompt.lock.json")
    ds_path = path / "dataset.jsonl"
    ds_present = ds_path.is_file()
    ds_rows = read_jsonl(ds_path) if ds_present else []

    # last record per item wins (a resumed run may re-append)
    items_by_id: dict[str, dict] = {}
    for i, it in enumerate(items_raw):
        items_by_id[str(it.get("item_id", it.get("id", f"#{i}")))] = it
    items = list(items_by_id.items())

    ds_class: dict[str, str] = {}
    for row in ds_rows:
        key = row.get("id") or row.get("filename")
        if key is not None and row.get("expected_doc_class"):
            ds_class[str(key)] = str(row["expected_doc_class"])

    # nodes.jsonl: per-doc ordered visits
    per_doc_records: dict[str, list[dict]] = {}
    for r in nodes:
        per_doc_records.setdefault(str(r["doc"]), []).append(r)

    def visit_seq(records: list[dict]) -> list[str]:
        started = [r["node"] for r in records if r.get("status") == "running"]
        return started if started else [r["node"] for r in records]

    node_docs: dict[str, set[str]] = {}
    ms_by_node: dict[str, list[float]] = {}
    agents_by_node: dict[str, Counter] = {}
    for doc, recs in per_doc_records.items():
        for r in recs:
            node_docs.setdefault(r["node"], set()).add(doc)
            ms = _num(r.get("ms", r.get("duration_ms")))
            if ms is not None:
                ms_by_node.setdefault(r["node"], []).append(ms)
            if r.get("agent"):
                agents_by_node.setdefault(r["node"], Counter())[str(r["agent"])] += 1

    def doc_edges(doc: str) -> Counter:
        seq = visit_seq(per_doc_records.get(doc, []))
        return Counter(f"{a}>{b}" for a, b in zip(seq, seq[1:]) if a != b and (a, b) in edge_set)

    edge_fires: Counter = Counter()
    for doc in per_doc_records:
        edge_fires.update(doc_edges(doc))

    def last_stage_from_nodes(doc: str):
        for r in reversed(per_doc_records.get(doc, [])):
            if r.get("stage"):
                return r["stage"]
        return None

    outcomes: dict[str, dict] = {}
    class_outcomes: dict[str, dict] = {}
    aborts: Counter = Counter()
    ok_count = 0
    item_class: dict[str, str] = {}
    for item_id, it in items:
        ok = it.get("ok")
        if ok:
            ok_count += 1
        stage = _item_stage(it) or last_stage_from_nodes(item_id)
        bucket = _stage_bucket(stage, ok if isinstance(ok, bool) else None)
        cls = ds_class.get(item_id) or str(it.get("expected_doc_class") or it.get("expected") or "") or "?"
        item_class[item_id] = cls
        for table, key in ((outcomes, cls), (class_outcomes, ds_class.get(item_id))):
            if key is None:
                continue
            o = table.setdefault(key, _empty_outcome())
            o[bucket] += 1
            o["n"] += 1
        if bucket == "failed":
            recs = per_doc_records.get(item_id)
            aborts[recs[-1]["node"] if recs else "unknown"] += 1

    per_class: dict[str, dict] = {}
    if ds_present and ds_class:
        classes_seen = set(class_outcomes)
        for doc in per_doc_records:
            if doc in ds_class:
                classes_seen.add(ds_class[doc])
        for cls in sorted(classes_seen):
            docs = [d for d in per_doc_records if ds_class.get(d) == cls]
            pc_nodes: Counter = Counter()
            pc_edges: Counter = Counter()
            for d in docs:
                pc_nodes.update({r["node"] for r in per_doc_records[d]})
                pc_edges.update(doc_edges(d))
            per_class[cls] = {
                "nodes": dict(pc_nodes),
                "edges": dict(pc_edges),
                "outcomes": class_outcomes.get(cls, _empty_outcome()),
            }

    engine = lock.get("engine") if isinstance(lock.get("engine"), dict) else {}
    prompt_default = prompt_lock.get("default") if isinstance(prompt_lock.get("default"), dict) else {}
    dataset_lock = lock.get("dataset") if isinstance(lock.get("dataset"), dict) else {}
    dataset_hash = dataset_lock.get("sha256")
    if not dataset_hash and ds_present:
        dataset_hash = hashlib.sha256(ds_path.read_bytes()).hexdigest()

    total = None
    if ds_present:
        cp_total = checkpoint.get("total")
        total = cp_total if isinstance(cp_total, int) and not isinstance(cp_total, bool) else len(ds_rows)

    cursor = checkpoint.get("cursor")
    run = {
        "name": name,
        "state": checkpoint.get("state") or "unknown",
        "cursor": cursor if isinstance(cursor, int) and not isinstance(cursor, bool) else 0,
        "total": total,
        "items_attempted": len(items),
        "items_ok": ok_count,
        "engine": {"kind": engine.get("kind"), "model": engine.get("model")},
        "profile": lock.get("profile"),
        "spec_hash": lock.get("spec_hash") or checkpoint.get("spec_hash"),
        "dataset_hash": dataset_hash,
        "prompt_default": prompt_default.get("name") or prompt_default.get("source"),
        "tokens": _tokens(nodes, [it for _, it in items]),
        "node_fires": {n: len(d) for n, d in sorted(node_docs.items())},
        "edge_fires": dict(sorted(edge_fires.items())),
        "node_agents": {n: dict(sorted(c.items())) for n, c in sorted(agents_by_node.items())},
        "node_ms_p50": {n: (_int_if_whole(statistics.median(ms_by_node[n])) if ms_by_node.get(n) else 0)
                        for n in sorted(node_docs)},
        "aborts_by_last_node": dict(sorted(aborts.items())),
        "outcomes": dict(sorted(outcomes.items())),
        "per_class": per_class,
    }
    classes = {c for c in outcomes if c != "?"} | set(ds_class.values())
    return run, classes


# ── build / output ──────────────────────────────────────────────────────────────


def resolve_base(arg: str | None) -> Path:
    return Path(arg or os.environ.get("MAILROOM_BASE_DIR") or "./data")


def build_digest(base: Path, graph_path: Path) -> dict:
    graph = parse_graph(graph_path)
    runs_found = discover_runs(base)
    if not runs_found:
        raise DigestError(
            f"no runs found under {base}/runtime/runs/* or {base}/run-history/* "
            "(a run is any directory containing items.jsonl)",
            EXIT_NO_RUNS,
        )
    edge_set = {(a, b) for a, b in graph["edges"]}
    runs: list[dict] = []
    classes: set[str] = set()
    used: set[str] = set()
    for source, path in runs_found:
        name = path.name if path.name not in used else f"{path.name} ({source})"
        used.add(name)
        run, run_classes = build_run(name, path, edge_set)
        runs.append(run)
        classes |= run_classes
    return {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "classes": sorted(classes),
        "graph_reference": graph,
        "runs": runs,
    }


def write_outputs(digest: dict, out: Path) -> tuple[Path, Path]:
    payload = json.dumps(digest, ensure_ascii=False, indent=1)
    json_path, js_path = out / "floor_digest.json", out / "floor_digest.js"
    try:
        out.mkdir(parents=True, exist_ok=True)
        for path, text in ((json_path, payload), (js_path, f"window.DIGEST={payload};\n")):
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_bytes(text.encode("utf-8"))  # bytes: no platform newline translation
            os.replace(tmp, path)
    except OSError as exc:
        raise DigestError(f"failed to write digest to {out}: {exc}", EXIT_WRITE) from exc
    return json_path, js_path


def summary_lines(digest: dict) -> list[str]:
    lines = []
    for r in digest["runs"]:
        top = sorted(r["node_fires"].items(), key=lambda kv: (-kv[1], kv[0]))[:3]
        lines.append(
            f"{r['name']}  state={r['state']}  attempted={r['items_attempted']}  ok={r['items_ok']}  "
            f"top3={', '.join(f'{n}={c}' for n, c in top) or '-'}"
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build floor_digest.json/.js from on-disk run artifacts.")
    ap.add_argument("--base", help="data base dir (default: $MAILROOM_BASE_DIR or ./data)")
    ap.add_argument("--out", help="output dir (default: this script's directory)")
    ap.add_argument("--print-summary", action="store_true", help="print one line per run")
    args = ap.parse_args(argv)
    graph_path = Path(os.environ.get("FLOOR_DIGEST_GRAPH") or DEFAULT_GRAPH)
    out = Path(args.out) if args.out else HERE
    try:
        digest = build_digest(resolve_base(args.base), graph_path)
        json_path, js_path = write_outputs(digest, out)
    except DigestError as exc:
        print(f"build_floor_digest: error: {exc}", file=sys.stderr)
        return exc.code
    if args.print_summary:
        print("\n".join(summary_lines(digest)))
    print(f"wrote {json_path} and {js_path} ({len(digest['runs'])} runs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
