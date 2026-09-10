"""Modal-deployed vLLM for the local-mailroom-sandbox (KANBAN-064 sibling).

Same env-knob contract as llm-mailroom ``deploy/modal_vllm.py``, plus
sandbox-local cost/scale knobs. App name and cache Volumes are
sandbox-scoped so a workspace can host mailroom + sandbox side by side, or
one deployment can back both via ``VLLM_BASE_URL``.

Pinned / verified 2026-09-09:

* Modal Python SDK **1.5.5** (2026-08-28) — the ``[deploy]`` extra pins
  ``modal==1.5.5``. ``Secret.from_local`` no longer exists in this SDK;
  optional knobs use ``Secret.from_dict`` (``from_local_environ`` raises on
  missing names, which would break optional ``HF_TOKEN`` /
  ``MODAL_VLLM_API_TOKEN``).
* vLLM **v0.28.0** — default image tag ``vllm/vllm-openai:v0.28.0``, matching
  the local compose pin (``v0.29.0`` is the newest stable as of 2026-09-09;
  adopt deliberately after a parity run).
* ``@modal.web_server`` remains supported (not deprecated); ``@app.server``
  (SDK 1.5.1+) is the modern low-latency path — migration notes live in
  ``deploy/README.md``.

Workflow::

    pip install -e ".[deploy]"
    modal token new
    modal run deploy/modal_vllm.py::download_model   # pre-warm HF cache
    modal deploy deploy/modal_vllm.py                # prints the modal.run URL

Then point the sandbox at it::

    SANDBOX_PROFILE=modal-vllm
    DEFAULT_PROVIDER=vllm
    VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1
    VLLM_API_KEY=<MODAL_VLLM_API_TOKEN>
    sandbox health --profile modal-vllm
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import modal

APP_NAME = "sandbox-vllm"
SERVER_PORT = 8000
HF_CACHE_VOLUME_NAME = "sandbox-hf-cache"
VLLM_CACHE_VOLUME_NAME = "sandbox-vllm-cache"
HF_CACHE_MOUNT = "/root/.cache/huggingface"
VLLM_CACHE_MOUNT = "/root/.cache/vllm"

# ── Deploy-time knobs (contract shared with llm-mailroom's Modal app) ───────
MODEL = os.environ.get("MODAL_VLLM_MODEL", "Qwen/Qwen3-8B")
GPU = os.environ.get("MODAL_VLLM_GPU", "L4")
QUANTIZATION = os.environ.get("MODAL_VLLM_QUANTIZATION", "")
MAX_MODEL_LEN = os.environ.get("MODAL_VLLM_MAX_MODEL_LEN", "32768")
REVISION = os.environ.get("MODAL_VLLM_REVISION", "")

# Pinned for reproducible deploys; override deliberately (tag or digest).
VLLM_IMAGE_TAG = os.environ.get("MODAL_VLLM_IMAGE_TAG", "v0.28.0")

# ── Sandbox-local cost/scale knobs (safe defaults) ──────────────────────────
# A test sandbox should never fan out GPUs by accident: max_containers=1 and
# scale-to-zero (min_containers=0) are the default posture.
SCALEDOWN_SECONDS = int(os.environ.get("MODAL_VLLM_SCALEDOWN_SECONDS", 15 * 60))
MAX_CONTAINERS = int(os.environ.get("MODAL_VLLM_MAX_CONTAINERS", 1))
MIN_CONTAINERS = int(os.environ.get("MODAL_VLLM_MIN_CONTAINERS", 0))
STARTUP_TIMEOUT_SECONDS = int(
    os.environ.get("MODAL_VLLM_STARTUP_TIMEOUT_SECONDS", 20 * 60)
)

# Knobs copied from the local env at DEPLOY time (values may be absent).
CONFIG_ENV_KEYS = (
    "MODAL_VLLM_MODEL",
    "MODAL_VLLM_QUANTIZATION",
    "MODAL_VLLM_MAX_MODEL_LEN",
    "MODAL_VLLM_API_TOKEN",
    "HF_TOKEN",
)


def _config_secrets() -> list[modal.Secret]:
    """Deploy-time knobs as an inline Secret (empty list when none are set).

    SDK 1.5.5 removed ``Secret.from_local``. Its replacement,
    ``Secret.from_local_environ``, raises when any named variable is missing,
    but ``HF_TOKEN`` and ``MODAL_VLLM_API_TOKEN`` are optional — so build the
    dict ourselves and let ``Secret.from_dict`` skip absent keys.
    """
    values = {
        name: os.environ.get(name) for name in CONFIG_ENV_KEYS if os.environ.get(name)
    }
    if not values:
        return []
    return [modal.Secret.from_dict(values)]


hf_cache = modal.Volume.from_name(HF_CACHE_VOLUME_NAME, create_if_missing=True)
# vLLM JIT/CUDA-graph compile artifacts: caching them cuts recompilation on
# cold start from minutes to ~seconds (Modal vLLM example, 2026-09).
vllm_cache = modal.Volume.from_name(VLLM_CACHE_VOLUME_NAME, create_if_missing=True)

image = (
    modal.Image.from_registry(f"vllm/vllm-openai:{VLLM_IMAGE_TAG}", add_python="3.12")
    .run_commands("pip install --no-cache-dir huggingface_hub[hf_transfer]")
    .env(
        {
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "HF_XET_HIGH_PERFORMANCE": "1",
        }
    )
)

# Slim image for the pre-warm function (no GPU, no vLLM).
download_image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("huggingface_hub[hf_transfer]")
    .env(
        {
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "HF_XET_HIGH_PERFORMANCE": "1",
        }
    )
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


def _server_env() -> dict[str, str]:
    """Environment for the vLLM process inside the container."""
    env: dict[str, str] = {}
    api_token = os.environ.get("MODAL_VLLM_API_TOKEN", "").strip()
    if api_token:
        # vLLM's native bearer enforcement: requests without
        # `Authorization: Bearer <token>` get a 401.
        env["VLLM_API_KEY"] = api_token
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if hf_token:
        env["HF_TOKEN"] = hf_token
    return env


def build_vllm_command(model: str) -> list[str]:
    """Assemble the `vllm serve` argv. Kept pure for unit testing."""
    cmd = [
        "vllm",
        "serve",
        model,
        "--host",
        "0.0.0.0",
        "--port",
        str(SERVER_PORT),
        "--max-model-len",
        MAX_MODEL_LEN,
    ]
    if REVISION:
        # Pin the Hub revision to avoid silent weight changes.
        cmd += ["--revision", REVISION]
    if QUANTIZATION:
        cmd += ["--quantization", QUANTIZATION]
    cmd += ["--disable-log-requests"]
    return cmd


@app.function(
    gpu=GPU,
    volumes={HF_CACHE_MOUNT: hf_cache, VLLM_CACHE_MOUNT: vllm_cache},
    secrets=_config_secrets(),
    timeout=60 * 30,
    startup_timeout=STARTUP_TIMEOUT_SECONDS,
    scaledown_window=SCALEDOWN_SECONDS,
    min_containers=MIN_CONTAINERS,
    max_containers=MAX_CONTAINERS,
)
@modal.web_server(port=SERVER_PORT, startup_timeout=STARTUP_TIMEOUT_SECONDS)
def serve() -> None:
    model = os.environ.get("MODAL_VLLM_MODEL", MODEL)
    cmd = build_vllm_command(model)
    print("starting:", " ".join(cmd))  # never contains secret values
    subprocess.Popen(cmd, env={**os.environ, **_server_env()})


@app.function(
    image=download_image,
    volumes={HF_CACHE_MOUNT: hf_cache},
    secrets=_config_secrets(),
    timeout=60 * 45,
)
def download_model(model: str = "", revision: str = "") -> None:
    """Pre-warm the HF cache Volume so the first `serve` boot skips downloads.

    ``modal run deploy/modal_vllm.py::download_model [--model ...]``
    """
    from huggingface_hub import snapshot_download

    model = model or os.environ.get("MODAL_VLLM_MODEL", MODEL)
    revision = revision or os.environ.get("MODAL_VLLM_REVISION", REVISION) or None
    snapshot_download(repo_id=model, revision=revision)
    hf_cache.commit()
    print(f"cached {model}" + (f"@{revision}" if revision else ""))


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
        raise SystemExit("401 — set VLLM_API_KEY to the deployed MODAL_VLLM_API_TOKEN")
    if resp.status_code >= 400:
        raise SystemExit(f"HTTP {resp.status_code} from {base}/models")
    payload = resp.json()
    ids = [
        item.get("id")
        for item in payload.get("data", [])
        if isinstance(item, dict) and item.get("id")
    ]
    print(f"ok: {base}/models -> {ids}")


@app.local_entrypoint()
def main(check: bool = False) -> None:
    """`modal run deploy/modal_vllm.py [--check]` — guidance + optional probe."""
    name = Path(__file__).name
    base = os.environ.get("VLLM_BASE_URL", "").rstrip("/")
    print(f"Deploy:   modal deploy {name}")
    print(f"Pre-warm: modal run {name}::download_model")
    print(
        f"Model:    {os.environ.get('MODAL_VLLM_MODEL', MODEL)} on {GPU} "
        f"(image vllm/vllm-openai:{VLLM_IMAGE_TAG})"
    )
    print(f"Endpoint: {base or 'set VLLM_BASE_URL after deploy'}")
    print(
        f"Cost:     GPU billed only while warm; scale-to-zero after "
        f"{SCALEDOWN_SECONDS}s idle (max {MAX_CONTAINERS} container(s))"
    )
    if check:
        _smoke_check(base)
