"""Run-spec models and canonical hashing for the sandbox job CLI (DMR-027)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

from mailroom_sandbox.paths import data_dir

_log = logging.getLogger("mailroom_sandbox.job.spec")

FAMILY_HF_REVISION = "46a4d3c240a36671cde0182fff4960f6b8b73aca"  # v9 mailroom-dataset tip (GT-closure revision, epic #27)
HF_DEFAULT_REPO = "Lucius-Morningstar/mailroom-dataset"

KNOWN_GPUS = (
    "L4",
    "A10",
    "A10G",
    "L40S",
    "T4",
    "A100",
    "A100-40GB",
    "A100-80GB",
    "H100",
    "H200",
    "B200",
    "B300",
)

VALID_QUANTIZATIONS = {
    "",
    "awq",
    "auto_awq",
    "gptq",
    "auto_gptq",
    "gptq_marlin",
    "awq_marlin",
    "fp8",
    "mxfp8",
    "fp8_per_tensor",
    "fp8_per_block",
    "fp8_per_channel",
    "int8_per_channel_weight_only",
    "online",
    "torchao",
    "compressed-tensors",
    "modelopt",
}

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class PromptRef(BaseModel):
    """One agent's prompt resolution: local file-, Langfuse pin, or code default."""

    source: Literal["local", "langfuse", "code-default"] = "code-default"
    file: str | None = None  # config/prompts/<file>.txt stem
    name: str | None = None  # Langfuse managed name (default: mailroom-<agent>)
    label: str | None = None  # xor with version; default label "production"
    version: int | None = None

    @model_validator(mode="after")
    def _one_pin(self) -> "PromptRef":
        if self.version is not None and self.label is not None:
            raise ValueError("prompt version and label are mutually exclusive")
        if self.source == "local":
            if not self.file:
                raise ValueError("local prompt requires file=stem")
            if self.version is not None or self.name:
                raise ValueError("local prompt takes no langfuse fields")
        if self.source == "langfuse":
            if not self.name and self.version is None and self.label is None:
                raise ValueError("langfuse prompt requires name= or a version/label")
        if self.source == "code-default":
            if self.file or self.name or self.version is not None:
                raise ValueError("code-default prompt takes no override fields")
        return self


class DatasetSpec(BaseModel):
    """HF dataset (full corpus or subset) or a local JSONL file."""

    provider: Literal["huggingface", "file"] = "huggingface"
    repo: str = HF_DEFAULT_REPO
    config: str = "ground_truth"  # None/'' = blind "default"
    split: str = "test"
    revision: str = ""  # pinned at lock time (default FAMILY_HF_REVISION)
    limit: int | None = None
    sample_seed: int | None = None
    # strata: {expected: [...], expected_subclass: [...]} filters OR
    #         {"buckets": [{doc_class, subclass, count}]} for stratified draws
    #         OR (DMR-066) {field: expected_subclass, values: [...],
    #         counts: [...]} — subclass-stratified draws over any row field;
    #         see corpus.strata_field / select_rows for semantics.
    strata: dict[str, Any] | None = None
    exclude_expected: list[str] | None = None
    columns: dict[str, str] | None = None
    expected_fields: list[str] | None = None
    local_path: str | None = None  # file:// or absolute path (offline)

    @field_validator("limit")
    @classmethod
    def _positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("limit must be >= 1")
        return v

    @field_validator("strata")
    @classmethod
    def _strata_shape(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Guard the strata block shape (DMR-066) so bad specs fail at parse."""
        if v is None:
            return v
        allowed = {"field", "values", "counts", "expected", "expected_subclass", "buckets"}
        unknown = set(v) - allowed
        if unknown:
            raise ValueError(f"strata: unknown keys {sorted(unknown)} (allowed: {sorted(allowed)})")
        if "buckets" in v:
            if not isinstance(v["buckets"], list) or not v["buckets"]:
                raise ValueError("strata.buckets must be a non-empty list")
            for b in v["buckets"]:
                if not isinstance(b, dict):
                    raise ValueError("strata.buckets entries must be objects")
                if "count" in b and (not isinstance(b["count"], int) or b["count"] < 1):
                    raise ValueError("strata.buckets[].count must be a positive int")
            return v
        if "values" in v:
            if not isinstance(v["values"], list) or not v["values"]:
                raise ValueError("strata.values must be a non-empty list")
            if any(not isinstance(x, str) or not x for x in v["values"]):
                raise ValueError("strata.values entries must be non-empty strings")
            if v.get("field") not in (None, "expected_doc_class", "expected_subclass"):
                raise ValueError("strata.field must be 'expected_doc_class' or 'expected_subclass'")
            counts = v.get("counts")
            if counts is not None:
                if not isinstance(counts, list) or len(counts) != len(v["values"]):
                    raise ValueError("strata.counts length must match strata.values")
                if any(not isinstance(c, int) or c < 1 for c in counts):
                    raise ValueError("strata.counts entries must be positive ints")
            return v
        # legacy {'expected': [...]} / {'expected_subclass': [...]} filters
        for key in ("expected", "expected_subclass"):
            if key in v:
                vals = v[key]
                if not isinstance(vals, list) or not vals:
                    raise ValueError(f"strata.{key} must be a non-empty list")
        return v

    def is_local(self) -> bool:
        if self.local_path:
            return True
        return self.provider == "file"

    def local_file(self) -> Path | None:
        if not self.local_path:
            return None
        url = self.local_path
        if url.startswith("file://"):
            url = url[len("file://") :]
        return Path(url)

    def request_core(self) -> dict[str, Any]:
        """The reproducibility-relevant spec (never row counts/hashes)."""
        if self.is_local() and self.local_file():
            local = self.local_file()
            core = {"provider": "file"}
            try:
                core["relative"] = str(local.resolve().relative_to(Path.cwd().resolve()))
            except ValueError:
                core["absolute"] = str(local.resolve())
            if local.is_file():
                import hashlib

                core["sha256"] = hashlib.sha256(local.read_bytes()).hexdigest()
            core.update(
                {
                    "limit": self.limit,
                    "sample_seed": self.sample_seed,
                    "strata": self.strata,
                    "exclude_expected": self.exclude_expected,
                }
            )
            return core
        return {
            "repo": self.repo,
            "config": self.config,
            "split": self.split,
            "revision": self.revision,
            "limit": self.limit,
            "sample_seed": self.sample_seed,
            "strata": self.strata,
            "exclude_expected": self.exclude_expected,
        }


class VLLMSpec(BaseModel):
    """vLLM serve flags (verified for v0.29.0 in DMR-022).

    ``max_model_len`` defaults to 16384 — the DMR-056 boot-valid cap for
    L4-bf16 8B-class rows: v0.29.0 RAISES at boot when the KV pool cannot
    hold one request at max_model_len (it does not shrink-and-warn). AWQ /
    FP8 rows may set 32768 explicitly.
    """

    max_model_len: int = 16384
    gpu_memory_utilization: float = 0.90
    max_num_seqs: int = 256
    quantization: str = ""
    revision: str = ""

    @field_validator("max_model_len")
    @classmethod
    def _ctx(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_model_len must be >= 1")
        return v

    @field_validator("gpu_memory_utilization")
    @classmethod
    def _gpu_util(cls, v: float) -> float:
        if not 0.0 < v <= 1.0:
            raise ValueError("gpu_memory_utilization must be in (0, 1]")
        return v

    @field_validator("max_num_seqs")
    @classmethod
    def _seqs(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_num_seqs must be >= 1")
        return v

    @field_validator("quantization")
    @classmethod
    def _quant(cls, v: str) -> str:
        if v not in VALID_QUANTIZATIONS:
            raise ValueError(
                f"quantization {v!r} is not a registered v0.29.0 method; "
                f"valid: {sorted(x for x in VALID_QUANTIZATIONS if x)}"
            )
        return v


class ModalSpec(BaseModel):
    app: str = "sandbox-vllm"
    gpu: str = "L4"
    image_tag: str = "v0.29.0"
    scaledown_seconds: int = 900
    max_containers: int = 1
    prewarm: bool = True
    # Hub weight-revision pin for the served model. Propagated by
    # deploy/run_modal_classifier_cost.py as MODAL_VLLM_REVISION so the
    # pre-warm and the serve boot pin the SAME commit (no tip drift between
    # pre-warm and eval). Empty = Hub tip (drifting).
    revision: str = ""

    @field_validator("gpu")
    @classmethod
    def _gpu(cls, v: str) -> str:
        base = v.split(":")[0]
        if base not in KNOWN_GPUS:
            raise ValueError(f"gpu {v!r} not in known classes {sorted(KNOWN_GPUS)}")
        return v

    @field_validator("image_tag")
    @classmethod
    def _tag(cls, v: str) -> str:
        if v == "latest":
            raise ValueError("image_tag must be pinned (never 'latest')")
        return v

    @field_validator("max_containers")
    @classmethod
    def _mc(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_containers must be >= 1 (cost guard)")
        return v


class EngineSpec(BaseModel):
    kind: Literal["vllm-local", "vllm-remote", "modal-vllm"] = "modal-vllm"
    model: str = "Qwen/Qwen3-8B"
    vllm: VLLMSpec = Field(default_factory=VLLMSpec)
    modal: ModalSpec | None = Field(default_factory=ModalSpec)


def known_tasks() -> tuple[str, ...]:
    """Every runnable job task: per-item + whole-run + registered agents (DMR-056).

    The agent half is data-driven from ``eval.agents.SPECS``: registering a
    new ``AgentSpec`` is the ONE-file extension point, and the new task
    automatically passes validation here, becomes a ``sandbox eval`` choice,
    and a ``sandbox run`` whole-run task. No cycle: ``eval.agents`` does not
    import ``job.spec``.
    """
    base = ("sorter", "legalbench", "pipeline", "extract", "chained", "local_vs_api", "isolated")
    try:
        from mailroom_sandbox.eval.agents import SPECS

        agents = tuple(n for n in SPECS if n not in ("sorter", "legalbench"))
    except Exception as exc:  # pragma: no cover — defensive for partial tooling imports
        _log.warning(
            "eval.agents.SPECS unavailable — agent-registered tasks are NOT in the "
            "known-task list; 'unknown task' errors below would misattribute this",
            exc_info=exc,
        )
        agents = ()
    return base + agents


def _check_task(value: str) -> str:
    tasks = known_tasks()
    if value not in tasks:
        raise ValueError(f"unknown task {value!r}; have {sorted(tasks)}")
    return value


class JobSpec(BaseModel):
    mode: Literal["endpoint", "modal"] = "endpoint"
    task: str = "sorter"
    mock: bool = True
    checkpoint_every: int = 1
    max_retries: int = 2
    fail_fast: bool = False
    # Modal-throughput alignment: how many rows the per-item loop runs at
    # once, so vLLM's continuous batching sees concurrent requests (offline
    # evals are a throughput workload). 1 preserves the serial, deterministic
    # default; 4-16 is the documented range for a vLLM endpoint. Guarded to
    # [1, 64] — unbounded fan-out is a cost accident.
    concurrency: int = 1

    @field_validator("task")
    @classmethod
    def _task_known(cls, v: str) -> str:
        return _check_task(v)

    @field_validator("checkpoint_every")
    @classmethod
    def _cp(cls, v: int) -> int:
        if v < 1:
            raise ValueError("checkpoint_every must be >= 1")
        return v

    @field_validator("concurrency")
    @classmethod
    def _conc(cls, v: int) -> int:
        if not 1 <= v <= 64:
            raise ValueError("concurrency must be in [1, 64]")
        return v


class TraceSpec(BaseModel):
    sink: Literal["langfuse", "phoenix", "otlp", "none"] = "langfuse"
    otlp: bool = True
    endpoint: str | None = None
    environment: str = "pilot"
    tags: list[str] = ["sandbox", "job"]


class RunSpec(BaseModel):
    schema_name: str = Field(default="sandbox.run/v1", alias="schema")
    run_id: str | None = None
    task: str = "sorter"
    profile: str = "modal-vllm"
    prompt: dict[str, Any] = Field(default_factory=dict)  # {default:..., agents:{name:...}}
    dataset: DatasetSpec = Field(default_factory=DatasetSpec)
    engine: EngineSpec = Field(default_factory=EngineSpec)
    job: JobSpec = Field(default_factory=JobSpec)
    trace: TraceSpec = Field(default_factory=TraceSpec)
    note: str | None = None

    model_config = {"populate_by_name": True}

    @field_validator("task")
    @classmethod
    def _task_known(cls, v: str) -> str:
        return _check_task(v)

    @model_validator(mode="after")
    def _prompt_map(self) -> "RunSpec":
        allowed = {"default", "agents"}
        if not set(self.prompt).issubset(allowed):
            raise ValueError(f"prompt section allows only {sorted(allowed)}")
        return self

    def spec_hash(self) -> str:
        return spec_hash(self)

    def effective_revision(self) -> str:
        return self.dataset.revision or FAMILY_HF_REVISION


def _strip_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def prompt_resolution_map(spec: RunSpec) -> dict[str, Any]:
    """Normalize the prompt section (default + per-agent overrides)."""
    agents = spec.prompt.get("agents", {}) if isinstance(spec.prompt.get("agents"), dict) else {}
    normalized: dict[str, Any] = {}
    default = spec.prompt.get("default", {}) if isinstance(spec.prompt.get("default"), dict) else {}
    if default:
        normalized["default"] = _strip_none(dict(PromptRef(**default)))
    for agent, ref in agents.items():
        normalized.setdefault("agents", {})[agent] = _strip_none(dict(PromptRef(**ref)))
    return normalized if normalized else {"default": {"source": "code-default"}}


def spec_core(spec: RunSpec) -> dict[str, Any]:
    """The behavioral core the spec_hash covers (excludes run_id/timestamps)."""
    return {
        "task": spec.task,
        "profile": spec.profile,
        "engine": {
            "kind": spec.engine.kind,
            "model": spec.engine.model,
            "vllm": spec.engine.vllm.model_dump(),
            "modal": spec.engine.modal.model_dump() if spec.engine.modal else None,
        },
        "job": spec.job.model_dump(),
        "trace": spec.trace.model_dump(),
        "prompt": prompt_resolution_map(spec),
        "dataset": spec.dataset.request_core(),
    }


def spec_hash(spec: RunSpec) -> str:
    core = spec_core(spec)
    blob = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-").lower()[:24] or "run"


def resolve_run_id(spec: RunSpec) -> str:
    if spec.run_id:
        if not _RUN_ID_RE.match(spec.run_id):
            raise ValueError(f"run_id {spec.run_id!r} must match {_RUN_ID_RE.pattern}")
        return spec.run_id
    return f"{_slug(spec.task)}-{_slug(spec.engine.model.split('/')[-1])}-{utc_stamp()}"


def runs_root() -> Path:
    path = data_dir() / "runtime" / "runs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_dir(run_id: str) -> Path:
    if not _RUN_ID_RE.match(run_id):
        raise ValueError(f"run_id {run_id!r} must match {_RUN_ID_RE.pattern}")
    return runs_root() / run_id


def load_run_spec(path: Path | str) -> RunSpec:
    """Load a YAML run spec file (no defaults merged from env)."""
    import yaml

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return RunSpec(**raw)


def engine_probe_base(profile: str) -> str | None:
    """Default base URL for a profile (mirrors providers.endpoints_for)."""
    from mailroom_sandbox.overlay import load_profile

    try:
        prof = load_profile(profile)
    except Exception as exc:
        _log.warning(
            "engine probe: profile %r could not be loaded — probing against "
            "the localhost default instead of raising",
            profile,
            exc_info=exc,
        )
        return None
    return prof.get("base_url") or None


def engine_base_url(spec: RunSpec, *, profile: str | None = None) -> str:
    """Resolve the engine base_url: VLLM_BASE_URL, profile default, or profile gateway.

    A profile name that cannot be loaded is a config error and RAISES
    (load_profile names the profile + available list) — a typo'd profile must
    never silently resolve to localhost.
    """
    env_base = os.environ.get("VLLM_BASE_URL", "").strip().rstrip("/")
    if env_base:
        return env_base
    prof = profile or spec.profile
    from mailroom_sandbox.overlay import load_profile

    profile_data = load_profile(prof)  # raises FileNotFoundError naming profile + available
    base = profile_data.get("base_url") or ""
    if base:
        return str(base).rstrip("/")
    if spec.engine.kind == "modal-vllm":
        workspace = os.environ.get("MODAL_WORKSPACE")
        if not workspace:
            raise ValueError(
                "MODAL_WORKSPACE is not set but the engine kind is 'modal-vllm' — "
                "cannot resolve the Modal gateway URL without it. Set "
                "MODAL_WORKSPACE=<your-workspace> or VLLM_BASE_URL, or fix the "
                "run spec's engine.kind."
            )
        return f"https://{workspace}--{spec.engine.modal.app}-serve.modal.run"
    return "http://localhost:8000"


def is_remote_url(url: str) -> bool:
    return urlparse(url).scheme in {"http", "https"}
