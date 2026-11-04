"""One guarded way to run an external CLI.

Every ``sandbox modal|vllm|hf`` command and ``sandbox doctor`` goes through here, so a
missing binary, a non-zero exit and a hang each surface as a single actionable
``ServiceError`` (rendered by ``cli.main`` as one ``error:`` line) instead of a traceback.
Arguments are always an argv list; nothing is ever run through a shell.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path


_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def strip_ansi(text: str) -> str:
    """Drop terminal colour codes (the real ``hf`` colours its errors)."""
    return _ANSI.sub("", text or "")


class ServiceError(Exception):
    """An operational failure an operator can act on (not a bug in the sandbox)."""


class ToolMissing(ServiceError):
    """The external binary is not on ``PATH``."""

    def __init__(self, tool: str, hint: str = "") -> None:
        self.tool = tool
        self.hint = hint
        message = f"`{tool}` not found on PATH"
        super().__init__(f"{message} — {hint}" if hint else message)


class ToolFailed(ServiceError):
    """The external binary ran and exited non-zero."""

    def __init__(self, argv: Sequence[str], returncode: int, stderr: str = "") -> None:
        self.argv = list(argv)
        self.returncode = returncode
        self.stderr = stderr
        tail = " ".join(strip_ansi(stderr).strip().split())[:300]
        message = f"`{' '.join(self.argv)}` failed (rc={returncode})"
        super().__init__(f"{message}: {tail}" if tail else message)


class ToolTimeout(ServiceError):
    """The external binary did not finish within its time limit."""

    def __init__(self, argv: Sequence[str], timeout: float) -> None:
        self.argv = list(argv)
        self.timeout = timeout
        super().__init__(f"`{' '.join(self.argv)}` timed out after {timeout:g}s")


def require_tool(name: str, hint: str = "") -> str:
    """Return the resolved path of ``name`` or raise :class:`ToolMissing` with an install hint."""
    path = shutil.which(name)
    if not path:
        raise ToolMissing(name, hint)
    return path


def run_tool(
    argv: Sequence[str],
    *,
    timeout: float = 60.0,
    check: bool = True,
    hint: str = "",
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run ``argv`` (no shell) and capture text output.

    Raises :class:`ToolMissing` if ``argv[0]`` is not installed, :class:`ToolTimeout` after
    ``timeout`` seconds, and — unless ``check=False`` — :class:`ToolFailed` on a non-zero exit.
    """
    command = list(argv)
    require_tool(command[0], hint)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=dict(env) if env is not None else None,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolTimeout(command, timeout) from exc
    if check and result.returncode != 0:
        raise ToolFailed(command, result.returncode, result.stderr or "")
    return result


def stream_tool(
    argv: Sequence[str],
    *,
    timeout: float | None = None,
    hint: str = "",
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
    on_line: Callable[[str], None] | None = None,
) -> int:
    """Run ``argv`` (no shell), echo its merged output line by line and return the exit code.

    For long-running commands (``modal deploy``, ``hf download``) whose progress the
    operator should see live. ``on_line`` receives every line too, so a beacon can mirror
    the output. A non-zero exit is *returned*, not raised: the caller decides what it means.
    Raises :class:`ToolMissing` if the binary is absent and :class:`ToolTimeout` (after
    killing the process) when ``timeout`` seconds pass.
    """
    command = list(argv)
    require_tool(command[0], hint)
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=dict(env) if env is not None else None,
        cwd=cwd,
    )
    timed_out = threading.Event()

    def _expire() -> None:
        timed_out.set()
        proc.kill()

    timer = threading.Timer(timeout, _expire) if timeout else None
    if timer:
        timer.start()
    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip("\n")
            print(line, flush=True)
            if on_line:
                on_line(line)
        rc = proc.wait()
    finally:
        if timer:
            timer.cancel()
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    if timed_out.is_set():
        raise ToolTimeout(command, timeout or 0.0)
    return rc


def passthrough_tool(
    argv: Sequence[str],
    *,
    hint: str = "",
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
) -> int:
    """Run ``argv`` with the terminal attached (prompts, browser logins) and return its exit code.

    For ``sandbox <tool> raw -- …``: nothing is captured, so interactive CLIs such as
    ``modal token new`` or ``hf auth login`` behave exactly as when typed directly.
    """
    command = list(argv)
    require_tool(command[0], hint)
    sys.stdout.flush()
    return subprocess.run(
        command, check=False, env=dict(env) if env is not None else None, cwd=cwd
    ).returncode
