from __future__ import annotations

from mailroom_ui.models import Stage
from mailroom_ui.reconsideration import (
    CLASS_MISS,
    EXTRACTION_MISS,
    JUDGE_MISS,
    collect_review_causes,
    should_reconsider,
)
from mailroom_ui.trace_interpreter import interpret_trace
from tests.fake_langfuse import make_trace, make_trace_v4


def _run(trace: dict):
    return interpret_trace(trace, trace.get("observations", []), trace.get("scores", []))


def test_high_confidence_archived_correct_is_not_reconsidered():
    run = _run(make_trace("t-ok"))
    assert run.stage == Stage.ARCHIVED
    assert run.classification_confidence >= 0.95
    assert run.review_causes == []
    assert run.needs_reconsideration is False
    assert run.needs_human is False


def test_archived_judge_miss_joins_review_queue():
    run = _run(make_trace("t-miss", verdict="MISS", quality=0.2))
    assert run.stage == Stage.ARCHIVED
    assert JUDGE_MISS in run.review_causes
    assert run.needs_reconsideration is True
    assert run.needs_human is True
    assert run.escalation_reason and "reconsider:" in run.escalation_reason


def test_archived_class_miss_vs_ground_truth():
    run = _run(
        make_trace(
            "t-class-miss",
            doc_type="contract",
            extra_input={"ground_truth": {"expected_hf_class": "correspondence"}},
            extra_metadata={"expected_hf_class": "correspondence"},
        )
    )
    assert CLASS_MISS in run.review_causes
    assert run.needs_human is True


def test_merger_agreement_vs_contract_is_a_class_miss():
    """v0.6.0: MAUD merger_agreement is not equivalent to CUAD contract."""
    run = _run(
        make_trace(
            "t-maud-miss",
            doc_type="contract",
            extra_input={"ground_truth": {"expected_hf_class": "merger_agreement"}},
            extra_metadata={"expected_hf_class": "merger_agreement"},
        )
    )
    assert CLASS_MISS in run.review_causes


def test_merger_agreement_exact_match_is_not_a_class_miss():
    run = _run(
        make_trace(
            "t-maud-hit",
            doc_type="merger_agreement",
            extra_input={"ground_truth": {"expected_hf_class": "merger_agreement"}},
            extra_metadata={"expected_hf_class": "merger_agreement"},
        )
    )
    assert CLASS_MISS not in run.review_causes


def test_extraction_score_below_floor_is_a_miss():
    run = _run(make_trace("t-ext", extra_scores={"extraction_overall_score": 0.41}))
    assert EXTRACTION_MISS in run.review_causes
    assert run.needs_human is True


def test_expected_field_presence_below_floor_is_a_miss():
    run = _run(make_trace("t-presence", extra_scores={"expected_field_presence": 0.2}))
    assert EXTRACTION_MISS in run.review_causes
    assert run.needs_human is True


def test_incomplete_reporting_parks_archived_run():
    from mailroom_ui.reconsideration import REPORTING_INCOMPLETE

    run = _run(make_trace("t-report", extra_scores={"completeness_label": "INCOMPLETE"}))
    assert REPORTING_INCOMPLETE in run.review_causes
    assert run.needs_human is True


def test_v4_archived_miss_also_reconsiders():
    run = _run(make_trace_v4("t-v4-miss", extra_scores={"mailroom-pipeline-judge": "MISS"}))
    assert run.stage == Stage.ARCHIVED
    assert JUDGE_MISS in run.review_causes
    assert run.needs_human is True


def test_failed_stage_is_not_reconsideration():
    run = _run(make_trace("t-fail", stage="failed", verdict="MISS"))
    assert run.needs_human is False
    assert should_reconsider("failed", collect_review_causes(verdict="MISS")) is False


def test_in_flight_miss_does_not_park_on_review_siding():
    causes = collect_review_causes(verdict="MISS")
    assert should_reconsider("extract", causes) is False


def test_metrics_do_not_count_reconsidered_archives_as_clean():
    from mailroom_ui.metrics import compute_metrics

    ok = _run(make_trace("t-ok-m"))
    miss = _run(make_trace("t-arch-miss", verdict="MISS", quality=0.2))
    m = compute_metrics([ok, miss])
    assert m.reconsideration == 1
    assert m.review == 1
    assert m.archived == 1
    assert m.failed == 0


def test_floor_payload_carries_reconsideration_flags():
    from server.poller import floor_payload

    run = _run(make_trace("t-floor-miss", verdict="MISS", quality=0.2))
    payload = floor_payload(run)
    assert payload["needs_reconsideration"] is True
    assert payload["needs_human"] is True
    assert JUDGE_MISS in payload["review_causes"]
    assert payload["escalation_reason"] and "reconsider:" in payload["escalation_reason"]


def test_review_queue_includes_archived_objective_miss():
    from datetime import datetime, timedelta, timezone

    from fastapi.testclient import TestClient

    from mailroom_ui.langfuse_source import LangfuseSource
    from server.main import create_app
    from tests.fake_langfuse import FakeClient

    now = datetime.now(timezone.utc) - timedelta(hours=1)
    traces = [
        make_trace("t-clean", base_time=now),
        make_trace("t-arch-miss", base_time=now, verdict="MISS", quality=0.2),
        make_trace("t-review", stage="review", verdict=None, quality=None, base_time=now),
    ]
    src = LangfuseSource(client=FakeClient(traces))
    with TestClient(create_app(src)) as c:
        queue = c.get("/api/review-queue").json()
        metrics = c.get("/api/metrics?since=86400").json()
    ids = {r["trace_id"] for r in queue["runs"]}
    assert "t-arch-miss" in ids
    assert "t-review" in ids
    assert "t-clean" not in ids
    assert queue["count"] == 2
    assert metrics["reconsideration"] == 1
    miss = next(r for r in queue["runs"] if r["trace_id"] == "t-arch-miss")
    assert JUDGE_MISS in miss["review_causes"]

