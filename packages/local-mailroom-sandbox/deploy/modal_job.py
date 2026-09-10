"""Remote job worker for the sandbox job CLI — `sandbox-job` Modal app (DMR-027, DMR-047).

Deployed once; ``sandbox run --job-mode modal`` pushes the locked run dir to
the ``sandbox-runs`` Volume and spawns ``run_job`` here. The worker:

- reads the immutable ``spec.lock.json`` + prepared ``dataset.jsonl`` from the
  Volume (never re-downloads, never floats the HF revision) and VERIFIES the
  dataset sha256 against the lock before scoring a single row (DMR-049),
- configures OTEL export to the locked trace sink from the deploy Secret,
- runs the checkpoint-aware loop, mirroring progress to the
  ``sandbox-job-state`` Dict every item and committing the Volume every
  ``COMMIT_EVERY_EVENTS`` so a crash loses at most that window (DMR-047),
- copies the worker's experiment-log records into the run dir (the reports
  dir is ephemeral) so the CLI can pull them back,
- commits the Volume so items/checkpoints survive; the CLI polls the Dict and
  can resume by re-spawning the same run_id.

The image bundles the eval surface the runners need: ``mailroom_sandbox``
source, the sandbox ``config/`` (profiles + taxonomy overlay), the committed
``data/fixtures/`` (LegalBench/agent fixtures), and the mailroom dist
(``mailroom@v0.6.0``) whose ``agents.*``/``graph.*``/``pipeline.*`` modules
the eval agents import — without them per-item evals silently mocked and
whole-run tasks crashed (DMR-047). ``SANDBOX_ROOT=/root`` anchors
``repo_root()``/``config_dir()``/``fixtures_dir()`` at the bundled paths.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import modal

APP_NAME = "sandbox-job"
RUNS_VOLUME_NAME = "sandbox-runs"
HF_VOLUME_NAME = "sandbox-hf-cache"
STATE_DICT = "sandbox-job-state"
RUNS_MOUNT = "/runs"
HF_MOUNT = "/root/.cache/huggingface"
SANDBOX_ROOT = "/root"
COMMIT_EVERY_EVENTS = 25

# Package root of this checkout (packages/local-mailroom-sandbox) — the
# config/ + data/fixtures/ dirs are bundled from here at deploy time.
_PKG_ROOT = Path(__file__).resolve().parent.parent

_DEPLOY_ENV_KEYS = (
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_BASE_URL",
    "LANGFUSE_HOST",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "HF_TOKEN",
    "VLLM_BASE_URL",
    "VLLM_API_KEY",
    "DEFAULT_PROVIDER",
)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .add_local_python_source("mailroom_sandbox")
    .add_local_dir(_PKG_ROOT / "config", remote_path=f"{SANDBOX_ROOT}/config")
    .add_local_dir(
        _PKG_ROOT / "data" / "fixtures",
        remote_path=f"{SANDBOX_ROOT}/data/fixtures",
    )
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
        # The eval agents import agents.sorter / graph.build_graph /
        # pipeline.bins from the MAILROOM dist (v0.6.0) — the sandbox pins it.
        "mailroom @ git+https://github.com/Exios66/llm-mailroom.git@v0.6.0",
    )
    .env(
        {
            "SANDBOX_ROOT": SANDBOX_ROOT,
            # This worker serves vLLM only; keep the direct live-call target
            # (LegalBench) on the vLLM family even when the deploy env is bare.
            "DEFAULT_PROVIDER": "vllm",
        }
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

    # DMR-049: never score a dataset other than the locked one. The lock's
    # sha256 is the hash of the payload written at preflight; the file must
    # still match it on the Volume (a partial put or a drifted re-upload).
    dataset_block = lock.get("dataset") if isinstance(lock.get("dataset"), dict) else {}
    expected_sha = str((dataset_block or {}).get("sha256") or "")
    actual_sha = store.dataset_sha256() or ""
    if expected_sha and actual_sha and expected_sha != actual_sha:
        raise RuntimeError(
            f"dataset.jsonl sha256 mismatch for run {run_id}: "
            f"lock={expected_sha[:12]} file={actual_sha[:12]} — re-fire the run (--force)"
        )

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

    events = {"n": 0}

    def on_event(progress: dict) -> None:
        progress.update({"run_id": run_id, "spec_hash": spec_hash, "heartbeat_at": _now()})
        state_dict.put(progress)
        events["n"] += 1
        if events["n"] % COMMIT_EVERY_EVENTS == 0:
            try:
                runs_volume.commit()
            except Exception:
                pass

    payload_mock = payload.get("mock")
    result = run_local_job(
        store,
        mock=None if payload_mock is None else bool(payload_mock),
        tracer=tracer,
        on_event=on_event,
    )

    # The reports dir is container-local; copy the run's experiment records
    # into the volume-committed run dir so the CLI can pull them back (DMR-047).
    reports_log = Path(SANDBOX_ROOT) / "reports" / "experiment_log.jsonl"
    if reports_log.is_file():
        try:
            shutil.copyfile(reports_log, store.dir / "experiment_log.jsonl")
        except OSError:
            pass

    state_dict.put({"run_id": run_id, "spec_hash": spec_hash, "heartbeat_at": _now(), **result})
    runs_volume.commit()
    flush_tracer(tracer)
    return result


@app.local_entrypoint()
def main() -> None:
    print(f"Deploy:  modal deploy {Path(__file__).name}")
    print("Then:    sandbox run start --job-mode modal --spec <run>.yaml")
