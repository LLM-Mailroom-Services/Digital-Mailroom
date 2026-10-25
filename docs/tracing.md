# Tracing

Canonical sink: **Langfuse 3** (Python SDK v4 data model) on
`http://localhost:3000` (compose profile `langfuse`). This is the same
contract llm-mailroom writes and The-Mailroom reads.

```
OBSERVABILITY_PROVIDER=langfuse   # or auto | phoenix | braintrust | none
OBSERVABILITY_ENVIRONMENT=pilot   # mock for --mock, pilot for --local
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-sandbox
LANGFUSE_SECRET_KEY=sk-lf-sandbox
```

`sandbox up` (ollama profile) starts **langfuse + ollama**. Phoenix remains an
optional sidecar (`--compose-profile phoenix`) — The-Mailroom cannot plot
Phoenix spans.

`auto` follows mailroom's chain: Langfuse if its secret is set, else Braintrust,
else Phoenix, else none.

## Family data model

One document (or isolated agent eval) is one trace:

| Field | Value |
| --- | --- |
| root name | `document-pipeline` |
| root type | `chain` |
| children | verb-first names from `NODE_OBSERVATION_TYPES` |
| `session_id` | `sandbox-<task>-<utc>` for evals; `matter_id` for watcher/api |
| tags | `mailroom`, environment, `sandbox`, profile, `mock`/`local`, `source-*` |
| metadata | `{pipeline: mailroom, run_id, attempt, source}` |
| ground truth on the trace | `expected_hf_class`, `expected_doc_class`, `expected_subclass`, `expected` only |

Isolated evals still open the root chain and nest the one relevant observation
so The-Mailroom can draw a partial conveyor.

Score names follow llm-mailroom `SCORE_CONFIGS` / dojo aliases
(`extraction_overall_verified_precision` → `extraction_verified_precision`).

## The-Mailroom

```bash
sandbox fetch-deps --visualizer
# point The-Mailroom at the same project:
# LANGFUSE_HOST=http://localhost:3000
# MAILROOM_TRACE_NAMES=document-pipeline
# MAILROOM_TRACE_TAGS=mailroom
# MAILROOM_TRACE_ENVIRONMENTS=mock,pilot
```

## Export

```bash
sandbox traces export    # writes data/traces/export.json (host + last trace ids)
```

Inspect traces in the Langfuse UI. Durable scores also live in
`reports/experiment_log.jsonl` and `reports/scores/`.

## Job spans: local first, then upload

`sandbox run start` in endpoint mode (the Modal-vLLM grid and SAND runs) opens a `job.run` span with one
`job.item` child per document (`item_id`, `job.ok`, `job.attempts`, `job.error`,
`gen_ai.usage.input_tokens` / `output_tokens`). Every span is mirrored to
`data/traces/<run_id>.spans.jsonl.gz` (gitignored) **whatever the locked sink is**, including `sink: none`,
so a run is never left without traces. `SANDBOX_TRACE_LOCAL=0` turns the mirror off.

To browse spans live, start Phoenix (`sandbox up --compose-profile phoenix --detach`) and lock new runs with
`trace: {sink: phoenix, otlp: true}`; the mirror still writes when Phoenix is down.

Pack, upload and prune (needs the `[observability]` extra for the OTel SDK; `pyarrow` for Parquet, else `spans.csv.gz`):

```bash
# Drive for desktop path to the LOGS folder (add the shared folder as a shortcut in My Drive so it syncs)
export SANDBOX_TRACE_UPLOAD_DIR="$HOME/Library/CloudStorage/GoogleDrive-<account>/My Drive/LLM-MAILROOM 📮/LOGS"
sandbox traces pack <run_id> --experiment SAND-041 --runner axios --prune
```

`pack` writes `<runner>_<experiment>_<run_id>.zip` (`spans.parquet` zstd + `manifest.json`) to
`data/runtime/exports/<YYYY-MM-DD>/`, copies it to `<dest>/<YYYY-MM-DD>/`, re-hashes the copy and tests the
zip. `--prune` deletes the local mirror and the local zip only after that check passes; without a verified
copy it refuses. Phoenix's own SQLite store (`~/.phoenix`) is a viewing cache and is not touched.
