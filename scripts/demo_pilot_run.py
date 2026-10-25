#!/usr/bin/env python3
"""Stagger a fake Langfuse pilot so envelopes actually travel the conveyor.

The pixel floor and Observatory still read `/api/*` + `/ws` only — this
script is a *source* (the same FakeClient the tests use), not a canned UI
fallback. Use it to record a pilot-run demo:

    PYTHONPATH=. python scripts/demo_pilot_run.py --port 8005 --delay 8
    # then open http://127.0.0.1:8005/?api=

`--check` prints the cast and schedule without serving.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Fast poll + no per-trace floor cache so stage changes show up immediately.
os.environ.setdefault("MAILROOM_POLL_INTERVAL", "0.4")

MATTER = "pilot-run-2026-08-25"

CAST: dict[str, dict[str, Any]] = {
    "contract": {
        "filename": "contract_service_agreement_03.pdf",
        "doc_type": "contract",
        "class_conf": 0.98,
        "extract_conf": 0.96,
        "verdict": "CORRECT",
        "quality": 0.97,
    },
    "claim": {
        "filename": "insurance_claim_fnol_package_01.pdf",
        "doc_type": "insurance_claim",
        "class_conf": 0.96,
        "extract_conf": 0.91,
        "verdict": "CORRECT",
        "quality": 0.93,
    },
    "merger": {
        "filename": "maud_merger_agreement_all_stock_42.pdf",
        "doc_type": "merger_agreement",
        "class_conf": 0.93,
        "extract_conf": 0.61,
        "verdict": "PARTIAL",
        "quality": 0.44,
        "escalation": "low extraction confidence (0.61) on indemnification clause",
    },
    "letter": {
        "filename": "correspondence_demand_letter_09.pdf",
        "doc_type": "correspondence",
        "class_conf": 0.94,
        "extract_conf": 0.81,
        "verdict": "PARTIAL",
        "quality": 0.72,
    },
    "articles": {
        "filename": "corporate_articles_of_incorporation_02.pdf",
        "doc_type": "corporate_record",
        "class_conf": 0.91,
        "extract_conf": 0.40,
        "verdict": "MISS",
        "quality": 0.22,
        "error": "extraction failed: LLM output not valid JSON",
    },
    "incoming": {
        "filename": "inbox_scan_correspondence_07.pdf",
        "doc_type": "correspondence",
        "class_conf": 0.0,
        "extract_conf": 0.0,
        "verdict": None,
        "quality": None,
    },
}

# (seconds_from_go, action, cast_key, extra)
# action: spawn | stage
SCHEDULE: list[tuple[float, str, str, dict[str, Any]]] = [
    (0.0, "spawn", "incoming", {"stage": "inbox"}),
    (0.0, "spawn", "contract", {"stage": "intake"}),
    (2.2, "stage", "contract", {"stage": "classify"}),
    (3.0, "spawn", "claim", {"stage": "intake"}),
    (5.0, "stage", "contract", {"stage": "extract"}),
    (5.2, "stage", "claim", {"stage": "classify"}),
    (7.0, "spawn", "merger", {"stage": "intake"}),
    (8.0, "stage", "contract", {"stage": "judge_verify"}),
    (10.0, "stage", "claim", {"stage": "extract"}),
    (10.2, "stage", "merger", {"stage": "classify"}),
    (12.0, "stage", "contract", {"stage": "report"}),
    (13.0, "spawn", "letter", {"stage": "intake"}),
    (14.0, "stage", "claim", {"stage": "judge_verify"}),
    (14.2, "stage", "merger", {"stage": "extract"}),
    (16.0, "stage", "contract", {"stage": "catalog"}),
    (16.2, "stage", "letter", {"stage": "classify"}),
    (18.0, "stage", "contract", {"stage": "archived", "stamp": True}),
    (18.2, "stage", "merger", {"stage": "review", "stamp": True}),
    (18.4, "stage", "claim", {"stage": "report"}),
    (20.0, "stage", "letter", {"stage": "extract"}),
    (20.5, "spawn", "articles", {"stage": "intake"}),
    (22.0, "stage", "claim", {"stage": "catalog"}),
    (22.2, "stage", "articles", {"stage": "classify"}),
    (24.0, "stage", "claim", {"stage": "archived", "stamp": True}),
    (24.2, "stage", "letter", {"stage": "judge_verify"}),
    (26.0, "stage", "articles", {"stage": "extract"}),
    (26.5, "stage", "letter", {"stage": "arbiter"}),
    (28.5, "stage", "articles", {"stage": "failed", "stamp": True}),
    (29.0, "stage", "letter", {"stage": "report"}),
    (31.5, "stage", "letter", {"stage": "catalog"}),
    (34.0, "stage", "letter", {"stage": "archived", "stamp": True}),
]


def _now():
    return datetime.now(timezone.utc)


def spawn(traces: list[dict], key: str, stage: str = "intake") -> dict:
    from tests.fake_langfuse import make_trace

    spec = CAST[key]
    trace = make_trace(
        f"pilot-{key}",
        filename=spec["filename"],
        matter_id=MATTER,
        session_id=MATTER,
        environment="pilot",
        tags=["mailroom", "pilot", "run-1", "source-demo_pilot_run"],
        stage=stage,
        doc_type=spec["doc_type"],
        class_conf=spec["class_conf"],
        extract_conf=spec.get("extract_conf") if stage not in ("intake", "classify") else None,
        verdict=None,
        quality=None,
        base_time=_now(),
        span_names=["intake-document"],
    )
    trace["updated_at"] = _now()
    traces.append(trace)
    return trace


def set_stage(trace: dict, stage: str, *, stamp: bool = False) -> None:
    spec_key = trace["id"].removeprefix("pilot-")
    spec = CAST[spec_key]
    out = trace.setdefault("output", {})
    out["stage"] = stage
    if stage in ("extract", "retry_extract", "judge_verify", "arbiter",
                 "report", "catalog", "archive", "archived", "review", "failed"):
        out["extraction_confidence"] = spec["extract_conf"]
    if stage == "review":
        out["review_decision"] = "human review"
        out["escalation_reason"] = spec.get("escalation") or "low confidence"
    if stage == "failed":
        out["error_message"] = spec.get("error") or "run aborted"
        out["run_aborted"] = True
    if stamp:
        from tests.fake_langfuse import Obj

        scores = trace.setdefault("scores", [])
        names = {getattr(s, "name", None) for s in scores}
        if spec.get("verdict") and "mailroom-pipeline-judge" not in names:
            scores.append(Obj(name="mailroom-pipeline-judge",
                              value=spec["verdict"], data_type="CATEGORICAL"))
        if spec.get("quality") is not None and "mailroom-pipeline-quality" not in names:
            scores.append(Obj(name="mailroom-pipeline-quality",
                              value=spec["quality"], data_type="NUMERIC"))
    trace["updated_at"] = _now()


def apply_event(traces: list[dict], action: str, key: str, extra: dict) -> dict:
    if action == "spawn":
        return spawn(traces, key, extra.get("stage", "intake"))
    found = next((t for t in traces if t["id"] == f"pilot-{key}"), None)
    if found is None:
        found = spawn(traces, key, "intake")
    set_stage(found, extra["stage"], stamp=bool(extra.get("stamp")))
    return found


def run_director(traces: list[dict], delay: float, log=print) -> None:
    log(f"pilot director: waiting {delay:.1f}s for the floor to connect…")
    time.sleep(delay)
    t0 = time.monotonic()
    log(f"pilot director: GO  matter={MATTER}  events={len(SCHEDULE)}")
    for when, action, key, extra in SCHEDULE:
        wait = t0 + when - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        trace = apply_event(traces, action, key, extra)
        stage = (trace.get("output") or {}).get("stage")
        log(f"  t={when:5.1f}s  {action:5}  {trace['input']['filename']:<42} → {stage}")
    log("pilot director: complete — holding final state (merger on REVIEW, others terminal)")


def _patch_poller() -> None:
    """Stage changes must not sit behind the 60s detail cache."""
    from server.poller import PollHub

    orig = PollHub.__init__

    def init(self, source, **kw):
        kw["detail_ttl"] = 0.0
        orig(self, source, **kw)

    PollHub.__init__ = init  # type: ignore[method-assign]


def serve(port: int, delay: float, host: str) -> None:
    _patch_poller()
    from mailroom_ui.langfuse_source import LangfuseSource
    from server.main import create_app
    from tests.fake_langfuse import FakeClient

    traces: list[dict] = []
    src = LangfuseSource(
        client=FakeClient(traces),
        cache_ttl=0.2,
        poll_cache_ttl=0.2,
        run_cache_ttl=0.2,
    )
    app = create_app(src)
    threading.Thread(target=run_director, args=(traces, delay), daemon=True).start()
    import uvicorn

    print(f"pilot floor  →  http://{host}:{port}/?api=")
    print(f"observatory  →  http://{host}:{port}/live?api=")
    uvicorn.run(app, host=host, port=port, log_level="warning")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8005)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--delay", type=float, default=8.0,
                        help="seconds to wait after boot before the first envelope")
    parser.add_argument("--check", action="store_true",
                        help="print the cast/schedule and exit")
    args = parser.parse_args()
    if args.check:
        print(f"matter {MATTER}  ({len(CAST)} docs, {len(SCHEDULE)} events, "
              f"{SCHEDULE[-1][0]:.0f}s of motion)")
        for key, spec in CAST.items():
            print(f"  {key:10} {spec['filename']}")
        for when, action, key, extra in SCHEDULE:
            print(f"  {when:5.1f}s  {action:5}  {key:10}  {extra}")
        traces: list[dict] = []
        for when, action, key, extra in SCHEDULE:
            apply_event(traces, action, key, extra)
        assert len(traces) == len(CAST)
        print("check ok")
        return
    serve(args.port, args.delay, args.host)


if __name__ == "__main__":
    main()
