# Modal + local compose + offline Dockerfile

Remote-serving paths (Modal, SSH-tunneled vLLM, CHTC/HTCondor, conda env)
have their own guides: [`conda/`](conda/) (environment spec),
[`htcondor/`](htcondor/) (CHTC job templates), and
[`../docs/remote-serving.md`](../docs/remote-serving.md) (the overview).

## Compose

```bash
sandbox up                       # langfuse + ollama (from the ollama profile)
sandbox up --compose-profile phoenix --compose-profile vllm
sandbox up --compose-profile jupyter   # builds deploy/Dockerfile → Lab :8888
sandbox down
```

Profiles: `langfuse`, `phoenix`, `ollama`, `vllm`, `llamacpp`, `jupyter`.

Langfuse 3 (`langfuse-web` + `langfuse-worker`) is the default tracing sink.
Phoenix is optional. Headless project keys are `pk-lf-sandbox` / `sk-lf-sandbox`
(see `config/.env.example`).

vLLM needs an NVIDIA GPU on the host. Ollama runs on CPU for smoke models
(`llama3.2:3b`); use a GPU host for `qwen3:8b`.

## Offline Dockerfile + Jupyter notebooks

[`Dockerfile`](Dockerfile) builds `mailroom-sandbox:offline` (Python 3.11 + sandbox +
Jupyter Lab). Full walkthrough: [`docs/docker-offline.md`](../docs/docker-offline.md).

```bash
# Image alone
docker build -f deploy/Dockerfile -t mailroom-sandbox:offline .

# Or via compose (mounts the repo at /workspace)
sandbox up --compose-profile langfuse --compose-profile ollama --compose-profile jupyter
# → http://127.0.0.1:8888/lab  (notebooks/01…03)
sandbox datasets prepare         # same cleaners the notebooks call
```

Dedicated notebooks:

1. `notebooks/01_offline_environment_setup.ipynb` — `.env`, profile activate, checklist  
2. `notebooks/02_load_clean_prepare_data.ipynb` — load/clean/write `data/runtime/prepared/`  
3. `notebooks/03_offline_sandbox_smoke.ipynb` — mock sorter/pipeline smoke

## Modal vLLM (remote GPU)

Modal SDK **1.5.5** (pinned in the `[deploy]` extra) + vLLM **v0.28.0**
(`vllm/vllm-openai:v0.28.0`, matching the local compose pin). Same knob
contract as llm-mailroom KANBAN-064 / entity-extraction KANBAN-096, plus
sandbox-local cost/scale knobs.

### Deploy

```bash
pip install -e ".[deploy]"
modal token new

export MODAL_VLLM_MODEL=Qwen/Qwen3-8B                   # default
export MODAL_VLLM_GPU=L4                                # 24 GB; justify bigger
export MODAL_VLLM_API_TOKEN="$(openssl rand -hex 24)"   # shared endpoints
# optional: export HF_TOKEN=...                         # gated weights

# 1) pre-warm weights into the sandbox-hf-cache Volume (CPU-only, no GPU spend)
modal run deploy/modal_vllm.py::download_model

# 2) deploy (prints the URL)
modal deploy deploy/modal_vllm.py
```

Endpoint: `https://<workspace>--sandbox-vllm-serve.modal.run`.

### Verify + point the sandbox at it

```bash
export VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1
export VLLM_API_KEY="$MODAL_VLLM_API_TOKEN"
sandbox health --profile modal-vllm

# raw check — 401 without the bearer (vLLM enforces it in-container)
curl -sS -H "Authorization: Bearer $VLLM_API_KEY" "$VLLM_BASE_URL/models"
# or, with VLLM_BASE_URL/VLLM_API_KEY exported:
modal run deploy/modal_vllm.py --check
```

For evals: `SANDBOX_PROFILE=modal-vllm` + `DEFAULT_PROVIDER=vllm` (see
`config/.env.example`), then `sandbox pilot --local --profile modal-vllm`.

### Knobs

| Env | Default | Notes |
| --- | --- | --- |
| `MODAL_VLLM_MODEL` | `Qwen/Qwen3-8B` | HF repo id |
| `MODAL_VLLM_GPU` | `L4` | 24 GB VRAM |
| `MODAL_VLLM_MAX_MODEL_LEN` | `32768` | context cap (KV-cache budget) |
| `MODAL_VLLM_GPU_MEMORY_UTILIZATION` | `0.90` | fraction of GPU memory; vLLM's default is `0.92` |
| `MODAL_VLLM_MAX_NUM_SEQS` | `256` | concurrency cap; vLLM's own L4/OpenAI-server default |
| `MODAL_VLLM_QUANTIZATION` | empty | `awq` / `gptq` / … |
| `MODAL_VLLM_IMAGE_TAG` | `v0.28.0` | pin; tag or `@sha256:` digest |
| `MODAL_VLLM_REVISION` | empty | HF revision (recommended for runs; travels via the deploy Secret) |
| `MODAL_VLLM_API_TOKEN` | empty | maps to `VLLM_API_KEY` (bearer) |
| `HF_TOKEN` | empty | gated/private weights |
| `MODAL_VLLM_SCALEDOWN_SECONDS` | `900` | idle warm window |
| `MODAL_VLLM_MAX_CONTAINERS` | `1` | cost guard; raise deliberately |
| `MODAL_VLLM_MIN_CONTAINERS` | `0` | scale-to-zero |
| `MODAL_VLLM_STARTUP_TIMEOUT_SECONDS` | `1200` | first-boot budget |

Image pin: v0.28.0 tracks the local compose pin so offline and Modal runs
speak the same engine version. v0.29.0 is the newest upstream stable
(released 2026-09-09) but flips Model Runner V2 to the default for all
models — bump **both** pins together only after a live parity run.

### Engine posture (v0.28.0, docs-verified 2026-09-09)

The local compose service (`deploy/docker-compose.yml`) and this app send
the same `vllm serve` argv:

| Flag | Value | Why |
| --- | --- | --- |
| `--host` / `--port` | `0.0.0.0` / `8000` | reachable from the compose network / Modal proxy |
| `--max-model-len` | `32768` (knob) | caps the KV-cache working set |
| `--gpu-memory-utilization` | `0.90` (knob) | vLLM's default is `0.92`; 0.90 keeps headroom on a 24 GB L4 and on shared local GPUs |
| `--max-num-seqs` | `256` (knob) | vLLM's own L4/OpenAI-server default, pinned so local and Modal schedule the same concurrency on any GPU |
| `--no-enable-log-requests` | on | v0.28.0 made request logging opt-in (`--enable-log-requests`); the pre-0.28 `--disable-log-requests` flag no longer exists |
| `--revision` / `--quantization` | optional | weight pin / quantized checkpoints (Modal knobs; compose overrides via a command override) |

Deliberately **not** set — the v0.28.0 defaults are already the safe test
posture:

- **Chunked prefill** — on by default (`SchedulerConfig.enable_chunked_prefill=True`).
- **Prefix caching** — on by default for decoder-only models
  (`CacheConfig.enable_prefix_caching=True`); the sandbox evals reuse a
  system prefix, so it pays off with no flag.
- **CUDA graphs / `--enforce-eager`** — graphs stay on; the
  `sandbox-vllm-cache` Volume mounts vLLM's default `VLLM_CACHE_ROOT`
  (`~/.cache/vllm`), so JIT/compile artifacts survive cold boots.
- **`--async-scheduling`** — opt-in in v0.28.0 (default scheduler is
  synchronous); a test sandbox values reproducibility over the latency win.
- **`--served-model-name`** — the default served id is the HF repo id, which
  the profiles' `default_model` (and `sandbox health`) already expect.
- **`--guided-decoding-backend`** — replaced by `--structured-outputs-config`
  (backend default `auto`, xgrammar); `response_format={"type":
  "json_object"}` works unflagged.
- **`--swap-space`** — removed with the V1 engine; CPU swap is not a
  v0.28.0 knob.

### Cost (verified 2026-09-09, modal.com/pricing)

| GPU | $/sec | ≈ $/hr |
| --- | --- | --- |
| L4 | 0.000222 | 0.80 |
| A10 | 0.000306 | 1.10 |
| A100 40 GB | 0.000583 | 2.10 |
| A100 80 GB | 0.000694 | 2.50 |
| H100 SXM5 | 0.001097 | 3.95 |
| H200 SXM | 0.001261 | 4.54 |
| B200 | 0.001736 | 6.25 |

- Scale-to-zero: no GPU billing while idle; containers stay warm for
  `MODAL_VLLM_SCALEDOWN_SECONDS` after the last request.
- `max_containers=1` by default — load tests must raise it on purpose.
- `download_model` runs CPU-only; Volumes are `$0.09/GiB/mo` (first 1 TiB
  free) and persist weights + compile artifacts across deploys.
- Spend check: `modal billing summary` / `modal billing rates` (SDK 1.5.3+).

### Teardown

```bash
modal app stop sandbox-vllm          # stop serving (Volumes persist)
modal volume ls sandbox-hf-cache     # weights survive
modal volume ls sandbox-vllm-cache   # vLLM JIT/CUDA-graph cache
```

### Security model

- Private endpoint: bearer enforced by vLLM inside the container
  (`MODAL_VLLM_API_TOKEN` → `VLLM_API_KEY`). Never deploy a shared endpoint
  without it.
- The bearer covers the `/v1`, `/v2`, `/inference`, and `/cohere` path
  prefixes; `/health` (and `/metrics`) stay unauthenticated by design. So
  `sandbox health` proves the token on `/v1/models` — a 200 from `/health`
  only means the process is up.
- Secrets are built at deploy time from local env (`Secret.from_dict`); only
  variable names appear in the repo. The app prints argv, never token values.
- Do **not** set `requires_proxy_auth=True`: the OpenAI client seam speaks
  `Authorization: Bearer`, not `Modal-Key`/`Modal-Secret` headers.

### Cold starts, snapshots, modern decorator

- Pre-warm (weights) + the `sandbox-vllm-cache` Volume (JIT/CUDA graphs) are
  the cold-start mitigations.
- Memory snapshots are intentionally **not** enabled: GPU snapshots are
  alpha, vLLM needs the dedicated KV-cache-discarding pattern
  (`modal.com/docs/examples/vllm_snapshot`), and weight loading is
  storage-bound — snapshots would add overhead without speeding it up.
- `@modal.web_server` is current and supported. `@app.server` (SDK 1.5.1+)
  is Modal's newer low-latency primitive; migrating is a deliberate
  follow-up — `@app.server` authenticates via proxy tokens by default, so
  the bearer contract above would need `unauthenticated=True` + vLLM's own
  bearer, and its 503-when-cold semantics need client handling.

### Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `401` | `VLLM_API_KEY` must equal the deployed `MODAL_VLLM_API_TOKEN` |
| first request slow | cold start; pre-warm and/or raise `MODAL_VLLM_SCALEDOWN_SECONDS` |
| CUDA OOM at boot | lower `MODAL_VLLM_MAX_MODEL_LEN`, quantize, or pick a bigger GPU |
| deploy import error on `from_local` | stale app revision — SDK 1.5.5 removed it; this file uses `from_dict` |

## Remote job worker (`modal_job.py`)

The DMR-027 job CLI's remote mode pushes a locked run dir to the
`sandbox-runs` Volume and spawns `run_job`:

```bash
modal deploy modal_job.py        # once (installs sandbox pkg + dojo + otel)
sandbox run start --job-mode modal --config <run.yaml> --watch
```

Deploy-time env (export before `modal deploy`): `LANGFUSE_*`,
`OTEL_EXPORTER_OTLP_ENDPOINT`, `VLLM_BASE_URL`, `VLLM_API_KEY`, `HF_TOKEN`.
See `docs/jobs.md`.
| `unrecognized arguments: --disable-log-requests` | pre-0.28 flag — v0.28.0 renamed it to the opt-in `--enable-log-requests`; the app/compose pin it off with `--no-enable-log-requests` |
| changed a `MODAL_VLLM_*` knob, redeployed, no effect | deploy-time knobs travel through the Secret; export the new value and re-run `modal deploy` |
