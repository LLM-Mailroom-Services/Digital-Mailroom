# Offline sandbox

`packages/local-mailroom-sandbox` is a **local-first experiment harness**
around the governed LLM-Mailroom family. It does not reimplement the
13-node graph — it activates profiles, patches config paths, and evals
against the real pipeline (in the monorepo via `[tool.uv.sources]`; see
[[Sub-Package-Sync]]).

**Full reference:** [`docs/SANDBOX-GUIDE.md`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/packages/local-mailroom-sandbox/docs/SANDBOX-GUIDE.md)

---

## Quick start checklist

```bash
# 1. Install
pip install -e ".[dev]"
cp config/.env.example .env

# 2. Start services
sandbox up                                    # langfuse + ollama (default)
sandbox pull-models                           # pull Ollama models

# 3. Verify
sandbox health
sandbox profiles
sandbox agents list

# 4. Run evals (mock — no LLM needed)
sandbox eval sorter --mock
sandbox eval pipeline --mock

# 5. Full stack with Jupyter
sandbox up --compose-profile langfuse --compose-profile ollama --compose-profile jupyter
# → Lab: http://127.0.0.1:8888/lab
# → Langfuse: http://127.0.0.1:3000 (pk-lf-sandbox / sk-lf-sandbox)
```

---

## Provider profiles

`config/profiles/*.yaml` — **ollama is the sandbox default**; all offline first:

| Profile | Provider | Default model | When to use |
| --- | --- | --- | --- |
| `ollama` | Ollama (`:11434`) | `qwen3:8b` | Default; CPU-capable |
| `vllm-local` | vLLM (`:8000`) | `Qwen/Qwen3-8B` | Local GPU host |
| `vllm-remote` | vLLM (`:18000` SSH) | `Qwen/Qwen3-8B` | Lab/remote GPU |
| `modal-vllm` | Modal `*.modal.run` | `Qwen/Qwen3-8B` | Zero-infra remote GPU |
| `llamacpp` | llama.cpp (`:8080`) | `qwen3-8b` | llama.cpp server |
| `lmstudio` | LM Studio (`:1234`) | `qwen3-8b` | LM Studio |
| `openrouter` | OpenRouter | `qwen/qwen3.7-flash` | Opt-in cloud only |

OpenRouter model ids are rewritten to local tags via the overlay —
`DEFAULT_PROVIDER` alone is not enough.

**Switching:** `--profile` AFTER the subcommand (`sandbox eval sorter --profile ollama`)
or `SANDBOX_PROFILE=modal-vllm sandbox eval sorter`. (`sandbox eval` needs its
task positional; `sandbox tunnel` is the exception — profile goes BEFORE the
leaf: `sandbox tunnel --profile vllm-remote plan`.)

---

## Reduced agent profile (HUB-015)

- The **reporter agent is retired**: compile stage is deterministic
  `compile_report` (zero LLM calls).
- **Reviewers stay enabled** (`sorter_reviewer` + `sorter_reviewer_local_v0`).
- Per-agent gates in `config/components.yaml`.

---

## HF targets aligned to the corpus

`data/fixtures/hf/docclass_mini.jsonl` — all 5 doc types with full
mailroom-corpus ground-truth: `expected_subclass` + `expected_fields`
from the 27-key GT schema. See [[HF-Corpus]].

---

## Docker & Jupyter

### Compose profiles

| Profile | Services | Port(s) |
| --- | --- | --- |
| `langfuse` | postgres, clickhouse, redis, minio, langfuse-web/worker | 3000 |
| `ollama` | sandbox-ollama | 11434 |
| `jupyter` | builds `deploy/Dockerfile`, Lab | 8888 |
| `vllm` | vllm server | 8000 |
| `phoenix` | Arize Phoenix | 6006 |
| `llamacpp` | llama.cpp | 8080 |

Images are **version-pinned** (ollama 0.33.2, vllm v0.28.0, phoenix
version-20.4.0, minio RELEASE.2025-09-07…, langfuse 3, redis 7,
clickhouse 24-alpine, pgvector pg16).

The sandbox image (`mailroom-sandbox:offline`) runs as **non-root** (uid
1000; override with `--user "$(id -u):$(id -g)"`) with a **HEALTHCHECK**.

### Standalone image

```bash
docker build -f deploy/Dockerfile -t mailroom-sandbox:offline .
docker run --rm -p 8888:8888 -v "$PWD":/workspace mailroom-sandbox:offline

# CLI inside container:
docker run --rm --entrypoint sandbox mailroom-sandbox:offline pilot --mock
```

### Notebooks

| Notebook | Purpose |
| --- | --- |
| `notebooks/01_offline_environment_setup.ipynb` | .env, profile activate, checklist |
| `notebooks/02_load_clean_prepare_data.ipynb` | Load/clean/write `data/runtime/prepared/` |
| `notebooks/03_offline_sandbox_smoke.ipynb` | Mock pilot/smoke test |

---

## CLI reference

### Core

```bash
sandbox profiles                          # list profiles
sandbox agents list                       # show agents + models
sandbox cutover --profile ollama --agent-model judge=qwen3:14b
sandbox up / down                         # compose services
sandbox pull-models                       # Ollama model pull
sandbox health                            # probe active provider
sandbox fetch-deps                        # clone vendored deps (llm-mailroom v0.6.0)
sandbox fetch-deps --visualizer           # also The-Mailroom
```

### Evaluations

```bash
sandbox eval sorter --mock                # isolated, no LLM
sandbox eval sorter --local               # against live provider
sandbox eval judge --mock
sandbox eval pipeline --mock              # connected graph scoring
sandbox eval local_vs_api --mock          # offline vs API comparison
sandbox matrix --providers ollama --models qwen3:8b --prompts sorter_local_v0 --mock --dry-run
```

### Job system (`sandbox run`)

```bash
sandbox run preflight --config <run.yaml> [--offline] [--live] [--dry-run]
sandbox run start      --config <run.yaml> [--mock|--local] [--job-mode endpoint|modal] [--watch]
sandbox run status     --run-id <id> [--watch] [--json]
sandbox run resume     --config <run.yaml> --run-id <id> [--force]
sandbox run cancel     --run-id <id>
sandbox run list
```

### Prompts & metrics

```bash
sandbox prompts list                      # all pipeline agent prompts
sandbox prompts show <agent> [--variant X]  # unknown agents exit 2 (DMR-056);
                                            # sorter/specialists surface the
                                            # registry version_key (v14/v33)
sandbox metrics compare --runs local,modal,api
sandbox metrics compare --log
```

### Datasets & tunnels

```bash
sandbox datasets pull --max-rows 50       # LIVE pinned Hub pull → data/cache/
                                          # (network; pinned FAMILY_HF_REVISION,
                                          # sha-verified, exit 1 on failure — DMR-056)
sandbox datasets prepare                  # offline JSONL → data/runtime/prepared/
sandbox tunnel --profile vllm-remote plan|up|status|down
```

Whole-run job tasks (`pipeline`/`extract`/`chained`/`isolated`/ANY agent
name) score the run spec's LOCKED dataset — a Hub `dataset:` block means the
connected graph runs on live corpus rows (DMR-056). `task:` is validated at
spec parse; bogus tasks are rejected up front.

### Tests

```bash
pytest -v                                 # network-free suite
SANDBOX_LOCAL_LLM=1 pytest -v             # include live LLM tests
```

---

## Modal deployment (remote GPU)

Modal SDK **1.5.5** (pinned) + vLLM **v0.28.0** (matches local compose pin).

```bash
pip install -e ".[deploy]" && modal token new
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B MODAL_VLLM_GPU=L4 MODAL_VLLM_API_TOKEN=<secret>

modal run deploy/modal_vllm.py::download_model   # pre-warm (CPU-only)
modal deploy deploy/modal_vllm.py                # prints the URL

export VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1
export VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox health --profile modal-vllm
```

Key knobs: `MODAL_VLLM_MODEL`, `MODAL_VLLM_GPU`, `MODAL_VLLM_MAX_MODEL_LEN`,
`MODAL_VLLM_IMAGE_TAG`, `MODAL_VLLM_REVISION`, `MODAL_VLLM_API_TOKEN`,
`MODAL_VLLM_SCALEDOWN_SECONDS`, `MODAL_VLLM_MAX_CONTAINERS`,
`MODAL_VLLM_TP_SIZE` (from the GPU `:N` suffix; must be set for 70B-class),
`MODAL_VLLM_MIN_CONTAINERS`, `MODAL_VLLM_STARTUP_TIMEOUT_SECONDS`.

Debug (DMR-053): `modal run deploy/modal_vllm.py --debug` prints the masked
resolved config; `modal run deploy/modal_vllm.py --check` probes `/models`
with bearer hints.

Full deploy guide: [`deploy/README.md`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/packages/local-mailroom-sandbox/deploy/README.md).
Cost: L4 ≈ $0.80/hr warm, scale-to-zero after 900s.

---

## SSH tunnels (`vllm-remote`)

```bash
export SANDBOX_TUNNEL_HOST=gpu.lab.example SANDBOX_TUNNEL_USER=jdoe
sandbox tunnel --profile vllm-remote plan
sandbox tunnel --profile vllm-remote up      # → localhost:18000
sandbox health  --profile vllm-remote
sandbox eval sorter --local
sandbox tunnel  --profile vllm-remote down
```

---

## Tracing & observability

| Backend | Default | Setup |
| --- | --- | --- |
| Langfuse 3 | Yes | `sandbox up --compose-profile langfuse` |
| Phoenix | Optional | `sandbox up --compose-profile phoenix` |
| Braintrust | Opt-in | Set `BRAINTRUST_API_KEY` |
| none | — | `OBSERVABILITY_PROVIDER=none` |

Default: Langfuse 3 / SDK v4 (`OBSERVABILITY_PROVIDER=langfuse`).
Traces follow the `document-pipeline` pattern: one trace per document,
verb-first spans, managed prompts, auto-created score configs.

---

## CHTC / HTCondor

See [`deploy/htcondor/README.md`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/packages/local-mailroom-sandbox/deploy/htcondor/README.md).

- **Shared pool** → batch eval (`vllm_batch_eval.sub`): job hosts vLLM
  itself, runs evals in-process, transfers `results/` back.
- **Owned machines** → server (`vllm_serve.sub`): long-lived vLLM +
  `condor_ssh_to_job` forwarding → `vllm-remote` profile.

Set `SANDBOX_DEBUG=1` in the `.sub` environment for a full `set -x` trace;
every step also lands in `results/run.log`, and any failure dumps package
versions + masked env + the vLLM log tail (DMR-053).

---

## Troubleshooting

| Symptom | Cause / Fix |
| --- | --- |
| `401` on `/v1/models` | `VLLM_API_KEY` must equal `MODAL_VLLM_API_TOKEN` |
| First request slow | Cold start; pre-warm or raise `MODAL_VLLM_SCALEDOWN_SECONDS` |
| CUDA OOM at boot | Lower `MAX_MODEL_LEN`, quantize, or bigger GPU |
| `--disable-log-requests` unrecognized | v0.28.0 renamed it; use `--no-enable-log-requests` |
| `Secret.from_local` error | SDK 1.5.5 removed it; this repo uses `from_dict` |
| `json_object_ok: false` | Engine lacks structured output; use vLLM or recent Ollama |
| Tunnel port in use | `sandbox tunnel down` first; check `data/runtime/tunnel-*.pid` |
| `503` from a `*.modal.run` endpoint | scale-to-zero cold start — llm-mailroom retries on a 90s base / 240s cap backoff (DMR-052) |
