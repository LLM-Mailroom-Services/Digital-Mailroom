from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from mailroom_ui.langfuse_source import (
    DEFAULT_LANGFUSE_HOST,
    LangfuseSource,
    LangfuseUnavailable,
    langfuse_host,
    list_recent_runs,
)
from mailroom_ui.models import PipelineRun
from tests.fake_langfuse import FakeClient, Obj, make_trace


def _source(traces, cache_ttl=0, poll_cache_ttl=0):
    return LangfuseSource(client=FakeClient(traces), cache_ttl=cache_ttl, poll_cache_ttl=poll_cache_ttl)


def test_langfuse_host_accepts_base_url_alias(monkeypatch):
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)
    assert langfuse_host() == DEFAULT_LANGFUSE_HOST
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")
    assert langfuse_host() == "https://us.cloud.langfuse.com"
    monkeypatch.setenv("LANGFUSE_HOST", "https://example.invalid")
    assert langfuse_host() == "https://example.invalid"


def test_list_traces_returns_dicts():
    src = _source([make_trace("t1"), make_trace("t2")])
    traces = src.list_traces()
    assert len(traces) == 2
    assert traces[0]["id"] == "t1"


def test_get_run_full():
    src = _source([make_trace("t1")])
    run = src.get_run("t1")
    assert run is not None
    assert run.trace_id == "t1"
    assert run.generations[0].model == "qwen/qwen3.7-flash"


def test_get_run_missing():
    src = _source([])
    assert src.get_run("nope") is None


def test_list_recent_runs_newest_first():
    base = datetime(2026, 1, 1, 12, 0, 0)
    t_old = make_trace("t-old", base_time=base - timedelta(hours=5))
    t_new = make_trace("t-new", base_time=base)
    src = _source([t_old, t_new])
    runs = list_recent_runs(src, since=base - timedelta(hours=6), limit=10)
    assert [r.trace_id for r in runs] == ["t-new", "t-old"]


def test_sessions():
    src = _source([make_trace("t1", matter_id="M-1"), make_trace("t2", matter_id="M-2")])
    sessions = src.list_sessions()
    assert len(sessions) == 2
    traces = src.get_session_traces("M-1")
    assert len(traces) == 1


def test_v4_session_get_uses_traces_and_no_limit_argument():
    trace = make_trace("t-v4-session", matter_id="M-V4")
    client = FakeClient([trace])

    class V4Sessions:
        def get(self, session_id):
            assert session_id == "M-V4"
            return Obj(id=session_id, traces=[trace])

    client.api.sessions = V4Sessions()
    src = LangfuseSource(client=client, cache_ttl=0, poll_cache_ttl=0)

    traces = src.get_session_traces("M-V4")
    assert [t["id"] for t in traces] == ["t-v4-session"]


def test_list_traces_name_filter_passed_to_client():
    src = _source([make_trace("t1"), make_trace("t2", stage="processing")])
    src.list_traces(name="document-pipeline")
    call = src.client.api.trace.calls[-1]
    assert call["name"] == "document-pipeline"


def test_list_traces_tags_and_environments_passed():
    src = _source([make_trace("t1")])
    src.list_traces(tags=["mailroom", "live"], environments=["pilot"])
    call = src.client.api.trace.calls[-1]
    assert call["tags"] == "mailroom,live"
    assert call["environment"] == "pilot"


def test_list_traces_since_passed():
    base = datetime(2026, 1, 1, 12, 0, 0)
    src = _source([make_trace("t1")])
    src.list_traces(since=base)
    assert src.client.api.trace.calls[-1]["from_timestamp"] == base


def test_list_recent_runs_filters_to_pipeline_traces():
    src = _source([make_trace("t1"), make_trace("t2", stage="processing")])
    src.client.traces.append(
        {"id": "other", "name": "ingest-log", "updated_at": datetime(2026, 1, 1, 12, 0, 0)}
    )
    runs = list_recent_runs(src, since=datetime(2025, 1, 1), limit=10)
    assert {r.trace_id for r in runs} == {"t1", "t2"}


def test_cache_avoids_requery_within_ttl():
    src = _source([make_trace("t1")], cache_ttl=60, poll_cache_ttl=60)
    src.list_traces()
    src.list_traces()
    assert len(src.client.api.trace.calls) == 1


def test_cache_expires():
    src = _source([make_trace("t1")], cache_ttl=-1, poll_cache_ttl=-1)
    src.list_traces()
    src.list_traces()
    assert len(src.client.api.trace.calls) == 2


def test_unavailable_raises_when_client_has_no_api():
    src = LangfuseSource(client=object())
    with pytest.raises(LangfuseUnavailable):
        src.list_traces()
    assert src.health()["langfuse"] is False


def test_get_run_caches_full_detail():
    src = _source([make_trace("t1")], cache_ttl=60, poll_cache_ttl=60)
    first = src.get_run("t1")
    second = src.get_run("t1")
    assert first == second
    assert first.trace_id == "t1"


def test_health_reports_ok_and_down():
    assert _source([make_trace("t1")]).health()["langfuse"] is True
    assert LangfuseSource(client=object()).health()["langfuse"] is False


def test_health_probe_is_cached_within_window():
    """Concurrent polls (page + poller + extra tabs) must collapse into one
    Langfuse read — a slow cloud previously turned /api/health into a 30s hang."""
    src = _source([make_trace("t1")])
    first = src.health()
    second = src.health()
    assert first == second
    assert first["langfuse"] is True
    assert len(src.client.api.trace.calls) == 1


def test_health_probe_revalidates_after_window_expiry():
    src = _source([make_trace("t1")])
    src.health()
    src.health_cache.clear()
    src.health()
    assert len(src.client.api.trace.calls) == 2


def test_health_probe_caches_failures():
    src = LangfuseSource(client=object())
    assert src.health()["langfuse"] is False
    assert src.health()["langfuse"] is False


def test_list_recent_runs_returns_pipeline_runs():
    src = _source([make_trace("t1")])
    runs = list_recent_runs(src, since=datetime(2025, 1, 1), limit=5)
    assert all(isinstance(r, PipelineRun) for r in runs)


class TestScoreContaminationFix:
    """V-2: the v1 scores fallback ignored trace_id on Langfuse v4 and returned
    OTHER traces' scores. Empty-v3 must be treated as empty."""

    def test_empty_v3_does_not_fallback_to_v1(self):
        from mailroom_ui.langfuse_source import LangfuseSource
        from tests.fake_langfuse import FakeClient, Obj

        class V3Empty:
            def get_many_v3(self, trace_id, limit=100):
                return Obj(data=[])

        class V1Poisoned:
            # The v1 endpoint ignores trace_id — would return other traces' scores.
            def get_many(self, trace_id, limit=100):
                return Obj(data=[{"name": "mailroom-pipeline-judge", "value": "CORRECT"}])

        client = FakeClient()
        client.api.scores_v3 = V3Empty()
        client.api.scores = V1Poisoned()
        src = LangfuseSource(client=client)
        scores = src.get_scores("some-trace")
        assert scores == []  # no cross-trace contamination

    def test_v3_scores_used_when_present(self):
        from mailroom_ui.langfuse_source import LangfuseSource
        from tests.fake_langfuse import FakeClient, Obj

        class V3Ok:
            def get_many_v3(self, trace_id, limit=100):
                return Obj(data=[{"name": "stage_completed", "value": 1}])

        client = FakeClient()
        client.api.scores_v3 = V3Ok()
        src = LangfuseSource(client=client)
        scores = src.get_scores("t1")
        assert len(scores) == 1
        assert scores[0]["name"] == "stage_completed"


class TestPollerPartialFailure:
    """V-4: a Langfuse fetch failure returns None (keep last good snapshot)
    instead of [] (wiping the floor)."""

    def test_fetch_failure_returns_none_not_empty(self):
        import asyncio
        from unittest.mock import patch

        from server.poller import PollHub

        src = object()
        hub = PollHub(src, interval=60, window=21600, limit=100)
        with patch("server.poller.list_recent_runs", side_effect=RuntimeError("langfuse down")):
            assert hub._fetch() is None

    def test_fetch_success_returns_runs(self):
        from unittest.mock import patch

        from server.poller import PollHub

        src = object()
        hub = PollHub(src, interval=60, window=21600, limit=100)
        with patch("server.poller.list_recent_runs", return_value=[]):
            assert hub._fetch() == []
            assert hub.runs == []


class TestNoNPlusOneFetching:
    """V-5: list_recent_runs must not issue per-trace score/observation calls
    on every poll — that was an N+1 (~102-302 Langfuse calls per poll)."""

    def test_list_recent_runs_does_not_call_scores_api(self):
        from tests.fake_langfuse import make_trace

        src = _source([make_trace("t1")])
        calls = {"count": 0}

        class ExplodingScores:
            def get_many_v3(self, trace_id, limit=100):
                calls["count"] += 1
                raise AssertionError("N+1 score fetch in list_recent_runs")

            def get_many(self, trace_id, limit=100):
                calls["count"] += 1
                raise AssertionError("N+1 score fetch in list_recent_runs")

        src.client.api.scores_v3 = ExplodingScores()
        runs = list_recent_runs(src, since=datetime(2025, 1, 1), limit=5)
        assert calls["count"] == 0
        # embedded list-level scores still resolve verdict/quality — no fetch
        # needed, so nothing regressed for the floor.
        assert runs[0].verdict == "CORRECT"

    def test_get_run_shared_cache_single_fetch(self):
        from tests.fake_langfuse import make_trace

        # V-26: drill-down prefers the LIST harvest — the rate-limited
        # detail endpoint is never touched when the trace was seen in a
        # recent list page. The run-level cache then makes the poller +
        # metrics + review + sessions share one fetch per TTL.
        src = _source([make_trace("t1")], cache_ttl=15, poll_cache_ttl=15)
        get_calls = []
        orig_get = src.client.api.trace.get

        def counting(trace_id):
            get_calls.append(trace_id)
            return orig_get(trace_id)

        src.client.api.trace.get = counting
        src.get_run("t1")
        src.get_run("t1")
        src.get_run("t1")
        assert len(get_calls) == 0  # harvest hit: detail endpoint avoided

    def test_get_run_detail_fallback_when_harvest_misses(self):
        from tests.fake_langfuse import make_trace

        # A trace NOT present in list pages still resolves via the detail
        # endpoint (fast-fail, no retry storms) exactly once per TTL.
        src = _source([make_trace("t1")], cache_ttl=15, poll_cache_ttl=15)
        # poison the harvest so the fallback path is exercised
        src.cache.set("list-harvest", {}, 30)
        get_calls = []
        orig_get = src.client.api.trace.get

        def counting(trace_id, **kw):
            get_calls.append(trace_id)
            return orig_get(trace_id)

        src.client.api.trace.get = counting
        run = src.get_run("t1")
        assert run is not None
        assert len(get_calls) == 1

    def test_observations_index_is_primary_path(self):
        from tests.fake_langfuse import make_trace, Obj

        # V-26: observations come from the v2 index (the documented
        # alternative to the rate-limited detail endpoint); the embedded
        # set on the trace record is only a fallback.
        embedded_used = []
        tr = make_trace("t1")
        src = _source([tr], cache_ttl=15, poll_cache_ttl=15)
        obs_api = src.client.api.observations

        real_get_many = obs_api.get_many

        def counting(**kw):
            embedded_used.append(kw.get("trace_id"))
            return real_get_many(**kw)

        obs_api.get_many = counting
        obs = src.get_observations("t1")
        assert obs, "observations should resolve from the index"
        assert "t1" in embedded_used


class TestEnrichedRecentRuns:
    """V-3: aggregations need full runs, not list-level light ones."""

    def test_enriched_runs_carry_tokens_cost_verdict(self):
        from mailroom_ui.langfuse_source import enriched_recent_runs
        from tests.fake_langfuse import make_trace

        src = _source([make_trace("t1")], cache_ttl=-1, poll_cache_ttl=-1)
        runs = enriched_recent_runs(src, since=datetime(2025, 1, 1), limit=5)
        r = runs[0]
        assert r.llm_call_count == 2
        assert r.total_tokens == 4600
        assert r.cost_usd > 0
        assert r.verdict == "CORRECT"

    def test_one_bad_trace_degrades_to_light_not_abort(self):
        from mailroom_ui.langfuse_source import enriched_recent_runs
        from tests.fake_langfuse import make_trace

        src = _source([make_trace("t1"), make_trace("t2")], cache_ttl=-1, poll_cache_ttl=-1)
        with patch.object(src, "get_run", side_effect=RuntimeError("langfuse exploded")):
            runs = enriched_recent_runs(src, since=datetime(2025, 1, 1), limit=5)
        assert len(runs) == 2  # both survive via light fallback


class TestRateLimitBackoff:
    """V-5: HTTP 429 gets exponential backoff instead of compounding."""

    def test_429_backs_off_exponentially_and_raises(self):
        """A 429 opens a cool-down window (0.5 * 2^n, capped at 10 s) instead
        of sleeping inside the poll thread; calls in the window fail fast."""
        src = _source([make_trace("t1")], cache_ttl=-1, poll_cache_ttl=-1)
        calls = []

        def boom():
            calls.append(1)
            err = RuntimeError("rate limit")
            err.status = 429
            raise err

        clock = [1000.0]
        windows = []
        with patch("mailroom_ui.langfuse_source.time.monotonic", side_effect=lambda: clock[0]), \
                patch("time.sleep", side_effect=AssertionError("must not sleep")):
            for _ in range(3):
                with pytest.raises(LangfuseUnavailable):
                    src._guarded("x", boom)
                windows.append(src._backoff_until - clock[0])
                # Inside the window: no API call at all.
                with pytest.raises(LangfuseUnavailable, match="cooling down"):
                    src._guarded("x", boom)
                clock[0] += 60
        assert windows == [0.5, 1.0, 2.0]
        assert len(calls) == 3
        # Success resets the ladder.
        with patch("mailroom_ui.langfuse_source.time.monotonic", side_effect=lambda: clock[0]):
            assert src._guarded("x", lambda: "ok") == "ok"
        assert src._rate_hits == 0
