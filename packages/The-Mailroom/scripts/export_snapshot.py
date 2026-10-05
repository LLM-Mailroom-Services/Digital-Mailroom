"""Export a static JSON snapshot of the current trace sources for GitHub Pages.

Pulls once from whichever source is configured (Langfuse, Phoenix, or both)
and writes the exact shapes the SPA's static mode consumes:

    <out>/meta.json            doc classes + endpoint index + build info
    <out>/traces.json          floor-level runs ({count, runs})
    <out>/runs/<id>.json       full run detail (spans/generations/scores)
    <out>/metrics.json         window aggregates
    <out>/sessions.json        session summaries
    <out>/review-queue.json    needs_human runs
    <out>/../debug/build-info.json   provenance for agents (git sha, counts)

Nothing is fabricated: an unreachable source yields an empty snapshot (the
site shows its closed state), never canned data.

Usage:
    python scripts/export_snapshot.py [--source langfuse|phoenix|both]
                                     [--out site/data] [--since-hours 24]
                                     [--limit 200] [--check]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Aware sort sentinel: parsed run timestamps are tz-aware UTC.
EPOCH = datetime.min.replace(tzinfo=timezone.utc)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _safe_id(trace_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", trace_id)


def _detail(run) -> dict:
    from mailroom_ui.models import PipelineRun
    from server.poller import floor_payload

    assert isinstance(run, PipelineRun)
    return {
        **floor_payload(run),
        "spans": [s.model_dump(mode="json") for s in run.spans],
        "generations": [g.model_dump(mode="json") for g in run.generations],
        "scores": run.scores,
    }


def _sessions(runs, limit: int = 50) -> list[dict]:
    """Group enriched runs by session — mirrors /api/sessions logic."""
    grouped: dict[str, list] = {}
    for r in runs:
        sid = r.session_id or r.matter_id
        if not sid:
            continue
        grouped.setdefault(sid, []).append(r)
    out = []
    for sid, rs in grouped.items():
        rs.sort(key=lambda r: (r.updated_at or r.created_at or EPOCH), reverse=True)
        created = [r.created_at for r in rs if r.created_at]
        updated = [r.updated_at or r.created_at for r in rs if (r.updated_at or r.created_at)]
        out.append({
            "id": sid,
            "created_at": min(created).isoformat() if created else None,
            "updated_at": max(updated).isoformat() if updated else None,
            "trace_count": len(rs),
            "runs": [_detail(r) for r in rs[:20]],
        })
    out.sort(key=lambda s: s["updated_at"] or "", reverse=True)
    return out[:limit]


def build_snapshot(source_name: str, since_hours: float, limit: int) -> dict:
    from mailroom_ui.langfuse_source import LangfuseSource, enriched_recent_runs
    from mailroom_ui.metrics import compute_metrics
    from mailroom_ui.pipeline_schema import DOC_CLASSES, DOC_SUBCLASS_BY_CLASS, PipelineSchema
    from mailroom_ui.phoenix_source import PhoenixSource
    from mailroom_ui.multi_source import MultiSource
    from server.poller import floor_payload

    if source_name == "phoenix":
        src = PhoenixSource()
    elif source_name in ("both", "multi", "all"):
        src = MultiSource([LangfuseSource(), PhoenixSource()])
    else:
        src = LangfuseSource()

    since_dt = _utcnow() - timedelta(hours=since_hours)
    # Transient cloud blips (read timeouts, 429s) must not silently produce an
    # empty snapshot: bounded retry with backoff, then honest empty.
    runs: list = []
    for attempt in range(1, 4):
        try:
            runs = enriched_recent_runs(src, since=since_dt, limit=limit)
            break
        except Exception as exc:
            if attempt < 3:
                wait = 5 * attempt
                print(f"WARN: source fetch failed ({exc}); retry {attempt}/2 in {wait}s",
                      file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"WARN: source fetch failed after retries ({exc}); "
                      "exporting empty snapshot", file=sys.stderr)

    try:
        schema = PipelineSchema.load()
        doc_classes = getattr(schema, "doc_classes", DOC_CLASSES)
    except Exception:
        doc_classes = DOC_CLASSES

    metrics = compute_metrics(runs, since=since_dt)
    review = [r for r in runs if r.needs_human]
    sessions = _sessions(runs)

    meta = {
        "mode": "snapshot",
        "generated_at": _utcnow().isoformat(),
        "source": source_name,
        "doc_classes": doc_classes,
        "doc_subclasses": {k: list(v) for k, v in DOC_SUBCLASS_BY_CLASS.items()},
        "pipeline_configured": False,
        "endpoints": [
            {"method": "GET", "path": "data/traces.json", "desc": "floor runs; per-run at data/runs/{id}.json"},
            {"method": "GET", "path": "data/metrics.json", "desc": "window aggregates"},
            {"method": "GET", "path": "data/sessions.json", "desc": "session summaries"},
            {"method": "GET", "path": "data/review-queue.json", "desc": "needs_human runs"},
            {"method": "GET", "path": "../debug/build-info.json", "desc": "snapshot provenance for agents"},
        ],
    }
    return {
        "meta": meta,
        "traces": {"count": len(runs), "runs": [floor_payload(r) for r in runs]},
        "runs": {r.trace_id: _detail(r) for r in runs if r.trace_id},
        "metrics": {"source": source_name, **metrics.model_dump()},
        "sessions": {"count": len(sessions), "sessions": sessions},
        "review_queue": {
            "count": len(review),
            "runs": [floor_payload(r) for r in review],
        },
    }


def write_snapshot(snap: dict, out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    runs_dir = out_dir / "runs"
    runs_dir.mkdir(exist_ok=True)

    (out_dir / "meta.json").write_text(json.dumps(snap["meta"], indent=2))
    (out_dir / "traces.json").write_text(json.dumps(snap["traces"], indent=2))
    (out_dir / "metrics.json").write_text(json.dumps(snap["metrics"], indent=2))
    (out_dir / "sessions.json").write_text(json.dumps(snap["sessions"], indent=2))
    (out_dir / "review-queue.json").write_text(json.dumps(snap["review_queue"], indent=2))
    n_run_files = 0
    for tid, detail in snap["runs"].items():
        (runs_dir / f"{_safe_id(tid)}.json").write_text(json.dumps(detail, indent=2))
        n_run_files += 1

    debug_dir = out_dir.parent / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    sha = "?"
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip() or "?"
    except Exception:
        pass
    build_info = {
        "generated_at": snap["meta"]["generated_at"],
        "git_sha": sha,
        "source": snap["meta"]["source"],
        "trace_count": snap["traces"]["count"],
        "run_detail_files": n_run_files,
        "session_count": snap["sessions"]["count"],
        "review_count": snap["review_queue"]["count"],
        "generator": "scripts/export_snapshot.py",
    }
    (debug_dir / "build-info.json").write_text(json.dumps(build_info, indent=2))
    return build_info


def check(out_dir: Path) -> int:
    ok = True
    required = ["meta.json", "traces.json", "metrics.json", "sessions.json", "review-queue.json"]
    for name in required:
        p = out_dir / name
        try:
            json.loads(p.read_text())
            print(f"OK   {p}")
        except Exception as exc:
            ok = False
            print(f"FAIL {p}: {exc}")
    traces = json.loads((out_dir / "traces.json").read_text())
    n = len(traces.get("runs", []))
    if n != traces.get("count"):
        ok = False
        print(f"FAIL traces count mismatch: header={traces.get('count')} actual={n}")
    missing_detail = [
        r["trace_id"] for r in traces.get("runs", [])
        if not (out_dir / "runs" / f"{_safe_id(r['trace_id'])}.json").exists()
    ]
    if missing_detail:
        ok = False
        print(f"FAIL missing run detail files: {missing_detail[:5]}")
    build = out_dir.parent / "debug" / "build-info.json"
    print(("OK   " if build.exists() else "FAIL ") + str(build))
    ok = ok and build.exists()
    print("SNAPSHOT CHECK:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_source = os.environ.get("MAILROOM_SOURCE", "langfuse")
    ap.add_argument("--source", default=default_source,
                    choices=["langfuse", "phoenix", "both", "auto"],
                    help="trace source (default MAILROOM_SOURCE or langfuse)")
    ap.add_argument("--out", default="site/data", help="output dir (default site/data)")
    ap.add_argument("--since-hours", type=float, default=24.0)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--check", action="store_true", help="validate an existing snapshot")
    args = ap.parse_args()

    out_dir = Path(args.out)
    if args.check:
        return check(out_dir)

    source_name = args.source
    if source_name == "auto":
        source_name = os.environ.get("MAILROOM_SOURCE", "langfuse")
    if source_name in ("both", "multi"):
        source_name = "both"

    print(f"exporting snapshot: source={source_name} since={args.since_hours}h limit={args.limit}")
    snap = build_snapshot(source_name, args.since_hours, args.limit)
    info = write_snapshot(snap, out_dir)
    print(json.dumps(info, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
