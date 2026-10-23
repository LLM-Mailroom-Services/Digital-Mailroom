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
└── run.lock             # advisory local-filesystem writer flock
```

## Spec

`config/runs/examples/example.yaml` is the template. Key blocks:

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
  versions:                 # eval-environment prompt versions (any _v0 / _v1 / mutation key)
    correspondence_specialist: correspondence_specialist_v3   # one role: `prompt.agents` OR `versions`

dataset:                    # full mailroom-dataset OR a subset
  provider: huggingface     # or file:/…/x.jsonl (offline)
  repo: Lucius-Morningstar/mailroom-dataset
  config: ground_truth      # labels + doc_text joined on filename
  split: all                # train+test (3,302 rows). `test` cannot back 40/100-per-class.
  revision: ed7576b676343e0b402ec5412cded301e629bdee     # pinned (no floating)
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
         max_num_seqs: 6, enable_prefix_caching: true, enforce_eager: true,
         quantization: "", revision: ""}
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

Exit codes: `0` done · `1` failed · `2` paused · `3` drift/busy/foreign-store refusal.

A matching repeated preflight validates the committed dataset hash, prompt lock,
checkpoint and spec identity and leaves all generation artifacts byte-identical,
including remote call identity. Missing/drifted artifacts fail rather than being
silently rebuilt. It does not repeat live probes for an existing generation.
Preflight shares the endpoint runner's local filesystem writer lock and returns
`busy_refused` immediately when that lock is held. A worker's Volume copy of
`run.lock` is separate: Modal Volumes do not support distributed file locks.
Remote reset protection uses the checkpoint's call ID and a result-path
completion check, never the local flock or a diagnostic call graph.

`--force` is a generation reset. It refuses a running local checkpoint or a
remote call whose completion cannot be proven, even if the local writer lock
is free. For Modal SDK 1.6.2, a nonblocking `FunctionCall.get(timeout=0)` result,
remote execution timeout, terminated-result error or expired output with no
unfinished inputs permits reset. Pending polls, transport/lookup failures and
ambiguous exceptions refuse reset. A terminal-looking checkpoint or call graph
alone is insufficient. Cancel and wait for a paused endpoint or a proven
terminal remote call first. An eligible reset
archives the lock, dataset, items, prompts, checkpoint, events, cold-boot
measurement, worker-local experiment log and cancellation controls together in a unique archive directory.
It does not terminate remote work or bypass foreign-store ownership guards.

Each execution process restores the locked profile, engine model, explicit
`agent_models`, complete `agent_knobs` map and frozen prompt texts/selections.
Existing eval runners' subsequent activations obey that policy too. CLI
`--model`/`--agent-model` selections become lock/spec identity at start;
`agent_models: {judge: model-id}` can also be specified in YAML. Empty maps
preserve legacy spec hashes. Run-id-only resume refuses runtime overrides that
differ from the lock; use a config and a safe explicit reset for new choices.
Provider endpoint URLs and credentials remain operator environment settings.

For a running row-resumable `sorter`/`legalbench` endpoint task, `run cancel`
writes `cancel.request.json` without waiting for the runner's lock and reports
`cancel_requested`. Prepared, paused and terminal local runs report their
current state without creating a pending token. The runner marks `running`
before the first provider submission, so a first-row cancellation still drains
and pauses correctly. A separate short `cancel.lock` serializes control writes
and generation resets without taking the runner lock. The runner checks before
each submission, drains all
submitted calls, persists their results, then acknowledges the token in
`cancel.ack.json` and writes `paused`. The checkpoint remains `running` while
calls drain. Resume ignores an acknowledged token, skips completed indices and
runs the remaining rows; a newer token cannot be erased by an older
acknowledgement. A provider call already submitted can still finish, so pause
latency includes its duration. Whole-run delegates retain their existing
whole-run granularity; this row-level protocol does not add resumability to
those evaluators. Remote `FunctionCall.cancel` behavior is unchanged.

A recovered valid JSONL final record may lack LF; the next append supplies its
separator. Completed per-item summaries and score error counts cover all stored
indices, including earlier invocations. Quality metrics continue to score only
successful predictions, with their own explicit denominator.

API-evals terminal reuse validates the requested spec/prompt/dataset lock and
requires an exact run ID (or exact legacy experiment name) and spec hash in the
record. Substring matches and stale scores cannot satisfy a changed request.
New records also stamp `run_task` from the immutable lock before append,
retaining the evaluator's `task` (`isolated` delegates to `sorter`; `chained`
to `extract`). Both fields are validated: a foreign scorer task cannot pass
by carrying a correct run-task stamp. Legacy records require exact task,
full prompt SHA, dataset fingerprint, bounded time and an unreset legacy lock.
Matching reuse still needs no API key; missing matching evidence fails loudly.

## Preflight

The sandbox `.env` and `config/.env` load before prompt resolution, endpoint
probes, trace credential checks or knob capture, without activating the runtime.
Explicit environment values take precedence. Cold execution still restores
locked prompts/models/knobs rather than later ambient generation settings.

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
- **Modal mode**: immutable lock content identifies the complete generation,
  including its UUID, prompt text and dataset bytes. A new upload uses
  `/runs/.generations/<lock_sha256>/<run_id>` on `sandbox-runs`, with no
  `--force`; mismatched legacy directories are left untouched. An exactly
  matching original `/runs/<run_id>` directory remains resumable. Deploy the
  updated worker before dispatching this protocol; old worker images do not
  understand the new path/expectation payload.
- Spawn expectations and worker progress/terminal values carry the exact
  generation identity. The worker reloads its mounted view before checking
  the expectation, validates before activation, and commits terminal artifacts
  before publishing terminal state. Dict keys include lock content identity.
  Stamped runs reject unstamped/stale terminal caches. Old-format worker
  progress needs a matching legacy lock and a heartbeat after lock creation.
- Terminal pulls validate the fetched lock, dataset, prompt, checkpoint and
  transferable JSON/JSONL in staging before changing local artifacts. Local
  immutable files and writer/control lock inodes stay intact. Finalization
  imports only matching run/spec/generation/task records; a refused pull makes
  status/watch fail instead of reporting completion.
- Resume attaches to a known matching live call. Re-fire requires an expired
  cooldown and result-path proof of termination; unknown status fails closed.
  These checks are not a distributed dispatch lease. Two independent clients
  without a shared recorded call ID can still race to dispatch the same
  generation, as in the baseline worker. Serialize control operations for one
  run across clients; different runs remain independent. This proposal adds
  no atomic lease or unsafe stale-owner takeover. Interrupted no-force uploads
  can require operator recovery after confirming no live writer.

## Remote GPU (Modal)

```bash
# build/deploy the worker once (installs the sandbox package + dojo + otel)
cd deploy && modal deploy modal_job.py
# run
sandbox run start --job-mode modal --config <run.yaml> --watch
```

For long Modal **endpoint** evals against `sandbox-vllm`, use the full mailroom watch
TUI (in-tray + postage + `modal app logs -f`) in a second pane or browser tab —
see **[pretty-logging/mailroom-themed-logging.md](pretty-logging/mailroom-themed-logging.md)**. `sandbox run … --watch`
only streams job progress lines, not vLLM dispatch logs.

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
- Regenerate a committed serving artifact from a live run store (no Modal spend
  on regen — reads `data/runtime/runs/<run_id>/` only):

  ```bash
  sandbox metrics serving-record --run run-20-correspondence-awq-c8
  # → reports/serving/run-20-correspondence-awq-c8.serving.json
  ```

  Wall clock comes from item `ts` spans when present; pass `--wall-seconds` when
  the store lacks timestamps (historical runs). Measured run stores are not
  committed — reproducing byte-identical committed JSON requires the original
  `items.jsonl` + lock under `data/runtime/runs/`.
- Offline Grant-style parity (no Modal secret):
  `sandbox metrics compare --fixture`. Adapter
  (`mailroom_sandbox.eval.serving_parity`) converts `latency_ms`/`ttft_ms`,
  stamps champion token $ for `Qwen/Qwen3-8B`, and checks sandbox rows
  against `get_suite("local_vs_api")`. Dojo still remaps identity
  `serving_kind=modal` → `local` (two-bucket suite); GPU $ stays sandbox-only.

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

See [`docs/runbooks/README.md`](runbooks/README.md) for the Modal L4 Qwen specialist
suite (singular 1×L4 / 1-container) and improved configs. Catalog:
[`config/runbooks/catalog.yaml`](../config/runbooks/catalog.yaml). CLI:
`sandbox runbook show l4-qwen3-8b`.

### AWQ vs FP16 isolation (issue #21) — config only, do not run

[`config/runs/legacy/run-20-correspondence-fp16-c8.yaml`](../config/runs/legacy/run-20-correspondence-fp16-c8.yaml)
is the FP16 twin of `run-20-correspondence-awq-c8`: same seed-42 correspondence
draw (fingerprint `285f423d3708`), same local prompt, concurrency 8, targeting
`Qwen/Qwen3-8B` (non-AWQ). The live quality compare is **blocked until
spend/auth go**. Do not `modal deploy` / `sandbox run start` this YAML from the
diagnosis PR.

When an operator is cleared to run it: `sandbox runbook show improved-correspondence-fp16-c8`.
Confirm the lock fingerprint is `285f423d3708` before scoring. Diagnosis of the
AWQ floor (no GPU):
[`docs/archive/extraction-quality-diagnosis.md`](archive/extraction-quality-diagnosis.md).

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
### Generation integrity

New locked generations carry a unique ID alongside the existing spec hash.
Initial operator generation knobs and resolved prompt bytes are frozen at
preflight. Every execution entry checks dataset, prompt and checkpoint identity
before activation; resume uses the frozen prompt even if its local stem changes.
A missing or damaged artifact refuses execution. An eligible explicit force reset
archives the old generation; API result reuse requires successful evidence from
the current generation and task. Complete old-format evidence retains a narrow
compatibility path; unproven historical records cannot silently become current.
