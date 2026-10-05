"""Optional React desk (`ui/`) is a dependency branch — never required to boot."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from mailroom_ui.langfuse_source import LangfuseSource
from operator_desk.mount import react_ui_available
from server.main import create_app
from tests.fake_langfuse import FakeClient, make_trace

ROOT = Path(__file__).resolve().parent.parent
PKG = (ROOT / "ui" / "package.json").read_text(encoding="utf-8")
VITE = (ROOT / "ui" / "vite.config.ts").read_text(encoding="utf-8")
CLIENT = (ROOT / "ui" / "src" / "api" / "client.ts").read_text(encoding="utf-8")
DOCS = (ROOT / "ui" / "src" / "api" / "documents.ts").read_text(encoding="utf-8")
REVIEW = (ROOT / "ui" / "src" / "api" / "review.ts").read_text(encoding="utf-8")
WS = (ROOT / "ui" / "src" / "api" / "websocket.ts").read_text(encoding="utf-8")


def test_optional_package_points_at_this_visualizer():
    assert '"name": "the-mailroom-ui"' in PKG
    assert "127.0.0.1:8001" in VITE
    assert "localhost:8000" not in VITE
    assert "/api/traces" in DOCS
    assert "/api/review/resolve" in REVIEW
    assert "/api/review-queue" in REVIEW
    assert "/ws/pipeline" in WS
    assert "url.includes('/v1/')" in CLIENT
    assert "default pip install never needs this package" in PKG


def test_pixel_console_is_still_vanilla():
    web = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "react" not in web.lower()
    assert "vite" not in web.lower()


def test_default_app_does_not_require_a_react_build():
    src = LangfuseSource(client=FakeClient([make_trace("t-ui")]))
    with TestClient(create_app(src)) as client:
        health = client.get("/api/health").json()
        assert health["operator"]["react_ui"] is react_ui_available()
        meta = client.get("/api/meta").json()
        assert any(e["path"] == "/desk" for e in meta["endpoints"])
        root = client.get("/")
        assert root.status_code == 200
        assert "THE MAILROOM" in root.text


def test_desk_mounts_when_dist_exists(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>operator react desk</body></html>", encoding="utf-8")
    monkeypatch.setenv("MAILROOM_UI_DIST", str(dist))
    src = LangfuseSource(client=FakeClient([make_trace("t-desk")]))
    with TestClient(create_app(src)) as client:
        assert client.get("/api/health").json()["operator"]["react_ui"] is True
        page = client.get("/desk")
        assert page.status_code == 200
        assert "operator react desk" in page.text
        spa = client.get("/desk/login")
        assert spa.status_code == 200
        assert "operator react desk" in spa.text
