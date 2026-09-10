"""Remote job worker for the sandbox job CLI — `sandbox-job` Modal app (DMR-027).

Deployed once; ``sandbox run --job-mode modal`` pushes the locked run dir to
the ``sandbox-runs`` Volume and spawns ``run_job`` here. The worker:

- reads the immutable ``spec.lock.json`` + prepared ``dataset.jsonl`` from the
  Volume (never re-downloads, never floats the HF revision),
- configures OTEL export to the locked trace sink from the deploy Secret,
- runs the checkpoint-aware loop, mirroring progress to the
  ``sandbox-job-state`` Dict every item,
- commits the Volume so items/checkpoints survive; the CLI polls the Dict and
  can resume by re-spawning the same run_id.

``mailroom_sandbox`` source is baked in via ``add_local_python_source``; the
image installs the package's core deps + pinned dojo + HF/OTEL extras.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import modal

APP_NAME = "sandbox-job"
RUNS_VOLUME_NAME = "sandbox-runs"
HF_VOLUME_NAME = "sandbox-hf-cache"
STATE_DICT = "sandbox-job-state"
RUNS_MOUNT = "/runs"
HF_MOUNT = "/root/.cache/huggingface"

_DEPLOY_ENV_KEYS = (
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_BASE_URL",
    "LANGFUSE_HOST",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "HF_TOKEN",
    "VLLM_BASE_URL",
    "VLLM_API_KEY",
)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .add_local_python_source("mailroom_sandbox")
    .uv_pip_install(
        "httpx",
        "openai>=1.30",
        "pydantic>=2.0",
        "pyyaml>=6.0",
        "python-dotenv>=1.0",
        "structlog>=24.0",
        "huggingface_hub",
        "pyarrow",
        "langfuse>=4.0,<5",
        "opentelemetry-sdk",
        "opentelemetry-exporter-otlp-proto-http",
        "llm-dojo-scoring @ git+https://github.com/Exios66/llm-dojo-scoring.git@v0.12.2",
    )
)

runs_volume = modal.Volume.from_name(RUNS_VOLUME_NAME, create_if_missing=True)
hf_cache = modal.Volume.from_name(HF_VOLUME_NAME, create_if_missing=True)

app = modal.App(
    APP_NAME,
    image=image,
    tags={"project": "digital-mailroom", "package": "local-mailroom-sandbox", "purpose": "remote-job"},
)


def _config_secrets() -> list[modal.Secret]:
    values = {name: os.environ.get(name) for name in _DEPLOY_ENV_KEYS if os.environ.get(name)}
    if not values:
        return []
    return [modal.Secret.from_dict(values)]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@app.function(
    volumes={RUNS_MOUNT: runs_volume, HF_MOUNT: hf_cache},
    secrets=_config_secrets(),
    timeout=60 * 45,
    startup_timeout=60 * 5,
)
def run_job(payload: dict) -> dict:
    """Run a locked job from the Volume; mirror progress to the state Dict."""
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.otel import configure_tracing, flush_tracer, resolve_sink
    from mailroom_sandbox.job.runner import run_job as run_local_job

    run_id = str(payload["run_id"])
    store = RunStore(Path(RUNS_MOUNT) / run_id)
    lock = store.read_lock() or {}
    spec_hash = store.spec_hash() or ""
    state_dict = modal.Dict.from_name(STATE_DICT, create_if_missing=True)

    trace_block = lock.get("trace") or {}
    sink_cfg = resolve_sink(
        sink=trace_block.get("sink", "none"),
        otlp=bool(trace_block.get("otlp", True)),
        endpoint=trace_block.get("endpoint"),
        environment=trace_block.get("environment", "pilot"),
        service_name="sandbox-job",
        run_id=run_id,
        tags=trace_block.get("tags") or ["sandbox", "job"],
    )
    tracer = configure_tracing(sink_cfg) if sink_cfg.active else None

    def on_event(progress: dict) -> None:
        progress.update({"run_id": run_id, "spec_hash": spec_hash, "heartbeat_at": _now()})
        state_dict.put(progress)

    result = run_local_job(
        store,
        mock=bool(payload.get("mock", False)),
        tracer=tracer,
        on_event=on_event,
    )
    state_dict.put({"run_id": run_id, "spec_hash": spec_hash, "heartbeat_at": _now(), **result})
    runs_volume.commit()
    flush_tracer(tracer)
    return result


@app.local_entrypoint()
def main() -> None:
    print(f"Deploy:  modal deploy {Path(__file__).name}")
    print("Then:    sandbox run start --job-mode modal --spec <run>.yaml")