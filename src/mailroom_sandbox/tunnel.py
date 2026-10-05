"""SSH local-port-forward lifecycle for remote serving profiles.

Network-free by import; the only socket touch is `is_up`, and subprocesses
spawn only from the explicit CLI handlers (`sandbox tunnel up/down`).
Credentials resolve from the environment named in the profile's `tunnel:`
block — nothing secret is stored in config.
"""

from __future__ import annotations

import os
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path

from mailroom_sandbox.paths import repo_root

TUNNEL_ENV_PREFIX = "SANDBOX_TUNNEL"


class TunnelError(Exception):
    """Profile tunnel block is missing or incomplete."""


@dataclass(frozen=True)
class TunnelSpec:
    profile: str
    local_port: int
    remote_host: str
    remote_port: int
    host: str
    user: str
    ssh_port: int
    key: str | None

    @property
    def forward(self) -> str:
        return f"{self.local_port}:{self.remote_host}:{self.remote_port}"

    @property
    def destination(self) -> str:
        return f"{self.user}@{self.host}"

    @property
    def base_url(self) -> str:
        return f"http://localhost:{self.local_port}/v1"


def tunnel_spec(profile: dict) -> TunnelSpec:
    block = profile.get("tunnel")
    if not isinstance(block, dict):
        raise TunnelError(f"profile '{profile.get('name')}' has no tunnel: block")

    def _env(key: str, *, required: bool) -> str:
        env_name = str(block.get(key) or "")
        if not env_name:
            if required:
                raise TunnelError(f"tunnel block is missing '{key}'")
            return ""
        value = os.environ.get(env_name, "").strip()
        if required and not value:
            raise TunnelError(
                f"environment variable {env_name} is not set (required by the "
                f"'{profile.get('name')}' tunnel block)"
            )
        return value

    local_port = int(block.get("local_port") or 0)
    remote_port = int(block.get("remote_port") or 0)
    if not (0 < local_port < 65536) or not (0 < remote_port < 65536):
        raise TunnelError("tunnel local_port/remote_port must be valid TCP ports")
    return TunnelSpec(
        profile=str(profile.get("name")),
        local_port=local_port,
        remote_host=str(block.get("remote_host") or "localhost"),
        remote_port=remote_port,
        host=_env("host_env", required=True),
        user=_env("user_env", required=True),
        ssh_port=int(_env("ssh_port_env", required=False) or 22),
        key=_env("key_env", required=False) or None,
    )


def build_ssh_argv(spec: TunnelSpec) -> list[str]:
    """The exact forward command (no shell, no secrets beyond the key path)."""
    argv = [
        "ssh",
        "-N",
        "-L",
        spec.forward,
        "-p",
        str(spec.ssh_port),
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "ServerAliveCountMax=3",
        "-o",
        "BatchMode=yes",
    ]
    if spec.key:
        argv += ["-i", spec.key]
    argv.append(spec.destination)
    return argv


def is_up(local_port: int, *, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", local_port), timeout=timeout):
            return True
    except OSError:
        return False


def pidfile(profile: str) -> Path:
    return repo_root() / "data" / "runtime" / f"tunnel-{profile}.pid"


def read_pid(profile: str) -> int | None:
    path = pidfile(profile)
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def spawn(spec: TunnelSpec) -> int:
    """Start the detached forward and record its pid (CLI handler only)."""
    if is_up(spec.local_port):
        raise TunnelError(
            f"localhost:{spec.local_port} already answers — is the tunnel (or the "
            "service itself) already up? Refusing to double-forward."
        )
    argv = build_ssh_argv(spec)
    proc = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    path = pidfile(spec.profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{proc.pid}\n", encoding="utf-8")
    return proc.pid


def terminate(spec: TunnelSpec) -> int | None:
    """Stop the recorded forward, if any (CLI handler only)."""
    pid = read_pid(spec.profile)
    if pid is None:
        return None
    proc = subprocess.run(["kill", str(pid)], check=False, capture_output=True)
    if proc.returncode != 0:
        raise TunnelError(
            f"kill {pid} failed (rc={proc.returncode}): "
            f"{(proc.stderr.strip() or proc.stdout.strip())[:300]} — the tunnel "
            "process may still be alive; pidfile kept so `tunnel status` can see it"
        )
    pidfile(spec.profile).unlink(missing_ok=True)
    return pid
