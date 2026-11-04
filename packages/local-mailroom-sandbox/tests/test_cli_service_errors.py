"""`main()` turns known operational failures into one `error:` line, never a traceback.

Only failures an operator can act on are mapped (a missing/failed/timed-out external
tool, a tunnel problem, an unresolved Modal endpoint, a port already in use). Anything
else — a plain `ValueError`, a permission error — still propagates so real bugs are not
hidden behind a friendly message.
"""

from __future__ import annotations

import errno
import subprocess

import pytest

from mailroom_sandbox import cli
from mailroom_sandbox.job.spec import EndpointUnresolved, EngineSpec, ModalSpec, RunSpec, engine_base_url
from mailroom_sandbox.services._exec import ServiceError, ToolFailed, ToolMissing, ToolTimeout
from mailroom_sandbox.tunnel import TunnelError


def _raises(exc: BaseException):
    def handler(args):
        raise exc

    return handler


@pytest.mark.parametrize(
    ("exc", "needle"),
    [
        (ToolMissing("modal", "pip install -e '.[deploy]'"), "modal"),
        (ToolFailed(["modal", "app", "list"], 3, "not authenticated"), "not authenticated"),
        (ToolTimeout(["vllm", "--version"], 5.0), "timed out"),
        (TunnelError("ssh not found"), "ssh not found"),
        (EndpointUnresolved("MODAL_WORKSPACE is not set"), "MODAL_WORKSPACE"),
        (subprocess.TimeoutExpired(["ollama", "pull", "x"], 30), "timed out"),
        (OSError(errno.EADDRINUSE, "Address already in use"), "already in use"),
    ],
    ids=["missing", "failed", "timeout", "tunnel", "endpoint", "timeout-expired", "port-busy"],
)
def test_known_operational_failures_exit_one_with_a_single_error_line(monkeypatch, capsys, exc, needle):
    monkeypatch.setattr(cli, "_cmd_profiles", _raises(exc))
    assert cli.main(["profiles"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and needle in err
    assert err.count("\n") == 1 and "Traceback" not in err


@pytest.mark.parametrize(
    "exc",
    [ValueError("a real bug"), KeyError("oops"), OSError(errno.EACCES, "Permission denied")],
    ids=["value-error", "key-error", "permission"],
)
def test_unexpected_errors_still_propagate(monkeypatch, exc):
    monkeypatch.setattr(cli, "_cmd_profiles", _raises(exc))
    with pytest.raises(type(exc)):
        cli.main(["profiles"])


def test_tunnel_and_tool_errors_share_the_service_error_base():
    assert issubclass(TunnelError, ServiceError)
    assert issubclass(ToolMissing, ServiceError) and issubclass(ToolFailed, ServiceError)


def test_unresolved_modal_endpoint_is_a_value_error_and_a_service_error(monkeypatch):
    """Existing `except ValueError` callers keep working; the CLI maps it to one line."""
    monkeypatch.setattr("mailroom_sandbox.paths.dotenv_files", lambda: [])
    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    monkeypatch.delenv("MODAL_WORKSPACE", raising=False)
    spec = RunSpec(
        profile="modal-vllm",
        task="sorter",
        engine=EngineSpec(kind="modal-vllm", model="Qwen/Qwen3-8B", modal=ModalSpec(app="sandbox-vllm")),
    )
    with pytest.raises(EndpointUnresolved) as exc:
        engine_base_url(spec)
    assert isinstance(exc.value, ValueError) and isinstance(exc.value, ServiceError)
