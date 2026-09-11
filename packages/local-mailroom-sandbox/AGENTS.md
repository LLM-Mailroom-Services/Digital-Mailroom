# AGENTS.md

Local-mailroom-sandbox: a **local-first experiment harness** around the governed
LLM-Mailroom family. It does **not** reimplement the 13-node LangGraph pipeline.
The family code the sandbox imports at runtime — the pipeline
([`llm-mailroom`](https://github.com/Exios66/llm-mailroom) `v0.6.0`:
`pipeline.*`/`graph.*`/`agents.*`/`llm.*`/`legalbench.*`) and scoring
([`llm-dojo-scoring`](https://github.com/Exios66/llm-dojo-scoring) `v0.12.2`) —
ships as **tracked snapshots under `vendor/`** (DMR-057). The sandbox is
**self-contained**: no pip git pins, no `sandbox fetch-deps` step, no network
needed to score or run evals. Prompt loops optionally in `llm-entity-extraction`.

Python 3.11+, no build step.

## Skills (tool selection)

Committed under `.cursor/skills/`. **Read `sandbox-tool-router` first** for any
provider, tracing, dataset, or deploy task, then open exactly one specialty skill.

| Skill | Appropriate for |
| --- | --- |
| `sandbox-tool-router` | Choosing among the stacks below |
| `ollama` | Default local LLM (prefer over OpenRouter/Modal) |
| `modal` | Remote GPU vLLM (`sandbox-vllm`) |
| `langfuse` | Default tracing + The-Mailroom (Langfuse 3 / SDK v4) |
| `apache-phoenix` | Optional Arize Phoenix OTEL sidecar only |
| `braintrust` | Opt-in hosted Braintrust (never default offline) |
| `huggingface` | Hub pulls / weights; offline fixtures first |

Do not use Phoenix or Braintrust as the The-Mailroom sink. Do not use OpenRouter
unless explicitly opted in.

## Commands

```bash
pip install -e ".[dev]"
cp config/.env.example .env
sandbox profiles
sandbox agents list
sandbox cutover --profile ollama --agent-model judge=qwen3:14b
sandbox up                          # langfuse + ollama compose profiles
sandbox pull-models                 # ollama pull qwen3:8b
sandbox health
sandbox fetch-deps                  # optional: refresh tracked vendor snapshots (llm-mailroom v0.6.0, llm-dojo-scoring v0.12.2)
sandbox fetch-deps --visualizer     # also clone The-Mailroom
sandbox pilot --mock                # no LLM
sandbox eval sorter --mock
sandbox eval judge --mock
sandbox eval pipeline --mock        # connected graph scores
sandbox eval local_vs_api --mock    # Ollama vs OpenRouter serving (no API key)
sandbox matrix --providers ollama --models qwen3:8b --prompts sorter_local_v0 --mock --dry-run
pytest -v                           # network-free; live LLM tests need SANDBOX_LOCAL_LLM=1
sandbox datasets pull               # LIVE pinned Hub pull → data/cache/ (network; exit 1 on failure)
sandbox datasets prepare            # offline JSONL under data/runtime/prepared/
sandbox up --compose-profile jupyter  # Lab on :8888 (deploy/Dockerfile)
sandbox tunnel plan|up|status|down    # SSH forward for vllm-remote (HUB-026)
modal run deploy/modal_vllm.py::download_model  # Modal: pre-warm HF cache ([deploy])
modal deploy deploy/modal_job.py  # Modal job worker (remote runs)
sandbox run preflight|start|status|resume|cancel|list --config config/runs/<name>.yaml [--job-mode endpoint|modal] [--watch]
sandbox prompts list|show <agent>     # all pipeline agent prompts (local + Langfuse)
sandbox metrics compare --runs local,modal,api   # serving metrics comparison
# SANDBOX_DEBUG=1 → set -x + results/run.log diagnostics (CHTC/Modal, DMR-053)
```

- Config: `config/profiles/*.yaml` + `config/taxonomy.overlay.yaml` + `config/components.yaml` + `config/models.yaml`.
- Remote serving (Modal / SSH-tunneled vLLM / CHTC / conda): `docs/remote-serving.md` + `deploy/htcondor/` + `deploy/conda/`. Modal deploy workflow (SDK pinned `modal==1.5.5`; pre-warm → deploy → verify → teardown, cost guards, troubleshooting) lives in `deploy/README.md`. CLI rule: pass `--profile` AFTER the subcommand (or via `SANDBOX_PROFILE`) — a `--profile` before the subcommand is clobbered by the subparser default.
- Runtime taxonomy is written to `data/runtime/taxonomy.yaml` (gitignored).
- Prepared fixtures: `data/runtime/prepared/` via notebooks or `sandbox datasets prepare`.
- Experiment log: `reports/experiment_log.jsonl` (sandbox-local, not a sister-repo mirror).
- Tracing default: Langfuse 3 / SDK v4 (`OBSERVABILITY_PROVIDER=langfuse`). Phoenix is an optional sidecar. OpenRouter is opt-in.
- Docker: `deploy/Dockerfile` + Compose profiles including `jupyter` — see `docs/docker-offline.md`.
- Agent skills: `.cursor/skills/` (router + Langfuse / Braintrust / Phoenix / Ollama / Modal / Hugging Face).

## Reduced agent profile (HUB-015)

- The **reporter agent is retired** in this sandbox: `components.yaml` lists it
  under `retired_agents`, and the compile stage is the **computational
  procedural reporter** — the graph's `compile_report` node backed by
  llm-mailroom v0.6.0's `compile_matter_record` (deterministic, **no LLM
  call**; the sandbox eval never acquires an LLM client for it).
- **Reviewers stay enabled** (`sorter_reviewer` + its `sorter_reviewer_local_v0`
  prompt) — the reduced profile removes the reporter, not the reviewers.
- HF fixture targets (`data/fixtures/hf/docclass_mini.jsonl`) carry the full
  mailroom-corpus ground-truth schema: per-doc-type `expected_subclass`
  (corpus strata vocabulary) + `expected_fields` (27-key GT schema subset:
  intent + provenance, sentiment, claims/entity fields) propagated into every
  eval row.

## Architecture gotchas

- Activate **before** importing mailroom graph/agents: `mailroom_sandbox.runtime.activate(profile)`.
- The vendored family trees are put on `sys.path` at package import (`mailroom_sandbox/__init__.py`) — a fresh checkout works offline, no `fetch-deps`. `MAILROOM_SRC` / `DOJO_SRC` env vars still override for refresh workflows.
- Mailroom's `pipeline.config.CONFIG_PATH` is hardcoded; the sandbox monkeypatches it.
- `DEFAULT_PROVIDER` alone is not enough — OpenRouter model ids must be rewritten via the overlay.
- `--model` overrides every agent; `--agent-model NAME=tag` is surgical and wins last.
- Scoring + pipeline are pinned by the tracked snapshots: `vendor/llm-mailroom/VENDOR.md` (v0.6.0, commit `3cf9fb92`) + `vendor/llm-dojo-scoring/VENDOR.md` (v0.12.2, commit `6dab61bd`); refresh both with `sandbox fetch-deps` and commit the diff. `get_suite("local_vs_api")` compares offline vs API-key serving metrics (table + scorecard + cost; TTFT never inferred; GPU/KV stripped on API records).
- Isolated evals call vendored agent classes (always importable now); the `offline_fallback` path still exists for missing deps.
- `scripts/` and `legalbench/` are not in the installed `mailroom` wheel — they ARE in the vendored tree, which also supplies `PYTHONPATH` for `sandbox pipeline watcher` / `sandbox pipeline api` (`_mailroom_env` adds both vendored srcs).
- No second kanban board in this repo. Cross-family work stays on llm-entity-extraction's MESSAGE_BOARD.

## Tests

No real LLM calls in the default suite. `@pytest.mark.local_llm` is skipped unless `SANDBOX_LOCAL_LLM=1`.
