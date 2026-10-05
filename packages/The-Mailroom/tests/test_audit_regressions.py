"""Regression tests for the 0.5.0 audit (quiet + loud failures in the data core).

Each test names the failure it pins: the pre-fix behaviour crashed, served a
wrong-but-plausible value, or hid an outage behind an empty result.
"""

from __future__ import annotations

import json
import urllib.error
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from mailroom_ui.langfuse_source import LangfuseSource, LangfuseUnavailable, TTLCache
from mailroom_ui.multi_source import MultiSource
from mailroom_ui.review_actions import ReviewActionError, _request_json
from mailroom_ui.sources import TraceSourceUnavailable
from mailroom_ui.trace_interpreter import interpret_trace
from tests.fake_langfuse import FakeClient, Obj, make_trace, make_trace_v4


def _run(trace, **kw):
    return interpret_trace(trace, trace.get("observations"), trace.get("scores"), **kw)


# ---------------------------------------------------------------- interpreter

def test_observation_without_start_time_does_not_crash_sort():
    """Aware timestamps sorted against a naive datetime.min raised TypeError."""
    trace = make_trace("t-nostart")
    trace["observations"].append(Obj(id="x", name="write-catalog", type="SPAN", start_time=None))
    run = _run(trace)
    assert run.trace_id == "t-nostart"


def test_list_payload_observation_ids_are_not_fake_spans():
    """The trace LIST API embeds observation ids; they became 'observation' spans."""
    trace = make_trace("t-ids")
    trace["observations"] = ["obs-1", "obs-2", "obs-3"]
    trace["scores"] = ["score-1"]
    run = interpret_trace(trace)
    assert run.spans == []
    assert run.generations == []


def test_non_numeric_attempt_does_not_abort_interpretation():
    trace = make_trace("t-attempt", extra_metadata={"attempt": "retry-1"})
    trace["input"].pop("attempt", None)
    run = _run(trace)
    assert run.attempt is None


def test_nan_confidence_and_zero_confidence():
    trace = make_trace("t-nan", extra_scores={"classification_confidence": float("nan")})
    run = _run(trace)
    # NaN is dropped, so the trace-output confidence (0.98) wins — and the
    # payload stays JSON-serialisable.
    assert run.classification_confidence == pytest.approx(0.98)
    json.dumps(run.model_dump(mode="json"), allow_nan=False)

    zero = make_trace("t-zero", extract_conf=0.0)
    assert _run(zero).extraction_confidence == 0.0


def test_json_string_span_io_is_parsed():
    trace = make_trace("t-json")
    for obs in trace["observations"]:
        if getattr(obs, "name", "") == "classify-document":
            obs.output = json.dumps({"stage": "classified", "doc_subclass": "license"})
    run = _run(trace)
    span = next(s for s in run.spans if s.name == "classify-document")
    assert span.output and span.output.get("doc_subclass") == "license"


def test_scores_from_an_earlier_run_are_dropped():
    """A reused trace id kept the previous attempt's MISS verdict."""
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    trace = make_trace("t-rerun", base_time=base + timedelta(hours=2), verdict=None, quality=None)
    old_run = make_trace("t-rerun", base_time=base, verdict=None, quality=None)
    trace["observations"] = [*old_run["observations"], *trace["observations"]]
    trace["scores"].append({
        "name": "mailroom-pipeline-judge",
        "value": "MISS",
        "data_type": "CATEGORICAL",
        "timestamp": (base + timedelta(seconds=30)).isoformat(),
    })
    run = _run(trace)
    assert run.verdict is None
    assert "judge_miss" not in run.review_causes


def test_v4_usage_details_and_calculated_cost():
    trace = make_trace_v4("t-v4-usage")
    trace["observations"].append({
        "id": "gen-x",
        "name": "classify-generation",
        "observationType": "GENERATION",
        "startTime": trace["timestamp"],
        "usageDetails": {"input": 10, "output": 5, "total": 15},
        "calculatedTotalCost": 0.25,
        "promptName": "mailroom-sorter",
        "promptVersion": 12,
    })
    run = _run(trace)
    gen = next(g for g in run.generations if g.name == "classify-generation")
    assert gen.usage_total_tokens == 15
    assert gen.cost_usd == pytest.approx(0.25)
    assert gen.prompt_version == "mailroom-sorter@12"


def test_light_run_uses_trace_level_cost():
    trace = make_trace("t-light")
    trace["totalCost"] = 0.0123
    trace.pop("observations")
    trace.pop("scores")
    run = interpret_trace(trace)
    assert run.cost_usd == pytest.approx(0.0123)


# -------------------------------------------------------------------- source

def test_ttl_cache_evicts_expired_and_caps_size():
    cache = TTLCache(max_entries=10)
    for i in range(50):
        cache.set(f"k{i}", i, ttl=-1)  # already expired
    assert len(cache) <= 10
    for i in range(30):
        cache.set(f"live{i}", i, ttl=60)
    assert len(cache) <= 10


class _FailingObs:
    def get_many(self, **kw):
        err = RuntimeError("rate limited")
        err.status = 429
        raise err


def test_observation_outage_raises_and_is_not_cached():
    client = FakeClient([make_trace("t-obs")])
    client.api.observations = _FailingObs()
    src = LangfuseSource(client=client, cache_ttl=60, poll_cache_ttl=60)
    # The harvested list payload embeds full observation dicts in the fake,
    # so strip them to model the real list API (ids only).
    client.traces[0]["observations"] = ["o1", "o2"]
    with pytest.raises(LangfuseUnavailable):
        src.get_observations("t-obs")
    assert src.cache.get("obs:t-obs") is None


class _Trace429:
    def list(self, **kw):
        return Obj(data=[])

    def get(self, trace_id, **kw):
        err = RuntimeError("Too Many Requests")
        err.status_code = 429
        raise err


class _Trace404(_Trace429):
    def get(self, trace_id, **kw):
        err = RuntimeError("Trace not found")
        err.status_code = 404
        raise err


def test_get_trace_rate_limit_is_an_outage_not_a_404():
    client = FakeClient([])
    client.api.trace = _Trace429()
    src = LangfuseSource(client=client)
    with pytest.raises(LangfuseUnavailable):
        src.get_trace("missing")


def test_get_trace_real_404_is_none():
    client = FakeClient([])
    client.api.trace = _Trace404()
    src = LangfuseSource(client=client)
    assert src.get_trace("missing") is None


class _Dead:
    def list_traces(self, **kw):
        raise TraceSourceUnavailable("down")

    def get_run(self, trace_id, **kw):
        raise TraceSourceUnavailable("down")

    def health(self):
        return {"source": "dead", "ok": False}


def test_multi_source_total_outage_raises_instead_of_empty_floor():
    multi = MultiSource([_Dead(), _Dead()])
    with pytest.raises(TraceSourceUnavailable):
        multi.list_traces()
    with pytest.raises(TraceSourceUnavailable):
        multi.get_run("t")
    assert multi.health()["source"] == "dead+dead"


def test_multi_source_partial_outage_still_serves():
    live = LangfuseSource(client=FakeClient([make_trace("t-live")]))
    multi = MultiSource([live, _Dead()])
    assert [t["id"] for t in multi.list_traces()] == ["t-live"]


# ------------------------------------------------------------ review proxy

def test_producer_timeout_is_504_not_500():
    with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        with pytest.raises(ReviewActionError) as exc:
            _request_json("GET", "http://producer/v1/lookup")
    assert exc.value.status == 504


def test_producer_url_timeout_is_504():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError(TimeoutError())):
        with pytest.raises(ReviewActionError) as exc:
            _request_json("GET", "http://producer/v1/lookup")
    assert exc.value.status == 504


class _Resp:
    def __init__(self, body: bytes):
        self._body = body
        self.headers = {}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_producer_non_json_body_is_502():
    with patch("urllib.request.urlopen", return_value=_Resp(b"<html>bad gateway</html>")):
        with pytest.raises(ReviewActionError) as exc:
            _request_json("GET", "http://producer/v1/lookup")
    assert exc.value.status == 502
