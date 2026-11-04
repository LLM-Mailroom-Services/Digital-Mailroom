"""The sandbox serves through Modal vLLM unless the operator opts out."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

from mailroom_sandbox.cli import build_parser
from mailroom_sandbox.health import _effective_base_url, health_check, missing_modal_endpoint
from mailroom_sandbox.overlay import load_profile
from mailroom_sandbox.providers import DEFAULT_PROFILE, default_profile, modal_gateway_url


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch):
    """A developer's real `.env` must not change what the defaults resolve to."""
    monkeypatch.setattr("mailroom_sandbox.paths.dotenv_files", lambda: [])


def test_default_profile_constant_is_modal_vllm():
    assert DEFAULT_PROFILE == "modal-vllm"
    assert load_profile(DEFAULT_PROFILE)["provider"] == "vllm"


def test_default_profile_honors_env_opt_out(monkeypatch):
    monkeypatch.delenv("SANDBOX_PROFILE", raising=False)
    assert default_profile() == "modal-vllm"

    monkeypatch.setenv("SANDBOX_PROFILE", "ollama")
    assert default_profile() == "ollama"


def test_cli_parser_uses_the_default_profile(monkeypatch):
    monkeypatch.delenv("SANDBOX_PROFILE", raising=False)
    parser = build_parser()
    assert parser.parse_args(["health"]).profile == "modal-vllm"
    assert parser.parse_args(["health", "--profile", "ollama"]).profile == "ollama"


def test_modal_profile_has_no_silent_localhost_health_probe(monkeypatch):
    """Unset VLLM_BASE_URL must not be reported as a healthy local server."""
    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    monkeypatch.delenv("MODAL_WORKSPACE", raising=False)
    assert _effective_base_url(load_profile("modal-vllm")) is None
    assert missing_modal_endpoint(load_profile("modal-vllm")) is True

    result = health_check("modal-vllm")
    assert result["ok"] is False
    assert "VLLM_BASE_URL" in result["models"]["detail"]
    assert "localhost" not in result["models"]["url"]

    monkeypatch.setenv("MODAL_WORKSPACE", "exios66")
    assert (
        _effective_base_url(load_profile("modal-vllm"))
        == "https://exios66--sandbox-vllm-serve.modal.run/v1"
    )
    assert missing_modal_endpoint(load_profile("modal-vllm")) is False
    assert modal_gateway_url(load_profile("ollama")) is None


def test_dotenv_profile_opt_out_survives_the_default_flip(monkeypatch, tmp_path):
    """A pre-existing `.env` saying SANDBOX_PROFILE=ollama must keep winning.

    The CLI resolves its default before any `.env` is loaded, so `default_profile()`
    reads the file itself (real env still wins; `os.environ` is left untouched).
    """
    env_file = tmp_path / ".env"
    env_file.write_text("SANDBOX_PROFILE=ollama   # offline opt-out\n", encoding="utf-8")
    monkeypatch.delenv("SANDBOX_SKIP_DOTENV", raising=False)
    monkeypatch.setattr("mailroom_sandbox.paths.dotenv_files", lambda: [env_file])
    monkeypatch.delenv("SANDBOX_PROFILE", raising=False)

    assert default_profile() == "ollama"
    assert build_parser().parse_args(["health"]).profile == "ollama"
    assert "SANDBOX_PROFILE" not in os.environ

    monkeypatch.setenv("SANDBOX_PROFILE", "vllm-local")
    assert default_profile() == "vllm-local"
    assert build_parser().parse_args(["health", "--profile", "ollama"]).profile == "ollama"


def test_dotenv_without_a_profile_falls_back_to_modal(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OBSERVABILITY_PROVIDER=langfuse\nSANDBOX_PROFILE=\n", encoding="utf-8")
    monkeypatch.delenv("SANDBOX_SKIP_DOTENV", raising=False)
    monkeypatch.setattr("mailroom_sandbox.paths.dotenv_files", lambda: [env_file])
    monkeypatch.delenv("SANDBOX_PROFILE", raising=False)
    assert default_profile() == "modal-vllm"


def _isolated_environ(monkeypatch):
    """Let `apply_profile_env` mutate a private copy of the environment."""
    env = {k: v for k, v in os.environ.items() if k not in {"VLLM_BASE_URL", "MODAL_WORKSPACE"}}
    monkeypatch.setattr(os, "environ", env)
    return env


def test_modal_activation_never_seeds_the_localhost_fallback(monkeypatch):
    """An unset Modal URL must stay unset so the pipeline's live-or-loud warning fires."""
    from mailroom_sandbox.runtime import apply_profile_env

    env = _isolated_environ(monkeypatch)
    apply_profile_env(load_profile("modal-vllm"))
    assert "VLLM_BASE_URL" not in env
    assert env["DEFAULT_PROVIDER"] == "vllm"


def test_modal_activation_prefers_exported_url_then_workspace_gateway(monkeypatch):
    from mailroom_sandbox.runtime import apply_profile_env

    env = _isolated_environ(monkeypatch)
    env["MODAL_WORKSPACE"] = "ws1"
    apply_profile_env(load_profile("modal-vllm"))
    assert env["VLLM_BASE_URL"] == "https://ws1--sandbox-vllm-serve.modal.run/v1"

    env = _isolated_environ(monkeypatch)
    env.update(MODAL_WORKSPACE="ws1", VLLM_BASE_URL="https://exported.example/v1")
    apply_profile_env(load_profile("modal-vllm"))
    assert env["VLLM_BASE_URL"] == "https://exported.example/v1"


def test_other_profiles_still_seed_their_static_base_url(monkeypatch):
    from mailroom_sandbox.providers import endpoints_for
    from mailroom_sandbox.runtime import apply_profile_env

    env = _isolated_environ(monkeypatch)
    profile = load_profile("vllm-local")
    apply_profile_env(profile)
    assert env["VLLM_BASE_URL"] == endpoints_for(profile).base_url


# ── provenance: nothing may still assume the old Ollama default ──────────────


def test_trace_tags_name_the_profile_that_is_actually_the_default(monkeypatch):
    from mailroom_sandbox.eval.tracing import default_tags

    monkeypatch.delenv("SANDBOX_PROFILE", raising=False)
    assert "modal-vllm" in default_tags() and "ollama" not in default_tags()
    monkeypatch.setenv("SANDBOX_PROFILE", "ollama")
    assert "ollama" in default_tags() and "modal-vllm" not in default_tags()


def test_lock_without_a_profile_falls_back_to_the_default_profile(monkeypatch):
    """Same fallback as `runtime.activate`, so a record never names a profile that did not run."""
    from mailroom_sandbox.job.runner import _lock_profile

    monkeypatch.delenv("SANDBOX_PROFILE", raising=False)
    assert _lock_profile(SimpleNamespace(read_lock=lambda: None)) == "modal-vllm"
    assert _lock_profile(SimpleNamespace(read_lock=lambda: {})) == "modal-vllm"
    assert _lock_profile(SimpleNamespace(read_lock=lambda: {"profile": "ollama"})) == "ollama"
    monkeypatch.setenv("SANDBOX_PROFILE", "vllm-local")
    assert _lock_profile(SimpleNamespace(read_lock=lambda: {})) == "vllm-local"


def test_dotenv_files_lists_existing_files_in_precedence_order(monkeypatch, tmp_path):
    from mailroom_sandbox import paths

    monkeypatch.undo()  # the autouse fixture stubs dotenv_files; this test needs the real one
    monkeypatch.setenv("SANDBOX_ROOT", str(tmp_path))
    assert paths.dotenv_files() == []
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / ".env").write_text("A=1\n", encoding="utf-8")
    assert paths.dotenv_files() == [tmp_path.resolve() / "config" / ".env"]
    (tmp_path / ".env").write_text("A=2\n", encoding="utf-8")
    assert paths.dotenv_files() == [tmp_path.resolve() / ".env", tmp_path.resolve() / "config" / ".env"]


def test_load_dotenv_never_overrides_the_real_environment(monkeypatch, tmp_path):
    from mailroom_sandbox import runtime

    first, second = tmp_path / "a.env", tmp_path / "b.env"
    first.write_text("FROM_FIRST=1\nSHARED=first\nPRESET=file\n", encoding="utf-8")
    second.write_text("FROM_SECOND=1\nSHARED=second\n", encoding="utf-8")
    env = {"PRESET": "real"}
    monkeypatch.setattr(os, "environ", env)
    monkeypatch.delenv("SANDBOX_SKIP_DOTENV", raising=False)
    monkeypatch.setattr("mailroom_sandbox.runtime.dotenv_files", lambda: [first, second])
    runtime._load_dotenv()
    assert env == {"PRESET": "real", "FROM_FIRST": "1", "SHARED": "first", "FROM_SECOND": "1"}


def test_modal_gateway_url_honours_the_app_name_override(monkeypatch):
    monkeypatch.setenv("MODAL_WORKSPACE", "ws1")
    profile = load_profile("modal-vllm")
    monkeypatch.delenv("MODAL_VLLM_APP_NAME", raising=False)
    assert modal_gateway_url(profile) == "https://ws1--sandbox-vllm-serve.modal.run/v1"
    monkeypatch.setenv("MODAL_VLLM_APP_NAME", "sandbox-vllm-b")
    assert modal_gateway_url(profile) == "https://ws1--sandbox-vllm-b-serve.modal.run/v1"
    monkeypatch.setenv("MODAL_VLLM_APP_NAME", "  ")
    assert modal_gateway_url(profile) == "https://ws1--sandbox-vllm-serve.modal.run/v1"
    monkeypatch.setenv("MODAL_WORKSPACE", "  ")
    assert modal_gateway_url(profile) is None


# ── CLI surface of the default flip ──────────────────────────────────────────


def test_profiles_marks_exactly_the_active_default(monkeypatch, capsys):
    from mailroom_sandbox import cli

    monkeypatch.delenv("SANDBOX_PROFILE", raising=False)
    assert cli.main(["profiles"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [ln for ln in lines if "(default)" in ln] == ["modal-vllm  (default)"]
    assert "ollama" in lines

    monkeypatch.setenv("SANDBOX_PROFILE", "ollama")
    assert cli.main(["profiles"]) == 0
    assert [ln for ln in capsys.readouterr().out.splitlines() if "(default)" in ln] == ["ollama  (default)"]


def test_up_explains_the_langfuse_only_compose_surface(monkeypatch, capsys):
    from mailroom_sandbox import cli

    started = []
    monkeypatch.setattr("mailroom_sandbox.compose.run_compose", lambda profiles, *a, **k: started.append(list(profiles)))
    monkeypatch.delenv("SANDBOX_PROFILE", raising=False)

    assert cli.main(["up"]) == 0
    assert "Langfuse only" in capsys.readouterr().out and started[-1] == ["langfuse"]

    assert cli.main(["up", "--compose-profile", "ollama"]) == 0  # explicit list: no Modal hint
    assert "Langfuse only" not in capsys.readouterr().out and started[-1] == ["ollama"]

    assert cli.main(["up", "--profile", "ollama"]) == 0
    assert "Langfuse only" not in capsys.readouterr().out and "ollama" in started[-1]


def _stub_probes(monkeypatch, ok: bool):
    from mailroom_sandbox.health import ProbeResult

    probe = lambda profile, **kw: ProbeResult(ok, profile.get("name", "?"), "stub://", "stub")  # noqa: E731
    monkeypatch.setattr("mailroom_sandbox.health.probe_models", probe)
    monkeypatch.setattr("mailroom_sandbox.health.probe_chat", probe)
    monkeypatch.setattr("mailroom_sandbox.runtime.load_env_file", lambda: None)


def test_health_without_a_modal_endpoint_hints_and_exits_one(monkeypatch, capsys):
    from mailroom_sandbox import cli

    _stub_probes(monkeypatch, ok=True)  # even a reachable localhost must not count as the Modal endpoint
    for name in ("VLLM_BASE_URL", "MODAL_WORKSPACE", "SANDBOX_PROFILE"):
        monkeypatch.delenv(name, raising=False)
    assert cli.main(["health"]) == 1
    out = capsys.readouterr()
    assert "hint: modal-vllm has no VLLM_BASE_URL" in out.err
    assert json.loads(out.out)["ok"] is False


def test_health_exit_code_ignores_langfuse_and_phoenix(monkeypatch, capsys):
    """Provider healthy => exit 0, even though the sink probes are reported separately."""
    from mailroom_sandbox import cli
    from mailroom_sandbox.health import ProbeResult

    monkeypatch.setattr("mailroom_sandbox.runtime.load_env_file", lambda: None)
    monkeypatch.setenv("MODAL_WORKSPACE", "ws1")
    monkeypatch.delenv("VLLM_BASE_URL", raising=False)

    def probe(profile, **kw):
        name = profile.get("name", "?")
        return ProbeResult(name not in {"langfuse", "phoenix"}, name, "stub://", "stub")

    monkeypatch.setattr("mailroom_sandbox.health.probe_models", probe)
    monkeypatch.setattr("mailroom_sandbox.health.probe_chat", probe)
    assert cli.main(["health"]) == 0
    out = capsys.readouterr()
    report = json.loads(out.out)
    assert report["ok"] is True and report["langfuse"]["ok"] is False and report["phoenix"]["ok"] is False
    assert "hint:" not in out.err


def test_phased_redeploy_script_exports_the_bearer_after_defining_it():
    from mailroom_sandbox.job import runbooks as rb

    runbook = {"id": "t", "serving": "baseline", "phases": [{"id": "p1", "configs": ["config/runs/x.yaml"]}]}
    lines = rb._phase_shell(runbook, deploy="modal deploy deploy/modal_vllm.py", preflight_force="", job_mode="endpoint")
    token = next(i for i, ln in enumerate(lines) if "export MODAL_VLLM_API_TOKEN=" in ln)
    key = next(i for i, ln in enumerate(lines) if ln.startswith('export VLLM_API_KEY="$MODAL_VLLM_API_TOKEN"'))
    cutover = next(i for i, ln in enumerate(lines) if ln.startswith("sandbox cutover"))
    assert token < key < cutover


def test_api_key_export_is_a_comment_when_the_script_does_not_deploy():
    from mailroom_sandbox.job.runbooks import _api_key_export

    assert _api_key_export(deploys=True).startswith('export VLLM_API_KEY="$MODAL_VLLM_API_TOKEN"')
    assert _api_key_export(deploys=False).startswith("# export VLLM_API_KEY=")
