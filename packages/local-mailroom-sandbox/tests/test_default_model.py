"""SAND-077: Qwen3.5-9B is the Modal+vLLM default; OpenRouter runs the same weights.

Every place that names the default must agree, or a run silently serves (or
prices) a different model than the one its config claims.
"""

from __future__ import annotations

import ast
import json

import pytest

from mailroom_sandbox import modal_matrix
from mailroom_sandbox.job.deploy_env import BF16_QUANTIZATION, render_exports, spec_env
from mailroom_sandbox.job.spec import DEFAULT_ENGINE_MODEL, MODEL_SERVE_DEFAULTS, EngineSpec, RunSpec, spec_core
from mailroom_sandbox.overlay import build_merged_taxonomy, load_model_map, load_profile
from mailroom_sandbox.paths import repo_root

MODELS = load_model_map()
PREFERENCE = MODELS["openrouter_preference"]


def _deploy_constants() -> dict:
    tree = ast.parse((repo_root() / "deploy" / "modal_vllm.py").read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {"DEFAULT_MODEL", "TEXT_ONLY_MM_LIMITS"}:
                out[name] = ast.literal_eval(node.value)
            elif name == "MODEL_SERVE_DEFAULTS":
                out[name] = node.value
    limits = out["TEXT_ONLY_MM_LIMITS"]
    rows = {}
    for key, value in zip(out["MODEL_SERVE_DEFAULTS"].keys, out["MODEL_SERVE_DEFAULTS"].values):
        row = {}
        for k, v in zip(value.keys, value.values):
            row[ast.literal_eval(k)] = limits if isinstance(v, ast.Name) else ast.literal_eval(v)
        rows[ast.literal_eval(key)] = row
    return {"DEFAULT_MODEL": out["DEFAULT_MODEL"], "MODEL_SERVE_DEFAULTS": rows}


def test_every_vllm_default_names_qwen35_9b():
    assert DEFAULT_ENGINE_MODEL == "Qwen/Qwen3.5-9B"
    assert modal_matrix.DEFAULT_MODAL_MODEL == DEFAULT_ENGINE_MODEL
    assert MODELS["defaults"]["vllm"] == DEFAULT_ENGINE_MODEL
    assert _deploy_constants()["DEFAULT_MODEL"] == DEFAULT_ENGINE_MODEL
    assert EngineSpec().model == DEFAULT_ENGINE_MODEL
    for name in ("modal-vllm", "vllm-local", "vllm-remote"):
        profile = load_profile(name)
        assert profile["default_model"] == profile["judge_model"] == DEFAULT_ENGINE_MODEL, name


def test_openrouter_top_three_are_open_weights_with_a_vllm_counterpart():
    assert PREFERENCE == ["qwen/qwen3.5-9b", "qwen/qwen3.5-35b-a3b", "qwen/qwen3.5-27b"]
    for slug in PREFERENCE:
        row = MODELS["map"][slug]
        assert row["openrouter"] == slug and row["vllm"].startswith("Qwen/Qwen3.5-")
    # First choice = the Modal default's own weights, and the profile default.
    assert MODELS["map"][PREFERENCE[0]]["vllm"] == DEFAULT_ENGINE_MODEL
    assert MODELS["defaults"]["openrouter"] == load_profile("openrouter")["default_model"] == PREFERENCE[0]
    # The MoE pick has a Modal row, so it can be served on both sides too.
    assert MODELS["map"][PREFERENCE[1]]["vllm"] in modal_matrix.modal_models()


@pytest.mark.parametrize(("profile", "model"), [("modal-vllm", "Qwen/Qwen3.5-9B"), ("openrouter", "qwen/qwen3.5-9b")])
def test_pipeline_agents_resolve_to_the_comparable_pair(profile, model):
    # The vendored mailroom assigns its champion id to every agent; the champion
    # row is what actually decides the served model.
    agents = build_merged_taxonomy(load_profile(profile))["agents"]
    for name in ("sorter", "contracts_specialist", "boss"):
        assert agents[name]["model"] == model, name


def test_serve_defaults_match_the_models_yaml_row_and_the_deploy_script():
    row = modal_matrix.modal_models()[DEFAULT_ENGINE_MODEL]
    serve = MODEL_SERVE_DEFAULTS[DEFAULT_ENGINE_MODEL]
    assert row["quantization"] == serve["quantization"] == "fp8"
    deploy = _deploy_constants()["MODEL_SERVE_DEFAULTS"][DEFAULT_ENGINE_MODEL]
    assert deploy["quantization"] == serve["quantization"]
    assert json.loads(deploy["limit_mm_per_prompt"]) == serve["limit_mm_per_prompt"]


def test_engine_fills_serve_defaults_but_an_explicit_value_wins():
    engine = EngineSpec(model=DEFAULT_ENGINE_MODEL)
    assert engine.vllm.quantization == "fp8"
    assert engine.vllm.limit_mm_per_prompt == {"image": 0, "video": 0, "audio": 0}
    bf16 = EngineSpec(model=DEFAULT_ENGINE_MODEL, vllm={"quantization": "", "limit_mm_per_prompt": {"image": 1}})
    assert bf16.vllm.quantization == "" and bf16.vllm.limit_mm_per_prompt == {"image": 1}
    frozen = EngineSpec(model="Qwen/Qwen3-8B")
    assert frozen.vllm.quantization == "" and frozen.vllm.limit_mm_per_prompt is None


def _run(model: str) -> RunSpec:
    return RunSpec.model_validate({
        "schema": "sandbox.run/v1", "run_id": "default-model", "task": "pipeline", "profile": "modal-vllm",
        "dataset": {"provider": "file", "local_path": "data/fixtures/hf/docclass_mini.jsonl", "limit": 1},
        "engine": {"kind": "modal-vllm", "model": model},
    })


def test_frozen_qwen3_8b_specs_keep_their_hash_shape():
    # limit_mm_per_prompt is hashed only when set, so pre-SAND-077 locks do not drift.
    assert "limit_mm_per_prompt" not in spec_core(_run("Qwen/Qwen3-8B"))["engine"]["vllm"]
    assert spec_core(_run(DEFAULT_ENGINE_MODEL))["engine"]["vllm"]["limit_mm_per_prompt"] == {
        "image": 0, "video": 0, "audio": 0}


def test_spec_env_renders_the_deploy_default_mm_limits_byte_for_byte():
    env = spec_env(_run(DEFAULT_ENGINE_MODEL))
    deploy = _deploy_constants()["MODEL_SERVE_DEFAULTS"][DEFAULT_ENGINE_MODEL]
    assert env["MODAL_VLLM_LIMIT_MM_PER_PROMPT"] == deploy["limit_mm_per_prompt"]
    assert env["MODAL_VLLM_QUANTIZATION"] == "fp8"
    assert spec_env(_run("Qwen/Qwen3-8B"))["MODAL_VLLM_LIMIT_MM_PER_PROMPT"] == ""


def test_critical_judge_route_matches_its_serve_defaults_and_modal_row():
    # SAND-078: the judge tier route, the spec/deploy serve defaults and the
    # modal_models row all describe the same Qwen3.5-27B serve.
    judge = MODELS["critical_tier"]["judge"]
    serve = MODEL_SERVE_DEFAULTS[judge["model"]]
    assert judge["vllm"]["quantization"] == serve["quantization"]
    assert judge["vllm"]["limit_mm_per_prompt"] == serve["limit_mm_per_prompt"]
    deploy = _deploy_constants()["MODEL_SERVE_DEFAULTS"][judge["model"]]
    assert json.loads(deploy["limit_mm_per_prompt"]) == serve["limit_mm_per_prompt"]
    row = modal_matrix.modal_models()[judge["model"]]
    assert (row["gpu"], row["quantization"]) == (judge["modal"]["gpu"], serve["quantization"])
    assert load_profile("openrouter")["judge_model"] == "deepseek/deepseek-v4-flash"


def test_specialist_tiers_match_serve_defaults_modal_rows_and_openrouter_preference():
    # SAND-079: mid is the Qwen3.5-35B-A3B MoE, full is the judge's 27B route.
    tiers = MODELS["critical_tier"]["specialists"]
    assert tiers["full"]["modal-vllm"] == MODELS["critical_tier"]["judge"]
    mid = tiers["mid"]["modal-vllm"]
    serve = MODEL_SERVE_DEFAULTS[mid["model"]]
    assert mid["vllm"]["quantization"] == serve["quantization"]
    assert mid["vllm"]["limit_mm_per_prompt"] == serve["limit_mm_per_prompt"]
    assert _deploy_constants()["MODEL_SERVE_DEFAULTS"][mid["model"]]["quantization"] == serve["quantization"]
    assert modal_matrix.modal_models()[mid["model"]]["gpu"] == mid["modal"]["gpu"]
    # OpenRouter tiers are the 2nd and 3rd preference picks, the same weights as Modal.
    assert [tiers["mid"]["openrouter"], tiers["full"]["openrouter"]] == PREFERENCE[1:]
    for tier in ("mid", "full"):
        assert MODELS["map"][tiers[tier]["openrouter"]]["vllm"] == tiers[tier]["modal-vllm"]["model"]


def test_local_vllm_compose_and_pull_hint_serve_the_profile_default(capsys):
    # vllm-local asks the compose server for its default_model; the server and
    # the `pull-models` hint must name the same weights, or every call 404s.
    import yaml

    from mailroom_sandbox.cli import main

    compose = yaml.safe_load((repo_root() / "deploy" / "docker-compose.yml").read_text(encoding="utf-8"))
    served = compose["services"]["vllm"]["command"][0]
    assert served == "${VLLM_MODEL:-" + DEFAULT_ENGINE_MODEL + "}"
    assert load_profile("vllm-local")["pull_models"] == [DEFAULT_ENGINE_MODEL]
    assert main(["pull-models", "--profile", "vllm-local"]) == 0
    assert f"First boot downloads {DEFAULT_ENGINE_MODEL} " in capsys.readouterr().out


def test_explicit_bf16_on_a_serve_default_model_is_not_rendered_as_unset():
    # An explicit quantization: "" means bf16. Rendered as "" it would be
    # unset and the deploy would fall back to the row's fp8.
    bf16 = RunSpec.model_validate({
        **_run(DEFAULT_ENGINE_MODEL).model_dump(by_alias=True),
        "engine": {"kind": "modal-vllm", "model": DEFAULT_ENGINE_MODEL, "vllm": {"quantization": ""}},
    })
    assert spec_env(bf16)["MODAL_VLLM_QUANTIZATION"] == BF16_QUANTIZATION == "bf16"
    assert "export MODAL_VLLM_QUANTIZATION=bf16" in render_exports(bf16)
    assert spec_env(_run("Qwen/Qwen3-8B"))["MODAL_VLLM_QUANTIZATION"] == ""
