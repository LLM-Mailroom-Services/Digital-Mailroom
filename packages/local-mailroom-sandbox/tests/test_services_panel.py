"""The services snapshot (`mailroom.services/v1`) and its board rendering.

`sandbox doctor --publish` writes ``services.json`` under the beacon root; the board reads it
(no network, no probing) and shows a status strip in the browser and the terminal. A snapshot
that stops being refreshed is marked stale rather than shown as current.
"""

from __future__ import annotations

import json
import time
from http.client import HTTPConnection
from threading import Thread

import pytest

from mailroom_sandbox.tui import board as bd
from mailroom_sandbox.tui.beacon import Beacon
from mailroom_sandbox.tui.services_snapshot import (
    SERVICES_VERSION,
    publish_services,
    read_services,
)

ROWS = [
    {"name": "modal", "state": "ok", "detail": "modal 1.6.2", "hint": ""},
    {"name": "provider", "state": "fail", "detail": "VLLM_BASE_URL unset", "hint": "sandbox modal deploy"},
    {"name": "phoenix", "state": "skipped", "detail": "optional sidecar", "hint": ""},
]


def test_publish_then_read_round_trips(tmp_path):
    publish_services(ROWS, root=tmp_path, profile="modal-vllm", live=False)
    snap = read_services(tmp_path)
    assert snap["schema"] == SERVICES_VERSION
    assert snap["profile"] == "modal-vllm" and snap["live"] is False
    assert [r["name"] for r in snap["services"]] == ["modal", "provider", "phoenix"]
    assert snap["stale"] is False and snap["age_s"] < 5


def test_publish_is_atomic_and_leaves_no_temp_files(tmp_path):
    publish_services(ROWS, root=tmp_path, profile="p", live=False)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["services.json"]


def test_read_is_none_for_a_missing_foreign_or_corrupt_file(tmp_path):
    assert read_services(tmp_path) is None
    (tmp_path / "services.json").write_text("{not json", encoding="utf-8")
    assert read_services(tmp_path) is None
    (tmp_path / "services.json").write_text(json.dumps({"schema": "other/v9", "services": []}), encoding="utf-8")
    assert read_services(tmp_path) is None


def test_an_old_snapshot_is_marked_stale(tmp_path):
    publish_services(ROWS, root=tmp_path, profile="p", live=False)
    path = tmp_path / "services.json"
    data = json.loads(path.read_text())
    data["generated_at"] -= 3600
    path.write_text(json.dumps(data))
    snap = read_services(tmp_path, stale_s=600)
    assert snap["stale"] is True and snap["age_s"] >= 3600


def test_the_snapshot_is_not_listed_as_a_job(tmp_path):
    publish_services(ROWS, root=tmp_path, profile="p", live=False)
    Beacon("real-job", package="p", root=tmp_path)
    assert [j["job_id"] for j in bd.list_jobs(tmp_path)] == ["real-job"]


@pytest.mark.parametrize("fields", [
    {"generated_at": "invalid"}, {"generated_at": []}, {"generated_at": None},
    {"generated_at": float("nan")}, {"generated_at": float("inf")},
    {"services": [None]}, {"services": ["invalid"]}, {"services": [{"state": []}]},
])
def test_malformed_snapshots_are_unreadable(tmp_path, fields):
    publish_services(ROWS, root=tmp_path, profile="p", live=False)
    path = tmp_path / "services.json"
    data = json.loads(path.read_text())
    data.update(fields)
    path.write_text(json.dumps(data))
    assert read_services(tmp_path) is None


def test_service_attribute_text_is_escaped(server, tmp_path):
    publish_services([{"name": "provider", "state": "fail", "detail": 'bad" onmouseover="alert(1)', "hint": ""}], root=tmp_path, profile="p", live=False)
    page = _get(server, "/")[1].decode()
    assert '.replace(/"/g,"&quot;")' in page
    assert "esc(r.detail)" in page and "esc(r.hint)" in page and "esc(r.state)" in page


def test_board_payload_carries_the_services(tmp_path):
    publish_services(ROWS, root=tmp_path, profile="modal-vllm", live=True)
    payload = bd.board_payload(tmp_path, 120.0, {})
    assert payload["services"]["live"] is True
    assert payload["services"]["services"][1]["name"] == "provider"


def test_board_payload_has_no_services_before_any_doctor_run(tmp_path):
    assert bd.board_payload(tmp_path, 120.0, {})["services"] is None


def test_terminal_board_shows_the_services_and_their_hints(tmp_path):
    publish_services(ROWS, root=tmp_path, profile="modal-vllm", live=False)
    text = bd.render_board([], width=100, on=False, services=read_services(tmp_path))
    assert "SERVICES" in text
    assert "modal" in text and "provider" in text and "FAIL" in text
    assert "sandbox modal deploy" in text  # the hint for the failing row


def test_terminal_board_marks_a_stale_snapshot(tmp_path):
    publish_services(ROWS, root=tmp_path, profile="p", live=False)
    snap = read_services(tmp_path)
    snap["stale"], snap["age_s"] = True, 4000.0
    assert "stale" in bd.render_board([], width=100, on=False, services=snap).lower()


def test_terminal_board_without_a_snapshot_points_at_doctor(tmp_path):
    text = bd.render_board([], width=100, on=False, services=None)
    assert "sandbox doctor --publish" in text


def test_run_board_tui_once_includes_the_services_box(tmp_path, capsys):
    publish_services(ROWS, root=tmp_path, profile="modal-vllm", live=False)
    assert bd.run_board_tui(root=tmp_path, stale_s=120, interval=0.1, once=True) == 0
    assert "SERVICES" in capsys.readouterr().out


@pytest.fixture
def server(tmp_path):
    httpd = bd.make_board_server("127.0.0.1", 0, root=tmp_path, interval=0.1)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd.server_address[1]
    httpd.board_stop.set()
    httpd.shutdown()
    httpd.server_close()


def _get(port, path):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    resp = conn.getresponse()
    return resp.status, resp.read()


def test_api_services_serves_the_snapshot(server, tmp_path):
    publish_services(ROWS, root=tmp_path, profile="modal-vllm", live=False)
    status, body = _get(server, "/api/services")
    assert status == 200
    assert json.loads(body)["services"][0]["name"] == "modal"


def test_api_services_is_null_when_unpublished(server):
    status, body = _get(server, "/api/services")
    assert status == 200 and json.loads(body) is None


def test_the_page_has_a_services_strip(server):
    status, body = _get(server, "/")
    assert status == 200
    assert b'id="svc"' in body and b"d.services" in body
    # a failing service must not look like a warning: it gets its own glyph, not just the gold dot
    assert ".svc .s.fail::before" in body.decode() and "✖" in body.decode()


def test_the_board_stays_network_free(server, tmp_path, monkeypatch):
    """Rendering the strip must never probe anything: it only reads the published file."""
    import httpx

    def boom(*a, **k):
        raise AssertionError("the board must not make network calls")

    monkeypatch.setattr(httpx, "get", boom)
    publish_services(ROWS, root=tmp_path, profile="p", live=False)
    assert _get(server, "/api/services")[0] == 200
    assert _get(server, "/api/jobs")[0] == 200
    time.sleep(0.05)
