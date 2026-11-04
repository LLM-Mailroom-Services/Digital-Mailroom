"""One browser watcher: every entry point serves the same page as `sandbox dev` (network-free)."""

from __future__ import annotations

from http.client import HTTPConnection
from pathlib import Path
from threading import Thread
from types import SimpleNamespace

import pytest

from mailroom_sandbox import cli
from mailroom_sandbox import experiments as exp_mod
from mailroom_sandbox.job import spec as spec_mod
from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.tui import web as web_mod
from mailroom_sandbox.tui.demo import CAMPAIGN_RUNS, RUN_ID, DemoRun

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def served(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(web_mod, "serve_watch_web", lambda **kw: calls.append(kw) or 0)
    return calls


def _real_run(run_id="parity-run"):
    store = RunStore(spec_mod.run_dir(run_id))
    store.write_lock({"run_id": run_id, "task": "sorter", "engine": {"model": "m"}, "job": {"concurrency": 2}})
    store.write_checkpoint(state="running", cursor=0, total=2, remote=None)
    return store


@pytest.mark.parametrize("argv", [
    ["dev", "--no-browser"],
    ["dev", "--pipeline", "--no-browser"],
    ["web", "--demo", "--no-browser"],
    ["web", "--demo", "--pipeline", "--no-browser"],
    ["watch", "--web", "--demo", "--no-browser"],
    ["web", "parity-run", "--no-browser"],
    ["web", "--no-browser"],
    ["watch", "--web", "parity-run", "--no-browser"],
])
def test_every_browser_entry_point_uses_the_one_web_server(argv, served, job_data_dir):
    _real_run()
    assert cli.main(argv) == 0
    assert len(served) == 1
    kw = served[0]
    store, _app = kw["resolve"]()
    assert isinstance(store, RunStore)
    assert kw["campaign_path"] is not None  # every entry point can render the Campaign tab


def test_experiment_watch_uses_the_one_web_server(served, job_data_dir, tmp_path, monkeypatch):
    folder = tmp_path / "study"
    folder.mkdir()
    (folder / "experiment.yaml").write_text("schema: sandbox.experiment/v1\n")
    runs = [(folder / "a.yaml", SimpleNamespace(run_id="parity-run"))]
    monkeypatch.setattr(exp_mod, "_load", lambda p: (Path(p).resolve(), SimpleNamespace(study="s", design="d"), runs))
    _real_run()
    assert cli.main(["experiment", "watch", "--config", str(folder / "experiment.yaml"), "--no-browser"]) == 0
    assert len(served) == 1 and served[0]["campaign_path"]("parity-run") == folder / "experiment.yaml"


def test_launcher_script_routes_web_and_dev_to_the_same_commands():
    body = (REPO / "scripts" / "mailroom-tui").read_text()
    assert 'run watch --web "$@"' in body and 'run dev "$@"' in body


def _serve(session):
    httpd = web_mod.ThreadingHTTPServer(("127.0.0.1", 0), web_mod.make_handler(session))
    Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def _get(httpd, path):
    conn = HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
    conn.request("GET", path)
    resp = conn.getresponse()
    return resp.status, dict(resp.getheaders()), resp.read()


def _session(resolve, tmp_path, **kw):
    return web_mod.WatchWebSession(resolve=resolve, ledger=None, cap_usd=5.0, times_dir=None, log_path=None,
                                   serving_dir=tmp_path / "serving", interval=0.05, follow_logs=False, **kw)


def test_demo_and_real_watchers_serve_byte_identical_pages_and_the_same_build(tmp_path, job_data_dir):
    demo = DemoRun(tmp_path / "demo")
    demo_session = _session(demo.resolve, tmp_path, tick=demo.step, campaign_path=demo.campaign_path)
    store = _real_run()
    real_session = _session(lambda: (store, "app"), tmp_path)
    demo_session.refresh()
    real_session.refresh()
    servers = [_serve(demo_session), _serve(real_session)]
    try:
        (s1, h1, page1), (s2, h2, page2) = (_get(h, "/") for h in servers)
        assert s1 == s2 == 200 and page1 == page2 == web_mod._html_page()
        assert "no-store" in h1["Cache-Control"] and "no-store" in h2["Cache-Control"]
        build = web_mod.page_build()
        assert f'const PAGE_BUILD = "{build}";'.encode() in page1 and b"__PAGE_BUILD__" not in page1
        assert demo_session.snapshot()[1]["page_build"] == real_session.snapshot()[1]["page_build"] == build
    finally:
        for h in servers:
            h.shutdown()
            h.server_close()


def test_waiting_and_error_states_also_carry_the_build(tmp_path):
    session = _session(lambda: (_ for _ in ()).throw(RuntimeError("x")), tmp_path)
    session.mark_waiting("waiting")
    assert session.snapshot()[1]["page_build"] == web_mod.page_build()


def test_page_build_is_stable_and_tracks_the_template(monkeypatch):
    first = web_mod.page_build()
    assert first == web_mod.page_build() and len(first) == 12
    web_mod.page_build.cache_clear()
    monkeypatch.setattr(web_mod, "_html_page_template", lambda: "<html>changed __PAGE_BUILD__</html>")
    try:
        assert web_mod.page_build() != first
    finally:
        web_mod.page_build.cache_clear()


def test_stale_tabs_reload_once_per_build_and_never_loop():
    page = web_mod._html_page().decode()
    render = page[page.index("function render(state) {"):]
    assert render.splitlines()[1].strip() == "if (checkBuild(state)) return;"
    check = page[page.index("function checkBuild(state) {"):page.index("const LOG_CLASS")]
    assert "location.reload()" in check and 'sessionStorage.getItem("mailroom-reload-for")' in check
    assert "if (tried === live) return false;" in check
    assert "hard-refresh" not in page


def test_dev_demo_fills_the_campaign_tab_through_the_real_reader(tmp_path):
    demo = DemoRun(tmp_path / "demo")
    session = _session(demo.resolve, tmp_path, tick=demo.step, campaign_path=demo.campaign_path)
    campaign = session.refresh()["campaign"]
    assert campaign["study"] == "demo-study" and campaign["current"] == RUN_ID
    assert [r["run_id"] for r in campaign["runs"]] == list(CAMPAIGN_RUNS)
    states = {r["run_id"]: r["state"] for r in campaign["runs"]}
    assert states["sand032-demo-baseline"] == "done" and states["sand032-demo-followup"] == "waiting"
    assert campaign["completed"] == 1 and campaign["total"] == 3
    assert (tmp_path / "demo" / "runs" / "sand032-demo-followup").is_dir()  # never falls back to a real run
    for _ in range(4):
        campaign = session.refresh()["campaign"]
    live = next(r for r in campaign["runs"] if r["run_id"] == RUN_ID)
    assert live["total"] == demo.n_docs  # the live demo run's own checkpoint, not the global runs root


def test_campaign_sibling_runs_are_read_beside_the_watched_run(tmp_path, monkeypatch):
    from mailroom_sandbox.tui import tray_context as tc

    folder = tmp_path / "exp"
    folder.mkdir()
    runs = [(None, SimpleNamespace(run_id="sib-a")), (None, SimpleNamespace(run_id="sib-b"))]
    monkeypatch.setattr(exp_mod, "_load", lambda p: (p, SimpleNamespace(study="s", design="d"), runs))
    runs_dir = tmp_path / "elsewhere"
    RunStore(runs_dir / "sib-a").write_checkpoint(state="done", cursor=3, total=3)
    ctx = tc.campaign_context(folder / "experiment.yaml", "sib-b", runs_dir)
    assert {r["run_id"]: r["state"] for r in ctx["runs"]} == {"sib-a": "done", "sib-b": "waiting"}
