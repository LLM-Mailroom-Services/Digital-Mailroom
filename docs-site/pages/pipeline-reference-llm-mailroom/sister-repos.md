---
description: The repositories around the pipeline.
icon: people-group
title: Sister repositories
---

# Sister repositories

llm-mailroom does not fly alone. It is the pipeline at the center of a small constellation of governed repositories, plus derived artifacts hosted elsewhere. Each repository has its own repo, board discipline, and release train.

Since 2026-08-30 the whole constellation also lives as **one monorepo** ([`Digital-Mailroom`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom)). Every family repo is a git-subtree package under `packages/`, wired as a single `uv` workspace. The monorepo is the **source of truth for active development**.

This page maps who is who, what flows between them, and where the canonical state of each lives.

| Fact | Value |
| --- | --- |
| Links re-verified | 2026-10-06 |
| Monorepo verified | 2026-10-06 |
| Corpus pin | Hub tag `v9.3` / `ff4ca546` (as of 2026-11-08) |
| Dojo pin | `v0.28.1` (as of 2026-11-08) |

This page describes each neighbour from the point of view of llm-mailroom. For each one it gives what it gives to the pipeline, what it takes from it, and what breaks if the coupling drifts. For the diagram of all the flows, see [The constellation](../how-it-fits-together/architecture.md).

| Your question | Read |
| --- | --- |
| Where do I make a change that touches several repos? | [Digital-Mailroom — the monorepo](#digital-mailroom-the-monorepo-since-2026-08-30) |
| Where do the production prompts come from? | [llm-entity-extraction — the sister loop](#llm-entity-extraction-the-sister-loop) |
| How do I move the scoring pin? | [Auto-bump when dojo publishes](#auto-bump-when-dojo-publishes) |
| What must I update when I rename a span or a class? | [The-Mailroom — the visual engine](#the-mailroom-the-visual-engine) (schema mirror duty) |

## At a glance

| Repository                                                                              | Role                                                                                                                                                                                                | Relationship to mailroom                                                                                                                                                                 |
| --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Digital-Mailroom](https://github.com/LLM-Mailroom-Services/Digital-Mailroom)           | **Monorepo / hub** — every constellation repo as a git-subtree `packages/` member in ONE uv workspace; hub task board `governance/TASKS.md`; sub-package sync driver `scripts/sync_packages.py`     | **Development source of truth for cross-repo work** — this repo is `packages/llm-mailroom` there; sync via subtree `pull`/`push` (issue #2, DMR-era cards)                               |
| [llm-entity-extraction](https://github.com/Exios66/llm-entity-extraction)               | Prompt-experiment loop: prompt versions × models over CUAD/LegalBench/MAUD corpora                                                                                                                  | **Sister repo.** Source of the vendored LangChain sorter/contracts prompts; shares ONE kanban board with this repo                                                                       |
| [llm-dojo-scoring](https://github.com/Exios66/llm-dojo-scoring)                         | Deterministic, field-type-aware scoring engine (metric registry, dedicated specialist suites, sorter subclass catalogs, computable intake clerk, prompt catalog, `local_vs_api` serving comparison) | **Upstream governed dependency**, pinned in `pyproject.toml` (`@v0.28.1`); auto-bump via `.github/workflows/bump-dojo-scoring.yml`                                                       |
| [Enron-Evaluation-Environment](https://github.com/Exios66/Enron-Evaluation-Environment) | EDA + pipeline-ready correspondence dataset from the CMU Enron corpus                                                                                                                               | **Corpus feed** for the `correspondence` doc class; publishes HF datasets consumed by eval loops. Virtual monorepo member (no build)                                                     |
| [claims-data-eda](https://github.com/Exios66/claims-data-eda)                           | Insurance-claims candidate-corpus EDA (CMS DE-SynPUF direction)                                                                                                                                     | **Corpus feed (candidate)** for the `insurance_claim` doc class — its honest-gap benchmark source. Virtual monorepo member (no build)                                                    |
| [atticus-investigation](https://github.com/Exios66/atticus-investigation)               | LegalBench classification prompt-engineering pipeline                                                                                                                                               | **Eval sibling**: same prompt-version × model methodology, LegalBench focus                                                                                                              |
| [The-Mailroom](https://github.com/Exios66/The-Mailroom)                                 | Pixel-art visual engine + hosted Observatory Space — floor, review siding, Inbox enqueue, inspector, sessions, metrics — plus a TUI console                                                         | **Downstream visualizer** — Langfuse-only display; Inbox / REVIEW proxy this API via `MAILROOM_PIPELINE_URL` + token + `/v1` ([PR #30](https://github.com/Exios66/The-Mailroom/pull/30)) |
| [agent-mailroom](https://github.com/Exios66/agent-mailroom)                             | Self-contained mailroom: one state machine per document, specialist agents at desks (Electron/TUI/live floor)                                                                                       | **Sibling implementation** — same doctrine, independent train; monorepo member (`packages/agent-mailroom`)                                                                               |
| [local-mailroom-sandbox](https://github.com/Exios66/local-mailroom-sandbox)             | Local-first experiment sandbox (Ollama, vLLM, llama.cpp)                                                                                                                                            | **Sibling sandbox** — local-model experiments; monorepo member (`packages/local-mailroom-sandbox`)                                                                                       |
| [eval-environment](https://github.com/LLM-Mailroom-Services/eval-environment) | Per-node evaluations, calibration, the frozen v1 prompt lineage and the GEPA prompt-mutation loop | **Downstream evaluator** — imports this repo as an editable path source; traces to Braintrust or local Phoenix, never to the production Langfuse project |
| [mailroom-ml](https://github.com/LLM-Mailroom-Services/mailroom-ml) | ModernBERT document classifier (standalone contractor repo, not a monorepo member) | **Optional intake fast path** — lazily imported when `MAILROOM_BERT_INTAKE` is on; fail-open, so the pipeline runs without it |
| [llm-mailroom-graph](https://exios66.github.io/llm-mailroom-graph/)                     | Interactive graphify knowledge graph of this codebase                                                                                                                                               | **Derived site** — build artifact only, never committed here                                                                                                                             |
| [llm-entity-extraction-graph](https://exios66.github.io/llm-entity-extraction-graph/)   | Interactive graphify knowledge graph of the sister experiment loop                                                                                                                                  | **Derived site** — companion map of the sister repo's code structure                                                                                                                     |

## Digital-Mailroom — the monorepo (since 2026-08-30)

The Mailroom Umbrella's single checkout: `git clone LLM-Mailroom-Services/Digital-Mailroom` reproduces **every** family repo under `packages/` (git subtrees, own history). One `uv sync` installs the whole workspace editable against a single `uv.lock`. There are no cross-repo pip installs and no import-path juggling.

* **Layout**: `packages/<name>/` per standalone repo — this repo is `packages/llm-mailroom`. `Enron-Evaluation-Environment`, `claims-data-eda`, `llm-mailroom-graph` and `mailroom-corpus-eda` are **virtual members** (`package = false`): their data/code stays colocated but nothing installs from them.
* **Workspace rules** (monorepo `AGENTS.md`): member `pyproject.toml` files **keep their published git pins**. Dev redirection happens ONLY through `[tool.uv.sources]` tables. This repo's table currently redirects `llm-dojo-scoring` to the workspace. `pip install .` inside the package / subtree keeps using the pins, so Docker/HF Spaces builds are unaffected.
* **Sub-package sync**: `python scripts/sync_packages.py {status|pull|push|snapshot}` reconciles the subtree mirrors with `Exios66/*` (baseline cursor `scripts/packages_sync.json`; `status` recomputes live drift). The monorepo is the **dev source of truth**; standalone-repo fixes that already landed here win merges unless the upstream supersedes them.
* **Cross-repo task board**: `governance/TASKS.md` (hub scope: workspace wiring, cross-package governance, sync, docs, releases). Read it before any hub-scope work; package-scoped work keeps each package's own board (e.g. the entity repo's `MESSAGE_BOARD.md`).
* **Test gates**: suites run one package per pytest invocation (`uv run pytest packages/llm-mailroom/src/tests`, …) — several packages ship colliding top-level `tests` packages.
* **Heavy assets pruned**: example PDFs, demo screenshots, and report archives are NOT in the monorepo (see the `docs/examples/samples/` note in [Agents](agents.md)). Monorepo tests skip when a pruned fixture is absent.

Every package still carries its own `AGENTS.md`, docs, tests and deploy configs. This page (and this repo's `docs/`) remain canonical for the pipeline. The monorepo root `README.md` is the hub manual.

## llm-entity-extraction — the sister loop

The experiment environment where prompts are born and measured before they reach this pipeline:

* Measures how well prompt versions classify legal documents and extract entities — every run produces one append-only record in its `reports/experiment_log.jsonl`.
* Its champion prompts are vendored into this repo under `langchain_agents/` (`sorter`, `contracts_specialist`). The full version lineage (`PROMPT_VERSIONS`) comes along, so evaluation can pin exact versions.
* **Governance:** one shared kanban board (`board/MESSAGE_BOARD.md` + discussion log in that repo) tracks cards for BOTH repos. Cross-repo work = one card, one issue, both changelogs. Never create a mailroom-side board.
* Release discipline there: semver tags trace single commits; this repo's vendored copies are refreshed deliberately against its `main`.

## llm-dojo-scoring — the upstream scoring engine

The scoring layer both mailroom and entity-extraction consume:

* Field-type-aware deterministic scoring (id/date/money normalization, Jaro-Winkler/token-set names, SQuAD-style token F1, Hungarian bipartite list matching, optional embedding rescue) — never exact-match-on-everything.
* A metric registry with T0–T3 tiers and task-aware dispatch (`score_task`).
* **Agent profiles** covering every mailroom agent.
* `DOC_TYPE_BUNDLES` keyed on the processed document classes, with the explicit-fallback honesty resolver (`resolve_doc_bundle()`).
* Pinned as a git dependency (`@v0.28.1` as of 2026-11-08). Mailroom wires its `taxonomy.yaml` scoring block onto package Settings via `observability/field_scoring.py`. That module is a deprecation shim: move imports to `llm_dojo_scoring.field_scoring`.
* **v0.21.0** — re-synced the six `production` classification prompts from llm-mailroom `6ddde73` (the five-class doctrine no longer names the MAUD/CUAD corpora); catalog `version: 0.21.0`.
* **v0.20.0** — the `production` family is re-vendored from live llm-mailroom (`scripts/sync_production_prompts.py`). Five specialists equal the frozen `production_prompts` v1 bytes, and `reporter` is `kind: deterministic`. Rows record `source_commit`. It adds `llm_dojo_scoring.intents` and the exact-match `label` field type.
* **v0.12.2** ([PR #11](https://github.com/Exios66/llm-dojo-scoring/pull/11)) is additive core-dependency alignment. `jellyfish>=1.0` moves into the base install, so there is no silent `difflib` fallback. It adds optional extras `tracing` / `all` (and `openai` on the `embeddings` extra). Scoring formulas from v0.12.1 are unchanged.
* **v0.12.1** ([PR #10](https://github.com/Exios66/llm-dojo-scoring/pull/10)) adds the `local_vs_api` serving suite: `compare_serving` tables, scorecards, and cost cards for local-vs-API-key runs. Document-pipeline scoring formulas from v0.11.0 are unchanged.
* **v0.11.0** ([PR #8](https://github.com/Exios66/llm-dojo-scoring/pull/8)) is additive on the 0.10.0 scoring surface. T0/T1 `MetricDef`s carry `citation` / `inclusion` / `ground_truth`. `llm_dojo_scoring.prompts` vendors production + docclass templates, with metric names in catalog metadata only (anti-priming). `field_presence` stays unemitted.

### Auto-bump when dojo publishes

Mailroom keeps the dojo pin current via `.github/workflows/bump-dojo-scoring.yml` and `src/scripts/bump_dojo_scoring.py`:

1.  **Preferred:** from `llm-dojo-scoring`'s release workflow, fire a `repository_dispatch` at this repo:

    ```yaml
    - name: Notify llm-mailroom to bump pin
      uses: peter-evans/repository-dispatch@v3
      with:
        token: ${{ secrets.MAILROOM_DISPATCH_TOKEN }}  # PAT with repo scope on llm-mailroom
        repository: Exios66/llm-mailroom
        event-type: dojo-scoring-released
        client-payload: '{"tag": "v0.12.2"}'  # use github.event.release.tag_name
    ```
2. **Backstop:** the workflow also runs on a daily cron and via `workflow_dispatch` (optional tag / dry-run inputs), polling `Exios66/llm-dojo-scoring` releases/latest.
3. When the pin is behind, the workflow opens (or updates) a PR on `cursor/bump-dojo-scoring-<tag>` that rewrites `pyproject.toml` plus the documented pin references. Merge after CI is green.

> In the **monorepo**, the nested `.github/workflows/` is not read by GitHub (only the hub root's workflows are) — the auto-bump is **release-time only** there: run `src/scripts/bump_dojo_scoring.py --check/--apply` manually when cutting a mailroom release, then `sync_packages.py push` the pin change.

Local check / apply:

```bash
PYTHONPATH=src python src/scripts/bump_dojo_scoring.py --check
PYTHONPATH=src python src/scripts/bump_dojo_scoring.py --apply --tag v0.28.1
```

## Corpus feeds

* [**Enron-Evaluation-Environment**](https://github.com/Exios66/Enron-Evaluation-Environment): builds the correspondence-class corpus (517K-message index → stratified pipeline dumps), with the shared heuristic labeler as ground truth. Published datasets live under the [`Lucius-Morningstar`](https://huggingface.co/Lucius-Morningstar) HF org (`enron-correspondence`, `enron-correspondence-dedup`, …).
* [**claims-data-eda**](https://github.com/Exios66/claims-data-eda): exploratory analysis toward an insurance-claims benchmark. Hub rows today are CMS DE-SynPUF source tables; dojo v0.28.1 ships **`determination_consistency` / `amount_exactness`** as real scorers. CMS GT is homogeneous (all-approved / empty denials), so Hub `determination_consistency` is gated as a quality KPI. Mailroom exercises the scorer on a local approved/denied/partial contrast pack (documented in [Agents](agents.md)).
* **Honesty (dojo v0.28.1 suites):** `compliance_filing` has zero `mailroom-dataset` rows. HF `--real` omits it, and the local fixture pack is mock/check only. `corporate_record` has 450 Hub subclass rows: 39 legacy S-1 rows, expanded by +411 EDGAR exhibits in v9. It has **no external extraction benchmark**; schema-complete extraction GT is the local pack. `court_opinion` / `due_diligence` are retired from live mailroom (`retired=True`).
* [**atticus-investigation**](https://github.com/Exios66/atticus-investigation): LegalBench classification sibling — its methodology (prompt versions × models, paired-bootstrap ablations) is the same doctrine this constellation follows.

## The-Mailroom — the visual engine

* [**The-Mailroom**](https://github.com/Exios66/The-Mailroom) (v0.5.0) renders every pipeline run as an animated conveyor of document envelopes. The stations are sorter, specialist bays, judge gate, boss's desk, reporter, and archive, grouped into three rooms. It also has:
  * a human-review siding queue;
  * a per-trace inspector;
  * a matter/session explorer;
  * live metrics.

  Surfaces: `mailroom-web` (FastAPI + vanilla JS on :8001) and `mailroom-tui` (AgentLab-style live console).
* **Langfuse is its sole source of truth**: every envelope, badge, verdict, and metric comes from this repo's Langfuse project. Nothing is fabricated, and nothing falls back to canned data. Demo mode seeds synthetic runs INTO Langfuse (env `demo`) rather than bypassing it.
* **Schema mirror duty (its #1 maintenance rule)**: THIS repo can change span names, node order, agent roster, doc classes, confidence thresholds, or judge score names. When it does, The-Mailroom must update `mailroom_ui/pipeline_schema.py` and `mailroom_ui/trace_interpreter.py` in the same change window. New spans render as `unknown` stage until mirrored. `MAILROOM_TAXONOMY` can point it at this repo's `src/config/taxonomy.yaml` live instead of its bundled mirror.

  Current intake contract:

  * span `normalize-intake` (INGEST), agent `intake`;
  * HF runner `src/scripts/run_hf_pilot.py`, session `pilot-hf-<stamp>`;
  * tag `source-mailroom-corpus` on the v9 full corpus. Other Hub sets use their own `source-*` tag from `pipeline/hf_corpora.py`;
  * ground truth on trace input/metadata, including `expected_hf_class`.

  Production session `pilot-hf-20260825T044207Z` is the reference five-doc Qwen 3.7-Flash subset.
* **Reconsideration (The-Mailroom** [**PR #14**](https://github.com/Exios66/The-Mailroom/pull/14)**):** the visualizer parks archived objective misses as **RECONSIDER**. It uses ground truth, judge, and scores, never self-reported confidence. This pipeline mirrors those cause tokens in `pipeline/reconsideration.py` and acts on them **before** catalog write:
  * GT class miss → Lane A, even at 0.99;
  * reviewer still wrong → human review;
  * hollow extract, or expected-field coverage below `confidence.low` → retry, then review;
  * failed `compile_report` → `catalog_write` is withheld.
* **First-pass / STP metrics (production, no ground truth):** every finished run now emits the registered dojo score `success_rate` (0/1). It is 1 only when the document archived in one hop. Any of these makes it 0: a classify/extract retry, Lane A, arbiter, boss, human review, guardrail, parse/schema failure, or transient provider self-loop.

  Incoming live documents are zero-shot. This flag does **not** consult `class_correct`, field GT, or the hosted LLM-judge overlay; those stay eval-only.

  The-Mailroom metrics (pixel METRICS tab, hosted Observatory, TUI `m`) tile **FIRST PASS** (count) and **FIRST-PASS RATE** from that score. Traces from before the producer score existed use a routing-path/`retried` fallback. Do not flatten FIRST PASS into ARCHIVED, because archived includes retries that later succeeded. Do not flatten it into RECONSIDER (GT/judge overlay) either.

  The Langfuse **Mailroom Performance** dashboard charts the live+pilot rate and count. `GET /ops/status` reports `first_pass` / `first_pass_rate` from the catalog.
* **Live floor (The-Mailroom** [**PR #16**](https://github.com/Exios66/The-Mailroom/pull/16)**):** the visualizer re-enriches in-flight traces every poll. It reads producer liveness from `GET /health` (`checks.watcher`, `inbox_pending`). This pipeline does three things so an upload appears on the floor within one poll tick:
  * it flushes after each graph node (`output.stage` on the span);
  * it embeds the inbox watcher in the API lifespan by default;
  * it handles `on_moved` / `on_modified` inbox events.

  Set `MAILROOM_PIPELINE_URL` on the visualizer to this API. Use `http://127.0.0.1:8000` on a shared host, or the public producer Space URL when the Observatory is itself a Space.
* **Inbox enqueue + Observatory cards (The-Mailroom** [**PR #30**](https://github.com/Exios66/The-Mailroom/pull/30)**):** Observatory **Queue a document** proxies multipart files to `POST /v1/upload` (202). Unconfigured visualizer returns 503 — no fabricated catalog row. Cards show classification hit/miss/pending and a headline strip; Langfuse snapshot cache (`MAILROOM_TRACE_CACHE_DIR`) is visualizer-side. Pairing knobs: `MAILROOM_PIPELINE_URL` + `MAILROOM_PIPELINE_TOKEN` + `MAILROOM_PIPELINE_API_PREFIX=/v1`. The-Mailroom `publish_space.py` copies those as Observatory Space secrets/variables. Checklist: [`deploy/space/PAIRING.md`](https://github.com/Exios66/llm-mailroom/tree/main/deploy/space/PAIRING.md).
* **REVIEW resolve (The-Mailroom [PR #18](https://github.com/Exios66/The-Mailroom/pull/18), [PR #20](https://github.com/Exios66/The-Mailroom/pull/20)):** the visualizer proxies operator decisions to this API. It never holds producer keys in the browser. REVIEW desk buttons call the producer, so operators never type endpoints. The buttons are Approve / Reject / Requeue, class / subtype selects, and Open original / text pane.

  Producer surface:

  * `GET /lookup` and `GET /audit/{doc_id}`;
  * `POST /review/{doc_id}/resolve` with `disposition=resume|record|requeue` (plus mailroom-local `complete`). Optional `doc_type` / `doc_subclass` are written to the parked manifest on resume, and stamped on the inbox sidecar on requeue;
  * `GET /documents/{doc_id}/source` (`?download=1` for original bytes).

  Set `MAILROOM_PIPELINE_URL` + `MAILROOM_PIPELINE_TOKEN` on the visualizer. Do not use `MAILROOM_API_URL`, which is TUI → visualizer `:8001`. The producer must be **reachable from the visualizer process**:

  * localhost `:8000` for a laptop pair;
  * the published Hugging Face Docker Space for the hosted Observatory (`src/scripts/publish_space.py`, URL `https://lucius-morningstar-mailroom-producer.hf.space`).

  Local compose: `docker compose -f deploy/docker-compose.producer.yml --env-file .env up -d --build`. `GET /health` advertises `producer` / `review_resolve`. Full audit parse: `GET /audit` / `scripts/analyze_audit_db.py`.
* **Governance:** fully governed member of the family — own `AGENTS.md`, own semver release train (v0.5.0), own test suite (never hits real Langfuse), own wiki. It is a downstream OBSERVER: dependency of no family repo — the coupling is the shared trace contract.

## Derived artifacts

* [**llm-mailroom-graph**](https://exios66.github.io/llm-mailroom-graph/) — interactive AST-derived knowledge graph of this codebase (built with [graphify](https://github.com/Graphify-Labs/graphify); the vendored agent skill lives in `.opencode/skills/graphify/`). Graphs are build artifacts: query them for structure questions ("what calls X", "where does Y route"), but board rules and source win any disagreement.
* [**llm-entity-extraction-graph**](https://exios66.github.io/llm-entity-extraction-graph/) — companion graphify map of the sister experiment loop's codebase.
* **Hugging Face —** [**`Lucius-Morningstar`**](https://huggingface.co/Lucius-Morningstar) — the family's published dataset surface.
  * **`mailroom-dataset` schema v9** is the targeted full pipeline corpus: 3,302 docs, pinned Hub tag `v9.3` / `ff4ca546…`. It holds CUAD contracts, MAUD merger agreements, S-1 corporate records, an Enron correspondence sample, and CMS insurance claims.
  * It is the v9 successor of the frozen v8 baseline `mailroom-corpus` (hardened tip `eafe1ab4…`). Version v8 is the HUB-028 insurance LOB expansion (GNOTHEIA property + BDR auto) with full GT conformance. It also carries HUB-032's §84 hardened ground\_truth columns: identity, evaluation contract, matter/group.
  * **`docclass-pilot`** is the class × subclass example pack (48 strata: every type and subtype in that parent).
  * Other pipeline-ready Hub sets ingest the same way via `run_hf_pilot.py --dataset`: `enron-correspondence-dedup` (\~247k), `cms-desynpuf-insurance-claims`, `mailroom-cuad-contracts[-full]`.
  * `legalbench-full` is a LegalBench CLI task pack, not a document-pipeline ingest.
  * One split rule serves the whole family: `md5(filename) % 10 == 0 → test`. Entity-extraction's publisher scripts own it.
  * Local committed PDFs under `docs/examples/samples/` remain PDF-ingest fixtures. They are not the class catalog.

## Governance notes

* Every repo above runs the same working agreement:
  * read the board first; no card = no work;
  * append-only prompt versioning;
  * a changelog entry in the ship commit;
  * evidence before "done".
* **Hub-scope work is tracked on the monorepo board** (`Digital-Mailroom/governance/TASKS.md`, cards `DMR-0NN`). Claim cross-package wiring, sub-package sync and docs alignments there before editing, and commit them with `DMR-0NN:` references. Standalone-package work keeps each package's own board (`read the board first` applies on both sides).
* Cross-repo changes ride **one card + one issue**, with both repos' CHANGELOGs updated in the same pass. Docs that describe the constellation (this page, wiki pages, README umbrella sections) are maintained in the standalone repo. They arrive in the monorepo via subtree `pull`, and go back the other way on `push`.
* Dependency pins are audited after every upstream release (pin ↔ tag ↔ import-time validation must agree across `pyproject.toml`, `requirements*.txt`, and installed provenance). In the monorepo the pins keep their published meaning; `[tool.uv.sources]` redirects are dev-only.
