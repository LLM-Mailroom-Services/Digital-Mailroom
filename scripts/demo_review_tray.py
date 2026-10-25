#!/usr/bin/env python3
"""Working REVIEW-tray demo: FakeClient Langfuse + in-process producer stub.

The visualizer proxies Approve / Reject / Record / Requeue / Complete, class
correction, and the parked-text pane through the real ``/api/review/*``
handlers to a fake llm-mailroom on ``MAILROOM_PIPELINE_URL`` (``/v1``).
Document *display* is still FakeClient traces — not a canned UI fallback.

    PYTHONPATH=. python scripts/demo_review_tray.py --check
    PYTHONPATH=. python scripts/demo_review_tray.py --check-api
    PYTHONPATH=. python scripts/demo_review_tray.py --port 8006
    # pixel        → http://127.0.0.1:8006/?api=
    # Observatory  → http://127.0.0.1:8006/live?api=
    # TUI          → MAILROOM_API_URL=http://127.0.0.1:8006 mailroom-tui

Cast (matter ``review-tray-demo``):
  * parked REVIEW merger (resume + class correction)
  * parked REVIEW insurance FNOL (Complete with extracted_data)
  * archived judge-MISS RECONSIDER (record-only)
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("MAILROOM_POLL_INTERVAL", "0.4")

MATTER = "review-tray-demo"
DEMO_TOKEN = "demo-review-token"


def _now():
    return datetime.now(timezone.utc)


def build_cast(base_time: datetime | None = None) -> list[dict[str, Any]]:
    from tests.fake_langfuse import make_trace

    t0 = base_time or _now()
    tags = ["mailroom", "pilot", "run-1", "source-demo_review_tray"]
    common = dict(matter_id=MATTER, session_id=MATTER, environment="pilot",
                  tags=tags, base_time=t0, user_id="review-demo",
                  release="the-mailroom@0.3.0")
    return [
        make_trace(
            "tray-review",
            filename="maud_merger_agreement_all_stock_42.pdf",
            stage="review",
            doc_type="merger_agreement",
            class_conf=0.93,
            extract_conf=0.61,
            verdict="PARTIAL",
            quality=0.44,
            span_names=[
                "intake-document", "classify-document", "extract-fields",
                "route-for-review",
            ],
            output_extra={
                "doc_id": "doc-merger-42",
                "review_decision": "human review",
                "escalation_reason": "low extraction confidence (0.61) on indemnification clause",
            },
            **common,
        ),
        make_trace(
            "tray-complete",
            filename="insurance_claim_fnol_package_01.pdf",
            stage="review",
            doc_type="insurance_claim",
            class_conf=0.91,
            extract_conf=0.55,
            verdict="PARTIAL",
            quality=0.48,
            span_names=[
                "intake-document", "classify-document", "extract-fields",
                "route-for-review",
            ],
            doc_subclass="fnol",
            output_extra={
                "doc_id": "doc-claim-fnol",
                "review_decision": "human review",
                "escalation_reason": "partial FNOL extraction — operator can Complete with extracted_data",
            },
            **common,
        ),
        make_trace(
            "tray-reconsider",
            filename="insurance_claim_cms_synpuf_miss.pdf",
            stage="archived",
            doc_type="insurance_claim",
            class_conf=0.99,
            extract_conf=0.97,
            verdict="MISS",
            quality=0.18,
            extra_scores={"extraction_overall_score": 0.31},
            output_extra={"doc_id": "doc-claim-miss"},
            extra_input={"ground_truth": {"expected_hf_class": "insurance_claim"}},
            **common,
        ),
    ]


def _patch_poller() -> None:
    from server.poller import PollHub

    orig = PollHub.__init__

    def init(self, source, **kw):
        kw["detail_ttl"] = 0.0
        orig(self, source, **kw)

    PollHub.__init__ = init  # type: ignore[method-assign]


def _start_producer(host: str, port: int):
    from tests.fake_producer import FakeProducerStore, create_fake_producer, serve_in_thread

    store = FakeProducerStore()
    app = create_fake_producer(store, token=DEMO_TOKEN)
    server, bound, _thread = serve_in_thread(app, host=host, port=port)
    return server, bound, store


def _point_visualizer_at_producer(url: str) -> dict[str, str | None]:
    keys = (
        "MAILROOM_PIPELINE_URL",
        "MAILROOM_PIPELINE_TOKEN",
        "MAILROOM_PIPELINE_API_PREFIX",
        "MAILROOM_PIPELINE_API",
        "MAILROOM_API_TOKEN",
    )
    prev = {k: os.environ.get(k) for k in keys}
    os.environ["MAILROOM_PIPELINE_URL"] = url
    os.environ["MAILROOM_PIPELINE_TOKEN"] = DEMO_TOKEN
    os.environ["MAILROOM_PIPELINE_API_PREFIX"] = "/v1"
    os.environ.pop("MAILROOM_PIPELINE_API", None)
    os.environ.pop("MAILROOM_API_TOKEN", None)
    return prev


def _restore_env(prev: dict[str, str | None]) -> None:
    for key, value in prev.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def check_cast() -> list[Any]:
    from mailroom_ui.trace_interpreter import interpret_trace

    traces = build_cast()
    runs = [
        interpret_trace(t, t.get("observations", []), t.get("scores", []))
        for t in traces
    ]
    by_id = {r.trace_id: r for r in runs}
    assert by_id["tray-review"].stage.value == "review"
    assert by_id["tray-review"].doc_id == "doc-merger-42"
    assert by_id["tray-review"].needs_human
    assert by_id["tray-complete"].doc_id == "doc-claim-fnol"
    assert by_id["tray-complete"].needs_human
    assert by_id["tray-reconsider"].needs_reconsideration
    assert by_id["tray-reconsider"].needs_human
    return runs


def check_api(producer_host: str, producer_port: int) -> None:
    """Exercise visualizer /api/review/* against the fake producer over HTTP."""
    from fastapi.testclient import TestClient

    from mailroom_ui.langfuse_source import LangfuseSource
    from server.main import create_app
    from tests.fake_langfuse import FakeClient
    from tests.fake_producer import pick_port

    port = producer_port if producer_port > 0 else pick_port(producer_host)
    server, bound, _store = _start_producer(producer_host, port)
    prev = _point_visualizer_at_producer(f"http://{producer_host}:{bound}")
    src = LangfuseSource(client=FakeClient(build_cast()), cache_ttl=0.2,
                         poll_cache_ttl=0.2, run_cache_ttl=0.2)
    try:
        with TestClient(create_app(src)) as c:
            health = c.get("/api/health").json()
            assert health["pipeline_configured"] is True, health
            pipe = c.get("/api/pipeline").json()
            assert pipe["configured"] is True and pipe["watcher"] == "live", pipe
            ctx = c.get("/api/review/context", params={"trace_id": "tray-review"}).json()
            assert ctx["configured"] is True
            assert ctx["document"]["doc_id"] == "doc-merger-42"
            assert ctx["document"]["original_filename"].endswith(".pdf")
            src_json = c.get("/api/review/source", params={"trace_id": "tray-review"}).json()
            assert src_json["configured"] is True
            assert src_json["source"] == "lookup"
            assert "Helios Holdings" in (src_json.get("text") or "")
            dl = c.get("/api/review/source", params={"doc_id": "doc-merger-42", "download": True})
            assert dl.status_code == 404
            rec = c.post("/api/review/resolve", json={
                "trace_id": "tray-reconsider",
                "decision": "approved",
                "disposition": "record",
                "notes": "paper trail from demo --check-api",
            }).json()
            assert rec["disposition"] == "record", rec
            resumed = c.post("/api/review/resolve", json={
                "trace_id": "tray-review",
                "decision": "approved",
                "disposition": "resume",
                "doc_type": "merger_agreement",
                "notes": "class confirmed",
            }).json()
            assert resumed["disposition"] == "resume"
            assert resumed.get("resume", {}).get("doc_type") == "merger_agreement"
            done = c.post("/api/review/resolve", json={
                "doc_id": "doc-claim-fnol",
                "decision": "approved",
                "disposition": "complete",
                "extracted_data": {
                    "claim_number": "CL-4419",
                    "coverage_determination": "approved",
                },
            }).json()
            assert done["disposition"] == "complete", done
            audit = c.get("/api/review/audit", params={"doc_id": "doc-claim-fnol"}).json()
            assert audit["count"] >= 1
            print("check-api ok")
            print(f"  lookup     doc-merger-42  source=lookup")
            print(f"  record     doc-claim-miss")
            print(f"  resume     doc-merger-42  override_doc_type=merger_agreement")
            print(f"  complete   doc-claim-fnol")
    finally:
        from tests.fake_producer import stop_server
        stop_server(server)
        _restore_env(prev)


def serve(port: int, host: str, producer_port: int) -> None:
    from tests.fake_producer import pick_port

    pport = producer_port if producer_port > 0 else pick_port(host)
    server, bound, _store = _start_producer(host, pport)
    _point_visualizer_at_producer(f"http://{host}:{bound}")
    _patch_poller()
    from mailroom_ui.langfuse_source import LangfuseSource
    from server.main import create_app
    from tests.fake_langfuse import FakeClient

    traces = build_cast()
    src = LangfuseSource(
        client=FakeClient(traces),
        cache_ttl=0.2,
        poll_cache_ttl=0.2,
        run_cache_ttl=0.2,
    )
    app = create_app(src)
    import uvicorn

    print(f"review-tray demo  {len(traces)} traces  matter={MATTER}")
    print(f"producer          →  http://{host}:{bound}/v1/health  (token={DEMO_TOKEN})")
    print(f"pixel             →  http://{host}:{port}/?api=")
    print(f"observatory       →  http://{host}:{port}/live?api=")
    print("REVIEW: parked merger (resume) · FNOL (complete) · reconsider (record)")
    try:
        uvicorn.run(app, host=host, port=port, log_level="warning")
    finally:
        from tests.fake_producer import stop_server
        stop_server(server)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8006)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--producer-port", type=int, default=0,
                        help="fake llm-mailroom port (0 = ephemeral)")
    parser.add_argument("--check", action="store_true",
                        help="interpret the cast and exit")
    parser.add_argument("--check-api", action="store_true",
                        help="hit /api/review/* against the fake producer and exit")
    args = parser.parse_args()
    runs = check_cast()
    if args.check:
        print(f"matter {MATTER}  ({len(runs)} docs)")
        for run in runs:
            print(f"  {run.trace_id:18} {run.stage.value:12} {run.filename}  "
                  f"doc_id={run.doc_id} human={run.needs_human}")
        print("check ok")
        return
    if args.check_api:
        check_api(args.host, args.producer_port)
        return
    serve(args.port, args.host, args.producer_port)


if __name__ == "__main__":
    main()
