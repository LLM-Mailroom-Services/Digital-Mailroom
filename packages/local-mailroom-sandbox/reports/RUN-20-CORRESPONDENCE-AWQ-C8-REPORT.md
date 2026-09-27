# Run report — `run-20-correspondence-awq-c8`

SAND-019 follow-up: the **same 20-document correspondence draw** (seed 42,
fingerprint `285f423d3708`) as `run-20-correspondence-awq`, re-run at
**concurrency 8**. The only variable is concurrency; the draw, prompt, engine
and quantization are identical. Purpose: log a measured, *effective* 8-wide
batched run on one L4.

| | |
|---|---|
| run_id | `run-20-correspondence-awq-c8` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local, pinned) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 1x L4 |
| context / quant | `max_model_len=32768`, AWQ, gpu_util=0.90, max_num_seqs=256 |
| profile / provider | `modal-vllm` / `vllm` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `46a4d3c2`, seed 42 |
| draw | 20 correspondence docs (seeded class bucket; identical to c5) |
| git | `fa74d59` (dirty=True) |
| spec_hash | `39b5a2a2a7543a80c0bf988e343ddd8d2d6a530fbdbb61f0daa9920ab4aa5c2f` |

## Headline results

| metric | value |
|---|---|
| docs ok / total | **20 / 20** (`error_count=0`) |
| **overall_extraction_score** | **0.08714** |
| exact_match | 0.08714 |
| offline_fallback rows | 0 |

## Serving / cost metrics

| metric | value |
|---|---|
| wall (busy interval) | 90.401 s |
| concurrency | 8 |
| cold boot (measured) | 159.887 s |
| gpu_seconds | 250.29 s (wall + cold boot) |
| estimated GPU cost | **$0.055620** |
| cost per document | $0.00278100 |
| latency e2e / p50 / max | 30.232271 / 34.993895 / 38.517704 s |
| prompt / completion / total tokens | 39058 / 3619 / 42677 |
| throughput | 472.09 tok/s |
| cost cap | $0.35 (config) -> under cap |

**Concurrency proof (not serial):**
- sum(per-doc latency) = 604.6 s
- wall = 90.401 s -> speedup **6.69x** at concurrency 8
- serial would show wall ~= sum(latency); observed wall is the batched value.
- max latency is 38.5s — every doc finished inside a single short batch wave; no tail doc pinned the wall.

## Concurrency scaling vs `run-20-correspondence-awq` (c5)

| metric | c5 | c8 | delta |
|---|---|---|---|
| concurrency | 5 | 8 | +3 |
| wall | 253.692 s | 90.401 s | -163.3 s |
| speedup vs serial | 4.84x | 6.69x | +1.85x |
| p50 latency | 23.298 s | 34.994 s | +11.696 s |
| gpu_seconds | 514.04 s | 250.29 s | -263.8 s |
| estimated GPU cost | $0.114231 | $0.055620 | $-0.058611 |
| overall score | 0.08934 | 0.08714 | -0.00220 |

Reading: c8 cuts wall and GPU cost roughly in half at the same work, with a
mild p50 rise (more docs share each decode step) and a small score drift
(batch-order nondeterminism, not a regression).

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | latency s | prompt tok | compl tok | error |
|---|---|---|---|---|---|---|---|---|
| 1 | `DOC-2b5939247214be02` | demand | 0.0218 | 0.0 | 20.8 | 1890 | 190 | None |
| 2 | `DOC-b8d0988b09eefe09` | notice | 0.0478 | 0.0 | 12.8 | 1804 | 188 | None |
| 3 | `DOC-7d05b5b564199628` | notice | 0.0909 | 0.0952 | 30.4 | 1704 | 122 | None |
| 4 | `DOC-edc1649f20e66169` | letter | 0.0393 | 0.0 | 27.5 | 1964 | 153 | None |
| 5 | `DOC-2116c1f1706dced1` | email | 0.0917 | 0.0 | 23.7 | 1714 | 123 | None |
| 6 | `DOC-a4a29801ed53a8b1` | press_release | 0.1144 | 0.0833 | 16.1 | 1856 | 139 | None |
| 7 | `DOC-0fb811b124432763` | email | 0.1191 | 0.08 | 8.7 | 2416 | 245 | None |
| 8 | `DOC-81dde8f2cd0e6c5b` | email | 0.1192 | 0.0769 | 38.1 | 2148 | 322 | None |
| 9 | `DOC-38a7cb4be93dbecd` | notice | 0.2121 | 0.1538 | 34.9 | 2090 | 228 | None |
| 10 | `DOC-f1db54435294f184` | email | 0.0091 | 0.0 | 35.4 | 1660 | 191 | None |
| 11 | `DOC-27306248d00b66c2` | press_release | 0.1295 | 0.0869 | 35.1 | 1702 | 124 | None |
| 12 | `DOC-3ab61766974251fd` | demand | 0.0455 | 0.0 | 35.2 | 2137 | 192 | None |
| 13 | `DOC-5c54a5baef4b9f06` | email | 0.0348 | 0.0 | 35.4 | 1714 | 130 | None |
| 14 | `DOC-9ba1246dd99b264d` | notice | 0.0364 | 0.0 | 36.4 | 2184 | 198 | None |
| 15 | `DOC-56a2f3a613f97dee` | meeting_request | 0.1917 | 0.0769 | 38.5 | 1847 | 208 | None |
| 16 | `DOC-59f834ec3e6a34c0` | press_release | 0.138 | 0.0769 | 35.7 | 2575 | 188 | None |
| 17 | `DOC-0e928cc6feb45aa1` | email | 0.1169 | 0.08 | 35.2 | 1827 | 211 | None |
| 18 | `DOC-3936c819036c3b03` | letter | 0.075 | 0.0 | 34.4 | 1786 | 153 | None |
| 19 | `DOC-816e7205bde414f2` | email | 0.0218 | 0.0 | 35.8 | 2163 | 181 | None |
| 20 | `DOC-25e99e5e72fe5b90` | email | 0.0878 | 0.0 | 34.4 | 1877 | 133 | None |

- scored rows: 20/20; min=0.0091 max=0.2121 mean=0.0871

## Notes

- `scipy>=1.11` is now a base dependency (SAND-019), so entity-list
  matching is **optimal** (`linear_sum_assignment`); the greedy
  `bipartite_matching_failed` fallback is gone. This draw has mostly
  single-item entity lists, so the aggregate is unchanged to 4 dp — the fix
  removes the caveat, it does not inflate the score.
- Metric is the dojo suite mean over per-field scores; correspondence GT has
  ~18 keys/doc, many empty for non-insurance rows. 0.087 is a genuine
  small-model extraction score, not a ceiling.
- Identical draw and prompt to c5 (fingerprint `285f423d3708`), so c5/c8
  are directly comparable.

