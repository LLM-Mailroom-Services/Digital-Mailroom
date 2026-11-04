"""Opt-in real Chromium UX checks; no network providers or paid jobs.

SANDBOX_BROWSER_TESTS=1 uv run --extra dev --with playwright pytest -q tests/test_observer_browser.py
Set SANDBOX_BROWSER_EXECUTABLE to a local Chromium/Chrome executable, or install
Playwright Chromium first. These are separate from the default offline gate.
"""
import os
from http.server import ThreadingHTTPServer
from threading import Thread

import pytest

from mailroom_sandbox.tui import web
from mailroom_sandbox.tui.demo import DemoRun


@pytest.mark.parametrize("width,height", [(375, 812), (1280, 900)])
def test_operator_workspaces_and_keyboard(tmp_path, width, height):
    if os.environ.get("SANDBOX_BROWSER_TESTS") != "1":
        pytest.skip("SANDBOX_BROWSER_TESTS not set")
    pw = pytest.importorskip("playwright.sync_api")
    demo = DemoRun(tmp_path)
    session = web.WatchWebSession(resolve=demo.resolve, ledger=demo.ledger,
        cap_usd=5, times_dir=demo.times_dir, serving_dir=demo.serving_dir,
        interval=0.1, follow_logs=False)
    state = session.refresh()
    server = ThreadingHTTPServer(("127.0.0.1", 0), web.make_handler(session))
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        with pw.sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get("SANDBOX_BROWSER_EXECUTABLE"))
            page = browser.new_page(viewport={"width": width, "height": height}, reduced_motion="reduce")
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}")
            page.wait_for_function("commandCatalog.length > 0 && operatorState.ok")
            assert page.locator('[data-view="overview"]').is_visible()
            assert not page.locator('[data-view="terminal"]').is_visible()
            assert not page.locator(".brand-art").get_attribute("open")

            page.get_by_role("tab", name="Terminal").click()
            assert page.locator("#command-input").evaluate("el => el === document.activeElement")
            for group, child in [("run", "start"), ("experiment", "create"), ("modal", "deploy")]:
                page.locator("#command-input").fill("menu")
                page.locator("#command-input").press("Enter")
                page.locator("#command-menu").select_option(group)
                page.locator("#command-menu").select_option(child)
                assert page.locator("#command-path").inner_text() == f"sandbox {group} {child}"
                assert page.locator("#command-menu").is_disabled()
                page.get_by_role("button", name="← Parent").click()
                assert page.locator("#command-path").inner_text() == f"sandbox {group}"
                assert page.locator("#command-menu").is_enabled()

            # Two-level primary tasks: eval → specialist|pipeline → target.
            page.locator("#command-input").fill("menu eval")
            page.locator("#command-input").press("Enter")
            options = page.locator("#command-menu option").all_inner_texts()
            assert options[1:] == ["specialist", "pipeline"]
            page.locator("#command-menu").select_option("pipeline")
            assert page.locator("#command-menu").is_enabled()
            page.locator("#command-menu").select_option(label="merger_agreement")
            assert page.locator("#command-input").input_value() == "eval pipeline --class merger_agreement --mock"
            assert "sandbox eval pipeline --class merger_agreement" in page.locator("#command-output").inner_text()
            assert page.locator("#command-input").evaluate("el => el === document.activeElement")

            field = page.locator("#command-input")
            field.fill("run res")
            field.press("Tab")
            assert field.input_value() == "run resume "
            field.fill("status")
            field.press("Enter")
            assert state["snapshot"]["run_id"] in page.locator("#command-output").inner_text()
            field.press("ArrowUp")
            assert field.input_value() == "status"
            field.press("ArrowDown")
            assert field.input_value() == ""
            field.fill("secret=dummy-browser-secret")
            field.press("Enter")
            assert "dummy-browser-secret" not in page.locator("#command-output").inner_text()
            field.press("Control+l")
            assert page.locator("#command-output").inner_text() == ""

            page.get_by_role("tab", name="Configuration").click()
            config = page.locator("#configuration")
            assert "engine" in config.inner_text() and "model" in config.inner_text()
            assert "True" not in config.inner_text()  # manifest values, not Python reprs
            page.get_by_role("tab", name="Campaign").click()
            assert "No campaign" in page.locator("#campaign-content").inner_text()
            page.get_by_role("tab", name="Overview").click()
            hostile = {**state, "logs": [
                {"text": f"line {i}", "role": "plain"} for i in range(80)] + [
                {"text": '<img src=x onerror="alert(1)"> ERROR', "role": "error"}]}
            page.evaluate("state => render(state)", hostile)
            assert page.locator("#logs img").count() == 0
            page.locator("#log-follow").uncheck()
            page.locator("#logs").evaluate("el => el.parentElement.scrollTop = 30")
            page.evaluate("state => render(state)", hostile)
            assert page.locator("#logs").evaluate("el => el.parentElement.scrollTop") == 30
            page.locator("#log-level").select_option("error")
            assert page.locator("#logs .log-line").count() == 1
            page.locator("#log-query").fill("no-match")
            assert "No matching" in page.locator("#logs").inner_text()
            page.locator("#log-query").press("Escape")
            assert page.locator("#log-query").input_value() == ""
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert not errors, errors
            output = os.environ.get("SANDBOX_BROWSER_SCREENSHOTS")
            if output:
                from pathlib import Path
                path = Path(output)
                path.mkdir(parents=True, exist_ok=True)
                page.locator("#log-level").select_option("all")
                page.locator("#log-follow").check()
                page.evaluate("state => render(state)", state)
                page.screenshot(path=str(path / f"overview-{width}.png"), full_page=True)
                page.get_by_role("tab", name="Terminal").click()
                page.locator("#command-input").fill("status")
                page.locator("#command-input").press("Enter")
                page.screenshot(path=str(path / f"terminal-{width}.png"), full_page=True)
            browser.close()
    finally:
        session.stop()
        server.shutdown()
        server.server_close()


def test_workspace_keybindings_and_replay_strip(tmp_path):
    if os.environ.get("SANDBOX_BROWSER_TESTS") != "1":
        pytest.skip("SANDBOX_BROWSER_TESTS not set")
    pw = pytest.importorskip("playwright.sync_api")
    demo = DemoRun(tmp_path)
    session = web.WatchWebSession(resolve=demo.resolve, ledger=demo.ledger,
        cap_usd=5, times_dir=demo.times_dir, serving_dir=demo.serving_dir,
        interval=0.1, follow_logs=False)
    state = session.refresh()
    server = ThreadingHTTPServer(("127.0.0.1", 0), web.make_handler(session))
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        with pw.sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get("SANDBOX_BROWSER_EXECUTABLE"))
            page = browser.new_page(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            base = f"http://127.0.0.1:{server.server_port}"
            # A deep link opens its workspace; an unknown hash falls back to Overview.
            page.goto(base + "/#configuration")
            page.wait_for_function("operatorState.ok")
            assert page.locator("#view-configuration").is_visible()
            page.goto(base + "/#nonsense")
            page.wait_for_function("operatorState.ok")
            assert page.locator("#view-overview").is_visible()

            # Number keys switch workspaces and keep tab ARIA state in sync.
            page.locator("body").press("3")
            assert page.get_by_role("tab", name="Configuration").get_attribute("aria-selected") == "true"
            assert page.evaluate("location.hash") == "#configuration"
            page.locator("body").press("1")
            assert page.locator("#view-overview").is_visible()
            # Arrow keys rove focus across the tablist and wrap at the ends.
            page.get_by_role("tab", name="Overview").focus()
            page.keyboard.press("ArrowLeft")
            assert page.get_by_role("tab", name="Campaign").get_attribute("aria-selected") == "true"
            assert page.evaluate("document.activeElement.id") == "tab-campaign"
            page.keyboard.press("Home")
            assert page.evaluate("document.activeElement.id") == "tab-overview"
            assert page.locator('[role="tab"][tabindex="0"]').count() == 1
            # Typing digits inside the terminal must not switch workspaces.
            page.locator("body").press("2")
            page.locator("#command-input").type("menu 1")
            assert page.locator("#view-terminal").is_visible()
            page.locator("#command-input").fill("")
            page.locator("#command-input").press("Escape")
            page.locator("body").click(position={"x": 5, "y": 5})

            # f toggles follow, w toggles the wordmark, ? opens the keymap dialog.
            page.locator("body").press("1")
            follow = page.locator("#log-follow")
            page.locator("body").press("f")
            assert not follow.is_checked()
            page.locator("body").press("f")
            assert follow.is_checked()
            page.locator("body").press("w")
            assert page.locator(".brand-art").get_attribute("open") is not None
            page.locator("body").press("w")
            page.locator("body").press("?")
            assert page.locator("#keymap").is_visible()
            page.keyboard.press("Escape")
            assert not page.locator("#keymap").is_visible()
            page.locator("body").press("/")
            assert page.evaluate("document.activeElement.id") == "log-query"

            # Replay strip: one lane per lifecycle phase, one tick per document and a
            # ruby diamond for each returned document.
            assert page.locator("#lanes .lane").count() == 6
            mixed = {**state, "snapshot": {**state["snapshot"], "state": "running", "done": 5, "total": 10,
                                           "ok": 4, "errors": 1},
                     "lifecycle": {"phase": "SORTING", "detail": "in flight", "elapsed_s": 75},
                     "timeline": [True, False, True, True, True]}
            page.evaluate("state => render(state)", mixed)
            assert page.locator("#timeline .tick").count() == 5
            assert page.locator("#timeline .tick.err").count() == 1
            assert page.locator("#timeline .cursor").count() == 1
            assert "5 of 10" in page.locator("#timeline").get_attribute("aria-label")
            assert page.locator("#lanes .lane.now .name").inner_text() == "sorting"
            assert page.locator("#replay-clock").inner_text().startswith("01:15")
            stats = page.locator("#stats").inner_text()
            assert "returned 1" in stats and "first-pass 80%" in stats
            # An endpoint run without driver stamps never deployed: deploy lanes read as skipped.
            endpoint = {**mixed, "layout": {**mixed["layout"], "times_path": None}}
            page.evaluate("state => render(state)", endpoint)
            assert page.locator("#lanes .lane.skip").count() == 3
            assert not errors, errors
            browser.close()
    finally:
        session.stop()
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize("width", [375, 1280])
def test_pipeline_floor_renders_routes_and_decisions(tmp_path, width):
    if os.environ.get("SANDBOX_BROWSER_TESTS") != "1":
        pytest.skip("SANDBOX_BROWSER_TESTS not set")
    pw = pytest.importorskip("playwright.sync_api")
    from mailroom_sandbox.watch import LogBuffer

    demo = DemoRun(tmp_path, n_docs=4, pipeline=True)
    for tick in range(10):
        demo.step(LogBuffer(None), tick=tick)
    session = web.WatchWebSession(resolve=demo.resolve, ledger=demo.ledger,
        cap_usd=5, times_dir=demo.times_dir, serving_dir=demo.serving_dir,
        interval=0.1, follow_logs=False)
    session.refresh()
    server = ThreadingHTTPServer(("127.0.0.1", 0), web.make_handler(session))
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        with pw.sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get("SANDBOX_BROWSER_EXECUTABLE"))
            page = browser.new_page(viewport={"width": width, "height": 900}, reduced_motion="reduce")
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}")
            page.wait_for_selector("#floor:not([hidden]) .hop.done")
            text = page.locator("#floor").inner_text()
            assert "now · document DOC-demo-00-003" in text and "previous · document DOC-demo-00-002" in text
            assert "doc_type → insurance_claim · p 0.89 (choice)" in text
            assert page.get_by_role("listitem", name="intake: in flight").count() == 1
            assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
            assert not errors
            browser.close()
    finally:
        session.stop()
        server.shutdown()
        server.server_close()


def test_terminal_edge_input_stays_short_and_actionable(tmp_path):
    if os.environ.get("SANDBOX_BROWSER_TESTS") != "1":
        pytest.skip("SANDBOX_BROWSER_TESTS not set")
    pw = pytest.importorskip("playwright.sync_api")
    demo = DemoRun(tmp_path)
    session = web.WatchWebSession(resolve=demo.resolve, ledger=demo.ledger,
        cap_usd=5, times_dir=demo.times_dir, serving_dir=demo.serving_dir,
        interval=0.1, follow_logs=False)
    session.refresh()
    server = ThreadingHTTPServer(("127.0.0.1", 0), web.make_handler(session))
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        with pw.sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get("SANDBOX_BROWSER_EXECUTABLE"))
            page = browser.new_page(viewport={"width": 375, "height": 812}, reduced_motion="reduce")
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/#terminal")
            page.wait_for_function("commandCatalog.length > 0")
            field = page.locator("#command-input")

            def run(line):
                page.evaluate("commandOutput.textContent = ''")
                field.fill(line)
                field.press("Enter")
                return page.locator("#command-output").inner_text().strip()

            # A blank line is a fresh prompt: no root usage dump, nothing in history.
            assert run("") == "mailroom>"
            assert run("   ") == "mailroom>"
            assert "usage:" not in run("")
            history = run("history")
            assert history == "mailroom> history"

            # Suggestions are close spellings, not any name sharing two letters.
            assert "did you mean" not in run("definitely-not-a-command")
            assert "did you mean start" in run("run strat")
            assert "did you mean doctor" in run("docter")

            # Hidden legacy tasks still parse in the CLI: point at the local command.
            out = run("eval judge --mock")
            assert "Unknown command" not in out and "sandbox eval judge --mock" in out
            assert "sandbox eval judge --help" in out

            # Long input is echoed once at the prompt, and clipped in the error.
            out = run("x" * 3000)
            assert out.count("x") < 200, len(out)
            assert "…" in out

            # A real leaf command with options names the local command to run.
            out = run("run start --config config/runs/x.yaml")
            assert "sandbox run start --config config/runs/x.yaml" in out
            assert "help run start" in out
            assert "Not a browser inspection command" not in out
            assert not errors, errors
            browser.close()
    finally:
        session.stop()
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize("width", [375, 1280])
def test_board_page_loads_clean_and_flags_a_dead_server(tmp_path, width):
    if os.environ.get("SANDBOX_BROWSER_TESTS") != "1":
        pytest.skip("SANDBOX_BROWSER_TESTS not set")
    pw = pytest.importorskip("playwright.sync_api")
    from mailroom_sandbox.tui import board

    demo = board.DemoJobs(tmp_path)
    for _ in range(5):
        demo.step()
    server = board.make_board_server("127.0.0.1", 0, root=tmp_path, interval=0.1)
    Thread(target=server.serve_forever, daemon=True).start()
    with pw.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("SANDBOX_BROWSER_EXECUTABLE"))
        page = browser.new_page(viewport={"width": width, "height": 860}, reduced_motion="reduce")
        problems = []
        page.on("pageerror", lambda error: problems.append(str(error)))
        page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
        page.goto(f"http://127.0.0.1:{server.server_port}/")
        page.wait_for_function("document.querySelectorAll('.card').length === 2")
        assert page.locator("#n").inner_text() == "2"
        assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        assert not problems, problems  # no favicon 404 or script error
        server.board_stop.set()
        server.shutdown()
        server.server_close()
        page.wait_for_selector("#err:not([hidden])", timeout=10000)
        assert "disconnected" in page.locator("#err").inner_text().lower()
        browser.close()
