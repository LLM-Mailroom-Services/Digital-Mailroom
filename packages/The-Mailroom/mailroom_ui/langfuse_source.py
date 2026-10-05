"""Langfuse adapter — the sole source of truth for The-Mailroom.

Every function here reads Langfuse API data only. The interface never falls
back to locally fabricated data: if Langfuse is unreachable, callers get an
empty result + healthy error so the UI can say "MAILROOM CLOSED".

Works with langfuse SDK >= 2.50 (both the v2/v3 `api.*` surface and the
core `Langfuse(...)` client). Attribute guards keep it version-tolerant.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from .models import PipelineRun
from .sources import TraceSourceUnavailable
from .trace_interpreter import EPOCH, interpret_trace

log = logging.getLogger("mailroom.langfuse_source")

DEFAULT_LANGFUSE_HOST = "https://us.cloud.langfuse.com"


def langfuse_host() -> str:
    """Resolve the Langfuse API host.

    This repo's knob is ``LANGFUSE_HOST`` (SDK convention). Langfuse docs
    and some dashboards export ``LANGFUSE_BASE_URL`` instead — accept that
    alias so a Space / VPS secret copied from the Langfuse UI still works.
    """
    host = (os.environ.get("LANGFUSE_HOST") or "").strip()
    if not host:
        host = (os.environ.get("LANGFUSE_BASE_URL") or "").strip()
    return host or DEFAULT_LANGFUSE_HOST


class LangfuseUnavailable(TraceSourceUnavailable):
    """Back-compat alias: the shared TraceSourceUnavailable base is what the
    server's 503 handler registers; this subclass keeps every existing
    except-clause working."""


class TTLCache:
    """Thread-safe TTL cache with eviction.

    Expired entries are swept on write and the store is capped: the traces
    list key rotates every 30 s (time bucket) and per-trace keys accumulate,
    so lazy eviction-on-read alone grew memory for the life of the process.
    """

    MAX_ENTRIES = 4096
    SWEEP_EVERY = 256

    def __init__(self, max_entries: int | None = None) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self.max_entries = max_entries or self.MAX_ENTRIES
        self._writes = 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def _sweep_locked(self, now: float) -> None:
        for key in [k for k, (exp, _v) in self._data.items() if exp < now]:
            self._data.pop(key, None)
        overflow = len(self._data) - self.max_entries
        if overflow > 0:
            # Drop the entries closest to expiry first.
            for key, _ in sorted(self._data.items(), key=lambda kv: kv[1][0])[:overflow]:
                self._data.pop(key, None)

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            hit = self._data.get(key)
            if hit is None:
                return None
            expires, value = hit
            if time.monotonic() > expires:
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl: float) -> None:
        now = time.monotonic()
        with self._lock:
            self._data[key] = (now + ttl, value)
            self._writes += 1
            if self._writes % self.SWEEP_EVERY == 0 or len(self._data) > self.max_entries:
                self._sweep_locked(now)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


def _to_dict(obj: Any) -> Any:
    """Pydantic SDK models -> plain dict; pass dicts through."""
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            return obj.model_dump()
    return obj


def _page_data(response: Any) -> list[Any]:
    """Paginated API responses: pull the `.data` list defensively."""
    if response is None:
        return []
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return data
    if isinstance(response, list):
        return response
    return []


def _status_of(exc: BaseException) -> Optional[int]:
    status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def _is_not_found(exc: BaseException) -> bool:
    if _status_of(exc) == 404:
        return True
    return type(exc).__name__ == "NotFoundError" or "not found" in str(exc).lower()[:200]


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


class LangfuseSource:
    """Read-only gateway to one Langfuse project."""

    def __init__(
        self,
        client: Any = None,
        *,
        cache_ttl: float = 3.0,
        poll_cache_ttl: float = 3.0,
        run_cache_ttl: float = 60.0,
    ) -> None:
        # List/obs TTL matches MAILROOM_POLL_INTERVAL (default 3 s) so a new
        # document-pipeline trace appears on the next snapshot instead of
        # sitting behind a 15 s list cache. Full-run cache stays longer;
        # the poller force-refreshes in-flight traces.
        self.client = client if client is not None else self._build_client()
        self.available = self.client is not None
        self.cache = TTLCache()
        self.cache_ttl = cache_ttl
        self.poll_cache_ttl = poll_cache_ttl
        self.run_cache_ttl = run_cache_ttl
        self._rate_hits = 0
        self._backoff_until = 0.0
        self._rate_lock = threading.Lock()
        # Health probe TTL: several concurrent polls (page + poller + extra
        # tabs) otherwise each run a full Langfuse read — one 15s timeout with
        # one retry became a 30s /api/health hang on a slow cloud. 5s of
        # staleness is invisible to the UI and still fails fast on outage.
        self.health_cache = TTLCache()

    # ---------------------------------------------------------------- client

    @staticmethod
    def _build_client() -> Any:
        # Preflight: the v4 SDK constructs a DISABLED client (with only a
        # console warning) when keys are missing, which later surfaces as a
        # confusing "client.api unavailable" deep in a fetch. Fail here with
        # the actual reason instead.
        if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
            log.warning("LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY not set — Langfuse source disabled")
            return None
        try:
            import langfuse  # noqa: F401
        except ImportError:
            return None
        from langfuse import Langfuse

        try:
            # V-27: cap SDK-internal retries — v4 cloud rate-limits bursty
            # read paths and the default retry/backoff turned a contended
            # list call into a 40s hang (observed). One fast retry is plenty
            # for a UI that polls every few seconds anyway.
            return Langfuse(
                public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
                secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
                host=langfuse_host(),
                timeout=15,
                max_retries=1,
            )
        except TypeError:
            # Older SDKs without these kwargs
            try:
                return Langfuse(
                    public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
                    secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
                    host=langfuse_host(),
                )
            except Exception:
                return None
        except Exception:
            return None

    def _api(self, resource: str) -> Any:
        if not self.available:
            raise LangfuseUnavailable("no Langfuse client")
        api = getattr(self.client, "api", None)
        if api is None:
            raise LangfuseUnavailable("client.api unavailable")
        return getattr(api, resource, None)

    def _guarded(self, label: str, fn: Callable[[], Any]) -> Any:
        """Any Langfuse API failure surfaces as LangfuseUnavailable — the
        documented contract for callers (never stale, never fabricated).

        V-5: HTTP 429 (rate limit) gets exponential backoff so a burst of
        polls doesn't compound into a sustained 429 storm.
        """
        # Cool-down instead of sleeping: the old in-thread sleep stalled the
        # poll loop (sequential get_run calls) for minutes during a 429 storm
        # and then raised anyway. Calls inside the window fail fast.
        with self._rate_lock:
            remaining = self._backoff_until - time.monotonic()
        if remaining > 0:
            raise LangfuseUnavailable(f"{label}: rate limited (cooling down {remaining:.1f}s)")
        try:
            out = fn()
        except LangfuseUnavailable:
            raise
        except Exception as exc:
            if _status_of(exc) == 429:
                with self._rate_lock:
                    backoff = min(0.5 * (2 ** min(self._rate_hits, 6)), 10.0)
                    self._rate_hits += 1
                    self._backoff_until = time.monotonic() + backoff
                raise LangfuseUnavailable(f"{label}: rate limited (429, backoff {backoff:.1f}s)") from exc
            raise LangfuseUnavailable(f"{label}: {str(exc)[:200]}") from exc
        with self._rate_lock:
            self._rate_hits = 0
        return out

    # ----------------------------------------------------------------- traces

    # The Langfuse list API hard-caps `limit` at 100 per page ("Too big:
    # expected number to be <=100"); larger caller limits are satisfied by
    # paginating. Without this the documented MAILROOM_TRACE_LIMIT=200 made
    # every poller/review/metrics query fail with a 400 against the real API.
    MAX_PAGE_LIMIT = 100
    MAX_PAGES = 20

    def list_traces(
        self,
        *,
        since: Optional[datetime] = None,
        limit: int = 200,
        tags: Optional[list[str]] = None,
        environments: Optional[list[str]] = None,
        name: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Raw trace summaries (list page(s))."""
        # V-27: bucket the window to 30s for the cache key — the caller passes
        # a fresh now()-delta every request, so the raw datetime key never hit
        # and every poll re-struck Langfuse (compounding v4 rate limits).
        since = since or (datetime.now(timezone.utc) - timedelta(hours=6))
        bucket = int(since.timestamp()) // 30
        key = f"traces:{bucket}:{limit}:{tags}:{environments}:{name}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        trace_api = self._api("trace")
        if trace_api is None:
            raise LangfuseUnavailable("trace API unavailable")
        page_limit = max(1, min(limit, self.MAX_PAGE_LIMIT))
        kw: dict[str, Any] = {"limit": page_limit}
        if since is not None:
            kw["from_timestamp"] = since
        if tags:
            kw["tags"] = ",".join(tags)
        if environments:
            kw["environment"] = ",".join(environments)
        if name:
            kw["name"] = name
        out: list[dict[str, Any]] = []
        page = 1
        while len(out) < limit and page <= self.MAX_PAGES:
            resp = self._guarded(
                "trace.list", lambda p=page: trace_api.list(page=p, **kw)
            )
            batch = [_to_dict(t) for t in _page_data(resp)]
            out.extend(batch)
            if len(batch) < page_limit:
                break
            page += 1
        out = out[:limit]
        self.cache.set(key, out, self.poll_cache_ttl)
        self._merge_list_harvest(out)
        return out

    def _light_traces_from_list(self) -> dict[str, dict[str, Any]]:
        """Trace records harvested from list pages (cheap, un-rate-limited).

        The v4 cloud rate-limits GET /traces/{traceId} hard — its own error
        says to use the observations index instead — so drill-down first
        reuses the list payloads we already fetch every poll.
        """
        key = "list-harvest"
        cached = self.cache.get(key)
        if isinstance(cached, dict):
            return cached
        trace_api = self._api("trace")
        out: dict[str, dict[str, Any]] = {}
        if trace_api is not None:
            for page in (1, 2):
                try:
                    resp = self._guarded(
                        "trace.list", lambda p=page: trace_api.list(limit=100, page=p)
                    )
                except LangfuseUnavailable:
                    break
                batch = [_to_dict(t) for t in _page_data(resp)]
                for t in batch:
                    tid = t.get("id")
                    if tid:
                        out[tid] = t
                        self.cache.set(f"trace:{tid}", t, self.cache_ttl)
                if len(batch) < 100:
                    break
        self.cache.set(key, out, self.cache_ttl)
        return out

    def _merge_list_harvest(self, traces: list[dict[str, Any]]) -> None:
        """Keep drill-down harvest in lockstep with the poller list payload.

        Pilot re-runs reuse deterministic trace ids. A stale list-harvest
        (or trace:{id} entry) keeps the first-write session_id, so SESSIONS
        and REVIEW split one 50-doc matter across old and new session ids.
        """
        harvest = self.cache.get("list-harvest")
        merged: dict[str, dict[str, Any]] = dict(harvest) if isinstance(harvest, dict) else {}
        for t in traces:
            tid = t.get("id")
            if tid:
                merged[tid] = t
                self.cache.set(f"trace:{tid}", t, self.cache_ttl)
        self.cache.set("list-harvest", merged, self.cache_ttl)

    def get_trace(self, trace_id: str) -> Optional[dict[str, Any]]:
        key = f"trace:{trace_id}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        # Preferred: the list harvest (V-26) — avoids the rate-limited
        # detail endpoint entirely for anything seen in a recent poll.
        harvested = self._light_traces_from_list().get(trace_id)
        if harvested is not None:
            return harvested
        trace_api = self._api("trace")
        if trace_api is None:
            raise LangfuseUnavailable("trace API unavailable")
        def _fetch():
            try:
                # Fast-fail: retrying the detail endpoint just burns ~30s in
                # backoff before returning the same rate-limit error.
                return trace_api.get(trace_id, request_options={
                    "timeout_in_seconds": 10, "max_retries": 0})
            except TypeError:
                return trace_api.get(trace_id)  # older SDKs: no request_options

        try:
            resp = self._guarded("trace.get", _fetch)
        except LangfuseUnavailable as exc:
            # Only a real 404 means "no such trace". A 429/timeout/5xx is an
            # outage and must not surface as a misleading "trace not found".
            if exc.__cause__ is not None and _is_not_found(exc.__cause__):
                return None
            raise
        if resp is None:
            return None
        out = _to_dict(resp)
        self.cache.set(key, out, self.cache_ttl)
        return out

    def get_observations(self, trace_id: str) -> list[dict[str, Any]]:
        key = f"obs:{trace_id}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        # V-26: the observations INDEX (documented alternative to the
        # rate-limited trace-detail endpoint) is now the primary path;
        # the embedded set from trace.get is only a fallback.
        obs_api = self._api("observations")
        out: list[dict[str, Any]] = []
        failure: Optional[LangfuseUnavailable] = None
        if obs_api is not None:
            try:
                out = self._paged(
                    "observations.get_many",
                    lambda p: obs_api.get_many(trace_id=trace_id, limit=self.MAX_PAGE_LIMIT,
                                               **({"page": p} if p else {})),
                )
            except LangfuseUnavailable as exc:
                failure = exc
        if not out:
            # Fallback: a trace DETAIL record embeds full observation objects.
            # The LIST payload (the usual harvest) embeds only id strings —
            # those carry nothing and used to become fake "observation" spans.
            embedded = (self.get_trace(trace_id) or {}).get("observations")
            if isinstance(embedded, list):
                full = [d for d in (_to_dict(o) for o in embedded) if isinstance(d, dict) and d]
                if full:
                    out, failure = full, None
        if failure is not None:
            # Never cache an outage as "this trace has no observations".
            raise failure
        self.cache.set(key, out, self.cache_ttl)
        return out

    def _paged(
        self, label: str, fetch: Callable[[Optional[int]], Any], max_pages: int = 10,
    ) -> list[dict[str, Any]]:
        """Collect every page of a per-trace index (100-row cap per page).

        ``fetch(page)`` is called with ``page=None`` once when the SDK method
        rejects the ``page`` kwarg (older clients): single page only.
        """
        out: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            try:
                resp = self._guarded(label, lambda p=page: fetch(p))
            except LangfuseUnavailable as exc:
                if page == 1 and isinstance(exc.__cause__, TypeError):
                    resp = self._guarded(label, lambda: fetch(None))
                    return [_to_dict(o) for o in _page_data(resp)]
                raise
            batch = [_to_dict(o) for o in _page_data(resp)]
            out.extend(batch)
            if len(batch) < self.MAX_PAGE_LIMIT:
                break
        return out

    def get_scores(self, trace_id: str) -> list[dict[str, Any]]:
        key = f"scores:{trace_id}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        # v3 scores endpoint: trace filter works and CATEGORICAL values come
        # back label-resolved. The v1 endpoint ignores `trace_id` on Langfuse
        # v4 (returns global pages) — V-2: it must NEVER be used as a fallback
        # for an empty v3 result, or other traces' verdicts get displayed on
        # this envelope (wrong-but-plausible data, cached up to 60 s).
        v3 = getattr(self.client, "api", None) and getattr(self.client.api, "scores_v3", None)
        out: list[dict[str, Any]] = []
        if v3 is not None:
            # Raises LangfuseUnavailable on outage — an empty verdict cached
            # for 60 s is indistinguishable from "not judged" on the floor.
            out = self._paged(
                "scores.get_many_v3",
                lambda p: v3.get_many_v3(trace_id=trace_id, limit=self.MAX_PAGE_LIMIT,
                                         **({"page": p} if p else {})),
            )
        # V-2: empty-v3 is treated as empty — no v1 fallback (the v1 endpoint
        # ignores the trace filter on Langfuse v4 and returns global pages).
        self.cache.set(key, out, self.cache_ttl)
        return out

    def get_score_configs(self) -> dict[str, dict[str, Any]]:
        """Project score configs: name -> {"data_type", "categories"}.

        Used to resolve CATEGORICAL score values (judge verdicts) back to
        their labels. Cached at process level.
        """
        key = "score-configs"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        out: dict[str, dict[str, Any]] = {}
        try:
            cfg_api = self._api("score_configs")
            if cfg_api is not None:
                def _cfg():
                    try:
                        return cfg_api.get(limit=self.MAX_PAGE_LIMIT)
                    except TypeError:
                        return cfg_api.get()

                resp = self._guarded("score_configs.get", _cfg)
                for cfg in _page_data(resp):
                    d = _to_dict(cfg)
                    name = d.get("name")
                    if not name:
                        continue
                    cats = []
                    for cat in d.get("categories") or []:
                        if isinstance(cat, dict) and cat.get("label") is not None:
                            cats.append({"value": cat.get("value"), "label": cat.get("label")})
                    out[name] = {
                        "data_type": d.get("data_type") or d.get("dataType"),
                        "categories": cats,
                    }
        except Exception as exc:
            # Don't cache the failure: CATEGORICAL verdicts would stay numeric
            # indices until the next TTL. Retry on the next run fetch.
            log.warning("score configs unavailable: %s", exc)
            return {}
        self.cache.set(key, out, self.cache_ttl)
        return out

    def invalidate_run(self, trace_id: str) -> None:
        """Drop cached obs/scores/run so the next get_run is live.

        Leave ``trace:{id}`` and ``list-harvest`` alone — ``list_traces``
        merges the current list payload into those keys. Deleting them here
        made force-refresh fall through to the rate-limited GET /traces/{id}
        (or a first-write harvest) and kept reused-id pilots on the old
        session_id.
        """
        if not trace_id:
            return
        for prefix in ("run:", "obs:", "scores:"):
            self.cache.delete(f"{prefix}{trace_id}")

    def get_run(self, trace_id: str, *, force_refresh: bool = False) -> Optional[PipelineRun]:
        """Full interpreted pipeline run for one trace (sole source: Langfuse).

        V-5: results are cached for `run_cache_ttl` so the poller and the
        metrics/sessions/review endpoints share one fetch per terminal run.
        Pass ``force_refresh=True`` for in-flight conveyor traces so a node
        that just flushed is not stuck on the previous station for 60 s.
        """
        key = f"run:{trace_id}"
        if force_refresh:
            self.invalidate_run(trace_id)
        else:
            cached = self.cache.get(key)
            if cached is not None:
                return cached
        trace = self.get_trace(trace_id)
        if trace is None:
            return None
        obs = self.get_observations(trace_id)
        scores = self.get_scores(trace_id)
        run = interpret_trace(trace, obs, scores, score_configs=self.get_score_configs())
        self.cache.set(key, run, self.run_cache_ttl)
        return run

    # --------------------------------------------------------------- sessions

    def list_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
        key = f"sessions:{limit}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        sessions_api = self._api("sessions")
        if sessions_api is None:
            return []
        resp = self._guarded("sessions.list",
                             lambda: sessions_api.list(limit=min(limit, self.MAX_PAGE_LIMIT)))
        out = [_to_dict(s) for s in _page_data(resp)]
        self.cache.set(key, out, self.cache_ttl)
        return out

    def get_session_traces(self, session_id: str, limit: int = 100) -> list[dict[str, Any]]:
        key = f"session-traces:{session_id}:{limit}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        try:
            sessions_api = self._api("sessions")
            try:
                # v2/v3 paginated surface.
                resp = self._guarded(
                    "sessions.get",
                    lambda: sessions_api.get(session_id, limit=limit),
                )
            except LangfuseUnavailable as exc:
                # v4 SessionsClient.get(id) removed `limit` and returns a
                # SessionWithTraces whose list lives on `.traces`, not `.data`.
                if not isinstance(exc.__cause__, TypeError):
                    raise
                resp = self._guarded(
                    "sessions.get",
                    lambda: sessions_api.get(session_id),
                )
        except LangfuseUnavailable:
            return []
        traces = getattr(resp, "traces", None)
        if traces is None and isinstance(resp, dict):
            traces = resp.get("traces")
        raw = traces if isinstance(traces, list) else _page_data(resp)
        out = [_to_dict(t) for t in raw[:limit]]
        self.cache.set(key, out, self.cache_ttl)
        return out

    # ---------------------------------------------------------------- health

    def health(self) -> dict[str, Any]:
        """Live Langfuse reachability: real API call, cached 5s.

        The probe is cheap to share: the SPA polls every few seconds and two
        tabs + the poller can collapse into one Langfuse read per window.
        Failures are cached too, so a slow cloud does not pile up timeouts.
        """
        cached = self.health_cache.get("probe")
        if cached is not None:
            return cached
        try:
            self.list_traces(limit=1)
            ok = True
        except Exception:
            ok = False
        # "ok" is the source-agnostic key the SPA checks (Phoenix/multi
        # sources return their own keys; "langfuse" stays for back-compat).
        payload = {"ok": ok, "langfuse": ok, "source": "langfuse", "cached_trace_count": None}
        self.health_cache.set("probe", payload, 5.0)
        return payload


def list_recent_runs(
    source: LangfuseSource,
    *,
    since: Optional[datetime] = None,
    limit: int = 200,
) -> list[PipelineRun]:
    """Convenience: recent traces -> interpreted runs, newest first.

    Uses the trace-list response only (light runs) — cheap enough to poll.
    Fetches score configs so CATEGORICAL verdicts can be label-resolved.

    V-5: this deliberately does NOT fetch scores per trace — that was an N+1
    (one Langfuse call per run per poll). Verdicts/qualities surface via the
    embedded `observations`/`scores` arrays when the API includes them in the
    list response (interpret_trace falls back to those), and via the poller's
    per-run detail enrichment (get_run, cached) otherwise. Use
    `enriched_recent_runs` when the caller needs tokens/cost/verdicts now.

    Honors the documented MAILROOM_TRACE_TAGS / MAILROOM_TRACE_ENVIRONMENTS
    knobs (V-8: they were documented but never read).
    """
    import os

    since = since or (datetime.now(timezone.utc) - timedelta(hours=6))
    tags = [t.strip() for t in os.environ.get("MAILROOM_TRACE_TAGS", "").split(",") if t.strip()] or None
    environments = [e.strip() for e in os.environ.get("MAILROOM_TRACE_ENVIRONMENTS", "").split(",") if e.strip()] or None
    # Trace-name universe: the llm-mailroom pipeline plus optional extra
    # producers whose traces should surface on the floor (e.g. the
    # entity-repo docclass eval runner -> "docclass_classification").
    names = [n.strip() for n in os.environ.get("MAILROOM_TRACE_NAMES", "document-pipeline").split(",") if n.strip()]
    traces: list[dict[str, Any]] = []
    seen: set[str] = set()
    for name in names:
        for t in source.list_traces(since=since, limit=limit, name=name,
                                     tags=tags, environments=environments):
            tid = t.get("id")
            if tid and tid not in seen:
                seen.add(tid)
                traces.append(t)
    score_configs = source.get_score_configs()
    runs = []
    for t in traces:
        tid = t.get("id")
        if not tid:
            continue
        runs.append(interpret_trace(t, score_configs=score_configs))
    runs.sort(key=lambda r: r.updated_at or EPOCH, reverse=True)
    return runs


def enriched_recent_runs(
    source: LangfuseSource,
    *,
    since: Optional[datetime] = None,
    limit: int = 200,
) -> list[PipelineRun]:
    """Recent runs enriched with per-trace observations/scores (V-3).

    Aggregations (cost, tokens, LLM calls, verdicts) need full runs, not the
    list-level "light" ones — the old /api/metrics aggregated light runs and
    permanently showed $0.00 / 0 tok / 0 calls. get_run() is cached for
    `run_cache_ttl`, so repeated calls (metrics + review + sessions + poller)
    share the same fetches. One bad trace degrades to its light run instead
    of aborting the whole list (per-trace isolation).

    V-26 note: deliberately SEQUENTIAL — enrichment now rides the un-rate-
    limited observations index + list harvest, and parallelism on Langfuse's
    read endpoints just trips the per-endpoint rate limiter faster.
    """
    runs = list_recent_runs(source, since=since, limit=limit)
    out = []
    for r in runs:
        try:
            full = source.get_run(r.trace_id)
        except Exception as exc:
            log.warning("enrichment failed for %s: %s", r.trace_id, exc)
            full = None
        out.append(full if full is not None else r)
    return out
