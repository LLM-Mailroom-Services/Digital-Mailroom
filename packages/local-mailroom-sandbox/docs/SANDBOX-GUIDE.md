# Offline Sandbox — Complete Usage Guide

A single reference for setting up, configuring, and using every feature of
`local-mailroom-sandbox`. This is the checklist; the deep-dive docs live in
`docs/` subdirectory files linked throughout.

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Initial setup](#2-initial-setup)
3. [Configuration](#3-configuration)
4. [Provider profiles](#4-provider-profiles)
5. [CLI reference](#5-cli-reference)
6. [Docker & Jupyter](#6-docker--jupyter)
7. [Evaluations](#7-evaluations)
8. [Job system (sandbox run)](#8-job-system-sandbox-run)
9. [Modal deployment](#9-modal-deployment)
10. [SSH tunnels (vllm-remote)](#10-ssh-tunnels-vllm-remote)
11. [Tracing & observability](#11-tracing--observability)
12. [Datasets & fixtures](#12-datasets--fixtures)
13. [Metrics & comparison](#13-metrics--comparison)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | `pyproject.toml` `requires-python` |
| Docker + Compose | latest | For compose profiles and the Jupyter image |
| NVIDIA GPU (optional) | Any CUDA GPU | Required only for `vllm` compose profile or local vLLM |
| Modal CLI (optional) | SDK 1.5.5 | For remote GPU deployment |
| Ollama (optional) | latest | Default local LLM; CPU-capable for small models |

---

## 2. Initial setup

```bash
# Clone and install
git clone <repo-url> && cd local-mailroom-sandbox
pip install -e ".[dev]"              # core install (editable)
# OR for full feature set:
pip install -e ".[dev,notebooks,hf]" # + Jupyter notebooks + HF dataset loading

# Environment
cp config/.env.example .env          # edit as needed
```

**What each extra provides:**

| Extra | Packages |
|---|---|
| `dev` | pytest, ruff, mypy |
| `notebooks` | jupyter, ipykernel |
| `hf` | huggingface_hub, pyarrow |
| `deploy` | modal (SDK 1.5.5 pinned) |
| `pipeline` | llm-mailroom + llm-dojo-scoring |
| `observability` | opentelemetry-sdk, opentelemetry-exporter-otlp-proto-http |

---

## 3. Configuration

### Environment variables (`.env`)

The sandbox reads `.env` from the repo root. Key groups:

| Variable | Default | Purpose |
|---|---|---|
| `SANDBOX_PROFILE` | `ollama` | Active provider profile |
| `DEFAULT_PROVIDER` | `ollama` | Mailroom LLM provider |
| `OBSERVABILITY_PROVIDER` | `langfuse` | Tracing backend (`langfuse` / `phoenix` / `braintrust` / `none`) |
| `OBSERVABILITY_ENVIRONMENT` | `pilot` | Trace environment tag |
| `MAILROOM_BASE_DIR` | `./data` | Data root |

### Config files

| File | Purpose |
|---|---|
| `config/profiles/*.yaml` | Provider profiles (ollama, vllm-local, modal-vllm, etc.) |
| `config/models.yaml` | OpenRouter→local model ID mapping |
| `config/taxonomy.overlay.yaml` | Agent-level overrides (temperature, max_tokens) |
| `config/components.yaml` | Agent enable/disable gates |
| `config/taxonomy.yaml` | Full pipeline taxonomy (doc classes, agents, thresholds) |
| `config/runs/*.yaml` | Job runner specs (`sandbox run`) |

### Switching profiles

```bash
# Permanent (edit .env):
SANDBOX_PROFILE=modal-vllm

# Per-command:
sandbox eval sorter --local --profile modal-vllm

# Or via env:
SANDBOX_PROFILE=vllm-local sandbox eval sorter --local
```

**Important:** pass `--profile` AFTER the subcommand, not before. A
`--profile` before the subcommand is clobbered by the subparser default.

---

## 4. Provider profiles

| Profile | Provider | Base URL | Default Model | When to use |
|---|---|---|---|---|
| `ollama` | Ollama | `localhost:11434/v1` | `qwen3:8b` | Default; CPU-capable |
| `vllm-local` | vLLM | `localhost:8000/v1` | `Qwen/Qwen3-8B` | Local GPU host |
| `vllm-remote` | vLLM | `localhost:18000/v1` (SSH forward) | `Qwen/Qwen3-8B` | Lab/remote GPU |
| `modal-vllm` | vLLM | `*.modal.run/v1` | `Qwen/Qwen3-8B` | Zero-infra remote GPU |
| `llamacpp` | generic | `localhost:8080/v1` | `qwen3-8b` | llama.cpp server |
| `lmstudio` | generic | `localhost:1234/v1` | `qwen3-8b` | LM Studio |
| `openrouter` | openrouter | `openrouter.ai/api/v1` | `qwen/qwen3.7-flash` | Opt-in cloud only |

### Health check

```bash
sandbox health                           # default profile
sandbox health --profile vllm-local      # specific profile
sandbox health --profile modal-vllm      # includes bearer check
```

Returns: model list, structured-output capability (`json_object_ok`), and
bearer auth status.

### Surgical model override

```bash
sandbox cutover --profile ollama --agent-model judge=qwen3:14b
sandbox cutover --profile ollama --model llama3.2:3b   # all agents
```

---

## 5. CLI reference

### Core commands

| Command | Description |
|---|---|
| `sandbox profiles` | List available profiles |
| `sandbox agents list` | Show all pipeline agents and their current models |
| `sandbox cutover --profile X --agent-model NAME=tag` | Override one agent's model |
| `sandbox up` | Start compose services (default: langfuse + ollama) |
| `sandbox down` | Stop compose services |
| `sandbox pull-models` | Pull required Ollama models |
| `sandbox health` | Probe the active provider |
| `sandbox fetch-deps` | Optional: refresh the TRACKED vendor snapshots (llm-mailroom v0.6.0 + llm-dojo-scoring v0.12.2) from pinned tags |
| `sandbox fetch-deps --visualizer` | Also clone The-Mailroom |

### Eval commands

| Command | Description |
|---|---|
| `sandbox eval sorter --mock` | Isolated sorter eval (no LLM) |
| `sandbox eval sorter --local` | Sorter eval against live provider |
| `sandbox eval judge --mock` | Judge eval |
| `sandbox eval pipeline --mock` | Connected pipeline scoring |
| `sandbox eval local_vs_api --mock` | Offline vs API serving comparison |
| `sandbox matrix --providers ollama --models qwen3:8b --prompts sorter_local_v0 --mock --dry-run` | Provider×model×prompt matrix |

### Job commands (`sandbox run`)

| Command | Description |
|---|---|
| `sandbox run preflight --config <run.yaml>` | Validate and lock a run spec |
| `sandbox run start --config <run.yaml> --mock` | Execute a locked run |
| `sandbox run status --run-id <id>` | Check run progress |
| `sandbox run resume --config <run.yaml> --run-id <id>` | Resume a paused/failed run |
| `sandbox run cancel --run-id <id>` | Cancel a running job |
| `sandbox run list` | List all runs |

### Prompt & metric commands

| Command | Description |
|---|---|
| `sandbox prompts list` | All pipeline agent prompts (local + Langfuse) |
| `sandbox prompts show <agent>` | Show a specific agent's prompt |
| `sandbox metrics compare --runs local,modal,api` | Compare serving metrics |
| `sandbox metrics compare --log` | Compare from experiment log |

### Dataset commands

| Command | Description |
|---|---|
| `sandbox datasets prepare` | Load/clean/write fixtures to `data/runtime/prepared/` |

### Tunnel commands

| Command | Description |
|---|---|
| `sandbox tunnel plan --profile vllm-remote` | Print the SSH command |
| `sandbox tunnel up --profile vllm-remote` | Start SSH forward |
| `sandbox tunnel status --profile vllm-remote` | Check tunnel status |
| `sandbox tunnel down --profile vllm-remote` | Stop SSH forward |

### Tests

```bash
pytest -v                                # full network-free suite
pytest -v -k "sorter"                    # sorter tests only
SANDBOX_LOCAL_LLM=1 pytest -v            # include live LLM tests
```

---

## 6. Docker & Jupyter

### Compose profiles

| Profile | Services | Port(s) |
|---|---|---|
| `langfuse` | postgres, clickhouse, redis, minio, langfuse-web, langfuse-worker | 3000 |
| `ollama` | sandbox-ollama | 11434 |
| `jupyter` | builds `deploy/Dockerfile`, Lab | 8888 |
| `vllm` | vllm server | 8000 |
| `phoenix` | Arize Phoenix | 6006 |
| `llamacpp` | llama.cpp server | 8080 |

### Quick start

```bash
# Full stack: Langfuse + Ollama + Jupyter
sandbox up --compose-profile langfuse --compose-profile ollama --compose-profile jupyter
# → Lab: http://127.0.0.1:8888/lab
# → Langfuse: http://127.0.0.1:3000 (pk-lf-sandbox / sk-lf-sandbox)

sandbox pull-models                      # pull Ollama models
```

### Standalone Docker image

```bash
docker build -f deploy/Dockerfile -t mailroom-sandbox:offline .
docker run --rm -p 8888:8888 -v "$PWD":/workspace mailroom-sandbox:offline

# Run CLI inside the container:
docker run --rm --entrypoint sandbox mailroom-sandbox:offline pilot --mock
```

### Notebooks

| Notebook | Purpose |
|---|---|
| `notebooks/01_offline_environment_setup.ipynb` | Copy .env, activate profile, verify |
| `notebooks/02_load_clean_prepare_data.ipynb` | Load/clean/write `data/runtime/prepared/` |
| `notebooks/03_offline_sandbox_smoke.ipynb` | Mock pilot/smoke test |

---

## 7. Evaluations

### Isolated agent evals

```bash
sandbox eval sorter --mock              # deterministic, no LLM
sandbox eval sorter --local             # against live provider
sandbox eval judge --mock
sandbox eval contracts_specialist --mock
sandbox eval arbiter --mock
```

### Connected pipeline eval

```bash
sandbox eval pipeline --mock            # full graph, mock LLM
sandbox eval pipeline --local           # full graph, live provider
```

### Offline vs API comparison

```bash
sandbox eval local_vs_api --mock        # no API key needed
sandbox eval local_vs_api --local       # needs Ollama/vLLM running
```

Returns a T0/T1 table, scorecard with identity tags, and token × price cost.

### Provider × model × prompt matrix

```bash
sandbox matrix \
  --providers ollama \
  --models qwen3:8b \
  --prompts sorter_local_v0 \
  --mock --dry-run
```

### Running tests

```bash
# Network-free (default):
pytest -v

# Include live LLM tests:
SANDBOX_LOCAL_LLM=1 pytest -v
```

---

## 8. Job system (`sandbox run`)

The DMR-027 job CLI runs pipeline evals as **locked, resumable jobs** with
crash-safe checkpoints.

### Workflow

```bash
# 1. Write a run spec (see config/runs/example.yaml)
# 2. Preflight: validate, prepare, lock
sandbox run preflight --config config/runs/my-run.yaml

# 3. Start the run
sandbox run start --config config/runs/my-run.yaml --mock

# 4. Check status
sandbox run status --run-id <id>

# 5. Resume after pause/failure
sandbox run resume --config config/runs/my-run.yaml --run-id <id>

# 6. Cancel if needed
sandbox run cancel --run-id <id>

# 7. List all runs
sandbox run list
```

### Run spec structure

```yaml
schema: sandbox.run/v1
run_id: <auto if omitted>
task: sorter                  # sorter | legalbench (per-item) | pipeline | extract |
                              # chained | local_vs_api | isolated | ANY agent name
                              # (DMR-056: every AgentSpec is a whole-run task)
profile: vllm-local           # provider profile

prompt:
  default: {source: code-default}
  agents:
    judge: {source: local, file: judge_local_v0}
    sorter: {source: langfuse, name: mailroom-sorter, version: 9}

dataset:
  provider: huggingface
  repo: Lucius-Morningstar/mailroom-corpus
  config: ground_truth
  split: test
  revision: <pinned-sha>
  strata: {expected: [insurance_claim, contract]}
  limit: 50
  sample_seed: 42

engine:
  kind: modal-vllm
  model: Qwen/Qwen3-8B
  vllm: {max_model_len: 16384, gpu_memory_utilization: 0.90}
  # DMR-056: 16384 default — L4-bf16 8B-class rows cannot hold 32768 (v0.28.0
  # raises at boot); AWQ rows set 32768 explicitly.

trace:
  sink: langfuse
  environment: pilot
```

### Run artifacts

```
data/runtime/runs/<run_id>/
├── spec.lock.json       # immutable preflight manifest
├── prompt.lock.json     # resolved prompts + sha256
├── dataset.jsonl        # prepared subset
├── items.jsonl          # per-item results (progress truth)
├── checkpoint.json      # atomic mirror
├── events.jsonl         # lifecycle journal
└── run.lock             # advisory single-writer flock
```

### Modal remote mode

```bash
cd deploy && modal deploy modal_job.py  # one-time
sandbox run start --job-mode modal --config config/runs/my-run.yaml --watch
```

---

## 9. Modal deployment

### One-time setup

```bash
pip install -e ".[deploy]"
modal token new
```

### Deploy vLLM

```bash
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_API_TOKEN="$(openssl rand -hex 24)"

# Pre-warm weights (CPU-only, no GPU spend)
modal run deploy/modal_vllm.py::download_model

# Debug / verify (DMR-053)
modal run deploy/modal_vllm.py --debug   # masked resolved config
modal run deploy/modal_vllm.py --check   # probes /models with hints

# Deploy
modal deploy deploy/modal_vllm.py
```

### Connect the sandbox

```bash
export VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1
export VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox health --profile modal-vllm
```

### Key knobs

| Variable | Default | Purpose |
|---|---|---|
| `MODAL_VLLM_MODEL` | `Qwen/Qwen3-8B` | HF model id |
| `MODAL_VLLM_GPU` | `L4` | GPU type |
| `MODAL_VLLM_MAX_MODEL_LEN` | `16384` | Context cap — DMR-056: boot-valid default (v0.28.0 raises when the KV pool can't hold one request); AWQ/FP8 rows use 32768 |
| `MODAL_VLLM_GPU_MEMORY_UTILIZATION` | `0.90` | GPU memory fraction |
| `MODAL_VLLM_MAX_NUM_SEQS` | `256` | Concurrency cap |
| `MODAL_VLLM_TP_SIZE` | GPU `:N` suffix (1 single-GPU) | Tensor-parallel size — must match `MODAL_VLLM_GPU="A100-80GB:2"` for 70B-class |
| `MODAL_VLLM_IMAGE_TAG` | `v0.28.0` | vLLM version pin |
| `MODAL_VLLM_REVISION` | empty | HF revision pin |
| `MODAL_VLLM_SCALEDOWN_SECONDS` | `900` | Idle warm window |
| `MODAL_VLLM_MAX_CONTAINERS` | `1` | Cost guard |

### Teardown

```bash
modal app stop sandbox-vllm              # stop serving (volumes persist)
modal volume ls sandbox-hf-cache         # weights survive
```

Cost: L4 ≈ $0.80/hr warm, scale-to-zero after 900s idle.

---

## 10. SSH tunnels (`vllm-remote`)

For vLLM on any SSH-reachable machine:

```bash
export SANDBOX_TUNNEL_HOST=gpu.lab.example
export SANDBOX_TUNNEL_USER=jdoe

sandbox tunnel --profile vllm-remote plan    # print SSH command
sandbox tunnel --profile vllm-remote up      # forward → localhost:18000
sandbox health  --profile vllm-remote
sandbox eval sorter --local                  # evals hit the tunneled engine
sandbox tunnel  --profile vllm-remote down
```

---

## 11. Tracing & observability

### Backends

| Backend | Default | When to use |
|---|---|---|
| Langfuse 3 | Yes (`OBSERVABILITY_PROVIDER=langfuse`) | Production tracing |
| Arize Phoenix | Optional sidecar | Local OTLP tracing |
| Braintrust | Opt-in | Hosted eval platform |
| none | — | Disable tracing |

### Langfuse setup

```bash
sandbox up --compose-profile langfuse     # starts Langfuse 3 stack
# → http://localhost:3000 (pk-lf-sandbox / sk-lf-sandbox)
```

Traces follow the `document-pipeline` pattern: one trace per document, verb-first
node spans, Langfuse-managed prompts, auto-created score configs.

### Phoenix (local OTLP)

```bash
sandbox up --compose-profile phoenix      # optional sidecar
# → http://localhost:6006
```

---

## 12. Datasets & fixtures

### Offline data prep

```bash
sandbox datasets prepare                  # writes to data/runtime/prepared/
```

### HF fixtures

`data/fixtures/hf/docclass_mini.jsonl` — all 5 doc types with full
mailroom-corpus ground-truth targets (`expected_subclass` + `expected_fields`
from the 27-key GT schema).

### Fetch vendored deps

```bash
sandbox fetch-deps                        # optional: refresh tracked vendor snapshots (llm-mailroom v0.6.0 + llm-dojo-scoring v0.12.2)
sandbox fetch-deps --visualizer           # also clone The-Mailroom
```

---

## 13. Metrics & comparison

### Serving comparison

```bash
sandbox metrics compare --runs local,modal,api
sandbox metrics compare --log             # from experiment log
```

Buckets by profile (`local`/`modal`/`api`), aggregates, computes deltas vs
API (latency, tokens, throughput, cost), and runs dojo pairwise comparisons.

### Experiment log

Reports land in `reports/experiment_log.jsonl` (append-only JSONL). Regenerate
the markdown:

```bash
python scripts/reporting/render_experiment_log.py
```

---

## 14. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `401` on `/v1/models` | Bearer token mismatch | Ensure `VLLM_API_KEY == MODAL_VLLM_API_TOKEN` |
| First request slow | Cold start (Modal) | Pre-warm weights or raise `MODAL_VLLM_SCALEDOWN_SECONDS` |
| CUDA OOM at boot | Model too large for GPU | Lower `MAX_MODEL_LEN`, quantize, or use bigger GPU |
| `unrecognized arguments: --disable-log-requests` | Pre-0.28 vLLM flag | Use `--no-enable-log-requests` (v0.28.0+) |
| `deploy import error on from_local` | Stale Modal SDK | SDK 1.5.5 removed it; this repo uses `from_dict` |
| `sandbox health` shows `json_object_ok: false` | Engine lacks structured output | Use a vLLM/Ollama version that supports `response_format` |
| Compose won't start | Port conflict | Check `docker compose ps` for conflicting services |
| `git ls-files` race in `sync_packages.py` | Fixed in DMR-028 | `patch_push` now extracts committed blobs only |
| Tunnel port already in use | Existing tunnel | `sandbox tunnel down` first, or check `data/runtime/tunnel-*.pid` |
| CHTC job died without a clear error | Debug run | `SANDBOX_DEBUG=1` in the `.sub` environment → `set -x` trace + `results/run.log` + a diagnostics dump (versions, masked env, vLLM log tail, DMR-053) |

---

## Quick reference card

```bash
# Setup
pip install -e ".[dev]" && cp config/.env.example .env

# Default offline workflow
sandbox up && sandbox pull-models
sandbox eval sorter --mock
sandbox eval pipeline --mock

# With Jupyter
sandbox up --compose-profile jupyter
# → http://localhost:8888/lab

# With Modal GPU
pip install -e ".[deploy]" && modal token new
modal run deploy/modal_vllm.py::download_model
modal deploy deploy/modal_vllm.py
export VLLM_BASE_URL=<url>/v1 VLLM_API_KEY=<token>
sandbox health --profile modal-vllm

# Job runner
sandbox run preflight --config config/runs/my-run.yaml
sandbox run start --config config/runs/my-run.yaml --mock
sandbox run status --run-id <id>

# Tests
pytest -v
```
