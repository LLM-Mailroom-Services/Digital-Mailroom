# Jobs (DMR-027) — spec-driven, locked, resumable runs

The `sandbox run` system runs **pipeline evals as locked jobs**: every input —
prompt version(s) for any pipeline agent, the HF dataset (full mailroom-corpus
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
task: sorter                # sorter | legalbench (per-item v1); others at whole-run
profile: vllm-local         # ollama | vllm-local | vllm-remote | modal-vllm | openrouter

prompt:                     # ALL pipeline agents: local variants + Langfuse + code
  default: {source: code-default}
  agents:
    judge: {source: local, file: judge_local_v0}
    sorter: {source: langfuse, name: mailroom-sorter, version: 9}   # integer pin

dataset:                    # full mailroom-corpus OR a subset
  provider: huggingface     # or file:/…/x.jsonl (offline)
  repo: Lucius-Morningstar/mailroom-corpus
  config: ground_truth      # labels + doc_text joined on filename
  split: test
  revision: eafe1ab4c0d330d8f9c7a5fb254155e75d290828     # pinned (no floating)
  strata: {expected: [insurance_claim, contract]}
  limit: 50
  sample_seed: 42

engine:
  kind: modal-vllm            # modal-vllm | vllm-local | vllm-remote
  model: Qwen/Qwen3-8B
  vllm: {max_model_len: 32768, gpu_memory_utilization: 0.90,
         max_num_seqs: 256, quantization: "", revision: ""}
  modal: {app: sandbox-vllm, gpu: L4, image_tag: v0.28.0,
          scaledown_seconds: 900, max_containers: 1, prewarm: true}

job: {mode: endpoint, mock: false, max_retries: 2, fail_fast: false}

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
3. **engine** — vLLM field/range guards (DMR-022 flags, v0.28.0 rules) +
   optional live `/v1/models` probe (`data[0].id == spec.model`) with `--live`.
4. **modal** — GPU/image/`max_containers` guards.
5. **trace sink** — OTLP contract resolved (Langfuse `/api/public/otel`,
   Basic auth + `x-langfuse-ingestion-version: 4`; Phoenix `/v1/traces`;
   generic `OTEL_EXPORTER_OTLP_ENDPOINT`).
6. **lock** — `spec.lock.json` written LAST (the commit point) with
   `spec_hash` over the behavioral core. Resume refuses on drift unless
   `--force`.

## Checkpoint / resume

- `items.jsonl` is the progress source of truth; `checkpoint.json` is the
  atomic mirror. On every load the torn tail is truncated and the cursor is
  recomputed from items (self-healing).
- `run_job` appends one `items.jsonl` row per item (index, expected,
  predicted, ok/error, latency, ts), then writes the checkpoint.
- Ctrl-C → `paused`; errors retry up to `max_retries`; `fail_fast` marks
  `failed`. `resume` continues from the reconciled cursor and never re-runs
  completed rows (indices are contiguous).
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

## Metrics: local vs Modal vs API

`job/metrics.py` builds dojo-compatible serving records from run stores:

- per-run: n, mean e2e/ttft, prompt/completion tokens, tokens/s, `model`
  price from `price_for`, and `estimated_cost_usd` when the price table
  knows the model;
- `sandbox metrics compare` buckets by profile (`local`/`modal`/`api`),
  aggregates each bucket, computes deltas vs API (latency, tt, throughput,
  cost), runs dojo `compare_serving` pairwise (local↔api, modal↔api), and
  prints a markdown table.

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