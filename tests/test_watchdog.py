"""Tray TUI watchdog: alert rules, rate/ETA/projection, and in-place painting."""

from __future__ import annotations

from datetime import datetime, timezone

from mailroom_sandbox import watch
from mailroom_sandbox.tui import pretty_log as pl
from mailroom_sandbox.tui import watchdog as wd

T0 = 1_790_000_000.0


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, tz=timezone.utc).isoformat()


def _items(n: int, *, every: float = 10.0, errors: dict[int, str] | None = None) -> list[dict]:
    errors = errors or {}
    return [
        {"item_id": f"D{i}", "ok": i not in errors, "error": errors.get(i), "ts": _iso(T0 + every * (i + 1))}
        for i in range(n)
    ]


def _assess(items, *, now, state="running", total=50, spend=None, **kw):
    spend = spend or {"total_usd": 0.10, "live_usd": 0.10, "cap_usd": 3.2, "gate_usd": 4.5}
    return wd.assess(items=items, state=state, total=total, spend=spend, now=now, run_started=T0, **kw)


def _codes(dog):
    return {a["code"]: a["level"] for a in dog["alerts"]}


def test_healthy_run_is_all_clear_with_rate_and_eta():
    items = _items(20)
    dog = _assess(items, now=T0 + 205)
    assert dog["level"] == "ok" and not dog["alerts"]
    assert 5.5 < dog["rate_dpm"] < 6.5  # one doc every 10 s
    assert 250 < dog["eta_s"] < 350  # 30 left at ~6/min
    assert dog["projected_usd"] > 0.10


def test_auth_401_is_critical():
    items = _items(5, errors={4: "AuthenticationError: Error code: 401 - invalid api key"})
    dog = _assess(items, now=T0 + 55)
    assert _codes(dog)["AUTH"] == "critical"
    assert dog["error_kinds"] == {"Auth401": 1}


def test_error_burst_and_rate():
    errs = {i: "Timeout: request timed out" for i in (9, 10, 11)}
    dog = _assess(_items(12, errors=errs), now=T0 + 125)
    assert _codes(dog)["BURST"] == "critical"
    assert _codes(dog)["ERRORS"] == "warn"


def test_length_truncations_are_flagged():
    errs = {3: "LengthFinishReasonError: Could not parse", 7: "LengthFinishReasonError: Could not parse"}
    dog = _assess(_items(20, errors=errs), now=T0 + 205)
    assert _codes(dog)["LENGTH"] == "warn"
    assert dog["error_kinds"] == {"LengthFinishReasonError": 2}


def test_stall_uses_floor_or_three_p95():
    items = _items(10)
    assert "STALL" not in _codes(_assess(items, now=T0 + 100 + 170))
    assert _codes(_assess(items, now=T0 + 100 + 200))["STALL"] == "critical"
    # a slow class (p95 120 s) gets 360 s before it is called a stall
    assert "STALL" not in _codes(_assess(items, now=T0 + 100 + 300, p95_s=120.0))
    # finished runs never stall
    assert "STALL" not in _codes(_assess(items, now=T0 + 10_000, state="done"))


def test_spend_projection_against_cap_and_gate():
    items = _items(10)
    spend = {"total_usd": 3.0, "live_usd": 3.0, "cap_usd": 3.2, "gate_usd": 4.5}
    assert _codes(_assess(items, now=T0 + 105, spend=spend))["SPEND"] == "critical"


def test_engine_fault_and_silent_logs():
    dog = _assess(_items(5), now=T0 + 55, log_lines=["INFO ok", "torch.OutOfMemoryError: CUDA out of memory"])
    assert _codes(dog)["ENGINE"] == "critical"
    dog = _assess(_items(5), now=T0 + 55, last_log_ts=T0 + 55 - 400)
    assert _codes(dog)["LOGS"] == "warn"


def test_sparkline_buckets_recent_documents():
    stamps = [T0 + 1190 + i for i in range(5)]
    spark = wd.sparkline(stamps, now=T0 + 1200)
    assert len(spark) == wd.SPARK_BUCKETS and spark[-1] == "█" and set(spark[:-1]) == {"▁"}


def test_bell_rings_once_per_critical_code():
    seen: set[str] = set()
    dog = {"alerts": [{"level": "critical", "code": "STALL", "text": ""}, {"level": "warn", "code": "LENGTH", "text": ""}]}
    assert watch.new_critical(dog, seen) == ["STALL"]
    assert watch.new_critical(dog, seen) == []


def test_paint_repaints_in_place_without_clearing():
    out = watch.paint("a\nb\nc", rows=3)
    assert pl.CLEAR_SCREEN not in out
    assert out.startswith(watch.SYNC_BEGIN + pl.CURSOR_HOME) and out.endswith(watch.ERASE_BELOW + watch.SYNC_END)
    assert "c" not in out  # trimmed to rows - 1 so the frame never scrolls


def test_frame_shows_watchdog_panel_and_postage_not_double_counted():
    snap = {
        "run_id": "r", "task": "t", "state": "running", "done": 3, "total": 10, "ok": 3, "errors": 0,
        "replicas": 1, "gpu": "L4", "p50_s": 1.0, "p95_s": 2.0, "mean_score": 0.5, "last_error": "",
    }
    spend = {"spent_usd": 0.1, "live_usd": 0.1, "total_usd": 0.1, "cap_usd": 1.0}
    dog = _assess(_items(3), now=T0 + 35)
    frame = watch.render_frame(snapshot=snap, app="a", log_lines=[], spend=spend, watchdog=dog, width=100)
    assert "WATCHDOG" in frame and "ALL CLEAR" in frame
    assert "$0.1000 / $1.00" in frame


def _timed(n: int, *, latency_s: float, every: float = 10.0) -> list[dict]:
    return [dict(r, latency_ms=latency_s * 1000.0) for r in _items(n, every=every)]


def test_stall_limit_tracks_average_document_time():
    # fast class: 10 s docs → the 180 s floor still applies
    limit, basis = wd.stall_limit(_timed(5, latency_s=10.0), total=50)
    assert limit == wd.STALL_FLOOR_S and "avg doc 10s" in basis
    # slow whole-document class: 600 s docs → 3 × 600 s before a STALL
    limit, basis = wd.stall_limit(_timed(3, latency_s=600.0), total=50)
    assert limit == 1800.0 and "avg doc 600s" in basis
    items = _timed(3, latency_s=600.0)
    assert "STALL" not in _codes(_assess(items, now=T0 + 30 + 1700))
    assert _codes(_assess(items, now=T0 + 30 + 1900))["STALL"] == "critical"


def test_stall_limit_before_first_doc_uses_wall_budget_per_wave():
    # 5 docs at C32 → one wave → the whole 1800 s wall budget
    limit, basis = wd.stall_limit([], total=5, concurrency=32, max_wall_s=1800)
    assert limit == 1800.0 and "wave" in basis
    # 100 docs at C32 → 4 waves of a 3600 s budget
    assert wd.stall_limit([], total=100, concurrency=32, max_wall_s=3600)[0] == 900.0
    # no budget known → floor
    assert wd.stall_limit([], total=5)[0] == wd.STALL_FLOOR_S
    # a chunked merger gate 5 min in, nothing finished yet: not a stall
    dog = _assess([], now=T0 + 300, total=5, concurrency=32, max_wall_s=1800)
    assert "STALL" not in _codes(dog)
    assert dog["stall_basis"].startswith("wall budget")


def test_panel_shows_pace_line_with_basis():
    dog = _assess(_timed(3, latency_s=600.0), now=T0 + 100)
    text = "\n".join(wd.panel_lines(dog, on=False, palette={}))
    assert "last doc" in text and "stall at 30m00s (3× avg doc 600s)" in text
    dog = _assess([], now=T0 + 100, total=5, concurrency=32, max_wall_s=1800)
    assert "since start 1m40s" in "\n".join(wd.panel_lines(dog, on=False, palette={}))
