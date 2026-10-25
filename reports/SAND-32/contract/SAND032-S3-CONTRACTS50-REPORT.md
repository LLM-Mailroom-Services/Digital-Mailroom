# Run report — `sand032-s3-contracts50`

SAND-032 Modal × vLLM specialist extract: **50 contract docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 32** on **2×L4** (MIN=MAX=2 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s3-contracts50` |
| task / agent | `contracts_specialist` |
| prompt | `contracts_specialist_v33_simplified` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel replicas) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=16 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16], max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 2/2, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 50 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `c29633d769b5` |
| git | `d2bb4ef (dirty)` |
| spec_hash | `d3a7e840182bf09d6c7e7d9209975d09ea98f28cd17be33e77bed9ae6f05bb18` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **47 / 50** (errors 3) |
| **overall_extraction_score** | **0.6011** (sd 0.1092, min 0.3571, max 0.8571) |
| schema_valid_rate | 1.000 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 234.311 s |
| concurrency | 32 (16 per replica) |
| cold boot — deploy→engine ready (driver stamps) | — |
| preflight probe (engine answering) | 0.192 s |
| latency p50 / p95 / max | 85.75 / 167.54 / 182.26 s |
| prompt / completion tokens | 303486 / 75157 |
| throughput | 1616.0 tok/s |
| GPU $ over busy wall (×2 L4 @ $0.8/h) | 0.104138 |
| **$ per doc (busy)** | **0.002216** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $1.4 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 2 of 2** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790546353.94`: requests Δ 22 (cumulative 300), measured TTFT mean 7.016 s (vLLM histogram, cumulative), prefix-cache hit 48.9%, preemptions 0, length-capped finishes 7, KV usage at scrape 0%.
- replica `1790546749.43`: requests Δ 28 (cumulative 170), measured TTFT mean 7.170 s (vLLM histogram, cumulative), prefix-cache hit 37.8%, preemptions 0, length-capped finishes 2, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 4409.9 s over wall 234.3 s = **18.82×** effective parallelism at c32 (59% of the ideal 32×).
- **Tail:** slowest doc `DOC-962cc639f3ebee80` (License_Agreements) 182.3 s = 78% of wall — p95/p50 = 1.95×.
- **Prompt length vs latency:** Pearson r = 0.01 across 47 docs (not prefill-dominated).
- **Decode budget:** mean completion 1599 tok/doc, mean prompt 6457 tok/doc.
- **Subclass spread:** best `Joint Venture _ Filing` 0.857 (n=1), worst `Marketing` 0.357 (n=1).
- **Field-level extraction:** 47/47 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.

## Scoring method — CUAD clause detection

The pinned Hub contract rows carry ground truth only as `cuad_clause_labels` (CUAD category → annotated spans). The suite field map never meets them, so field F1 was 0 and the overall score null by construction. The headline here is **per-doc CUAD category-presence F1** within each row's labeled universe (`src/mailroom_sandbox/eval/cuad_scoring.py`).

| metric | value |
| --- | --- |
| docs with CUAD labels (scored) | 38 of 47 ok |
| micro precision / recall / F1 | 0.658 / 0.545 / **0.596** |
| metadata value checks (name, parties, governing law) | 67/105 = 63.8% |
| predicted categories outside the labeled universe (ignored, scored docs) | 169 |

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s3-contracts50-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s3-contracts50-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| Supply | 5 | 0.6198 |
| Maintenance | 4 | 0.5875 |
| Co_Branding | 4 | 0.5696 |
| Sponsorship | 3 | 0.7289 |
| Endorsement | 3 | 0.5684 |
| Development | 3 | 0.5164 |
| Strategic Alliance | 3 | 0.5972 |
| Hosting | 2 | 0.6543 |
| Joint Venture _ Filing | 1 | 0.8571 |
| License_Agreements | 1 | 0.6000 |
| Marketing | 1 | 0.3571 |
| Service | 1 | 0.6667 |
| Reseller | 1 | 0.6061 |
| Distributor | 1 | 0.6207 |
| Agency Agreements | 1 | 0.6429 |
| Franchise | 1 | 0.5556 |
| IP | 1 | 0.5882 |
| Joint Venture | 1 | 0.4828 |
| Promotion | 1 | 0.5946 |
| **total** | **38** | **0.6011** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-98ff556893f1a98f` | Joint Venture _ Filing | 0.8571 | 0.0000 | ✓ | 31.5 | 3200 | 330 |  |
| 2 | `DOC-6712aa595cfe3e2c` | Supply | 0.5714 | 0.0000 | ✓ | 53.6 | 6549 | 785 |  |
| 3 | `DOC-9696c5996f24d85d` | Consulting Agreements | — | 0.0000 | ✓ | 59.1 | 4377 | 864 |  |
| 4 | `DOC-fca31a55b1d526ea` | Supply | 0.7273 | 0.0000 | ✓ | 67.0 | 5459 | 1017 |  |
| 5 | `DOC-c30c293d38a2cd8b` | Maintenance | 0.6923 | 0.0000 | ✓ | 74.3 | 8376 | 1120 |  |
| 6 | `DOC-34904aee099a62c7` | License_Agreements | 0.6000 | 0.0000 | ✓ | 78.1 | 6857 | 1118 |  |
| 7 | `DOC-440a54573c24b918` | Maintenance | 0.4000 | 0.0000 | ✓ | 79.9 | 3493 | 1228 |  |
| 8 | `DOC-2e3e2bb13d6c83ca` | IP | — | 0.0000 | ✓ | 82.2 | 10731 | 1161 |  |
| 9 | `DOC-25f822c661011bfe` | Marketing | 0.3571 | 0.0000 | ✓ | 82.3 | 6620 | 1249 |  |
| 10 | `DOC-15262384b17086bb` | Sponsorship | 0.7200 | 0.0000 | ✓ | 83.1 | 6858 | 1237 |  |
| 11 | `DOC-c7f557969d953fae` | Supply | — | 0.0000 | ✓ | 85.4 | 6777 | 1251 |  |
| 12 | `DOC-ba6d7a0ea5100bbb` | Service | 0.6667 | 0.0000 | ✓ | 85.7 | 6637 | 1266 |  |
| 13 | `DOC-83320eec5eec6235` | Reseller | 0.6061 | 0.0000 | ✓ | 85.8 | 6720 | 1224 |  |
| 14 | `DOC-4be26020b0470e43` | Sponsorship | 0.6667 | 0.0000 | ✓ | 88.0 | 6346 | 1284 |  |
| 15 | `DOC-9b569749ea3d6f42` | Supply | — | 0.0000 | ✓ | 90.9 | 8481 | 1265 |  |
| 16 | `DOC-ea746c407db93af2` | Supply | — | 0.0000 | ✓ | 92.1 | 4804 | 1026 |  |
| 17 | `DOC-770401d1d47fd744` | Distributor | 0.6207 | 0.0000 | ✓ | 93.1 | 6647 | 1299 |  |
| 18 | `DOC-55df050fcb737129` | Endorsement | 0.5714 | 0.0000 | ✓ | 98.8 | 5461 | 1382 |  |
| 19 | `DOC-e235bc9735f96335` | Agency Agreements | 0.6429 | 0.0000 | ✓ | 99.2 | 6267 | 1471 |  |
| 20 | `DOC-c68a4dd90660c113` | Endorsement | 0.6154 | 0.0000 | ✓ | 71.8 | 6692 | 1183 |  |
| 21 | `DOC-adad5ef793c0e409` | Co_Branding | 0.5185 | 0.0000 | ✓ | 107.6 | 7011 | 1628 |  |
| 22 | `DOC-09c0c774c3e5ec74` | Supply | 0.5333 | 0.0000 | ✓ | 112.8 | 7294 | 1638 |  |
| 23 | `DOC-93e9bb030e2b282d` | Development | 0.5455 | 0.0000 | ✓ | 62.0 | 7333 | 987 |  |
| 24 | `DOC-8a776dec500b074c` | Franchise | 0.5556 | 0.0000 | ✓ | 44.5 | 7030 | 690 |  |
| 25 | `DOC-ade03c57c5f78e21` | Maintenance | 0.7059 | 0.0000 | ✓ | 119.9 | 4093 | 1900 |  |
| 26 | `DOC-06229aa6571f9d46` | Strategic Alliance | 0.6250 | 0.0000 | ✓ | 44.5 | 6154 | 741 |  |
| 27 | `DOC-2ca7b08d2d439f1e` | Service | — | 0.0000 | ✓ | 124.6 | 6344 | 1997 |  |
| 28 | `DOC-f9b36fee351217c2` | IP | 0.5882 | 0.0000 | ✓ | 58.7 | 6757 | 892 |  |
| 29 | `DOC-ee4369c8980926dc` | Development | 0.6286 | 0.0000 | ✓ | 132.4 | 6849 | 2064 |  |
| 30 | `DOC-e492894fbfa36087` | Co_Branding | 0.4000 | 0.0000 | ✓ | 47.2 | 6821 | 926 |  |
| 31 | `DOC-03f1f6c0db99e651` | Strategic Alliance | 0.5000 | 0.0000 | ✓ | 79.3 | 6833 | 1321 |  |
| 32 | `DOC-9e063c6e3baf1233` | Supply | 0.5714 | 0.0000 | ✓ | 142.4 | 6953 | 2312 |  |
| 33 | `DOC-364e40f0752551a3` | Joint Venture | 0.4828 | 0.0000 | ✓ | 60.4 | 8770 | 1164 |  |
| 34 | `DOC-5892b6dc609c8d0f` | Affiliate_Agreements | — | 0.0000 | ✓ | 147.0 | 6733 | 2411 |  |
| 35 | `DOC-c2ac5762c7f227fa` | License_Agreements | — | 0.0000 | ✓ | 150.4 | 6999 | 2518 |  |
| 36 | `DOC-561364d531fca179` | Endorsement | 0.5185 | 0.0000 | ✓ | 65.2 | 6399 | 1456 |  |
| 37 | `DOC-e853a8ab86c5a54d` | Strategic Alliance | 0.6667 | 0.0000 | ✓ | 80.0 | 4692 | 1728 |  |
| 38 | `DOC-d66d8f6c92207c3c` | Co_Branding | 0.6250 | 0.0000 | ✓ | 167.5 | 4746 | 3084 |  |
| 39 | `DOC-a2ce7adbf6f5cb8d` | Hosting | 0.7000 | 0.0000 | ✓ | 83.6 | 6520 | 1908 |  |
| 40 | `DOC-0de76b97986b57b3` | Development | 0.3750 | 0.0000 | ✓ | 90.0 | 6581 | 1972 |  |
| 41 | `DOC-f717fb61aa615da0` | Co_Branding | 0.7347 | 0.0000 | ✓ | 175.9 | 6958 | 2556 |  |
| 42 | `DOC-dfa5c8eb1e7b837c` | Supply | 0.6957 | 0.0000 | ✓ | 90.4 | 6055 | 2059 |  |
| 43 | `DOC-4ab8d1d37d3af05c` | Hosting | 0.6087 | 0.0000 | ✓ | 98.9 | 6463 | 2154 |  |
| 44 | `DOC-962cc639f3ebee80` | License_Agreements | — | 0.0000 | ✓ | 182.3 | 6071 | 2692 |  |
| 45 | `DOC-54ad252b1e5e8d58` | Manufacturing | — | — | ✗ | 199.2 | None | None | LengthFinishReasonError: Could not parse response content as |
| 46 | `DOC-99ca00712a84f039` | Outsourcing | — | — | ✗ | 199.1 | None | None | LengthFinishReasonError: Could not parse response content as |
| 47 | `DOC-d1c45d175a8abeb5` | Sponsorship | 0.8000 | 0.0000 | ✓ | 107.7 | 6841 | 2759 |  |
| 48 | `DOC-f333c4b8048d5d8c` | Promotion | 0.5946 | 0.0000 | ✓ | 121.0 | 6732 | 3287 |  |
| 49 | `DOC-9a2c7cc21a860fc4` | Maintenance | 0.5517 | 0.0000 | ✓ | 132.0 | 6102 | 3553 |  |
| 50 | `DOC-01633b99e74dc9f2` | Sponsorship | — | — | ✗ | 135.3 | None | None | LengthFinishReasonError: Could not parse response content as |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s3-contracts50.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s3-contracts50
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s3-contracts50.yaml` | run spec |
| `reports/serving/sand032-s3-contracts50.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s3-contracts50/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s3-contracts50/` | offline Braintrust-shaped rows — disposed after this report is committed |
