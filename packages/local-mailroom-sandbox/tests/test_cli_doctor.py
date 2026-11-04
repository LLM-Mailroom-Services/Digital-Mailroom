"""`sandbox doctor`: one status table for every service the sandbox talks to.

Offline by default (binaries, config, credentials-present), `--live` adds network probes. Warnings
never fail the command; a *failing* check (e.g. the active profile has no endpoint) exits 1.
"""

from __future__ import annotations

import json

import httpx
import pytest

from mailroom_sandbox import cli
from mailroom_sandbox.tui.services_snapshot import read_services

PIN = "modal client version: 1.6.2\n"


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setattr("mailroom_sandbox.paths.dotenv_files", lambda: [])
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("SANDBOX_PROFILE", "modal-vllm")
    for name in (
        "MODAL_WORKSPACE", "VLLM_BASE_URL", "VLLM_API_KEY", "MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET",
        "MODAL_CONFIG_PATH", "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HF_HOME", "LANGFUSE_HOST",
        "LANGFUSE_BASE_URL", "PHOENIX_ENDPOINT", "MODAL_VLLM_APP_NAME", "OPENROUTER_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    def boom(*a, **k):
        raise AssertionError("offline doctor must not touch the network")

    monkeypatch.setattr("mailroom_sandbox.health.httpx.get", boom)
    monkeypatch.setattr("mailroom_sandbox.health.httpx.post", boom)


def _doctor(capsys, *args):
    rc = cli.main(["doctor", "--json", *args])
    return rc, {row["name"]: row for row in json.loads(capsys.readouterr().out)["services"]}


def _tools(fake_bin):
    fake_bin.add("modal", rules=[{"prefix": ["--version"], "stdout": PIN}])
    fake_bin.add("hf", stdout="2.3.0\n")
    for name in ("docker", "ollama", "ssh", "git", "vllm"):
        fake_bin.add(name)


def test_offline_doctor_reports_every_service_without_network(fake_bin, capsys, monkeypatch):
    _tools(fake_bin)
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    rc, rows = _doctor(capsys)
    assert rc == 0
    assert {"modal", "modal-auth", "hf", "hf-auth", "docker", "ollama", "ssh", "git", "vllm",
            "provider", "openrouter", "langfuse", "phoenix", "tunnel", "compose"} <= set(rows)
    assert all(r["state"] in {"ok", "warn", "fail", "skipped"} for r in rows.values())


def test_json_rows_have_the_documented_fields(fake_bin, capsys, monkeypatch):
    _tools(fake_bin)
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    _rc, rows = _doctor(capsys)
    assert set(rows["modal"]) == {"name", "state", "detail", "hint"}


def test_modal_ok_at_the_pinned_sdk(fake_bin, capsys, monkeypatch):
    _tools(fake_bin)
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    _rc, rows = _doctor(capsys)
    assert rows["modal"]["state"] == "ok" and "1.6.2" in rows["modal"]["detail"]


def test_modal_missing_is_a_warning_with_the_install_hint(fake_bin, capsys, monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    rc, rows = _doctor(capsys)
    assert rc == 0  # a warning never fails the command
    assert rows["modal"]["state"] == "warn" and ".[deploy]" in rows["modal"]["hint"]


def test_modal_off_the_pin_is_a_warning(fake_bin, capsys, monkeypatch):
    fake_bin.add("modal", rules=[{"prefix": ["--version"], "stdout": "modal client version: 1.4.0\n"}])
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    _rc, rows = _doctor(capsys)
    assert rows["modal"]["state"] == "warn" and "1.4.0" in rows["modal"]["detail"] and "1.6.2" in rows["modal"]["detail"]


def test_ollama_is_skipped_when_the_profile_does_not_use_it(fake_bin, capsys, monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    _rc, rows = _doctor(capsys)
    assert rows["ollama"]["state"] == "skipped" and rows["vllm"]["state"] == "skipped"


def test_ollama_missing_warns_under_the_ollama_profile(fake_bin, capsys):
    _rc, rows = _doctor(capsys, "--profile", "ollama")
    assert rows["ollama"]["state"] == "warn"


@pytest.mark.parametrize(
    ("setup", "state"),
    [
        ({"MODAL_TOKEN_ID": "tok-id-9f3", "MODAL_TOKEN_SECRET": "tok-secret-7c1"}, "ok"),
        ({}, "warn"),
    ],
    ids=["env-tokens", "none"],
)
def test_modal_auth_is_detected_without_reading_secrets(fake_bin, capsys, monkeypatch, setup, state):
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    for k, v in setup.items():
        monkeypatch.setenv(k, v)
    _rc, rows = _doctor(capsys)
    assert rows["modal-auth"]["state"] == state
    if state == "warn":
        assert "modal token new" in rows["modal-auth"]["hint"]
    dumped = json.dumps(rows)
    assert "tok-id-9f3" not in dumped and "tok-secret-7c1" not in dumped


@pytest.mark.parametrize("live", [False, True])
def test_endpoint_credentials_never_reach_output_or_snapshot(fake_bin, monkeypatch, capsys, live):
    from mailroom_sandbox.tui.beacon import beacon_root

    base = "https://user-secret:password-secret@vllm.test/v1?token=query-secret#fragment-secret"
    monkeypatch.setenv("VLLM_BASE_URL", base)
    monkeypatch.setenv("LANGFUSE_HOST", base)

    def get(url, **kw):
        raise httpx.ConnectError(f"failed: {url}")

    monkeypatch.setattr("mailroom_sandbox.health.httpx.get", get)
    cli.main(["doctor", "--json", "--publish", *(["--live"] if live else [])])
    captured = capsys.readouterr()
    output = captured.out + captured.err + json.dumps(read_services(beacon_root()))
    assert "vllm.test" in output
    for secret in ("user-secret", "password-secret", "query-secret", "fragment-secret"):
        assert secret not in output


def test_one_failed_check_does_not_abort_remaining_checks(fake_bin, monkeypatch, capsys):
    from mailroom_sandbox.services import doctor
    from mailroom_sandbox.services._exec import ToolTimeout

    _tools(fake_bin)
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    original = doctor.run_tool

    def run(argv, **kw):
        if argv[0] == "modal":
            raise ToolTimeout(argv, 15)
        return original(argv, **kw)

    monkeypatch.setattr(doctor, "run_tool", run)
    rc, rows = _doctor(capsys)
    assert rc == 0 and rows["modal"]["state"] == "warn"
    assert "timed out" in rows["modal"]["detail"]
    assert rows["hf"]["state"] == "ok" and rows["provider"]["state"] == "ok"


@pytest.mark.parametrize(("stdout", "stderr", "code", "state", "detail"), [
    ("", "\x1b[31mdaemon\n unavailable\x1b[0m", 1, "warn", "daemon unavailable"),
    ("langfuse\npostgres\n", "", 0, "ok", "running: langfuse, postgres"),
    ("", "", 0, "warn", "no compose service running"),
])
def test_live_compose_states(fake_bin, capsys, stdout, stderr, code, state, detail):
    _tools(fake_bin)
    fake_bin.add("docker", stdout=stdout, stderr=stderr, rc=code)
    rc, rows = _doctor(capsys, "--live", "--service", "compose")
    assert rc == 0 and rows["compose"]["state"] == state
    assert rows["compose"]["detail"] == detail


def test_unrecognized_version_warns(fake_bin, capsys):
    fake_bin.add("modal", stdout="development build\n")
    rc, rows = _doctor(capsys, "--service", "modal")
    assert rc == 0 and rows["modal"]["state"] == "warn"
    assert "could not determine" in rows["modal"]["detail"]


def test_live_tunnel_with_closed_port_warns(fake_bin, monkeypatch, capsys):
    monkeypatch.setenv("SANDBOX_TUNNEL_HOST", "gpu.test")
    monkeypatch.setenv("SANDBOX_TUNNEL_USER", "alice")
    monkeypatch.setattr("mailroom_sandbox.tunnel.read_pid", lambda name: 1234)
    monkeypatch.setattr("mailroom_sandbox.tunnel.is_alive", lambda pid: True)
    monkeypatch.setattr("mailroom_sandbox.tunnel.is_ssh_process", lambda pid: True)
    monkeypatch.setattr("mailroom_sandbox.tunnel.is_up", lambda port: False)
    rc, rows = _doctor(capsys, "--profile", "vllm-remote", "--live", "--service", "tunnel")
    assert rc == 0 and rows["tunnel"]["state"] == "warn"
    assert "not answering" in rows["tunnel"]["detail"]


def test_modal_auth_ok_from_the_config_file(fake_bin, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    (home / ".modal.toml").write_text("[default]\n", encoding="utf-8")
    _rc, rows = _doctor(capsys)
    assert rows["modal-auth"]["state"] == "ok"


def test_hf_version_and_auth(fake_bin, capsys, monkeypatch):
    _tools(fake_bin)
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    monkeypatch.setenv("HF_TOKEN", "hf_secret")
    _rc, rows = _doctor(capsys)
    assert rows["hf"]["state"] == "ok" and "2.3.0" in rows["hf"]["detail"]
    assert rows["hf-auth"]["state"] == "ok"
    assert "hf_secret" not in json.dumps(rows)


def test_hf_without_a_token_warns_but_names_the_anonymous_fallback(fake_bin, capsys, monkeypatch):
    _tools(fake_bin)
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    _rc, rows = _doctor(capsys)
    assert rows["hf-auth"]["state"] == "warn" and "hf auth login" in rows["hf-auth"]["hint"]


def test_provider_without_an_endpoint_fails_the_command_never_localhost(fake_bin, capsys):
    rc, rows = _doctor(capsys)
    assert rc == 1
    assert rows["provider"]["state"] == "fail"
    assert "VLLM_BASE_URL" in rows["provider"]["hint"] and "localhost" not in rows["provider"]["detail"]


def test_provider_ok_when_the_endpoint_is_configured_not_probed(fake_bin, capsys, monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    _rc, rows = _doctor(capsys)
    assert rows["provider"]["state"] == "ok" and "vllm.test" in rows["provider"]["detail"]
    assert "not probed" in rows["provider"]["detail"]


def test_live_probes_the_provider_and_reports_a_down_endpoint(fake_bin, capsys, monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")

    def get(url, **kw):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr("mailroom_sandbox.health.httpx.get", get)
    rc, rows = _doctor(capsys, "--live")
    assert rc == 1 and rows["provider"]["state"] == "fail" and "ConnectError" in rows["provider"]["detail"]


def test_live_ok_endpoint(fake_bin, capsys, monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    monkeypatch.setattr(
        "mailroom_sandbox.health.httpx.get",
        lambda url, **kw: httpx.Response(200, json={"data": [{"id": "Qwen/Qwen3-8B"}]}),
    )
    rc, rows = _doctor(capsys, "--live")
    assert rc == 0 and rows["provider"]["state"] == "ok" and "Qwen/Qwen3-8B" in rows["provider"]["detail"]


def _modal_endpoint_times_out(fake_bin, monkeypatch, rows):
    monkeypatch.setenv("VLLM_BASE_URL", "https://ws--sandbox-vllm-serve.modal.run/v1")
    fake_bin.add("modal", rules=[
        {"prefix": ["--version"], "stdout": "modal client version: 1.6.2\n"},
        {"prefix": ["app", "list"], "stdout": json.dumps(rows)},
    ])

    def get(url, **kw):
        raise httpx.ReadTimeout("The read operation timed out")

    monkeypatch.setattr("mailroom_sandbox.health.httpx.get", get)


APP = {"description": "sandbox-vllm", "state": "deployed", "tasks": "0"}


def test_a_queued_modal_endpoint_warns_instead_of_failing(fake_bin, capsys, monkeypatch):
    _modal_endpoint_times_out(fake_bin, monkeypatch, [APP])
    rc, rows = _doctor(capsys, "--live")
    assert rc == 0 and rows["provider"]["state"] == "warn"
    assert "queued for a GPU" in rows["provider"]["detail"] and "not billing" in rows["provider"]["detail"]


def test_a_booting_modal_container_is_called_out_as_billing(fake_bin, capsys, monkeypatch):
    _modal_endpoint_times_out(fake_bin, monkeypatch, [{**APP, "tasks": "1"}])
    rc, rows = _doctor(capsys, "--live")
    assert rc == 0 and "still booting (billing)" in rows["provider"]["detail"]


def test_a_timeout_on_an_undeployed_app_still_fails(fake_bin, capsys, monkeypatch):
    _modal_endpoint_times_out(fake_bin, monkeypatch, [])
    rc, rows = _doctor(capsys, "--live")
    assert rc == 1 and rows["provider"]["state"] == "fail" and "not deployed" in rows["provider"]["detail"]


def test_vllm_probe_says_a_queued_endpoint_is_not_ready(fake_bin, capsys, monkeypatch):
    _modal_endpoint_times_out(fake_bin, monkeypatch, [APP])
    assert cli.main(["vllm", "probe", "--profile", "modal-vllm"]) == 1
    captured = capsys.readouterr()
    assert "not ready:" in captured.err and "not healthy" not in captured.err
    assert "skipped (endpoint still starting)" in captured.out


def test_health_explains_a_queued_endpoint(fake_bin, capsys, monkeypatch):
    from mailroom_sandbox.health import health_check

    _modal_endpoint_times_out(fake_bin, monkeypatch, [APP])
    report = health_check("modal-vllm")
    assert report["ok"] is False and "queued for a GPU" in report["models"]["detail"]


def test_live_modal_row_reads_the_account_without_touching_the_endpoint(fake_bin, capsys, monkeypatch):
    _modal_endpoint_times_out(fake_bin, monkeypatch, [APP])
    rc, rows = _doctor(capsys, "--live", "--service", "modal")
    assert rc == 0 and "sandbox-vllm deployed, containers=0" in rows["modal"]["detail"]


def test_live_modal_row_fails_when_the_account_cannot_be_read(fake_bin, capsys, monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", "https://ws--sandbox-vllm-serve.modal.run/v1")
    fake_bin.add("modal", rules=[
        {"prefix": ["--version"], "stdout": "modal client version: 1.6.2\n"},
        {"prefix": ["app", "list"], "code": 1, "stderr": "token invalid"},
    ])
    rc, rows = _doctor(capsys, "--live", "--service", "modal")
    assert rc == 1 and rows["modal"]["state"] == "fail" and "account check failed" in rows["modal"]["detail"]


def test_langfuse_warns_when_the_sdk_is_missing(fake_bin, capsys, monkeypatch):
    monkeypatch.setenv("LANGFUSE_HOST", "http://lf.test")
    monkeypatch.setenv("OBSERVABILITY_PROVIDER", "langfuse")
    monkeypatch.setattr("mailroom_sandbox.services.doctor.find_spec", lambda name: None)
    _, rows = _doctor(capsys)
    assert rows["langfuse"]["state"] == "warn" and "no traces" in rows["langfuse"]["detail"]
    assert "observability" in rows["langfuse"]["hint"]


def test_live_states_that_probing_modal_can_wake_a_billed_gpu(fake_bin, capsys, monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", "https://ws--sandbox-vllm-serve.modal.run/v1")
    monkeypatch.setattr("mailroom_sandbox.health.httpx.get", lambda url, **kw: httpx.Response(200, json={"data": []}))
    cli.main(["doctor", "--live"])
    assert "cold-start" in capsys.readouterr().err


def test_langfuse_and_phoenix_never_fail_the_command_when_down(fake_bin, capsys, monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    monkeypatch.setenv("PHOENIX_ENDPOINT", "http://phoenix.test/v1/traces")

    def get(url, **kw):
        if "vllm.test" in url:
            return httpx.Response(200, json={"data": []})
        raise httpx.ConnectError("down")

    monkeypatch.setattr("mailroom_sandbox.health.httpx.get", get)
    rc, rows = _doctor(capsys, "--live")
    assert rc == 0
    assert rows["langfuse"]["state"] == "warn" and rows["phoenix"]["state"] == "warn"


def test_phoenix_is_skipped_unless_configured(fake_bin, capsys, monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    monkeypatch.setenv("PHOENIX_ENDPOINT", "")  # an operator .env must not configure it
    _rc, rows = _doctor(capsys)
    assert rows["phoenix"]["state"] == "skipped"


def test_tunnel_is_skipped_for_a_profile_without_one(fake_bin, capsys, monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    _rc, rows = _doctor(capsys)
    assert rows["tunnel"]["state"] == "skipped"


def test_tunnel_warns_when_no_forward_is_running(fake_bin, capsys, monkeypatch, tmp_path):
    monkeypatch.setattr("mailroom_sandbox.tunnel.repo_root", lambda: tmp_path)
    monkeypatch.setenv("SANDBOX_TUNNEL_HOST", "h")
    monkeypatch.setenv("SANDBOX_TUNNEL_USER", "u")
    _rc, rows = _doctor(capsys, "--profile", "vllm-remote")
    assert rows["tunnel"]["state"] == "warn" and "sandbox tunnel" in rows["tunnel"]["hint"]


def test_tunnel_with_a_live_ssh_pid_is_ok(fake_bin, capsys, monkeypatch, tmp_path):
    monkeypatch.setattr("mailroom_sandbox.tunnel.repo_root", lambda: tmp_path)
    monkeypatch.setenv("SANDBOX_TUNNEL_HOST", "h")
    monkeypatch.setenv("SANDBOX_TUNNEL_USER", "u")
    monkeypatch.setattr("mailroom_sandbox.tunnel.read_pid", lambda profile: 4242)
    monkeypatch.setattr("mailroom_sandbox.tunnel.is_alive", lambda pid: True)
    monkeypatch.setattr("mailroom_sandbox.tunnel.is_ssh_process", lambda pid: True)
    _rc, rows = _doctor(capsys, "--profile", "vllm-remote")
    assert rows["tunnel"]["state"] == "ok" and "4242" in rows["tunnel"]["detail"]


def test_a_tunnel_profile_missing_its_env_is_a_warning_not_a_crash(fake_bin, capsys, monkeypatch, tmp_path):
    monkeypatch.setattr("mailroom_sandbox.tunnel.repo_root", lambda: tmp_path)
    monkeypatch.delenv("SANDBOX_TUNNEL_HOST", raising=False)
    monkeypatch.delenv("SANDBOX_TUNNEL_USER", raising=False)
    _rc, rows = _doctor(capsys, "--profile", "vllm-remote")
    assert rows["tunnel"]["state"] == "warn" and "SANDBOX_TUNNEL_HOST" in rows["tunnel"]["detail"]


def test_service_filter_limits_the_rows(fake_bin, capsys, monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    _tools(fake_bin)
    _rc, rows = _doctor(capsys, "--service", "modal", "--service", "hf")
    assert set(rows) == {"modal", "hf"}


def test_unknown_service_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["doctor", "--service", "nope"])
    assert exc.value.code == 2


def test_text_output_has_one_line_per_service_and_hints(fake_bin, capsys):
    rc = cli.main(["doctor"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "provider" in out and "FAIL" in out and "sandbox modal deploy" in out
    assert out.count("\n") >= 14


def test_publish_writes_the_snapshot_the_board_reads(fake_bin, capsys, monkeypatch, tmp_path):
    from mailroom_sandbox.tui.beacon import beacon_root

    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    assert cli.main(["doctor", "--publish"]) == 0
    capsys.readouterr()
    snap = read_services(beacon_root())
    assert snap["profile"] == "modal-vllm" and snap["live"] is False
    assert {r["name"] for r in snap["services"]} >= {"modal", "provider"}


def test_without_publish_nothing_is_written(fake_bin, capsys, monkeypatch):
    from mailroom_sandbox.tui.beacon import beacon_root

    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.test/v1")
    cli.main(["doctor"])
    assert read_services(beacon_root()) is None


def test_the_suite_never_loads_a_developers_env_file(monkeypatch, tmp_path):
    import os

    from mailroom_sandbox import runtime

    env_file = tmp_path / ".env"
    env_file.write_text("SANDBOX_ENV_LEAK=1\n")
    monkeypatch.setattr("mailroom_sandbox.runtime.dotenv_files", lambda: [env_file], raising=False)
    monkeypatch.setattr("mailroom_sandbox.paths.dotenv_files", lambda: [env_file])
    monkeypatch.delenv("SANDBOX_ENV_LEAK", raising=False)
    runtime.load_env_file()
    assert "SANDBOX_ENV_LEAK" not in os.environ
