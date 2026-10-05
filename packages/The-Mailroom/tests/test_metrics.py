from __future__ import annotations

from datetime import datetime, timedelta

from mailroom_ui.metrics import compute_metrics
from mailroom_ui.trace_interpreter import interpret_trace
from tests.fake_langfuse import make_trace


def _runs():
    runs = []
    for i, stage in enumerate(["archived", "archived", "review", "failed", "processing"]):
        t = make_trace(
            f"t{i}",
            stage=stage,
            doc_type="contract" if i % 2 == 0 else "correspondence",
            verdict="CORRECT" if stage == "archived" else None,
            quality=0.9 if stage == "archived" else None,
            base_time=datetime(2026, 1, 1, 12, 0, 0) + timedelta(minutes=i),
        )
        runs.append(interpret_trace(t, t["observations"], t["scores"]))
    return runs


def test_metrics_counts():
    m = compute_metrics(_runs())
    assert m.total_docs == 5
    assert m.archived == 2
    assert m.review == 1
    assert m.failed == 1
    assert m.in_flight == 1
    assert m.verdict_counts == {"CORRECT": 2}
    assert m.avg_quality == 0.9
    assert m.per_doc_type["contract"] == 3
    assert m.per_doc_type["correspondence"] == 2
    assert m.llm_calls == 10


def test_metrics_since_filter():
    runs = _runs()
    base = datetime(2026, 1, 1, 12, 0, 0)
    m = compute_metrics(runs, since=base + timedelta(minutes=3, seconds=21))
    assert m.total_docs == 2


def test_p95_generation_latency():
    base = datetime(2026, 1, 1, 12, 0, 0)
    runs = []
    for i in range(10):
        t = make_trace(f"t95-{i}", stage="archived", verdict=None, quality=None,
                       base_time=base + timedelta(minutes=i))
        for gen in [o for o in t["observations"] if o.type == "GENERATION"]:
            gen.latency = float(0.1 + i)
        runs.append(interpret_trace(t, t["observations"], t["scores"]))
    m = compute_metrics(runs)
    assert m.p95_generation_latency_s == 9.1


def test_verdict_mix_counts():
    base = datetime(2026, 1, 1, 12, 0, 0)
    runs = []
    for i, verdict in enumerate(["CORRECT", "CORRECT", "PARTIAL", "MISS", None]):
        t = make_trace(
            f"tv-{i}",
            stage="archived" if verdict else "review",
            verdict=verdict,
            quality=0.8 if verdict else None,
            base_time=base + timedelta(minutes=i),
        )
        runs.append(interpret_trace(t, t["observations"], t["scores"]))
    m = compute_metrics(runs)
    assert m.verdict_counts == {"CORRECT": 2, "PARTIAL": 1, "MISS": 1}
    assert m.avg_quality == 0.8


def test_metrics_empty():
    m = compute_metrics([])
    assert m.total_docs == 0
    assert m.p95_generation_latency_s is None
    assert m.avg_latency_s is None
    assert m.avg_quality is None
    assert m.verdict_counts == {}


class TestTzNormalization:
    """V-6/V-7: mixed naive/aware datetimes must never crash the snapshot, and
    window comparisons must convert (not relabel) so non-UTC servers don't
    drop the last hours of runs."""

    def test_parse_dt_normalizes_to_utc(self):
        from datetime import datetime, timedelta, timezone
        from mailroom_ui.trace_interpreter import parse_dt

        # naive input assumed UTC
        naive = parse_dt(datetime(2026, 8, 10, 12, 0, 0))
        assert naive.tzinfo is not None
        assert naive.utcoffset().total_seconds() == 0

        # aware non-UTC input CONVERTED to UTC (V-7: astimezone, not replace)
        aware = datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone(timedelta(hours=9)))
        parsed = parse_dt(aware)
        assert parsed.hour == 3  # 12:00+09:00 == 03:00 UTC

        # ISO string with Z
        assert parse_dt("2026-08-10T12:00:00Z").hour == 12

    def test_compute_metrics_mixed_tz_no_crash(self):
        from datetime import datetime, timedelta, timezone
        from mailroom_ui.metrics import compute_metrics
        from mailroom_ui.models import PipelineRun

        # Timestamps are RELATIVE to now so the 24 h window can never go
        # stale (the original fixed 2026-08-10 dates silently broke the
        # moment real time passed them — a date bomb). The naive/aware mix
        # is preserved: naive == the same UTC instant with tzinfo stripped.
        now_utc = datetime.now(timezone.utc)
        naive_run = PipelineRun(
            trace_id="t1", filename="a.pdf", stage="archived",
            updated_at=now_utc.replace(tzinfo=None, microsecond=0),  # naive
        )
        aware_run = PipelineRun(
            trace_id="t2", filename="b.pdf", stage="failed",
            updated_at=now_utc.astimezone(timezone(timedelta(hours=-5))),
        )
        since = now_utc - timedelta(days=1)
        m = compute_metrics([naive_run, aware_run], since=since)
        assert m.total_docs == 2


class TestGroundedScoreMining:
    """compute_metrics mines the pilot's grounded extraction-quality scores
    (llm-mailroom SCORE_CONFIGS) from PipelineRun.scores."""

    def _run(self, scores: dict):
        from mailroom_ui.models import PipelineRun

        return PipelineRun(trace_id="t", stage="archived", scores=scores)

    def test_grounded_aggregates(self):
        from mailroom_ui.metrics import compute_metrics

        runs = [
            self._run({"extraction_field_score": 0.9,
                       "extraction_overall_score": 0.95,
                       "entity_list_precision": 0.8,
                       "entity_list_recall": 0.7,
                       "extraction_hallucination_rate": 0.02}),
            self._run({"extraction_field_score": 0.6,
                       "entity_list_precision": 0.6}),
        ]
        m = compute_metrics(runs)
        assert m.n_grounded_runs == 2
        assert m.avg_extraction_field_score == 0.75
        assert m.avg_extraction_overall_score == 0.95
        assert m.avg_entity_list_precision == 0.7
        assert m.avg_entity_list_recall == 0.7
        assert m.avg_hallucination_rate == 0.02
        # absent score -> None (never fabricated)
        assert m.avg_expected_field_presence is None

    def test_verified_precision_alias_and_suite_extras(self):
        from mailroom_ui.metrics import compute_metrics

        runs = [
            self._run({
                "extraction_field_score": 0.9,
                "extraction_verified_precision": 0.8,
                "content_topic_accuracy": 1.0,
                "content_topic_f1_macro": 0.9,
                "sentiment_accuracy": 0.5,
                "maud_question_accuracy": 0.7,
                "maud_clause_presence": 1.0,
            }),
            self._run({
                "extraction_overall_verified_precision": 0.6,
                "content_topic_accuracy": 0.5,
            }),
        ]
        m = compute_metrics(runs)
        assert m.avg_extraction_verified_precision == 0.7
        assert m.avg_content_topic_accuracy == 0.75
        assert m.avg_content_topic_f1_macro == 0.9
        assert m.avg_sentiment_accuracy == 0.5
        assert m.avg_maud_question_accuracy == 0.7
        assert m.avg_maud_clause_presence == 1.0
        # absent extras are not fabricated as zeros
        assert m.avg_maud_category_accuracy is None
        assert m.avg_sentiment_f1_macro is None

    def test_per_doc_subclass_counts(self):
        from mailroom_ui.metrics import compute_metrics
        from mailroom_ui.models import PipelineRun

        runs = [
            PipelineRun(trace_id="a", stage="archived", doc_type="contract",
                        doc_subclass="license"),
            PipelineRun(trace_id="b", stage="archived", doc_type="contract",
                        doc_subclass="license"),
            PipelineRun(trace_id="c", stage="archived", doc_type="compliance_filing",
                        doc_subclass="10-K"),
        ]
        m = compute_metrics(runs)
        assert m.per_doc_subclass == {
            "contract/license": 2,
            "compliance_filing/10-K": 1,
        }

    def test_no_grounded_runs(self):
        from mailroom_ui.metrics import compute_metrics

        m = compute_metrics([self._run({})])
        assert m.n_grounded_runs == 0
        assert m.avg_extraction_field_score is None

    def test_non_numeric_scores_ignored(self):
        from mailroom_ui.metrics import compute_metrics

        m = compute_metrics([self._run({"extraction_field_score": "oops"})])
        assert m.avg_extraction_field_score is None


def test_p95_is_nearest_rank():
    from mailroom_ui.metrics import _p95

    assert _p95([float(i) for i in range(1, 31)]) == 29.0  # ceil(0.95*30)=29th
    assert _p95([]) is None


def test_non_finite_scores_do_not_poison_metrics():
    base = datetime(2026, 1, 1, 12, 0, 0)
    t = make_trace("t-nan", stage="archived", base_time=base)
    run = interpret_trace(t, t["observations"], t["scores"])
    run.scores["extraction_field_score"] = float("nan")
    run.quality = float("inf")
    m = compute_metrics([run])
    assert m.avg_extraction_field_score is None
    assert m.avg_quality is None
    import json

    json.dumps(m.model_dump(), allow_nan=False)  # would raise on NaN
