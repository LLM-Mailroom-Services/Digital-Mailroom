"""SAND-032: render the deploy env a run YAML implies, and diff it vs a shell.

``deploy/modal_vllm.py`` reads ``MODAL_VLLM_*`` at import time, but the run
YAML is the source of truth. ``spec_env`` is the single mapping,
``env_drift`` is the loud check benchmark-check runs, and ``render_exports``
is what the operator sources before ``modal deploy``. No credentials are
ever rendered (the API token and HF token stay out of this module).
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Mapping

from mailroom_sandbox.job.runbooks import _shell_quote
from mailroom_sandbox.job.specialist_posture import sand42_cell_label
from mailroom_sandbox.job.spec import MODEL_SERVE_DEFAULTS, RunSpec

# deploy/modal_vllm.py maps this to no --quantization flag.
BF16_QUANTIZATION = "bf16"


_DEPLOY_DEFAULT_KEYS = (
    "MODAL_VLLM_TP_SIZE",
    "MODAL_VLLM_ATTENTION_BACKEND",
    "MODAL_VLLM_ASYNC_SCHEDULING",
    "MODAL_VLLM_REASONING_PARSER",
    "MODAL_VLLM_REASONING_PARSER_PLUGIN",
    "MODAL_VLLM_TOOL_CALL_PARSER",
    "MODAL_VLLM_ENABLE_AUTO_TOOL_CHOICE",
    "MODAL_VLLM_STARTUP_TIMEOUT_SECONDS",
    "MODAL_VLLM_CHAT_TEMPLATE",
    "MODAL_VLLM_USE_NAMED_IMAGE",
    # SAND-042 in-container GPU telemetry: deploy defaults are on / 5s / 6 / the
    # shared volume, so a stale shell cannot silently redirect or silence it.
    "MODAL_VLLM_TELEMETRY",
    "MODAL_VLLM_TELEMETRY_INTERVAL",
    "MODAL_VLLM_TELEMETRY_COMMIT_EVERY",
    "MODAL_VLLM_TELEMETRY_VOLUME",
)


def _b(value: bool) -> str:
    return "1" if value else "0"


def _quantization(spec: RunSpec) -> str:
    """An explicit bf16 ("") on a model with a quantized serve default must not read as unset."""
    quant = spec.engine.vllm.quantization
    if not quant and MODEL_SERVE_DEFAULTS.get(spec.engine.model, {}).get("quantization"):
        return BF16_QUANTIZATION
    return quant


def spec_env(spec: RunSpec) -> dict[str, str]:
    """Every deploy knob the spec pins, as the exact env string modal_vllm reads."""
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
        "MODAL_VLLM_QUANTIZATION": _quantization(spec),
        "MODAL_VLLM_REVISION": v.revision,
        "MODAL_VLLM_KV_CACHE_DTYPE": v.kv_cache_dtype,
        "MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS": kwargs,
        "MODAL_VLLM_CUDAGRAPH_CAPTURE_SIZES": ",".join(str(x) for x in v.cudagraph_capture_sizes),
        "MODAL_VLLM_MAX_NUM_BATCHED_TOKENS": (
            "" if v.max_num_batched_tokens is None else str(v.max_num_batched_tokens)
        ),
        "MODAL_VLLM_MAX_INPUTS": str(v.max_inputs) if v.max_inputs else "",
        "MODAL_VLLM_HF_OVERRIDES": json.dumps(v.hf_overrides, sort_keys=True) if v.hf_overrides else "",
        "MODAL_VLLM_LIMIT_MM_PER_PROMPT": (
            "" if v.limit_mm_per_prompt is None else json.dumps(v.limit_mm_per_prompt, separators=(",", ":"))
        ),
        # SAND-042: the serving container writes its nvidia-smi series under this
        # label. Derived from the run id (one label per cell, shared by its five
        # configs) so the scraper finds the series from any of them; "" elsewhere.
        "MODAL_VLLM_TELEMETRY_LABEL": sand42_cell_label(spec.run_id),
        # Knobs the deploy reads that no SAND-032 run sets: pinned to "unset"
        # (deploy default) so a stale shell — e.g. the Granite runbook's
        # MODAL_VLLM_REASONING_PARSER=granite — is caught as drift and cleared
        # by sourcing render_exports. Parity with deploy/modal_vllm.py is
        # enforced by test_spec_env_covers_every_key_the_deploy_reads.
        **{key: "" for key in _DEPLOY_DEFAULT_KEYS},
    }
    if m is not None:
        env.update(
            {
                "MODAL_VLLM_APP_NAME": "" if m.app == "sandbox-vllm" else m.app,
                "MODAL_VLLM_GPU": m.gpu,
                "MODAL_VLLM_IMAGE_TAG": m.image_tag,
                "MODAL_VLLM_MAX_CONTAINERS": str(m.max_containers),
                "MODAL_VLLM_MIN_CONTAINERS": str(m.min_containers),
                "MODAL_VLLM_SCALEDOWN_SECONDS": str(m.scaledown_seconds),
                "MODAL_VLLM_USE_NAMED_IMAGE": "1" if m.named_image else "",
            }
        )
    return env


def env_drift(spec: RunSpec, environ: Mapping[str, str]) -> list[str]:
    """One message per key whose shell value differs from the spec (unset == "")."""
    out: list[str] = []
    for key, want in spec_env(spec).items():
        have = (environ.get(key) or "").strip()
        if have != want:
            out.append(f"{key}: shell has {have!r}, run YAML wants {want!r}")
    return out


def render_exports(spec: RunSpec) -> str:
    lines = [f"# deploy env for {spec.run_id} (generated by `sandbox run deploy-env`)"]
    for key, val in spec_env(spec).items():
        # "" means deploy default: unset it (an exported "" breaks int() knobs).
        lines.append(f"unset {key}" if val == "" else f"export {key}={_shell_quote(val)}")
    return "\n".join(lines) + "\n"


def durable_mailroom_env(run_dir: Path) -> dict[str, str]:
    """Keep a remote run's bins, catalog and review checkpoints on the run's Volume.

    The mailroom defaults to ``./data``, which dies with a Modal container, and
    a parked document is only reviewable while those files exist.
    """
    return {"MAILROOM_BASE_DIR": str(run_dir / "mailroom")}


# Background writers the vendored pipeline leaves on mailroom.db after a document
# archives: the post-archive relations pass and aiosqlite's per-connection thread.
_MAILROOM_WRITER_THREADS = ("relations-scan", "_connection_worker_thread")


def settle_mailroom_writers(timeout: float = 60.0) -> list[str]:
    """Wait for the pipeline's background ``mailroom.db`` writers to finish.

    ``dispatch_relations_scan`` runs on a daemon thread that outlives the
    document. A Volume commit (or a pull) taken while it holds the database
    captures a WAL mid-write, and a container exit kills the scan. Call this
    before committing a run directory. Returns the names of writers still
    running when ``timeout`` expires (empty when everything settled).
    """
    deadline = time.monotonic() + timeout
    current = threading.current_thread()
    for thread in threading.enumerate():
        if thread is current or not any(tag in thread.name for tag in _MAILROOM_WRITER_THREADS):
            continue
        thread.join(max(0.0, deadline - time.monotonic()))
    return [t.name for t in threading.enumerate()
            if t is not current and t.is_alive() and any(tag in t.name for tag in _MAILROOM_WRITER_THREADS)]
