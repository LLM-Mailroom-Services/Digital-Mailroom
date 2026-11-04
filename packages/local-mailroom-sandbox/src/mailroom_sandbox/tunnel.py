"""SSH local-port-forward lifecycle for remote serving profiles.

Network-free by import; the only socket touch is `is_up`, and subprocesses
spawn only from the explicit CLI handlers (`sandbox tunnel up/down`).
Credentials resolve from the environment named in the profile's `tunnel:`
block — nothing secret is stored in config.
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from mailroom_sandbox.paths import repo_root
from mailroom_sandbox.services._exec import ServiceError, ToolMissing, require_tool

TUNNEL_ENV_PREFIX = "SANDBOX_TUNNEL"


class TunnelError(ServiceError):
    """The tunnel block is incomplete, or the ssh forward could not be started or stopped."""


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
        ssh_port=_ssh_port(block, _env("ssh_port_env", required=False)),
        key=_env("key_env", required=False) or None,
    )


def _ssh_port(block: dict, raw: str) -> int:
    """The ssh port from its env var (default 22); a non-numeric value is a clear error."""
    if not raw:
        return 22
    try:
        port = int(raw)
    except ValueError:
        port = 0
    if not 0 < port < 65536:
        raise TunnelError(f"{block.get('ssh_port_env')} must be a TCP port (1-65535), got {raw!r}")
    return port


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


def is_alive(pid: int) -> bool:
    """True when ``pid`` is a running (non-zombie) process."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        return stat.rsplit(")", 1)[1].split()[0] != "Z"
    except (OSError, IndexError):
        # macOS has no /proc; kill(pid, 0) also succeeds for an unreaped zombie.
        try:
            result = subprocess.run(
                ["/bin/ps" if Path("/bin/ps").is_file() else "ps", "-p", str(pid), "-o", "stat="],
                capture_output=True, text=True, timeout=5, check=False,
            )
            state = result.stdout.strip()
            return bool(state) and not state.startswith("Z")
        except (OSError, subprocess.SubprocessError):
            return True


def _command_tokens(pid: int) -> list[str]:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return [t for t in raw.decode(errors="replace").split("\0") if t]
    except OSError:
        pass
    try:
        out = subprocess.run(
            ["/bin/ps" if Path("/bin/ps").is_file() else "ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True, timeout=5, check=False
        ).stdout
        return out.split()
    except (OSError, subprocess.SubprocessError):
        return []


def is_ssh_process(pid: int) -> bool:
    """True when ``pid`` is an ssh client (guards against killing a process that reused the pid)."""
    return any(os.path.basename(token) == "ssh" for token in _command_tokens(pid)[:2])


def _stderr_tail(path: str) -> str:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return " ".join(text.split())[-300:]


def spawn(spec: TunnelSpec, *, wait: float = 10.0) -> int:
    """Start the detached forward and record its pid once the local port answers (CLI handler only).

    ssh's stderr is captured so a refused key or unreachable host is reported, not discarded;
    a forward that exits early or never opens the port within ``wait`` seconds is cleaned up
    and raised as a :class:`TunnelError` — no pidfile is left for a dead process.
    """
    if is_up(spec.local_port):
        raise TunnelError(
            f"localhost:{spec.local_port} already answers — is the tunnel (or the "
            "service itself) already up? Refusing to double-forward."
        )
    try:
        require_tool("ssh", "install an OpenSSH client")
    except ToolMissing as exc:
        raise TunnelError(str(exc)) from exc
    argv = build_ssh_argv(spec)
    errfile = tempfile.NamedTemporaryFile(prefix="sandbox-tunnel-", suffix=".err", delete=False)
    proc = None
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=errfile,
            start_new_session=True,
        )
        errfile.close()
        deadline = time.monotonic() + wait
        while True:
            returncode = proc.poll()
            if returncode is not None:
                detail = _stderr_tail(errfile.name)
                raise TunnelError(
                    f"ssh exited (rc={returncode}) before the forward opened"
                    + (f": {detail}" if detail else "")
                )
            if is_up(spec.local_port):
                break
            if time.monotonic() >= deadline:
                _kill_group(proc)
                detail = _stderr_tail(errfile.name)
                raise TunnelError(
                    f"forward did not open localhost:{spec.local_port} within {wait:g}s"
                    + (f": {detail}" if detail else "")
                )
            time.sleep(0.1)
        path = pidfile(spec.profile)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{proc.pid}\n", encoding="utf-8")
    except BaseException:
        if proc is not None and proc.poll() is None:
            _kill_group(proc)
        raise
    finally:
        errfile.close()
        Path(errfile.name).unlink(missing_ok=True)
    return proc.pid


def _kill_group(proc: subprocess.Popen) -> None:
    """Terminate the ssh child (it leads its own session) and reap it."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def terminate(spec: TunnelSpec) -> int | None:
    """Stop the recorded forward and return its pid; ``None`` when nothing was running.

    A pidfile whose process is gone — or that now belongs to something that is not ssh
    (pid reuse) — is cleared without signalling anything.
    """
    pid = read_pid(spec.profile)
    if pid is None:
        return None
    path = pidfile(spec.profile)
    if not is_alive(pid) or not is_ssh_process(pid):
        path.unlink(missing_ok=True)
        return None
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        path.unlink(missing_ok=True)
        return None
    except PermissionError as exc:
        raise TunnelError(f"not allowed to stop pid {pid}: {exc}") from exc
    deadline = time.monotonic() + 5
    while is_alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    if is_alive(pid):
        raise TunnelError(
            f"pid {pid} did not exit after SIGTERM — pidfile kept so `tunnel status` can see it"
        )
    path.unlink(missing_ok=True)
    return pid
