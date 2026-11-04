"""`sandbox modal …`: a guarded passthrough to the real Modal CLI.

Driven through ``cli.main`` with fake binaries (no Modal account, no network, no spend).
The contract: a missing binary is one ``error:`` line with the install hint, ``--dry-run``
prints the exact argv and runs nothing, sandbox defaults (model/GPU from the matrix, the
pinned app name) are injected, and ``stop`` is idempotent.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from mailroom_sandbox import cli

DEPLOY_ARGV = ["deploy", "deploy/modal_vllm.py"]
PIN = "modal client version: 1.6.2\n"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr("mailroom_sandbox.paths.dotenv_files", lambda: [])
    for name in ("MODAL_WORKSPACE", "MODAL_VLLM_APP_NAME", "VLLM_BASE_URL", "MODAL_VLLM_MODEL", "MODAL_VLLM_GPU"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("mailroom_sandbox.services.modal_cli.VERIFY_DELAY", 0.0)


def _modal(fake_bin, **kw):
    kw.setdefault("rules", [{"prefix": ["--version"], "stdout": PIN}])
    return fake_bin.add("modal", **kw)


def _apps(*rows):
    return {"prefix": ["app", "list"], "stdout": json.dumps(list(rows))}


# --------------------------------------------------------------------------- guards


@pytest.mark.parametrize("sub", [["deploy"], ["prewarm"], ["status"], ["stop"], ["logs"]])
def test_every_command_names_the_install_hint_when_modal_is_missing(fake_bin, capsys, sub):
    assert cli.main(["modal", *sub]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and "`modal` not found" in err and ".[deploy]" in err
    assert "Traceback" not in err


def test_deploy_dry_run_prints_the_argv_and_runs_nothing(fake_bin, capsys):
    assert cli.main(["modal", "deploy", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "modal deploy deploy/modal_vllm.py" in out
    assert "dry-run" in out
    assert fake_bin.calls() == []


def test_dry_run_needs_no_modal_binary(fake_bin):
    assert cli.main(["modal", "prewarm", "--dry-run"]) == 0
    assert fake_bin.calls() == []


# --------------------------------------------------------------------------- deploy / prewarm


def test_deploy_runs_modal_deploy_and_prints_the_endpoint_exports(fake_bin, capsys, monkeypatch):
    _modal(fake_bin, stdout="Created web function serve => https://ws--sandbox-vllm-serve.modal.run\n")
    monkeypatch.setenv("MODAL_WORKSPACE", "ws")
    assert cli.main(["modal", "deploy"]) == 0
    out = capsys.readouterr().out
    assert fake_bin.calls("modal")[-1] == DEPLOY_ARGV
    assert "export VLLM_BASE_URL=https://ws--sandbox-vllm-serve.modal.run/v1" in out
    assert "VLLM_API_KEY" in out
    assert "sandbox modal stop" in out  # the next step is always teardown


def test_deploy_without_a_workspace_tells_the_operator_to_copy_the_printed_url(fake_bin, capsys):
    _modal(fake_bin)
    assert cli.main(["modal", "deploy"]) == 0
    out = capsys.readouterr().out
    assert "MODAL_WORKSPACE" in out and "export VLLM_BASE_URL=" in out


def test_deploy_failure_is_one_error_line_with_the_exit_code(fake_bin, capsys):
    _modal(fake_bin, rules=[{"prefix": ["--version"], "stdout": PIN}, {"prefix": ["deploy"], "rc": 2, "stderr": "auth\n"}])
    assert cli.main(["modal", "deploy"]) == 1
    err = capsys.readouterr().err
    assert "error: " in err and "rc=2" in err


def test_deploy_injects_the_matrix_row_for_the_chosen_model(fake_bin, capsys):
    assert cli.main(["modal", "deploy", "--model", "Qwen/Qwen3-8B-AWQ", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "MODAL_VLLM_MODEL=Qwen/Qwen3-8B-AWQ" in out
    assert "MODAL_VLLM_QUANTIZATION=awq" in out
    assert "MODAL_VLLM_GPU=L4" in out


def test_deploy_passes_the_matrix_env_to_the_child_process(fake_bin, monkeypatch):
    _modal(fake_bin)
    monkeypatch.setenv("MODAL_WORKSPACE", "ws")
    assert cli.main(["modal", "deploy", "--model", "Qwen/Qwen3-8B-AWQ", "--gpu", "A100-40GB:2"]) == 0
    env = fake_bin.envs("modal")[-1]
    assert env["MODAL_VLLM_MODEL"] == "Qwen/Qwen3-8B-AWQ"
    assert env["MODAL_VLLM_GPU"] == "A100-40GB:2"
    assert env["MODAL_VLLM_TP_SIZE"] == "2"


def test_deploy_rejects_a_model_missing_from_the_matrix_without_a_traceback(fake_bin, capsys):
    assert cli.main(["modal", "deploy", "--model", "nope/not-a-model", "--dry-run"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and "nope/not-a-model" in err and "Traceback" not in err


def test_an_sdk_version_other_than_the_pin_warns_but_still_runs(fake_bin, capsys):
    _modal(fake_bin, rules=[{"prefix": ["--version"], "stdout": "modal client version: 1.5.0\n"}])
    assert cli.main(["modal", "deploy"]) == 0
    err = capsys.readouterr().err
    assert "1.5.0" in err and "1.6.2" in err
    assert fake_bin.calls("modal")[-1] == DEPLOY_ARGV


def test_publish_image_dry_run_names_the_image_and_builds_nothing(fake_bin, capsys, monkeypatch):
    monkeypatch.setenv("MODAL_PROFILE", "jjburleson")
    assert cli.main(["modal", "publish-image", "--tag", "v0.30.0", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "publish_modal_image.py" in out and "sandbox-vllm:v0.30.0" in out and "jjburleson" in out


def test_publish_image_refuses_a_moving_tag(fake_bin, capsys):
    assert cli.main(["modal", "publish-image", "--tag", "latest", "--dry-run"]) != 0
    assert "never latest" in capsys.readouterr().err


def test_deploy_named_image_passes_the_switch_to_the_app(fake_bin, capsys):
    assert cli.main(["modal", "deploy", "--named-image", "--dry-run"]) == 0
    assert "MODAL_VLLM_USE_NAMED_IMAGE=1" in capsys.readouterr().out


def test_prewarm_runs_the_download_entrypoint_and_points_to_deploy(fake_bin, capsys):
    _modal(fake_bin)
    assert cli.main(["modal", "prewarm"]) == 0
    assert fake_bin.calls("modal")[-1] == ["run", "deploy/modal_vllm.py::download_model"]
    assert "sandbox modal deploy" in capsys.readouterr().out


# --------------------------------------------------------------------------- status


@pytest.mark.parametrize(
    "payload",
    [
        [{"description": "sandbox-vllm", "state": "deployed"}, {"description": "other", "state": "deployed"}],
        [{"Description": "sandbox-vllm", "State": "deployed"}],
        [{"name": "sandbox-vllm", "state": "deployed"}],
        {"apps": [{"description": "sandbox-vllm", "state": "deployed"}]},
    ],
    ids=["snake", "title-case", "name-key", "wrapped"],
)
def test_status_tolerates_the_shapes_modal_app_list_json_can_take(fake_bin, capsys, payload):
    _modal(fake_bin, rules=[{"prefix": ["--version"], "stdout": PIN}, {"prefix": ["app", "list"], "stdout": json.dumps(payload)}])
    assert cli.main(["modal", "status", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    by_name = {row["name"]: row for row in report["apps"]}
    assert by_name["sandbox-vllm"]["deployed"] is True
    assert by_name["sandbox-job"]["deployed"] is False
    assert "other" not in by_name  # only the sandbox's own apps are reported


def test_status_matches_app_names_exactly(fake_bin, capsys):
    rows = [{"description": "sandbox-vllm-a", "state": "deployed"}]
    _modal(fake_bin, rules=[{"prefix": ["--version"], "stdout": PIN}, _apps(*rows)])
    assert cli.main(["modal", "status", "--json"]) == 0
    by_name = {r["name"]: r for r in json.loads(capsys.readouterr().out)["apps"]}
    assert by_name["sandbox-vllm"]["deployed"] is False  # a concurrent fleet is not the default app


def test_status_reports_a_scoped_app_this_shell_does_not_name(fake_bin, capsys):
    rows = [
        {"description": "sandbox-vllm-reviewer", "state": "deployed", "tasks": "1"},
        {"description": "sandbox-vllm-old", "state": "stopped"},
        {"description": "mailroom-ml-eval", "state": "deployed"},
    ]
    _modal(fake_bin, rules=[{"prefix": ["--version"], "stdout": PIN}, _apps(*rows)])
    assert cli.main(["modal", "status", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["any_deployed"] is True
    assert [row["name"] for row in report["apps"]] == ["sandbox-vllm", "sandbox-job", "sandbox-vllm-reviewer"]
    assert cli.main(["modal", "status"]) == 0
    assert "sandbox modal stop --app sandbox-vllm-reviewer" in capsys.readouterr().out


def test_cli_runs_its_own_venv_tools_when_the_venv_is_not_activated(monkeypatch, tmp_path):
    import os
    import sys

    from mailroom_sandbox import prefer_own_venv_tools

    own_bin = str(tmp_path / "venv" / "bin")
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "venv"))
    monkeypatch.setattr(sys, "base_prefix", "/usr/local")
    monkeypatch.setattr(sys, "executable", own_bin + "/python")
    monkeypatch.setenv("PATH", os.pathsep.join(["/opt/homebrew/bin", own_bin]))
    prefer_own_venv_tools()
    assert os.environ["PATH"].split(os.pathsep) == [own_bin, "/opt/homebrew/bin"]

    monkeypatch.setattr(sys, "base_prefix", sys.prefix)  # outside a venv PATH is the operator's
    monkeypatch.setenv("PATH", "/opt/homebrew/bin")
    prefer_own_venv_tools()
    assert os.environ["PATH"] == "/opt/homebrew/bin"


def test_status_text_marks_a_warm_app_as_billing(fake_bin, capsys):
    _modal(fake_bin, rules=[{"prefix": ["--version"], "stdout": PIN}, _apps({"description": "sandbox-vllm", "state": "deployed"})])
    assert cli.main(["modal", "status"]) == 0
    out = capsys.readouterr().out
    assert "sandbox-vllm" in out and "deployed" in out and "sandbox modal stop" in out


@pytest.mark.parametrize(
    ("tasks", "shown", "billing"),
    [("0", "containers=0", "not billing now"), ("2", "containers=2", "bills while containers are warm")],
)
def test_status_separates_an_idle_deployment_from_a_billing_one(fake_bin, capsys, tasks, shown, billing):
    row = {"description": "sandbox-vllm", "state": "deployed", "tasks": tasks}
    _modal(fake_bin, rules=[{"prefix": ["--version"], "stdout": PIN}, _apps(row)])
    assert cli.main(["modal", "status"]) == 0
    out = capsys.readouterr().out
    assert shown in out and billing in out
    assert cli.main(["modal", "status", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["apps"][0]["tasks"] == int(tasks)


def test_status_reports_unparseable_output_as_an_error(fake_bin, capsys):
    _modal(fake_bin, rules=[{"prefix": ["--version"], "stdout": PIN}, {"prefix": ["app", "list"], "stdout": "not json at all"}])
    assert cli.main(["modal", "status"]) == 1
    assert "could not parse" in capsys.readouterr().err


# --------------------------------------------------------------------------- stop


def test_stop_is_a_noop_when_the_app_is_not_deployed(fake_bin, capsys):
    _modal(fake_bin, rules=[{"prefix": ["--version"], "stdout": PIN}, _apps()])
    assert cli.main(["modal", "stop"]) == 0
    assert "already stopped" in capsys.readouterr().out
    assert ["app", "stop"] not in [c[:2] for c in fake_bin.calls("modal")]


def test_stop_stops_then_verifies_the_app_is_gone(fake_bin, capsys):
    deployed = json.dumps([{"description": "sandbox-vllm", "state": "deployed"}])
    _modal(
        fake_bin,
        rules=[
            {"prefix": ["--version"], "stdout": PIN},
            {"prefix": ["app", "stop"], "stdout": "stopped\n"},
            # the first listing (pre-check) says deployed; every later one says gone
            {"prefix": ["app", "list"], "seq": [{"stdout": deployed}, {"stdout": "[]"}]},
        ],
    )
    assert cli.main(["modal", "stop"]) == 0
    out = capsys.readouterr().out
    assert "stopped" in out and "verified" in out
    stop_calls = [c for c in fake_bin.calls("modal") if c[:2] == ["app", "stop"]]
    assert stop_calls == [["app", "stop", "sandbox-vllm", "--yes"]]


def test_stop_treats_app_not_found_as_success(fake_bin, capsys):
    deployed = _apps({"description": "sandbox-vllm", "state": "deployed"})
    _modal(
        fake_bin,
        rules=[
            {"prefix": ["--version"], "stdout": PIN},
            {"prefix": ["app", "stop"], "rc": 1, "stderr": "Could not find a deployed app named 'sandbox-vllm'\n"},
            deployed,
        ],
    )
    # the listing keeps saying deployed, but the stop said there is nothing to stop
    assert cli.main(["modal", "stop", "--no-verify"]) == 0
    assert "already stopped" in capsys.readouterr().out


def test_stop_fails_loudly_when_the_stop_command_fails_for_another_reason(fake_bin, capsys):
    _modal(
        fake_bin,
        rules=[
            {"prefix": ["--version"], "stdout": PIN},
            {"prefix": ["app", "stop"], "rc": 1, "stderr": "token expired\n"},
            _apps({"description": "sandbox-vllm", "state": "deployed"}),
        ],
    )
    assert cli.main(["modal", "stop"]) == 1
    assert "token expired" in capsys.readouterr().err


def test_stop_fails_when_the_app_is_still_deployed_after_verification(fake_bin, capsys):
    _modal(
        fake_bin,
        rules=[
            {"prefix": ["--version"], "stdout": PIN},
            {"prefix": ["app", "stop"], "stdout": "ok\n"},
            _apps({"description": "sandbox-vllm", "state": "deployed"}),
        ],
    )
    assert cli.main(["modal", "stop"]) == 1
    assert "still" in capsys.readouterr().err


def test_stop_targets_the_scoped_app_name(fake_bin, monkeypatch):
    monkeypatch.setenv("MODAL_VLLM_APP_NAME", "sandbox-vllm-a")
    _modal(fake_bin, rules=[{"prefix": ["--version"], "stdout": PIN}, _apps({"description": "sandbox-vllm-a", "state": "deployed"})])
    cli.main(["modal", "stop", "--no-verify"])
    assert ["app", "stop", "sandbox-vllm-a", "--yes"] in fake_bin.calls("modal")


def test_stop_dry_run_does_nothing(fake_bin, capsys):
    assert cli.main(["modal", "stop", "--dry-run"]) == 0
    assert "modal app stop sandbox-vllm --yes" in capsys.readouterr().out
    assert fake_bin.calls() == []


# --------------------------------------------------------------------------- url / logs / raw


def test_url_prints_the_gateway_for_the_workspace(monkeypatch, capsys):
    monkeypatch.setenv("MODAL_WORKSPACE", "ws")
    assert cli.main(["modal", "url"]) == 0
    assert capsys.readouterr().out.strip() == "https://ws--sandbox-vllm-serve.modal.run/v1"


def test_url_follows_a_scoped_app_name(monkeypatch, capsys):
    monkeypatch.setenv("MODAL_WORKSPACE", "ws")
    monkeypatch.setenv("MODAL_VLLM_APP_NAME", "sandbox-vllm-a")
    cli.main(["modal", "url"])
    assert "ws--sandbox-vllm-a-serve.modal.run" in capsys.readouterr().out


def test_url_without_a_workspace_is_an_error_never_localhost(capsys):
    assert cli.main(["modal", "url"]) == 1
    err = capsys.readouterr().err
    assert "MODAL_WORKSPACE" in err and "localhost" not in err


def test_url_json(monkeypatch, capsys):
    monkeypatch.setenv("MODAL_WORKSPACE", "ws")
    assert cli.main(["modal", "url", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["base_url"].endswith("/v1")


@pytest.mark.parametrize(
    ("args", "argv"),
    [
        (["logs"], ["modal", "app", "logs", "sandbox-vllm"]),
        (["logs", "--follow"], ["modal", "app", "logs", "-f", "sandbox-vllm"]),
        (["logs", "--app", "sandbox-job"], ["modal", "app", "logs", "sandbox-job"]),
    ],
)
def test_logs_dry_run_prints_the_modal_logs_argv(capsys, args, argv):
    assert cli.main(["modal", *args, "--dry-run"]) == 0
    assert " ".join(argv) in capsys.readouterr().out


def test_raw_passes_arguments_through_and_mirrors_the_exit_code(fake_bin):
    _modal(fake_bin, rc=3)
    assert cli.main(["modal", "raw", "--", "volume", "ls"]) == 3
    assert fake_bin.calls("modal") == [["volume", "ls"]]


def test_raw_without_modal_is_the_guarded_error(fake_bin, capsys):
    assert cli.main(["modal", "raw", "--", "volume", "ls"]) == 1
    assert "`modal` not found" in capsys.readouterr().err


def test_bare_modal_group_prints_usage(capsys):
    assert cli.main(["modal"]) == 0
    out = capsys.readouterr().out
    assert "deploy" in out and "stop" in out and "status" in out


def test_status_recommends_teardown_for_each_deployed_app(fake_bin, capsys):
    _modal(fake_bin, rules=[{'prefix': ['--version'], 'stdout': PIN}, _apps(
        {'description': 'sandbox-vllm', 'state': 'deployed'},
        {'description': 'sandbox-job', 'state': 'deployed'},
    )])
    assert cli.main(['modal', 'status']) == 0
    out = capsys.readouterr().out
    assert 'sandbox modal stop --app sandbox-vllm' in out
    assert 'sandbox modal stop --app sandbox-job' in out


def test_status_counts_a_live_ephemeral_app_as_billing(fake_bin, capsys):
    row = {"description": "sandbox-vllm-probe", "state": "ephemeral", "tasks": "1"}
    _modal(fake_bin, rules=[{"prefix": ["--version"], "stdout": PIN}, _apps(row)])
    assert cli.main(["modal", "status", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["any_deployed"] is True
    assert cli.main(["modal", "status"]) == 0
    assert "sandbox modal stop --app sandbox-vllm-probe" in capsys.readouterr().out


def test_prefer_own_venv_tools_uses_the_default_path_when_path_is_unset(tmp_path, monkeypatch):
    from mailroom_sandbox import prefer_own_venv_tools

    own_bin = str(tmp_path / "venv" / "bin")
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "venv"))
    monkeypatch.setattr(sys, "base_prefix", "/usr/local")
    monkeypatch.setattr(sys, "executable", own_bin + "/python")
    monkeypatch.delenv("PATH")
    prefer_own_venv_tools()
    assert os.environ["PATH"] == os.pathsep.join([own_bin, os.defpath])


def test_importing_the_package_leaves_path_alone():
    code = "import os, mailroom_sandbox; print(os.environ['PATH'])"
    env = {**os.environ, "PATH": "/custom/bin"}
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True).stdout
    assert out.strip() == "/custom/bin"
