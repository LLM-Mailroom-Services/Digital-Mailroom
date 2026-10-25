"""Tray-TUI screenshot gallery guard: docs images stay generated and in sync.

Covers ``docs/pretty-logging/mailroom-watch-web.md`` + ``docs/assets/watch/`` +
``scripts/sand032/capture_watch_screenshots.py``. Network-free, no LLM.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "docs" / "assets" / "watch"
DOC = REPO / "docs" / "pretty-logging" / "mailroom-watch-web.md"
SCRIPT = REPO / "scripts" / "sand032" / "capture_watch_screenshots.py"

IMG_RE = re.compile(r"!\[([^\]]*)\]\((\.\./assets/watch/[^)]+)\)")


def _manifest() -> dict:
    return json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))


def test_capture_script_exists():
    assert SCRIPT.is_file()


def test_manifest_cases_all_have_assets():
    manifest = _manifest()
    names = [c["name"] for c in manifest["cases"]]
    assert len(names) >= 15  # every lifecycle phase + aesthetics + board + session + web
    assert len(set(names)) == len(names)
    kinds = {c["kind"] for c in manifest["cases"]}
    assert {"watch", "board", "session", "web-theme"} <= kinds
    for case in manifest["cases"]:
        svg = ASSETS / f"{case['name']}.svg"
        txt = ASSETS / f"{case['name']}.ansi.txt"
        assert svg.is_file(), svg.name
        assert txt.is_file(), txt.name
        body = svg.read_text(encoding="utf-8")
        assert "<svg" in body and "\x1b" not in body
        assert txt.read_text(encoding="utf-8").strip()


def test_every_doc_image_resolves_and_every_case_is_shown():
    refs = IMG_RE.findall(DOC.read_text(encoding="utf-8"))
    assert refs, "gallery must embed screenshots"
    for alt, rel in refs:
        assert alt.strip(), f"missing alt text: {rel}"
        assert (DOC.parent / rel).is_file(), rel
    shown = {Path(rel).name for _, rel in refs}
    manifest = _manifest()
    for case in manifest["cases"]:
        assert f"{case['name']}.svg" in shown, case["name"]


def test_gallery_covers_states_and_aesthetics():
    text = DOC.read_text(encoding="utf-8")
    for needle in (
        "SORTING",
        "QUEUED",
        "DEPLOYING",
        "PREFLIGHT",
        "COLD BOOT",
        "container starting",
        "capturing CUDA graphs",
        "engine ready",
        "TEARDOWN",
        "STOPPED",
        "Program route",
        "over-gate",
        "Blink frame",
        "Dispatch log",
        "wide vs narrow",
        "Job board",
        "Session CLI",
        "Browser UI theme",
        "capture_watch_screenshots",
    ):
        assert needle in text, needle


def test_capture_script_check_passes():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(ASSETS), "--check"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
