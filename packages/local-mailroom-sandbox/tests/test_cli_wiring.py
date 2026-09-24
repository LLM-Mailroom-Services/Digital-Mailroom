"""DMR-048 CLI live-or-loud wiring regression tests.

Covers the explore findings: health ignoring VLLM_BASE_URL (G1), pull-models
being Ollama-only (G2), eval-ish commands silently mocking on vLLM profiles
(G3), the modal run-start engine probe (G6), and matrix --providers accepting
non-profile names (G34).
"""

from __future__ import annotations

import subprocess
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


# ── DMR-056: datasets pull is live-or-loud (never a silent marker) ───────────


def test_datasets_pull_success_prints_rows_and_exit0(monkeypatch, capsys):
    from mailroom_sandbox.job.spec import FAMILY_HF_REVISION

    captured: dict = {}

    def fake_prepare(spec, dest):
        captured["spec"] = spec
        return {
            "rows": 7,
            "sha256": "a" * 64,
            "revision_resolved": "46a4d3c2",
            "metadata": {"source": "huggingface"},
        }

    monkeypatch.setattr("mailroom_sandbox.corpus.prepare_subset", fake_prepare)
    args = _args(
        dataset="Lucius-Morningstar/mailroom-dataset",
        max_rows=7,
        revision="",
        config="ground_truth",
        split="test",
    )
    assert cli._cmd_datasets_pull(args) == 0
    out = capsys.readouterr().out
    assert "pulled 7 row(s)" in out
    assert "sha256=aaaaaaaaaaaa" in out
    # DMR-056: the default revision is the pinned FAMILY_HF_REVISION snapshot —
    # a pull never floats to the Hub tip.
    assert captured["spec"].revision == FAMILY_HF_REVISION
    assert captured["spec"].config == "ground_truth"
    assert captured["spec"].limit == 7


def test_datasets_pull_zero_max_rows_is_full_corpus(monkeypatch, capsys):
    captured: dict = {}

    def fake_prepare(spec, dest):
        captured["spec"] = spec
        return {
            "rows": 3302,
            "sha256": "c" * 64,
            "revision_resolved": "46a4d3c2",
            "metadata": {"source": "huggingface"},
        }

    monkeypatch.setattr("mailroom_sandbox.corpus.prepare_subset", fake_prepare)
    args = _args(
        dataset="Lucius-Morningstar/mailroom-dataset",
        max_rows=0,
        revision="",
        config="ground_truth",
        split="all",
        per_class=0,
        sample_seed=42,
    )
    assert cli._cmd_datasets_pull(args) == 0
    assert captured["spec"].limit is None
    assert captured["spec"].split == "all"
    assert "pulled 3302 row(s)" in capsys.readouterr().out


def test_datasets_sample_missing_cache_is_exit1(capsys, tmp_path, monkeypatch):
    from mailroom_sandbox import datasets as ds

    monkeypatch.setattr(ds, "full_corpus_cache_path", lambda **k: tmp_path / "missing.jsonl")
    args = _args(per_class=20, sample_seed=42, classes="", source="", out="")
    assert cli._cmd_datasets_sample(args) == 1
    assert "full corpus cache missing" in capsys.readouterr().out


def test_datasets_pull_failure_is_exit1(monkeypatch, capsys):
    def boom(spec, dest):
        raise RuntimeError("network down")

    monkeypatch.setattr("mailroom_sandbox.corpus.prepare_subset", boom)
    args = _args(dataset="Lucius-Morningstar/mailroom-dataset", max_rows=5, revision="", config="ground_truth", split="test")
    assert cli._cmd_datasets_pull(args) == 1
    assert "error: RuntimeError: network down" in capsys.readouterr().out


def test_datasets_pull_zero_rows_refused(monkeypatch, capsys):
    def empty(spec, dest):
        return {"rows": 0, "sha256": "", "revision_resolved": None, "metadata": {}}

    monkeypatch.setattr("mailroom_sandbox.corpus.prepare_subset", empty)
    args = _args(dataset="Lucius-Morningstar/mailroom-dataset", max_rows=5, revision="", config="ground_truth", split="test")
    assert cli._cmd_datasets_pull(args) == 1
    assert "refusing to write an empty dataset" in capsys.readouterr().out


# ── DMR-056: prompts show validates + surfaces the registry pin ──────────────


def test_prompts_show_unknown_agent_exit2(capsys):
    args = _args(name="not_an_agent", variant=None, offline=False)
    assert cli._cmd_prompts_show(args) == 2
    assert "unknown agent" in capsys.readouterr().out


def test_prompts_show_sorter_surfaces_version_key(capsys):
    args = _args(name="sorter", variant=None, offline=True)
    assert cli._cmd_prompts_show(args) == 0
    out = capsys.readouterr().out
    assert "sorter_v14" in out  # the registry's pinned family-B key (DMR-056)


def test_prompts_show_variant_has_no_version_key(capsys):
    args = _args(name="sorter", variant="sorter_local_v0", offline=True)
    assert cli._cmd_prompts_show(args) == 0
    assert "version_key" not in capsys.readouterr().out


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


# ── DMR-058: docker/ollama/ssh failures degrade cleanly, not as tracebacks ───


def test_up_missing_docker_degrades_cleanly(mocker, capsys):
    from mailroom_sandbox.cli import main as cli_main

    exc = subprocess.CalledProcessError(1, ["docker", "compose", "up"], stderr=b"no daemon")
    mocker.patch("mailroom_sandbox.compose.run_compose", side_effect=exc)
    assert cli_main(["up"]) == 1
    out = capsys.readouterr().err
    assert "command failed" in out
    assert "no daemon" in out


def test_pull_models_missing_ollama_degrades_cleanly(mocker, capsys):
    from mailroom_sandbox.cli import main as cli_main

    mocker.patch("mailroom_sandbox.compose.pull_ollama_models", side_effect=FileNotFoundError("no ollama"))
    assert cli_main(["pull-models"]) == 1
    assert "command unavailable" in capsys.readouterr().err

# ── hub#56: -d/--detach default, phoenix health URL derivation ──────────────


def test_up_detach_defaults_to_foreground():
    """hub#56: `sandbox up` runs in the FOREGROUND by default (the old
    action='store_true', default=True made -d a permanent no-op)."""
    import argparse

    parser = cli.build_parser()
    args = parser.parse_args(["up"])
    assert args.detach is False, "default must be foreground"
    args_d = parser.parse_args(["up", "-d"])
    assert args_d.detach is True
    args_long = parser.parse_args(["up", "--detach"])
    assert args_long.detach is True


def test_phoenix_health_probe_follows_phoenix_endpoint(monkeypatch, capsys):
    """hub#56: _cmd_health derives the Phoenix healthz URL from the resolved
    PHOENIX_ENDPOINT — the old hardcoded localhost probed the wrong server."""
    monkeypatch.setenv("PHOENIX_ENDPOINT", "https://phoenix.example.com/v1/traces")
    captured: dict = {}

    class _Probe:
        def __init__(self, ok=True, url="", detail=""):
            self.ok, self.url, self.detail = ok, url, detail

        def as_dict(self):
            return {"ok": self.ok, "url": self.url, "detail": self.detail}

    def _fake_probe(profile, **kw):
        if profile.get("name") == "phoenix":
            captured["phoenix_url"] = profile["health"]["models_url"]
            return _Probe(True, profile["health"]["models_url"])
        return _Probe(True, profile.get("base_url", ""))

    import mailroom_sandbox.health as health_mod

    monkeypatch.setattr(health_mod, "probe_models", _fake_probe)
    monkeypatch.setattr(health_mod, "health_check", lambda profile: {"profile": profile, "ok": True, "models": {}, "chat": {}})
    monkeypatch.setattr("mailroom_sandbox.runtime.load_env_file", lambda: None)

    class _Args:
        profile = "ollama"

    rc = cli._cmd_health(_Args())
    assert rc == 0
    assert captured["phoenix_url"] == "https://phoenix.example.com/healthz"
    monkeypatch.delenv("PHOENIX_ENDPOINT")
