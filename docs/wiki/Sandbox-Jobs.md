# Job runner (`sandbox run`)

Spec-driven, locked, resumable pipeline evals. Introduced in DMR-027.

**Full reference:** [`docs/jobs.md`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/packages/local-mailroom-sandbox/docs/jobs.md)

---

## Quick start

```bash
# 1. Write a run spec (copy config/runs/example.yaml)
# 2. Preflight: validate + prepare + lock
sandbox run preflight --config config/runs/my-run.yaml

# 3. Execute
sandbox run start --config config/runs/my-run.yaml --mock

# 4. Monitor
sandbox run status --run-id <id>

# 5. Resume after pause/failure
sandbox run resume --config config/runs/my-run.yaml --run-id <id>
```

---

## Run spec (`config/runs/*.yaml`)

```yaml
schema: sandbox.run/v1
task: sorter                  # sorter | legalbench
profile: vllm-local           # provider profile

prompt:
  default: {source: code-default}
  agents:
    judge: {source: local, file: judge_local_v0}
    sorter: {source: langfuse, name: mailroom-sorter, version: 9}

dataset:
  provider: huggingface       # or file:/path/to/data.jsonl
  repo: Lucius-Morningstar/mailroom-corpus
  config: ground_truth
  revision: <pinned-sha>
  strata: {expected: [insurance_claim, contract]}
  limit: 50
  sample_seed: 42

engine:
  kind: modal-vllm            # modal-vllm | vllm-local | vllm-remote
  model: Qwen/Qwen3-8B
  vllm: {max_model_len: 32768, gpu_memory_utilization: 0.90}

trace:
  sink: langfuse              # langfuse | phoenix | otlp | none
  environment: pilot
```

---

## CLI

| Command | Description |
| --- | --- |
| `sandbox run preflight --config <yaml>` | Validate, prepare, lock the spec |
| `sandbox run start --config <yaml> [--mock]` | Execute a locked run |
| `sandbox run status --run-id <id>` | Check progress |
| `sandbox run resume --config <yaml> --run-id <id>` | Resume paused/failed run |
| `sandbox run cancel --run-id <id>` | Cancel a run |
| `sandbox run list` | List all runs |
| `sandbox prompts list` | All pipeline agent prompts |
| `sandbox prompts show <agent>` | Show specific agent prompt |
| `sandbox metrics compare --runs a,b,c` | Compare serving metrics |

---

## Run artifacts

```
data/runtime/runs/<run_id>/
├── spec.lock.json       # immutable preflight manifest
├── prompt.lock.json     # resolved prompts + sha256
├── dataset.jsonl        # prepared subset
├── items.jsonl          # per-item results (progress truth)
├── checkpoint.json      # atomic mirror
├── events.jsonl         # lifecycle journal
├── experiment_log.jsonl # records pulled back from a remote worker (DMR-047)
└── run.lock             # advisory single-writer flock
```

`spec.lock.json` also carries `dataset.sha256`, `revision_resolved`,
`prompt_text_sha`, and `spec_hash`; drift refuses on resume unless `--force`
(DMR-049). Whole-run records are stamped `prompt_version` (the lock's LOCAL
variant stem), `spec_hash`, `dataset_fingerprint`, `run_id` — delegated runs
used to mislabel every record `mailroom-default` (DMR-053).

---

## Checkpoint / resume

- `items.jsonl` is the source of truth; `checkpoint.json` is the atomic mirror.
- On every load, torn tails are truncated and cursor recomputed (self-healing).
- Ctrl-C → paused; errors retry up to `max_retries`; `fail_fast` marks failed.
- `resume` continues from the reconciled cursor — never re-runs completed rows.

---

## Modal remote mode

```bash
cd deploy && modal deploy modal_job.py   # one-time (installs sandbox + dojo + otel)
sandbox run start --job-mode modal --config <yaml> --watch
```

Worker runs on a CPU container against the Modal-hosted `sandbox-vllm` GPU endpoint.
Emits OTEL job/item spans to the locked sink.

- `run start --job-mode modal` probes `/v1/models` before firing (skipped for
  mock/`--offline`) — a stale `VLLM_BASE_URL` fails fast as
  `engine_unreachable` (DMR-048).
- Worker failures land in the state dict with `error`, `traceback_tail`, and
  runtime `diagnostics`; `SANDBOX_DEBUG=1` enables DEBUG logging;
  `modal run modal_job.py --debug` prints the app config (DMR-053).
- `--watch` prints the worker traceback + a diagnose hint on failure (DMR-053).

---

## Metrics: local vs Modal vs API

```bash
sandbox metrics compare --runs local,modal,api
sandbox metrics compare --log
```

Buckets by profile, aggregates each bucket, computes deltas vs API (latency,
tokens, throughput, cost), runs dojo `compare_serving` pairwise.

---

## Tests

```bash
uv run pytest packages/local-mailroom-sandbox/tests/test_job_spec.py
uv run pytest packages/local-mailroom-sandbox/tests/test_job_checkpoint.py
uv run pytest packages/local-mailroom-sandbox/tests/test_job_preflight.py
uv run pytest packages/local-mailroom-sandbox/tests/test_job_runner.py
uv run pytest packages/local-mailroom-sandbox/tests/test_job_otel.py
uv run pytest packages/local-mailroom-sandbox/tests/test_job_remote.py
uv run pytest packages/local-mailroom-sandbox/tests/test_job_metrics.py
uv run pytest packages/local-mailroom-sandbox/tests/test_job_cli.py
```
