"""Run-spec models and canonical hashing for the sandbox job CLI (DMR-027)."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

from mailroom_sandbox.paths import data_dir

FAMILY_HF_REVISION = "eafe1ab4c0d330d8f9c7a5fb254155e75d290828"
HF_DEFAULT_REPO = "Lucius-Morningstar/mailroom-corpus"

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
    #         {"buckets": [{doc_class, subclass, count}]} for stratified draws.
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
    """vLLM serve flags (verified for v0.28.0 in DMR-022)."""

    max_model_len: int = 32768
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
                f"quantization {v!r} is not a registered v0.28.0 method; "
                f"valid: {sorted(x for x in VALID_QUANTIZATIONS if x)}"
            )
        return v


class ModalSpec(BaseModel):
    app: str = "sandbox-vllm"
    gpu: str = "L4"
    image_tag: str = "v0.28.0"
    scaledown_seconds: int = 900
    max_containers: int = 1
    prewarm: bool = True

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


class JobSpec(BaseModel):
    mode: Literal["endpoint", "modal"] = "endpoint"
    task: str = "sorter"
    mock: bool = True
    checkpoint_every: int = 1
    max_retries: int = 2
    fail_fast: bool = False

    @field_validator("checkpoint_every")
    @classmethod
    def _cp(cls, v: int) -> int:
        if v < 1:
            raise ValueError("checkpoint_every must be >= 1")
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
    except Exception:
        return None
    return prof.get("base_url") or None


def engine_base_url(spec: RunSpec, *, profile: str | None = None) -> str:
    """Resolve the engine base_url: VLLM_BASE_URL, profile default, or profile gateway."""
    env_base = os.environ.get("VLLM_BASE_URL", "").strip().rstrip("/")
    if env_base:
        return env_base
    prof = profile or spec.profile
    from mailroom_sandbox.overlay import load_profile

    try:
        base = load_profile(prof).get("base_url") or ""
    except Exception:
        base = ""
    if base:
        return str(base).rstrip("/")
    if spec.engine.kind == "modal-vllm":
        return f"https://{os.environ.get('MODAL_WORKSPACE', '<workspace>')}--{spec.engine.modal.app}-serve.modal.run"
    return "http://localhost:8000"


def is_remote_url(url: str) -> bool:
    return urlparse(url).scheme in {"http", "https"}
