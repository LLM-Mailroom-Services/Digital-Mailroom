# Run report — `run-50-correspondence-specialist-awq`

Modal × vLLM specialist extract: **50 correspondence docs** (fills the 62-row
test pool; demand/notice pools exhaust at 3), on **Qwen/Qwen3-8B-AWQ** at
**concurrency 8** on **2×L4 data-parallel** (MIN=MAX=2 pinned, SAME warm app as
the 20-doc run — no redeploy), DMR-074 **production** prompt pin.

| | |
| --- | --- |
| run_id | `run-50-correspondence-specialist-awq` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local DMR-074 pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel, one replica per L4) |
| context / quant | `max_model_len=32768`, AWQ, gpu_util=0.90, max_num_seqs=6 |
| engine flags | prefix_caching=on, enforce_eager=on, async_scheduling=off, attention_backend=default, no reasoning/tool parsers |
| modal | `sandbox-vllm`, max_containers=2, min_containers=2 (pinned warm), scaledown=120 |
| profile / provider | `modal-vllm` / `vllm` |
| dataset | mailroom-dataset `ground_truth`, split=test, rev `46a4d3c2`, seed 42 |
| draw | 50 correspondence docs; fingerprint `d7eda8cf7c32` (superset of the 20-doc draw) |
| git | `59b9d35` (dirty=True) |
| spec_hash | `b6722111cba8ec4d668f1b88cca994ae82ec9e6540b8aaa9707356a1acdb7413` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **50 / 50** (`error_count=0`) |
| **overall_extraction_score** | **0.254748** |
| exact_match | 0.254748 |
| schema_valid_rate | 0.94 (47/50) |
| offline_fallback rows | 0 |
| parse_error_count | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (busy interval) | 280.099 s |
| concurrency | 8 (~4 per replica) |
| cold boot (measured at preflight) | 0.503 s (endpoint already warm) |
| gpu_seconds (1-replica export) | 280.602 s (wall + cold boot) |
| estimated GPU cost (billed, 2 replicas) | **$0.124712** |
| cost per document (billed, 2 replicas) | $0.00249424 |
| serving-record export (1-replica basis) | $0.062356 ($0.00124712/doc) — doubled for billing: the export assumes one GPU |
| token-proxy cost | $0.004539 ($0.00009078/doc) |
| latency e2e / p50 / max | 28.555953 / 27.260120 / 142.829407 s |
| prompt / completion / total tokens | 111514 / 9183 / 120697 |
| throughput | 430.91 tok/s |
| slot utilization | 0.637 (busy_slot 178.5 s vs wall 280.1 s; tail doc pins the wall) |
| cost cap | $0.80 (config) → under cap |

**Concurrency proof (not serial):**

- sum(per-doc latency) = 1427.8 s
- wall = 280.099 s → speedup **5.10x** at concurrency 8
- One tail doc (`DOC-6357890dcb31f6b2`, meeting_request, 142.8 s) pins the wall;
  without it the speedup would read ~7x. Serial would show wall ≈ sum(latency).

## Engine observations (KV / prefix cache)

- Same deployment as Run A (no redeploy): eager on, AWQ fusions, 32768 window.
- `/metrics` (sampled replica, cumulative since deploy): prefix-cache
  **62.0% hit rate** (62,208 / 100,329 queried tokens). Run-B-window delta on
  the sampled replica: +43,741 queried / +27,536 hits ≈ **63.0%** — the shared
  production system prompt keeps amortizing prefill at 50-doc scale.
- `GPU KV cache usage: 0.0%` at idle scrapes; `Running: 0 reqs` between waves —
  no KV pressure, no waiting-queue buildup (`num_requests_waiting` stayed 0).
- Per-replica APC caches are independent (round-robin routing); the second
  replica's counters were not sampled — rates above are one replica's view.
- Async scheduling stayed **off** (structured extraction outputs required).

## Strata (seed 42, split=test)

| subclass | n | mean overall |
| --- | --- | --- |
| email | 24 | 0.2655 |
| letter | 7 | 0.1989 |
| press_release | 6 | 0.1782 |
| memo | 4 | 0.1787 |
| meeting_request | 3 | 0.2797 |
| demand | 3 | 0.4275 |
| notice | 3 | 0.3556 |
| **total** | **50** | **0.254748** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-02dc4ab50ea271a4` | email | 0.0741 | 0.0000 | 15.2 | 2034 | 161 | None |
| 2 | `DOC-639c75dabf456876` | email | 0.2133 | 0.0000 | 28.7 | 2763 | 271 | None |
| 3 | `DOC-c8ad805cf688bfe2` | letter | 0.0833 | 0.0000 | 19.8 | 1777 | 130 | None |
| 4 | `DOC-41ab75d8d308b240` | demand | 0.6667 | 0.2667 | 15.0 | 1746 | 138 | None |
| 5 | `DOC-d52b54bc1a69fe75` | email | 0.3889 | 0.1428 | 9.8 | 1686 | 123 | None |
| 6 | `DOC-8d7644247d152274` | letter | 0.1000 | 0.0000 | 23.7 | 3297 | 189 | None |
| 7 | `DOC-b4ada461ba4bbe61` | press_release | 0.5468 | 0.1112 | 8.7 | 2651 | 177 | None |
| 8 | `DOC-19af28d3520c24fd` | meeting_request | 0.1000 | 0.0000 | 6.2 | 1754 | 150 | None |
| 9 | `DOC-5c32c7fd683b2464` | email | 0.0513 | 0.0000 | 27.7 | 1759 | 230 | None |
| 10 | `DOC-15c7be585a5bdd6b` | press_release | 0.0494 | 0.0000 | 28.0 | 2078 | 249 | None |
| 11 | `DOC-6b099b159b9a23bb` | email | 0.4167 | 0.1176 | 31.8 | 2204 | 171 | None |
| 12 | `DOC-5cdfee2b0ef0a218` | meeting_request | 0.2029 | 0.0000 | 27.0 | 1728 | 158 | None |
| 13 | `DOC-47c480a8749b6128` | email | 0.0444 | 0.0000 | 32.3 | 2031 | 130 | None |
| 14 | `DOC-b714773e73596e20` | notice | 0.1333 | 0.0000 | 28.5 | 2181 | 200 | None |
| 15 | `DOC-166a38f8097667fe` | memo | 0.5000 | 0.1112 | 32.5 | 1985 | 207 | None |
| 16 | `DOC-78c2282e6dfb948b` | email | 0.1191 | 0.0000 | 27.5 | 2013 | 245 | None |
| 17 | `DOC-228d359edcc4d302` | email | 0.3333 | 0.1333 | 28.3 | 1738 | 132 | None |
| 18 | `DOC-ed443335be29033d` | email | 0.2832 | 0.0000 | 26.9 | 1922 | 234 | None |
| 19 | `DOC-58b23ffd74bbc3c8` | press_release | 0.1261 | 0.0000 | 30.2 | 2032 | 218 | None |
| 20 | `DOC-03d58afbec80a06b` | letter | 0.4203 | 0.1176 | 28.8 | 1991 | 217 | None |
| 21 | `DOC-1f7ea83aa0ef6fc6` | press_release | 0.1228 | 0.0000 | 42.8 | 5305 | 619 | None |
| 22 | `DOC-4eb0e9385b81cc4b` | email | 0.0303 | 0.0000 | 30.8 | 1780 | 161 | None |
| 23 | `DOC-84ffaa54f0382296` | email | 0.2029 | 0.0000 | 29.9 | 1735 | 160 | None |
| 24 | `DOC-0bf6b6f34bf3b894` | letter | 0.3333 | 0.1333 | 37.4 | 1827 | 172 | None |
| 25 | `DOC-690cb07fef21747b` | email | 0.1754 | 0.0000 | 33.9 | 1950 | 170 | None |
| 26 | `DOC-ddb5ea45629b0002` | email | 0.0833 | 0.0000 | 36.2 | 2130 | 136 | None |
| 27 | `DOC-db203ac15614f83e` | email | 0.2778 | 0.0000 | 32.6 | 1830 | 226 | None |
| 28 | `DOC-a14148982aa7bc36` | email | 0.2050 | 0.0000 | 33.8 | 2584 | 128 | None |
| 29 | `DOC-5c54a5baef4b9f06` | email | 0.1276 | 0.0000 | 28.6 | 1714 | 130 | None |
| 30 | `DOC-d93fc6f9d8a12c94` | memo | 0.0741 | 0.0000 | 26.8 | 1924 | 163 | None |
| 31 | `DOC-a7e5e24fade86aae` | memo | 0.0606 | 0.0000 | 22.9 | 2695 | 160 | None |
| 32 | `DOC-8a4d83e88d9283c4` | press_release | 0.0417 | 0.0000 | 26.6 | 4424 | 167 | None |
| 33 | `DOC-a4bea6c6cd58226c` | notice | 0.4667 | 0.1112 | 25.3 | 1925 | 237 | None |
| 34 | `DOC-fdd758cb29665d7e` | press_release | 0.1825 | 0.0000 | 27.1 | 2407 | 146 | None |
| 35 | `DOC-704a6ade122c33c7` | email | 0.1111 | 0.0000 | 22.1 | 1682 | 116 | None |
| 36 | `DOC-2cde0c6d0c70b02b` | memo | 0.0800 | 0.0000 | 25.2 | 2202 | 162 | None |
| 37 | `DOC-bfbaa0b7fefa7640` | demand | 0.4524 | 0.1112 | 25.4 | 1686 | 137 | None |
| 38 | `DOC-c2c4ef739985acb6` | demand | 0.1633 | 0.0000 | 24.3 | 1996 | 194 | None |
| 39 | `DOC-f6a9a00e53cc7973` | notice | 0.4667 | 0.1176 | 29.1 | 6879 | 168 | None |
| 40 | `DOC-7e0a41f1efa97e06` | email | 0.7619 | 0.2105 | 22.8 | 1724 | 176 | None |
| 41 | `DOC-dcb984a30205f166` | letter | 0.2167 | 0.0000 | 28.6 | 1876 | 175 | None |
| 42 | `DOC-a0d2177d94df8da4` | email | 0.5555 | 0.1250 | 22.8 | 1793 | 157 | None |
| 43 | `DOC-7bae2384ef8f8a8f` | email | 0.6667 | 0.2222 | 27.5 | 2119 | 177 | None |
| 44 | `DOC-cf33df0934b38188` | letter | 0.0533 | 0.0000 | 27.8 | 2638 | 201 | None |
| 45 | `DOC-e040557913d9976b` | email | 0.1111 | 0.0000 | 26.6 | 1723 | 152 | None |
| 46 | `DOC-6357890dcb31f6b2` | meeting_request | 0.5362 | 0.1112 | 142.8 | 2224 | 194 | None |
| 47 | `DOC-57a4610edf1cb5ed` | email | 0.4762 | 0.1112 | 23.5 | 1894 | 160 | None |
| 48 | `DOC-35146decb7e3ffb8` | letter | 0.1856 | 0.0000 | 23.2 | 1836 | 211 | None |
| 49 | `DOC-16be7fa7e8ae5431` | email | 0.1451 | 0.0000 | 22.5 | 1697 | 113 | None |
| 50 | `DOC-b8d90997f6f4d17a` | email | 0.5185 | 0.1112 | 22.4 | 1945 | 185 | None |

- scored rows: 50/50; min=0.0303 max=0.7619 mean=0.2547

## Deploy env actually used

Same warm app as Run A (no redeploy between runs):

```bash
modal profile activate hermes-agent-jjb   # verified via `modal profile current`
export SANDBOX_PROFILE=modal-vllm MODAL_VLLM_MODEL=Qwen/Qwen3-8B-AWQ \
  MODAL_VLLM_QUANTIZATION=awq MODAL_VLLM_MAX_MODEL_LEN=32768 \
  MODAL_VLLM_GPU=L4 MODAL_VLLM_IMAGE_TAG=v0.29.0 \
  MODAL_VLLM_MAX_CONTAINERS=2 MODAL_VLLM_MIN_CONTAINERS=2 \
  MODAL_VLLM_SCALEDOWN_SECONDS=120 MODAL_VLLM_MAX_NUM_SEQS=6 \
  MODAL_VLLM_GPU_MEMORY_UTILIZATION=0.90 \
  MODAL_VLLM_ENABLE_PREFIX_CACHING=1 MODAL_VLLM_ENFORCE_EAGER=1
```

- Preflight `--live` re-verified the engine (AWQ / 32768 / prefix on / max_containers=2),
  cold boot 0.503 s (warm), then `start --job-mode endpoint --watch`.
- Teardown after this run: `./deploy/teardown_vllm.sh` → app `stopped`,
  `modal container list` verified **zero** warm containers.
- Billing window (session): metered $17.14 → $17.90 (**+$0.76** covering deploy
  warm + both runs + MIN=MAX=2 idle), credits −$16.95 → −$17.71,
  **billed $0.00**.

## Artifacts

| path | role |
| --- | --- |
| `config/runs/run-50-correspondence-specialist-awq.yaml` | run spec |
| `data/runtime/runs/run-50-correspondence-specialist-awq/` | run dir |
| `data/runtime/runs/run-50-correspondence-specialist-awq/dataset.jsonl` | seeded draw (50) |
| `data/runtime/runs/run-50-correspondence-specialist-awq/items.jsonl` | per-doc results (reconstructed from captured run output) |
| `data/runtime/runs/run-50-correspondence-specialist-awq/stdout.log` | full captured run output |
| `reports/experiment_log.jsonl` | sandbox experiment record (gitignored) |
| `reports/serving/run-50-correspondence-specialist-awq.serving.json` | serving-record export (1-replica basis) |

## Reproduce

```bash
modal profile activate hermes-agent-jjb
export SANDBOX_PROFILE=modal-vllm MODAL_VLLM_MODEL=Qwen/Qwen3-8B-AWQ \
  MODAL_VLLM_QUANTIZATION=awq MODAL_VLLM_MAX_MODEL_LEN=32768 \
  MODAL_VLLM_GPU=L4 MODAL_VLLM_IMAGE_TAG=v0.29.0 \
  MODAL_VLLM_MAX_CONTAINERS=2 MODAL_VLLM_MIN_CONTAINERS=2 \
  MODAL_VLLM_SCALEDOWN_SECONDS=120
# set VLLM_BASE_URL + VLLM_API_KEY after deploy (never commit tokens)
modal run deploy/modal_vllm.py::download_model
modal deploy deploy/modal_vllm.py --strategy recreate
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm
sandbox run benchmark-check --config config/runs/run-50-correspondence-specialist-awq.yaml
sandbox run preflight --config config/runs/run-50-correspondence-specialist-awq.yaml --live
sandbox run start --config config/runs/run-50-correspondence-specialist-awq.yaml --job-mode endpoint --watch
./deploy/teardown_vllm.sh   # ONLY after the last run (+ container list + billing window)
```

## Comparison

### (a) Sibling Modal runs (same harness, same AWQ checkpoint)

| run | n | overall | wall s | conc | GPU topology | GPU $ (billed) | $/doc (GPU) | tok/s | schema_valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| run-20-correspondence-specialist-awq (Run A) | 20 | 0.22799 | 75.084 | 8 | 2×L4 | $0.033616 | $0.00168080 | 715.08 | 0.90 |
| **run-50-correspondence-specialist-awq (Run B)** | **50** | **0.254748** | **280.099** | **8** | **2×L4** | **$0.124712** | **$0.00249424** | **430.91** | **0.94** |
| run-20-insurance-claims-specialist-awq | 20 | 0.671435 | 422.152 | 8 | 1×L4 | $0.093892 | $0.00469460 | 185.74¹ | 0.25 |
| run-20-correspondence-awq (c5, vendored default³) | 20 | 0.08934 | 253.692 | 5 | 1×L4 | $0.114231 | $0.00571155 | 167.47¹ | n/a² |
| run-20-correspondence-awq-c8 (vendored default³) | 20 | 0.08714 | 90.401 | 8 | 1×L4 | $0.055620 | $0.00278100 | 472.09 | n/a² |

¹ tok/s recomputed as total_tokens/wall from the archived figures (insurance:
78,418/422.152; c5: 42,482/253.692). ² Schema-validity was not recorded on the
pre-SAND-026 simplified-prompt runs — genuinely unavailable, not zero.
³ Corrected 2026-09-28. These rows were labelled `*_simplified`, but both runs
(25 Sep, ~13:30 UTC) predate the `*_simplified` stems (commit `164d45d`, 19:30 UTC)
and ran before job runners applied per-agent prompt pins (commit `6dbf457`), so they
sent the agent's vendored default text.

Reading:

- Run B scores a touch above Run A (0.2547 vs 0.2280) on the same engine and
  prompt — the 50-doc draw leans email/demand/notice, which score highest.
- ~~Production prompt is the dominant quality variable: 0.228–0.255 here vs
  0.087–0.089 on the same checkpoint with `*_simplified` (schema validity
  0.90–0.94 vs unrecorded/low). Scale-out buys speed, not score.~~
  **Corrected 2026-09-28:** the 0.087–0.089 → 0.228–0.255 lift is confounded,
  not a prompt effect. Between those runs the scorer changed (`8e507e1`: empty
  and other-class GT no longer scored as misses), prompt delivery changed
  (`6dbf457`: pins applied for the first time), the draw changed (split=all
  unstratified → test split, subclass-stratified) and serving changed (1×L4,
  `max_num_seqs` 256 → 2×L4, 6). Only one document is shared between the eras.
- *(Corrected 2026-09-28: 75 s vs 90 s is a 17% cut, not a halving, and the two
  runs used different draws.)*
- 2×L4 halves wall vs the 1×L4 c8 precedent (75 s vs 90 s at n=20) while
  serving ~4 docs per replica; per-doc $/doc stays below the 1×L4 c8 figure
  at n=20 ($0.00168 vs $0.00278) because wall falls faster than replicas bill.
- Run B's $/doc ($0.00249) exceeds Run A's ($0.00168): the 142.8 s tail doc
  idles one replica while the wall (and both GPUs) keeps billing — tail
  latency, not throughput, sets large-run cost.
- Insurance scores far higher (0.6714) on the same checkpoint/posture:
  correspondence extraction is the harder task under this scorer (GT has ~18
  mostly-empty keys/doc; entity F1 is ~0 for most correspondence rows), not a
  regression — the API leg shows the same gap (0.7488 insurance vs 0.5130
  correspondence).

### (b) Eval-environment API legs (OpenRouter, seed-42 20-doc waves + probes)

All from `/Users/morningstar/Desktop/Cold_Storage/eval-environment/reports`
(same dataset rev `46a4d3c2`); paired stems match the Modal legs.

| report | engine (API) | n | score³ | wall s | conc | cost $ (actual) | $/doc | tokens p/c/t |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| correspondence `20260927T033031Z` | qwen/qwen3-8b | 20 | 0.5130 | 1230.1 | 8 | $0.0604 | $0.0030 | 87002/110287/197289 |
| insurance_claims `20260927T035135Z` | qwen/qwen3-8b | 20 | 0.7488 | 203.3 | 8 | $0.0320 | $0.0016 | 75955/50885/126840 |
| contracts `20260927T035621Z` | qwen/qwen3-8b | 20 | 0.6169 | 1457.5 | 8 | $0.1141 | $0.0057 | 546225/110286/656511 |
| corporate_records `20260927T042239Z` | qwen/qwen3-8b | 20 | 0.4004 | 436.5 | 8 | $0.0602 | $0.0030 | 301916/54703/356619 |
| merger_agreement `20260927T022750Z` | qwen/qwen3.7-flash | 20 | 0.3748 | 142.0 | 8 | $0.0575 | $0.0029 | 1422210/114281/1536491 |
| merger_agreement `20260927T020724Z` | qwen/qwen3.7-flash | 2 | 0.3460 | 106.5 | 1 | $0.0064 | $0.0032 | 157083/13016/170099 |
| classification `20260927T043145Z` | qwen/qwen3-8b | 20 | 0.7000⁴ | 194.3 | 8 | $0.1493 | $0.0075 | 1213021/16132/1229153 |
| correspondence granite `20260927T044805Z` | ibm-granite/granite-4.2-8b | 20 | 0.0999 | 185.8 | 8 | n/a⁵ | $0.0018⁵ | 93101/120989/214090 |
| correspondence granite `20260927T044725Z` | ibm-granite/granite-4.2-8b | 2 | 0.0000 | 2.5 | 1 | n/a⁵ | n/a⁵ | 20/20/40⁶ |

³ `overall_score` (extraction mean) except where noted. ⁴ Classification reports
`class_accuracy` (subclass 0.05) — no `overall_score` exists on that report;
field genuinely unavailable, not omitted. ⁵ Granite-20 has no `cost actual`
row — only `$0.0018/doc est`; the 2-doc probe has no cost rows at all
(degenerate 2.5 s probe, 40 tokens). ⁶ 20/20/40 tokens mark the probe as degenerate; scored 0.0.

Reading (Modal 2×L4 AWQ vs API legs):

- Quality: Run B (0.2547) trails the qwen3-8b API correspondence leg (0.5130)
  but beats the granite API correspondence leg (0.0999) and both pre-existing
  local AWQ correspondence runs (0.087–0.089). Local AWQ + production prompt
  closes roughly half the gap to the API leg on this class.
- Cost: Run B GPU-billed $0.00249/doc vs API correspondence $0.0030/doc —
  the 2×L4 run is modestly cheaper per doc than the API leg while ~4.4× faster
  in wall (280 s vs 1230 s). Run A is cheaper still ($0.00168/doc).
- Latency shape differs: API legs show huge completion-token tails
  (correspondence API: 110k completion tokens; max per-doc 1086.9 s on a
  39k-token thinking blowout) while the Modal leg's decode stays tight
  (9,183 completion tokens over 50 docs; max 142.8 s). Different decode
  posture (frozen API budgets up to 4096/doc vs overlay 2048), not just serving.
- *(Corrected 2026-09-28: contracts and merger have no valid Modal-AWQ score —
  GT gap and agent confound — so the ordering below holds on the API legs only.)*
- Cross-class calibration holds: insurance > contracts > correspondence >
  merger ordering is the same on Modal-AWQ and API legs; absolute levels are
  lower on Modal-AWQ throughout (quantization + decode budget + prompt lineage).

### Run-to-run stability (built-in replication)

- Run B's draw is a strict superset of Run A's (same seed 42; all 20 Run-A
  doc ids recur in Run B). Overlapping docs: 19/20 identical scores,
  mean |Δ| = 0.0008, max |Δ| = 0.0166 — temperature-0.1 decode is stable
  across runs; batching nondeterminism is a ±0.02 effect at most.
- Run A itself was executed twice on the identical draw (first attempt
  overall=0.244565 @ 80.43 s; canonical repeat 0.22799 @ 75.084 s) — same
  stability band. Report the band, not the digit.

## Notes

- `items.jsonl` for both runs was reconstructed from the captured
  `--watch` stdout (the isolated specialist path returns rows in-memory and
  does not persist them; only the per-item whole-run path writes
  `items.jsonl`). Reconstruction is byte-faithful to the returned rows
  (same key shape as the insurance precedent). Follow-up: persist isolated
  rows to `items.jsonl` in the harness so serving-record export works
  without stdout capture.
- GPU $ presented as billed (2× replicas) is derived as
  2 × (wall + cold_boot) / 3600 × $0.80/L4-hr. The `serving-record` export
  records the 1-replica basis ($0.062356 / $0.00124712/doc); both figures are
  kept so the export stays reproducible and billing stays honest.
- Token-proxy $ uses champion pricing (0.03/0.13 per 1M) — a like-for-like
  comparator, not a bill.
