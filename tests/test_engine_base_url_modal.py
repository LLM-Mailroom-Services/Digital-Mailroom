"""`engine_base_url` must resolve the real Modal gateway for the default `modal-vllm` profile.

The `modal-vllm` profile carries a localhost `base_url` only as a parity value for
`endpoints_for()` and `sandbox profiles` (see `config/profiles/modal-vllm.yaml`).
`health` and activation already ignore it; the run-spec resolver used by
`run preflight --live`, `run start` and `run scrape-metrics` must too, otherwise a
Modal run probes whatever listens on `localhost:8000`.
"""

from __future__ import annotations

import pytest

from mailroom_sandbox.job.spec import EngineSpec, ModalSpec, RunSpec, engine_base_url
from mailroom_sandbox.overlay import load_profile


@pytest.fixture(autouse=True)
def _clean_endpoint_env(monkeypatch):
    """A developer's real `.env` or exported endpoint must not change the result."""
    monkeypatch.setattr("mailroom_sandbox.paths.dotenv_files", lambda: [])
    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    monkeypatch.delenv("MODAL_WORKSPACE", raising=False)


def _modal_spec(app: str = "sandbox-vllm", profile: str = "modal-vllm") -> RunSpec:
    return RunSpec(
        profile=profile,
        task="sorter",
        engine=EngineSpec(kind="modal-vllm", model="Qwen/Qwen3-8B", modal=ModalSpec(app=app)),
    )


def test_modal_profile_with_workspace_resolves_the_gateway_not_localhost(monkeypatch):
    """With only MODAL_WORKSPACE set, the default profile must not resolve to localhost."""
    monkeypatch.setenv("MODAL_WORKSPACE", "ws1")
    assert engine_base_url(_modal_spec()) == "https://ws1--sandbox-vllm-serve.modal.run"


def test_modal_profile_gateway_follows_the_run_spec_app_name(monkeypatch):
    """An app-scoped fleet (`engine.modal.app`) is addressed by its own gateway URL."""
    monkeypatch.setenv("MODAL_WORKSPACE", "ws1")
    assert engine_base_url(_modal_spec(app="sandbox-vllm-b")) == "https://ws1--sandbox-vllm-b-serve.modal.run"


@pytest.mark.parametrize("app_env,expected_app", [(None, "sandbox-vllm"), ("custom-app", "custom-app")])
def test_modal_spec_without_a_modal_block_uses_the_profile_app_name(monkeypatch, app_env, expected_app):
    """`engine.modal` is optional (explicit `modal: null`): a modal-vllm spec without it must resolve, not AttributeError."""
    monkeypatch.setenv("MODAL_WORKSPACE", "ws1")
    if app_env:
        monkeypatch.setenv("MODAL_VLLM_APP_NAME", app_env)
    else:
        monkeypatch.delenv("MODAL_VLLM_APP_NAME", raising=False)
    spec = RunSpec(profile="modal-vllm", task="sorter", engine=EngineSpec(kind="modal-vllm", model="Qwen/Qwen3-8B", modal=None))
    assert spec.engine.modal is None
    assert engine_base_url(spec) == f"https://ws1--{expected_app}-serve.modal.run"


def test_exported_endpoint_still_wins_over_the_workspace(monkeypatch):
    monkeypatch.setenv("MODAL_WORKSPACE", "ws1")
    monkeypatch.setenv("VLLM_BASE_URL", "https://exported.example/v1/")
    assert engine_base_url(_modal_spec()) == "https://exported.example/v1"


def test_modal_profile_without_any_endpoint_fails_loudly_instead_of_localhost():
    """No VLLM_BASE_URL and no MODAL_WORKSPACE: raise, never fall back to localhost."""
    with pytest.raises(ValueError, match="MODAL_WORKSPACE"):
        engine_base_url(_modal_spec())


def test_non_modal_profiles_keep_their_static_base_url():
    """The fix is scoped to the Modal profile: local profiles still use their own URL."""
    spec = RunSpec(
        profile="vllm-local",
        task="sorter",
        engine=EngineSpec(kind="vllm-local", model="Qwen/Qwen3-8B"),
    )
    expected = str(load_profile("vllm-local")["base_url"]).rstrip("/")
    assert engine_base_url(spec) == expected


@pytest.mark.parametrize('workspace', [' ws1 ', '\tws1\n'])
def test_workspace_is_trimmed(monkeypatch, workspace):
    monkeypatch.setenv('MODAL_WORKSPACE', workspace)
    assert engine_base_url(_modal_spec()) == 'https://ws1--sandbox-vllm-serve.modal.run'


def test_blank_workspace_is_unresolved(monkeypatch):
    monkeypatch.setenv('MODAL_WORKSPACE', '  ')
    with pytest.raises(ValueError, match='MODAL_WORKSPACE'):
        engine_base_url(_modal_spec())
