"""Modal-deployed vLLM for the local-mailroom-sandbox (KANBAN-064 sibling).

Same env-knob contract as llm-mailroom ``deploy/modal_vllm.py``, plus
sandbox-local cost/scale knobs. App name and cache Volumes are
sandbox-scoped.

Default experiment posture (specialist 5×30 cost eval)
------------------------------------------------------
``MODAL_VLLM_MODEL=Qwen/Qwen3-8B`` on ``MODAL_VLLM_GPU=L4``,
``max_containers=1``, ``scaledown=120`` (attended; restore **600** for
unattended/overnight), job concurrency 4 — see ``docs/benchmark-l4.md``.
Leave knobs unset to get this posture. One warm app for all five runs;
teardown only after the fifth.

Advanced: swap model / GPU (one control surface)
------------------------------------------------
All deploy knobs are env-driven below. Prefer the catalog row in
``config/models.yaml`` ``modal_models:`` via::

    eval "$(sandbox modal-matrix env Qwen/Qwen3-8B-AWQ)"          # L4 AWQ
    eval "$(sandbox modal-matrix env Qwen/Qwen3-14B --gpu A100-40GB)"
    eval "$(sandbox modal-matrix env Qwen/Qwen3-8B-FP8)"          # H100 FP8
    # or bare env:
    #   export MODAL_VLLM_MODEL=… MODAL_VLLM_GPU=L4|A10G|A100-80GB:2|H100
    #   export MODAL_VLLM_QUANTIZATION=awq   # or empty for bf16/FP8 auto
    #   export MODAL_VLLM_MAX_MODEL_LEN=16384|32768
    #   export MODAL_VLLM_TP_SIZE=2          # must match GPU :N suffix
    modal run deploy/modal_vllm.py::download_model
    modal deploy deploy/modal_vllm.py --strategy recreate

Do **not** edit ``config/runs/run-30-*-specialist.yaml`` for swaps — those
YAMLs pin the default Qwen+L4 suite. Copy a YAML if an alternate scorecard
needs matching ``engine.model`` / ``engine.modal.gpu``.

Architecture (2026-09-16 — direct subprocess)
---------------------------------------------
vLLM runs as a subprocess on port 8000 in the image's native Python
(the Docker image has vLLM under its own Python where ``vllm serve`` works).
``.entrypoint([])`` allows Modal to run our ``serve()`` function, which
launches vLLM via ``subprocess.Popen`` and returns. Modal's ``@web_server``
proxies directly to the subprocess on port 8000 — **no reverse-proxy**,
no ASGI wrapper.

Pinned / verified 2026-09-16:

* Modal Python SDK **1.5.5** (2026-08-28).
* vLLM **v0.29.0** — ``vllm/vllm-openai:v0.29.0`` (newest stable).
* ``.entrypoint([])`` clears the image's vLLM entrypoint so Modal can run
  our ``serve()`` function without flag leakage.
* ``NETWORKX_AUTOMATIC_BACKEND_SELECTION=0`` prevents import hang.

Workflow::

    modal run deploy/modal_vllm.py::download_model   # pre-warm HF cache
    modal deploy deploy/modal_vllm.py                # prints the modal.run URL
"""

from __future__ import annotations

import atexit
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import modal

APP_NAME = "sandbox-vllm"
SERVER_PORT = 8000                  # Modal web_server port (vLLM subprocess)
HF_CACHE_VOLUME_NAME = "sandbox-hf-cache"
VLLM_CACHE_VOLUME_NAME = "sandbox-vllm-cache"
HF_CACHE_MOUNT = "/root/.cache/huggingface"
VLLM_CACHE_MOUNT = "/root/.cache/vllm"

# ── Deploy-time knobs ────────────────────────────────────────────────────────
MODEL = os.environ.get("MODAL_VLLM_MODEL", "Qwen/Qwen3-8B")
GPU = os.environ.get("MODAL_VLLM_GPU", "L4")
QUANTIZATION = os.environ.get("MODAL_VLLM_QUANTIZATION", "")
MAX_MODEL_LEN = os.environ.get("MODAL_VLLM_MAX_MODEL_LEN", "16384")
REVISION = os.environ.get("MODAL_VLLM_REVISION", "")
GPU_MEMORY_UTILIZATION = os.environ.get("MODAL_VLLM_GPU_MEMORY_UTILIZATION", "0.90")
MAX_NUM_SEQS = os.environ.get("MODAL_VLLM_MAX_NUM_SEQS", "256")
ATTENTION_BACKEND = os.environ.get("MODAL_VLLM_ATTENTION_BACKEND", "")
ASYNC_SCHEDULING = os.environ.get("MODAL_VLLM_ASYNC_SCHEDULING", "")
TP_SIZE = os.environ.get("MODAL_VLLM_TP_SIZE", "") or str(
    int(os.environ.get("MODAL_VLLM_GPU", "L4").split(":")[1])
    if ":" in os.environ.get("MODAL_VLLM_GPU", "L4")
    else 1
)
VLLM_IMAGE_TAG = os.environ.get("MODAL_VLLM_IMAGE_TAG", "v0.29.0")

# Attended specialist suite default: 120s idle warm (DMR-076 cost-saver).
# Unattended / overnight: export MODAL_VLLM_SCALEDOWN_SECONDS=600 before deploy.
SCALEDOWN_SECONDS = int(os.environ.get("MODAL_VLLM_SCALEDOWN_SECONDS", 120))
MAX_CONTAINERS = int(os.environ.get("MODAL_VLLM_MAX_CONTAINERS", 1))
MIN_CONTAINERS = int(os.environ.get("MODAL_VLLM_MIN_CONTAINERS", 0))
STARTUP_TIMEOUT_SECONDS = int(
    os.environ.get("MODAL_VLLM_STARTUP_TIMEOUT_SECONDS", 20 * 60)
)

CONFIG_ENV_KEYS = (
    "MODAL_VLLM_MODEL",
    "MODAL_VLLM_QUANTIZATION",
    "MODAL_VLLM_MAX_MODEL_LEN",
    "MODAL_VLLM_GPU_MEMORY_UTILIZATION",
    "MODAL_VLLM_MAX_NUM_SEQS",
    "MODAL_VLLM_TP_SIZE",
    "MODAL_VLLM_ATTENTION_BACKEND",
    "MODAL_VLLM_ASYNC_SCHEDULING",
    "MODAL_VLLM_REVISION",
    "MODAL_VLLM_API_TOKEN",
    # HF_TOKEN deliberately absent: it lives in the named Modal secret
    # `huggingface-secret` (below). Modal applies function secrets in list
    # order — LAST WINS on duplicate keys — so a locally-exported HF_TOKEN
    # in the from_dict secret would silently override the named secret.
)

# Named secret configured in Modal (created 2026-09-16 in the Modal dashboard);
# carries HF_TOKEN for gated/private weight downloads. Referenced by name so
# deploys do not depend on local env for the Hub credential. required_keys
# makes a missing HF_TOKEN fail the deploy at hydration (fail-loud), not at
# first gated-repo download.
HF_SECRET_NAME = os.environ.get("MODAL_HF_SECRET_NAME", "huggingface-secret")


def _config_secrets() -> list[modal.Secret]:
    secrets: list[modal.Secret] = [
        modal.Secret.from_name(HF_SECRET_NAME, required_keys=["HF_TOKEN"])
    ]
    values = {
        name: os.environ.get(name) for name in CONFIG_ENV_KEYS if os.environ.get(name)
    }
    if values:
        secrets.append(modal.Secret.from_dict(values))
    return secrets


hf_cache = modal.Volume.from_name(HF_CACHE_VOLUME_NAME, create_if_missing=True)
vllm_cache = modal.Volume.from_name(VLLM_CACHE_VOLUME_NAME, create_if_missing=True)

image = (
    modal.Image.from_registry(f"vllm/vllm-openai:{VLLM_IMAGE_TAG}", add_python="3.12")
    .entrypoint([])
    .run_commands("pip install --no-cache-dir huggingface_hub httpx")
    .env(
        {
            "HF_XET_HIGH_PERFORMANCE": "1",
            "NETWORKX_AUTOMATIC_BACKEND_SELECTION": "0",
        }
    )
)

download_image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("huggingface_hub")
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)

app = modal.App(
    APP_NAME,
    image=image,
    tags={
        "project": "digital-mailroom",
        "package": "local-mailroom-sandbox",
        "purpose": "remote-gpu-testing",
    },
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _server_env() -> dict[str, str]:
    """Environment for the vLLM subprocess."""
    env: dict[str, str] = {}
    api_token = os.environ.get("MODAL_VLLM_API_TOKEN", "").strip()
    if api_token:
        env["VLLM_API_KEY"] = api_token
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if hf_token:
        env["HF_TOKEN"] = hf_token
    return env


def build_vllm_command(model: str) -> list[str]:
    """Assemble the `vllm serve` argv for the subprocess."""
    cmd = [
        "vllm", "serve", model,
        "--host", "0.0.0.0",
        "--port", str(SERVER_PORT),
        "--max-model-len", MAX_MODEL_LEN,
        "--gpu-memory-utilization", GPU_MEMORY_UTILIZATION,
        "--max-num-seqs", MAX_NUM_SEQS,
    ]
    if TP_SIZE and TP_SIZE != "1":
        cmd += ["--tensor-parallel-size", TP_SIZE]
    if REVISION:
        cmd += ["--revision", REVISION]
    if QUANTIZATION:
        cmd += ["--quantization", QUANTIZATION]
    if ATTENTION_BACKEND:
        cmd += ["--attention-backend", ATTENTION_BACKEND]
    if _truthy(ASYNC_SCHEDULING):
        cmd += ["--async-scheduling"]
    cmd += ["--no-enable-log-requests"]
    return cmd


def _masked_config() -> dict[str, str]:
    def presence(name: str) -> str:
        return "set" if os.environ.get(name, "").strip() else "unset"

    return {
        "model": os.environ.get("MODAL_VLLM_MODEL", MODEL),
        "gpu": GPU,
        "image": VLLM_IMAGE_TAG,
        "max_model_len": MAX_MODEL_LEN,
        "gpu_memory_utilization": GPU_MEMORY_UTILIZATION,
        "max_num_seqs": MAX_NUM_SEQS,
        "tensor_parallel_size": TP_SIZE,
        "quantization": QUANTIZATION or "unset(bf16)",
        "revision": REVISION or "unset(tip)",
        "attention_backend": ATTENTION_BACKEND or "unset(engine-default)",
        "async_scheduling": "on" if _truthy(ASYNC_SCHEDULING) else "off",
        "VLLM_API_KEY": presence("MODAL_VLLM_API_TOKEN"),
        "HF_TOKEN": presence("HF_TOKEN"),
        "scaledown_seconds": str(SCALEDOWN_SECONDS),
        "startup_timeout_seconds": str(STARTUP_TIMEOUT_SECONDS),
    }


def _wait_for_port(port: int, timeout: int = 600) -> bool:
    """Block until localhost:*port* accepts connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2.0):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(1.0)
    return False


# ---------------------------------------------------------------------------
# Modal functions
# ---------------------------------------------------------------------------

@app.function(
    gpu=GPU,
    volumes={HF_CACHE_MOUNT: hf_cache, VLLM_CACHE_MOUNT: vllm_cache},
    secrets=_config_secrets(),
    timeout=STARTUP_TIMEOUT_SECONDS,
    scaledown_window=SCALEDOWN_SECONDS,
    min_containers=MIN_CONTAINERS,
    max_containers=MAX_CONTAINERS,
)
@modal.web_server(port=SERVER_PORT, startup_timeout=STARTUP_TIMEOUT_SECONDS)
def serve() -> None:
    """Launch vLLM subprocess on port 8000 in the image's native Python.

    Modal's ``@web_server`` proxies directly to the subprocess — no
    reverse-proxy, no ASGI wrapper, no in-process imports needed.
    """
    model = os.environ.get("MODAL_VLLM_MODEL", MODEL)

    config = _masked_config()
    print("=== sandbox-vllm serve config (masked) ===")
    for key, value in config.items():
        print(f"  {key}: {value}")
    sys.stdout.flush()

    # Verify secrets are available in the container
    hf_token = os.environ.get("HF_TOKEN", "")
    api_token = os.environ.get("MODAL_VLLM_API_TOKEN", "")
    print(f"secrets check: HF_TOKEN={'set' if hf_token else 'UNSET'} "
          f"MODAL_VLLM_API_TOKEN={'set' if api_token else 'unset'}")
    sys.stdout.flush()

    vllm_cmd = build_vllm_command(model)
    child_env = {**os.environ, **_server_env()}
    print(f"launching vLLM subprocess: {' '.join(vllm_cmd)}")
    sys.stdout.flush()

    vllm_proc = subprocess.Popen(
        vllm_cmd,
        env=child_env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    def _cleanup() -> None:
        if vllm_proc.poll() is None:
            vllm_proc.terminate()
            try:
                vllm_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                vllm_proc.kill()

    atexit.register(_cleanup)

    if not _wait_for_port(SERVER_PORT, timeout=STARTUP_TIMEOUT_SECONDS):
        print(f"ERROR: vLLM did not start on port {SERVER_PORT} within "
              f"{STARTUP_TIMEOUT_SECONDS}s")
        vllm_proc.terminate()
        raise RuntimeError("vLLM startup timeout")

    print(f"vLLM ready on port {SERVER_PORT} (pid={vllm_proc.pid})")
    sys.stdout.flush()

    # Return — Modal keeps container alive and routes to port (standard pattern)


# ---------------------------------------------------------------------------
# pre-warm
# ---------------------------------------------------------------------------

@app.function(
    image=download_image,
    volumes={HF_CACHE_MOUNT: hf_cache},
    secrets=_config_secrets(),
    timeout=60 * 45,
)
def download_model(model: str = "", revision: str = "") -> None:
    """Pre-warm the HF cache Volume (``modal run ...::download_model``)."""
    from huggingface_hub import snapshot_download

    model = model or os.environ.get("MODAL_VLLM_MODEL", MODEL)
    revision = revision or os.environ.get("MODAL_VLLM_REVISION", REVISION) or None
    print(f"pre-warming {model}" + (f"@{revision}" if revision else ""))
    snapshot_dir = snapshot_download(repo_id=model, revision=revision)
    n_files = sum(1 for _ in Path(snapshot_dir).rglob("*")) if snapshot_dir else 0
    if not n_files:
        raise SystemExit(
            f"snapshot_download returned empty snapshot for {model}"
        )
    hf_cache.commit()
    print(f"cached {model} ({n_files} file(s))")


# ---------------------------------------------------------------------------
# smoke-check / local-entrypoint
# ---------------------------------------------------------------------------

def _smoke_check(base: str) -> None:
    """Bearer-aware `/models` probe for `modal run ... --check`."""
    import httpx

    if not base:
        raise SystemExit(
            "VLLM_BASE_URL is not set — export the URL printed by `modal deploy`"
        )
    token = os.environ.get("VLLM_API_KEY", "").strip()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        resp = httpx.get(f"{base}/models", headers=headers, timeout=30.0)
    except httpx.HTTPError as exc:
        raise SystemExit(f"probe failed: {type(exc).__name__}: {exc}") from exc
    if resp.status_code == 401:
        raise SystemExit(
            f"401 from {base}/models — set VLLM_API_KEY"
        )
    if resp.status_code >= 400:
        raise SystemExit(f"HTTP {resp.status_code}: {resp.text[:400]!r}")
    try:
        payload = resp.json()
    except ValueError as exc:
        raise SystemExit(f"non-JSON response: {resp.text[:400]!r}") from exc
    ids = [
        item.get("id")
        for item in payload.get("data", [])
        if isinstance(item, dict) and item.get("id")
    ]
    print(f"ok: {base}/models -> {ids}")


@app.local_entrypoint()
def main(check: bool = False, debug: bool = False) -> None:
    name = Path(__file__).name
    base = os.environ.get("VLLM_BASE_URL", "").rstrip("/")
    print(f"Deploy:   modal deploy {name}")
    print(f"Pre-warm: modal run {name}::download_model")
    print(f"Model:    {MODEL} on {GPU} (vllm/vllm-openai:{VLLM_IMAGE_TAG})")
    print(
        f"Knobs:    max_model_len={MAX_MODEL_LEN} quant={QUANTIZATION or '(none)'} "
        f"tp={TP_SIZE} max_containers={MAX_CONTAINERS} scaledown={SCALEDOWN_SECONDS}s"
    )
    print(f"Endpoint: {base or 'set VLLM_BASE_URL after deploy'}")
    print(
        "Swap:     eval \"$(sandbox modal-matrix env <HF-id> [--gpu GPU])\" "
        "then redeploy --strategy recreate (default catalog row: Qwen/Qwen3-8B @ L4)"
    )
    if debug:
        for key, value in _masked_config().items():
            print(f"  {key}: {value}")
    if check:
        _smoke_check(base)