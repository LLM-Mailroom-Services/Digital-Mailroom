"""Run-spec models and canonical hashing for the sandbox job CLI (DMR-027)."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

from mailroom_sandbox.paths import data_dir
from mailroom_sandbox.services._exec import ServiceError

_log = logging.getLogger("mailroom_sandbox.job.spec")

# Canonical Hub tag ``v9.1`` (2026-09-27). This commit only records the tag;
# the parquet row set is ``FAMILY_HF_DATA_REVISION`` (mailroom-issues#196
# Phase B). SAND-032 run YAMLs keep the data SHA they were measured against.
FAMILY_HF_TAG = "v9.1"
FAMILY_HF_REVISION = "bc9eab280044befb51e19dda3071d290a8677f42"
FAMILY_HF_DATA_REVISION = "ed7576b676343e0b402ec5412cded301e629bdee"
HF_DEFAULT_REPO = "Lucius-Morningstar/mailroom-dataset"
# Full corpus row count at FAMILY_HF_REVISION (train+test; mailroom-ml pin).
FAMILY_CORPUS_SIZE = 3302
# Hub README composition at the same pin. Test-only is ~10% (323 rows) and
# cannot back 40/100-per-class Modal draws — merger_agreement has ~17 in
# test / 152 all-splits. `sandbox datasets pull` defaults to split=all.
FAMILY_CLASS_COUNTS: dict[str, int] = {
    "contract": 600,
    "corporate_record": 450,
    "correspondence": 1000,
    "insurance_claim": 1100,
    "merger_agreement": 152,
}
LIVE_DOC_CLASSES: tuple[str, ...] = tuple(FAMILY_CLASS_COUNTS)
assert sum(FAMILY_CLASS_COUNTS.values()) == FAMILY_CORPUS_SIZE

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


class InvalidRunIdError(ValueError):
    """A run id that is not a safe directory name (an input error, not a bug)."""


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
    # Drop documents whose class's task-native metric has no ground truth to score
    # against (a contract with empty cuad_clause_labels, a merger with empty
    # maud_clause_labels) BEFORE the draw. Such a document can never be scored, so
    # drawing it costs a GPU pass and deflates the paired n — the SAND-042 contracts
    # column was computed on 45 of 50 documents for exactly this reason. Off by
    # default: synthetic fixtures and other studies draw deliberately unlabeled rows.
    require_task_gt: bool = False
    # Merge the interim GT overlay (data/labels/interim, mailroom_sandbox.interim_labels) into the
    # drawn rows' expected_fields: the labels the next dataset revision is expected to publish.
    # Off by default; the lock records the overlay's sha256 so such scores never pass for Hub-GT ones.
    interim_labels: bool = False
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
                sub_buckets = b.get("sub_buckets")
                if sub_buckets is not None:
                    if not isinstance(sub_buckets, list) or not sub_buckets:
                        raise ValueError("strata.buckets[].sub_buckets must be a non-empty list")
                    for sb in sub_buckets:
                        if not isinstance(sb, dict):
                            raise ValueError("strata.buckets[].sub_buckets entries must be objects")
                        if not sb.get("subclass") or not isinstance(sb["subclass"], str):
                            raise ValueError("strata.buckets[].sub_buckets[].subclass must be a non-empty string")
                        if not isinstance(sb.get("count"), int) or sb["count"] < 1:
                            raise ValueError("strata.buckets[].sub_buckets[].count must be a positive int")
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
        """The reproducibility-relevant spec (never row counts/hashes).

        ``interim_labels`` is hashed only when set (with the overlay's fingerprint, so a rebuilt
        overlay is a new spec), so every pre-existing run YAML keeps its spec_hash.
        """
        core = self._request_core()
        if self.interim_labels:
            from mailroom_sandbox.interim_labels import overlay_fingerprint

            core["interim_labels"] = overlay_fingerprint()
        return core

    def _request_core(self) -> dict[str, Any]:
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

    L4 long-prompt defaults (specialist / ~9.7k-token prompts):
    ``max_num_seqs=6``, ``enable_prefix_caching=True``, ``enforce_eager=True``.
    Short-doc scale-matrix cells override ``max_num_seqs`` to 256 and should
    export matching ``MODAL_VLLM_MAX_NUM_SEQS`` at deploy time.
    """

    max_model_len: int = 16384
    gpu_memory_utilization: float = 0.90
    max_num_seqs: int = 6
    enable_prefix_caching: bool = True
    enforce_eager: bool = True
    quantization: str = ""
    revision: str = ""
    # SAND-032 knobs (all default OFF so existing run YAMLs are unchanged).
    kv_cache_dtype: str = ""  # "" = vLLM auto; "fp8" pinned for SAND-032 2×L4
    enable_thinking: bool | None = None  # None = send no chat-template kwargs
    cudagraph_capture_sizes: list[int] = Field(default_factory=list)
    max_num_batched_tokens: int | None = None
    max_inputs: int = 0  # >0 wraps serve() in @modal.concurrent(max_inputs=…)
    # SAND-040: HF config overrides passed to `vllm serve --hf-overrides` (JSON). The
    # 64K Qwen3 window is YaRN ×2 over the native 32768:
    # {"rope_parameters": {"rope_type": "yarn", "factor": 2.0,
    #  "original_max_position_embeddings": 32768, "rope_theta": 1000000}}
    # (v0.29.0 reads Transformers-v5 `rope_parameters`; vLLM derives max len 65536).
    hf_overrides: dict[str, Any] | None = None
    # SAND-077: per-modality item caps (`vllm serve --limit-mm-per-prompt`).
    # {"image": 0, ...} keeps a multimodal checkpoint (Qwen3.5) text-only.
    limit_mm_per_prompt: dict[str, int] | None = None

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
    """Modal fleet knobs.

    Scale a second L4 with ``max_containers=2`` (data-parallel replicas, one
    GPU each). Modal's web endpoint load-balances across replicas. Do not use
    ``gpu=L4:2`` + tensor parallel for 8B-class models that fit on one L4.
    """

    app: str = "sandbox-vllm"
    gpu: str = "L4"
    image_tag: str = "v0.29.0"
    # Efficient conservative / unattended default: 600s idle warm.
    # Specialist 5×30 attended suite pins 120 explicitly in run-30 YAMLs (DMR-076);
    # deploy/modal_vllm.py defaults to 120 for the same attended posture.
    scaledown_seconds: int = 600
    max_containers: int = 1
    min_containers: int = 0  # scale-to-zero; mirror MODAL_VLLM_MIN_CONTAINERS
    prewarm: bool = True
    # Deploy from the workspace's published sandbox-vllm:<image_tag> instead of building.
    named_image: bool = False

    @field_validator("gpu")
    @classmethod
    def _gpu(cls, v: str) -> str:
        base = v.split(":")[0]
        if base not in KNOWN_GPUS:
            raise ValueError(f"gpu {v!r} not in known classes {sorted(KNOWN_GPUS)}")
        parts = v.split(":")
        if len(parts) > 2 or (len(parts) == 2 and (not parts[1].isdigit() or int(parts[1]) < 1)):
            raise ValueError("GPU count must be a positive integer, e.g. H100:2")
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

    @field_validator("min_containers")
    @classmethod
    def _minc(cls, v: int) -> int:
        if v < 0:
            raise ValueError("min_containers must be >= 0")
        return v


DEFAULT_ENGINE_MODEL = "Qwen/Qwen3.5-9B"  # SAND-077 app default (Modal+vLLM)

# Serve flags a model needs when the spec leaves them unset. Mirrors the
# config/models.yaml row and deploy/modal_vllm.py MODEL_SERVE_DEFAULTS (parity
# tested): Qwen3.5 has no published FP8 checkpoint, so it serves online fp8,
# text-only.
MODEL_SERVE_DEFAULTS: dict[str, dict[str, Any]] = {
    "Qwen/Qwen3.5-9B": {
        "quantization": "fp8",
        "limit_mm_per_prompt": {"image": 0, "video": 0, "audio": 0},
    },
    "Qwen/Qwen3.5-35B-A3B": {  # SAND-079 mid specialist tier
        "quantization": "fp8",
        "limit_mm_per_prompt": {"image": 0, "video": 0, "audio": 0},
    },
    "Qwen/Qwen3.5-27B": {  # SAND-078 judge tier
        "quantization": "fp8",
        "limit_mm_per_prompt": {"image": 0, "video": 0, "audio": 0},
    },
}


class EngineSpec(BaseModel):
    kind: Literal["vllm-local", "vllm-remote", "modal-vllm", "openrouter"] = "modal-vllm"
    model: str = DEFAULT_ENGINE_MODEL
    vllm: VLLMSpec = Field(default_factory=VLLMSpec)
    modal: ModalSpec | None = Field(default_factory=ModalSpec)

    @model_validator(mode="after")
    def _serve_defaults(self) -> "EngineSpec":
        """Fill a model's required serve flags; an explicit value always wins."""
        for key, value in MODEL_SERVE_DEFAULTS.get(self.model, {}).items():
            unset = key not in self.vllm.model_fields_set if key == "quantization" else getattr(self.vllm, key) is None
            if unset:
                setattr(self.vllm, key, value.copy() if isinstance(value, dict) else value)
        return self


class AgentRoute(BaseModel):
    """One agent's explicit OpenAI-compatible transport and optional Modal deployment."""
    model_config = {"extra": "forbid"}
    provider: Literal["modal-vllm", "vllm", "openrouter", "api"]
    model: str = Field(min_length=1)
    base_url: str | None = None
    api_key_env: str | None = None
    modal: ModalSpec | None = None
    vllm: VLLMSpec = Field(default_factory=VLLMSpec)

    @model_validator(mode="after")
    def _transport(self) -> "AgentRoute":
        if self.provider == "modal-vllm" and self.modal is None:
            raise ValueError("modal-vllm agent route requires a scoped modal deployment")
        if self.provider == "modal-vllm" and self.base_url:
            raise ValueError("managed Modal route derives its endpoint; use provider=vllm for an existing URL")
        if self.provider != "modal-vllm" and self.modal is not None:
            raise ValueError("modal deployment settings require provider=modal-vllm")
        if self.provider in {"vllm", "api"} and not self.base_url:
            raise ValueError("vllm/api agent route requires base_url")
        if self.provider == "api" and not self.api_key_env:
            raise ValueError("api agent route requires api_key_env")
        if self.base_url:
            url = urlparse(self.base_url)
            if url.scheme not in {"http", "https"} or not url.netloc or url.username or url.password or url.query or url.fragment:
                raise ValueError("base_url must be an HTTP(S) endpoint without credentials, query, or fragment; use api_key_env")
        if self.api_key_env and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", self.api_key_env):
            raise ValueError("api_key_env must name an environment variable, not contain a credential")
        return self


def known_tasks() -> tuple[str, ...]:
    """Every runnable job task: per-item + whole-run + registered agents (DMR-056).

    The agent half is data-driven from ``eval.agents.SPECS``: registering a
    new ``AgentSpec`` is the ONE-file extension point, and the new task
    automatically passes validation here, becomes a ``sandbox eval`` choice,
    and a ``sandbox run`` whole-run task. No cycle: ``eval.agents`` does not
    import ``job.spec``.
    """
    base = (
        "sorter",
        "specialist",
        "pipeline",
        "extract",
        "chained",
        "local_vs_api",
        "sorter_vs_modernbert",
        "isolated",
    )
    try:
        from mailroom_sandbox.eval.agents import SPECS

        agents = tuple(n for n in SPECS if n != "sorter")
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
    # evals are a throughput workload). Default 4 is the efficient
    # conservative sweet spot (docs/jobs.md recommends 4-16 vs Modal vLLM;
    # DMR-072 found 8-way on 1×L4 piled at the web proxy). Specialist
    # run-30 YAMLs pin per-doc-type concurrency via specialist_posture
    # (DMR-078: short docs 5, long MAUD 3). Guarded to [1, 64].
    concurrency: int = 4
    # Cost / wall abort guards (DMR-078). None = disabled. Modal endpoint
    # runs estimate GPU $ from wall clock × L4 rate while the item loop
    # runs; exceeding either cap fails the run loud (no silent overspend).
    cost_cap_usd: float | None = None
    max_wall_seconds: int | None = None
    # SAND-089: token spend ceiling for agents on a token-billed API (OpenRouter).
    # cost_cap_usd estimates GPU time only; a paid run that bills API tokens needs
    # this too, and a known price for every API model (job/api_budget.py).
    api_cost_cap_usd: float | None = None

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

    @field_validator("cost_cap_usd")
    @classmethod
    def _cost_cap(cls, v: float | None) -> float | None:
        """Reject a NaN or non-positive cost cap when one is set.

        NaN fails every comparison, so it would pass ``<= 0`` and never trip.
        """
        if v is not None and (not math.isfinite(v) or v <= 0):
            raise ValueError("cost_cap_usd must be > 0 when set")
        return v

    @field_validator("api_cost_cap_usd")
    @classmethod
    def _api_cost_cap(cls, v: float | None) -> float | None:
        """Reject a NaN or non-positive API spend ceiling when one is set."""
        if v is not None and (not math.isfinite(v) or v <= 0):
            raise ValueError("api_cost_cap_usd must be > 0 when set")
        return v

    @field_validator("max_wall_seconds")
    @classmethod
    def _max_wall(cls, v: int | None) -> int | None:
        """Reject a wall-clock cap under 60 seconds when one is set."""
        if v is not None and v < 60:
            raise ValueError("max_wall_seconds must be >= 60 when set")
        return v


class ReviewerSpec(BaseModel):
    """Frozen decision-model reviewer: which backend, which pinned model, which classes at what cutoff."""
    model_config = {"extra": "forbid"}
    backend: Literal["jev", "local", "api", "decisions", "mock"]
    model: str = Field(min_length=1)
    # Per-class cutoffs. Empty only on a calibration run (task: sorter_reviewer), which
    # routes nothing; preflight requires at least one class on a pipeline run.
    classes: dict[str, float] = Field(default_factory=dict)
    # backend decisions: the question-set stem, config/decisions/<stem>.yaml (locked by content).
    questions: str | None = None
    # A chat model as the decision reviewer must be chosen on purpose (see _decision_model_guard).
    allow_chat_model: bool = False
    # Calibration only (task: sorter_reviewer): a finished sorter run whose answers are the
    # sorter handoff for each document. The pipeline passes the live handoff instead.
    # A finished sorter run, a saved pass (data/handoff/<name>/<split>.jsonl), or several of
    # these merged (later entries win on overlap).
    handoff_run: str | list[str] | None = None

    @field_validator("classes", mode="before")
    @classmethod
    def _cutoffs(cls, values: Any) -> Any:
        if values is None:
            return {}
        if not isinstance(values, dict):
            raise ValueError("reviewer classes must map class names to cutoffs")
        for name, cutoff in values.items():
            if isinstance(cutoff, bool) or not isinstance(cutoff, (int, float)) or not math.isfinite(cutoff) or not 0 <= cutoff <= 1:
                raise ValueError(f"{name}: cutoff must be a finite number in [0, 1]")
        return values

    @model_validator(mode="after")
    def _backend_pin(self) -> "ReviewerSpec":
        # The pin check lives with the backends; building one does no network call.
        from mailroom_sandbox.decision_backends import build_backend

        build_backend(self.backend, self.model, questions=self.questions)
        return self

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        # Fields added for the Decisions backend are omitted at their defaults, so the
        # spec hash of every reviewer block written before them is unchanged.
        out = super().model_dump(**kwargs)
        if out.get("questions") is None:
            out.pop("questions", None)
        if out.get("allow_chat_model") is False:
            out.pop("allow_chat_model", None)
        if out.get("handoff_run") is None:
            out.pop("handoff_run", None)
        return out

    @model_validator(mode="after")
    def _decision_model_guard(self) -> "ReviewerSpec":
        # 2026-11-01: a whole calibration ran on the chat model openai/gpt-6-luna through the api
        # backend when the intended reviewer was the Decisions model openai/gpt-6-luna-decisions.
        # A Decisions model only works on backend decisions, and a chat model on api needs an
        # explicit opt-in, so the two can no longer be swapped silently.
        from mailroom_sandbox.decision_backends import is_decisions_model

        if self.backend == "decisions" and not is_decisions_model(self.model):
            raise ValueError(f"reviewer backend decisions needs a Decisions-API model (e.g. 'openai/gpt-6-luna-decisions'); "
                             f"{self.model!r} is a chat model")
        if self.backend == "decisions" and not self.questions:
            raise ValueError("reviewer backend decisions needs questions: <stem> (config/decisions/<stem>.yaml)")
        if self.backend == "decisions":
            # A human verdict gates at confidence 0.0, parked only by a cutoff above 0.
            zero = sorted(name for name, cutoff in self.classes.items() if cutoff <= 0)
            if zero:
                raise ValueError(f"reviewer backend decisions needs cutoffs above 0 ({', '.join(zero)}): "
                                 "a human verdict gates at 0.0 and a cutoff of 0 would never park it")
        if self.backend != "decisions" and is_decisions_model(self.model):
            raise ValueError(f"{self.model!r} is a Decisions-API model; use reviewer backend decisions, not {self.backend!r}")
        if self.backend == "api" and not self.allow_chat_model:
            raise ValueError(f"reviewer backend api runs the chat model {self.model!r} as the decision reviewer; "
                             "the decision reviewer is a Decisions-API model (backend decisions). "
                             "Set allow_chat_model: true only to compare against a chat model on purpose")
        return self


class TraceSpec(BaseModel):
    sink: Literal["langfuse", "phoenix", "otlp", "none"] = "langfuse"
    otlp: bool = True
    endpoint: str | None = None
    environment: str = "pilot"
    tags: list[str] = ["sandbox", "job"]


class ExtractionGateSpec(BaseModel):
    """The Decisions-model extraction gate in a pipeline run (advisory; llm-mailroom >= the gate hook).

    The pipeline sends the sorter's subclass with every extraction; the gate's answers are
    recorded per document (``extraction_gate``) and never change routing.
    """
    model_config = {"extra": "forbid"}
    model: str = Field(min_length=1)
    # The question-set stem, config/decisions/<stem>.yaml, of kind extraction_gate (locked by content).
    questions: str = Field(min_length=1)

    @model_validator(mode="after")
    def _decisions_model(self) -> "ExtractionGateSpec":
        from mailroom_sandbox.decision_backends import is_decisions_model

        if not is_decisions_model(self.model):
            raise ValueError(f"extraction_gate model {self.model!r} is not a Decisions-API model")
        return self


class RunSpec(BaseModel):
    schema_name: str = Field(default="sandbox.run/v1", alias="schema")
    run_id: str | None = None
    runbook_id: str | None = None
    task: str = "sorter"
    # Level 2 of the primary tasks: one specialist (task: specialist) or one
    # document class through the full graph (task: pipeline). None = all.
    target: str | None = None
    profile: str = "modal-vllm"
    prompt: dict[str, Any] = Field(default_factory=dict)  # {default:..., agents:{name:...}}
    dataset: DatasetSpec = Field(default_factory=DatasetSpec)
    engine: EngineSpec = Field(default_factory=EngineSpec)
    job: JobSpec = Field(default_factory=JobSpec)
    trace: TraceSpec = Field(default_factory=TraceSpec)
    note: str | None = None
    agent_models: dict[str, str] = Field(default_factory=dict)
    agent_knobs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    agent_routes: dict[str, AgentRoute] = Field(default_factory=dict)
    reviewer: ReviewerSpec | None = None
    extraction_gate: ExtractionGateSpec | None = None

    model_config = {"populate_by_name": True}

    @field_validator("agent_knobs")
    @classmethod
    def _knobs(cls, values: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        allowed = {"max_tokens", "temperature", "max_input_chars", "reasoning_effort", "chunk_chars", "overlap_chars"}
        for name, knobs in values.items():
            if set(knobs) - allowed:
                raise ValueError(f"{name}: unsupported generation knobs {sorted(set(knobs) - allowed)}; configure transports with agent_routes")
            for key, value in knobs.items():
                if key == "reasoning_effort":
                    if value is not None and not isinstance(value, str):
                        raise ValueError("reasoning_effort must be a string")
                elif key == "temperature":
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 2:
                        raise ValueError("temperature must be finite in [0, 2]")
                elif isinstance(value, bool) or not isinstance(value, int) or value < (0 if key == "overlap_chars" else 1):
                    raise ValueError(f"{key} must be a positive integer (overlap may be zero)")
        return values

    @field_validator("task")
    @classmethod
    def _task_known(cls, v: str) -> str:
        return _check_task(v)

    @model_validator(mode="after")
    def _gate_in_pipeline(self) -> "RunSpec":
        if self.extraction_gate is not None and self.task != "pipeline":
            raise ValueError(f"extraction_gate reviews pipeline extractions; task {self.task!r} runs none "
                             "(calibrate the gate with task: extraction_gate and a reviewer block)")
        return self

    @model_validator(mode="after")
    def _reviewer_classes(self) -> "RunSpec":
        if self.reviewer is not None and not self.reviewer.classes and self.task not in ("sorter_reviewer", "extraction_gate"):
            raise ValueError("reviewer classes must map at least one class to a cutoff "
                             "(an empty map is only for a task: sorter_reviewer calibration run)")
        return self

    @model_validator(mode="after")
    def _target(self) -> "RunSpec":
        if self.target is None:
            return self
        from mailroom_sandbox.eval.primary import PRIMARY_TASKS, resolve_class

        if self.task not in PRIMARY_TASKS:
            raise ValueError(f"target only applies to task specialist or pipeline, not {self.task!r}")
        self.target = resolve_class(self.target)
        return self

    @model_validator(mode="after")
    def _prompt_map(self) -> "RunSpec":
        allowed = {"default", "agents", "versions"}
        if not set(self.prompt).issubset(allowed):
            raise ValueError(f"prompt section allows only {sorted(allowed)}")
        if "versions" in self.prompt:
            # eval-environment prompt versions (any archived / frozen / mutation key),
            # {role: key} or a list of "role=key" / bare keys. Format only here (no
            # dojo needed to load a spec); preflight resolves + verifies against the dojo.
            from mailroom_sandbox.prompt_versions import check_spec_prompt

            self.prompt = {**self.prompt, "versions": check_spec_prompt(self.prompt)}
        return self

    @model_validator(mode="after")
    def _modal_concurrency_posture(self) -> "RunSpec":
        """Warn when a Modal profile would starve continuous batching at concurrency=1."""
        if (
            self.profile == "modal-vllm"
            and self.engine.kind == "modal-vllm"
            and self.job.concurrency == 1
        ):
            _log.warning(
                "run spec profile=modal-vllm with job.concurrency=1 starves vLLM "
                "continuous batching on the warm L4 — set concurrency: 4 (efficient "
                "conservative default) unless this is an intentional serial probe"
            )
        if self.engine.modal is not None and self.engine.modal.min_containers > self.engine.modal.max_containers:
            raise ValueError(
                f"modal.min_containers ({self.engine.modal.min_containers}) cannot "
                f"exceed modal.max_containers ({self.engine.modal.max_containers})"
            )
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
    # Hashed only when set, so every pre-existing run YAML keeps its spec_hash.
    if spec.prompt.get("versions"):
        normalized["versions"] = dict(sorted(dict(spec.prompt["versions"]).items()))
    return normalized if normalized else {"default": {"source": "code-default"}}


# SAND-032 knobs hash only when set, so pre-SAND-032 run YAMLs keep their
# recorded spec_hash (locks, resume, and hashes cited in committed reports).
_HASH_WHEN_SET = ("kv_cache_dtype", "enable_thinking", "cudagraph_capture_sizes",
                  "max_num_batched_tokens", "max_inputs", "hf_overrides", "limit_mm_per_prompt")


def _vllm_core(vllm: VLLMSpec) -> dict[str, Any]:
    core = vllm.model_dump()
    defaults = VLLMSpec().model_dump()
    for key in _HASH_WHEN_SET:
        if core.get(key) == defaults[key]:
            core.pop(key, None)
    return core


def spec_core(spec: RunSpec) -> dict[str, Any]:
    """The behavioral core the spec_hash covers (excludes run_id/timestamps)."""
    return {
        **({"agent_models": dict(sorted(spec.agent_models.items()))} if spec.agent_models else {}),
        **({"agent_knobs": spec.agent_knobs} if spec.agent_knobs else {}),
        **({"agent_routes": {name: _route_core(route) for name, route in spec.agent_routes.items()}} if spec.agent_routes else {}),
        **({"reviewer": spec.reviewer.model_dump()} if spec.reviewer else {}),
        # Hashed only when set, so every pre-existing run YAML keeps its spec_hash.
        **({"extraction_gate": spec.extraction_gate.model_dump()} if spec.extraction_gate else {}),
        "task": spec.task,
        # Hashed only when set, so every pre-existing run YAML keeps its spec_hash.
        **({"target": spec.target} if spec.target else {}),
        "profile": spec.profile,
        "engine": {
            "kind": spec.engine.kind,
            "model": spec.engine.model,
            "vllm": _vllm_core(spec.engine.vllm),
            "modal": _modal_core(spec.engine.modal),
        },
        # api_cost_cap_usd is hashed only when set, so pre-SAND-089 YAMLs keep their hash.
        "job": {key: value for key, value in spec.job.model_dump().items()
                if not (key == "api_cost_cap_usd" and value is None)},
        "trace": spec.trace.model_dump(),
        "prompt": prompt_resolution_map(spec),
        "dataset": spec.dataset.request_core(),
    }


def _modal_core(modal: ModalSpec | None) -> dict[str, Any] | None:
    """named_image is hashed only when set, so existing run YAMLs keep their hash."""
    if modal is None:
        return None
    return {key: value for key, value in modal.model_dump().items() if key != "named_image" or value}


def _route_core(route: Any) -> dict[str, Any]:
    return {**route.model_dump(), "modal": _modal_core(route.modal)}


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
            raise InvalidRunIdError(f"run_id {spec.run_id!r} must match {_RUN_ID_RE.pattern}")
        return spec.run_id
    return f"{_slug(spec.task)}-{_slug(spec.engine.model.split('/')[-1])}-{utc_stamp()}"


def runs_root() -> Path:
    path = data_dir() / "runtime" / "runs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_dir(run_id: str) -> Path:
    if not _RUN_ID_RE.match(run_id):
        raise InvalidRunIdError(f"run_id {run_id!r} must match {_RUN_ID_RE.pattern}")
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


class EndpointUnresolved(ServiceError, ValueError):
    """A Modal run has neither ``VLLM_BASE_URL`` nor ``MODAL_WORKSPACE`` to build its endpoint from.

    A ``ValueError`` so existing callers keep working; a ``ServiceError`` so the CLI
    reports it as one actionable line.
    """


def engine_base_url(spec: RunSpec, *, profile: str | None = None) -> str:
    """Resolve the engine base_url: VLLM_BASE_URL, profile default, or profile gateway.

    A profile name that cannot be loaded is a config error and RAISES
    (load_profile names the profile + available list) — a typo'd profile must
    never silently resolve to localhost.
    """
    if spec.engine.kind == "openrouter":
        from mailroom_sandbox.overlay import load_profile
        from mailroom_sandbox.providers import endpoints_for
        return endpoints_for(load_profile(profile or spec.profile)).base_url.rstrip("/")
    env_base = os.environ.get("VLLM_BASE_URL", "").strip().rstrip("/")
    if env_base:
        return env_base
    prof = profile or spec.profile
    from mailroom_sandbox.overlay import load_profile

    profile_data = load_profile(prof)  # raises FileNotFoundError naming profile + available
    base = profile_data.get("base_url") or ""
    # The `modal-vllm` profile's static base_url is a localhost parity value only
    # (health and activation never use it); a Modal run resolves its gateway below
    # or fails loudly, never probing whatever listens on localhost:8000.
    modal_parity = spec.engine.kind == "modal-vllm" and profile_data.get("name") == "modal-vllm"
    if base and not modal_parity:
        return str(base).rstrip("/")
    if spec.engine.kind == "modal-vllm":
        workspace = os.environ.get("MODAL_WORKSPACE", "").strip()
        if not workspace:
            raise EndpointUnresolved(
                "MODAL_WORKSPACE is not set but the engine kind is 'modal-vllm' — "
                "cannot resolve the Modal gateway URL without it. Set "
                "MODAL_WORKSPACE=<your-workspace> or VLLM_BASE_URL, or fix the "
                "run spec's engine.kind."
            )
        app = spec.engine.modal.app if spec.engine.modal else (os.environ.get("MODAL_VLLM_APP_NAME", "").strip() or "sandbox-vllm")
        return f"https://{workspace}--{app}-serve.modal.run"
    return "http://localhost:8000"


def is_remote_url(url: str) -> bool:
    return urlparse(url).scheme in {"http", "https"}
