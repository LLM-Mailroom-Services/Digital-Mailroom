# Evals

Isolated evals cover every live pipeline agent / node. Connected `pipeline`
runs the vendored 13-node graph (tracked snapshot, DMR-057 — always present) and
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
sandbox eval merger_agreement_specialist --mock
sandbox eval judge --mock
sandbox eval arbiter --mock
sandbox eval pipeline --mock          # connected: class + stage + extract + routing
sandbox eval chained --mock           # sorter → extract only
sandbox eval legalbench --mock
sandbox eval local_vs_api --mock  # fixture timings; no OPENROUTER_API_KEY
sandbox eval local_vs_api --from-log  # pair experiment_log local vs API-key rows (per comparable group)
sandbox eval local_vs_api --from-log --group 2   # several groups: pick the headline one (index or label)
sandbox eval sorter_vs_modernbert --mock  # LLM sorter vs ModernBERT accuracy+cost
sandbox metrics compare --runs local,modal,api
sandbox metrics compare --fixture   # Grant cost-compare parity (offline)
sandbox metrics compare --sorter-vs-modernbert
sandbox matrix --task judge --providers ollama --models qwen3:8b \
  --prompts mailroom-default --sample 2 --mock --dry-run
sandbox matrix --task sorter --providers ollama,openrouter \
  --models qwen3:8b --prompts mailroom-default --mock
```

`--local` uses the active profile's OpenAI-compatible server (live agent classes
ship in the vendored tree — always importable, DMR-057). `--mock` uses deterministic fixtures / the fake
client. `local_vs_api` is importable dojo serving comparison (`get_suite("local_vs_api")`):
TTFT stays `None` unless recorded; GPU/KV/VRAM are stripped on API-key records;
local Ollama cost stays `None` without a price table. The suite returns a
scoring **table** (every T0/T1 metric, missing as `None`), a **scorecard**
(identity + cost calculations), and markdown for the experiment log.
Sorter headlines stay `accuracy` + `f1_macro`.

### Serving provenance and comparable groups (dojo v0.22)

The dojo refuses to emit a serving scorecard without a provenance stamp
(`dataset_revision`, `prompt_id`, `serving_kind`, `model_id`; USD metrics also
`cost_basis`) and treats a comparison leg that pools runs differing on
serving kind / model / prompt / task / dataset fingerprint / revision / split /
draw seed as `identity_mixed`.

* **Records carry the stamp.** Job-run records (`record_from_run`) take
  `dataset_revision` (the lock's resolved Hub sha), `split` and `draw_seed`
  (`sample_seed`) from the run lock via `job.metrics.lock_dataset_provenance`;
  a local `file` dataset has no Hub revision and gets none. Token-price USD is
  labelled `cost_basis=token_price_estimate`. The committed serving fixtures
  carry `dataset_revision = job.spec.FAMILY_HF_REVISION`. `dataset_revision` is
  never derived from the dataset fingerprint (the fingerprint maps to
  `draw_seed`). Isolated fixture evals and old log rows have no Hub revision, so
  their scorecard emission **fails loudly**: `emit_local_vs_api_scorecard` /
  `emit_group_scorecards` raise `ScorecardEmissionError` (a dojo
  `ProvenanceExportError` carrying `field`, `group` and a sandbox hint), nothing
  is written or logged (every group is validated before any is emitted), and
  `sandbox eval` / `sandbox matrix` / a job run exit non-zero with one line,
  e.g. `error: scorecard not emitted: local_vs_api group 2 (...): ... dataset_revision
  ... pin a Hub revision or pass --dataset-revision <40-hex Hub sha>`. There is no
  "refused" entry, no skip and no fabricated stamp. Supply the real revision with
  `sandbox eval local_vs_api --dataset-revision <40-hex sha>` (or
  `provenance={"local": {...}, "api": {...}}`); it fills a gap but never
  contradicts a revision a record already carries, and a branch name or short sha
  is rejected. An incomparable (`identity_mixed`) group raises too.
* **`--from-log` / `sandbox matrix` group before comparing.** Rows are grouped
  by full identity and a local-side leg is paired with an API-side leg only when
  they measured the same thing (`mailroom_sandbox.serving_groups`, as dojo
  `pair_comparable_runs`). Each comparable pair is one entry in `groups`; each
  is emitted as `<name>.g<n>`. With several groups the headline `scores` stay
  empty until `--group <n|label>` selects one; legs with no counterpart are
  listed under `unpaired`. The run's own `local_vs_api` comparison records in the
  log are skipped.
* **`sandbox metrics compare`** pairs per group too (`pairwise` keys
  `local_vs_api`, or `local_vs_api[n]` when several); a bucket that pools unlike
  runs is flagged `identity_mixed` and incomparable legs are listed.

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
the monorepo hub's experiment logs. Each record carries profile, provider, `serving_kind`
(`local` | `modal` | `api`), model, prompt version, dataset fingerprint, scores +
bootstrap CI when available, tracing backend, tags, session id, and a git
snapshot. Mixed local + API-key matrix runs attach a `local_vs_api` block
from the same importable suite (table, scorecard, cost, markdown).

Markdown is regenerated next to the JSONL on every append.

Specialist / extract / pipeline summaries also carry additive **schema
adherence** fields (`parse_error_rate`, `schema_valid_rate`,
`schema_adherence_rate`) that are distinct from `overall_extraction_score`
and `extraction_f1`. Isolated eval copies `overall_extraction_score` into
`scores.exact_match` when there is no classification `match` — those two
keys matching is a runner alias, not proof that partial credit is off.
Empty-field and partial-credit behavior is documented in
[`docs/archive/extraction-quality-diagnosis.md`](archive/extraction-quality-diagnosis.md).

## Fixtures

Offline catalog: `data/fixtures/` (see `ATTRIBUTION.md`). Tiny HF slice:
`data/fixtures/hf/docclass_mini.jsonl`. LegalBench Yes/No:
`data/fixtures/legalbench/contract_qa.jsonl`. Per-agent gold:
`data/fixtures/agents/*.jsonl`. Tiny PDF/PNG: `data/fixtures/intake/`.
Synthetic serving pair: `data/fixtures/serving/local_vs_api.json`.
Grant-style local / Modal / API triple (ms fields + HF id):
`data/fixtures/serving/cost_compare.json` — scored by
`sandbox metrics compare --fixture` (sandbox three-way table + dojo
`get_suite("local_vs_api")` pairwise; no GPU).

`sandbox datasets pull` performs a LIVE, PINNED Hub pull of the **full**
[`Lucius-Morningstar/mailroom-dataset`](https://huggingface.co/datasets/Lucius-Morningstar/mailroom-dataset/viewer/ground_truth)
`ground_truth` corpus (train+test, 3,302 rows at `FAMILY_HF_REVISION`) into
`data/cache/` (network required). It routes through the SAME corpus loader the
job preflight uses: `default`+`ground_truth` merge, `content_sha256`
verification, GT-shard-absent refusal, deterministic subsetting. Any failure
exits 1 with the error — a pull that fetched zero rows can never look
successful (live-or-loud, DMR-056). The Hub `test` split is only ~323 rows
(~17 mergers) and **cannot** back 40/100-per-class Modal draws; default
`split=all`.

```bash
sandbox datasets pull                         # full ground_truth train+test
sandbox datasets sample --per-class 20        # or 40 / 100 (merger cap is 152)
sandbox datasets pull --max-rows 50 --split test   # legacy tiny slice
sandbox datasets pull --revision <sha> --config default --split train
```

`datasets prepare` (and notebooks `01`–`03`) clean the offline catalog into
`data/runtime/prepared/` with no network — see
[`docs/setting-up/docker-offline.md`](setting-up/docker-offline.md). Note: `prepare` output feeds
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
corpus subset through the connected graph (see `config/runs/examples/example.yaml`'s
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

## Extraction scoring vs empty / class-mismatched Hub GT

Hub `mailroom-dataset` `ground_truth` / `gt_fields` is a **union** of
specialist keys. Many rows are not insurance claims, so insurance-claim
fields arrive empty or absent (`denial_reasons: []`, `claim_number: null`,
…). Correspondence fixtures also reuse the insurance money key
(`claimed_amount`) for a demanded dollar amount.

**Rule (SAND-026):** empty GT for a schema that does not apply to that
document type is **not** a miss. It must not pull down
`overall_extraction_score` or extraction F1. The same holds in the other
direction (empty correspondence keys on an insurance row, empty CUAD
leftovers on a merger row, …).

What the vendor already does vs where the sandbox seams:

| Layer | Empty `None` / `""` | Empty `[]` | Foreign-class keys |
| --- | --- | --- | --- |
| `llm_dojo_scoring.field_scoring.score_extraction` | skipped | **scored as an event** (missing pred → 0.0) | scored if present on expected |
| `llm_dojo_scoring.extraction_metrics.extraction_binary_metrics` | skipped | skipped | extra expected keys are FN |
| sandbox `eval.extraction_scope` (before `suite.score`) | dropped | dropped | dropped (plus Hub alias `claimed_amount` → `demand_amount` on correspondence) |

The sandbox does **not** patch `vendor/llm-dojo-scoring` (hub#62
byte-identity). `score_extraction_row` calls `scope_extraction_pair` so
the dojo suite only sees in-schema, non-empty events. Trace-only keys
(`reasoning`, `confidence`) and Hub annotation metadata (`intent_source`,
…) are never scoring events. Content extras (`content_topic`,
`sentiment_label`, `maud_clause_labels`) stay on the pair so
`peel_non_extraction_fields` still sees them.

Numeric zero (`0`, `0.0`, `$0`) is a stated value and still scores.

Offline lock: `tests/test_extraction_scope.py`.

## Prompt variants

`config/prompts/*_local_v0.txt` are shorter, JSON-strict templates for 7B/8B
local models. Pass `--prompt sorter_local_v0` (or `sorter_reviewer_local_v0`,
`judge_local_v0`). Per-agent prompt stems also live under
`config/components.yaml` `prompts:`. Specialist `*_simplified` stems are
**class-specific** (live schema + class traps + class-local empty rules) and
are the eval-environment frozen v1 catalog (`*_v1` keys, sha256-locked in
[`config/prompts/eval_environment_lineage.json`](../config/prompts/eval_environment_lineage.json)).
Isolated specialist evals and Modal + vLLM job runs inject that text —
see [`config/prompts/README.md`](../config/prompts/README.md). Further catalog
re-freezes land in eval-environment, not this repo.

### Any eval-environment prompt version (`--prompt-version`)

The full catalog — all 40 versions (archived `_v0`, frozen `_v1`, 20 mutations) with
memos, what changed between versions, diffs and the exact text — is in
[`docs/prompts/`](prompts/README.md) (generated from the vendored dojo lineage by
`python scripts/render_prompt_catalog.py`; `--check` fails when it drifts). Browse it
from the CLI with `sandbox prompts list-versions [--role R]` and
`sandbox prompts show <key> [--diff <other-key> | --memo]`.

Run an eval or job with any archived (`_v0`), frozen (`_v1`) or mutation
(`correspondence_specialist_v3`, `contracts_specialist_v2`, `sorter_v3`, ...) prompt:

```bash
sandbox eval correspondence_specialist --prompt-version correspondence_specialist=correspondence_specialist_v3
sandbox eval sorter --prompt-version sorter_v3          # bare key: role inferred (<role>_v<N>)
sandbox eval pipeline --prompt-version sorter_v3 --prompt-version contracts_specialist_v2
sandbox run start --config run.yaml --prompt-version correspondence_specialist_v7
```

or in the run spec (`prompt.versions`, a `{role: key}` map or a list of `role=key` /
bare keys; the CLI flag wins per role):

```yaml
prompt:
  versions:
    sorter: sorter_v3
    correspondence_specialist: correspondence_specialist_v3
```

* Texts come from the dojo lineage (`llm_dojo_scoring.prompts.get_prompt_version`)
  through ONE function, `prompt_versions.lookup_prompt_version`. They never come
  from the vendored mailroom registry (`PROMPT_VERSIONS` also has `sorter_v0..v14`:
  same names, other texts) or from `config/prompts/*.txt` (the stem `sorter_v1` is
  the mailroom text, not eval-environment `sorter_v1`).
* An unknown key, a key whose role differs from the one named, a role the pipeline
  lacks (`pipeline_quality_v1`), a text whose sha256 differs from the dojo's, two
  versions for one role, `--prompt` + `--prompt-version` for one role, or a selection
  the task would not use is an error (exit 1, one `error: prompt version: ...` line;
  a job fails preflight with the reason). Nothing falls back to a default.
* The selected key + sha256 are stamped in the run lock (`prompt.agents.<role>` with
  `source: eval-environment`, and `prompt_versions`), are part of `spec_hash` (another
  mutation drifts the lock), and ride on every record: `prompt_version` = the key,
  `prompt_sha256`, `eval_environment_prompt_key`, `prompt_versions` (`{role: {key,
  sha256}}`). A pipeline-level task logs the whole selection (`keyA+keyB` + a digest).
* `prompt_version` and `prompt_sha256` are grouping identity (`serving_groups`):
  different mutations form different legs and never pair, and one name with
  different bytes (eval-env `sorter_v1` vs the mailroom stem) never pools.
* No flag = today's default (the `*_simplified` stems; correspondence / corporate
  records are bytes-equal to eval-environment `_v7` / `_v6`).

## Component gates

`config/components.yaml` enables/disables isolated evals and overlays
confidence routing onto `data/runtime/taxonomy.yaml`. It does not fork the
LangGraph topology.
