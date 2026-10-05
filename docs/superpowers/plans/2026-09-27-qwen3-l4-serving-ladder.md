# SAND-032 Qwen3-8B-AWQ L4 Serving Ladder — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every serving knob measurable and spec-driven, then run a gated 1×L4 knob ladder, a 1-vs-2-replica scale-out on correspondence n=100, a 5-specialist n=50 sweep, and a bf16 quality arm. Total Modal spend stays ≤ $5, and the outputs back a defensible funding proposal.

**Architecture:** Part A (Tasks 1–9) is code only: $0, TDD, network-free.
- **Deploy knobs:** new ones are added to `deploy/modal_vllm.py` (env-driven, as today) and mirrored as validated `VLLMSpec` fields.
- **Env from YAML:** `sandbox run deploy-env` renders the exact env from a run YAML, and `benchmark-check` fails when the shell env drifts from it.
- **Metrics:** cost caps become replica-aware; `items.jsonl`, p95, the billed span and a replica-resolved `/metrics` scrape land in the serving record.
- **Offline records:** Braintrust-Experiment-shaped rows are written offline and deleted after reporting.

Part B (Tasks 10–15) is live execution with explicit spend gates, on the **`exios66`** Modal profile.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, Modal SDK 1.5.5 (stubbed in tests), vLLM v0.29.0 image, Qwen/Qwen3-8B-AWQ.

**Spec:** `docs/superpowers/specs/2026-09-27-qwen3-l4-serving-ladder-design.md`

## Global Constraints

- **Budget:** $5.00 hard cap on total Modal spend; the Stage-3 projected-total gate is ≤ $4.50; Stage-1 stop rule is spend > $0.50.
- **Modal profile:** `exios66` for every live run.
- **Serving pins:**
  - model `Qwen/Qwen3-8B-AWQ`, image `v0.29.0`, `max_model_len` 32768, `gpu_memory_utilization` 0.90, prefix caching on, seed 42
  - dataset `Lucius-Morningstar/mailroom-dataset` config `ground_truth` at `FAMILY_HF_REVISION` (`ed7576b676343e0b402ec5412cded301e629bdee`), `split: all`
  - **`kv_cache_dtype=fp8` on every Stage 2–3 run** (and the 1-replica baseline)
  - bf16 arm: `Qwen/Qwen3-8B`, `max_model_len` 16384
- **Data:** only the public HF dataset. No AmFam/proprietary data, and no wording that implies otherwise.
- **Code boundaries:**
  - No edits under `vendor/` (drift guard `tests/test_vendor_drift.py`).
  - Default `pytest` stays network-free.
- **Git hygiene:**
  - Run `git branch --show-current` (must print `sand-032-qwen3-l4-ladder`) before every commit.
  - Push only with `git push origin sand-032-qwen3-l4-ladder`.
  - An external tool in this checkout switches branches.
- **Commit trailer:** `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- **Credentials:** never write credentials to files, logs or commands; the HF token lives only in the Modal secret `huggingface-secret`.
- **Records:** offline BT rows go under `data/runtime/bt_experiments/` (already gitignored via `data/runtime/`).

## Review Focus

1. **Stale shell env:** an operator shell still exports `MODAL_VLLM_*` from an earlier run. Expected: `benchmark-check` fails loudly, naming every key that differs from the YAML (Task 2 test `test_env_drift_names_every_mismatch`).
2. **Two replicas, one cap:** a 2-replica run with `cost_cap_usd` sized for one GPU. Expected: the cap trips at half the wall a 1-replica run would reach (Task 3 test `test_isolated_guard_scales_by_replicas`).
3. **Identical replica scrapes:** a `/metrics` scrape where both replicas report identical counters, or one replica never answers. Expected: the report says "replicas observed: 1 of 2", not a fabricated split (Task 5 test `test_scrape_reports_unobserved_replicas`).
4. **Unknown vLLM flag:** a new flag is missing on the v0.29.0 image. Expected: the operator finds out from the CPU-only `--help` probe before any GPU boot. The argv builder emits nothing for unset knobs (Task 1 test `test_new_knobs_absent_by_default`).
5. **Dispose before commit:** `sandbox run dispose` runs before the report is committed. Expected: it refuses unless the run's report path is tracked in git (Task 7 test `test_dispose_refuses_untracked_report`).

---

## File Structure

| File | Responsibility |
| --- | --- |
| `deploy/modal_vllm.py` (modify) | New env knobs → argv (`--kv-cache-dtype`, `--default-chat-template-kwargs`, `--compilation-config`, `--max-num-batched-tokens`, `--chat-template`), optional `@modal.concurrent` |
| `src/mailroom_sandbox/job/spec.py` (modify) | `VLLMSpec` new fields |
| `src/mailroom_sandbox/job/deploy_env.py` (create) | Spec → `MODAL_VLLM_*` env dict; drift diff vs an environ |
| `src/mailroom_sandbox/job/runner.py` (modify) | Replica-aware caps; write `items.jsonl` for whole-run isolated tasks |
| `src/mailroom_sandbox/eval/runners.py` (modify) | `replicas` param in isolated guard + cost; p95 |
| `src/mailroom_sandbox/job/metrics.py` (modify) | `estimate_gpu_cost_usd(..., replicas=)`; p95; billed-span block |
| `src/mailroom_sandbox/job/vllm_metrics.py` (create) | Parse Prometheus text; scrape N times; group by replica (`process_start_time_seconds`) |
| `src/mailroom_sandbox/job/bt_offline.py` (create) | Write/dispose Braintrust-Experiment-shaped rows offline |
| `src/mailroom_sandbox/job/funding.py` (create) | Unit-cost + line-item projection math for the proposal |
| `src/mailroom_sandbox/job/specialist_posture.py` (modify) | SAND-032 posture rows (generated), concurrency band up to 8 × replicas |
| `src/mailroom_sandbox/job/benchmark_check.py` (modify) | Allowlists, fp8-KV + env-drift assertions, explicit Modal profile |
| `src/mailroom_sandbox/cli.py` (modify) | `run deploy-env`, `run dispose`, `run scrape-metrics`, `--modal-profile` |
| `config/runs/sand032-*.yaml` (create, 15 files) | Ladder, scale-out, sweep, bf16 configs |
| `config/suites/sand032-sweep.yaml` (create) | Stage-3 chain |
| `governance/TASKS.md` (modify) | SAND-032 card |
| Tests: `tests/test_modal_vllm.py`, `tests/test_job_spec.py`, `tests/test_deploy_env.py`, `tests/test_job_runner.py`, `tests/test_job_metrics.py`, `tests/test_vllm_metrics.py`, `tests/test_bt_offline.py`, `tests/test_funding.py`, `tests/test_specialist_posture.py`, `tests/test_sand032_configs.py`, `tests/test_corpus.py` | |

---

## Part A — Code ($0)

### Task 1: New vLLM deploy knobs

**Files:**
- Modify: `deploy/modal_vllm.py:98-160` (knob block + `CONFIG_ENV_KEYS`), `:236-266` (`build_vllm_command`), `:321-330` (`serve` decorators)
- Test: `tests/test_modal_vllm.py` (add to `KNOB_ENV` tuple and `TestCommandBuilder`)

**Interfaces:**
- Produces:
  - env keys `MODAL_VLLM_KV_CACHE_DTYPE`, `MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS` (JSON string), `MODAL_VLLM_CUDAGRAPH_CAPTURE_SIZES` (comma list, e.g. `1,2,4,8,16`), `MODAL_VLLM_MAX_NUM_BATCHED_TOKENS`, `MODAL_VLLM_CHAT_TEMPLATE` (path inside image), `MODAL_VLLM_MAX_INPUTS` (int; enables `@modal.concurrent`)
  - module constants of the same stem (`KV_CACHE_DTYPE`, …)

- [ ] **Step 1: Write the failing tests**

Append the six env names to `KNOB_ENV` in `tests/test_modal_vllm.py`, then add to `class TestCommandBuilder`:

```python
    def test_new_knobs_absent_by_default(self):
        mod = _load_app_module()
        cmd = mod.build_vllm_command("Qwen/Qwen3-8B-AWQ")
        for flag in (
            "--kv-cache-dtype",
            "--default-chat-template-kwargs",
            "--compilation-config",
            "--max-num-batched-tokens",
            "--chat-template",
        ):
            assert flag not in cmd

    def test_kv_cache_dtype_fp8(self, monkeypatch):
        monkeypatch.setenv("MODAL_VLLM_KV_CACHE_DTYPE", "fp8")
        mod = _load_app_module()
        cmd = mod.build_vllm_command("Qwen/Qwen3-8B-AWQ")
        assert cmd[cmd.index("--kv-cache-dtype") + 1] == "fp8"

    def test_thinking_off_kwargs_passed_verbatim_json(self, monkeypatch):
        monkeypatch.setenv(
            "MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS", '{"enable_thinking": false}'
        )
        mod = _load_app_module()
        cmd = mod.build_vllm_command("Qwen/Qwen3-8B-AWQ")
        import json as _json
        raw = cmd[cmd.index("--default-chat-template-kwargs") + 1]
        assert _json.loads(raw) == {"enable_thinking": False}

    def test_invalid_chat_template_kwargs_fail_at_import(self, monkeypatch):
        monkeypatch.setenv("MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS", "{not json")
        with pytest.raises(ValueError, match="DEFAULT_CHAT_TEMPLATE_KWARGS"):
            _load_app_module()

    def test_cudagraph_capture_sizes_render_compilation_config(self, monkeypatch):
        monkeypatch.setenv("MODAL_VLLM_ENFORCE_EAGER", "0")
        monkeypatch.setenv("MODAL_VLLM_CUDAGRAPH_CAPTURE_SIZES", "1,2,4,8,16")
        mod = _load_app_module()
        cmd = mod.build_vllm_command("Qwen/Qwen3-8B-AWQ")
        import json as _json
        cfg = _json.loads(cmd[cmd.index("--compilation-config") + 1])
        assert cfg == {"cudagraph_capture_sizes": [1, 2, 4, 8, 16]}
        assert "--enforce-eager" not in cmd

    def test_capture_sizes_with_eager_is_rejected(self, monkeypatch):
        monkeypatch.setenv("MODAL_VLLM_ENFORCE_EAGER", "1")
        monkeypatch.setenv("MODAL_VLLM_CUDAGRAPH_CAPTURE_SIZES", "1,2")
        with pytest.raises(ValueError, match="enforce_eager"):
            _load_app_module()

    def test_batched_tokens_and_chat_template(self, monkeypatch):
        monkeypatch.setenv("MODAL_VLLM_MAX_NUM_BATCHED_TOKENS", "8192")
        monkeypatch.setenv("MODAL_VLLM_CHAT_TEMPLATE", "/templates/qwen3_nothink.jinja")
        mod = _load_app_module()
        cmd = mod.build_vllm_command("Qwen/Qwen3-8B-AWQ")
        assert cmd[cmd.index("--max-num-batched-tokens") + 1] == "8192"
        assert cmd[cmd.index("--chat-template") + 1] == "/templates/qwen3_nothink.jinja"

    def test_new_knobs_forwarded_to_container(self):
        mod = _load_app_module()
        for key in (
            "MODAL_VLLM_KV_CACHE_DTYPE",
            "MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS",
            "MODAL_VLLM_CUDAGRAPH_CAPTURE_SIZES",
            "MODAL_VLLM_MAX_NUM_BATCHED_TOKENS",
            "MODAL_VLLM_CHAT_TEMPLATE",
        ):
            assert key in mod.CONFIG_ENV_KEYS
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_modal_vllm.py -k "new_knobs or kv_cache or thinking or chat_template or cudagraph or capture_sizes or batched" -v`
Expected: FAIL. The flags are absent, `CONFIG_ENV_KEYS` lacks the keys, and no `ValueError` is raised.

- [ ] **Step 3: Implement**

In `deploy/modal_vllm.py`, after `TOOL_CALL_PARSER`/`ENABLE_AUTO_TOOL_CHOICE`:

```python
# SAND-032: KV-cache dtype (fp8 doubles the L4 KV pool; pinned for 2×L4 runs),
# Qwen3 thinking control, CUDA-graph capture sizes, prefill chunk budget.
KV_CACHE_DTYPE = os.environ.get("MODAL_VLLM_KV_CACHE_DTYPE", "")
DEFAULT_CHAT_TEMPLATE_KWARGS = os.environ.get("MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS", "")
CUDAGRAPH_CAPTURE_SIZES = os.environ.get("MODAL_VLLM_CUDAGRAPH_CAPTURE_SIZES", "")
MAX_NUM_BATCHED_TOKENS = os.environ.get("MODAL_VLLM_MAX_NUM_BATCHED_TOKENS", "")
CHAT_TEMPLATE = os.environ.get("MODAL_VLLM_CHAT_TEMPLATE", "")
MAX_INPUTS = int(os.environ.get("MODAL_VLLM_MAX_INPUTS", "0") or 0)

if DEFAULT_CHAT_TEMPLATE_KWARGS:
    try:
        json.loads(DEFAULT_CHAT_TEMPLATE_KWARGS)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS is not valid JSON: {exc}"
        ) from exc
if CUDAGRAPH_CAPTURE_SIZES and _truthy(ENFORCE_EAGER):
    raise ValueError(
        "MODAL_VLLM_CUDAGRAPH_CAPTURE_SIZES requires enforce_eager off "
        "(MODAL_VLLM_ENFORCE_EAGER=0) — eager mode never captures graphs"
    )
```

Add `import json` at the top if absent. `_truthy` must be defined above this block; move its `def` up if needed. Add the five string keys plus `"MODAL_VLLM_MAX_INPUTS"` to `CONFIG_ENV_KEYS`. In `build_vllm_command`, before `cmd += ["--no-enable-log-requests"]`:

```python
    if KV_CACHE_DTYPE:
        cmd += ["--kv-cache-dtype", KV_CACHE_DTYPE]
    if DEFAULT_CHAT_TEMPLATE_KWARGS:
        cmd += ["--default-chat-template-kwargs", DEFAULT_CHAT_TEMPLATE_KWARGS]
    if CHAT_TEMPLATE:
        cmd += ["--chat-template", CHAT_TEMPLATE]
    if CUDAGRAPH_CAPTURE_SIZES:
        sizes = [int(s) for s in CUDAGRAPH_CAPTURE_SIZES.split(",") if s.strip()]
        cmd += ["--compilation-config", json.dumps({"cudagraph_capture_sizes": sizes})]
    if MAX_NUM_BATCHED_TOKENS:
        cmd += ["--max-num-batched-tokens", MAX_NUM_BATCHED_TOKENS]
```

For `serve`, apply `@modal.concurrent(max_inputs=MAX_INPUTS)` only when `MAX_INPUTS > 0`. Wrap the existing decorator stack in a helper so the default deploy stays byte-for-byte the same:

```python
def _maybe_concurrent(fn):
    return modal.concurrent(max_inputs=MAX_INPUTS)(fn) if MAX_INPUTS > 0 else fn
```

Place it between `@app.function(...)` and `@modal.web_server(...)`. The test stub needs `concurrent`: add `stub.concurrent = lambda **kw: (lambda f: f)` in `_install_modal_stub`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_modal_vllm.py -v`
Expected: all PASS, including the pre-existing `test_command_defaults`.

- [ ] **Step 5: Commit**

```bash
git branch --show-current   # must print sand-032-qwen3-l4-ladder
git add deploy/modal_vllm.py tests/test_modal_vllm.py
git commit -m "SAND-032: vLLM deploy knobs — kv-cache dtype, thinking kwargs, CUDA-graph sizes, batched tokens, max_inputs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Spec fields + YAML→env rendering + drift check

**Files:**
- Modify: `src/mailroom_sandbox/job/spec.py:230-281` (`VLLMSpec`)
- Create: `src/mailroom_sandbox/job/deploy_env.py`
- Modify: `src/mailroom_sandbox/cli.py` (register `run deploy-env`, next to `benchmark-check` at ~L632)
- Test: `tests/test_job_spec.py`, `tests/test_deploy_env.py` (create)

**Interfaces:**
- Consumes: env key names from Task 1.
- Produces:
  - `VLLMSpec.kv_cache_dtype: str = ""`
  - `VLLMSpec.enable_thinking: bool | None = None` (None = don't send)
  - `VLLMSpec.cudagraph_capture_sizes: list[int] = []`
  - `VLLMSpec.max_num_batched_tokens: int | None = None`
  - `VLLMSpec.max_inputs: int = 0`
  - `deploy_env.spec_env(spec: RunSpec) -> dict[str, str]`
  - `deploy_env.env_drift(spec: RunSpec, environ: Mapping[str, str]) -> list[str]`
  - `deploy_env.render_exports(spec: RunSpec) -> str`

- [ ] **Step 1: Write failing tests**

`tests/test_job_spec.py` (append):

```python
import pytest
from mailroom_sandbox.job.spec import VLLMSpec


def test_vllmspec_new_fields_default_off():
    v = VLLMSpec()
    assert v.kv_cache_dtype == ""
    assert v.enable_thinking is None
    assert v.cudagraph_capture_sizes == []
    assert v.max_num_batched_tokens is None
    assert v.max_inputs == 0


def test_vllmspec_rejects_unknown_kv_dtype():
    with pytest.raises(ValueError, match="kv_cache_dtype"):
        VLLMSpec(kv_cache_dtype="int4")


def test_vllmspec_capture_sizes_require_eager_off():
    with pytest.raises(ValueError, match="enforce_eager"):
        VLLMSpec(enforce_eager=True, cudagraph_capture_sizes=[1, 2])
    assert VLLMSpec(enforce_eager=False, cudagraph_capture_sizes=[1, 2]).cudagraph_capture_sizes == [1, 2]
```

`tests/test_deploy_env.py` (create):

```python
from mailroom_sandbox.job.deploy_env import env_drift, render_exports, spec_env
from mailroom_sandbox.job.spec import RunSpec


def _spec(**vllm):
    base = {"max_model_len": 32768, "quantization": "awq_marlin", "enforce_eager": False,
            "kv_cache_dtype": "fp8", "enable_thinking": False,
            "cudagraph_capture_sizes": [1, 2, 4, 8, 16], "max_num_seqs": 16}
    base.update(vllm)
    return RunSpec.model_validate({
        "schema": "sandbox.run/v1", "run_id": "sand032-test", "task": "correspondence_specialist",
        "profile": "modal-vllm",
        "engine": {"kind": "modal-vllm", "model": "Qwen/Qwen3-8B-AWQ", "vllm": base,
                   "modal": {"gpu": "L4", "max_containers": 2, "min_containers": 2,
                             "scaledown_seconds": 120}},
    })


def test_spec_env_renders_every_knob():
    env = spec_env(_spec())
    assert env["MODAL_VLLM_MODEL"] == "Qwen/Qwen3-8B-AWQ"
    assert env["MODAL_VLLM_QUANTIZATION"] == "awq_marlin"
    assert env["MODAL_VLLM_KV_CACHE_DTYPE"] == "fp8"
    assert env["MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS"] == '{"enable_thinking": false}'
    assert env["MODAL_VLLM_CUDAGRAPH_CAPTURE_SIZES"] == "1,2,4,8,16"
    assert env["MODAL_VLLM_ENFORCE_EAGER"] == "0"
    assert env["MODAL_VLLM_MAX_NUM_SEQS"] == "16"
    assert env["MODAL_VLLM_MAX_CONTAINERS"] == "2"
    assert env["MODAL_VLLM_MIN_CONTAINERS"] == "2"
    assert env["MODAL_VLLM_SCALEDOWN_SECONDS"] == "120"


def test_thinking_none_renders_empty_kwargs():
    env = spec_env(_spec(enable_thinking=None))
    assert env["MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS"] == ""


def test_env_drift_names_every_mismatch():
    spec = _spec()
    environ = dict(spec_env(spec))
    environ["MODAL_VLLM_KV_CACHE_DTYPE"] = ""          # stale shell: fp8 missing
    environ["MODAL_VLLM_MAX_NUM_SEQS"] = "6"           # stale shell: old value
    drift = env_drift(spec, environ)
    assert any("MODAL_VLLM_KV_CACHE_DTYPE" in d for d in drift)
    assert any("MODAL_VLLM_MAX_NUM_SEQS" in d and "'6'" in d and "'16'" in d for d in drift)
    assert len(drift) == 2


def test_env_drift_treats_unset_as_empty():
    spec = _spec(kv_cache_dtype="", enable_thinking=None, cudagraph_capture_sizes=[],
                 enforce_eager=True)
    environ = {k: v for k, v in spec_env(spec).items() if v != ""}
    assert env_drift(spec, environ) == []


def test_render_exports_is_sourceable_and_secret_free():
    text = render_exports(_spec())
    assert "export MODAL_VLLM_KV_CACHE_DTYPE=fp8" in text
    assert "HF_TOKEN" not in text and "API_TOKEN" not in text
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_job_spec.py tests/test_deploy_env.py -v`
Expected: FAIL (fields and module missing).

- [ ] **Step 3: Implement**

In `VLLMSpec`, add these fields after `revision`:

```python
    kv_cache_dtype: str = ""  # "" = vLLM auto; "fp8" pinned for SAND-032 2×L4
    enable_thinking: bool | None = None  # None = don't send chat-template kwargs
    cudagraph_capture_sizes: list[int] = Field(default_factory=list)
    max_num_batched_tokens: int | None = None
    max_inputs: int = 0  # >0 wraps serve() in @modal.concurrent(max_inputs=…)

    @field_validator("kv_cache_dtype")
    @classmethod
    def _kv(cls, v: str) -> str:
        if v not in {"", "auto", "fp8", "fp8_e4m3", "fp8_e5m2"}:
            raise ValueError(f"kv_cache_dtype {v!r} not supported on v0.29.0")
        return v

    @model_validator(mode="after")
    def _graphs_need_no_eager(self) -> "VLLMSpec":
        if self.cudagraph_capture_sizes and self.enforce_eager:
            raise ValueError("cudagraph_capture_sizes requires enforce_eager=false")
        return self
```

Import `model_validator` from pydantic; it is already used elsewhere in `spec.py`. Then create `src/mailroom_sandbox/job/deploy_env.py`:

```python
"""SAND-032: render the deploy env a run YAML implies, and diff it vs a shell.

deploy/modal_vllm.py reads MODAL_VLLM_* at import time; the run YAML is the
source of truth. `spec_env` is the single mapping, `env_drift` is the loud
check benchmark-check runs, `render_exports` is what the operator sources.
"""

from __future__ import annotations

import json
from typing import Mapping

from mailroom_sandbox.job.runbooks import _shell_quote
from mailroom_sandbox.job.spec import RunSpec


def _b(value: bool) -> str:
    return "1" if value else "0"


def spec_env(spec: RunSpec) -> dict[str, str]:
    v = spec.engine.vllm
    m = spec.engine.modal
    kwargs = "" if v.enable_thinking is None else json.dumps({"enable_thinking": v.enable_thinking})
    env = {
        "MODAL_VLLM_MODEL": spec.engine.model,
        "MODAL_VLLM_MAX_MODEL_LEN": str(v.max_model_len),
        "MODAL_VLLM_GPU_MEMORY_UTILIZATION": f"{v.gpu_memory_utilization:.2f}",
        "MODAL_VLLM_MAX_NUM_SEQS": str(v.max_num_seqs),
        "MODAL_VLLM_ENABLE_PREFIX_CACHING": _b(v.enable_prefix_caching),
        "MODAL_VLLM_ENFORCE_EAGER": _b(v.enforce_eager),
        "MODAL_VLLM_QUANTIZATION": v.quantization,
        "MODAL_VLLM_REVISION": v.revision,
        "MODAL_VLLM_KV_CACHE_DTYPE": v.kv_cache_dtype,
        "MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS": kwargs,
        "MODAL_VLLM_CUDAGRAPH_CAPTURE_SIZES": ",".join(str(s) for s in v.cudagraph_capture_sizes),
        "MODAL_VLLM_MAX_NUM_BATCHED_TOKENS": "" if v.max_num_batched_tokens is None else str(v.max_num_batched_tokens),
        "MODAL_VLLM_MAX_INPUTS": str(v.max_inputs) if v.max_inputs else "",
    }
    if m is not None:
        env.update({
            "MODAL_VLLM_GPU": m.gpu,
            "MODAL_VLLM_IMAGE_TAG": m.image_tag,
            "MODAL_VLLM_MAX_CONTAINERS": str(m.max_containers),
            "MODAL_VLLM_MIN_CONTAINERS": str(m.min_containers),
            "MODAL_VLLM_SCALEDOWN_SECONDS": str(m.scaledown_seconds),
        })
    return env


def env_drift(spec: RunSpec, environ: Mapping[str, str]) -> list[str]:
    out: list[str] = []
    for key, want in spec_env(spec).items():
        have = (environ.get(key) or "").strip()
        if have != want:
            out.append(f"{key}: shell has {have!r}, run YAML wants {want!r}")
    return out


def render_exports(spec: RunSpec) -> str:
    lines = [f"# deploy env for {spec.run_id} (generated by `sandbox run deploy-env`)"]
    for key, val in spec_env(spec).items():
        lines.append(f"export {key}={_shell_quote(val)}")
    return "\n".join(lines) + "\n"
```

Note: `gpu_memory_utilization` renders as `0.90`, which matches the deploy default string. `MODAL_VLLM_MAX_MODEL_LEN` for the bf16 arm is 16384.

Register the CLI command in `cli.py` after `bcheck` (~L637):

```python
    denv = run_sub.add_parser("deploy-env", parents=[common],
                              help="print MODAL_VLLM_* exports implied by --config")
    denv.set_defaults(handler=_cmd_run_deploy_env)
```

with the handler:

```python
def _cmd_run_deploy_env(args) -> int:
    from mailroom_sandbox.job.deploy_env import render_exports
    from mailroom_sandbox.job.spec import load_run_spec

    if not getattr(args, "config", None):
        print("ERROR: --config required", file=sys.stderr)
        return 2
    sys.stdout.write(render_exports(load_run_spec(args.config)))
    return 0
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_job_spec.py tests/test_deploy_env.py tests/test_cli_wiring.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git branch --show-current
git add src/mailroom_sandbox/job/spec.py src/mailroom_sandbox/job/deploy_env.py src/mailroom_sandbox/cli.py tests/test_job_spec.py tests/test_deploy_env.py
git commit -m "SAND-032: VLLMSpec knobs + run deploy-env + env drift check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Replica-aware cost caps and cost estimates

**Files:**
- Modify: `src/mailroom_sandbox/job/metrics.py:120-130` (`estimate_gpu_cost_usd`), `:429-521` (`enrich_serving_report`)
- Modify: `src/mailroom_sandbox/job/runner.py:373-378, 457-466, 233-288`
- Modify: `src/mailroom_sandbox/eval/runners.py:125-144, 262-275, 368-378`
- Test: `tests/test_job_metrics.py`, `tests/test_job_runner.py`

**Interfaces:**
- Produces:
  - `estimate_gpu_cost_usd(gpu_seconds, *, gpu=None, replicas: int = 1)`
  - `runner._lock_replicas(store) -> int`
  - `run_isolated_eval(..., replicas: int = 1)`
  - `enrich_serving_report(..., replicas: int = 1)`, which writes `record["replicas"]`

- [ ] **Step 1: Write failing tests**

`tests/test_job_metrics.py`:

```python
from mailroom_sandbox.job.metrics import estimate_gpu_cost_usd, enrich_serving_report


def test_gpu_cost_scales_with_replicas(monkeypatch):
    monkeypatch.delenv("MODAL_GPU_USD_PER_HOUR", raising=False)
    monkeypatch.delenv("MODAL_GPU_USD_PER_SEC", raising=False)
    one = estimate_gpu_cost_usd(3600, gpu="L4")
    two = estimate_gpu_cost_usd(3600, gpu="L4", replicas=2)
    assert two == round(one * 2, 6)


def test_enrich_bills_every_replica():
    rec = {"provider": "vllm", "profile": "modal-vllm", "gpu": "L4", "n": 2}
    items = [{"ok": True, "latency_ms": 1000.0}, {"ok": True, "latency_ms": 3000.0}]
    one = enrich_serving_report(dict(rec), items=items, wall_seconds=100, gpu="L4")
    two = enrich_serving_report(dict(rec), items=items, wall_seconds=100, gpu="L4", replicas=2)
    assert two["estimated_gpu_cost_usd"] == round(one["estimated_gpu_cost_usd"] * 2, 6)
    assert two["replicas"] == 2
```

`tests/test_job_runner.py` (append; this follows the file's existing `RunStore` fixtures):

```python
def test_lock_replicas_reads_max_containers(tmp_path):
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.runner import _lock_replicas

    store = RunStore(tmp_path / "r")
    store.write_lock({"engine": {"modal": {"gpu": "L4", "max_containers": 2}}})
    assert _lock_replicas(store) == 2
    store.write_lock({"engine": {"modal": {"gpu": "L4"}}})
    assert _lock_replicas(store) == 1


def test_isolated_guard_scales_by_replicas(monkeypatch):
    from mailroom_sandbox.job import metrics

    monkeypatch.delenv("MODAL_GPU_USD_PER_HOUR", raising=False)
    # $0.80/hr L4: 0.10 USD cap trips at 450 s on one replica, 225 s on two.
    assert metrics.estimate_gpu_cost_usd(300, gpu="L4") < 0.10
    assert metrics.estimate_gpu_cost_usd(300, gpu="L4", replicas=2) >= 0.10
```

If `RunStore` has no `write_lock`, use the method the existing runner tests use to seed a lock: `grep -n "def write_lock\|lock_path.write_text" src/mailroom_sandbox/job/checkpoint.py tests/test_job_runner.py`.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_job_metrics.py tests/test_job_runner.py -k "replica" -v`
Expected: FAIL (`unexpected keyword 'replicas'`, and `_lock_replicas` missing).

- [ ] **Step 3: Implement**

`metrics.py`:

```python
def estimate_gpu_cost_usd(
    gpu_seconds: float,
    *,
    gpu: str | None = None,
    replicas: int = 1,
) -> float | None:
    """USD for ``gpu_seconds`` of wall on ``replicas`` concurrently-billed GPUs."""
    if gpu_seconds is None or gpu_seconds <= 0:
        return None
    rate = gpu_usd_per_hour(gpu) * max(1, int(replicas))
    return round(gpu_seconds / 3600.0 * rate, 6)
```

In `enrich_serving_report`, add the `replicas: int = 1` kwarg. Set `out["replicas"] = max(1, int(replicas))`, and pass `replicas=replicas` to all four `estimate_gpu_cost_usd` calls inside it.

`runner.py`:

```python
def _lock_replicas(store: RunStore) -> int:
    """Concurrently-billed replicas (MIN=MAX pinned 2×L4 bills 2 GPUs)."""
    engine = (store.read_lock() or {}).get("engine") or {}
    modal = engine.get("modal") if isinstance(engine, dict) else None
    if isinstance(modal, dict):
        return max(1, int(modal.get("max_containers") or 1))
    return 1
```

In `_estimate_run_gpu_usd`, pass `replicas=_lock_replicas(store)`. In `_run_whole_run`, compute `replicas = _lock_replicas(store)` next to `gpu = _lock_gpu(store)` and pass `replicas=replicas` to both `run_isolated_eval` calls.

`eval/runners.py`: add `replicas: int = 1` to the `run_isolated_eval` signature. In `_guard`, use `estimate_gpu_cost_usd(wall, gpu=gpu or "L4", replicas=replicas)`. In the record block (~L368), use `estimate_gpu_cost_usd(billed_seconds, gpu=gpu or "L4", replicas=replicas)` and set `record["replicas"] = int(replicas)`.

Billing semantics: `max_containers` is the billed replica count when `min_containers == max_containers`, which every SAND-032 2-replica config pins. A scale-to-zero config with `max_containers=2` over-estimates, which is the safe direction for a cap.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_job_metrics.py tests/test_job_runner.py tests/test_eval.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git branch --show-current
git add src/mailroom_sandbox/job/metrics.py src/mailroom_sandbox/job/runner.py src/mailroom_sandbox/eval/runners.py tests/test_job_metrics.py tests/test_job_runner.py
git commit -m "SAND-032: replica-aware live cost caps and GPU cost estimates

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: items.jsonl, p95 and billed span for isolated specialist runs

**Files:**
- Modify: `src/mailroom_sandbox/job/runner.py` (`_run_whole_run`, after `result` is obtained ~L302)
- Modify: `src/mailroom_sandbox/eval/runners.py:350-354`, `src/mailroom_sandbox/job/metrics.py:455-466`
- Test: `tests/test_job_runner.py`, `tests/test_job_metrics.py`

**Interfaces:**
- Consumes: `result["rows"]` from `run_isolated_eval` (each has `id, pred, score, error, latency_ms, prompt_tokens, completion_tokens`).
- Produces:
  - `runner._persist_isolated_items(store, rows) -> int` (count written)
  - serving/record keys `latency_p95_seconds`, `billed_span_seconds`, `billed_span_usd`
  - `metrics.p95(values: list[float]) -> float`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_job_metrics.py
from mailroom_sandbox.job.metrics import p95


def test_p95_nearest_rank():
    assert p95([float(i) for i in range(1, 21)]) == 19.0
    assert p95([5.0]) == 5.0


def test_enrich_adds_p95_and_billed_span():
    rec = {"provider": "vllm", "profile": "modal-vllm", "gpu": "L4", "n": 20}
    items = [{"ok": True, "latency_ms": float(i * 1000)} for i in range(1, 21)]
    out = enrich_serving_report(rec, items=items, wall_seconds=100, gpu="L4",
                                replicas=2, scaledown_seconds=120, cold_boot_seconds=150)
    assert out["latency_p95_seconds"] == 19.0
    # span = cold boot + wall + scaledown tail, billed on both replicas
    assert out["billed_span_seconds"] == 370.0
    assert out["billed_span_usd"] == estimate_gpu_cost_usd(370.0, gpu="L4", replicas=2)
```

```python
# tests/test_job_runner.py
def test_persist_isolated_items_writes_items_jsonl(tmp_path):
    import json
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.runner import _persist_isolated_items

    store = RunStore(tmp_path / "r")
    rows = [
        {"id": "a", "pred": {"x": 1}, "score": {"overall_extraction_score": 0.5},
         "error": None, "latency_ms": 1200.0, "prompt_tokens": 10, "completion_tokens": 5},
        {"id": "b", "pred": None, "score": {}, "error": "OpenAIConnectionError: x",
         "latency_ms": 900.0, "prompt_tokens": 0, "completion_tokens": 0},
    ]
    assert _persist_isolated_items(store, rows) == 2
    lines = [json.loads(l) for l in store.items_path.read_text().splitlines()]
    assert [l["item_id"] for l in lines] == ["a", "b"]
    assert lines[0]["ok"] is True and lines[1]["ok"] is False
    assert lines[1]["error"].startswith("OpenAIConnectionError")


def test_persist_isolated_items_is_idempotent(tmp_path):
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.runner import _persist_isolated_items

    store = RunStore(tmp_path / "r")
    rows = [{"id": "a", "score": {}, "error": None, "latency_ms": 1.0}]
    _persist_isolated_items(store, rows)
    assert _persist_isolated_items(store, rows) == 0
    assert len(store.items_path.read_text().splitlines()) == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_job_metrics.py tests/test_job_runner.py -k "p95 or billed_span or persist_isolated" -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

`metrics.py`:

```python
def p95(values: Sequence[float]) -> float:
    """Nearest-rank 95th percentile (no interpolation; defensible in reports)."""
    ordered = sorted(float(v) for v in values)
    if not ordered:
        raise ValueError("p95 of empty sequence")
    rank = max(1, math.ceil(0.95 * len(ordered)))
    return ordered[rank - 1]
```

Import `math` if needed. In `enrich_serving_report`, add the kwarg `scaledown_seconds: float | None = None`. After the p50 `setdefault`, add `out.setdefault("latency_p95_seconds", round(p95(latencies_ms) / 1000.0, 6))`. In the `kind == "modal"` block, add:

```python
        span = float(wall_seconds) + float(cold_boot_seconds or 0.0) + float(scaledown_seconds or 0.0)
        out["billed_span_seconds"] = round(span, 3)
        out["billed_span_usd"] = estimate_gpu_cost_usd(span, gpu=gpu_class, replicas=replicas)
```

(Superseded in the Part A review: renamed `run_span_*_lower_bound`, and pinned MIN=MAX fleets add no scale-down tail.) `billed_span` is the defensible upper estimate of what Modal charges for a run: boot + wall + idle tail before scale-down. The Modal usage page stays the ground truth (Task 12).

`eval/runners.py` ~L353: add `record["latency_p95_seconds"] = round(p95(latencies) / 1000.0, 6)`, importing `p95` from `mailroom_sandbox.job.metrics`.

`runner.py`:

```python
def _persist_isolated_items(store: RunStore, rows: list[dict[str, Any]] | None) -> int:
    """SAND-032: isolated specialist runs wrote no items.jsonl — per-doc rows
    are the evidence the reports and offline BT rows are built from."""
    if not rows:
        return 0
    seen = {i.get("item_id") for i in store.read_items()} if store.items_path.is_file() else set()
    written = 0
    for row in rows:
        item_id = row.get("id")
        if item_id in seen:
            continue
        store.append_item({
            "item_id": item_id,
            "ok": not row.get("error"),
            "error": row.get("error"),
            "pred": row.get("pred"),
            "score": row.get("score"),
            "latency_ms": row.get("latency_ms"),
            "prompt_tokens": row.get("prompt_tokens"),
            "completion_tokens": row.get("completion_tokens"),
            "ts": utc_now(),
        })
        written += 1
    return written
```

Call it in `_run_whole_run` right after the `try/except` that sets `result`: `_persist_isolated_items(store, result.get("rows") if isinstance(result, dict) else None)`. If `RunStore` lacks `read_items`, use the reader the file already exposes: `grep -n "def read_items\|def items(" src/mailroom_sandbox/job/checkpoint.py`.

Pass `replicas=_lock_replicas(store)` and `scaledown_seconds=` (from the lock's `engine.modal.scaledown_seconds`) through the serving-json path in `serving_record_from_store` (`metrics.py:523`), which calls `enrich_serving_report`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_job_metrics.py tests/test_job_runner.py tests/test_serving_report.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git branch --show-current
git add -A src/mailroom_sandbox tests
git commit -m "SAND-032: items.jsonl for isolated runs, p95 latency, billed span in serving record

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: vLLM /metrics scrape resolved per replica

**Files:**
- Create: `src/mailroom_sandbox/job/vllm_metrics.py`
- Modify: `src/mailroom_sandbox/cli.py` (register `run scrape-metrics --config <yaml> --label before|after`)
- Test: `tests/test_vllm_metrics.py` (create)

**Interfaces:**
- Produces:
  - `parse_prometheus(text: str) -> dict[str, float]` (summed by metric name, labels dropped)
  - `group_replicas(samples: list[dict[str, float]]) -> dict[str, dict[str, float]]`, keyed by `process_start_time_seconds`
  - `scrape(base_url: str, api_key: str, attempts: int = 12) -> dict`
  - The CLI writes `data/runtime/runs/<run_id>/vllm_metrics_<label>.json`.

- [ ] **Step 1: Write failing tests**

```python
from mailroom_sandbox.job.vllm_metrics import group_replicas, parse_prometheus, summarize

TEXT_A = """# HELP process_start_time_seconds x
process_start_time_seconds 1000.0
vllm:request_success_total{finished_reason="stop",model_name="m"} 40.0
vllm:request_success_total{finished_reason="length",model_name="m"} 2.0
vllm:num_preemptions_total{model_name="m"} 0.0
vllm:gpu_cache_usage_perc{model_name="m"} 0.31
vllm:prefix_cache_hits_total{model_name="m"} 600.0
vllm:prefix_cache_queries_total{model_name="m"} 1000.0
vllm:time_to_first_token_seconds_sum{model_name="m"} 21.0
vllm:time_to_first_token_seconds_count{model_name="m"} 42.0
"""
TEXT_B = TEXT_A.replace("1000.0\nvllm:request_success_total{finished_reason=\"stop\"", "2000.0\nvllm:request_success_total{finished_reason=\"stop\"")


def test_parse_sums_label_sets():
    m = parse_prometheus(TEXT_A)
    assert m["vllm:request_success_total"] == 42.0
    assert m["process_start_time_seconds"] == 1000.0


def test_group_by_process_start():
    reps = group_replicas([parse_prometheus(TEXT_A), parse_prometheus(TEXT_B), parse_prometheus(TEXT_A)])
    assert sorted(reps) == ["1000.0", "2000.0"]


def test_summarize_derives_rates():
    s = summarize(parse_prometheus(TEXT_A))
    assert s["requests"] == 42.0
    assert s["length_finishes"] == 2.0
    assert s["prefix_cache_hit_rate"] == 0.6
    assert s["ttft_mean_seconds"] == 0.5


def test_scrape_reports_unobserved_replicas():
    reps = group_replicas([parse_prometheus(TEXT_A)] * 5)
    from mailroom_sandbox.job.vllm_metrics import replica_coverage
    assert replica_coverage(reps, expected=2) == "replicas observed: 1 of 2"
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_vllm_metrics.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement** `src/mailroom_sandbox/job/vllm_metrics.py`:

```python
"""SAND-032: scrape vLLM Prometheus /metrics through the Modal web URL.

Modal routes each GET to one replica, so repeated scrapes sample replicas;
`process_start_time_seconds` is unique per vLLM process and groups them.
TTFT here is MEASURED by vLLM (histogram sum/count) — never inferred.
"""

from __future__ import annotations

import re
import time
from typing import Any

_LINE = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+([-+0-9.eE]+|NaN|\+Inf|-Inf)$")
_KEEP = (
    "process_start_time_seconds",
    "vllm:request_success_total",
    "vllm:num_preemptions_total",
    "vllm:gpu_cache_usage_perc",
    "vllm:kv_cache_usage_perc",
    "vllm:prefix_cache_hits_total",
    "vllm:prefix_cache_queries_total",
    "vllm:time_to_first_token_seconds_sum",
    "vllm:time_to_first_token_seconds_count",
    "vllm:prompt_tokens_total",
    "vllm:generation_tokens_total",
)


def parse_prometheus(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    length = 0.0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE.match(line)
        if not m:
            continue
        name, labels, value = m.group(1), m.group(2) or "", m.group(3)
        if name not in _KEEP:
            continue
        try:
            val = float(value)
        except ValueError:
            continue
        out[name] = out.get(name, 0.0) + val
        if name == "vllm:request_success_total" and 'finished_reason="length"' in labels:
            length += val
    out["length_finishes"] = length
    return out


def group_replicas(samples: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    reps: dict[str, dict[str, float]] = {}
    for s in samples:
        key = s.get("process_start_time_seconds")
        if key is None:
            continue
        reps[str(key)] = s  # later scrape of the same replica wins (monotonic counters)
    return reps


def replica_coverage(reps: dict[str, Any], *, expected: int) -> str:
    return f"replicas observed: {len(reps)} of {expected}"


def summarize(m: dict[str, float]) -> dict[str, float | None]:
    q = m.get("vllm:prefix_cache_queries_total") or 0.0
    c = m.get("vllm:time_to_first_token_seconds_count") or 0.0
    kv = m.get("vllm:kv_cache_usage_perc", m.get("vllm:gpu_cache_usage_perc"))
    return {
        "requests": m.get("vllm:request_success_total"),
        "length_finishes": m.get("length_finishes"),
        "preemptions": m.get("vllm:num_preemptions_total"),
        "kv_cache_usage_perc": kv,
        "prefix_cache_hit_rate": round(m["vllm:prefix_cache_hits_total"] / q, 4) if q else None,
        "ttft_mean_seconds": round(m["vllm:time_to_first_token_seconds_sum"] / c, 4) if c else None,
        "prompt_tokens": m.get("vllm:prompt_tokens_total"),
        "generation_tokens": m.get("vllm:generation_tokens_total"),
    }


def scrape(base_url: str, api_key: str, *, attempts: int = 12, expected: int = 1) -> dict[str, Any]:
    import httpx

    root = base_url.rstrip("/")
    root = root[: -len("/v1")] if root.endswith("/v1") else root
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    samples: list[dict[str, float]] = []
    errors: list[str] = []
    for _ in range(attempts):
        try:
            resp = httpx.get(f"{root}/metrics", headers=headers, timeout=15.0)
            resp.raise_for_status()
            samples.append(parse_prometheus(resp.text))
        except Exception as exc:  # noqa: BLE001 — report, never crash a run
            errors.append(f"{type(exc).__name__}: {str(exc)[:120]}")
        time.sleep(0.5)
    reps = group_replicas(samples)
    return {
        "coverage": replica_coverage(reps, expected=expected),
        "replicas": {k: summarize(v) for k, v in reps.items()},
        "errors": errors,
        "at": time.time(),
    }
```

CLI handler `_cmd_run_scrape_metrics`:
- Load the spec.
- Resolve `base = engine_base_url(spec)` from `mailroom_sandbox.job.preflight`, and `api_key = os.environ.get("VLLM_API_KEY", "")`.
- Call `scrape(base, api_key, expected=spec.engine.modal.max_containers)`.
- Write the JSON to `runtime_dir() / "runs" / spec.run_id / f"vllm_metrics_{args.label}.json"` and print the coverage line.

Add the `--label` argument (choices `before`, `after`) to this parser only.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_vllm_metrics.py tests/test_cli_wiring.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git branch --show-current
git add src/mailroom_sandbox/job/vllm_metrics.py src/mailroom_sandbox/cli.py tests/test_vllm_metrics.py
git commit -m "SAND-032: per-replica vLLM /metrics scrape (measured TTFT, KV, preemptions, prefix hits)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Nested per-class draws (prove, don't rebuild)

The single-bucket path (`strata: {buckets: [{doc_class: X, count: N}]}`) already draws a seeded shuffle-prefix (`corpus._seeded_prefix`), so n=20 ⊂ 50 ⊂ 100 holds by construction. Issue #38 describes the older `random.sample` code. This task pins the property in a test and forbids `sub_buckets` in SAND-032 configs (sub-bucket quotas are not nested across totals).

**Files:**
- Test: `tests/test_corpus.py` (append)

**Interfaces:**
- Consumes: `mailroom_sandbox.corpus.select_rows`.

- [ ] **Step 1: Write the test**

```python
def test_single_class_bucket_draws_are_nested():
    from mailroom_sandbox.corpus import select_rows

    rows = [
        {"id": f"d{i:04d}", "expected_doc_class": "correspondence", "expected_subclass": "email",
         "source_split": "train" if i % 3 else "test"}
        for i in range(1000)
    ] + [{"id": f"x{i}", "expected_doc_class": "contract", "expected_subclass": "nda",
          "source_split": "train"} for i in range(50)]

    def draw(n):
        chosen = select_rows(rows, strata={"buckets": [{"doc_class": "correspondence", "count": n}]},
                             sample_seed=42, limit=None)
        return {r["id"] for r in chosen}

    d20, d50, d100 = draw(20), draw(50), draw(100)
    assert len(d20) == 20 and len(d50) == 50 and len(d100) == 100
    assert d20 <= d50 <= d100
```

If `_stable_key` needs other fields, look at `corpus._stable_key` (L116) and add the fields it reads.

- [ ] **Step 2: Run**

Run: `pytest tests/test_corpus.py::test_single_class_bucket_draws_are_nested -v`
Expected: PASS immediately; this pins existing behavior. If it FAILS, stop: nesting is broken, and Task 9's configs must reference one locked 100-row file (`dataset.provider: file`) instead. Record which path applied in the commit message.

- [ ] **Step 3: Commit**

```bash
git branch --show-current
git add tests/test_corpus.py
git commit -m "SAND-032: pin nested single-class draws (20 ⊂ 50 ⊂ 100, seed 42) — closes issue #38 for bucket draws

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Offline Braintrust-Experiment-shaped rows + dispose

**Files:**
- Create: `src/mailroom_sandbox/job/bt_offline.py`
- Modify: `src/mailroom_sandbox/cli.py` (register `run export-bt --config`, `run dispose --config --report <path>`)
- Test: `tests/test_bt_offline.py` (create)

**Interfaces:**
- Consumes: `RunStore` items (Task 4), lock, serving record.
- Produces:
  - `write_experiment(store, *, out_root: Path, git_commit: str) -> Path`: writes `experiment.json` + `rows.jsonl`
  - `dispose(run_id: str, *, out_root: Path, report: Path, is_tracked: Callable[[Path], bool]) -> bool`

- [ ] **Step 1: Write failing tests**

```python
import json
from pathlib import Path

import pytest

from mailroom_sandbox.job.bt_offline import dispose, write_experiment
from mailroom_sandbox.job.checkpoint import RunStore


def _store(tmp_path):
    s = RunStore(tmp_path / "runs" / "sand032-x")
    s.lock_path.write_text(json.dumps({"run_id": "sand032-x", "engine": {
        "model": "Qwen/Qwen3-8B-AWQ", "vllm": {"kv_cache_dtype": "fp8"},
        "modal": {"gpu": "L4", "max_containers": 2}}}))
    s.append_item({"item_id": "a", "ok": True, "pred": {"k": 1},
                   "score": {"overall_extraction_score": 0.4}, "latency_ms": 1500.0,
                   "prompt_tokens": 100, "completion_tokens": 20})
    return s


def test_write_experiment_shape(tmp_path):
    out = write_experiment(_store(tmp_path), out_root=tmp_path / "bt", git_commit="abc123")
    meta = json.loads((out / "experiment.json").read_text())
    assert meta["name"] == "sand032-x"
    assert meta["metadata"]["engine"]["vllm"]["kv_cache_dtype"] == "fp8"
    assert meta["metadata"]["git_commit"] == "abc123"
    row = json.loads((out / "rows.jsonl").read_text().splitlines()[0])
    assert set(row) >= {"id", "input", "output", "expected", "scores", "metrics", "metadata"}
    assert row["scores"]["overall_extraction_score"] == 0.4
    assert row["metrics"]["latency_seconds"] == 1.5


def test_dispose_refuses_untracked_report(tmp_path):
    out = write_experiment(_store(tmp_path), out_root=tmp_path / "bt", git_commit="abc")
    with pytest.raises(RuntimeError, match="not tracked"):
        dispose("sand032-x", out_root=tmp_path / "bt", report=Path("reports/x.md"),
                is_tracked=lambda p: False)
    assert out.exists()


def test_dispose_removes_after_tracked_report(tmp_path):
    out = write_experiment(_store(tmp_path), out_root=tmp_path / "bt", git_commit="abc")
    assert dispose("sand032-x", out_root=tmp_path / "bt", report=Path("reports/x.md"),
                   is_tracked=lambda p: True) is True
    assert not out.exists()
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_bt_offline.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement** `src/mailroom_sandbox/job/bt_offline.py`:

```python
"""SAND-032: Braintrust-Experiment-shaped rows, written OFFLINE (no upload).

Lives under data/runtime/ (gitignored). Reports are built from these rows,
committed, and then the rows are disposed. `dispose` refuses until the
report is tracked in git, so evidence can't vanish before it is recorded.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from mailroom_sandbox.job.checkpoint import RunStore


def write_experiment(store: RunStore, *, out_root: Path, git_commit: str) -> Path:
    lock = store.read_lock() or {}
    run_id = str(lock.get("run_id") or store.dir.name)
    out = Path(out_root) / run_id
    out.mkdir(parents=True, exist_ok=True)
    meta = {
        "name": run_id,
        "project": "mailroom-sandbox-offline",
        "metadata": {
            "engine": lock.get("engine") or {},
            "dataset": lock.get("dataset") or {},
            "prompt": lock.get("prompt") or {},
            "git_commit": git_commit,
        },
    }
    (out / "experiment.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    lines = []
    for item in store.read_items():
        latency = item.get("latency_ms")
        lines.append(json.dumps({
            "id": item.get("item_id"),
            "input": {"doc_id": item.get("item_id")},
            "output": item.get("pred"),
            "expected": (item.get("score") or {}).get("expected"),
            "scores": {k: v for k, v in (item.get("score") or {}).items()
                       if isinstance(v, (int, float)) and not isinstance(v, bool)},
            "metrics": {
                "latency_seconds": None if latency is None else round(float(latency) / 1000.0, 6),
                "prompt_tokens": item.get("prompt_tokens"),
                "completion_tokens": item.get("completion_tokens"),
            },
            "metadata": {"ok": item.get("ok"), "error": item.get("error")},
        }, default=str))
    (out / "rows.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return out


def git_tracked(path: Path) -> bool:
    res = subprocess.run(["git", "ls-files", "--error-unmatch", str(path)],
                         capture_output=True, text=True)
    return res.returncode == 0


def dispose(run_id: str, *, out_root: Path, report: Path,
            is_tracked: Callable[[Path], bool] = git_tracked) -> bool:
    if not is_tracked(Path(report)):
        raise RuntimeError(f"report {report} is not tracked in git — commit it before disposing {run_id}")
    target = Path(out_root) / run_id
    if target.exists():
        shutil.rmtree(target)
        return True
    return False
```

CLI:
- `run export-bt --config X` → `write_experiment(RunStore(runtime_dir()/"runs"/run_id), out_root=runtime_dir()/"bt_experiments", git_commit=<git rev-parse HEAD>)`.
- `run dispose --config X --report reports/...md` → `dispose(...)`.

Match the existing store-path helper: check how `_cmd_run_status` builds its `RunStore` (`grep -n "RunStore(" src/mailroom_sandbox/cli.py`) and reuse that exact call.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_bt_offline.py tests/test_cli_wiring.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git branch --show-current
git add src/mailroom_sandbox/job/bt_offline.py src/mailroom_sandbox/cli.py tests/test_bt_offline.py
git commit -m "SAND-032: offline Braintrust-Experiment-shaped rows + guarded dispose

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Funding projection math

**Files:**
- Create: `src/mailroom_sandbox/job/funding.py`
- Test: `tests/test_funding.py` (create)

**Interfaces:**
- Produces:
  - `UnitCost(doc_class: str, usd_per_doc: float, rel_spread: float)`
  - `full_corpus_usd(units: dict[str, UnitCost], rows: dict[str, int], *, overhead_usd: float, seeds: int) -> tuple[float, float, float]`, returning (low, mid, high)
  - `eval_iteration_usd(unit: UnitCost, n: int, *, overhead_usd: float) -> float`
  - `with_contingency(usd: float, rate: float) -> float`
  - `tier_budget(tier_usd: float, *, contingency: float, line_items: dict[str, float]) -> dict[str, int]` (how many of each item fit)

- [ ] **Step 1: Write failing tests**

```python
import pytest

from mailroom_sandbox.job.funding import (
    UnitCost, eval_iteration_usd, full_corpus_usd, tier_budget, with_contingency,
)

UNITS = {"correspondence": UnitCost("correspondence", 0.0025, 0.10),
         "contract": UnitCost("contract", 0.019, 0.20)}
ROWS = {"correspondence": 1000, "contract": 600}


def test_full_corpus_mid_is_formula():
    low, mid, high = full_corpus_usd(UNITS, ROWS, overhead_usd=0.5, seeds=1)
    assert mid == pytest.approx(1000 * 0.0025 + 600 * 0.019 + 0.5)
    assert low < mid < high


def test_full_corpus_scales_with_seeds():
    _, mid1, _ = full_corpus_usd(UNITS, ROWS, overhead_usd=0.5, seeds=1)
    _, mid3, _ = full_corpus_usd(UNITS, ROWS, overhead_usd=0.5, seeds=3)
    assert mid3 == pytest.approx(3 * (mid1 - 0.5) + 0.5)


def test_missing_class_unit_cost_is_loud():
    with pytest.raises(KeyError, match="insurance_claim"):
        full_corpus_usd(UNITS, {**ROWS, "insurance_claim": 1100}, overhead_usd=0, seeds=1)


def test_eval_iteration_and_contingency():
    assert eval_iteration_usd(UNITS["contract"], 50, overhead_usd=0.1) == pytest.approx(1.05)
    assert with_contingency(100.0, 0.2) == pytest.approx(120.0)


def test_tier_budget_counts_whole_items():
    fit = tier_budget(200.0, contingency=0.2, line_items={"full_corpus_pass": 25.0, "prompt_iter": 1.0})
    # 200 / 1.2 = 166.67 spendable; greedy in given order: 6 passes (150) then 16 iters
    assert fit == {"full_corpus_pass": 6, "prompt_iter": 16}
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_funding.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement** `src/mailroom_sandbox/job/funding.py`:

```python
"""SAND-032: turn measured unit costs into funding line items.

Every projection is a transparent formula over measured inputs; spread
comes from the measured run-to-run variance (rel_spread), never a guess.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UnitCost:
    doc_class: str
    usd_per_doc: float
    rel_spread: float  # e.g. 0.10 = ±10% from repeat/paired runs


def full_corpus_usd(units: dict[str, UnitCost], rows: dict[str, int], *,
                    overhead_usd: float, seeds: int) -> tuple[float, float, float]:
    mid = low = high = 0.0
    for cls, n in rows.items():
        if cls not in units:
            raise KeyError(f"no measured unit cost for class {cls}")
        u = units[cls]
        base = n * u.usd_per_doc * seeds
        mid += base
        low += base * (1 - u.rel_spread)
        high += base * (1 + u.rel_spread)
    return (low + overhead_usd, mid + overhead_usd, high + overhead_usd)


def eval_iteration_usd(unit: UnitCost, n: int, *, overhead_usd: float) -> float:
    return n * unit.usd_per_doc + overhead_usd


def with_contingency(usd: float, rate: float) -> float:
    return usd * (1 + rate)


def tier_budget(tier_usd: float, *, contingency: float,
                line_items: dict[str, float]) -> dict[str, int]:
    spendable = tier_usd / (1 + contingency)
    out: dict[str, int] = {}
    for name, cost in line_items.items():
        count = int(spendable // cost) if cost > 0 else 0
        out[name] = count
        spendable -= count * cost
    return out
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_funding.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git branch --show-current
git add src/mailroom_sandbox/job/funding.py tests/test_funding.py
git commit -m "SAND-032: funding projection math (full-corpus, eval iteration, tiers)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: SAND-032 run configs, posture rows, benchmark gate, governance card

**Files:**
- Create: `config/runs/sand032-*.yaml` (15 files, table below), `config/suites/sand032-sweep.yaml`
- Modify: `src/mailroom_sandbox/job/specialist_posture.py` (SAND-032 rows; concurrency band)
- Modify: `src/mailroom_sandbox/job/benchmark_check.py` (allowlists; fp8 + drift assertions; `--modal-profile`)
- Modify: `src/mailroom_sandbox/cli.py` (`--modal-profile` on `common`, passed as `expected_modal_profile`)
- Modify: `governance/TASKS.md` (SAND-032 card; bump Next ID to `SAND-033`)
- Test: `tests/test_sand032_configs.py` (create), `tests/test_specialist_posture.py`

**Interfaces:**
- Consumes: `VLLMSpec` fields (Task 2), `deploy_env.env_drift` (Task 2).
- Produces:
  - `SAND032_RUNS: frozenset[str]` in `specialist_posture.py`
  - `validate_mapping` allowing `concurrency ≤ 8 × replicas`, where the posture row carries `"replicas"`
  - `check_benchmark_posture(..., env: Mapping[str, str] | None = None)`

**Config matrix.** Every file starts from this template:

```yaml
schema: sandbox.run/v1
run_id: <run_id>
task: <task>
profile: modal-vllm
prompt:
  default: {source: code-default}
  agents:
    <agent>: {source: local, file: <prompt_file>}
dataset:
  provider: huggingface
  repo: Lucius-Morningstar/mailroom-dataset
  config: ground_truth
  split: all
  revision: ed7576b676343e0b402ec5412cded301e629bdee
  strata:
    buckets:
      - {doc_class: <doc_class>, count: <n>}
  limit: <n>
  sample_seed: 42
engine:
  kind: modal-vllm
  model: <model>
  vllm:
    max_model_len: <ctx>
    gpu_memory_utilization: 0.90
    max_num_seqs: <seqs>
    enable_prefix_caching: true
    enforce_eager: <eager>
    quantization: <quant>
    revision: ""
    kv_cache_dtype: <kv>
    enable_thinking: <thinking>
    cudagraph_capture_sizes: <graphs>
    max_inputs: 32
  modal:
    app: sandbox-vllm
    gpu: L4
    image_tag: v0.29.0
    scaledown_seconds: 120
    max_containers: <rep>
    min_containers: <rep>
    prewarm: true
job:
  mode: endpoint
  mock: false
  max_retries: 2
  fail_fast: false
  concurrency: <conc>
  cost_cap_usd: <cap>
  max_wall_seconds: <wall>
trace:
  sink: none
  otlp: false
  environment: sand032
  tags: [sandbox, sand032, qwen3-8b, l4]
```

**Ladder rungs** (`task: correspondence_specialist`, `agent: correspondence_specialist`, `prompt_file: correspondence_specialist_production`, `doc_class: correspondence`, n=20, model AWQ, ctx 32768, rep 1, conc 8, cap 0.15, wall 1800):

| run_id | quant | thinking | kv | seqs | eager | graphs |
| --- | --- | --- | --- | --- | --- | --- |
| sand032-l0-baseline | awq | null | "" | 6 | true | [] |
| sand032-l1-nothink | awq | false | "" | 6 | true | [] |
| sand032-l2-marlin | awq_marlin | false | "" | 6 | true | [] |
| sand032-l3-fp8kv | awq_marlin | false | fp8 | 6 | true | [] |
| sand032-l4-seqs16 | awq_marlin | false | fp8 | 16 | true | [] |
| sand032-l5-graphs | awq_marlin | false | fp8 | 16 | false | [1,2,4,8,16] |

**Frozen-config runs.** These use the Stage-1 winner. Until Stage 1 runs, the winner is assumed to be L5. Task 11 Step 5 edits these files if a rung is reverted.

| run_id | task / agent | prompt_file | doc_class | n | rep | conc | cap | wall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sand032-s2a-corr100-1rep | correspondence_specialist | correspondence_specialist_production | correspondence | 100 | 1 | 8 | 0.60 | 3600 |
| sand032-s2b-corr100-2rep | correspondence_specialist | correspondence_specialist_production | correspondence | 100 | 2 | 16 | 0.60 | 3600 |
| sand032-s3-corr50 | correspondence_specialist | correspondence_specialist_production | correspondence | 50 | 2 | 16 | 0.30 | 2400 |
| sand032-s3-insurance50 | insurance_claims_specialist | insurance_claims_specialist_simplified | insurance_claim | 50 | 2 | 16 | 0.60 | 3600 |
| sand032-s3-corporate50 | corporate_records_specialist | corporate_records_specialist_simplified | corporate_record | 50 | 2 | 16 | 0.70 | 3600 |
| sand032-s3-merger50 | merger_agreement_specialist | merger_agreement_specialist_simplified | merger_agreement | 50 | 2 | 16 | 1.40 | 5400 |
| sand032-s3-contracts50 | contracts_specialist | contracts_specialist_v33_simplified | contract | 50 | 2 | 16 | 1.40 | 5400 |
| sand032-s3-corr50-repeat | correspondence_specialist | correspondence_specialist_production | correspondence | 50 | 2 | 16 | 0.30 | 2400 |

**bf16 arm:** `sand032-s4-corr20-bf16` uses correspondence n=20, model `Qwen/Qwen3-8B`, ctx 16384, quant "", thinking false, kv "", seqs 6, eager true, graphs [], rep 1, conc 8, cap 0.20, wall 2400.

Before writing the table, verify that each `prompt_file` exists in `config/prompts/` (`ls config/prompts | grep -E "specialist_(production|simplified|v33)"`). If a stem differs, use the stem the latest AWQ runs used (`grep -n "file:" config/runs/run-20-*-awq*.yaml`).

- [ ] **Step 1: Write failing tests** `tests/test_sand032_configs.py`:

```python
from pathlib import Path

import pytest

from mailroom_sandbox.job.spec import load_run_spec
from mailroom_sandbox.job.specialist_posture import SAND032_RUNS, validate_mapping, SPECIALIST_POSTURE
from mailroom_sandbox.paths import config_dir

RUNS = sorted((config_dir() / "runs").glob("sand032-*.yaml"))
STAGE23 = [p for p in RUNS if p.stem.startswith(("sand032-s2", "sand032-s3"))]


def test_fifteen_configs_exist():
    assert len(RUNS) == 15
    assert {p.stem for p in RUNS} == set(SAND032_RUNS)


@pytest.mark.parametrize("path", RUNS, ids=lambda p: p.stem)
def test_config_parses_and_pins(path):
    spec = load_run_spec(path)
    assert spec.dataset.split == "all"
    assert spec.dataset.sample_seed == 42
    assert spec.dataset.revision == "ed7576b676343e0b402ec5412cded301e629bdee"
    buckets = spec.dataset.strata["buckets"]
    assert len(buckets) == 1 and "sub_buckets" not in buckets[0]
    assert spec.engine.modal.image_tag == "v0.29.0"
    assert spec.engine.modal.min_containers == spec.engine.modal.max_containers


@pytest.mark.parametrize("path", STAGE23, ids=lambda p: p.stem)
def test_stage23_pins_fp8_kv_awq(path):
    spec = load_run_spec(path)
    assert spec.engine.vllm.kv_cache_dtype == "fp8"
    assert spec.engine.model == "Qwen/Qwen3-8B-AWQ"
    assert spec.engine.vllm.max_model_len == 32768


def test_merger_uses_merger_specialist():
    spec = load_run_spec(config_dir() / "runs" / "sand032-s3-merger50.yaml")
    assert spec.task == "merger_agreement_specialist"


def test_posture_rows_valid_including_c16_on_two_replicas():
    assert validate_mapping({k: SPECIALIST_POSTURE[k] for k in SAND032_RUNS}) == []


def test_c16_on_one_replica_rejected():
    row = dict(SPECIALIST_POSTURE["sand032-s2b-corr100-2rep"], replicas=1)
    assert validate_mapping({"x": row})
```

In `tests/test_specialist_posture.py`, if an existing test asserts that every posture row has `concurrency ≤ 8`, update it to `≤ 8 * row.get("replicas", 1)`.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_sand032_configs.py -v`
Expected: FAIL (no configs, no `SAND032_RUNS`).

- [ ] **Step 3: Write the 15 YAMLs** from the template and tables above, plus `config/suites/sand032-sweep.yaml`. Copy the schema from an existing suite (`cat config/suites/*.yaml | head -40`) and list the six `sand032-s3-*` configs in table order.

- [ ] **Step 4: Posture rows.** In `specialist_posture.py`, after `SPECIALIST_POSTURE`:

```python
# SAND-032: ladder / scale-out / sweep / bf16 rows, generated from one table so
# the caps and budgets stay consistent with config/runs/sand032-*.yaml.
_SAND032_AGENTS = {
    "correspondence": ("correspondence_specialist", "correspondence_specialist_production", 2048, 3500, 600),
    "insurance_claim": ("insurance_claims_specialist", "insurance_claims_specialist_simplified", 3072, 5000, 900),
    "corporate_record": ("corporate_records_specialist", "corporate_records_specialist_simplified", 3072, 8000, 1500),
    "merger_agreement": ("merger_agreement_specialist", "merger_agreement_specialist_simplified", 4096, 11000, 1200),
    "contract": ("contracts_specialist", "contracts_specialist_v33_simplified", 8192, 11000, 1200),
}
_SAND032_TABLE = [
    # run_id, doc_class, n, replicas, concurrency, cap, wall, max_model_len
    *[(f"sand032-{rung}", "correspondence", 20, 1, 8, 0.15, 1800, 32768)
      for rung in ("l0-baseline", "l1-nothink", "l2-marlin", "l3-fp8kv", "l4-seqs16", "l5-graphs")],
    ("sand032-s2a-corr100-1rep", "correspondence", 100, 1, 8, 0.60, 3600, 32768),
    ("sand032-s2b-corr100-2rep", "correspondence", 100, 2, 16, 0.60, 3600, 32768),
    ("sand032-s3-corr50", "correspondence", 50, 2, 16, 0.30, 2400, 32768),
    ("sand032-s3-insurance50", "insurance_claim", 50, 2, 16, 0.60, 3600, 32768),
    ("sand032-s3-corporate50", "corporate_record", 50, 2, 16, 0.70, 3600, 32768),
    ("sand032-s3-merger50", "merger_agreement", 50, 2, 16, 1.40, 5400, 32768),
    ("sand032-s3-contracts50", "contract", 50, 2, 16, 1.40, 5400, 32768),
    ("sand032-s3-corr50-repeat", "correspondence", 50, 2, 16, 0.30, 2400, 32768),
    ("sand032-s4-corr20-bf16", "correspondence", 20, 1, 8, 0.20, 2400, 16384),
]
SAND032_RUNS: frozenset[str] = frozenset(r[0] for r in _SAND032_TABLE)
for _rid, _cls, _n, _rep, _conc, _cap, _wall, _ctx in _SAND032_TABLE:
    _agent, _prompt, _mt, _pt, _ct = _SAND032_AGENTS[_cls]
    SPECIALIST_POSTURE[_rid] = {
        "task": _agent, "doc_class": _cls, "agent": _agent, "prompt_file": _prompt,
        "concurrency": _conc, "replicas": _rep, "max_model_len": _ctx,
        "max_tokens": _mt, "max_input_chars": _input_chars_for(_mt, _pt, _ctx),
        "cost_cap_usd": _cap, "max_wall_seconds": _wall,
        "tokens_assumed": {"prompt": _pt, "completion": _ct},
        "sec_per_doc": {"low": 5.0, "likely": 15.0, "high": 60.0},
        "rationale": "SAND-032 ladder/scale-out/sweep (docs/superpowers/specs/2026-09-27-qwen3-l4-serving-ladder-design.md)",
    }
    SPECIALIST_LIMIT_BY_RUN[_rid] = _n
```

`AGENT_GENERATION_BUDGETS` is last-writer-wins per agent, and a prior row pins contracts at a larger budget. To keep existing runs' budgets unchanged, build `AGENT_GENERATION_BUDGETS` before this block, or skip `sand032-*` rows when building it. Then confirm the existing posture tests still pass.

Place this block after `SPECIALIST_LIMIT_BY_RUN` is defined and before `AGENT_GENERATION_BUDGETS` is built with a filter `if not run_id.startswith("sand032-")`. The overlay (`config/taxonomy.overlay.yaml`) is what actually sets generation budgets at runtime. Check that its entries for the five agents are ≥ the `max_tokens` above: `grep -n "max_tokens" config/taxonomy.overlay.yaml`. If contracts is below 8192, pass `SANDBOX_AGENT_KNOBS` in the runbook (Task 12) rather than editing the overlay globally.

In `validate_mapping`, replace the band check:

```python
        conc = int(row["concurrency"])
        ceiling = 8 * max(1, int(row.get("replicas", 1)))
        if not 2 <= conc <= ceiling:
            errors.append(f"{run_id}: concurrency={conc} outside specialist band [2,{ceiling}]")
```

- [ ] **Step 5: Benchmark gate.** In `benchmark_check.py`:
- Import `SAND032_RUNS`.
- Add the 2-replica SAND-032 ids to `TWO_GPU_RUNS` and the 1-replica ones to `PINNED_ONE_GPU_RUNS`.
- Add an `env: Mapping[str, str] | None = None` kwarg (default `os.environ`).
- When `spec.run_id in SAND032_RUNS`, run the block below. Also allow `max_num_seqs` / `concurrency` from posture instead of `BENCHMARK_EXPECTED` for these ids. Check `_check_spec_pins` (L340–500) for any `concurrency == 4` / `limit == 30` equality and route SAND-032 ids through `expected_concurrency` / `expected_limit`, which already read the posture rows.

```python
    if spec is not None and spec.run_id in SAND032_RUNS:
        from mailroom_sandbox.job.deploy_env import env_drift

        for msg in env_drift(spec, env if env is not None else os.environ):
            errors.append(f"deploy env drift — {msg} (run `sandbox run deploy-env --config …`)")
        if spec.run_id.startswith(("sand032-s2", "sand032-s3")) and spec.engine.vllm.kv_cache_dtype != "fp8":
            errors.append(f"{spec.run_id}: kv_cache_dtype must be fp8 for 2×L4 / scale-out runs")
```

Add a test to `tests/test_sand032_configs.py`:

```python
def test_benchmark_check_flags_env_drift(monkeypatch):
    from mailroom_sandbox.job.benchmark_check import check_benchmark_posture
    from mailroom_sandbox.job.deploy_env import spec_env

    spec = load_run_spec(config_dir() / "runs" / "sand032-s2b-corr100-2rep.yaml")
    env = dict(spec_env(spec)); env["MODAL_VLLM_KV_CACHE_DTYPE"] = ""
    rep = check_benchmark_posture(spec=spec, require_hermes=False, env=env)
    assert any("MODAL_VLLM_KV_CACHE_DTYPE" in e for e in rep["errors"])
```

CLI: add `common.add_argument("--modal-profile", default=None, help="benchmark-check: required active Modal profile (e.g. exios66)")`. In `_cmd_run_benchmark_check`, pass `expected_modal_profile=args.modal_profile` to `check_benchmark_posture` (and the suite variant); when it is set, `require_hermes` is ignored, as the function already does.

- [ ] **Step 6: Governance.** In `governance/TASKS.md`, add a row after SAND-031 in the same table format:

```
| SAND-032 | Qwen3-8B-AWQ L4 serving ladder → 2-replica scale-out → 5-specialist n=50 sweep + bf16 arm; funding evidence ($5 cap, Modal profile exios66, public HF data only) | claude | in progress | Spec docs/superpowers/specs/2026-09-27-qwen3-l4-serving-ladder-design.md; plan docs/superpowers/plans/2026-09-27-qwen3-l4-serving-ladder.md. Related: SAND-028, SAND-030, SAND-031, issue #38. |
```

Change `**Next ID: \`SAND-032\`**` to `**Next ID: \`SAND-033\`**`. Run `pytest tests/test_governance_sand.py -v`.

- [ ] **Step 7: Run the whole suite**

Run: `pytest -q`
Expected: all PASS (live tests skipped). Also run `sandbox runbook check` and `for f in config/runs/sand032-*.yaml; do sandbox run preflight --config "$f" || echo "FAIL $f"; done`. Expected: no FAIL lines. Offline preflight needs `data/cache` from `sandbox datasets pull`; if the cache is missing, preflight reports that and it is expected until Task 10.

- [ ] **Step 8: Commit and push**

```bash
git branch --show-current
git add config/runs/sand032-*.yaml config/suites/sand032-sweep.yaml src/mailroom_sandbox/job/specialist_posture.py src/mailroom_sandbox/job/benchmark_check.py src/mailroom_sandbox/cli.py governance/TASKS.md tests/test_sand032_configs.py tests/test_specialist_posture.py
git commit -m "SAND-032: ladder/scale-out/sweep/bf16 run configs, posture rows, fp8+drift benchmark gate, SAND-032 card

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin sand-032-qwen3-l4-ladder
```

Open a PR for Part A: `gh pr create --repo Exios66/local-mailroom-sandbox --base main --head sand-032-qwen3-l4-ladder`, with the title "SAND-032 Part A: spec-driven serving knobs, replica-aware costs, offline evidence rows" and a body listing Tasks 1–9. Part B spends money; do not start it until this PR's tests are green.

---

## Part B — Live execution (spends money; `exios66` profile)

Every live task begins with the **spend preamble**:

```bash
git branch --show-current                       # sand-032-qwen3-l4-ladder
modal profile current                           # must print exios66
set -a; eval "$(sandbox run deploy-env --config config/runs/<RUN>.yaml)"; set +a
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"
export VLLM_API_KEY="$MODAL_VLLM_API_TOKEN"
export SANDBOX_PROFILE=modal-vllm
sandbox run benchmark-check --config config/runs/<RUN>.yaml --modal-profile exios66
```

**Rules:**
- Keep a running spend ledger in `reports/serving/SAND-32/SAND032-SPEND-LEDGER.md`: one row per run with `run_span_usd_lower_bound` (the serving record; a LOWER bound — renamed from `billed_span_usd` in the Part A review), the wall-clock deploy→`modal app stop` timestamps for each fleet (times replicas × $0.80/hr = the operator's upper estimate), and a Modal usage-page reading after each stage, supplied by the user (ground truth).
- Stop and report if the ledger ever exceeds the stage's stop rule, or $4.50 in total.

### Task 10: Account readiness + flag probe (≈$0)

- [ ] **Step 1:** `modal profile current` → `exios66`. `modal secret list` must show `huggingface-secret`. If it's missing, **stop and ask the user** to run `modal secret create huggingface-secret HF_TOKEN=<token>` themselves; Claude never handles the token.
- [ ] **Step 2:** Pre-warm weights (CPU only), once per model:

```bash
MODAL_VLLM_MODEL=Qwen/Qwen3-8B-AWQ modal run deploy/modal_vllm.py::download_model
MODAL_VLLM_MODEL=Qwen/Qwen3-8B modal run deploy/modal_vllm.py::download_model
```

- [ ] **Step 3:** Flag probe on the pinned image, CPU only. Add a tiny `@app.function(image=vllm_image, timeout=300)` named `vllm_help` to `deploy/modal_vllm.py` that runs `vllm serve --help=all` and prints stdout (cover it with a stub test asserting the function exists). Then run `modal run deploy/modal_vllm.py::vllm_help | tee /tmp/claude-vllm-help.txt` and check each flag: `grep -E -- "--default-chat-template-kwargs|--kv-cache-dtype|--compilation-config|--max-num-batched-tokens|--chat-template" /tmp/claude-vllm-help.txt`.
  - If `--default-chat-template-kwargs` is missing, add `deploy/templates/qwen3_nothink.jinja`: copy the Qwen3 template from the HF cache and change the thinking default to off. Mount it with `image.add_local_file(..., "/templates/qwen3_nothink.jinja")`, and set `enable_thinking: null` plus `MODAL_VLLM_CHAT_TEMPLATE=/templates/qwen3_nothink.jinja` in rungs L1+ (add a `chat_template` field to `VLLMSpec`/`spec_env`, with a test). Commit.
- [ ] **Step 4:** Datasets: `sandbox datasets pull` (the LIVE HF pull of public data, pinned revision), then `sandbox run preflight --config` for all 15 configs. All must pass.
- [ ] **Step 5:** Verify `@modal.concurrent` necessity. Read Modal's docs on `web_server` input concurrency (WebFetch `https://modal.com/docs/guide/concurrent-inputs`). If a web_server container handles one input at a time by default, keep `max_inputs: 32` in all configs. If not, keep it anyway, since it's harmless and explicit, and note the finding in the ledger. Either way, record the merger-run connection-drop hypothesis status.
- [ ] **Step 6:** Commit the ledger header and any fallback template. Push with the explicit refspec.

### Task 11: Stage 1 — knob ladder (≈$0.35; stop at $0.50)

For each rung `R` in `l0-baseline, l1-nothink, l2-marlin, l3-fp8kv, l4-seqs16, l5-graphs`:

- [ ] **Step 1:** Run the spend preamble with `config/runs/sand032-R.yaml`. Then deploy: `modal deploy deploy/modal_vllm.py`, set `VLLM_BASE_URL` to the printed URL + `/v1`, and run `sandbox run preflight --config … --live` (records the cold boot).
- [ ] **Step 2:** `sandbox run scrape-metrics --config … --label before`, then `sandbox run start --config … --job-mode endpoint --watch`, then `sandbox run scrape-metrics --config … --label after`.
- [ ] **Step 3:** Write the serving record with the existing `sandbox metrics serving` command (cli.py ~L2387) and export offline rows with `sandbox run export-bt --config …`. Stop the app: `modal app stop sandbox-vllm`.
- [ ] **Step 4:** Apply the gate, paired on the same 20 doc ids vs L0: ok 20/20; mean score ≥ L0 − 0.02; schema_valid ≥ L0 − 0.05; `gpu_cost_per_document` ≤ the previous kept rung. A failing rung (other than L3) is reverted: the next rung's YAML drops that change. Record every rung, kept or reverted, in `reports/serving/SAND-32/SAND032-LADDER.md`: boot s, wall, p50/p95, measured TTFT, tok/s, KV usage, preemptions, length finishes, score, schema_valid, $/doc, run_span_usd_lower_bound.
- [ ] **Step 5:** Freeze. Edit the eight `sand032-s2*`/`sand032-s3*` YAMLs so their `vllm:` blocks equal the best passing stack, always with `kv_cache_dtype: fp8`. Re-run `pytest tests/test_sand032_configs.py`, then commit and push.

### Task 12: Stage 2 — scale-out (correspondence n=100)

- [ ] **Step 1:** Run `sand032-s2a-corr100-1rep` with the Task 11 Steps 1–3 flow. This is the recorded production cold boot.
- [ ] **Step 2:** Run `sand032-s2b-corr100-2rep`, redeploying with its env (max=min=2). The scrape must show `replicas observed: 2 of 2`. If it shows 1 of 2, rerun the scrape up to 3×, then report the coverage honestly.
- [ ] **Step 3:** Write `reports/serving/SAND-32/SAND032-SCALE-OUT.md`: wall ratio, $/doc for both, tok/s, per-replica request split, p50/p95, TTFT, KV peak. **Leave the app warm** (min=2) for Task 13 and do not stop it.

### Task 13: Stage 3 — 5-specialist sweep (warm 2-replica fleet, ≤ $4.50 projected)

- [ ] **Step 1:** Before each class, compute the projection: `spent_so_far + measured_usd_per_doc(prev comparable class, or the 20-doc AWQ reports for first-time classes) × n`. If it exceeds $4.50, rewrite merger/contracts to n=20: set `count`/`limit` to 20 in their YAMLs and `SPECIALIST_LIMIT_BY_RUN`, then commit.
- [ ] **Step 2:** Run in order: corr50 → insurance50 → corporate50 → merger50 → contracts50 → corr50-repeat. The env is unchanged across these (same serving block), so **no redeploy**; only `sandbox run start` + scrapes + `export-bt` per class. Contracts needs `SANDBOX_AGENT_KNOBS='{"contracts_specialist":{"max_tokens":8192}}'` if the Task 9 overlay check found the budget below 8192.
- [ ] **Step 3:** After the last run: `modal app stop sandbox-vllm`. Ask the user for the Modal usage-page total and record it in the ledger.
- [ ] **Step 4:** Write per-class reports (`reports/SAND-32/<class>/SAND032-S3-<CLASS>50-REPORT.md`) and `reports/serving/SAND-32/SAND032-SWEEP.md`: the 5-class scorecard, plus repeat-run variance (paired per-doc score delta and $/doc delta between corr50 and corr50-repeat). Contracts is marked serving-only.

### Task 14: Stage 4 — bf16 arm (skip if ledger > $4.40)

- [ ] **Step 1:** Run `sand032-s4-corr20-bf16` (deploy with its env, run, scrape, export, stop).
- [ ] **Step 2:** Add the paired AWQ-vs-bf16 score delta on the same 20 ids to `reports/serving/SAND-32/SAND032-LADDER.md`.

### Task 15: Summary, funding proposal, review, disposal

- [ ] **Step 1:** Write `reports/serving/QWEN3-L4-LADDER-SUMMARY.md`: ladder table, scale-out table, 5-class scorecard, bf16 delta, final spend (billed vs estimated).
- [ ] **Step 2:** Write `reports/funding/AMFAM-BUDGET-PROPOSAL.md` per spec §5a:
  - Compute every projection with `mailroom_sandbox.job.funding`, from measured `UnitCost`s (`rel_spread` from the repeat run) and `FAMILY_CLASS_COUNTS`. Show each formula with its inputs.
  - Label model-comparison costs *projected*.
  - Include the data statement (public HF data only; no AmFam data; partner data would need a DSA and is out of scope).
  - Include the prior-investment line only if the user supplies a figure.
- [ ] **Step 3:** Adversarial review. Dispatch a review subagent using `.opencode/agents/adversarial-reviewer.md` as its instructions, with the reports + serving JSONs + items as evidence. Fix every claim it can't trace to a record.
- [ ] **Step 4:** Commit the reports, then run `sandbox run dispose --config <each> --report <its report>` for all runs. Commit ledger closure, push, and open the Part B PR.

---

## Self-review notes

- **Spec coverage:**
  - §3 Stage 0 rows → Tasks 1–9. Deploy knobs → 1; spec fields/env → 2; live verification → 4 (argv in record) and 10 (flag probe); cost cap → 3; metrics → 4 and 5; nested sampling → 6; BT offline → 7; run configs → 9; governance → 9; proxy robustness → 1 (`max_inputs`), 4 (billed span) and 10 Step 5.
  - Stages 1–4 → Tasks 11–14. §5/§5a → Task 15. Budget gates → Part B rules and Task 13 Step 1.
- **Known coupling:** Task 11 Step 5 rewrites Task 9 YAMLs. `test_stage23_pins_fp8_kv_awq` guards the invariants that must survive the rewrite.
- **Assumption to verify in Task 10:** the vLLM v0.29.0 flag names. The fallback path for the thinking flag is specified.
