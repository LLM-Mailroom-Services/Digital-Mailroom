"""`sandbox dev` / `watch --web --demo`: a synthetic run that exercises every web panel (no Modal)."""

import json

from mailroom_sandbox.tui import web as web_mod
from mailroom_sandbox.tui.demo import DemoRun
from mailroom_sandbox.watch import LogBuffer, compose_watch_state


def _state(demo, sink, now):
    store, app = demo.resolve()
    return compose_watch_state(
        store=store, app=app, sink=sink, ledger=demo.ledger, cap_usd=5.0,
        times_dir=demo.times_dir, serving_dir=demo.serving_dir, started=now, boot_mark={},
    )


def test_demo_walks_every_lifecycle_phase_and_ends_with_a_scorecard(tmp_path):
    demo = DemoRun(tmp_path, n_docs=3)
    sink = LogBuffer(None)
    phases, card = [], None
    for tick in range(40):
        demo.step(sink, tick=tick)
        st = _state(demo, sink, now=0)
        phase = st["lifecycle"]["phase"]
        if not phases or phases[-1] != phase:
            phases.append(phase)
        if phase == "TEARDOWN" and st["scorecard"]:
            card = st["scorecard"]
        if phase == "STOPPED":
            break
    assert phases == ["DEPLOYING", "COLD BOOT", "PREFLIGHT", "SORTING", "TEARDOWN", "STOPPED"]
    assert card, "scorecard shows at teardown"
    text = "\n".join(card)
    for label in ("wall", "throughput", "cold boot"):  # serving record fields actually render
        line = next(l for l in text.splitlines() if l.strip().startswith(label))
        assert not line.rstrip().endswith("—"), line
    tok = next(l for l in text.splitlines() if l.strip().startswith("tokens in/out"))
    assert "0 / 0" not in tok, tok
    store, _ = demo.resolve()
    items = store.load_items()
    assert len(items) == 3 and any(not i["ok"] for i in items)  # a returned doc shows in-tray errors
    assert json.loads(demo.ledger.read_text())["spent_usd"] > 0
    assert any(role["role"] in ("kv", "ready") for role in st["logs"])


def test_demo_loops_to_a_fresh_run_after_stopping(tmp_path):
    demo = DemoRun(tmp_path, n_docs=2)
    sink = LogBuffer(None)
    for tick in range(60):
        demo.step(sink, tick=tick)
    store, _ = demo.resolve()
    assert demo.cycle >= 1
    assert len(store.load_items()) <= 2


def test_session_tick_hook_advances_demo_on_refresh(tmp_path):
    demo = DemoRun(tmp_path, n_docs=2)
    session = web_mod.WatchWebSession(
        resolve=demo.resolve, ledger=demo.ledger, cap_usd=5.0, times_dir=demo.times_dir,
        log_path=None, serving_dir=demo.serving_dir, interval=0.01, follow_logs=False,
        tick=demo.step,
    )
    first = session.refresh()["lifecycle"]["phase"]
    for _ in range(12):
        last = session.refresh()
    assert first == "DEPLOYING" and last["lifecycle"]["phase"] != "DEPLOYING"
    assert "hero_html" in last


def test_cli_watch_web_demo_needs_no_config_or_modal(monkeypatch):
    from mailroom_sandbox import cli

    seen = {}
    monkeypatch.setattr(web_mod, "serve_watch_web", lambda **kw: seen.update(kw) or 0)
    assert cli.main(["watch", "--web", "--demo", "--no-browser", "--port", "0"]) == 0
    assert seen["logs"] is False and callable(seen["tick"])
    store, app = seen["resolve"]()
    assert app == "sandbox-vllm-demo" and store.run_id == "sand032-demo"


def test_cli_dev_is_the_demo_web_server(monkeypatch):
    from mailroom_sandbox import cli

    seen = {}
    monkeypatch.setattr(web_mod, "serve_watch_web", lambda **kw: seen.update(kw) or 0)
    assert cli.main(["dev", "--no-browser", "--port", "0"]) == 0
    assert (seen["host"], seen["port"], seen["open_browser"]) == ("127.0.0.1", 0, False)
    assert callable(seen["tick"])
