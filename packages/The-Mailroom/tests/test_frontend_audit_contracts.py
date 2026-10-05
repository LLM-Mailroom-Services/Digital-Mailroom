"""Static contracts for frontend bugs fixed in the 0.5.0 audit.

No JS harness (AGENTS.md): these pin the fixed source shapes so the bugs —
all of which failed silently in the browser — can't quietly return.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_pixel_ws_url_has_scheme_separator():
    # `${proto}//host` produced "wss//host/ws" for every ?api= deploy.
    src = _read("web/js/api.js")
    assert "${proto}//" not in src
    assert "${proto}://${u.host}/ws" in src


def test_top_level_const_globals_are_exported_to_window():
    # `const X = …` at top level is not a window property.
    assert "window.ObservatoryDebug = ObservatoryDebug" in _read("hosted/js/debug.js")
    assert "window.MAILROOM_DATA = MAILROOM_DATA" in _read("terminal/js/data.js")


def test_retired_compliance_filing_not_offered_in_fallback_class_lists():
    for rel in ("web/js/api.js", "hosted/js/app.js"):
        assert "compliance_filing" not in _read(rel), rel


def test_terminal_escape_covers_quotes_and_links_are_scheme_checked():
    src = _read("terminal/js/terminal.js")
    esc = re.search(r"function escapeHtml\(s\) \{(.*?)\n\}", src, re.S).group(1)
    assert "&quot;" in esc and "&#39;" in esc
    assert "safeHref(" in src
    # Detail snapshot paths follow export_snapshot._safe_id, not encodeURIComponent.
    assert "'runs/' + safeId(run.trace_id)" in src


def test_pages_root_is_a_redirect_not_a_broken_terminal_copy():
    sh = _read("scripts/publish_pages.sh")
    assert "cp terminal/index.html site/index.html" not in sh
    assert 'url=terminal/' in sh
    # --skip-export must not blank the live data.
    assert "KEEP_REMOTE_DATA" in sh
    # The snapshot check result is no longer swallowed.
    assert "--check --out site/data 2>/dev/null ||" not in sh


def test_pixel_snapshot_root_resolves_from_pixel_dir():
    src = _read("web/js/api.js")
    assert "SNAP_ROOT" in src and "/pixel/" in src


def test_observatory_review_forms_do_not_open_inspector():
    src = _read("hosted/js/app.js")
    body = re.search(r"function bindCards\(root\) \{(.*?)\n  \}", src, re.S).group(1)
    assert 'closest("form")' in body or "form, form *" in body


def test_both_uis_go_live_after_a_failed_first_health_probe():
    assert "startLive()" in _read("web/js/main.js")
    assert "liveStarted" in _read("hosted/js/app.js")


def test_inspector_verdict_class_is_whitelisted():
    src = _read("web/js/inspector.js")
    assert '["CORRECT", "PARTIAL", "MISS"].includes(token)' in src
