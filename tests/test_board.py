"""`sandbox board`: persistent mailroom display of every beacon job (browser + TUI)."""

import json
import re
import time
from http.client import HTTPConnection
from threading import Thread

from mailroom_sandbox.tui import board as bd
from mailroom_sandbox.tui.beacon import Beacon


def _job(root, jid, **kw):
    b = Beacon(jid, package=kw.pop("package", "local-mailroom-sandbox"), title=kw.pop("title", jid), root=root)
    if kw:
        b.update(**kw)
    return b


def _age(root, jid, seconds):
    p = root / f"{jid}.json"
    d = json.loads(p.read_text())
    d["updated_at"] -= seconds
    p.write_text(json.dumps(d))


def test_status_running_stalled_done_failed(tmp_path):
    _job(tmp_path, "live", done=1, total=4)
    _job(tmp_path, "quiet", done=1, total=4)
    _age(tmp_path, "quiet", 600)
    _job(tmp_path, "ok").finish("done")
    _job(tmp_path, "bad").finish("failed")
    jobs = {j["job_id"]: j for j in bd.list_jobs(tmp_path, stale_s=120)}
    assert {k: v["status"] for k, v in jobs.items()} == {
        "live": "running", "quiet": "stalled", "ok": "done", "bad": "failed"}


def test_dead_pid_on_this_host_is_stalled(tmp_path):
    _job(tmp_path, "orphan", done=1, total=4)
    p = tmp_path / "orphan.json"
    d = json.loads(p.read_text())
    d["pid"] = 999_999_9  # no such process
    p.write_text(json.dumps(d))
    assert bd.list_jobs(tmp_path, stale_s=3600)[0]["status"] == "stalled"


def test_ordering_live_then_stalled_then_finished_newest_first(tmp_path):
    _job(tmp_path, "old-done").finish("done")
    _age(tmp_path, "old-done", 50)
    _job(tmp_path, "new-done").finish("done")
    _job(tmp_path, "quiet")
    _age(tmp_path, "quiet", 600)
    _job(tmp_path, "live")
    assert [j["job_id"] for j in bd.list_jobs(tmp_path, stale_s=120)] == ["live", "quiet", "new-done", "old-done"]


def test_log_tail_and_progress_fraction(tmp_path):
    b = _job(tmp_path, "j", done=3, total=12)
    for i in range(30):
        b.log(f"line {i}")
    j = bd.list_jobs(tmp_path, tail=5)[0]
    assert j["log_tail"] == [f"line {i}" for i in range(25, 30)]
    assert j["pct"] == 25.0


def test_corrupt_or_foreign_files_are_skipped(tmp_path):
    (tmp_path / "garbage.json").write_text("{not json")
    (tmp_path / "other.json").write_text(json.dumps({"schema": "something/else"}))
    _job(tmp_path, "real")
    assert [j["job_id"] for j in bd.list_jobs(tmp_path)] == ["real"]


def test_missing_root_is_an_empty_board(tmp_path):
    assert bd.list_jobs(tmp_path / "nope") == []


def test_tui_frame_shows_each_job_with_status_and_bar(tmp_path):
    _job(tmp_path, "sand032-s6", package="local-mailroom-sandbox", title="sorter n=1000", done=458, total=1000, phase="SORTING")
    _job(tmp_path, "gepa-ab", package="eval-environment", title="v2 A/B").finish("done")
    frame = bd.render_board(bd.list_jobs(tmp_path), width=100, on=False)
    assert "THE MAILROOM" in frame or "MAILROOM" in frame
    assert "sorter n=1000" in frame and "local-mailroom-sandbox" in frame and "458/1000" in frame
    assert "eval-environment" in frame and "DONE" in frame and "RUNNING" in frame
    assert "\033" not in frame  # on=False → plain


def test_tui_frame_empty_board_explains_how_to_publish(tmp_path):
    frame = bd.render_board([], width=100, on=False)
    assert "no jobs" in frame.lower() and "Beacon(" in frame


def _serve(root):
    httpd = bd.make_board_server("127.0.0.1", 0, root=root, stale_s=120, interval=0.05)
    Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def test_http_index_jobs_stream_and_404(tmp_path):
    _job(tmp_path, "sand032-s6", title="sorter n=1000", done=10, total=100)
    httpd, port = _serve(tmp_path)
    try:
        c = HTTPConnection("127.0.0.1", port, timeout=3)
        c.request("GET", "/")
        r = c.getresponse()
        page = r.read().decode()
        assert r.status == 200 and "MAILROOM" in page and "/api/jobs/stream" in page
        c.request("GET", "/api/jobs")
        r = c.getresponse()
        data = json.loads(r.read())
        assert r.status == 200 and data["jobs"][0]["job_id"] == "sand032-s6" and data["root"] == str(tmp_path)
        c.request("GET", "/nope")
        r = c.getresponse()
        r.read()
        assert r.status == 404
        s = HTTPConnection("127.0.0.1", port, timeout=3)
        s.request("GET", "/api/jobs/stream")
        r = s.getresponse()
        assert r.getheader("Content-Type").startswith("text/event-stream")
        line = r.fp.readline().decode()
        assert line.startswith("data: ") and json.loads(line[6:])["jobs"][0]["done"] == 10
    finally:
        httpd.board_stop.set()
        httpd.shutdown()
        httpd.server_close()


def test_board_page_escapes_job_text_and_uses_the_theme(tmp_path):
    page = bd.board_page().decode()
    assert "esc(j.title)" in page and "esc(l)" in page
    from mailroom_sandbox.tui.web import THEME
    for name, value in THEME.items():
        assert f"--{name}: {value}" in page
    assert re.search(r"\.card\.(stalled|failed)", page)


# ── CLI + runner wiring ─────────────────────────────────────────────────────
def test_cli_beacon_update_writes_and_finishes(tmp_path, monkeypatch):
    from mailroom_sandbox import cli

    monkeypatch.setenv("MAILROOM_BEACON_DIR", str(tmp_path))
    assert cli.main(["beacon", "update", "--job", "shell-job", "--package", "scripts", "--title", "nightly",
                     "--phase", "SORTING", "--done", "4", "--total", "10", "--metric", "p50_s=6.8",
                     "--log", "doc 4 ok"]) == 0
    j = bd.list_jobs(tmp_path)[0]
    assert (j["job_id"], j["done"], j["total"], j["phase"], j["title"]) == ("shell-job", 4, 10, "SORTING", "nightly")
    assert j["metrics"]["p50_s"] == "6.8" and j["log_tail"] == ["doc 4 ok"]
    assert cli.main(["beacon", "update", "--job", "shell-job", "--package", "scripts", "--finish", "done"]) == 0
    j = bd.list_jobs(tmp_path)[0]
    assert j["status"] == "done" and j["done"] == 4 and j["title"] == "nightly"  # resumes, not reset


def test_cli_board_once_renders_tui(tmp_path, monkeypatch, capsys):
    from mailroom_sandbox import cli

    _job(tmp_path, "j1", title="corr n=100", done=5, total=10)
    assert cli.main(["board", "--tui", "--once", "--root", str(tmp_path)]) == 0
    assert "corr n=100" in capsys.readouterr().out


def test_cli_board_web_wires_server(tmp_path, monkeypatch):
    from mailroom_sandbox import cli

    seen = {}
    monkeypatch.setattr(bd, "serve_board", lambda **kw: seen.update(kw) or 0)
    assert cli.main(["board", "--root", str(tmp_path), "--port", "0", "--no-browser", "--stale-s", "30"]) == 0
    assert (seen["root"], seen["port"], seen["open_browser"], seen["stale_s"], seen["demo"]) == (tmp_path, 0, False, 30.0, False)


def test_demo_writer_publishes_a_progressing_job(tmp_path):
    w = bd.DemoJobs(tmp_path, n=4)
    for _ in range(3):
        w.step()
    jobs = {j["job_id"]: j for j in bd.list_jobs(tmp_path)}
    assert "demo-sorter" in jobs and jobs["demo-sorter"]["done"] == 3
    for _ in range(10):
        w.step()
    assert any(j["status"] == "done" for j in bd.list_jobs(tmp_path))


def test_runner_publishes_a_beacon_for_run_start(tmp_path, monkeypatch):
    from mailroom_sandbox.job import runner

    monkeypatch.setenv("MAILROOM_BEACON_DIR", str(tmp_path / "beacons"))
    events = []
    wrapped, finish = runner._beacon_hook("sand032-x", task="correspondence_specialist", on_event=events.append)
    wrapped({"cursor": 3, "total": 10, "ok": 2, "errors": 1, "state": "running"})
    j = bd.list_jobs(tmp_path / "beacons")[0]
    assert (j["job_id"], j["package"], j["done"], j["total"], j["errors"]) == ("sand032-x", "local-mailroom-sandbox", 3, 10, 1)
    assert events == [{"cursor": 3, "total": 10, "ok": 2, "errors": 1, "state": "running"}]  # original consumer still called
    finish({"state": "done", "cursor": 10, "total": 10})
    assert bd.list_jobs(tmp_path / "beacons")[0]["status"] == "done"


def test_launcher_passes_beacon_and_board_through(tmp_path):
    import subprocess
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [str(repo / "scripts" / "mailroom-tui"), "beacon", "update", "--root", str(tmp_path),
         "--job", "sh", "--package", "scripts", "--done", "1", "--total", "2"],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert bd.list_jobs(tmp_path)[0]["job_id"] == "sh"
    r = subprocess.run([str(repo / "scripts" / "mailroom-tui"), "board", "--tui", "--once", "--root", str(tmp_path)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "sh" in r.stdout


def test_board_default_port_does_not_collide_with_watch_web(tmp_path, monkeypatch):
    from mailroom_sandbox import cli
    from mailroom_sandbox.tui import web as web_mod

    seen = {}
    monkeypatch.setattr(bd, "serve_board", lambda **kw: seen.update(kw) or 0)
    cli.main(["board", "--root", str(tmp_path), "--no-browser"])
    assert seen["port"] == bd.DEFAULT_PORT == 8767 != web_mod.DEFAULT_PORT
