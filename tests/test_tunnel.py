"""Tunnel spec/argv/pidfile lifecycle — network-free (no socket, no spawn)."""

import pytest

from mailroom_sandbox.tunnel import (
    TunnelError,
    build_ssh_argv,
    pidfile,
    read_pid,
    tunnel_spec,
)

BASE_PROFILE = {
    "name": "vllm-remote",
    "tunnel": {
        "local_port": 18000,
        "remote_host": "localhost",
        "remote_port": 8000,
        "host_env": "T_HOST",
        "user_env": "T_USER",
        "ssh_port_env": "T_PORT",
        "key_env": "T_KEY",
    },
}


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("T_HOST", "gpu.lab.example")
    monkeypatch.setenv("T_USER", "jdoe")
    monkeypatch.setenv("T_PORT", "2222")
    monkeypatch.setenv("T_KEY", "/home/jdoe/.ssh/chtc_key")
    return monkeypatch


def test_spec_resolves_from_environment(env):
    spec = tunnel_spec(BASE_PROFILE)
    assert spec.host == "gpu.lab.example"
    assert spec.user == "jdoe"
    assert spec.ssh_port == 2222
    assert spec.key == "/home/jdoe/.ssh/chtc_key"
    assert spec.forward == "18000:localhost:8000"
    assert spec.destination == "jdoe@gpu.lab.example"
    assert spec.base_url == "http://localhost:18000/v1"


def test_spec_defaults_ssh_port_and_missing_key(monkeypatch, env):
    monkeypatch.delenv("T_KEY")
    monkeypatch.delenv("T_PORT")
    spec = tunnel_spec(BASE_PROFILE)
    assert spec.ssh_port == 22
    assert spec.key is None


def test_spec_requires_host_and_user(monkeypatch):
    monkeypatch.setenv("T_USER", "jdoe")
    with pytest.raises(TunnelError, match="T_HOST"):
        tunnel_spec(BASE_PROFILE)
    monkeypatch.setenv("T_HOST", "h")
    monkeypatch.delenv("T_USER")
    with pytest.raises(TunnelError, match="T_USER"):
        tunnel_spec(BASE_PROFILE)


def test_spec_rejects_missing_block_and_bad_ports():
    with pytest.raises(TunnelError, match="no tunnel"):
        tunnel_spec({"name": "bare"})
    bad = {"name": "v", "tunnel": {**BASE_PROFILE["tunnel"], "local_port": 0}}
    with pytest.raises(TunnelError, match="ports"):
        tunnel_spec(bad)


def test_argv_shape(env):
    argv = build_ssh_argv(tunnel_spec(BASE_PROFILE))
    assert argv[:3] == ["ssh", "-N", "-L"]
    assert "18000:localhost:8000" in argv
    assert "-p" in argv and "2222" in argv
    assert "-i" in argv and "/home/jdoe/.ssh/chtc_key" in argv
    assert "ExitOnForwardFailure=yes" in argv
    assert argv[-1] == "jdoe@gpu.lab.example"


def test_argv_omits_key_when_unset(monkeypatch, env):
    monkeypatch.delenv("T_KEY")
    argv = build_ssh_argv(tunnel_spec(BASE_PROFILE))
    assert "-i" not in argv


def test_pidfile_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("mailroom_sandbox.tunnel.repo_root", lambda: tmp_path)
    assert read_pid("vllm-remote") is None
    path = pidfile("vllm-remote")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("4242\n", encoding="utf-8")
    assert read_pid("vllm-remote") == 4242
    path.write_text("not-a-pid", encoding="utf-8")
    assert read_pid("vllm-remote") is None
