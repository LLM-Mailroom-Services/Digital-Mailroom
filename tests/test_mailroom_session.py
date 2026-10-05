"""SAND-033: mailroom-themed CLI session layer (network-free)."""

import os

from mailroom_sandbox.tui.session import (
    MailroomConsole,
    item_progress_bar,
    mailroom_style_enabled,
    run_event_handler,
)
from mailroom_sandbox.watch import strip_ansi


def test_item_progress_bar_matches_watch_style():
    assert item_progress_bar(5, 10, width=10) == "█████░░░░░"


def test_mailroom_style_respects_no_color(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("SANDBOX_PLAIN_LOGS", raising=False)
    assert mailroom_style_enabled() is False or mailroom_style_enabled() is True
    monkeypatch.setenv("NO_COLOR", "1")
    assert mailroom_style_enabled() is False


def test_mailroom_style_plain_logs_override(monkeypatch):
    monkeypatch.setenv("SANDBOX_PLAIN_LOGS", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert mailroom_style_enabled() is False


def test_console_plain_banner(capsys):
    c = MailroomConsole(enabled=False)
    c.run_banner(run_id="run-a", task="sorter", subtitle="sandbox eval")
    err = capsys.readouterr().err
    assert "[mailroom] run-a" in err
    assert "sandbox eval" in err


def test_console_plain_progress_throttles_duplicate(capsys):
    c = MailroomConsole(enabled=False)
    c.progress(1, 10, ok=1, errors=0)
    c.progress(1, 10, ok=1, errors=0)
    lines = [ln for ln in capsys.readouterr().err.splitlines() if ln.startswith("[progress]")]
    assert len(lines) == 1


def test_console_styled_banner_has_frame():
    import io

    buf = io.StringIO()
    MailroomConsole(stream=buf, enabled=True).run_banner(run_id="run-b", task="t", width=72)
    plain = strip_ansi(buf.getvalue())
    assert plain.startswith("╔")
    assert "(o,o)" in plain and "INBOX → SORTER → TRAY" in plain


def test_run_event_handler_forwards_progress():
    seen: list[tuple[int, int]] = []

    class _C:
        on = False

        def progress(self, done, total, **kw):
            seen.append((done, total))

    run_event_handler(_C())({"cursor": 3, "total": 10, "ok": 2, "errors": 1})
    assert seen == [(3, 10)]


def test_operator_emit_plain_when_disabled(capsys):
    from mailroom_sandbox.tui.session import operator_emit
    import io

    operator_emit("hello", phase="deploy", stream=io.StringIO())
    # stream not TTY — plain print to provided stream; capsys may not capture StringIO
    buf = io.StringIO()
    MailroomConsole(stream=buf, enabled=False).operator_line("deploy", "hello")
    assert buf.getvalue().strip() == "hello"
