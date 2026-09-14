"""Docker Compose helpers for the sandbox stack."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from mailroom_sandbox.overlay import load_profile
from mailroom_sandbox.paths import deploy_dir, repo_root

_log = logging.getLogger("mailroom_sandbox.compose")

COMPOSE_FILE = "docker-compose.yml"
VALID_PROFILES = ("phoenix", "ollama", "vllm", "llamacpp", "langfuse", "jupyter")


def compose_file() -> Path:
    return deploy_dir() / COMPOSE_FILE


def _docker() -> str:
    docker = shutil.which("docker")
    if not docker:
        raise FileNotFoundError("docker is not on PATH")
    return docker


def compose_argv(profiles: list[str], *args: str, docker_bin: str = "docker") -> list[str]:
    cmd = [docker_bin, "compose", "-f", str(compose_file())]
    for name in profiles:
        if name not in VALID_PROFILES:
            raise ValueError(f"Unknown compose profile {name!r}. Valid: {VALID_PROFILES}")
        cmd.extend(["--profile", name])
    cmd.extend(args)
    return cmd


def default_profiles_for(sandbox_profile: str) -> list[str]:
    cfg = load_profile(sandbox_profile)
    names = list(cfg.get("compose_profiles") or ["langfuse"])
    return [n for n in names if n in VALID_PROFILES]


def run_compose(profiles: list[str], *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.setdefault("HF_HOME", str(repo_root() / "data" / "cache" / "hf"))
    return subprocess.run(
        compose_argv(profiles, *args, docker_bin=_docker()),
        check=check,
        cwd=repo_root(),
        env=env,
    )


def pull_ollama_models(models: list[str]) -> int:
    """Pull models into the mailroom-ollama container (or host ollama)."""
    if not models:
        return 0
    docker = shutil.which("docker")
    if docker:
        inspect = subprocess.run(
            [docker, "inspect", "-f", "{{.State.Running}}", "sandbox-ollama"],
            capture_output=True,
            text=True,
            check=False,
        )
        if inspect.returncode == 0 and inspect.stdout.strip() == "true":
            rc = 0
            for model in models:
                result = subprocess.run([docker, "exec", "sandbox-ollama", "ollama", "pull", model])
                rc = rc or result.returncode
            return rc
        _log.warning(
            "docker inspect on sandbox-ollama failed (rc=%d, stderr=%s) or the "
            "container is not running (stdout=%r) — falling back to host "
            "`ollama`, which may serve a DIFFERENT model set than the compose "
            "stack",
            inspect.returncode,
            inspect.stderr.strip()[:200],
            inspect.stdout.strip(),
        )
    ollama = shutil.which("ollama")
    if not ollama:
        raise FileNotFoundError("Neither sandbox-ollama container nor host `ollama` is available.")
    rc = 0
    for model in models:
        result = subprocess.run([ollama, "pull", model])
        rc = rc or result.returncode
    return rc
