"""Operator-desk Docker contract (mailroom-issues#117 / #118).

No Docker daemon in CI, so these pin the files' shape: one bin watcher, one
published front door, fail-fast secrets, a baked /desk, and a hosted root
Dockerfile that never grows a Node stage.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = ROOT / "operator_desk" / "docker-compose.yml"
OPERATOR_DOCKERFILE = ROOT / "operator_desk" / "Dockerfile"
NGINX = ROOT / "operator_desk" / "nginx" / "nginx.conf"


def _compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def _env(service: dict) -> dict[str, str]:
    out = {}
    for item in service.get("environment", []):
        key, _, value = item.partition("=")
        out[key] = value
    return out


def test_single_bin_watcher_in_process():
    services = _compose()["services"]
    assert set(services) == {"mailroom", "nginx"}, "no observer or ui sidecar"
    env = _env(services["mailroom"])
    assert env["MAILROOM_OBSERVER"] == "${MAILROOM_OBSERVER:-1}"
    for svc in services.values():
        assert "operator_desk.observer" not in str(svc.get("command", ""))


def test_secrets_fail_fast_and_ingest_token_optional():
    env = _env(_compose()["services"]["mailroom"])
    for key in ("MAILROOM_OPERATOR_JWT_SECRET", "MAILROOM_OPERATOR_ADMIN_PASSWORD"):
        assert env[key].startswith("${%s:?" % key), key
    assert env["MAILROOM_OPERATOR_INGEST_TOKEN"] == "${MAILROOM_OPERATOR_INGEST_TOKEN:-}"
    assert not any("changeme" in value for value in env.values())


def test_nginx_is_the_only_front_door():
    services = _compose()["services"]
    assert "ports" not in services["mailroom"]
    assert services["nginx"]["ports"] == ["${MAILROOM_HTTP_PORT:-80}:80"]
    assert services["nginx"]["depends_on"]["mailroom"]["condition"] == "service_healthy"


def test_visualizer_builds_the_operator_image():
    build = _compose()["services"]["mailroom"]["build"]
    assert build == {"context": "..", "dockerfile": "operator_desk/Dockerfile"}
    text = OPERATOR_DOCKERFILE.read_text(encoding="utf-8")
    assert '".[operator]"' in text
    assert "FROM node:22-alpine AS ui-builder" in text
    assert text.count("AS ui-builder") == 1
    assert "COPY --from=ui-builder --chown=mailroom:mailroom /ui/dist ./ui/dist" in text
    # devDependencies (vite) must be installed: NODE_ENV only on the build.
    assert "npm ci" in text and "NODE_ENV=production npm run build" in text
    assert "ENV NODE_ENV" not in text
    assert "USER mailroom" in text
    assert text.rstrip().endswith('CMD ["python", "-m", "server.main"]')


def test_hosted_root_dockerfile_has_no_node_or_ui():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "node:" not in text and "ui/" not in text
    stages = re.findall(r"^FROM\s+\S+(?:\s+AS\s+(\S+))?", text, re.M)
    assert stages[-1] == "runtime"
    assert 'CMD ["python", "-m", "server.hosted"]' in text


def test_nginx_proxies_every_surface_without_try_files():
    conf = re.sub(r"#[^\n]*", "", NGINX.read_text(encoding="utf-8"))
    assert "try_files" not in conf
    for loc in ("/api/", "/v1/", "/ws", "/desk", "/"):
        assert re.search(r"location\s+%s\s*\{" % re.escape(loc), conf), loc
    # Browser Host (with port) reaches the same-origin write guard.
    assert "proxy_set_header Host              $http_host;" in conf
    ws = conf.split("location /ws", 1)[1].split("}", 1)[0]
    assert "X-Real-IP" in ws and "$http_host" in ws and "Upgrade" in ws


def test_root_dockerignore_keeps_node_artifacts_out():
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").split()
    assert "ui/node_modules" in lines and "ui/dist" in lines
