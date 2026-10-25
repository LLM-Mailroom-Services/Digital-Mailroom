#!/usr/bin/env python3
"""Static FakeClient floor for v0.3.0 release stills and desk recordings.

Serves the same display API the pixel console / Observatory / TUI already
read (`/api` + `/ws`). Traces are fixture-shaped like the test suite — not
a canned UI fallback.

    PYTHONPATH=. python scripts/demo_v030_cast.py --port 8006
    # pixel        → http://127.0.0.1:8006/?api=
    # Observatory  → http://127.0.0.1:8006/live?api=

Cast (matter ``v030-release``):
  * inbox hopper (stage=inbox)
  * in-flight classify + extract
  * parked REVIEW with ``doc_id`` (Approve/Reject/Requeue forms)
  * archived judge MISS parked as RECONSIDER (high self-reported confidence)
  * archived CORRECT contract
  * failed corporate record

``MAILROOM_PIPELINE_URL`` is left unset so resolve posts show the honest 503.
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
# Resolve demos must show the unconfigured 503, never a live producer POST.
os.environ.pop("MAILROOM_PIPELINE_URL", None)
os.environ.pop("MAILROOM_PIPELINE_API", None)
os.environ.pop("MAILROOM_PIPELINE_TOKEN", None)
os.environ.pop("MAILROOM_API_TOKEN", None)

MATTER = "v030-release"


def _now():
    return datetime.now(timezone.utc)


def build_cast(base_time: datetime | None = None) -> list[dict[str, Any]]:
    from tests.fake_langfuse import make_trace

    t0 = base_time or _now()
    tags = ["mailroom", "pilot", "run-1", "source-demo_v030_cast"]
    common = dict(matter_id=MATTER, session_id=MATTER, environment="pilot",
                  tags=tags, base_time=t0, user_id="release-demo",
                  release="the-mailroom@0.3.0")
    return [
        make_trace(
            "v030-inbox",
            filename="inbox_scan_correspondence_07.pdf",
            stage="inbox",
            doc_type="correspondence",
            class_conf=0.0,
            extract_conf=0.0,
            verdict=None,
            quality=None,
            span_names=["intake-document"],
            output_extra={"doc_id": "doc-inbox-07"},
            **common,
        ),
        make_trace(
            "v030-classify",
            filename="insurance_claim_fnol_package_01.pdf",
            stage="classify",
            doc_type="insurance_claim",
            class_conf=0.88,
            extract_conf=0.0,
            verdict=None,
            quality=None,
            span_names=["intake-document", "classify-document"],
            doc_subclass="fnol",
            output_extra={"doc_id": "doc-claim-01"},
            **common,
        ),
        make_trace(
            "v030-extract",
            filename="contract_service_agreement_03.pdf",
            stage="extract",
            doc_type="contract",
            class_conf=0.97,
            extract_conf=0.82,
            verdict=None,
            quality=None,
            span_names=["intake-document", "classify-document", "extract-fields"],
            doc_subclass="service_agreement",
            contract_subtype="Service Agreement",
            output_extra={"doc_id": "doc-contract-03"},
            **common,
        ),
        make_trace(
            "v030-review",
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
            "v030-reconsider",
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
        make_trace(
            "v030-archived",
            filename="corporate_minutes_board_2026_q1.pdf",
            stage="archived",
            doc_type="corporate_record",
            class_conf=0.96,
            extract_conf=0.94,
            verdict="CORRECT",
            quality=0.95,
            output_extra={"doc_id": "doc-minutes-q1"},
            **common,
        ),
        make_trace(
            "v030-failed",
            filename="corporate_articles_of_incorporation_02.pdf",
            stage="failed",
            doc_type="corporate_record",
            class_conf=0.91,
            extract_conf=0.40,
            verdict="MISS",
            quality=0.22,
            output_extra={
                "doc_id": "doc-articles-02",
                "error_message": "extraction failed: LLM output not valid JSON",
                "run_aborted": True,
            },
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


def serve(port: int, host: str) -> None:
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

    print(f"v0.3.0 cast  {len(traces)} traces  matter={MATTER}")
    print(f"pixel        →  http://{host}:{port}/?api=")
    print(f"observatory  →  http://{host}:{port}/live?api=")
    uvicorn.run(app, host=host, port=port, log_level="warning")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8006)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--check", action="store_true",
                        help="interpret the cast and exit")
    args = parser.parse_args()
    traces = build_cast()
    from mailroom_ui.trace_interpreter import interpret_trace

    runs = [
        interpret_trace(t, t.get("observations", []), t.get("scores", []))
        for t in traces
    ]
    by_id = {r.trace_id: r for r in runs}
    assert by_id["v030-inbox"].stage.value == "inbox"
    assert by_id["v030-classify"].stage.value == "classify"
    assert by_id["v030-extract"].stage.value == "extract"
    assert by_id["v030-review"].stage.value == "review"
    assert by_id["v030-review"].doc_id == "doc-merger-42"
    assert by_id["v030-review"].needs_human
    assert by_id["v030-reconsider"].needs_reconsideration
    assert by_id["v030-reconsider"].needs_human
    assert by_id["v030-archived"].needs_human is False
    assert by_id["v030-failed"].stage.value == "failed"
    if args.check:
        print(f"matter {MATTER}  ({len(runs)} docs)")
        for run in runs:
            print(f"  {run.trace_id:18} {run.stage.value:12} {run.filename}  "
                  f"doc_id={run.doc_id} human={run.needs_human}")
        print("check ok")
        return
    serve(args.port, args.host)


if __name__ == "__main__":
    main()
