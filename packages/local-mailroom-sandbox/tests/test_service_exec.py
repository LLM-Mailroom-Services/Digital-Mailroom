"""The shared guard around external CLIs: missing binary, failure, timeout, argv-only.

Every `sandbox modal|vllm|hf` command and `sandbox doctor` goes through this module, so
the failure modes are pinned once here with fake binaries instead of per command.
"""

from __future__ import annotations

import pytest

from mailroom_sandbox.services._exec import (
    ServiceError,
    ToolFailed,
    ToolMissing,
    ToolTimeout,
    require_tool,
    run_tool,
)


def test_require_tool_returns_the_resolved_path(fake_bin):
    shim = fake_bin.add("modal")
    assert require_tool("modal") == str(shim)


def test_require_tool_names_the_tool_and_the_install_hint_when_missing(fake_bin):
    with pytest.raises(ToolMissing) as exc:
        require_tool("modal", hint="pip install -e '.[deploy]'")
    message = str(exc.value)
    assert "modal" in message and "pip install -e '.[deploy]'" in message
    assert isinstance(exc.value, ServiceError)


def test_run_tool_captures_stdout_and_records_the_argv(fake_bin):
    fake_bin.add("hf", stdout="user: alice\n")
    result = run_tool(["hf", "auth", "whoami"])
    assert result.stdout == "user: alice\n" and result.returncode == 0
    assert fake_bin.calls("hf") == [["auth", "whoami"]]


def test_run_tool_raises_tool_failed_with_rc_and_stderr(fake_bin):
    fake_bin.add("modal", stderr="not authenticated\n", rc=3)
    with pytest.raises(ToolFailed) as exc:
        run_tool(["modal", "app", "list"])
    assert exc.value.returncode == 3
    assert "not authenticated" in str(exc.value)
    assert "modal app list" in str(exc.value)


def test_run_tool_check_false_returns_the_failure_instead_of_raising(fake_bin):
    fake_bin.add("modal", stderr="no such app\n", rc=1)
    result = run_tool(["modal", "app", "stop", "x"], check=False)
    assert result.returncode == 1 and "no such app" in result.stderr


def test_run_tool_times_out_with_a_service_error(fake_bin):
    fake_bin.add("vllm", sleep=5)
    with pytest.raises(ToolTimeout) as exc:
        run_tool(["vllm", "--version"], timeout=0.3)
    assert "vllm --version" in str(exc.value) and "0.3" in str(exc.value)


def test_run_tool_on_a_missing_binary_raises_tool_missing_not_filenotfound(fake_bin):
    with pytest.raises(ToolMissing):
        run_tool(["ollama", "list"], hint="install Ollama")


def test_run_tool_never_goes_through_a_shell(fake_bin):
    """Arguments with shell metacharacters reach the tool verbatim."""
    fake_bin.add("hf")
    run_tool(["hf", "download", "a; rm -rf /", "$(whoami)"])
    assert fake_bin.calls("hf") == [["download", "a; rm -rf /", "$(whoami)"]]


def test_stream_tool_echoes_every_line_and_returns_the_exit_code(fake_bin, capsys):
    from mailroom_sandbox.services._exec import stream_tool

    fake_bin.add("modal", stdout="building image\nready\n", rc=0)
    lines: list[str] = []
    rc = stream_tool(["modal", "deploy", "x.py"], on_line=lines.append)
    assert rc == 0
    assert lines == ["building image", "ready"]
    assert "building image" in capsys.readouterr().out
    assert fake_bin.calls("modal") == [["deploy", "x.py"]]


def test_stream_tool_returns_a_non_zero_exit_code_without_raising(fake_bin):
    from mailroom_sandbox.services._exec import stream_tool

    fake_bin.add("modal", stderr="boom\n", rc=4)
    assert stream_tool(["modal", "deploy", "x.py"]) == 4


def test_stream_tool_missing_binary_raises_tool_missing(fake_bin):
    from mailroom_sandbox.services._exec import stream_tool

    with pytest.raises(ToolMissing):
        stream_tool(["modal", "deploy", "x.py"], hint="pip install -e '.[deploy]'")


def test_stream_tool_kills_a_hung_process_after_the_timeout(fake_bin):
    from mailroom_sandbox.services._exec import stream_tool

    fake_bin.add("modal", sleep=30)
    with pytest.raises(ToolTimeout):
        stream_tool(["modal", "deploy", "x.py"], timeout=0.5)


def test_passthrough_tool_returns_the_exit_code_and_records_argv(fake_bin):
    from mailroom_sandbox.services._exec import passthrough_tool

    fake_bin.add("hf", rc=5)
    assert passthrough_tool(["hf", "auth", "login"]) == 5
    assert fake_bin.calls("hf") == [["auth", "login"]]


def test_passthrough_tool_missing_binary_raises_tool_missing(fake_bin):
    from mailroom_sandbox.services._exec import passthrough_tool

    with pytest.raises(ToolMissing):
        passthrough_tool(["hf", "auth", "login"], hint="pip install -U huggingface_hub")


def test_tool_failed_strips_terminal_colour_codes_from_the_message():
    """The real `hf` colours its errors; escape codes must not leak into the one-line `error:` message."""
    exc = ToolFailed(["hf", "auth", "whoami"], 1, "\x1b[1m\x1b[31mError: Not logged in.\x1b[0m")
    assert "\x1b" not in str(exc)
    assert "Error: Not logged in." in str(exc)
