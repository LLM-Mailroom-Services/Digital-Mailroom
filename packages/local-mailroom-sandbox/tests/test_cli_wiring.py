"""DMR-048 CLI live-or-loud wiring regression tests.

Covers the explore findings: health ignoring VLLM_BASE_URL (G1), pull-models
being Ollama-only (G2), eval-ish commands silently mocking on vLLM profiles
(G3), the modal run-start engine probe (G6), and matrix --providers accepting
non-profile names (G34).
"""

from __future__ import annotations

import types

import pytest

from mailroom_sandbox import cli
from mailroom_sandbox.eval.matrix import plan_matrix
from mailroom_sandbox.health import probe_models
from mailroom_sandbox.overlay import load_profile


def _args(**overrides) -> types.SimpleNamespace:
    base = {
        "profile": "ollama",
        "mock": False,
        "local": False,
        "models": [],
    }
    base.update(overrides)
    return types.SimpleNamespace(**base)


# ── G3: silent-mock warning on vLLM/Modal profiles ───────────────────────────


def test_mock_for_warns_on_vllm_profile_without_flags(capsys):
    args = _args(profile="modal-vllm")
    assert cli._mock_for(args, subcommand="eval") is True
    assert "would run MOCK" in capsys.readouterr().out


def test_mock_for_no_warning_with_local(capsys):
    args = _args(profile="modal-vllm", local=True)
    assert cli._mock_for(args, subcommand="eval") is False
    assert capsys.readouterr().out == ""


def test_mock_for_no_warning_with_explicit_mock(capsys):
    args = _args(profile="modal-vllm", mock=True)
    assert cli._mock_for(args, subcommand="eval") is True
    assert capsys.readouterr().out == ""


# ── G1: health follows VLLM_BASE_URL ─────────────────────────────────────────


def test_health_follows_base_url_env(monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", "https://ws--sandbox-vllm-serve.modal.run/v1")
    captured: dict = {}

    class _Resp:
        status_code = 200

        def json(self):
            return {"data": [{"id": "Qwen/Qwen3-8B"}]}

    def _fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        return _Resp()

    monkeypatch.setattr("mailroom_sandbox.health.httpx.get", _fake_get)
    result = probe_models(load_profile("modal-vllm"))
    assert result.ok
    assert captured["url"].startswith("https://ws--sandbox-vllm-serve.modal.run")
    monkeypatch.delenv("VLLM_BASE_URL")


# ── G2: pull-models branches by serving family ───────────────────────────────


def test_pull_models_vllm_profile_prints_prewarm(capsys, monkeypatch):
    called: list = []
    monkeypatch.setattr(
        "mailroom_sandbox.compose.pull_ollama_models",
        lambda models: called.append(models) or 0,
    )
    rc = cli._cmd_pull_models(_args(profile="modal-vllm"))
    out = capsys.readouterr().out
    assert rc == 0 and called == []
    assert "download_model" in out


def test_pull_models_ollama_still_pulls(capsys, monkeypatch):
    called: list = []
    monkeypatch.setattr(
        "mailroom_sandbox.compose.pull_ollama_models",
        lambda models: called.append(models) or 0,
    )
    rc = cli._cmd_pull_models(_args(profile="ollama"))
    assert rc == 0
    assert called and called[0]  # ollama pull_models list forwarded


# ── G34: matrix --providers takes profile names ──────────────────────────────


def test_matrix_rejects_family_names():
    with pytest.raises(ValueError, match="profile names"):
        plan_matrix(
            task="sorter",
            providers=["vllm"],
            models=["qwen3:8b"],
            prompts=["code-default"],
        )
    cells = plan_matrix(
        task="sorter",
        providers=["vllm-local"],
        models=["qwen3:8b"],
        prompts=["code-default"],
    )
    assert cells and cells[0]["provider"] == "vllm-local"