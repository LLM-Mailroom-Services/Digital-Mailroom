# Run report — `sand032-s5-merger50-maud`

SAND-032 Modal × vLLM specialist extract: **50 merger_agreement docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 32** on **2×L4** (MIN=MAX=2 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s5-merger50-maud` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_maud_v1` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel replicas) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=16 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16], max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 2/2, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 50 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `23c90708536e` |
| git | `7d7f560 (dirty)` |
| spec_hash | `d88cdb640195e2c3bf12815f6db79fb67f1139e9782bd4024f92c706fece2454` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **46 / 50** (errors 4) |
| **overall_extraction_score** | **0.0830** (sd 0.0662, min 0.0000, max 0.3333) |
| schema_valid_rate | 1.000 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 442.470 s |
| concurrency | 32 (16 per replica) |
| cold boot — deploy→engine ready (driver stamps) | 125.5 s |
| preflight probe (engine answering) | 122.761 s |
| latency p50 / p95 / max | 183.45 / 315.19 / 364.92 s |
| prompt / completion tokens | 562999 / 49105 |
| throughput | 1383.4 tok/s |
| GPU $ over busy wall (×2 L4 @ $0.8/h) | 0.196653 |
| **$ per doc (busy)** | **0.004275** |
| fleet window deploy→stop (upper est.) | 593 s → 0.2635 USD |
| cost cap | $1.4 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 2 of 2** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790548269.81`: requests Δ 41 (cumulative 41), measured TTFT mean 95.588 s (vLLM histogram, cumulative), prefix-cache hit 30.8%, preemptions 0, length-capped finishes 3, KV usage at scrape 0%.
- replica `1790548270.71`: requests Δ 9 (cumulative 9), measured TTFT mean 3.401 s (vLLM histogram, cumulative), prefix-cache hit 28.0%, preemptions 0, length-capped finishes 1, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 8268.7 s over wall 442.5 s = **18.69×** effective parallelism at c32 (58% of the ideal 32×).
- **Tail:** slowest doc `DOC-be8461dd68cfe458` (all_stock) 364.9 s = 82% of wall — p95/p50 = 1.72×.
- **Prompt length vs latency:** Pearson r = 0.13 across 46 docs (not prefill-dominated).
- **Decode budget:** mean completion 1068 tok/doc, mean prompt 12239 tok/doc.
- **Subclass spread:** best `all_cash` 0.094 (n=19), worst `other` 0.063 (n=13).
- **Field-level extraction:** 46/46 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.
- **Boot:** deploy→engine-ready 125 s (driver stamps); preflight probe measured 122.8 s once the engine answered.

## Scoring method — MAUD answer accuracy

The pinned Hub merger rows carry ground truth only as `maud_clause_labels` (LegalBench MAUD question → answer). The suite field map scores document_name/parties/…, which those rows never populate, so field F1 is 0 by construction. The headline here is **per-question MAUD accuracy** (`src/mailroom_sandbox/eval/maud_scoring.py`); an unanswered question counts as wrong.

| metric | value |
| --- | --- |
| labeled MAUD questions | 755 |
| answered | 249 (33.0% coverage) |
| correct | 64 → **micro accuracy 8.5%** |
| precision on answered | 25.7% |
| clean subset (single MAUD sub-question per name) | 35/328 = 10.7% |

**Dataset caveat:** the corpus collapses several MAUD sub-questions under one name (e.g. `No-Shop` answers include `Yes`, `Strict liability`, `Reasonable standard`), so a per-doc target on those names is ambiguous; the clean subset excludes them.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s5-merger50-maud-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s5-merger50-maud-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| all_cash | 19 | 0.0943 |
| other | 13 | 0.0628 |
| all_stock | 10 | 0.0878 |
| mixed_cash_stock | 4 | 0.0835 |
| **total** | **46** | **0.0830** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-038a485469f83c9a` | all_stock | 0.0625 | 0.0000 | ✓ | 101.1 | 12190 | 699 |  |
| 2 | `DOC-fc07b37a0f0d1234` | mixed_cash_stock | 0.0625 | 0.0000 | ✓ | 107.4 | 12072 | 691 |  |
| 3 | `DOC-511062d64bc9afc6` | other | 0.0625 | 0.0000 | ✓ | 112.7 | 12231 | 704 |  |
| 4 | `DOC-45f801408be08af6` | all_stock | 0.0667 | 0.0000 | ✓ | 119.4 | 13102 | 786 |  |
| 5 | `DOC-37026835107f9684` | all_stock | 0.0000 | 0.0000 | ✓ | 120.9 | 12359 | 780 |  |
| 6 | `DOC-5fbb9ee2f4b4b114` | other | 0.0588 | 0.0000 | ✓ | 124.7 | 12117 | 765 |  |
| 7 | `DOC-7430de65e5471741` | all_cash | 0.1579 | 0.0000 | ✓ | 125.7 | 11941 | 816 |  |
| 8 | `DOC-5fa0ba13cf68b593` | other | 0.0667 | 0.0000 | ✓ | 132.7 | 12133 | 791 |  |
| 9 | `DOC-8a0bdfe3d16c33b2` | all_cash | 0.0588 | 0.0000 | ✓ | 137.1 | 12264 | 793 |  |
| 10 | `DOC-1e016055aa435e71` | other | 0.0000 | 0.0000 | ✓ | 40.7 | 11985 | 791 |  |
| 11 | `DOC-c1d57615929b483e` | mixed_cash_stock | 0.0625 | 0.0000 | ✓ | 144.3 | 12060 | 874 |  |
| 12 | `DOC-c96b9c7e12f91576` | other | 0.0000 | 0.0000 | ✓ | 149.5 | 12474 | 884 |  |
| 13 | `DOC-63beb09b179ea4ee` | all_cash | 0.0588 | 0.0000 | ✓ | 42.8 | 12301 | 838 |  |
| 14 | `DOC-8f599c800d19fd92` | all_cash | 0.0000 | 0.0000 | ✓ | 160.5 | 12010 | 1018 |  |
| 15 | `DOC-d5c4f12f934de48e` | other | 0.1053 | 0.0000 | ✓ | 44.1 | 12406 | 835 |  |
| 16 | `DOC-5c44797b6add60e4` | all_cash | 0.0667 | 0.0000 | ✓ | 40.8 | 12213 | 797 |  |
| 17 | `DOC-26fa94f698c37fc5` | all_cash | 0.0588 | 0.0000 | ✓ | 38.0 | 11957 | 805 |  |
| 18 | `DOC-f099c5c73d56631e` | other | 0.0667 | 0.0000 | ✓ | 71.1 | 12998 | 1519 |  |
| 19 | `DOC-fcaddb5bdc94ce63` | all_cash | 0.1765 | 0.0000 | ✓ | 43.2 | 12084 | 979 |  |
| 20 | `DOC-52f9a5be69429299` | mixed_cash_stock | 0.0588 | 0.0000 | ✓ | 205.6 | 12405 | 709 |  |
| 21 | `DOC-f546c7d6cf2e77e2` | all_cash | 0.0526 | 0.0000 | ✓ | 30.3 | 11709 | 893 |  |
| 22 | `DOC-d0495abfa5f3d8ee` | all_stock | 0.0000 | 0.0000 | ✓ | 214.4 | 11931 | 730 |  |
| 23 | `DOC-d554890e66786170` | all_cash | 0.1250 | 0.0000 | ✓ | 217.7 | 13442 | 938 |  |
| 24 | `DOC-1252fb5690e17c7b` | all_cash | 0.1111 | 0.0000 | ✓ | 222.6 | 12223 | 725 |  |
| 25 | `DOC-d01014aed8ad8824` | other | 0.0625 | 0.0000 | ✓ | 230.5 | 12415 | 897 |  |
| 26 | `DOC-0a733ab86f2390ae` | all_cash | 0.0667 | 0.0000 | ✓ | 234.3 | 11738 | 902 |  |
| 27 | `DOC-15f85636d1eb6b77` | all_cash | 0.0667 | 0.0000 | ✓ | 238.7 | 12448 | 985 |  |
| 28 | `DOC-ecf69d7e102ef62a` | other | 0.1429 | 0.0000 | ✓ | 240.3 | 12185 | 1751 |  |
| 29 | `DOC-4ab4ecd86ecf275d` | all_stock | 0.1875 | 0.0000 | ✓ | 253.7 | 12594 | 1055 |  |
| 30 | `DOC-8c661a1693d4655b` | other | 0.1333 | 0.0000 | ✓ | 258.0 | 12276 | 845 |  |
| 31 | `DOC-3927f91bc3daffc3` | all_cash | 0.0625 | 0.0000 | ✓ | 262.0 | 12691 | 1080 |  |
| 32 | `DOC-169bbcdc5d9e609c` | all_stock | — | — | ✗ | 120.9 | None | None | LengthFinishReasonError: Could not parse response content as |
| 33 | `DOC-62456d43b50f73fa` | all_stock | 0.2500 | 0.0000 | ✓ | 290.0 | 12609 | 2209 |  |
| 34 | `DOC-f4e726a7f2c25494` | all_stock | 0.1333 | 0.0000 | ✓ | 298.0 | 12408 | 721 |  |
| 35 | `DOC-2f9cf3ce009aaaf0` | all_cash | 0.0588 | 0.0000 | ✓ | 189.5 | 11905 | 651 |  |
| 36 | `DOC-30eda1e78a5f6fb5` | all_stock | 0.1111 | 0.0000 | ✓ | 311.2 | 12048 | 752 |  |
| 37 | `DOC-eb2b56fe30dc35f4` | all_cash | 0.1176 | 0.0000 | ✓ | 313.6 | 11897 | 809 |  |
| 38 | `DOC-f90cc5fb2ceac154` | mixed_cash_stock | 0.1500 | 0.0000 | ✓ | 315.2 | 12455 | 2465 |  |
| 39 | `DOC-2b9f668ab6cb8901` | all_cash | 0.0526 | 0.0000 | ✓ | 201.3 | 11833 | 899 |  |
| 40 | `DOC-03712a2b0a99a314` | all_stock | 0.0000 | 0.0000 | ✓ | 188.6 | 12276 | 853 |  |
| 41 | `DOC-d1e355800bff0425` | other | 0.0000 | 0.0000 | ✓ | 172.4 | 12065 | 866 |  |
| 42 | `DOC-fd6090e354177e5b` | all_cash | 0.0556 | 0.0000 | ✓ | 185.5 | 11829 | 921 |  |
| 43 | `DOC-ab735131c00271bc` | all_cash | 0.1111 | 0.0000 | ✓ | 167.0 | 11708 | 795 |  |
| 44 | `DOC-882fabf7aba36941` | other | 0.1176 | 0.0000 | ✓ | 361.7 | 12480 | 2646 |  |
| 45 | `DOC-be8461dd68cfe458` | all_stock | 0.0667 | 0.0000 | ✓ | 364.9 | 12090 | 3423 |  |
| 46 | `DOC-bec74557186e9409` | other | 0.0000 | 0.0000 | ✓ | 263.7 | 12394 | 1896 |  |
| 47 | `DOC-b866e2b4f5059213` | all_cash | 0.3333 | 0.0000 | ✓ | 181.4 | 12048 | 1524 |  |
| 48 | `DOC-eac7882cff200545` | other | — | — | ✗ | 414.4 | None | None | LengthFinishReasonError: Could not parse response content as |
| 49 | `DOC-74a69c5b3cdf1afc` | all_stock | — | — | ✗ | 439.1 | None | None | LengthFinishReasonError: Could not parse response content as |
| 50 | `DOC-8fe2855a2310cdbe` | mixed_cash_stock | — | — | ✗ | 309.6 | None | None | LengthFinishReasonError: Could not parse response content as |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s5-merger50-maud.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s5-merger50-maud
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s5-merger50-maud.yaml` | run spec |
| `reports/serving/sand032-s5-merger50-maud.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s5-merger50-maud/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s5-merger50-maud/` | offline Braintrust-shaped rows — disposed after this report is committed |
