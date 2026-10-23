"""Contracts for the terminal GH Pages site (terminal/) + corpus catalog.

There is no JS test harness (see AGENTS.md). These source-level assertions
lock the owlcot-style interaction details and the data contracts so they
cannot silently regress: TTY emulation, ghost-text completion, 1.06s blink
cursor, opt-in keypress sound, CRT toggle, animated man pages, the virtual
filesystem (ls/cat/cd/whoami/mail), the live Hub corpus fetches, and the
publish pipeline that stages the site with the slim corpus catalog.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "terminal" / "index.html").read_text()
CSS = (ROOT / "terminal" / "css" / "terminal.css").read_text()
JS = (ROOT / "terminal" / "js" / "terminal.js").read_text()
DATA = (ROOT / "terminal" / "js" / "data.js").read_text()
PUBLISH = (ROOT / "scripts" / "publish_pages.sh").read_text()

REPO_URLS = re.findall(r"url: 'https://github\.com/Exios66/([^']+)'", DATA)


def test_site_files_exist():
    for path in ("terminal/index.html", "terminal/css/terminal.css",
                 "terminal/js/terminal.js", "terminal/js/data.js"):
        assert (ROOT / path).is_file(), path


def test_index_references_assets():
    # Cache-bust follows pyproject.toml (scripts/release.py rewrites it).
    import re

    ver = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M).group(1)
    assert f'href="css/terminal.css?v={ver}"' in INDEX
    assert f'src="js/data.js?v={ver}"' in INDEX
    assert f'src="js/terminal.js?v={ver}"' in INDEX
    assert 'id="cmdInput"' in INDEX
    assert 'id="ghostText"' in INDEX
    assert 'id="blockCursor"' in INDEX
    assert 'id="crtOverlay"' in INDEX
    assert "noscript" in INDEX


def test_manifest_covers_every_synced_package():
    """The site's repos manifest must cover every package the monorepo
    mirrors upstream (mailroom-dev's packages/) plus the hub/derived repos."""
    sync_path = ROOT.parents[1] / "scripts" / "packages_sync.json"
    if not sync_path.is_file():
        pytest.skip("packages_sync.json lives in the Digital-Mailroom monorepo only")
    sync = json.loads(sync_path.read_text())
    synced = {k.lower() for k in sync["packages"].keys()}
    names = {n.lower() for n in REPO_URLS}
    assert not (synced - names), f"data.js missing synced packages: {sorted(synced - names)}"
    for expected in ("mailroom-dev", "mailroom-hub", "llm-postal",
                     "mailroom-dev-graph", "llm-entity-extraction-graph",
                     "llm-mailroom-graph", "mailroom-corpus-eda"):
        assert expected in names


def test_manifest_urls_unique_and_consistent():
    assert len(REPO_URLS) == len(set(REPO_URLS))
    assert len(REPO_URLS) >= 15


def test_data_payloads_present():
    assert "MAILROOM_DATA" in DATA
    assert "banner" in DATA and "motd" in DATA and "lore" in DATA
    assert "about" in DATA and "plan" in DATA and "contact" in DATA
    assert "help" in DATA and "manPages" in DATA
    assert "corpus" in DATA and "repos" in DATA


# --- owlcot-style interaction contracts -------------------------------------

def test_cursor_blinks_at_106s_crt_accurate():
    assert "animation: blink 1.06s steps(2, end) infinite" in CSS
    assert "@keyframes blink" in CSS


def test_ghost_text_completion_flicker():
    assert ".ghost-text" in CSS
    assert "ghostFlicker" in CSS
    assert "updateGhost" in JS
    assert "ghostText" in JS
    assert "acceptCompletion" in JS
    assert "Tab" in JS and "key === 'Tab'" in JS


def test_keypress_sound_opt_in():
    assert "playClick" in JS and "playBell" in JS
    assert "state.sound" in JS
    assert "COMMANDS.sound" in JS
    assert "'sound: on|off'" in JS or "sound: on|off" in JS
    assert "AudioContext" in JS


def test_man_page_animated_scroll():
    assert "printManPage" in JS
    assert "typeOutText" in JS
    assert "man-page" in CSS
    assert "COMMANDS.help" in JS


def test_crt_overlay_toggle():
    assert "COMMANDS.crt" in JS
    assert "crtOverlay" in JS
    assert ".crt-overlay.off" in CSS
    assert "scanlines" in CSS and "vignette" in CSS and "flicker" in CSS


def test_history_and_clear():
    assert "navigateHistory" in JS
    assert "state.history" in JS
    assert "ArrowUp" in JS and "ArrowDown" in JS
    assert "clearScreen" in JS
    assert "Ctrl+L" in JS or "ctrlKey" in JS


def test_virtual_filesystem_commands():
    for cmd in ("ls", "cat", "cd", "pwd", "tree", "whoami", "mail"):
        assert f"COMMANDS.{cmd}" in JS, cmd
    assert "mailto:" in JS
    assert "startCompose" in JS and "finishCompose" in JS


def test_trace_commands_read_snapshots():
    for cmd in ("floor", "inspect", "review", "metrics", "sessions"):
        assert f"COMMANDS.{cmd}" in JS, cmd
    assert "traces.json" in JS
    assert "metrics.json" in JS and "review-queue.json" in JS and "sessions.json" in JS
    assert "runs/" in JS


def test_corpus_commands_live_hub_fetch():
    assert "COMMANDS.corpus" in JS
    assert "sub === 'ls'" in JS and "sub === 'show'" in JS
    assert "sub === 'search'" in JS and "sub === 'stats'" in JS
    assert "datasets-server.huggingface.co" in JS
    assert "hfRowUrl" in JS
    assert "corpus.json" in JS
    assert "corpus show" in JS
    assert "hub unreachable" in JS


def test_repos_commands():
    assert "COMMANDS.repos" in JS
    assert "COMMANDS.open" in JS
    assert "COMMANDS.search" in JS
    assert "COMMANDS.neofetch" in JS


def test_settings_commands():
    for cmd in ("theme", "crt", "sound", "skyline"):
        assert f"COMMANDS.{cmd}" in JS, cmd
    assert "localStorage" in JS and "mailroomTerminalPrefs" in JS


def test_status_bar_links():
    assert "pixel" in INDEX and "observatory" in INDEX and "hub" in INDEX


# --- publish pipeline --------------------------------------------------------

def test_publish_stages_terminal_site():
    assert "terminal" in PUBLISH
    assert "docs/terminal" in PUBLISH
    assert "export_corpus_catalog" in PUBLISH
    assert "corpus.json" in PUBLISH


# --- corpus catalog export ---------------------------------------------------

def _fake_fetch(rows_by_split):
    def fake(**kw):
        split = kw["split"]
        rows = rows_by_split.get(split, [])
        if kw["config"] == "ground_truth":
            return [{"filename": r["filename"], "expected": "contract",
                     "expected_subclass": "license",
                     "content_sha256": "ab" * 32} for r in rows]
        return [{"filename": r["filename"], "doc_text": "body text",
                 "metadata": {"source": "test"}} for r in rows]
    return fake


def test_catalog_build_slim_fields(monkeypatch, tmp_path):
    import scripts.export_corpus_catalog as ecc
    monkeypatch.setattr(
        ecc.hf_corpus, "fetch_rows",
        _fake_fetch({"train": [{"filename": "a.htm"}], "test": []}))
    catalog = ecc.build_catalog(max_rows=10)
    rows = catalog["rows"]
    assert len(rows) == 1
    assert rows[0]["filename"] == "a.htm"
    assert rows[0]["doc_class"] == "contract"
    assert rows[0]["doc_subclass"] == "license"
    assert rows[0]["sha256"] == "ab" * 32
    assert rows[0]["index"] == 0 and rows[0]["gt_index"] == 0
    assert rows[0]["chars"] == len("body text")
    assert catalog["meta"]["splits"] == {"train": 1, "test": 0}


def test_catalog_check_roundtrip(monkeypatch, tmp_path):
    import scripts.export_corpus_catalog as ecc
    monkeypatch.setattr(
        ecc.hf_corpus, "fetch_rows",
        _fake_fetch({"train": [{"filename": "a.htm"}], "test": [{"filename": "b.htm"}]}))
    catalog = ecc.build_catalog(max_rows=10)
    target = tmp_path / "corpus.json"
    target.write_text(json.dumps(catalog))
    assert ecc.check_catalog(target) == 0
    monkeypatch.setattr(ecc.hf_corpus, "corpus_revision", lambda: "abc123")
    catalog["meta"]["revision"] = "abc123"


def test_catalog_check_refuses_empty(monkeypatch, tmp_path):
    import scripts.export_corpus_catalog as ecc
    target = tmp_path / "corpus.json"
    target.write_text(json.dumps({"meta": {}, "rows": []}))
    assert ecc.check_catalog(target) == 1
    target.write_text("{not json")
    assert ecc.check_catalog(target) == 1


def test_catalog_check_requires_sha_and_gt(monkeypatch, tmp_path):
    import scripts.export_corpus_catalog as ecc
    bad = {"meta": {"splits": {"train": 1}}, "rows": [
        {"filename": "a.htm", "split": "train", "index": 0, "gt_index": -1,
         "doc_class": None, "sha256": None}]}
    target = tmp_path / "corpus.json"
    target.write_text(json.dumps(bad))
    assert ecc.check_catalog(target) == 1