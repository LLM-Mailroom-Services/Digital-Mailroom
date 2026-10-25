"""Pilot-run demo director: staggered FakeClient traces for floor recordings."""

from scripts.demo_pilot_run import CAST, MATTER, SCHEDULE, apply_event


def test_fake_client_keeps_caller_owned_empty_list():
    from tests.fake_langfuse import FakeClient, make_trace

    traces: list[dict] = []
    client = FakeClient(traces)
    traces.append(make_trace("t-live", filename="live.pdf", stage="intake"))
    listed = client.api.trace.list().data
    assert len(listed) == 1
    assert listed[0]["id"] == "t-live"


def test_pilot_schedule_covers_stations_and_cast():
    stages = {extra.get("stage") for _, action, key, extra in SCHEDULE}
    assert {"inbox", "intake", "classify", "extract", "judge_verify", "arbiter",
            "report", "catalog", "archived", "review", "failed"} <= stages
    assert {key for _, _, key, _ in SCHEDULE} == set(CAST)
    traces: list[dict] = []
    for _, action, key, extra in SCHEDULE:
        apply_event(traces, action, key, extra)
    assert len(traces) == 6
    by_id = {t["id"]: t for t in traces}
    assert by_id["pilot-incoming"]["output"]["stage"] == "inbox"
    assert by_id["pilot-contract"]["output"]["stage"] == "archived"
    assert by_id["pilot-merger"]["output"]["stage"] == "review"
    assert by_id["pilot-articles"]["output"]["stage"] == "failed"
    assert by_id["pilot-claim"]["output"]["stage"] == "archived"
    assert by_id["pilot-letter"]["output"]["stage"] == "archived"
    assert all(t["session_id"] == MATTER for t in traces)


def test_pilot_script_check_mode(capsys):
    import scripts.demo_pilot_run as mod

    # argparse --check
    import sys
    old = sys.argv
    sys.argv = ["demo_pilot_run.py", "--check"]
    try:
        mod.main()
    finally:
        sys.argv = old
    out = capsys.readouterr().out
    assert "check ok" in out
    assert "maud_merger_agreement" in out
