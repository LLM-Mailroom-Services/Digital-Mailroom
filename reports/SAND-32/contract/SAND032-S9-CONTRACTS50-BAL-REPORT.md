# Run report — `sand032-s9-contracts50-bal`

SAND-032 Modal × vLLM specialist extract: **50 contract docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 64** on **2×L4** (MIN=MAX=2 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s9-contracts50-bal` |
| task / agent | `contracts_specialist` |
| prompt | `contracts_specialist_v33_simplified` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel replicas) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=32 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16, 32], max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 2/2, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 50 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `c29633d769b5` |
| git | `37e5f98 (dirty)` |
| spec_hash | `096b0afce76dd6319191081f6cf5f5eaa8a0f4841f22129341cd60469858e567` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **44 / 50** (errors 6) |
| **overall_extraction_score** | **0.5907** (sd 0.1241, min 0.3448, max 0.8571) |
| schema_valid_rate | 1.000 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 219.530 s |
| concurrency | 64 (32 per replica) |
| cold boot — deploy→engine ready (driver stamps) | — |
| preflight probe (engine answering) | 0.334 s |
| latency p50 / p95 / max | 109.81 / 186.88 / 217.36 s |
| prompt / completion tokens | 278595 / 66259 |
| throughput | 1570.9 tok/s |
| GPU $ over busy wall (×2 L4 @ $0.8/h) | 0.097569 |
| **$ per doc (busy)** | **0.002217** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $1.4 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 2 of 2** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790582921.77`: requests Δ 22 (cumulative 115), measured TTFT mean 8.249 s (vLLM histogram, cumulative), prefix-cache hit 42.8%, preemptions 0, length-capped finishes 3, KV usage at scrape 0%.
- replica `1790582929.28`: requests Δ 28 (cumulative 135), measured TTFT mean 11.179 s (vLLM histogram, cumulative), prefix-cache hit 43.2%, preemptions 0, length-capped finishes 3, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 5096.3 s over wall 219.5 s = **23.21×** effective parallelism at c64 (36% of the ideal 64×).
- **Tail:** slowest doc `DOC-99ca00712a84f039` (Outsourcing) 217.4 s = 99% of wall — p95/p50 = 1.70×.
- **Prompt length vs latency:** Pearson r = 0.04 across 44 docs (not prefill-dominated).
- **Decode budget:** mean completion 1506 tok/doc, mean prompt 6332 tok/doc.
- **Subclass spread:** best `Joint Venture _ Filing` 0.857 (n=1), worst `Franchise` 0.345 (n=1).
- **Field-level extraction:** 44/44 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.

## Scoring method — CUAD clause detection

The pinned Hub contract rows carry ground truth only as `cuad_clause_labels` (CUAD category → annotated spans). The suite field map never meets them, so field F1 was 0 and the overall score null by construction. The headline here is **per-doc CUAD category-presence F1** within each row's labeled universe (`src/mailroom_sandbox/eval/cuad_scoring.py`).

| metric | value |
| --- | --- |
| docs with CUAD labels (scored) | 38 of 44 ok |
| micro precision / recall / F1 | 0.681 / 0.491 / **0.570** |
| metadata value checks (name, parties, governing law) | 69/106 = 65.1% |
| predicted categories outside the labeled universe (ignored, scored docs) | 173 |

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s9-contracts50-bal-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s9-contracts50-bal-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| Supply | 5 | 0.6343 |
| Co_Branding | 4 | 0.4708 |
| Sponsorship | 4 | 0.5908 |
| Endorsement | 3 | 0.5703 |
| Development | 3 | 0.4797 |
| Maintenance | 3 | 0.7389 |
| Strategic Alliance | 2 | 0.5903 |
| Hosting | 2 | 0.6833 |
| Joint Venture _ Filing | 1 | 0.8571 |
| Promotion | 1 | 0.6364 |
| Service | 1 | 0.7143 |
| Franchise | 1 | 0.3448 |
| Reseller | 1 | 0.6667 |
| License_Agreements | 1 | 0.6667 |
| Marketing | 1 | 0.4138 |
| Agency Agreements | 1 | 0.5926 |
| IP | 1 | 0.4800 |
| Distributor | 1 | 0.6429 |
| Joint Venture | 1 | 0.5000 |
| Outsourcing | 1 | 0.6000 |
| **total** | **38** | **0.5907** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-98ff556893f1a98f` | Joint Venture _ Filing | 0.8571 | 0.0000 | ✓ | 44.2 | 3200 | 319 |  |
| 2 | `DOC-2e3e2bb13d6c83ca` | IP | — | 0.0000 | ✓ | 58.0 | 10731 | 570 |  |
| 3 | `DOC-f333c4b8048d5d8c` | Promotion | 0.6364 | 0.0000 | ✓ | 76.5 | 6732 | 656 |  |
| 4 | `DOC-06229aa6571f9d46` | Strategic Alliance | 0.6250 | 0.0000 | ✓ | 80.4 | 6154 | 739 |  |
| 5 | `DOC-ba6d7a0ea5100bbb` | Service | 0.7143 | 0.0000 | ✓ | 82.3 | 6637 | 754 |  |
| 6 | `DOC-55df050fcb737129` | Endorsement | 0.6154 | 0.0000 | ✓ | 83.9 | 5461 | 1039 |  |
| 7 | `DOC-93e9bb030e2b282d` | Development | 0.5455 | 0.0000 | ✓ | 86.0 | 7333 | 1086 |  |
| 8 | `DOC-9696c5996f24d85d` | Consulting Agreements | — | 0.0000 | ✓ | 91.7 | 4377 | 1192 |  |
| 9 | `DOC-e492894fbfa36087` | Co_Branding | 0.4000 | 0.0000 | ✓ | 92.4 | 6821 | 917 |  |
| 10 | `DOC-8a776dec500b074c` | Franchise | 0.3448 | 0.0000 | ✓ | 93.8 | 7030 | 1214 |  |
| 11 | `DOC-83320eec5eec6235` | Reseller | 0.6667 | 0.0000 | ✓ | 94.5 | 6720 | 930 |  |
| 12 | `DOC-440a54573c24b918` | Maintenance | 0.8000 | 0.0000 | ✓ | 95.4 | 3493 | 931 |  |
| 13 | `DOC-ea746c407db93af2` | Supply | — | 0.0000 | ✓ | 95.7 | 4804 | 978 |  |
| 14 | `DOC-561364d531fca179` | Endorsement | 0.4800 | 0.0000 | ✓ | 96.6 | 6399 | 978 |  |
| 15 | `DOC-34904aee099a62c7` | License_Agreements | 0.6667 | 0.0000 | ✓ | 96.7 | 6857 | 1297 |  |
| 16 | `DOC-c7f557969d953fae` | Supply | — | 0.0000 | ✓ | 97.3 | 6777 | 1290 |  |
| 17 | `DOC-f717fb61aa615da0` | Co_Branding | 0.4667 | 0.0000 | ✓ | 98.7 | 6958 | 1305 |  |
| 18 | `DOC-962cc639f3ebee80` | License_Agreements | — | 0.0000 | ✓ | 98.9 | 6071 | 1337 |  |
| 19 | `DOC-01633b99e74dc9f2` | Sponsorship | 0.5000 | 0.0000 | ✓ | 104.0 | 6805 | 1085 |  |
| 20 | `DOC-d66d8f6c92207c3c` | Co_Branding | 0.6000 | 0.0000 | ✓ | 104.4 | 4746 | 1451 |  |
| 21 | `DOC-25f822c661011bfe` | Marketing | 0.4138 | 0.0000 | ✓ | 105.7 | 6620 | 1481 |  |
| 22 | `DOC-adad5ef793c0e409` | Co_Branding | 0.4167 | 0.0000 | ✓ | 109.0 | 7011 | 1180 |  |
| 23 | `DOC-e235bc9735f96335` | Agency Agreements | 0.5926 | 0.0000 | ✓ | 110.8 | 6267 | 1598 |  |
| 24 | `DOC-ee4369c8980926dc` | Development | 0.5185 | 0.0000 | ✓ | 110.7 | 6849 | 1595 |  |
| 25 | `DOC-9a2c7cc21a860fc4` | Maintenance | 0.6667 | 0.0000 | ✓ | 112.8 | 6102 | 1258 |  |
| 26 | `DOC-09c0c774c3e5ec74` | Supply | 0.4167 | 0.0000 | ✓ | 113.4 | 7294 | 1239 |  |
| 27 | `DOC-e853a8ab86c5a54d` | Strategic Alliance | 0.5556 | 0.0000 | ✓ | 115.2 | 4692 | 1738 |  |
| 28 | `DOC-a2ce7adbf6f5cb8d` | Hosting | 0.7000 | 0.0000 | ✓ | 116.3 | 6520 | 1764 |  |
| 29 | `DOC-4be26020b0470e43` | Sponsorship | 0.6316 | 0.0000 | ✓ | 117.8 | 6346 | 1355 |  |
| 30 | `DOC-6712aa595cfe3e2c` | Supply | 0.5833 | 0.0000 | ✓ | 119.2 | 6549 | 1363 |  |
| 31 | `DOC-5892b6dc609c8d0f` | Affiliate_Agreements | — | 0.0000 | ✓ | 130.7 | 6733 | 1595 |  |
| 32 | `DOC-ade03c57c5f78e21` | Maintenance | 0.7500 | 0.0000 | ✓ | 130.6 | 4093 | 1614 |  |
| 33 | `DOC-4ab8d1d37d3af05c` | Hosting | 0.6667 | 0.0000 | ✓ | 132.3 | 6463 | 1615 |  |
| 34 | `DOC-f9b36fee351217c2` | IP | 0.4800 | 0.0000 | ✓ | 135.7 | 6757 | 1696 |  |
| 35 | `DOC-770401d1d47fd744` | Distributor | 0.6429 | 0.0000 | ✓ | 141.7 | 6647 | 1851 |  |
| 36 | `DOC-dfa5c8eb1e7b837c` | Supply | 0.7500 | 0.0000 | ✓ | 142.6 | 6055 | 2523 |  |
| 37 | `DOC-d1c45d175a8abeb5` | Sponsorship | 0.6316 | 0.0000 | ✓ | 143.6 | 6841 | 1915 |  |
| 38 | `DOC-c68a4dd90660c113` | Endorsement | 0.6154 | 0.0000 | ✓ | 157.8 | 6692 | 2298 |  |
| 39 | `DOC-364e40f0752551a3` | Joint Venture | 0.5000 | 0.0000 | ✓ | 159.6 | 8770 | 638 |  |
| 40 | `DOC-15262384b17086bb` | Sponsorship | 0.6000 | 0.0000 | ✓ | 159.9 | 6858 | 3045 |  |
| 41 | `DOC-0de76b97986b57b3` | Development | 0.3750 | 0.0000 | ✓ | 161.1 | 6581 | 2378 |  |
| 42 | `DOC-fca31a55b1d526ea` | Supply | 0.8333 | 0.0000 | ✓ | 186.9 | 5459 | 3090 |  |
| 43 | `DOC-03f1f6c0db99e651` | Strategic Alliance | — | — | ✗ | 191.5 | None | None | LengthFinishReasonError: Could not parse response content as |
| 44 | `DOC-9b569749ea3d6f42` | Supply | — | — | ✗ | 191.9 | None | None | LengthFinishReasonError: Could not parse response content as |
| 45 | `DOC-c2ac5762c7f227fa` | License_Agreements | — | — | ✗ | 191.9 | None | None | LengthFinishReasonError: Could not parse response content as |
| 46 | `DOC-9e063c6e3baf1233` | Supply | 0.5882 | 0.0000 | ✓ | 194.1 | 6953 | 3307 |  |
| 47 | `DOC-99ca00712a84f039` | Outsourcing | 0.6000 | 0.0000 | ✓ | 217.4 | 5337 | 4055 |  |
| 48 | `DOC-54ad252b1e5e8d58` | Manufacturing | — | — | ✗ | 218.9 | None | None | LengthFinishReasonError: Could not parse response content as |
| 49 | `DOC-c30c293d38a2cd8b` | Maintenance | — | — | ✗ | 219.1 | None | None | LengthFinishReasonError: Could not parse response content as |
| 50 | `DOC-2ca7b08d2d439f1e` | Service | — | — | ✗ | 219.5 | None | None | LengthFinishReasonError: Could not parse response content as |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s9-contracts50-bal.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s9-contracts50-bal
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s9-contracts50-bal.yaml` | run spec |
| `reports/serving/sand032-s9-contracts50-bal.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s9-contracts50-bal/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s9-contracts50-bal/` | offline Braintrust-shaped rows — disposed after this report is committed |
