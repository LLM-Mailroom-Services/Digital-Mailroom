"""Observer trust boundaries and CLI combinations, without starting services."""
import json

import pytest

from mailroom_sandbox import cli
from mailroom_sandbox.tui import board
from mailroom_sandbox.tui.beacon import Beacon


@pytest.mark.parametrize("argv", [
    ["watch", "--interval", "nan"], ["watch", "--interval", "0"],
    ["watch", "--cap-usd", "-1"], ["dev", "--interval", "inf"],
    ["board", "--interval", "nan"], ["board", "--stale-s", "-1"],
    ["dev", "--port", "65536"], ["board", "--port", "-1"],
    ["watch", "--port", "65536"],
    ["beacon", "update", "--job", "j", "--package", "p", "--done", "-1"],
])
def test_observer_numeric_arguments_are_validated(argv):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(argv)
    assert exc.value.code == 2


@pytest.mark.parametrize("argv", [
    ["watch", "--demo"], ["watch", "--web", "--once"],
    ["watch", "--port", "0"], ["watch", "--host", "127.0.0.1"],
    ["watch", "--no-browser"], ["watch", "--web", "--demo", "--config", "x"],
    ["board", "--once"], ["board", "--tui", "--demo"],
    ["board", "--tui", "--port", "0"], ["board", "--tui", "--no-browser"],
])
def test_ignored_observer_options_fail_before_starting(argv, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_serve_demo", lambda args: pytest.fail("demo started"))
    monkeypatch.setattr(cli, "_run_board", lambda args: pytest.fail("board started"))
    assert cli.main(argv) == 2
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize("changes", [
    {"updated_at": "yesterday"}, {"updated_at": float("nan")},
    {"updated_at": float("inf")}, {"done": "3"}, {"done": -1},
    {"done": True}, {"total": []}, {"total": -2}, {"metrics": []},
    {"state": {}}, {"job_id": "../../outside"}, {"job_id": ["j"]},
    {"done": 10**400}, {"total": 10**400}, {"updated_at": 10**400},
])
def test_one_malformed_beacon_does_not_break_the_board(tmp_path, changes):
    Beacon("healthy", package="test", root=tmp_path)
    bad = Beacon("broken", package="test", root=tmp_path)
    (tmp_path / "broken.json").write_text(json.dumps({**bad._state, **changes}))
    jobs = board.list_jobs(tmp_path)
    assert [j["job_id"] for j in jobs] == ["healthy"]
    assert "healthy" in board.render_board(jobs)


def test_beacon_metric_usage_error_does_not_write(tmp_path, capsys):
    assert cli.main(["beacon", "update", "--job", "j", "--package", "p",
                     "--root", str(tmp_path), "--metric", "misspelled"]) == 2
    assert "KEY=VALUE" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_board_progress_keeps_overrun_count(tmp_path):
    b = Beacon("overrun", package="test", root=tmp_path)
    b.update(done=12, total=10)
    row = board.list_jobs(tmp_path)[0]
    assert row["done"] == 12 and row["pct"] == 120
    assert board._bar(12, 10, 10) == "█" * 10
