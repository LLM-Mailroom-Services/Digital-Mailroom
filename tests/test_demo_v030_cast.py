"""v0.3.0 release-cast director: hopper, review resolve, reconsideration."""

from scripts.demo_v030_cast import MATTER, build_cast


def test_v030_cast_covers_new_desks():
    from mailroom_ui.trace_interpreter import interpret_trace

    traces = build_cast()
    assert len(traces) == 7
    runs = [
        interpret_trace(t, t.get("observations", []), t.get("scores", []))
        for t in traces
    ]
    by_id = {r.trace_id: r for r in runs}
    assert {r.stage.value for r in runs} >= {
        "inbox", "classify", "extract", "review", "archived", "failed",
    }
    assert by_id["v030-review"].doc_id == "doc-merger-42"
    assert by_id["v030-review"].needs_human
    assert by_id["v030-reconsider"].needs_reconsideration
    assert all(r.session_id == MATTER for r in runs)


def test_v030_cast_check_mode(capsys):
    import sys
    import scripts.demo_v030_cast as mod

    old = sys.argv
    sys.argv = ["demo_v030_cast.py", "--check"]
    try:
        mod.main()
    finally:
        sys.argv = old
    out = capsys.readouterr().out
    assert "check ok" in out
    assert "v030-review" in out
    assert "doc-merger-42" in out
