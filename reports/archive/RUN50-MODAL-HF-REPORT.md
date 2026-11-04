# DMR-063 — Run-50 report: `run-50-modal-hf` (Qwen/Qwen3-8B · 4×L4 Modal vLLM · HF-secret)

Experiment window: 2026-09-16 ~07:00–08:36 UTC (active compute ≈ 77 min).
Companion: `config/runs/run-50-modal-hf.yaml` (spec.lock.json = the commit point),
`deploy/modal_vllm.py` (v0.29.0, named HF secret), `deploy/teardown_vllm.sh`.

## 1. Run summary

| field | value |
| --- | --- |
| run_id / state | `run-50-modal-hf` / **done** (cursor 50/50, completed 50, run errors 0) |
| spec_hash (locked) | `8c403f3ce7893150292e6c410a4d33e0b1a2814d06001971b83112d79d0f0fda` |
| task / profile / mode | sorter · `modal-vllm` · endpoint (concurrency 16) |
| engine | Modal `sandbox-vllm` — vLLM `vllm/vllm-openai:v0.29.0`, `Qwen/Qwen3-8B`, L4, `max_model_len 16384`, `max_num_seqs 256`, `gpu_memory_utilization 0.90` |
| scale-out | `max_containers: 4`, `scaledown_seconds: 600` (2–3 replicas actually warmed; final stop post-run) |
| dataset | Hub pinned `Lucius-Morningstar/mailroom-dataset` `ground_truth`/`test` @ `46a4d3c240a36671cde0182fff4960f6b8b73aca`; limit 50, seed 42; rows sha256 `a657719ab436` |
| auth | Modal named secret `huggingface-secret` (`HF_TOKEN`, `required_keys`-hydrated; bearer via gitignored `.env`) |
| result | **49/50 = 98.0%** doc-class accuracy; 1 out-of-set misclassification; 0 timeouts, 0 run errors, 0 retries |

The run required **two driver sessions**: attempt A (launched 07:00 UTC) was stopped
at cursor 0 after the pre-fix 120 s call timeout produced `APITimeoutError` retry
storms (root cause: vendored `get_call_timeout_seconds` default of 120 s vs
measured 2.5–3.5 min/generation on L4 — fixed by pinning
`llm_call_timeout_seconds: 300` in the vendored taxonomy + base file, DMR-063).
Attempt B ran to cursor 31, lost its CLI driver (orphaned process death at
07:43:56 UTC — all 31 persisted items intact), and **`sandbox run resume`
re-attached and drove the remaining 19 items to `done`** (08:35:58 UTC). Zero
`APITimeoutError` after the fix, across both sessions.

## 2. Accuracy breakdown

`items.jsonl` (50/50): expected = `expected_doc_class` from `ground_truth`.

| metric | value |
| --- | --- |
| doc-class accuracy | **49/50 = 98.0%** (contract class) |
| misclassified | index 27 · `DOC-5011e1edb6c85cf4` — expected `contract` → predicted `corporate_record` (label **outside** the GT class set → also a classifier boundary signal) |
| subclass coverage | all 50 rows are contract-class, drawn across **19 contract subclasses** (IP 4, Service 6, Supply 4, Co_Branding 5, License 2, Distributor 3, Sponsorship 3, Development 4, Marketing 2, + 10 more) |

Stratification honesty: the `strata: [insurance_claim, contract, merger_agreement]`
constraint could **not stratify** — `expected_doc_class` is constant `contract` in
the joined `ground_truth` config, so the deterministic subsetter drew 50
contract-class rows. The 50-sample is therefore contract-class × 19 subclasses —
not the 3-class mix the spec intended (finding → new card).

## 3. Performance metrics (primary truth: `items.jsonl` + engine logs)

Per-item E2E (includes 16-way queueing behind 4–16 concurrent pipeline graphs):

| latency | value |
| --- | --- |
| mean | 970.9 s (16.2 min) |
| median | 883.2 s (14.7 min) |
| p90 | 1 519.5 s (25.3 min) |
| max | 2 054.1 s (34.2 min) |
| aggregate | 50 docs / ≈77 min active ≈ **0.65 docs/min** across 2–3 warm L4s |
| LLM calls/doc | ~5 serial generations (intake + sorter + reviewers), up to 2048 out-tokens each |

Engine-side (vLLM logger windows during the run): generation throughput
**8.7–13.9 tok/s per engine** (L4, bf16 8B), prompt throughput 170–349 tok/s,
**prefix-cache hit rate 56–58 %**, GPU KV cache ≤ 30 % (idle headroom).
Profile: per-engine generation rate is the binding resource; queueing dominated
per-item E2E at concurrency 16.

Cost (Modal billing): metered **$7.98** ($7.97 deployed apps + $0.01 ephemeral) →
credits −$7.98 → **billed $0.00** (credit-covered). ≈ **$0.16 metered/doc**.
Volumes (`sandbox-hf-cache`, `sandbox-vllm-cache`) persisted by design.

### Comparison: pilot vs 50-sample

| metric | pilot `pilot-sorter-modal-hf` | run-50 `run-50-modal-hf` |
| --- | --- | --- |
| docs (class mix) | 7 (5-class: contract 1, insurance_claim 3, corporate_record 1, merger_agreement 1, correspondence 1) | 50 (contract × 19 subclasses) |
| accuracy | 7/7 = 100 % | 49/50 = 98.0 % |
| engines | 1 × L4  (concurrency 4) | up to 4 × L4 (2–3 warm; concurrency 16) |
| per-item mean E2E | 83 s | 971 s |
| aggregate | ~4.1 docs/min (short fixture docs) | ~0.65 docs/min (full SEC filings, queueing) |
| timeouts / errors | 0 / 0 | 0 / 0 (post-fix) |
| cost share | (within same bill) | $7.98 metered total, $0.00 billed |

Honest caveat: the per-item and aggregate deltas are **confounded by document
size** (fixture snippets vs full filings with 2.5–11.4 k chars) and queueing
(concurrency 4 vs 16); they are serving-architecture numbers, not a clean
model-quality delta. Quality signal that survives the confound: both runs are
≥98 % accurate on their class surfaces.

## 4. Degraded/noted surfaces (non-fatal, logged, all loud)

- `sqlalchemy` absent from the sandbox `[pipeline]` extra → vendored
  `storage.catalog` / `storage.audit_log` imports fail; `catalog_upsert_error` /
  `latest_audit_hash_fetch_failed` errors are caught in-graph and the sorter
  surface completes (49/50 rows; 0 run errors). Fix: add `sqlalchemy` to the
  `[pipeline]` extra (finding card spawned).
- `vendored llm.prompts not importable … static roster (18 agents)` — same
  sqlalchemy root cause; no prompt-surface impact on pinned `code-default` +
  local variants.
- `config/mailroom.taxonomy.base.yaml` is shadowed by the vendored taxonomy file
  when present (taxonomy precedence); both are kept in sync (300 s) and a
  precedence note/pin test landed with DMR-063. Runs must bump the **vendored**
  file or the fix silently no-ops.

## 5. Findings → spawned cards

1. Stratification no-op: `expected_doc_class` constant in `ground_truth` — the
   sorter stratum constraint cannot stratify; 19-subclass coverage is the real
   diversity. Next: subclass-stratified run (19-vocab) or multi-class fixture
   strata (5-class docclass_mini-style).
2. Missing `sqlalchemy` in the sandbox pipeline extra → degraded storage/catalog
   surface; add it + re-run a row with the full surface.
3. Scale-out flatness at 4 × L4: aggregate did not 4× (per-engine ~12 tok/s
   generation is the wall; client concurrency 16 + ~5 serial calls/doc fill and
   queue; engines at 2–3 warm replicas). Next probe: concurrency 32–64,
   AWQ/int8 row, and a fixed-doc-size scale matrix (1 vs 2 vs 4 L4).
4. Teardown headless gap → `deploy/teardown_vllm.sh` now passes `--yes` when
   non-TTY (this report's session used the manual `-y` path; script verified).

## 6. Evidence trail

- `data/runtime/runs/run-50-modal-hf/` — `spec.lock.json`, `items.jsonl`
  (50 rows, per-item ts/latency/correctness/trace_id), `checkpoint.json`
  (done 50/50), `events.jsonl` (item_done … done cursor 50 ok_count 19).
- `reports/experiment_log.jsonl` — `run-50-modal-hf` entry
  (task sorter · mock false · serving_kind modal · n 50).
- Engine logs (`modal app logs sandbox-vllm`) — 200-only responses, throughput +
  prefix-cache windows above; `modal container list`/`app list` — stopped,
  0 containers post-teardown.
- Billing: `modal billing summary` (metered $7.98 / billed $0.00).