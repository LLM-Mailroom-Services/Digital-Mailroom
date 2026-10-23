"""Producer health advisory boundary; no Dojo import or release discovery."""

import copy
import subprocess
import sys

import pytest

from mailroom_ui import pipeline_ops


RELEASE_URL = "https://github.com/Exios66/llm-dojo-scoring/releases/latest"


def update(**overrides):
    payload = {
        "status": "update_available",
        "installed_version": "0.23.1",
        "latest_version": "0.24.0",
        "checked_at": 1792713600.0,
        "stale": True,
        "source": "cache",
        "error": None,
        "cache_persisted": True,
        "release_url": RELEASE_URL,
    }
    return {**payload, **overrides}


def health(advisory):
    return {"status": "ok", "checks": {"watcher": "live", "inbox_pending": 2},
            "dojo_update": advisory}


def fetch(monkeypatch, advisory):
    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://producer.invalid")
    monkeypatch.delenv("MAILROOM_PIPELINE_TOKEN", raising=False)
    monkeypatch.delenv("MAILROOM_API_TOKEN", raising=False)
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        return health(advisory)

    monkeypatch.setattr(pipeline_ops, "_get_json", get)
    result = pipeline_ops.fetch_pipeline_ops()
    assert calls == ["http://producer.invalid/v1/health"]
    assert (result["ok"], result["watcher"], result["inbox_pending"]) == (True, "live", 2)
    return result


def test_forwards_valid_health_advisory_without_mutation(monkeypatch):
    advisory = update(extra="not forwarded")
    original = copy.deepcopy(advisory)
    assert fetch(monkeypatch, advisory)["dojo_update"] == update()
    assert advisory == original


@pytest.mark.parametrize("status", ["update_available", "up_to_date", "unknown", "unavailable", "disabled"])
def test_known_statuses_preserve_health(monkeypatch, status):
    advisory = update(status=status)
    assert fetch(monkeypatch, advisory)["dojo_update"] == advisory


@pytest.mark.parametrize("version", ["0.24.0rc1", "0.24.0.dev1", "0.23.1+vendor.7"])
def test_loaded_engine_version_may_be_prerelease_or_vendor(monkeypatch, version):
    assert fetch(monkeypatch, update(installed_version=version))["dojo_update"]["installed_version"] == version


def test_latest_stable_post_release_is_supported(monkeypatch):
    assert fetch(monkeypatch, update(latest_version="0.23.1.post1"))["dojo_update"]["latest_version"] == "0.23.1.post1"


def test_display_imports_do_not_load_dojo_or_live_pipeline():
    result = subprocess.run([
        sys.executable, "-c",
        "import sys; import mailroom_ui.pipeline_ops; import tui.views; "
        "assert not any(n == 'api.main' or n.startswith('llm_dojo_scoring') for n in sys.modules)",
    ], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_pipeline_engine_version_is_forwarded_instead_of_local_eval_identity(monkeypatch):
    assert fetch(monkeypatch, update(installed_version="0.19.7"))["dojo_update"]["installed_version"] == "0.19.7"


@pytest.mark.parametrize("status", ["unknown", "unavailable", "disabled"])
def test_no_release_knowledge_is_valid_non_advisory(monkeypatch, status):
    advisory = update(status=status, latest_version=None, checked_at=None, source="none")
    assert fetch(monkeypatch, advisory)["dojo_update"] == advisory


@pytest.mark.parametrize("advisory", [
    None, [], "update_available", {},
    update(status="upgrade_now"), update(status=[]),
    update(installed_version=None), update(installed_version=24),
    update(installed_version="<script>window.__dojoInjected=1</script>"),
    update(installed_version="0.23.1\n"), update(installed_version="1." * 1000),
    update(latest_version="0.24.0\u2028"), update(latest_version="0.24.0rc1"),
    update(latest_version="javascript:alert(1)"), update(latest_version=None),
    update(checked_at=None), update(checked_at=True), update(checked_at=float("nan")),
    update(checked_at=float("inf")), update(checked_at=-1), update(checked_at=10**100),
    update(stale="false"), update(source="<img src=x onerror=alert(1)>"),
    update(source=[]), update(error="<script>alert(1)</script>"),
    update(cache_persisted=1), update(release_url="javascript:alert(1)"),
    update(release_url="https://evil.invalid/releases/latest"),
    {key: value for key, value in update().items() if key != "stale"},
])
def test_malformed_advisory_is_dropped_without_affecting_health(monkeypatch, advisory):
    assert "dojo_update" not in fetch(monkeypatch, advisory)


def test_missing_and_disconnected_producer_cannot_retain_advisory(monkeypatch):
    monkeypatch.setenv("MAILROOM_PIPELINE_URL", "http://producer.invalid")
    monkeypatch.delenv("MAILROOM_PIPELINE_TOKEN", raising=False)
    monkeypatch.delenv("MAILROOM_API_TOKEN", raising=False)
    monkeypatch.setattr(pipeline_ops, "_get_json", lambda *a, **kw: health(update()))
    assert "dojo_update" in pipeline_ops.fetch_pipeline_ops()
    monkeypatch.setattr(pipeline_ops, "_get_json", lambda *a, **kw: {"status": "ok", "checks": {"watcher": "live"}})
    assert "dojo_update" not in pipeline_ops.fetch_pipeline_ops()

    def offline(*a, **kw):
        raise OSError("fixture producer disconnected")

    monkeypatch.setattr(pipeline_ops, "_get_json", offline)
    ops = pipeline_ops.fetch_pipeline_ops()
    assert ops["ok"] is False
    assert ops["error"] == "fixture producer disconnected"
    assert "dojo_update" not in ops


def test_http_and_websocket_keep_validated_advisory(monkeypatch):
    from fastapi.testclient import TestClient
    from mailroom_ui.langfuse_source import LangfuseSource
    from server.main import create_app
    from server.poller import PollHub
    from tests.fake_langfuse import FakeClient

    expected = update()
    ops = fetch(monkeypatch, expected)
    src = LangfuseSource(client=FakeClient([]))  # no fabricated trace rows
    hub = PollHub(src, interval=1, window=60, limit=10)
    hub.pipeline_ops = ops
    assert hub._snapshot_message(stale=False)["pipeline"]["dojo_update"] == expected
    with TestClient(create_app(src)) as client:
        assert client.get("/api/pipeline").json()["dojo_update"] == expected
        with client.websocket_connect("/ws") as ws:
            for _ in range(4):
                message = ws.receive_json()
                if message.get("pipeline", {}).get("dojo_update"):
                    assert message["pipeline"]["dojo_update"] == expected
                    break
            else:
                pytest.fail("no validated producer advisory in WS snapshots")


def test_tui_uses_pipeline_versions_as_plain_text():
    from rich.console import Console
    from tui.views import status_header

    console = Console(record=True, width=180, color_system=None)
    ops = {"configured": True, "dojo_update": update()}
    console.print(status_header(True, 0, "fixture", ops))
    rendered = console.export_text()
    assert "Dojo update available for pipeline: installed 0.23.1; available 0.24.0" in rendered
    assert "stale; recheck needed" in rendered
    assert RELEASE_URL in rendered
    console.print(status_header(False, 0, "fixture", ops))
    assert "Dojo update available" not in console.export_text()
    for advisory in [None, update(status="up_to_date"), update(installed_version="[link=evil]bad[/link]")]:
        console.print(status_header(True, 0, "fixture", {"configured": True, "dojo_update": advisory}))
        assert "Dojo update available" not in console.export_text()
