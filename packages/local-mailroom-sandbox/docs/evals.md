# Evals

Isolated evals cover every live pipeline agent / node. Connected `pipeline`
runs the vendored 13-node graph (when `sandbox fetch-deps` is present) and
scores classification, stage, extraction, and routing together. All runners
are `--dry-run` capable, append one JSONL record per completed experiment,
and score with `llm-dojo-scoring` (never exact-match-on-extraction).

```bash
sandbox agents list
sandbox agents show judge
sandbox cutover --agent-model judge=qwen3:14b

sandbox eval sorter --mock
sandbox eval sorter_reviewer --mock
sandbox eval contracts_specialist --mock
sandbox eval judge --mock
sandbox eval arbiter --mock
sandbox eval pipeline --mock          # connected: class + stage + extract + routing
sandbox eval chained --mock           # sorter → extract only
sandbox eval legalbench --mock
sandbox eval local_vs_api --mock  # fixture timings; no OPENROUTER_API_KEY
sandbox eval local_vs_api --from-log  # pair experiment_log local vs API-key rows
sandbox matrix --task judge --providers ollama --models qwen3:8b \
  --prompts mailroom-default --sample 2 --mock --dry-run
sandbox matrix --task sorter --providers ollama,openrouter \
  --models qwen3:8b --prompts mailroom-default --mock
```

`--local` uses the active profile's OpenAI-compatible server (`sandbox fetch-deps`
required for live agent classes). `--mock` uses deterministic fixtures / the fake
client. `local_vs_api` is importable dojo serving comparison (`get_suite("local_vs_api")`):
TTFT stays `None` unless recorded; GPU/KV/VRAM are stripped on API-key records;
local Ollama cost stays `None` without a price table. The suite returns a
scoring **table** (every T0/T1 metric, missing as `None`), a **scorecard**
(identity + cost calculations), and markdown for the experiment log.
Sorter headlines stay `accuracy` + `f1_macro`.

## Isolated vs connected

| Task | What runs | Observation |
| --- | --- | --- |
| `intake` | dojo `deterministic_normalize` | `normalize-intake` span |
| `pdf_transcriber` / `image_extractor` | transcriber / vision agent | retriever |
| `sorter` / `sorter_reviewer` | classifier | `classify-document` agent |
| five live specialists | `.extract()` | `extract-fields` agent |
| `judge` | completeness judge | `judge-verify` evaluator |
| `arbiter` / `boss` | named agents | matching agent spans |
| `compile_report` | procedural reporter node (no LLM — HUB-015 reduced profile) | `compile-report` span |
| `human_review` / `catalog` / `archive` | procedural gold | matching spans |
| `pipeline` | full graph (or offline mock fallback) | `document-pipeline` chain |
| `chained` | sorter + extract only | (composite) |
| `local_vs_api` | dojo serving suite (fixtures or experiment log) | (serving; no Langfuse score names on sorter) |

Retired specialists (`court_opinions_specialist`, `due_diligence_specialist`)
are listed in `config/components.yaml` and skipped.

## Experiment log

`reports/experiment_log.jsonl` is **sandbox-local**. It is not a mirror of
llm-entity-extraction. Each record carries profile, provider, `serving_kind`
(`local` | `api`), model, prompt version, dataset fingerprint, scores +
bootstrap CI when available, tracing backend, tags, session id, and a git
snapshot. Mixed local + API-key matrix runs attach a `local_vs_api` block
from the same importable suite (table, scorecard, cost, markdown).

Markdown is regenerated next to the JSONL on every append.

## Fixtures

Offline catalog: `data/fixtures/` (see `ATTRIBUTION.md`). Tiny HF slice:
`data/fixtures/hf/docclass_mini.jsonl`. LegalBench Yes/No:
`data/fixtures/legalbench/contract_qa.jsonl`. Per-agent gold:
`data/fixtures/agents/*.jsonl`. Tiny PDF/PNG: `data/fixtures/intake/`.
Synthetic serving pair: `data/fixtures/serving/local_vs_api.json`.

`sandbox datasets pull` performs a LIVE, PINNED Hub pull into `data/cache/`
(network required; default revision is the family pin `FAMILY_HF_REVISION` —
never the floating Hub tip). It routes through the SAME corpus loader the job
preflight uses: `default`+`ground_truth` merge, `content_sha256` verification,
GT-shard-absent refusal, deterministic subsetting. Any failure exits 1 with
the error — a pull that fetched zero rows can never look successful
(live-or-loud, DMR-056):

```bash
sandbox datasets pull --max-rows 50                    # pinned ground_truth/test
sandbox datasets pull --revision <sha> --config default --split train
```

`datasets prepare` (and notebooks `01`–`03`) clean the offline catalog into
`data/runtime/prepared/` with no network — see
[`docs/docker-offline.md`](docker-offline.md). Note: `prepare` output feeds
the notebooks; JOB runs score the locked `dataset.jsonl` prepared by
`run preflight` — for live data through the eval surface, use a run spec with
a Hub `dataset:` block (below).

## Whole-run job tasks score the locked dataset (DMR-056)

`sandbox run` whole-run tasks (`pipeline`, `extract`, `chained`, `isolated`,
and every registered agent name) score the run spec's LOCKED dataset rows —
Hub or local — when the preflight prepared any. An empty lock (serving-only
specs) falls back to the runner's fixture defaults. Per-item tasks
(`sorter`, `legalbench`) always score the locked rows row-by-row. Example:
a spec with a Hub `dataset:` block and `task: pipeline` scores the live
corpus subset through the connected graph (see `config/runs/example.yaml`'s
commented Hub block).

## Adding a new eval task (the extension point, DMR-056)

Registering a new eval task is a ONE-FILE change — there is no enum, no
dispatch table, and no spec field to update:

**Isolated agent task** (e.g. a new specialist agent): add an `AgentSpec`
to `src/mailroom_sandbox/eval/agents.py` (`SPECS` / `_register()`; the
specialist pattern is `SPECIALIST_CLASS` + `LIVE_CLASS_MAP`). That single
registration automatically:

- appears in `sandbox eval <name>` (CLI choices derive from `EVAL_TASKS`),
- becomes a whole-run job task (`task: <name>` in a run spec — validation
  via `job.spec.known_tasks()`, dispatch via `job.runner`),
- is picked up by `sandbox matrix` (SPECS fallback),
- passes spec-level validation (`RunSpec`/`JobSpec` task check).

A registered task needs `mock_predict` + `score_one` (fixture rows via
`load_rows`); `live_predict` is optional — without it a live run marks
`offline_fallback` instead of silently mocking.

**Composite task** (`extract`-style): touch all five seams —
`COMPOSITE_TASKS` in `eval/agents.py`, a `_cmd_eval` arm in `cli.py`, the
matrix map in `eval/matrix.py`, `_WHOLE_RUN_TASKS` in `job/runner.py`, and a
`_run_whole_run` arm. The `_cmd_eval` fall-through to LegalBench is now an
explicit `raise` — an unregistered composite fails loudly instead of being
misrouted.

The regression test `test_registering_new_agent_spec_is_the_extension_point`
(`tests/test_job_runner.py`) pins this contract: register a dummy spec →
validation + dispatch accept it, run it, done.

## Prompt variants

`config/prompts/*_local_v0.txt` are shorter, JSON-strict templates for 7B/8B
local models. Pass `--prompt sorter_local_v0` (or `sorter_reviewer_local_v0`,
`judge_local_v0`). Per-agent prompt stems also live under
`config/components.yaml` `prompts:`.

## Component gates

`config/components.yaml` enables/disables isolated evals and overlays
confidence routing onto `data/runtime/taxonomy.yaml`. It does not fork the
LangGraph topology.
