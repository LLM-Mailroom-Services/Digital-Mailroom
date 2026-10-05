"""SAND-032: ladder / scale-out / sweep / bf16 configs, posture rows, benchmark gate."""

import pytest

from mailroom_sandbox.job.spec import load_run_spec
from mailroom_sandbox.job.specialist_posture import (
    SAND032_RUNS,
    SPECIALIST_POSTURE,
    validate_mapping,
)
from mailroom_sandbox.paths import config_dir

ALL = sorted((config_dir() / "runs").glob("sand032-*.yaml"))
SORTER = [p for p in ALL if "sorter" in p.stem]
RUNS = [p for p in ALL if p not in SORTER]  # specialist runs
STAGE23 = [p for p in RUNS if p.stem.startswith(("sand032-s2", "sand032-s3"))]
LADDER = [p for p in RUNS if p.stem.startswith("sand032-l")]


def test_sixteen_configs_exist():
    assert len(RUNS) == 31  # + s5 MAUD rerun + s7 admission-×2 + s8 batched-tokens runs
    assert {p.stem for p in RUNS} == set(SAND032_RUNS)


@pytest.mark.parametrize("path", RUNS, ids=lambda p: p.stem)
def test_config_parses_and_pins(path):
    spec = load_run_spec(path)
    assert spec.run_id == path.stem
    assert spec.dataset.split == "all"
    assert spec.dataset.sample_seed == 42
    assert spec.dataset.revision == "ed7576b676343e0b402ec5412cded301e629bdee"
    buckets = spec.dataset.strata["buckets"]
    assert len(buckets) == 1 and "sub_buckets" not in buckets[0]
    assert buckets[0]["count"] == spec.dataset.limit
    assert spec.engine.modal.image_tag == "v0.29.0"
    assert spec.engine.modal.gpu == "L4"
    assert spec.engine.modal.min_containers == spec.engine.modal.max_containers
    assert spec.engine.vllm.gpu_memory_utilization == (0.93 if path.stem.startswith("sand032-s8") else 0.90)  # s8 probes 0.93
    assert spec.engine.vllm.enable_prefix_caching is True


@pytest.mark.parametrize("path", STAGE23, ids=lambda p: p.stem)
def test_stage23_pins_fp8_kv_awq(path):
    spec = load_run_spec(path)
    assert spec.engine.vllm.kv_cache_dtype == "fp8"
    assert spec.engine.model == "Qwen/Qwen3-8B-AWQ"
    assert spec.engine.vllm.max_model_len == 32768


def test_stage23_share_one_serving_block():
    """Stage 2b + 3 run on one warm fleet — identical vllm/modal blocks (no redeploy)."""
    fleet = [p for p in STAGE23 if p.stem != "sand032-s2a-corr100-1rep"]
    blocks = {(load_run_spec(p).engine.vllm.model_dump_json(),
               load_run_spec(p).engine.modal.model_dump_json()) for p in fleet}
    assert len(blocks) == 1


def test_scale_out_arms_differ_only_in_replicas_and_concurrency():
    a = load_run_spec(config_dir() / "runs" / "sand032-s2a-corr100-1rep.yaml")
    b = load_run_spec(config_dir() / "runs" / "sand032-s2b-corr100-2rep.yaml")
    assert a.engine.vllm == b.engine.vllm
    assert (a.engine.modal.max_containers, b.engine.modal.max_containers) == (1, 2)
    assert (a.job.concurrency, b.job.concurrency) == (8, 16)
    assert a.dataset.request_core() == b.dataset.request_core()


def test_ladder_is_cumulative_one_knob_per_rung():
    v = [load_run_spec(p).engine.vllm for p in LADDER]  # sorted l0..l5
    assert v[0].quantization == "awq" and v[0].enable_thinking is None
    assert v[1].enable_thinking is False
    assert v[2].quantization == "awq_marlin"
    assert v[3].kv_cache_dtype == "fp8"
    assert v[4].max_num_seqs == 16
    assert v[5].enforce_eager is False and v[5].cudagraph_capture_sizes == [1, 2, 4, 8, 16]


def test_merger_uses_merger_specialist():
    spec = load_run_spec(config_dir() / "runs" / "sand032-s3-merger50.yaml")
    assert spec.task == "merger_agreement_specialist"


def test_bf16_arm_is_16k_unquantized():
    spec = load_run_spec(config_dir() / "runs" / "sand032-s4-corr20-bf16.yaml")
    assert spec.engine.model == "Qwen/Qwen3-8B"
    assert spec.engine.vllm.quantization == ""
    assert spec.engine.vllm.max_model_len == 16384


def test_posture_rows_valid_including_c16_on_two_replicas():
    assert validate_mapping({k: SPECIALIST_POSTURE[k] for k in SAND032_RUNS}) == []


def test_c16_on_one_replica_rejected():
    row = dict(SPECIALIST_POSTURE["sand032-s2b-corr100-2rep"], replicas=1)
    assert validate_mapping({"x": row})


def _gate(monkeypatch, spec, env):
    from mailroom_sandbox.job import benchmark_check as bc

    monkeypatch.setattr(bc, "active_modal_profile_name", lambda: "exios66")
    monkeypatch.setattr(bc, "_modal_cli_ok", lambda: {"ok": True, "version": "stub"})
    return bc.check_benchmark_posture(
        spec=spec, require_hermes=False, expected_modal_profile="exios66", env=env
    )


@pytest.mark.parametrize("path", RUNS, ids=lambda p: p.stem)
def test_benchmark_gate_passes_with_rendered_env(monkeypatch, path):
    from mailroom_sandbox.job.deploy_env import spec_env

    spec = load_run_spec(path)
    rep = _gate(monkeypatch, spec, spec_env(spec))
    assert rep["ok"], rep["errors"]


def test_benchmark_check_flags_env_drift(monkeypatch):
    from mailroom_sandbox.job.deploy_env import spec_env

    spec = load_run_spec(config_dir() / "runs" / "sand032-s2b-corr100-2rep.yaml")
    env = dict(spec_env(spec))
    env["MODAL_VLLM_KV_CACHE_DTYPE"] = ""
    rep = _gate(monkeypatch, spec, env)
    assert any("MODAL_VLLM_KV_CACHE_DTYPE" in e for e in rep["errors"])


def test_benchmark_check_requires_fp8_on_stage23(monkeypatch):
    from mailroom_sandbox.job.deploy_env import spec_env

    spec = load_run_spec(config_dir() / "runs" / "sand032-s3-corr50.yaml")
    spec.engine.vllm.kv_cache_dtype = ""
    rep = _gate(monkeypatch, spec, spec_env(spec))
    assert any("kv_cache_dtype must be fp8" in e for e in rep["errors"])


def test_benchmark_check_wrong_modal_profile(monkeypatch):
    from mailroom_sandbox.job import benchmark_check as bc
    from mailroom_sandbox.job.deploy_env import spec_env

    spec = load_run_spec(config_dir() / "runs" / "sand032-l0-baseline.yaml")
    monkeypatch.setattr(bc, "active_modal_profile_name", lambda: "hermes-agent-jjb")
    monkeypatch.setattr(bc, "_modal_cli_ok", lambda: {"ok": True, "version": "stub"})
    rep = bc.check_benchmark_posture(spec=spec, require_hermes=False,
                                     expected_modal_profile="exios66", env=spec_env(spec))
    assert any("exios66" in e for e in rep["errors"])


def test_sweep_suite_lists_stage3_in_order():
    import yaml

    data = yaml.safe_load((config_dir() / "runs" / "suites" / "sand032-sweep.yaml").read_text())
    assert data["modal_profile_default"] == "exios66"
    assert [c.split("/")[-1] for c in data["configs"]] == [
        "sand032-s3-corr50.yaml",
        "sand032-s3-insurance50.yaml",
        "sand032-s3-corporate50.yaml",
        "sand032-s3-merger50.yaml",
        "sand032-s3-contracts50.yaml",
        "sand032-s3-corr50-repeat.yaml",
    ]


def test_cli_benchmark_check_passes_modal_profile(monkeypatch, capsys):
    from mailroom_sandbox.cli import main
    from mailroom_sandbox.job import benchmark_check as bc

    seen = {}

    def fake_check(*, spec=None, require_hermes=True, require_modernbert=False,
                   expected_modal_profile=None, env=None):
        seen["profile"] = expected_modal_profile
        return {"ok": True, "errors": [], "warnings": [], "checks": {}, "markdown": "ok"}

    monkeypatch.setattr(bc, "check_benchmark_posture", fake_check)
    rc = main(["run", "benchmark-check", "--config",
               str(config_dir() / "runs" / "sand032-l0-baseline.yaml"), "--modal-profile", "exios66"])
    assert rc == 0 and seen["profile"] == "exios66"


@pytest.mark.parametrize("path", RUNS, ids=lambda p: p.stem)
def test_sand032_runs_on_dedicated_modal_app(path):
    assert load_run_spec(path).engine.modal.app == "sandbox-vllm-sand032"


def test_c32_on_two_replicas_needs_seqs16_admission():
    row = dict(SPECIALIST_POSTURE["sand032-s3-corr50"])
    assert row["concurrency"] == 32 and row["max_num_seqs"] == 16
    assert validate_mapping({"x": row}) == []
    row.pop("max_num_seqs")
    assert any("outside specialist band" in e for e in validate_mapping({"x": row}))



def test_sorter_1000_is_train_mix_on_frozen_2xl4():
    from mailroom_sandbox.job.specialist_posture import SAND032_SORTER_RUNS
    assert {p.stem for p in SORTER} == set(SAND032_SORTER_RUNS)
    spec = load_run_spec(next(p for p in SORTER if p.stem == "sand032-s6-sorter1000"))
    assert spec.task == "isolated" and spec.dataset.split == "train" and spec.dataset.limit == 1000
    assert sum(b["count"] for b in spec.dataset.strata["buckets"]) == 1000
    v, m = spec.engine.vllm, spec.engine.modal
    assert (v.kv_cache_dtype, v.quantization, v.max_num_seqs, v.enforce_eager) == ("fp8", "awq_marlin", 16, False)
    assert (m.min_containers, m.max_containers, spec.job.concurrency) == (2, 2, 32)


def test_run_start_activates_the_engine_model_not_the_profile_default():
    from mailroom_sandbox.cli import _activation_model
    spec = load_run_spec(SORTER[0])
    assert _activation_model(spec, None) == "Qwen/Qwen3-8B-AWQ"
    assert _activation_model(spec, "override/model") == "override/model"
