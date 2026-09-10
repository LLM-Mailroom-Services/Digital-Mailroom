"""Compose file / CLI argv construction (no docker required)."""

from __future__ import annotations

import yaml

from mailroom_sandbox.compose import VALID_PROFILES, compose_argv, compose_file, default_profiles_for
from mailroom_sandbox.paths import deploy_dir


def test_compose_file_parses():
    data = yaml.safe_load(compose_file().read_text(encoding="utf-8"))
    services = data["services"]
    for name in (
        "phoenix",
        "ollama",
        "vllm",
        "llamacpp",
        "langfuse-web",
        "langfuse-worker",
        "minio",
        "redis",
        "jupyter",
    ):
        assert name in services
    assert "phoenix" in services["phoenix"]["profiles"]
    assert "ollama" in services["ollama"]["profiles"]
    assert "jupyter" in services["jupyter"]["profiles"]
    assert services["jupyter"]["build"]["dockerfile"] == "deploy/Dockerfile"
    assert services["jupyter"]["image"] == "mailroom-sandbox:offline"
    assert "langfuse" in services["langfuse-web"]["profiles"]
    assert services["langfuse-web"]["image"].endswith(":3")
    assert services["langfuse-worker"]["image"].endswith("langfuse-worker:3")
    # Default ollama has no GPU reservation (CPU-capable smoke).
    assert "deploy" not in services["ollama"]
    # Healthchecks must not pass credentials as CLI flags (secret scanners).
    raw = compose_file().read_text(encoding="utf-8")
    assert "--password" not in raw
    assert "LANGFUSE_INIT_PROJECT_PUBLIC_KEY" in raw


def test_compose_jupyter_build_and_mount_resolve_from_package_root():
    """DMR-043: jupyter build context/volume must resolve against the package
    root, not the compose file's own directory (deploy/)."""
    from pathlib import Path

    data = yaml.safe_load(compose_file().read_text(encoding="utf-8"))
    jupyter = data["services"]["jupyter"]
    ctx = jupyter["build"]["context"]
    dockerfile = jupyter["build"]["dockerfile"]
    assert ctx == "..", f"build context must be the package root, got {ctx!r}"
    # The compose file lives in deploy/; context .. is the package root
    # (deploy_dir().parent) and the dockerfile is context-relative.
    resolved = (deploy_dir().parent / dockerfile).resolve()
    assert resolved.is_file(), f"resolved dockerfile does not exist: {resolved}"
    # The workspace mount must also be the package root.
    assert "..:/workspace" in jupyter["volumes"], jupyter["volumes"]
    # Compose project name so volumes are namespaced, not 'deploy_*'.
    assert data.get("name") == "mailroom-sandbox"


def test_compose_jupyter_binds_localhost_and_user():
    """DMR-043 F11/F12: Lab must not publish to all interfaces, and the
    container should run as the host user for writable bind mounts."""
    data = yaml.safe_load(compose_file().read_text(encoding="utf-8"))
    jupyter = data["services"]["jupyter"]
    assert jupyter["ports"] == ["127.0.0.1:8888:8888"]
    assert jupyter.get("user") == "${SANDBOX_UID:-1000}:${SANDBOX_GID:-1000}"


def test_compose_vllm_has_gpu_reservation():
    """DMR-043 F3: vLLM must request an NVIDIA GPU or it boots without CUDA."""
    data = yaml.safe_load(compose_file().read_text(encoding="utf-8"))
    vllm = data["services"]["vllm"]
    deploy = vllm.get("deploy") or {}
    reservations = (deploy.get("resources") or {}).get("reservations") or {}
    devices = reservations.get("devices") or []
    assert devices, "vllm service must carry a device reservation"
    assert devices[0]["driver"] == "nvidia"
    assert devices[0]["capabilities"] == ["gpu"]


def test_compose_argv_profiles():
    cmd = compose_argv(["phoenix", "ollama"], "up", "-d")
    assert cmd[1:3] == ["compose", "-f"]
    assert str(compose_file()) in cmd
    assert cmd.count("--profile") == 2
    assert "phoenix" in cmd and "ollama" in cmd
    assert cmd[-2:] == ["up", "-d"]


def test_default_profiles_ollama():
    names = default_profiles_for("ollama")
    assert names == ["langfuse", "ollama"]
    assert set(names) <= set(VALID_PROFILES)


def test_modal_vllm_app_is_sandbox_scoped():
    text = (deploy_dir() / "modal_vllm.py").read_text(encoding="utf-8")
    assert 'APP_NAME = "sandbox-vllm"' in text
    assert "build_vllm_command" in text
    assert "MODAL_VLLM_MODEL" in text
    assert "sandbox-hf-cache" in text
