---
description: Every configuration key and environment variable.
icon: gear
title: Configuration
---

# Configuration

## `config/taxonomy.yaml`

This is the single source of truth for document classification, pipeline behavior, and agent model mappings. **Nothing is hardcoded** — adding a document class or adjusting thresholds never requires touching agent code.

### Structure

Top-level keys:

```yaml
pipeline:                      # bins + pdf_direct_chars_per_page
llm_retry:                     # transient-failure retry tuning
run_limits:                    # per-run deadline / token budget
chunking:                      # chunked-extraction windows
cost_models:                   # per-1M-token pricing for estimated_cost_usd
confidence:                    # routing thresholds (high/low/retry/bands)
field_scoring:                 # deterministic field-type-aware scorer
vision:                        # additive page-image ingestion
doc_classes:                   # document type definitions
file_extensions:               # accepted file types
agents:                        # per-agent model/provider configs
```

### `pipeline.bins`

Defines the filesystem layout. `{base_dir}` is resolved from the `MAILROOM_BASE_DIR` environment variable (defaults to `./data`).

```yaml
pipeline:
  bins:
    inbox: "{base_dir}/pipeline/inbox"
    processing: "{base_dir}/pipeline/processing"
    classified: "{base_dir}/pipeline/classified"
    review: "{base_dir}/pipeline/review"
    failed: "{base_dir}/pipeline/failed"
    archive: "{base_dir}/archive"
    manifests: "{base_dir}/manifests"
```

### `confidence`

Controls the branching logic in `graph/routing.py`. Tunable without code changes.

| Key                  | Default                | Description                                                                                                                                                                                                         |
| -------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `high`               | 0.97 (global fallback) | Classification/extraction confidence ≥ this auto-continues; per-class overrides apply after `doc_type` is known                                                                                                     |
| `low`                | 0.88 (global fallback) | Below this: retry while `attempts <= retry_max`, then human review                                                                                                                                                  |
| `retry_max`          | 2                      | Maximum classify/extract retries before escalating to human review                                                                                                                                                  |
| `judge_band_high`    | 0.95 (global)          | Lane B completeness-judge gate: `low <= extraction_confidence < judge_band_high` fires `judge_verify`                                                                                                               |
| `arbiter_retry_max`  | 2                      | Max arbiter-approved re-extract loops (approval-inclusive)                                                                                                                                                          |
| `judge_max_passes`   | 3                      | `1 + arbiter_retry_max` — one completeness judge per extraction attempt                                                                                                                                             |
| `conflict_threshold` | 0.3                    | **Unused routing knob** (kept for config-file compatibility). Matter conflicts escalate via deterministic same-class field comparison in `graph/build_graph.py:_detect_conflict`, not an extraction-confidence gap. |
| `by_class`           | (severity map)         | Per-class `high` / `low` / `judge_band_high` for critical contracts/mergers/insurance, elevated corporate, standard correspondence. The `compliance_filing` tier was **removed 2026-09-15** along with the class — see [Agents](agents.md) |

```yaml
confidence:
  high: 0.97
  low: 0.88
  retry_max: 2
  judge_band_high: 0.95
  arbiter_retry_max: 2
  judge_max_passes: 3
  conflict_threshold: 0.3  # unused; conflicts are field-value comparison
  by_class:
    contract: { severity: critical, high: 0.98, low: 0.90, judge_band_high: 0.97 }
    # … merger_agreement, insurance_claim, corporate_record, correspondence
```

#### Tuning guide: what moving each threshold does

These are the directions of effect implied by the routing rules in [Operational procedure](operational-procedure.md) and the [Pipeline flowchart](../the-pipeline-in-depth/flowchart.md). Change one value at a time and re-run a pilot before and after, so any shift in accuracy or cost is attributable.

| Change | Effect on documents | Effect on cost and workload |
| --- | --- | --- |
| Raise `high` | More classifications fall below the auto-continue line, so more go to retry and Lane A | More sorter and reviewer calls; more documents may reach human review |
| Lower `high` | Fewer documents are second-checked | Cheaper and faster, with more risk of an unreviewed misclassification |
| Raise `low` | More documents retry or go to review instead of being accepted at moderate confidence | More retries and more human review |
| Raise `judge_band_high` | More extractions fall into the judged band | More judge (and arbiter) calls; each adds an LLM generation |
| Lower `judge_band_high` | More extractions skip the judge | Fewer calls; completeness gaps are more likely to go unchecked |
| Raise `retry_max` | More attempts before escalating | More LLM calls per hard document, and later escalation |

Per-class values under `by_class` let you do this for one class without touching the others: tighten contracts, for instance, while leaving correspondence alone.

### `doc_classes`

Each entry defines a document type. To add a new type:

1. Add an entry here
2. Create a Pydantic extraction schema in `schemas/documents.py`
3. Create a specialist agent in `agents/`
4. Register the schema in `EXTRACTION_SCHEMAS` dict in `schemas/documents.py`
5. Register the specialist dispatch in `graph/build_graph.py`

\| Field | Description | |---|---|---| | `key` | Internal identifier (used in `doc_type` field) | | `label` | Human-readable label | | `schema` | Pydantic model name for extraction (must match `schemas/documents.py`) | | `specialist` | Agent name (must match an entry under `agents`) | | `description` | Used in Sorter's system prompt for classification | | `field_types` | Per-field deterministic scoring type for the extraction schema (see `field_scoring` below) |

```yaml
doc_classes:
  - key: contract
    label: "Contract / Agreement"
    schema: ContractExtraction
    specialist: contracts_specialist
    description: "Formal agreements between parties: M&A, vendor, employment, NDAs, etc."
    field_types:
      parties: entity_list:name
      effective_date: date
      contract_value: money

  - key: corporate_record
    label: "Corporate Record"
    schema: CorporateRecordExtraction
    specialist: corporate_records_specialist
    description: "Bylaws, resolutions, board minutes, cap table entries, incorporation docs"

  - key: correspondence
    label: "Correspondence"
    schema: CorrespondenceExtraction
    specialist: correspondence_specialist
    description: "Letters, emails, memos, notices, demand letters, press releases, meeting requests"
    field_types:
      sender: name
      recipient: name
      additional_recipients: entity_list
      communication_type: name
      communication_date: date
      demand_amount: money
      action_items: entity_list
      urgency: name
      intent: name
      subject_matter: free_text
      keywords: entity_list:name

  - key: insurance_claim
    label: "Insurance Claim"
    schema: InsuranceClaimExtraction
    specialist: insurance_claims_specialist
    description: "FNOL forms, adjuster reports, demand packages, coverage determinations, denial letters"
```

> `merger_agreement` (MAUD) is a live class with its own `MergerAgreementExtraction` schema and `merger_agreement_specialist`. Predicting `contract` when ground truth is `merger_agreement` is a class miss — the two labels are not interchangeable. See `src/config/taxonomy.yaml`.

### `field_scoring`

Controls the deterministic field-type-aware extraction scorer (`observability/field_scoring.py`). Each field is normalized by its type before comparison: `id`/`date`/`money` are normalized then exact-matched, `name` uses Jaro-Winkler + token-set ratio, `free_text` uses token F1, and `entity_list` uses optimal bipartite matching (Hungarian) with precision/recall/F1. Embedding cosine similarity (sentence-transformers) acts as a second signal for ambiguous name/free-text fields.

| Key                         | Default                                  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| --------------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ambiguous_band`            | `[0.5, 0.85]`                            | Global scores-inside-this-band → escalate to the LLM judge (fallback when no per-type band applies)                                                                                                                                                                                                                                                                                                                                                            |
| `type_bands`                | see YAML                                 | **Per-field-type** judge-escalation bands, calibrated by `scripts/calibrate_field_scoring.py` (issues #4/#5). `date`/`id` are `never` (deterministic score decisive both ways); `money`/`free_text` get calibrated numeric cutoffs; `name`/`entity_list` use `[0.5, 1.0]` (trust only perfect scores, escalate near-misses — Jaro-Winkler/token-set are typo-tolerant by design, so a deterministic reject is unreliable). `always`/`never` are also accepted. **Caveat:** in the pinned scorer (v0.28.1) `score_extraction` calls `field_is_ambiguous` for every scored field, so the per-type bands decide; see [Scoring and performance](../the-pipeline-in-depth/scoring-and-metrics.md). |
| `bipartite_match_threshold` | `0.6`                                    | Minimum pairwise similarity for an entity-list match                                                                                                                                                                                                                                                                                                                                                                                                           |
| `embedding_enabled`         | `true`                                   | Use embedding cosine rescue for ambiguous name/free-text fields                                                                                                                                                                                                                                                                                                                                                                                                |
| `embedding_model`           | `sentence-transformers/all-MiniLM-L6-v2` | Sentence-transformer model for the embedding signal                                                                                                                                                                                                                                                                                                                                                                                                            |
| `embedding_rescue_below`    | `0.7`                                    | Only consult embeddings when the string score is below this                                                                                                                                                                                                                                                                                                                                                                                                    |

```yaml
field_scoring:
  ambiguous_band: [0.5, 0.85]
  type_bands:
    date: never              # exact-after-normalize: decisive both ways
    id: never                # exact match: decisive both ways
    money: [0.675, 0.938]    # numeric tolerance: calibrated cutoff
    free_text: [0.6, 0.95]   # token F1: paraphrases legitimately score 0.6-0.88 — escalate them
    name: [0.5, 1.0]         # trust only perfect matches; near-misses go to judge
    entity_list: [0.5, 1.0]  # trust only perfect lists; partial matches go to judge
  bipartite_match_threshold: 0.6
  embedding_enabled: true
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  embedding_rescue_below: 0.7
```

### `vision`

Controls vision-mode ingestion — rendering PDF/scan pages to image data-URIs for vision-capable models. Vision is **additive**: the full `doc_text` transcription is always sent; page images are appended only when the input agent's model matches one of `vision.models` (substring match). `max_pages` bounds the image budget, never the content.

| Key         | Default | Description                                                                                        |
| ----------- | ------- | -------------------------------------------------------------------------------------------------- |
| `enabled`   | `true`  | Master switch for vision ingestion                                                                 |
| `max_pages` | `10`    | Max PDF pages rendered as images per document (0 = all pages)                                      |
| `dpi`       | `150`   | Render resolution for page images                                                                  |
| `models`    | —       | Model strings (substring match) that accept image input (`qwen/`, `gpt-4o`, `claude`, `gemini`, …) |

```yaml
vision:
  enabled: true
  max_pages: 10
  dpi: 150
  models:
    - "qwen/"
    - "gpt-4o"
    - "gpt-4.1"
    - "claude"
    - "gemini"
    - "llava"
    - "llama-3.2"
    - "qwen-vl"
```

**Environment overrides** (useful for pilot sweeps without editing YAML): `MAILROOM_VISION_ENABLED`, `MAILROOM_VISION_MAX_PAGES`, `MAILROOM_VISION_DPI`.

### `file_extensions`

Accepted file extensions for inbox processing.

```yaml
file_extensions:
  - .txt
  - .pdf
  - .docx
  - .md
  - .jpg
  - .jpeg
  - .png
  - .gif
  - .bmp
  - .webp
  - .tiff
  - .tif
```

### `agents`

Per-agent model and provider configuration. This is where agent-by-agent local model cutover happens.

| Field              | Description                                                                                                       |
| ------------------ | ----------------------------------------------------------------------------------------------------------------- |
| `provider`         | LLM provider: `openrouter`, `ollama`, `vllm`, or `generic`                                                        |
| `model`            | Model name (provider-specific)                                                                                    |
| `temperature`      | LLM temperature (0.0–2.0)                                                                                         |
| `max_tokens`       | Output token cap for the agent (bounds runaway reasoning-token generation)                                        |
| `max_input_chars`  | Input-text budget per call (defaults to 25000); large docs need a bigger window or late-page fields get truncated |
| `reasoning_effort` | OpenRouter reasoning budget for thinking models: `none`, `low`, `medium`, `high`, `max`                           |

```yaml
agents:
  sorter:
    provider: openrouter
    model: qwen/qwen3.7-flash
    temperature: 0.1
    max_tokens: 2048

  contracts_specialist:
    provider: openrouter
    model: qwen/qwen3.7-flash
    temperature: 0.1
    max_tokens: 8192

  # ... (one entry per agent; includes pdf_transcriber, image_extractor and judge)
```

### `llm_retry`

Transient-failure retry for LLM calls (`llm/retry.py`). Retries only connection errors, timeouts, rate limits (429), and 5xx — never 4xx client errors.

| Field                   | Default | Description                                    |
| ----------------------- | ------- | ---------------------------------------------- |
| `max_attempts`          | 5       | Max attempts including the first               |
| `base_delay`            | 1.0     | Initial backoff seconds (doubles per attempt)  |
| `rate_limit_base_delay` | 8.0     | Initial backoff for 429 / rate-limit responses |
| `max_delay`             | 60.0    | Backoff ceiling in seconds                     |
| `jitter`                | 0.3     | Random jitter fraction applied to each delay   |

### `free_quota`

Since llm-mailroom v0.8.1 (2026-10-23). The free-quota circuit breaker ([`llm/quota.py`](https://github.com/Exios66/llm-mailroom/blob/main/src/llm/quota.py)) stops free-model calls while the shared OpenRouter free pool is rate-limited. Without it, each free call uses its full retry ladder before it fails.

```yaml
free_quota:
  trip_after: 3
  cooldown_s: 300
```

| Field | Default | Description |
| ----- | ------- | ----------- |
| `trip_after` | 3 | Consecutive 429 responses from free models before the breaker opens |
| `cooldown_s` | 300 | Seconds that the breaker stays open. The value doubles for each consecutive trip. A positive `Retry-After` from the server is used as given. Either way, the cooldown is capped at 3600 seconds |

* While the breaker is open, free calls raise `FreeQuotaExhausted` and do not use the network. The breaker also raises it when the opening 429 is the last retry attempt, so the caller always sees the breaker and not a bare 429.
* One successful free call closes the breaker and resets the trip count.
* Paid models never use the breaker ([`llm/retry.py`](https://github.com/Exios66/llm-mailroom/blob/main/src/llm/retry.py)).
* The Gmail triage lane answers with its deterministic header pass (`degraded: free_quota`) when the breaker is open. See [Gmail intake](gmail-intake.md#pathway-a-single-document-upload-the-free-triage-lane).

**`models` fallback (since v0.8.1, 2026-10-23).** On an OpenRouter base URL, a free call sends the rest of the `free_model_swarm` chain as the `models` array, with `provider.require_parameters: true`, when the chain has more than one entry. `model` stays the primary, so `models` holds only the fallbacks. OpenRouter then does the fallback on the server. The shipped `free_model_swarm` has one entry (`openrouter/free`), so the array is not sent by default.

**Served models (since v0.8.1, 2026-10-23).** The model that answered (`response.model`) is recorded for each agent as `served_models` in `usage_summary()`, next to the requested `models`. The `llm_response` log event also carries it.

### `pipeline.pdf_direct_chars_per_page`

PDF transcription threshold. Text-based PDFs whose extraction yields at least this many chars/page are transcribed directly without an LLM pass (the dominant latency win); scanned/garbled PDFs still get the LLM reformat.

## Environment Variables

See `.env.example` for the complete list:

| Variable                        | Required                  | Default                                                      | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------------------------- | ------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `OPENROUTER_API_KEY`            | Yes (if using OpenRouter) | —                                                            | OpenRouter API key                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `OPENROUTER_BASE_URL`           | No                        | `https://openrouter.ai/api/v1`                               | OpenRouter base URL                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `DEFAULT_PROVIDER`              | No                        | `openrouter`                                                 | Global provider override                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `OLLAMA_BASE_URL`               | No                        | `http://localhost:11434/v1`                                  | Ollama base URL                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `VLLM_BASE_URL`                 | No                        | `http://localhost:8000/v1`                                   | vLLM base URL                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `VLLM_API_KEY`                  | No                        | —                                                            | Optional bearer token for the vLLM endpoint (keyless local servers work — the client falls back internally)                                                                                                                                                                                                                                                                                                                                                                                        |
| `GENERIC_API_KEY`               | No                        | —                                                            | Generic provider API key                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `GENERIC_BASE_URL`              | No                        | —                                                            | Generic provider base URL                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `DATABASE_URL`                  | No                        | `sqlite+aiosqlite:///<MAILROOM_BASE_DIR>/mailroom.db`        | Async database URL. SQLite by default; set a Postgres URL to switch                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `MAILROOM_BASE_DIR`             | No                        | `./data`                                                     | Pipeline filesystem root (also where SQLite + `warehouse/` Parquet files live)                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `MAILROOM_WAREHOUSE_EXPORT`     | No                        | `auto`                                                       | After `archived`/`failed`, append rows to `data/warehouse/documents_YYYY-MM-DD.parquet` + matching audit file. `auto` = on when pyarrow is installed; `1`/`0` to force. Backfill: `scripts/export_warehouse.py`.                                                                                                                                                                                                                                                                                   |
| `OBSERVABILITY_PROVIDER`        | No                        | `auto`                                                       | Tracing backend: `auto` \| `langfuse` \| `braintrust` \| `phoenix` \| `none`. `auto` = Langfuse if key → Braintrust if key → local Arize Phoenix (cost-free) → `none`                                                                                                                                                                                                                                                                                                                              |
| `OBSERVABILITY_ENVIRONMENT`     | No                        | entrypoint default (`live`/`pilot`/`misc`/`mock`)            | Environment label copied onto every Langfuse observation                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `LANGFUSE_PUBLIC_KEY`           | No                        | `pk-lf-local`                                                | Langfuse public key                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `LANGFUSE_SECRET_KEY`           | No                        | —                                                            | Langfuse secret key (present ⇒ `auto` picks Langfuse)                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `LANGFUSE_HOST`                 | No                        | `http://localhost:3000`                                      | Langfuse server URL (`LANGFUSE_BASE_URL` accepted as alias)                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `LANGFUSE_FLUSH_AT`             | No                        | SDK default `512`                                            | Max queued events before the background exporter sends a batch. Do not set to `1` globally (API stampede). Short-lived jobs still MUST `flush()` before exit                                                                                                                                                                                                                                                                                                                                       |
| `LANGFUSE_FLUSH_INTERVAL`       | No                        | SDK default `5` (seconds)                                    | Max seconds the background exporter waits before sending a batch                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `LANGFUSE_RELEASE`              | No                        | `mailroom@<pkg version>`                                     | Release/version label on every observation                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `LANGFUSE_TIMEOUT`              | No                        | SDK default                                                  | HTTP timeout (seconds) for the Langfuse client                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `LANGFUSE_SAMPLE_RATE`          | No                        | `1.0`                                                        | Trace sampling rate (`0`–`1`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `MAILROOM_TRACE_USER_ID`        | No                        | —                                                            | Optional Langfuse `user_id` propagated onto every `document-pipeline` trace                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `LOG_LEVEL`                     | No                        | `INFO`                                                       | Structured log level (`DEBUG`, `INFO`, `WARNING`, ...)                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `LOG_FORMAT`                    | No                        | `pretty`                                                     | Log renderer: `pretty` (console) or `json` (machine-readable)                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `LOG_FILE`                      | No                        | —                                                            | Optional rotating file sink: every structlog event is appended here as a JSON line (audit item 10.3 — no unbounded log files)                                                                                                                                                                                                                                                                                                                                                                      |
| `LOG_MAX_BYTES`                 | No                        | `10485760`                                                   | Rotation size per log file (10 MB default)                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `LOG_BACKUP_COUNT`              | No                        | `5`                                                          | Rotated log files kept                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `BRAINTRUST_API_KEY`            | No                        | —                                                            | Braintrust API key (present ⇒ `auto` picks Braintrust)                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `BRAINTRUST_PROJECT`            | No                        | `mailroom`                                                   | Braintrust project name                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `PHOENIX_TRACING`               | No                        | `enabled`                                                    | Enable the local Arize Phoenix OTel backend (default fallback in `auto`)                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `PHOENIX_ENDPOINT`              | No                        | `http://localhost:6006/v1/traces`                            | Phoenix OTLP HTTP endpoint                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `PHOENIX_SERVICE_NAME`          | No                        | `mailroom`                                                   | OTel service name                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `PHOENIX_PROJECT`               | No                        | `mailroom`                                                   | Phoenix openinference project name                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `MAILROOM_CHECKPOINTER`         | No                        | `memory`                                                     | LangGraph checkpointer backend: `memory` (MemorySaver default — process-level compiled graph so `interrupt()` HITL can resume in-process; review bin is the durable park, with extract-invoke fallback if the checkpoint is gone) or `sqlite` (on-disk SqliteSaver at `<MAILROOM_BASE_DIR>/checkpoints.db`, for debugging/resume-across-restart experiments)                                                                                                                                       |
| `MAILROOM_JUDGE_VERIFY`         | No                        | `on`                                                         | Kill-switch for the judge-verify exception lane (KANBAN-063): set `off`/`false`/`0`/`no` to skip gated completeness verification entirely. When on, the lane fires on ANY extraction landing in the ambiguous band (`low <= confidence < judge_band_high`, effective default 0.95 from the `confidence:` config, per-class overrides apply) — clean high-confidence extractions cost zero added judge calls. Not ground-truth-gated: it guards extraction confidence, not whether a run is a pilot |
| `MAILROOM_BASE_DIR`             | No                        | `./data`                                                     | Pipeline filesystem root (also where SQLite files live)                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `WATCHER_POLL_INTERVAL_SECONDS` | No                        | `1`                                                          | Inbox rescan interval (seconds)                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `MAILROOM_EMBED_WATCHER`        | No                        | on (off under pytest)                                        | API lifespan starts the inbox watcher. Set `0` when a dedicated `python -m pipeline.watcher` holds `watcher.lock`                                                                                                                                                                                                                                                                                                                                                                                  |
| `MAILROOM_API_TOKEN`            | Off-loopback yes          | —                                                            | Bearer token for every route except `/health`. The-Mailroom `MAILROOM_PIPELINE_TOKEN` must match.                                                                                                                                                                                                                                                                                                                                                                                                  |
| `MAILROOM_API_TOKENS`           | No                        | —                                                            | Additional live bearer tokens as CSV (e.g. `current-key,next-key`) — unioned with `MAILROOM_API_TOKEN` for rotation windows                                                                                                                                                                                                                                                                                                                                                                        |
| `MAILROOM_API_TOKEN_REVOKED`    | No                        | —                                                            | Revoked tokens as CSV; subtracted from the live set so a rotated key stops working immediately                                                                                                                                                                                                                                                                                                                                                                                                     |
| `MAILROOM_MAX_UPLOAD_BYTES`     | No                        | `52428800` (50 MB)                                           | `POST /v1/upload` size cap                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `MAILROOM_UPLOAD_RATE`          | No                        | `20`                                                         | Uploads allowed per 60 s window                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `MAILROOM_API_HOST`             | No                        | `127.0.0.1`                                                  | Bind address. `0.0.0.0` requires a live token. Container/Space images set this.                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `MAILROOM_API_PORT`             | No                        | `8000` (image: `7860`)                                       | Image/local listen port. When the platform injects `PORT` (Hugging Face Space / Fly / Render / Heroku), **`PORT` wins** so the edge proxy can reach the process.                                                                                                                                                                                                                                                                                                                                              |
| `WATCHER_STALE_SECONDS`         | No                        | `15`                                                         | `/health` `checks.watcher` lamp: heartbeat older than this is `stale`                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `OPS_MONITOR_INTERVAL_SECONDS`  | No                        | `300`                                                        | Ops monitor sweep interval                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `MAILROOM_VISION_ENABLED`       | No                        | `true`                                                       | Enable/disable vision ingestion (overrides `vision.enabled` in taxonomy.yaml)                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `MAILROOM_VISION_MAX_PAGES`     | No                        | `10`                                                         | Max PDF pages to render as images (0 = all pages; overrides `vision.max_pages`)                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `MAILROOM_VISION_DPI`           | No                        | `150`                                                        | Render DPI for page images (overrides `vision.dpi`)                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `MAILROOM_PILOT_COST_ABORT`     | No                        | `2.00` (HF pilot) / `0.20` (committed-sample `run_pilot.py`) | Cumulative USD cap; abort the pilot when exceeded                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `MAILROOM_DOCCLASS_PROMPTS`     | No                        | off                                                          | Opt-in KANBAN-090 docclass prompt arm (`1`/`true`/`yes`/`on`). Runtime fetches `mailroom-docclass-<key>` with the in-repo append as fallback; production `mailroom-<agent>` templates are unchanged. `run_hf_pilot.py --docclass` sets this.                                                                                                                                                                                                                                                       |

The-Mailroom (not this process) reads `MAILROOM_PIPELINE_URL`, `MAILROOM_PIPELINE_TOKEN`, and `MAILROOM_PIPELINE_API_PREFIX=/v1`. A Space Observatory must use the public producer Space URL — see [`deploy/space/PAIRING.md`](https://github.com/Exios66/llm-mailroom/tree/main/deploy/space/PAIRING.md).

### Operational and tooling knobs

Read by the code but not in the main table above (verified against llm-mailroom v0.8.0). The rows formerly marked unreleased shipped in llm-mailroom v0.8.1 (2026-10-23).

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `MAILROOM_BERT_DEBUG` | on | Kill switch for the ModernBERT lane's debug capture. `MAILROOM_BERT_INTAKE` stays the gate (off by default). |
| `MAILROOM_TRACE_REDACT` | `0` | Since v0.8.1. `1` drops generation prompt and completion bodies from exported spans. E-mail addresses are always masked. See [Langfuse](deployment/langfuse.md#trace-privacy-prompt-cache-and-score-configs). |
| `MAILROOM_PROMPT_CACHE_TTL` | `60` | Since v0.8.1. Seconds a managed prompt stays cached. A failed fetch is never cached. |
| `MAILROOM_WATCHDOG_POLL_SECONDS` | `20` | How often the watcher watchdog checks the heartbeat. |
| `MAILROOM_WATCHDOG_STALE_SECONDS` | `30` | Heartbeat age after which the watcher counts as stale. |
| `MAILROOM_WATCHDOG_REMIND_MINUTES` | `60` | Reminder cadence while the watcher stays down. Healthy-status emails are never sent. |
| `MAILROOM_STATUS_EMAIL` | maintainer inbox | Recipient of watchdog and watcher status emails. Set it to your own address. |
| `MAILROOM_WATCHER_STATUS` | `1` | `0` disables every status email and the watcher-side heartbeat enrichment (used by hermetic tests). |
| `MAILROOM_PAUSE_TTL_SECONDS` | `3600` | How long the ops-monitor pause file (`ops_monitor_paused`) stays in effect. |
| `MAILROOM_MEMORY_DIR` | `<MAILROOM_BASE_DIR>/memory` | Location of the append-only agent memory JSONL. |
| `MAILROOM_HF_CACHE_DIR` | `<MAILROOM_BASE_DIR>/hf_cache/corpus` | Local cache for the pinned Hub corpus. |
| `MAILROOM_HF_PILOT_DIR` | under the base dir | Output root for HF pilot reports. |
| `MAILROOM_HF_PILOT_GAP_S` | `1.5` (`0` with `--mock`) | Pause between documents in the HF pilot. |
| `MAILROOM_FIELD_SCORING_EMBEDDING` | `0` in the HF pilot | `1` turns on embedding-based clause scoring, which spends OpenRouter quota at corpus scale. Lexical scoring always runs. |
| `MAILROOM_HF_SPACE` | — | Hugging Face Space id used by `publish_space.py`. |
| `MAILROOM_LLM_CACHE` | `1` (on) | Since v0.8.1 (2026-10-23). `0`, `false`, `no` or `off` turns off the triage result cache, for reads and writes. The cache is the SQLite file `<MAILROOM_BASE_DIR>/llm_result_cache.sqlite` ([`llm/result_cache.py`](https://github.com/Exios66/llm-mailroom/blob/main/src/llm/result_cache.py)). Entries expire after 30 days. It applies to the Gmail triage agent only. See [Gmail intake](gmail-intake.md#pathway-a-single-document-upload-the-free-triage-lane) |

### Gmail intake channel (HUB-037)

> The variables formerly marked "Unreleased on `main`" shipped in llm-mailroom v0.8.1 (2026-10-23).

The agent mailbox (`llmmailroom@gmail.com`) is a second intake route: an IMAP poller (running inside the watcher process) drops accepted attachments into the SAME inbox the watcher drains. The full operator guide — subject-line contract, upload best practices, every pathway a document takes from Gmail into the pipeline (free single-document triage lane, capability handoff, multi-document full pipeline), completion echoes, and troubleshooting — is [`docs/gmail-intake.md`](gmail-intake.md).

| Variable                           | Required              | Default                                | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ---------------------------------- | --------------------- | -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `MAILROOM_GMAIL_ENABLED`           | No                    | off                                    | Gmail intake channel (HUB-037): poll the agent mailbox and drop accepted attachments into the inbox. Explicit opt-in (`1`/`true`/`yes`/`on`); needs `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD`. Runs inside the watcher; `/health` reports `checks.gmail_intake`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `GMAIL_ADDRESS`                    | Yes (when channel on) | —                                      | Mailbox address (e.g. `llmmailroom@gmail.com`). Secret — `.env` only                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `GMAIL_APP_PASSWORD`               | Yes (when channel on) | —                                      | Gmail 2FA app password (16 chars; display spaces tolerated/stripped). Secret — `.env` only                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `MAILROOM_GMAIL_IMAP_HOST`         | No                    | `imap.gmail.com`                       | IMAP SSL host                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `MAILROOM_GMAIL_IMAP_PORT`         | No                    | `993`                                  | IMAP SSL port                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `MAILROOM_GMAIL_FOLDER`            | No                    | `INBOX`                                | Mailbox folder polled                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `MAILROOM_GMAIL_POLL_SECONDS`      | No                    | `60`                                   | Seconds between sweeps                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `MAILROOM_GMAIL_DEFAULT_MATTER_ID` | No                    | `DEFAULT`                              | Matter used when the subject has no `[M:<matter_id>]` tag                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `MAILROOM_GMAIL_MAX_ATTACHMENT_MB` | No                    | `50`                                   | Per-attachment size cap (larger attachments are skipped, message still marked seen)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `MAILROOM_GMAIL_ALLOWED_SENDERS` | No | — | CSV allowlist of sender addresses. Exact, case-insensitive match on the bare address; `+tag` variants do not match. Empty = accept all |
| `MAILROOM_GMAIL_REQUIRE_DMARC` | No | `1` | Since v0.8.1. An allowlisted sender also needs Gmail's `dmarc=pass` verdict (topmost `Authentication-Results` from `mx.google.com` only; otherwise fail closed). A sender whose domain publishes no DMARC record is rejected while this is on |
| `MAILROOM_GMAIL_MAX_ATTEMPTS` | No | `3` | Since v0.8.1. Failed sweeps before a message that keeps raising is quarantined: marked `\Seen`, labelled `mailroom/failed` |
| `MAILROOM_GMAIL_MAX_REPLIES_PER_HOUR` | No | `20` | Since v0.8.1. Cap on reject, acknowledgment and digest replies to any one address. Completion echoes are not capped |
| `MAILROOM_GMAIL_ACKS` | No | `1` | Since v0.8.1. Acknowledgment reply when the poller queues the attachments of an email |
| `MAILROOM_GMAIL_IDLE` | No | `0` | Since v0.8.1. Opt-in IMAP IDLE push between sweeps. Falls back to polling on any IDLE error |
| `MAILROOM_GMAIL_ALLOW_SELF` | No | `0` | Since v0.8.1. Process mail from the agent's own address. The agent's own replies stay excluded by their `Auto-Submitted` header |
| `MAILROOM_GMAIL_REACTIONS`         | No                    | `1`                                    | When the watcher claims a Gmail-channel attachment, react to the source email with the check emoji (a Gmail label via IMAP `X-GM-LABELS`) — the "picked up for processing" ack. Best-effort: a reaction failure never disturbs the claim. Set `0` to disable                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `MAILROOM_GMAIL_REACTION_LABEL`    | No                    | `✅`                                    | The emoji-named Gmail label applied as the reaction (auto-created best-effort)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `MAILROOM_GMAIL_ECHOES`            | No                    | `1` (with channel on)                  | When a Gmail-intake document reaches a terminal stage (archived/review/failed), reply on the source email thread with the completion report: status, classification, extraction, archive entry (path + sha256) and the verified audit chain                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `MAILROOM_GMAIL_TRIAGE`            | No                    | `1` (with channel on)                  | Single-document triage lane (HUB-037): an email carrying exactly ONE accepted attachment is handled by the FREE OpenRouter lane — the Free Models Router (`openrouter/free`, auto-selects the best free model per request) — core pipeline steps (deterministic prep, triage classification, auditable-hash archive with its own `triage_*` audit section, completion echo) without the paid agents, after a deterministic capability pre-check. Documents beyond the free team's reach (image-only, scanned PDFs, or longer than the free `max_input_chars` budget — merger agreements typically exceed it) are HONESTLY handed off to the full paid pipeline (`intake.triage_handoff` records the reason). Emails with 2+ accepted attachments drop the triage approach and run the FULL paid pipeline. Advisory; fails soft; set `0` to disable the lane (single-doc emails then take the full pipeline) |
| `MAILROOM_LLM_INTAKE`              | No                    | `1`                                    | LLM-assisted intake pass (HUB-038): the intake agent (`agents/intake.py`) adds a fused TRIAGE (advisory read → manifest `intake.triage` + sorter prior), CLEAN (structural repair of messy text, re-normalized deterministically), and PREPARE (section map) pass on top of the deterministic clerk. **No-truncation doctrine:** documents are never truncated — over-budget documents are processed in overlapping sliding windows and merged. The LLM pass fires ONLY for messy or over-sorter-budget documents (clean short docs pay zero); set `0` to disable (fully deterministic intake)                                                                                                                                                                                                                                                                                                              |
| `MAILROOM_GMAIL_SMTP_HOST`         | No                    | `smtp.gmail.com`                       | SMTP host for the echo replies (same app password)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `MAILROOM_GMAIL_SMTP_PORT`         | No                    | `465`                                  | SMTP SSL port for the echo replies                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `MAILROOM_RELATIONS`               | No                    | `1`                                    | Relations layer (HUB-040) master kill-switch (also `relations.enabled` in taxonomy): the post-archive association pass + background archive sweep + the own hash-chained relations ledger                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `MAILROOM_RELATIONS_SCAN_SECONDS`  | No                    | `300`                                  | Seconds between background archive sweeps (watermark-incremental — never rescans known documents)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `MAILROOM_RELATIONS_CONTEXT`       | No                    | `1`                                    | Advisory RELATED context block for the sorter/specialist handoff + the Gmail completion echo (from the relations ledger)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `MAILROOM_RELATIONS_LLM`           | No                    | `1` (and `relations.llm` off in pilot) | LLM judgment pass over ambiguous relation candidates — taxonomy `relations.llm: false` keeps the pilot deterministic-only                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `MAILROOM_RELATIONS_EMBEDDINGS`    | No                    | `1`                                    | Embedding cosine signal (dojo sentence-transformers / remote fallback; HUB-040 hang-proofing: 90s bounded load). `0` skips the cosine signal only — the other signals flow                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `MAILROOM_LLM_FREE_ONLY`           | No                    | off                                    | Free-only pilot guardrail (HUB-039): when on (`1`/`true`/`yes`/`on`), `get_llm` refuses to resolve any **OpenRouter** model that is not free — `cost_models` prices both 0.0, or unregistered with an OpenRouter `:free` suffix; self-hosted providers (`vllm`/`ollama`/`generic`) are exempt — there is no per-token price to bound (DMR-052). A paid-model resolution raises BEFORE any client exists, so documents fail-soft park instead of spending; the free triage lane is unaffected. Unset/`0` in full production, where paid agents handle multi-document emails and inbox/CLI uploads                                                                                                                                                                                                                                                                                                            |

#### Emailing the mailroom (Gmail intake format contract)

There is **no subject keyword to trigger pickup** — every email arriving at the mailbox is swept automatically (every `MAILROOM_GMAIL_POLL_SECONDS`, default 60). `RE:` / `FWD:` prefixes are irrelevant. The format rules that DO matter:

| Rule                          | Detail                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Attach the document**       | Only attachments are processed — the email body is never read. Body-only emails are marked seen and skipped (logged as `gmail_message_no_processable_attachments`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| **Accepted extensions**       | `file_extensions` in `config/taxonomy.yaml`: `.pdf`, `.txt`, `.docx`, `.md`, `.jpg`, `.jpeg`, `.png`, `.gif` (anything else is skipped, message still acknowledged)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| **Size**                      | ≤ `MAILROOM_GMAIL_MAX_ATTACHMENT_MB` (default 50 MB) per attachment                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| **Sender**                    | Any mailbox can send unless `MAILROOM_GMAIL_ALLOWED_SENDERS` is set (exact, case-insensitive bare address). Since v0.8.1: an allowlisted sender also needs Gmail's `dmarc=pass` verdict (`MAILROOM_GMAIL_REQUIRE_DMARC`), and auto-replies, bounces and list mail are skipped without a reply |
| **Replies**                   | Since v0.8.1: the sender gets an acknowledgment when the poller queues the attachments, a reject reply for each refused file, the completion echo for a single document, or one digest for a multi-document email. All replies go through the durable `mail_outbox.sqlite` outbox. See [Gmail intake](gmail-intake.md) |
| **Matter routing (optional)** | Put `[M:<matter_id>]` in the subject — e.g. `Hail damage FNOL [M:MORNINGSTAR-001]`. Allowed chars: `A-Z a-z 0-9 _ . -` (≤64). Without the tag the document files under `MAILROOM_GMAIL_DEFAULT_MATTER_ID` (default `DEFAULT`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **Single vs bundle routing**  | ONE accepted attachment = a **single-document upload**: handled by the FREE OpenRouter triage team (core pipeline steps — deterministic prep, triage classification, auditable-hash archive with its own `triage_*` audit section, completion echo — no paid agents), after a capability pre-check; documents beyond the free models' reach (image-only, scanned PDFs, or longer than the free input budget, e.g. most merger agreements) are **honestly handed off to the full paid pipeline** (`intake.triage_handoff` records the reason). TWO OR MORE accepted attachments = a **multi-document upload**: the triage approach is dropped and every attachment runs the **full paid pipeline** |
| **Multiple attachments**      | Each accepted attachment becomes its own document under the same matter; one email per document is cleanest for traceability                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

Worked example:

```
To:      llmmailroom@gmail.com
Subject: Hail damage FNOL [M:MORNINGSTAR-001]
Attach:  claim_2026-03-14.pdf
```

What you get back: the ✅ label appears on the email the moment the watcher claims the attachment for processing (the intake acknowledgement). A **single-document email** is then handled entirely by the free-triage lane: the triage read (primary class, subclass, confidence, gist, keywords) becomes the terminal manifest's `intake.triage`, the document is archived in the auditable hash archive with its own `triage_*` audit entries, and the mailroom replies on the thread with a completion report carrying the **INTAKE TRIAGE (pre-pipeline)** section — no paid pipeline agents are invoked — UNLESS the deterministic capability pre-check rejects the document (longer than the free model's input budget, image-only, or a scanned PDF): it is then honestly handed off to the full paid pipeline, with `intake.triage_handoff` recording the reason and the completion report noting "triage handoff: … — handled by the full pipeline". A **multi-document email** drops the triage approach: every attachment flows inbox → classify → extract → archive/review like any upload, with `intake.source: gmail` + `intake.route: pipeline` + the sender/subject recorded on the manifest for audit. Terminal-stage pipeline documents get the completion report on the same thread — STATUS, doc\_id/ matter, classification + confidence, the extraction report, the archive entry (path + sha256 for archived documents, or the failure/review reason), and the full audit trail with the hash-chain verification verdict — so the email thread itself is the notification surface.

## Provider Configuration

> **Scope (mailroom-issues directive 2026-09-14):** the default and primary provider is **OpenRouter**. **vLLM and Modal are used only for local deployments** — the `local-mailroom-sandbox` and self-hosted/local-model serving — and are never the default for production runs. In particular, **Gmail triage has no vLLM implementation**: the triage lane resolves through `openrouter/free`. vLLM/Modal engage only when an operator explicitly selects a local sandbox profile (`DEFAULT_PROVIDER=vllm` + `VLLM_BASE_URL` in the sandbox config).

### OpenRouter (Primary)

```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
DEFAULT_PROVIDER=openrouter
```

### Ollama (Local)

```bash
# Start Ollama + pull a model
docker compose -f src/config/docker/docker-compose.yml --profile local-llm up -d ollama
docker exec mailroom-ollama ollama pull qwen3:7b

# Configure
DEFAULT_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
```

### vLLM (Local)

```
DEFAULT_PROVIDER=vllm
VLLM_BASE_URL=http://localhost:8000/v1
```

With `DEFAULT_PROVIDER=vllm`, `taxonomy.yaml: vllm_model_map` rewrites champion slugs to the served HF ids; a missing `VLLM_BASE_URL` warns and falls back to localhost. `VLLM_API_KEY` is sent as an optional bearer (the Modal deploy app enforces one). A `503` from a `*.modal.run` endpoint is a scale-to-zero cold start — `retry_chat_completion` uses a long bounded backoff (90s base / 240s cap, DMR-052). Deploy and cutover: [Modal + vLLM](deployment/modal-vllm.md). Host compose that talks to those GPUs: [Docker deployment](deployment/docker-deployment.md).

### Generic OpenAI-Compatible

```
DEFAULT_PROVIDER=generic
GENERIC_BASE_URL=https://your-endpoint.com/v1
GENERIC_API_KEY=your-key
```

## Agent-by-Agent Cutover

To move individual agents to a different provider/model, edit `config/taxonomy.yaml`:

```yaml
# Before (OpenRouter):
agents:
  sorter:
    provider: openrouter
    model: openai/gpt-4o

# After (local Ollama):
agents:
  sorter:
    provider: ollama
    model: qwen3:7b
```

Or use the cutover utility:

```bash
PYTHONPATH=src python src/scripts/cutover.py --agent sorter --provider ollama --model qwen3:7b
PYTHONPATH=src python src/scripts/cutover.py --validate --agent sorter
```

See [Local Models](local-models.md) for the full cutover guide.

## Environment variables

The committed template [`.env.example`](https://github.com/Exios66/llm-mailroom/tree/main/.env.example) is the authoritative knob list (copy to `.env` at the repo root). The full per-provider / per-trace-sink configuration guide — covering THIS repo and llm-entity-extraction together, including the Modal-vLLM flip and the shared cross-repo contract — lives in the sibling repo: [`docs/configuration.md`](https://github.com/Exios66/llm-entity-extraction/blob/main/docs/configuration.md).

Quick orientation:

| Group          | Knobs                                                                                                                                                      |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LLM provider   | `DEFAULT_PROVIDER`, `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OLLAMA_BASE_URL`, `VLLM_BASE_URL`, `VLLM_API_KEY`, `GENERIC_API_KEY`, `GENERIC_BASE_URL` |
| Trace sinks    | `OBSERVABILITY_PROVIDER`, `OBSERVABILITY_ENVIRONMENT`, `LANGFUSE_*`, `BRAINTRUST_*`, `PHOENIX_*`                                                           |
| Pipeline & API | `MAILROOM_*`, `WATCHER_*`, `OPS_MONITOR_INTERVAL_SECONDS`, `DATABASE_URL`                                                                                  |
| Logging        | `LOG_LEVEL`, `LOG_FORMAT`, `LOG_FILE`, `LOG_MAX_BYTES`, `LOG_BACKUP_COUNT`                                                                                 |
| LegalBench     | `LEGALBENCH_EXPERIMENT_LOG`, `LEGALBENCH_SIBLING_REPO`                                                                                                     |
