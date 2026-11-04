"""Browser mailroom watch UI — payload + HTTP handlers (network-free)."""

import json
from http.client import HTTPConnection
from threading import Thread

from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.tui import web as web_mod
from mailroom_sandbox.watch import LogBuffer, compose_watch_state


def _store(tmp_path, *, replicas=2):
    s = RunStore(tmp_path / "sand032-x")
    s.write_lock(
        {
            "run_id": "sand032-x",
            "task": "correspondence_specialist",
            "engine": {
                "model": "Qwen/Qwen3-8B-AWQ",
                "vllm": {"kv_cache_dtype": "fp8"},
                "modal": {"gpu": "L4", "max_containers": replicas, "min_containers": replicas},
            },
            "job": {"concurrency": 16},
        }
    )
    s.write_checkpoint(state="running", cursor=3, total=10, remote=None)
    for i, (ok, lat) in enumerate([(True, 1000.0), (True, 3000.0), (False, 500.0)]):
        s.append_item(
            {
                "item_id": f"d{i}",
                "ok": ok,
                "latency_ms": lat,
                "error": None if ok else "OpenAIConnectionError: x",
                "score": {"overall_extraction_score": 0.5} if ok else {},
                "prompt_tokens": 100 + i,
                "completion_tokens": 10 + i,
            }
        )
    return s


def test_compose_watch_state_is_json_friendly(tmp_path):
    store = _store(tmp_path)
    sink = LogBuffer(None)
    sink.append("vLLM ready on port 8000")
    sink.append("ERROR boom")
    state = compose_watch_state(
        store=store,
        app="sandbox-vllm-sand032",
        sink=sink,
        ledger=None,
        cap_usd=5.0,
        times_dir=None,
        serving_dir=tmp_path / "serving",
        started=__import__("time").time() - 60,
        boot_mark={},
    )
    raw = json.dumps(state)
    data = json.loads(raw)
    assert data["snapshot"]["run_id"] == "sand032-x"
    assert data["spend"]["cap_usd"] == 5.0
    assert len(data["logs"]) == 2
    assert data["logs"][1]["role"] == "error"
    assert data["progress"]["done"] == 3
    assert data["snapshot"]["prompt_tokens"] == 303
    assert data["spend"]["spent_usd"] > 0  # no spend.json → live job GPU $
    assert data["spend"]["total_usd"] > 0
    assert data["spend"]["done"] == 3
    assert data["spend"]["total_tokens"] == 336


def test_should_open_browser_respects_no_browser(monkeypatch):
    monkeypatch.delenv("NO_BROWSER", raising=False)
    assert web_mod.should_open_browser(stream=type("S", (), {"isatty": lambda self: True})())
    monkeypatch.setenv("NO_BROWSER", "1")
    assert not web_mod.should_open_browser(stream=type("S", (), {"isatty": lambda self: True})())


def test_browser_url_maps_wildcard_bind():
    assert web_mod.browser_url("0.0.0.0", 8765) == "http://127.0.0.1:8765/"


def test_web_handler_serves_index_and_state(tmp_path):
    store = _store(tmp_path)

    def resolve():
        return store, "sandbox-vllm-test"

    session = web_mod.WatchWebSession(
        resolve=resolve,
        ledger=None,
        cap_usd=5.0,
        times_dir=None,
        log_path=None,
        serving_dir=tmp_path / "serving",
        interval=0.05,
        follow_logs=False,
    )
    session.refresh()
    handler = web_mod.make_handler(session)
    httpd = web_mod.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("GET", "/")
        resp = conn.getresponse()
        assert resp.status == 200
        body = resp.read()
        assert b"Tray TUI" in body and b"THE MAILROOM" in body
        assert b"text/event-stream" not in body

        conn.request("GET", "/api/state")
        resp = conn.getresponse()
        assert resp.status == 200
        state = json.loads(resp.read().decode())
        assert state["ok"] is True
        assert state["app"] == "sandbox-vllm-test"
    finally:
        session.stop()
        httpd.shutdown()
        httpd.server_close()


# ── theming parity, hero art, transport, CLI wiring ────────────────────────
import re
import time

from mailroom_sandbox.tui import pretty_log as pl
from mailroom_sandbox.watch import _LOG_ROLE


def _hex(rgb):
    return "#%02x%02x%02x" % rgb


def _session(tmp_path, resolve=None, interval=0.05):
    store = _store(tmp_path)
    return web_mod.WatchWebSession(
        resolve=resolve or (lambda: (store, "sandbox-vllm-test")),
        ledger=None,
        cap_usd=5.0,
        times_dir=None,
        log_path=None,
        serving_dir=tmp_path / "serving",
        interval=interval,
        follow_logs=False,
    )


def _serve(session):
    httpd = web_mod.ThreadingHTTPServer(("127.0.0.1", 0), web_mod.make_handler(session))
    Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def test_web_theme_is_derived_from_pretty_log_palette():
    t = web_mod.THEME
    assert t["blue"] == _hex(pl.BLUE) and t["teal"] == _hex(pl.TEAL) and t["cyan"] == _hex(pl.CYAN)
    assert t["navy"] == _hex(pl.NAVY) and t["gold"] == _hex(pl.GOLD) and t["cream"] == _hex(pl.CREAM)
    assert t["snow"] == _hex(pl.SNOW) and t["muted"] == _hex(pl.MUTED) and t["sky"] == _hex(pl.SKY)
    assert t["amber"] == _hex(pl.AMBER_FACE) and t["extrude"] == _hex(pl.AMBER_EXTRUDE)


def test_index_page_carries_every_theme_token_and_log_role():
    page = web_mod._html_page().decode()
    for name, value in web_mod.THEME.items():
        assert f"--{name}: {value}" in page
    for role in _LOG_ROLE:  # every classified log role has a themed CSS class
        assert f".log-line.{role}" in page


def test_ansi_to_html_maps_truecolor_bold_and_reset():
    html = web_mod.ansi_to_html("\033[1;38;2;245;196;69mAB\033[0mC")
    assert html == '<span style="color:#f5c445;font-weight:bold">AB</span>C'


def test_ansi_to_html_escapes_markup_and_background():
    html = web_mod.ansi_to_html("\033[48;2;11;42;74m<b>&\033[0m")
    assert "&lt;b&gt;&amp;" in html and "background:#0b2a4a" in html
    assert "\033" not in html


def test_state_carries_terminal_hero_as_html(tmp_path):
    state = _session(tmp_path).refresh()
    hero = state["hero_html"]
    assert "\033" not in hero  # all ANSI converted
    assert _hex(pl.AMBER_FACE) in hero  # the amber 3D wordmark survives
    assert "DIGITAL MAILROOM" in hero and "sand032-x" in hero
    json.dumps(state)  # still SSE/JSON-safe


def test_sse_stream_emits_state_events(tmp_path):
    session = _session(tmp_path)
    session.refresh()
    httpd, port = _serve(session)
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request("GET", "/api/stream")
        resp = conn.getresponse()
        assert resp.status == 200
        assert resp.getheader("Content-Type").startswith("text/event-stream")
        line = resp.fp.readline().decode()
        assert line.startswith("data: ")
        state = json.loads(line[len("data: "):])
        assert state["ok"] is True and state["snapshot"]["run_id"] == "sand032-x"
    finally:
        session.stop()
        httpd.shutdown()
        httpd.server_close()


def test_unknown_path_is_404(tmp_path):
    session = _session(tmp_path)
    httpd, port = _serve(session)
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("GET", "/etc/passwd")
        assert conn.getresponse().status == 404
    finally:
        session.stop()
        httpd.shutdown()
        httpd.server_close()


def test_refresh_loop_surfaces_errors_to_the_ui(tmp_path):
    def broken():
        raise RuntimeError("run YAML missing")

    session = _session(tmp_path, resolve=broken, interval=0.01)
    t = Thread(target=session.run_refresh_loop, daemon=True)
    t.start()
    deadline = time.time() + 2
    while time.time() < deadline and session.snapshot()[1].get("error") == "initializing":
        time.sleep(0.01)
    session.stop()
    _, state = session.snapshot()
    assert state["ok"] is False and "run YAML missing" in state["error"]


def test_client_renders_errors_logs_scorecard_and_gate():
    page = web_mod._html_page().decode()
    # untrusted text is escaped before innerHTML; the hero is trusted server HTML
    assert "esc(e.text)" in page and "esc(l)" in page
    assert 'getElementById("hero").innerHTML = state.hero_html' in page
    assert "OVER GATE" in page and "scorecard-wrap" in page
    assert "SSE disconnected" in page
    assert "state.ok === false" in page
    assert 'metric("docs"' in page and 'metric("tokens"' in page


def test_cli_watch_web_wires_host_port_and_no_browser(monkeypatch, tmp_path):
    from mailroom_sandbox import cli

    cfg = tmp_path / "run.yaml"
    cfg.write_text("x")
    seen = {}
    monkeypatch.setattr(web_mod, "serve_watch_web", lambda **kw: seen.update(kw) or 0)
    rc = cli.main(["watch", "--config", str(cfg), "--web", "--port", "0", "--no-browser",
                   "--host", "127.0.0.1", "--no-logs"])
    assert rc == 0
    assert (seen["host"], seen["port"], seen["open_browser"], seen["logs"]) == ("127.0.0.1", 0, False, False)


def test_serve_watch_web_binds_ephemeral_port_and_prints_url(monkeypatch, tmp_path, capsys):
    store = _store(tmp_path)
    opened = []
    monkeypatch.setattr(web_mod.webbrowser, "open", lambda url: opened.append(url))

    def stop_immediately(self, *a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(web_mod.ThreadingHTTPServer, "serve_forever", stop_immediately)
    # real Ctrl+C unwinds inside serve_forever; the stub never starts the loop
    monkeypatch.setattr(web_mod.ThreadingHTTPServer, "shutdown", lambda self: None)
    rc = web_mod.serve_watch_web(
        resolve=lambda: (store, "sandbox-vllm-test"), ledger=None, logs=False,
        serving_dir=tmp_path / "serving", host="127.0.0.1", port=0, open_browser=False,
    )
    assert rc == 0 and opened == []
    assert re.search(r"Tray TUI watch \(browser\) at http://127\.0\.0\.1:\d+/", capsys.readouterr().err)


def test_dispatch_log_autoscrolls_its_scrolling_panel():
    page = web_mod._html_page().decode()
    # #logs sits inside the .log panel that owns overflow-y — scroll THAT to the newest line
    assert "const pane = logs.parentElement;" in page
    assert "pane.scrollTop = pane.scrollHeight;" in page


def test_narrow_screens_get_the_terminal_compact_hero(tmp_path):
    state = _session(tmp_path).refresh()
    compact = state["hero_compact_html"]
    assert "\033" not in compact and _hex(pl.AMBER_FACE) in compact
    # compact = the TUI's <90-col wordmark: narrower rows than the wide hero
    widest = lambda h: max(len(re.sub(r"<[^>]+>", "", l)) for l in h.split("\n"))
    assert widest(compact) < widest(state["hero_html"])
    page = web_mod._html_page().decode()
    assert 'id="hero-compact"' in page and "@media (max-width: 800px)" in page
    assert "#hero {{" not in page  # f-string braces are rendered, not leaked


def test_long_metric_values_wrap_inside_their_panel():
    assert "overflow-wrap: anywhere" in web_mod._html_page().decode()


def test_hero_font_scales_to_fit_its_column_count():
    page = web_mod._html_page().decode()
    # 100-col wide hero and 60-col compact hero at 0.6em/char monospace
    assert "font-size: min(12px, calc((100vw - 84px) / 60))" in page
    assert "font-size: min(12px, calc((100vw - 84px) / 36))" in page


def test_state_tokens_and_log_source_rendering():
    page = web_mod._html_page().decode()
    for phase in ("failed", "complete", "paused", "remote", "sorting"):
        assert f".stage-{phase}" in page
    assert 'class="src"' in page or 'class="src"' in page.replace("'", '"')
    assert "Tray TUI watcher" in page or "watcher_label" in page
    assert "lifecycle-pulse" in page


def test_watch_reads_published_services_without_probing(tmp_path, monkeypatch):
    from mailroom_sandbox.tui.services_snapshot import publish_services
    import httpx

    def no_network(*args, **kwargs):
        raise AssertionError('watch rendering must not probe services')

    monkeypatch.setattr(httpx, 'get', no_network)
    publish_services([{'name': 'provider', 'state': 'fail', 'detail': 'missing endpoint', 'hint': 'sandbox modal deploy'}], profile='modal-vllm', live=False)
    store = _store(tmp_path)
    session = web_mod.WatchWebSession(resolve=lambda: (store, 'sandbox-vllm'), ledger=None,
        cap_usd=5, times_dir=None, serving_dir=tmp_path / 'serving', interval=0.1, follow_logs=False)
    try:
        state = session.refresh()
        assert state['services']['services'][0]['state'] == 'fail'
        page = web_mod._html_page().decode()
        assert 'services(state && state.services)' in page and 'id="svc"' in page
        assert '.replace(/"/g,"&quot;")' in page
    finally:
        session.stop()


def test_follow_switch_replaces_log_streams_and_header(tmp_path, monkeypatch):
    from mailroom_sandbox import watch
    from mailroom_sandbox.tui.demo import DemoRun

    first = _store(tmp_path)
    second, _ = DemoRun(tmp_path / "second").resolve()
    lock = second.read_lock()
    lock["engine"]["model"] = "provider/second-model"
    lock["task"] = "sorter"
    second.lock_path.write_text(json.dumps(lock))
    current = [first, "first-app"]
    streams = []
    monkeypatch.setattr(watch, "start_log_streams", lambda store, app, sink, stop: streams.append((app, stop)))
    session = web_mod.WatchWebSession(resolve=lambda: tuple(current), ledger=None, cap_usd=5,
        times_dir=None, serving_dir=tmp_path / "serving", interval=1, follow_logs=True)
    try:
        a = session.refresh()
        session.sink.append("old app line")
        current[:] = [second, "second-app"]
        b = session.refresh()
        assert "second-model" in b["hero_html"] and "second-model" not in a["hero_html"]
        assert b["route_label"] == "INBOX → SORTER → TRAY"
        assert "old app line" not in str(b["logs"])
        assert streams[0][1].is_set() and not streams[1][1].is_set()
    finally:
        session.stop()
    assert streams[-1][1].is_set()


def test_web_bind_failure_stops_session(tmp_path, monkeypatch):
    session = _session(tmp_path)
    monkeypatch.setattr(web_mod, "WatchWebSession", lambda **kw: session)
    def busy(*a, **k):
        raise OSError("busy")
    monkeypatch.setattr(web_mod, "ThreadingHTTPServer", busy)
    import pytest
    with pytest.raises(OSError, match="busy"):
        web_mod.serve_watch_web(resolve=session.resolve, ledger=None, logs=False)
    assert session._stop.is_set() and session._log_stop.is_set()


def test_watch_state_carries_capped_document_timeline(tmp_path):
    from mailroom_sandbox.tui.demo import DemoRun
    from mailroom_sandbox.tui import web
    from mailroom_sandbox import watch

    demo = DemoRun(tmp_path)
    session = web.WatchWebSession(resolve=demo.resolve, ledger=demo.ledger, cap_usd=5,
        times_dir=demo.times_dir, serving_dir=demo.serving_dir, interval=0.1, follow_logs=False,
        tick=demo.step)
    for _ in range(12):
        state = session.refresh()
    store, _ = demo.resolve()
    items = store.load_items()
    assert state["timeline"] == [i.get("ok", True) is not False for i in items][-watch.TIMELINE_MAX:]
    assert False in state["timeline"]  # the demo returns one document
    page = web._html_page().decode()
    assert 'role="tablist"' in page and 'aria-controls="view-terminal"' in page
    assert 'id="keymap"' in page and "rel=\"icon\"" in page
    session.stop()


def test_closing_a_log_buffer_hands_its_writer_lock_to_the_next(tmp_path):
    from mailroom_sandbox.watch import LogBuffer

    log = tmp_path / "modal-app.log"
    old = LogBuffer(log)
    old.append("first")
    blocked = LogBuffer(log)  # a second buffer on the same file cannot write …
    blocked.append("dropped")
    old.close()
    blocked.close()
    new = LogBuffer(log)  # … until the holder closes
    new.append("second")
    old.append("late line from a stopped stream")
    assert log.read_text().splitlines() == ["first", "second"]


def _no_logs_session(store, *, follow):
    return web_mod.WatchWebSession(resolve=lambda: (store, "app"), ledger=None, cap_usd=5.0, times_dir=None,
                                   serving_dir=store.dir, interval=1.0, follow_logs=follow)


def test_no_logs_still_loads_the_saved_dispatch_log(tmp_path):
    from mailroom_sandbox.job.checkpoint import RunStore

    store = RunStore(tmp_path / "run-a")
    (store.dir / "modal-app.log").write_text("saved line\n")
    session = _no_logs_session(store, follow=False)
    session.refresh()
    assert session.sink.tail(5) == ["saved line"]


def test_switching_runs_keeps_the_log_file_writable(tmp_path, monkeypatch):
    from mailroom_sandbox.job.checkpoint import RunStore

    shared = tmp_path / "logs" / "modal-app.log"  # SAND-032: both runs resolve to one file
    stores = [RunStore(tmp_path / "run-a"), RunStore(tmp_path / "run-b")]
    current = {"store": stores[0]}
    monkeypatch.setattr("mailroom_sandbox.watch.start_log_streams", lambda *a, **k: [])
    session = web_mod.WatchWebSession(resolve=lambda: (current["store"], "app"), ledger=None, cap_usd=5.0,
                                      times_dir=None, log_path=shared, serving_dir=tmp_path, interval=1.0,
                                      follow_logs=True)
    session.refresh()
    session.sink.append("run a")
    current["store"] = stores[1]
    session.refresh()
    session.sink.append("run b")
    assert shared.read_text().splitlines() == ["run a", "run b"]
