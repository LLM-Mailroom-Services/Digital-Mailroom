"""Pins for the operator-desk single-front-door compose (DMR-076).

These are file-read tests (no docker daemon, no network): they pin the
compose and nginx invariants that the operator-desk hardening must not
regress — fail-fast secrets, nginx :80 as the only published port, no
mailroom-ui sidecar, and no try_files inside a proxy_pass location.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

COMPOSE = ROOT / "operator_desk" / "docker-compose.yml"
NGINX = ROOT / "operator_desk" / "nginx" / "nginx.conf"

# The secrets that MUST be fail-fast (${VAR:?}) and MUST NOT carry a
# `:-` dev default in the compose environment block.
REQUIRED_FAIL_FAST = (
    "MAILROOM_OPERATOR_JWT_SECRET",
    "MAILROOM_OPERATOR_ADMIN_PASSWORD",
)


def _compose():
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def test_compose_fail_fast_and_single_front_door():
    cfg = _compose()
    # mailroom-ui sidecar is gone; nginx is the only service with ports.
    assert set(cfg["services"]) == {"mailroom", "mailroom-observer", "nginx"}
    services_with_ports = [
        name for name, svc in cfg["services"].items() if "ports" in svc
    ]
    assert services_with_ports == ["nginx"]
    # mailroom itself publishes nothing.
    assert "ports" not in cfg["services"]["mailroom"]

    # The visualizer builds the full `operator` target (baked ui/dist →
    # /desk); the headless observer builds the lean `operator-core` target
    # (no Node stage, no ui/dist). Both install the extras via the arg.
    for name, target in (("mailroom", "operator"), ("mailroom-observer", "operator-core")):
        build = cfg["services"][name]["build"]
        assert build["target"] == target
        assert build.get("args", {}).get("MAILROOM_EXTRAS") == "operator"

    # nginx + observer wait for a healthy backend (nginx resolves the
    # `mailroom` upstream at boot; the operator SQLite needs /data writable).
    for name in ("mailroom-observer", "nginx"):
        deps = cfg["services"][name]["depends_on"]
        assert deps["mailroom"]["condition"] == "service_healthy"

    # The required secrets are fail-fast and carry no `:-` dev default.
    env = cfg["services"]["mailroom"]["environment"]
    for var in REQUIRED_FAIL_FAST:
        line = next(ln for ln in env if ln.startswith(f"{var}="))
        assert ":?" in line, f"{var} must be fail-fast (${var}:? )"
        assert ":-" not in line, f"{var} must not carry a dev default"


def test_nginx_proxy_locations_have_no_try_files():
    conf = NGINX.read_text(encoding="utf-8")
    # Every proxied location prefix from the card is present.
    for prefix in ("/api/", "/v1/", "/ws", "/ws/pipeline", "/"):
        assert f"location {prefix}" in conf

    # No try_files DIRECTIVE inside any location block that proxies
    # (comments explaining the removal are fine).
    blocks = conf.split("location ")
    for block in blocks[1:]:
        if "proxy_pass" not in block:
            continue
        directives = [
            line.strip()
            for line in block.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert not any(line.startswith("try_files") for line in directives), (
            "try_files must not appear inside a proxy_pass location "
            "(nginx has no local SPA root; the mailroom container owns "
            "the fallback)"
        )
