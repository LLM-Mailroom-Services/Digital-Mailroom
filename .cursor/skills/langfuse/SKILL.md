---
name: langfuse
description: Configure and use Langfuse 3 (SDK v4) as the default tracing sink for local-mailroom-sandbox and The-Mailroom. Use when setting OBSERVABILITY_PROVIDER, debugging document-pipeline traces, compose langfuse, Langfuse keys, score names, or session/tags for family evals.
---

# Langfuse (default tracing)

**When:** Any sandbox tracing, The-Mailroom visualization, `document-pipeline` spans, or `OBSERVABILITY_PROVIDER=langfuse|auto` with keys set.  
**Prefer over:** Apache Phoenix (optional sidecar only) and Braintrust (opt-in hosted) for the governed mailroom conveyor.

## Contract

| Knob | Value |
| --- | --- |
| Stack | Langfuse **3** (web + worker) |
| SDK | Python **v4** data model |
| UI | `http://localhost:3000` |
| Keys | `pk-lf-sandbox` / `sk-lf-sandbox` (headless init) |
| Root trace | `document-pipeline` (`chain`) |
| Tags | `mailroom`, env (`mock`/`pilot`), `sandbox`, profile, `mock`/`local` |

Env (from `config/.env.example`):

```bash
OBSERVABILITY_PROVIDER=langfuse
OBSERVABILITY_ENVIRONMENT=pilot   # mock when SANDBOX_RUN_MODE=mock
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-sandbox
LANGFUSE_SECRET_KEY=sk-lf-sandbox
```

## Start / verify

```bash
sandbox up                         # ollama profile → langfuse + ollama
sandbox health                     # probes provider + Langfuse health
sandbox traces export              # data/traces/export.json
```

Compose services: `postgres`, `clickhouse`, `redis`, `minio`, `langfuse-web`, `langfuse-worker` under profile `langfuse`.

Inside the Jupyter container use `LANGFUSE_HOST=http://langfuse-web:3000`.

## Family rules (do not break)

1. One document / isolated eval → one root `document-pipeline` chain.  
2. Child names stay verb-first from dojo/mailroom `NODE_OBSERVATION_TYPES`.  
3. Public ground truth keys only: `expected_hf_class`, `expected_doc_class`, `expected_subclass`, `expected`.  
4. Score names use dojo aliases (e.g. `extraction_overall_verified_precision` → `extraction_verified_precision`).  
5. Implementation: `mailroom_sandbox.eval.tracing` (prefers vendored mailroom setup, else SDK, else no-op).

## The-Mailroom

```bash
sandbox fetch-deps --visualizer
# MAILROOM_TRACE_NAMES=document-pipeline
# MAILROOM_TRACE_TAGS=mailroom
# MAILROOM_TRACE_ENVIRONMENTS=mock,pilot
```

The-Mailroom **cannot** plot Phoenix spans — keep Langfuse as the sink when the visualizer matters.

## Docs

- `docs/tracing.md`  
- `deploy/README.md`  
- Sister skill: [sandbox-tool-router](../sandbox-tool-router/SKILL.md)
