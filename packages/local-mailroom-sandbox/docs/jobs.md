# Jobs (DMR-027) — spec-driven, locked, resumable runs

The `sandbox run` system runs **pipeline evals as locked jobs**: every input —
prompt version(s) for any pipeline agent, the HF dataset (full mailroom-dataset
or a subset), the vLLM/Modal engine spec, and the OTEL trace sink — is
resolved, validated, prepared, and pinned at **preflight**; the job then runs
per item with crash-safe checkpoints, resumes after pause/failure, and can be
polled. Serving metrics from local, Modal, and API runs are captured and
compared.

```
data/runtime/runs/<run_id>/
├── spec.lock.json       # immutable preflight manifest (the commit point)
├── prompt.lock.json     # per-agent resolved prompt + sha256 / Langfuse version
├── dataset.jsonl        # prepared subset (byte-identical per spec; hashed)
├── items.jsonl          # append-only per-item results (progress truth)
├── checkpoint.json      # atomic mirror (state/cursor/remote)
├── events.jsonl         # lifecycle journal (poll/pause/resume/fail)
└── run.lock             # advisory single-writer flock
```

## Spec

`config/runs/example.yaml` is the template. Key blocks:

```yaml
schema: sandbox.run/v1
run_id: <optional; auto ><task>-<model>-<utc>
task: sorter                # per-item: sorter | legalbench (resumable row-by-row)
                            # whole-run: pipeline | extract | chained | local_vs_api
                            #   | isolated (sorter spec) | ANY registered agent name
                            #   (e.g. judge, contracts_specialist — DMR-056: every
                            #   AgentSpec in eval/agents.py is a whole-run task; a
                            #   bogus task is rejected at spec parse, never "locks
                            #   prepared then dies")
profile: vllm-local         # ollama | vllm-local | vllm-remote | modal-vllm | openrouter

prompt:                     # ALL pipeline agents: local variants + Langfuse + code
  default: {source: code-default}
  agents:
    judge: {source: local, file: judge_local_v0}
    sorter: {source: langfuse, name: mailroom-sorter, version: 9}   # integer pin

dataset:                    # full mailroom-dataset OR a subset
  provider: huggingface     # or file:/…/x.jsonl (offline)
  repo: Lucius-Morningstar/mailroom-dataset
  config: ground_truth      # labels + doc_text joined on filename
  split: all                # train+test (3,302 rows). `test` cannot back 40/100-per-class.
  revision: 46a4d3c240a36671cde0182fff4960f6b8b73aca     # pinned (no floating)
  strata:
    buckets:
      - {doc_class: contract, count: 40}          # or 20 / 100; merger max 152
      - {doc_class: corporate_record, count: 40}
      - {doc_class: correspondence, count: 40}
      - {doc_class: insurance_claim, count: 40}
      - {doc_class: merger_agreement, count: 40}
  limit: 200
  sample_seed: 42

engine:
  kind: modal-vllm            # modal-vllm | vllm-local | vllm-remote
  model: Qwen/Qwen3-8B
  vllm: {max_model_len: 16384, gpu_memory_utilization: 0.90,
         max_num_seqs: 256, quantization: "", revision: ""}
  # DMR-056: 16384 default — L4-bf16 8B-class rows cannot hold 32768 (v0.29.0
  # raises at boot when the KV pool can't fit one request); AWQ rows set 32768.
  modal: {app: sandbox-vllm, gpu: L4, image_tag: v0.29.0,
          scaledown_seconds: 120, max_containers: 1, min_containers: 0,
          prewarm: true}  # attended; restore 600 unattended (DMR-076)

job:
  mode: endpoint            # endpoint | modal
  mock: false
  max_retries: 2
  fail_fast: false
  concurrency: 4            # default JobSpec value — efficient conservative
                            # vs Modal vLLM continuous batching (docs: 4-16);
                            # set 1 explicitly for serial/CPU-Ollama runs
                            # — bounded to [1, 64] at spec validation

trace:
  sink: langfuse            # langfuse | phoenix | otlp | none
  otlp: true
  environment: pilot
  tags: [sandbox, job]
```

## CLI

```bash
sandbox run preflight --config <run.yaml> [--offline] [--live] [--dry-run]
sandbox run start      --config <run.yaml> [--mock|--local] [--job-mode endpoint|modal] [--watch]
sandbox run status     --run-id <id> [--watch] [--json]
sandbox run resume     --config <run.yaml> --run-id <id> [--force]
sandbox run cancel     --run-id <id>
sandbox run list

sandbox prompts list                       # every pipeline agent prompt (local + Langfuse)
sandbox prompts show <agent> [--variant X]
sandbox metrics compare --runs a,b[,c]     # local / Modal / API comparison
sandbox metrics compare --log
```

Exit codes: `0` done · `1` failed · `2` paused · `3` drift refused.

## Preflight

1. **prompt** — resolves every agent override (local file sha256, Langfuse
   pushed integer version id, or code default). Unknown agents fail closed.
2. **dataset** — pinned-revision parquet (`default`+`ground_truth` joined on
   `filename`), `content_sha256 == sha256(doc_text)` verified per row, then
   deterministic subsetting (sorted by filename/id, per-stratum sub-seed
   draws, union, re-sort, `limit`). `file://` paths short-circuit all Hub
   calls. Idempotent: same spec → byte-identical `dataset.jsonl`.
3. **engine** — vLLM field/range guards (DMR-022 flags, v0.29.0 rules) +
   optional live `/v1/models` probe (`data[0].id == spec.model`) with `--live`.
   `run start --job-mode modal` probes the engine before firing (DMR-048).
4. **modal** — GPU/image/`max_containers` guards.
5. **trace sink** — OTLP contract resolved (Langfuse `/api/public/otel`,
   Basic auth + `x-langfuse-ingestion-version: 4`; Phoenix `/v1/traces`;
   generic `OTEL_EXPORTER_OTLP_ENDPOINT`).
6. **lock** — `spec.lock.json` written LAST (the commit point) with
   `spec_hash` over the behavioral core. Resume refuses on drift unless
   `--force`. The lock also pins `revision_resolved` + `prompt_text_sha`; a
   prompt-text change refuses (DMR-049), and `dataset.sha256` is re-verified
   at worker start and at resume — drift refuses (exit 3) unless `--force`
   re-locks and archives the old generation.

## Checkpoint / resume

- `items.jsonl` is the progress source of truth; `checkpoint.json` is the
  atomic mirror. On every load the torn tail is truncated and the cursor is
  recomputed from items (self-healing).
- `run_job` appends one `items.jsonl` row per item (index, expected,
  predicted, ok/error, latency, ts), then writes the checkpoint.
- Ctrl-C → `paused`; errors retry up to `max_retries`; `fail_fast` marks
  `failed` (with `concurrency > 1` it stops *scheduling* new rows; in-flight
  rows finish and persist — their GPU work is already spent). `resume` never
  re-runs completed rows: it skips by completed **index**, so concurrent
  runs whose items completed out of order resume exactly (the old
  contiguous-cursor skip would silently drop rows).
- **`concurrency: N`** (job block, `[1, 64]`) runs N rows in parallel so a
  vLLM endpoint's continuous batching fills up — offline evals are a
  throughput workload (Modal `vllm_throughput` exemplar). Workers only
  compute; every RunStore write and progress event happens on the main
  thread, and each row runs in a copied context so the pipeline's
  contextvar run limits and trace state stay per-doc isolated.   Recommended:
  4-16 against a Modal-hosted vLLM (JobSpec default is **4** — the efficient
  conservative sweet spot); set `concurrency: 1` explicitly for CPU Ollama or
  per-item latency-sensitive runs.
- **Modal mode**: the run dir is pushed to the `sandbox-runs` Volume and the
  remote worker mirrors progress to the `sandbox-job-state` Dict; the CLI
  polls it. Resume re-attaches to a live `FunctionCall` or re-spawns the same
  `run_id` after the lease goes stale (double-execution guard).

## Remote GPU (Modal)

```bash
# build/deploy the worker once (installs the sandbox package + dojo + otel)
cd deploy && modal deploy modal_job.py
# run
sandbox run start --job-mode modal --config <run.yaml> --watch
```

The worker runs the same checkout code on a CPU container against the
Modal-hosted `sandbox-vllm` endpoint (the GPU is the serve app). It emits
OTEL job/item spans to the locked sink. In-container vLLM (GPU job) is a
documented follow-up.

- `run start --job-mode modal` probes `/v1/models` first (skipped for
  mock/`--offline`) — a stale `VLLM_BASE_URL` fails fast as
  `engine_unreachable` (DMR-048).
- Whole-run tasks (`pipeline`/`extract`/`chained`/agent names) score the
  LOCKED dataset rows when preflight prepared any (Hub or local) — a Hub
  spec + `task: pipeline` runs the connected graph on live corpus rows
  (DMR-056); an empty lock falls back to the runners' fixture defaults.
- Worker failures land in the state dict with `error`, `traceback_tail`, and
  runtime `diagnostics`; `SANDBOX_DEBUG=1` enables DEBUG logging in the
  container — export it BEFORE `modal deploy` (it travels through the deploy
  Secret; DMR-056); `modal run modal_job.py --debug` prints the app config
  (DMR-053).
- Whole-run records are stamped `prompt_version` (the lock's LOCAL variant
  stem), `spec_hash`, `dataset_fingerprint`, `run_id`; delegated runs used to
  mislabel every record `mailroom-default` (DMR-053).

## Metrics: local vs Modal vs API

`job/metrics.py` builds dojo-compatible serving records from run stores:

- per-item (`items.jsonl`): `latency_ms`, and when the live OpenAI-compatible
  response exposes usage — `prompt_tokens`, `completion_tokens`, `llm_calls`;
  `ttft_ms` only when recorded (never inferred from e2e);
- per-run: n, mean e2e/ttft, prompt/completion tokens, tokens/s, `model`
  price from `price_for` / sandbox champion table, `estimated_cost_usd` +
  `cost_per_document` when the price table knows the model;
- Modal / vLLM GPU attribution: `gpu_seconds` × configurable L4 rate
  (default ≈ `$0.80/hr`, env `MODAL_GPU_USD_PER_HOUR` /
  `MODAL_GPU_USD_PER_SEC`) → `estimated_gpu_cost_usd` +
  `gpu_cost_per_document`. Prefer `MODAL_BILLED_GPU_SECONDS` when you have a
  warm billed window; else sum of ok-item `latency_ms` (busy-time lower bound).
  Missing tokens/GPU seconds omit the $ fields (loud warning) — never silent `$0`;
- `sandbox metrics compare` buckets by profile (`local`/`modal`/`api`),
  aggregates each bucket, computes deltas vs API (latency, ttft, throughput,
  token $, GPU $), runs dojo `compare_serving` pairwise (local↔api,
  modal↔api, local↔modal), and prints a markdown table.

### Sorter vs ModernBERT

```bash
sandbox eval sorter_vs_modernbert --mock
sandbox metrics compare --sorter-vs-modernbert
sandbox metrics compare --sorter-vs-modernbert --runs <sorter-run>,<modernbert-run>
```

Fixtures: `data/fixtures/serving/sorter_vs_modernbert.json`. Compares
accuracy / F1 / latency / `$/doc` between the LLM sorter and the trained
ModernBERT ingest classifier (mailroom-ml / Corpus-EDA).

Live feeder (no weight copies into the sandbox):

```bash
export MAILROOM_ML_SRC=/Users/morningstar/Desktop/Cold_Storage/mailroom-ml
export MODERNBERT_MODEL_PATH=$MAILROOM_ML_SRC/artifacts/run2-published
sandbox modernbert status
sandbox modernbert eval --sample 50 --json
sandbox eval sorter_vs_modernbert --local   # live ModernBERT + sorter fixture/log
```

### Cost extrapolation

```bash
# Pre-flight (no Modal spend) — specialist 5×30 suite defaults (scaledown 120)
sandbox metrics estimate-suite
sandbox metrics estimate-suite --scaledown-seconds 600 --json  # unattended what-if

# Post-run (needs items.jsonl + lock)
sandbox metrics extrapolate --run run-30-contracts-specialist \
  --corpus-size 3302 --docs-per-day 10000
```

See [`docs/benchmark-l4.md`](benchmark-l4.md) for the Modal L4 Qwen specialist
suite pins, Hermes profile, teardown sequence, and cost-saver path (AWQ gated
by DMR-068).

TTFT is only populated when a run records it (never inferred from e2e).
Document-pipeline eval traces stay on the Langfuse SDK path (family
contract); job/preflight/item spans travel over OTEL (job spans only).

## Tests

The job surface is covered by network-free suites:

```
uv run pytest packages/local-mailroom-sandbox/tests/test_job_spec.py
uv run pytest packages/local-mailroom-sandbox/tests/test_job_checkpoint.py
uv run pytest packages/local-mailroom-sandbox/tests/test_job_preflight.py
uv run pytest packages/local-mailroom-sandbox/tests/test_job_runner.py
uv run pytest packages/local-mailroom-sandbox/tests/test_job_otel.py
uv run pytest packages/local-mailroom-sandbox/tests/test_job_remote.py
uv run pytest packages/local-mailroom-sandbox/tests/test_job_metrics.py
uv run pytest packages/local-mailroom-sandbox/tests/test_job_cli.py
uv run pytest packages/local-mailroom-sandbox/tests/test_corpus.py
uv run pytest packages/local-mailroom-sandbox/tests/test_prompt_registry.py
```