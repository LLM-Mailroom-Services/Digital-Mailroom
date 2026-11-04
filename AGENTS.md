# AGENTS.md

Local-mailroom-sandbox: a **local-first experiment harness** around the governed
LLM-Mailroom family. It does **not** reimplement the 13-node LangGraph pipeline.
The family code the sandbox imports at runtime — the pipeline
([`llm-mailroom`](https://github.com/Exios66/llm-mailroom):
`pipeline.*`/`graph.*`/`agents.*`/`llm.*`/`legalbench.*`) and scoring
([`llm-dojo-scoring`](https://github.com/Exios66/llm-dojo-scoring)) —
ships as **tracked snapshots under `vendor/`** (DMR-057). Both snapshots
consume reviewed standalone source revisions: refresh from monorepo workspace
packages when available, otherwise from the standalone commit/release refs frozen to
SHAs in `_VENDOR_PINS` (`src/mailroom_sandbox/cli.py`). The standalone refresh
rejects moved refs before replacing tracked vendor files. The drift guard
(`tests/test_vendor_drift.py`) enforces byte-identity with available source
packages; `python scripts/sync_vendor.py` refreshes from the monorepo root
(DMR-070). The docclass-era compliance files are intentionally absent from
the vendored llm-mailroom tree (retired agent, 59c47401). The sandbox is
**self-contained**: no pip git pins, no `sandbox fetch-deps` step, no network
needed to score or run evals. Prompt loops run through the vendored `llm-mailroom`.

Python 3.11+, no build step.

**Source ownership:** `Exios66/local-mailroom-sandbox` owns this package.
Commit sandbox fixes here first, then import them into Digital-Mailroom.
Do not export hub package edits back into standalone repositories. Dojo owns
all scoring engine logic; llm-mailroom owns the pipeline. This sandbox owns
the offline/local and Modal/vLLM GPU execution and testing environment.
The-Mailroom is their shared visualizer. Vendor snapshots consume reviewed,
committed standalone source revisions; the hub refresh mirrors packages only
after those sources have been imported. Preserve live corporate v6 and sandbox
evaluation v7 independently. The historical sandbox v0.2.0 release exists;
current development version and immutable vendor pins are separate facts.

## Skills (tool selection)

Committed under `.cursor/skills/`. **Read `sandbox-tool-router` first** for any
provider, tracing, dataset, or deploy task, then open exactly one specialty skill.

| Skill | Appropriate for |
| --- | --- |
| `sandbox-tool-router` | Choosing among the stacks below |
| `modal` | **Default** serving: Modal vLLM (`modal-vllm`, `sandbox runbook show serve`) |
| `ollama` | Offline/CPU fallback (`--profile ollama`); not the default |
| `langfuse` | Default tracing + The-Mailroom (Langfuse 3 / SDK v4) |
| `apache-phoenix` | Optional Arize Phoenix OTEL sidecar only |
| `braintrust` | Opt-in hosted Braintrust (never default offline) |
| `huggingface` | Hub pulls / weights; offline fixtures first |

Do not use Phoenix or Braintrust as the The-Mailroom sink. Do not use OpenRouter
unless explicitly opted in.

## Coding subagents (Cursor + OpenCode)

Family-wide roster under `config/subagents/family-roster.yaml` with canonical
prompts in `.opencode/agents/`. Harness adapters sync OpenCode frontmatter and
Cursor stubs (`sandbox subagents sync --harness all`). Materialize into sibling checkouts on **Digital-Mailroom** with
`sandbox subagents propagate` or `materialize --package <id> --root <path>`
([`docs/subagents-family-sync.md`](docs/subagents-family-sync.md)).
Meta agents: **`harness-doctor`** and **`adversarial-reviewer`**. See
[`config/subagents/README.md`](config/subagents/README.md). Harness health:
`sandbox subagents doctor` (add `--also-root ~/path/to/eval-environment` for
sibling checkouts). Durable eve doctor:
`~/Downloads/agent-harness-doctor` (`npm exec -- eve dev`, Node >= 24).

## Commands

```bash
pip install -e ".[dev]"
# or: pip install -r requirements.txt   # → requirements/dev.txt (mirrors pyproject)
# .venv/bin/sandbox puts its own venv's bin first on PATH, so its pinned `modal` is used even when the venv is not activated
# specialist / Modal live path also needs:
#   pip install -e ".[pipeline,deploy,observability]"   # observability = the Langfuse SDK; without it runs record no traces
#   # or: pip install -r requirements/pipeline.txt -r requirements/deploy.txt -r requirements/observability.txt
cp config/.env.example .env
sandbox profiles
sandbox agents list
sandbox runbook show serve          # DEFAULT: Modal vLLM deploy → point → verify → teardown
sandbox cutover --profile modal-vllm
sandbox up                          # langfuse only (the Modal endpoint is external)
sandbox pull-models --profile ollama  # offline fallback: ollama pull qwen3:8b (on modal-vllm it only prints the prewarm command)
sandbox health                      # probes the deployed modal-vllm endpoint
sandbox fetch-deps                  # optional: refresh vendor snapshots (workspace packages first; SHA-frozen standalone commit/release refs otherwise)
sandbox fetch-deps --visualizer     # also clone The-Mailroom
sandbox pilot --mock                # no LLM
sandbox eval specialist [TARGET] --mock   # primary: all five specialists, or one (contract, merger_agreement, …)
sandbox eval pipeline [--class C] --mock  # primary: full connected graph, every class or one
sandbox eval --all-tasks            # other tasks (sorter, judge, …) still run; hidden from menus
sandbox eval local_vs_api --mock    # Ollama vs OpenRouter serving (no API key)
sandbox matrix --providers ollama --models qwen3:8b --prompts sorter_local_v0 --mock --dry-run
pytest -v                           # network-free; live LLM tests need SANDBOX_LOCAL_LLM=1
sandbox datasets pull               # LIVE pinned FULL Hub pull (train+test, 3302 rows) → data/cache/
sandbox datasets sample --per-class 40  # offline 40/class draw from that cache (20/40/100…)
sandbox datasets prepare            # offline JSONL under data/runtime/prepared/
sandbox up --compose-profile jupyter  # Lab on :8888 (deploy/Dockerfile)
sandbox tunnel plan|up|status|down    # SSH forward for vllm-remote (HUB-026)
modal run deploy/modal_vllm.py::download_model  # Modal: pre-warm HF cache ([deploy])
modal deploy deploy/modal_job.py  # Modal job worker (remote runs)
sandbox watch [--web] [--config config/runs/<name>.yaml|--follow <current-file>]  # terminal TUI or localhost browser UI (SSE); docs/pretty-logging/mailroom-themed-logging.md
sandbox run preflight|start|status|resume|cancel|list --config config/runs/<name>.yaml [--job-mode endpoint|modal] [--watch] [--initials JB]
sandbox runbook list|show <id>|check|write   # operator runbooks (catalog → docs/runbooks/)
sandbox prompts list|show <agent>     # all pipeline agent prompts (local + Langfuse)
sandbox subagents list|show <id>      # coding subagent roster (GEPA, traces, meta)
sandbox subagents sync --harness all  # OpenCode frontmatter + .cursor/agents/ stubs
sandbox subagents propagate              # materialize + sync all mapped family checkouts
sandbox subagents materialize --package digital-mailroom --root <path>  # monorepo hub export
sandbox metrics compare --runs local,modal,api   # serving metrics comparison
sandbox modal deploy|prewarm|status|logs|stop|url|raw|publish-image   # guarded Modal CLI passthrough (--dry-run on deploy/prewarm/stop/logs/publish-image; stop is idempotent + verified)
sandbox modal publish-image [--tag TAG]   # publish the vLLM image to the active workspace; `sandbox modal deploy --named-image` then reuses it
sandbox modal status                  # lists sandbox-vllm, sandbox-job and every other sandbox-* app that is not stopped (not sandbox-image-builds); containers shown for deployed apps
sandbox vllm probe|command|serve|metrics   # endpoint probe (models/chat//health//metrics), `vllm serve` argv, local serve, metrics scrape
sandbox experiment designs|create|review|preflight|launch|watch|report  # guided designs + initials-gated spend; docs/experiments.md
python scripts/smoke_campaign.py      # offline pre-flight: specialist, sand42 and pipeline mock campaigns must reach a 1.0 extraction headline (needs `sandbox datasets pull` once)
sandbox doctor [--service NAME] [--live] [--publish] [--json]   # one status table for every external CLI/service (offline by default); --publish feeds the board's services strip; --live adds the active Modal account's app listing (read-only, deploys nothing)
sandbox hf whoami|download|cache|raw   # guarded hf CLI passthrough (pinned dataset revision; --sandbox-cache = data/cache/hf)
sandbox watch --web                   # mailroom pretty-logs TUI in the browser (http://127.0.0.1:8765/, SSE); full command matrix in docs/pretty-logging/mailroom-themed-logging.md
sandbox dev                           # dev server: same themed UI on a synthetic looping run (no Modal/spend)
scripts/mailroom-tui dev|web|score <run>   # launcher; .claude/launch.json → mailroom-watch-dev / -live
sandbox board [--tui] [--demo] [--interval SECS] [--probe-interval SECS]  # persistent job board: every mailroom.beacon/v1 job (~/.mailroom/jobs), browser :8767 or terminal; refresh floor 0.1 s
sandbox beacon update --job ID --package P --done N --total M   # shell jobs publish to the board
# long Python jobs: `with Beacon(job_id, package=...) as b: b.update(done=i, total=n)` (mailroom_sandbox/tui/beacon.py — vendorable single file)
# keep the board up across reboots: deploy/launchd/com.mailroom.board.plist (install steps in the file)
# SANDBOX_DEBUG=1 → set -x + results/run.log diagnostics (CHTC/Modal, DMR-053)
```

- Config: `config/profiles/*.yaml` + `config/taxonomy.overlay.yaml` + `config/components.yaml` + `config/models.yaml` + `config/runbooks/catalog.yaml`.
- Remote serving (Modal / SSH-tunneled vLLM / CHTC / conda): `docs/setting-up/remote-serving.md` + `deploy/htcondor/` + `deploy/conda/`. Modal deploy workflow (SDK pinned `modal==1.6.2`; pre-warm → deploy → verify → teardown, cost guards, troubleshooting) lives in `deploy/README.md`. CLI rule: `--profile`, `--model`, `--prompt` and `--agent-model` work before OR after the subcommand on every command (a flag after the subcommand wins; `SANDBOX_PROFILE` is the default).
- Runtime taxonomy is written to `data/runtime/taxonomy.yaml` (gitignored).
- Prepared fixtures: `data/runtime/prepared/` via notebooks or `sandbox datasets prepare`.
- Experiment log: `reports/experiment_log.jsonl` (sandbox-local, not a sister-repo mirror).
- Experiment reports: `sandbox experiment report` writes `report.md`, `report.json` and `cards/<run-id>.card.json` beside the manifest with the sand42 card contract (`docs/SAND42-EXPERIMENT-DESIGN.md` section 5), per-class routing and paired CIs.
- Human review: `activate` defaults `MAILROOM_CHECKPOINTER=sqlite`, so parked documents survive a restart. Decision-reviewer classes (`--decision-reviewer BACKEND:MODEL`, `--decision-class CLASS=CUTOFF`) reach their reviewer at any sorter confidence, after the sorter's retries. Agreement at the cutoff goes to `extract`. A sorter below its low band may be corrected by a reviewer at the cutoff. An unsure reviewer, or disagreement with a medium or high sorter, parks for human review. Cutoffs are provisional until issue #208. Other classes have no disagreement check. An unsure extraction reaches the judge once its retries are spent, unless it is empty or failed a guardrail; only a complete, accurate judge pass that read the whole source lets it archive, otherwise it parks. The arbiter also reads the source.
- Decision backends (SAND-085): `local` runs `sorter_reviewer` on the run's own serving route; `api` runs it through OpenRouter on `agent_routes.sorter_reviewer` (e.g. `api:openai/gpt-6-luna`) and accepts pinned provider ids only, so `-latest`, `~`, `:floor` and `openrouter/*` ids are refused; `jev` and `mock` are the other backends. Every live class, correspondence included, accepts every backend. The Enron correspondence is public, so no backend refuses it (SAND-086 cancelled).
- Reviewer runs: the decision reviewer is the Decisions-API model `openai/gpt-6-luna-decisions` (OpenRouter `POST /api/alpha/decisions`; no chat route, a probability per option, input-only pricing), set with `reviewer: {backend: decisions, model: openai/gpt-6-luna-decisions, questions: <stem>}`. Question sets live in `config/decisions/` and are frozen in the run lock. `config/runs/reviewer-calibration-luna-decisions-v2.yaml` (735 train documents, `reviewer_decisions_v2`) puts all five classes over the 95% target (contract 0.78, merger_agreement 0.99, corporate_record 0.96, correspondence 0.64, insurance_claim 0.70); `reviewer-validation-luna-decisions-v2-test.yaml` routes 98.5% of the test split unattended with one misroute (`reports/reviewer-calibration/reviewer-calibration-luna-decisions.md`). `config/runs/pipeline-luna-decisions-qwen-smoke.yaml` runs the full pipeline (`qwen/qwen3.7-flash`, 10 documents at a time, single-call sorter) with that reviewer. Never calibrate the reviewer on a chat model: preflight refuses a paid `task: sorter_reviewer` run without a `reviewer:` block, and `backend: api` needs `allow_chat_model: true`. The older `reviewer-calibration-luna*.yaml`, `reviewer-validation-luna-*.yaml` and `sorter_reviewer_decision_v*.txt` runs used the chat model `openai/gpt-6-luna` by mistake and are superseded. `scripts/calibrate_reviewer.py --run <id>` picks each class's cutoff from a finished calibration run. Start: `sandbox run preflight --config <file>`, then `sandbox run start --config <file> --initials <XX>` (the spend gate; initials are 2–6 capital letters). If a long `task: pipeline` process dies, the checkpoint stays `running` and `sandbox run resume` continues it.
- Paid runs (SAND-089): every paid run needs `job.max_wall_seconds`; a run that warms a Modal GPU, or has no API model, also needs `job.cost_cap_usd`; a run that sends any agent to OpenRouter needs `job.api_cost_cap_usd` and a token price for every API model: `config/api_prices.yaml` (full OpenRouter price sheets; a tier applies to a whole call whose prompt reaches its `min_prompt_tokens`), with the built-in `SANDBOX_MODEL_PRICES` table in `src/mailroom_sandbox/job/metrics.py` as the fallback. The run ceiling uses each model's dearest tier. The GPU cap does not limit OpenRouter spend. `sandbox experiment create` recommends all three from the design.
- Tracing default: Langfuse 3 / SDK v4 (`OBSERVABILITY_PROVIDER=langfuse`). Phoenix is an optional sidecar. OpenRouter is opt-in.
- Docker: `deploy/Dockerfile` + Compose profiles including `jupyter` — see `docs/setting-up/docker-offline.md`. Every Compose port binds `127.0.0.1`; Langfuse web and worker are pinned to `3.225.15`.
- Serving/run cost: [`docs/RUN-COST-DERIVATION.md`](docs/RUN-COST-DERIVATION.md) — per-doc cost
  derivation (OpenRouter token-billing is exact; Modal is container-time), the wave/escalation cap
  rules, and the repo layout index at `docs/setting-up/LAYOUT.md`.
- Agent skills: `.cursor/skills/` (router + Langfuse / Braintrust / Phoenix / Ollama / Modal / Hugging Face).

## Reduced agent profile (HUB-015)

- The **reporter agent is retired** in this sandbox: `components.yaml` lists it
  under `retired_agents`, and the compile stage is the **computational
  procedural reporter** — the graph's `compile_report` node backed by
  the vendored llm-mailroom's `compile_matter_record` (deterministic, **no LLM
  call**; the sandbox eval never acquires an LLM client for it).
- **Reviewers stay enabled** (`sorter_reviewer` + its `sorter_reviewer_local_v0`
  prompt) — the reduced profile removes the reporter, not the reviewers.
- HF fixture targets (`data/fixtures/hf/docclass_mini.jsonl`) carry the full
  mailroom-dataset ground-truth schema: per-doc-type `expected_subclass`
  (corpus strata vocabulary) + `expected_fields` (27-key GT schema subset:
  intent + provenance, sentiment, claims/entity fields) propagated into every
  eval row.
- **1:1 live-class specialists:** `contract` → `contracts_specialist`,
  `merger_agreement` → `merger_agreement_specialist`, `corporate_record` →
  `corporate_records_specialist`, `correspondence` →
  `correspondence_specialist`, `insurance_claim` →
  `insurance_claims_specialist`. Merger no longer rides the CUAD contracts
  agent.

## Specialist extraction guidance

- `config/prompts/corporate_records_specialist_simplified.txt`, line 11:
  `subsidiary_list` maps to `record_type: other`; extract the parent into
  `entity_name`, describe the subsidiary listing in `subject_matter`, and use
  subsidiary names as `keywords`. Leave `filing_number` null unless an official
  filing or document number is present; never use an exhibit ID.
- `config/prompts/correspondence_specialist_simplified.txt`, lines 14 and 33:
  emit null for `communication_type` when no registered token fits the text;
  still extract sender, recipient, and date from headers. Never invent a type.

Keep extraction guidance aligned with these frozen rules; see
[prompt guidance](config/prompts/README.md#extraction-rules-in-the-re-frozen-v1-stems)
for source links and registered communication types.

## Architecture gotchas

- Activate **before** importing mailroom graph/agents: `mailroom_sandbox.runtime.activate(profile)`.
- The vendored family trees are put on `sys.path` at package import (`mailroom_sandbox/__init__.py`) — a fresh checkout works offline, no `fetch-deps`. `MAILROOM_SRC` / `DOJO_SRC` env vars still override for refresh workflows.
- Mailroom's `pipeline.config.CONFIG_PATH` is hardcoded; the sandbox monkeypatches it.
- `DEFAULT_PROVIDER` alone is not enough — OpenRouter model ids must be rewritten via the overlay.
- `--model` overrides every agent; `--agent-model NAME=tag` is surgical and wins last.
- Scoring + pipeline are pinned by the tracked snapshots: `vendor/llm-mailroom/VENDOR.md` + `vendor/llm-dojo-scoring/VENDOR.md` — both consume reviewed standalone revisions through workspace packages when available, with SHA-frozen standalone commit/release refs as the fallback; refresh with `python scripts/sync_vendor.py` (monorepo root) or `sandbox fetch-deps` and commit the diff. `get_suite("local_vs_api")` compares offline vs API-key serving metrics (table + scorecard + cost; TTFT never inferred; GPU/KV stripped on API records).
- Isolated evals call vendored agent classes (always importable now); the `offline_fallback` path still exists for missing deps.
- `scripts/` and `legalbench/` are not in the installed `mailroom` wheel — they ARE in the vendored tree, which also supplies `PYTHONPATH` for `sandbox pipeline watcher` / `sandbox pipeline api` (`_mailroom_env` adds both vendored srcs).
- Sandbox-isolated work uses the local **`SAND-*`** board in
  [`governance/TASKS.md`](governance/TASKS.md) (prefix cheat-sheet:
  [`governance/PREFIX.md`](governance/PREFIX.md)). Do **not** open `DMR-*`
  cards here. Cross-family / mailroom-pipeline work stays on
  the Digital-Mailroom hub board (`governance/TASKS.md`) as **`DMR-*`** — cite `Related:
  DMR-NNN` on a SAND card when a sandbox change is driven by family work.
  Do not invent a second family MESSAGE_BOARD in this repo.

## Tests

No real LLM calls in the default suite. `@pytest.mark.local_llm` is skipped unless `SANDBOX_LOCAL_LLM=1`. `tests/conftest.py` sets `SANDBOX_SKIP_DOTENV=1` before any test, so a developer's `.env` (real keys) never loads into the suite. `runtime._load_dotenv` honours the variable, so set it only for tests.
