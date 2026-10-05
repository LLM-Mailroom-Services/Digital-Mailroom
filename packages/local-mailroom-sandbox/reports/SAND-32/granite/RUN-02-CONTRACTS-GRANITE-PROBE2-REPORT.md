# Probe report — `run-02-contracts-granite-probe2` (functional PASS)

Fix re-probe after run-01 `LengthFinishReasonError` at 4096 completion tokens.
Separate instance (own run dir, items, serving record). Same doc
(fingerprint `3c221950cc53`) for comparability.

| | |
| --- | --- |
| run_id | `run-02-contracts-granite-probe2` |
| task / agent | `contracts_specialist` |
| prompt | `contracts_specialist_v33_simplified` (local DMR-074 pin) |
| engine | `ibm-granite/granite-4.2-8b-fp8`, vLLM `v0.29.0`, 1×L4, `compressed-tensors`, 32768 |
| fix under test | run-scoped `SANDBOX_AGENT_KNOBS`: `contracts_specialist` → `max_tokens` 16384, `max_input_chars` 18000 (prompt 6949 + 16384 + 4000 overhead fits 32768) |
| dataset | 1 service doc, test split, rev `46a4d3c2`, seed 42 |
| concurrency | 1 (serial probe) |
| cold boot | 1.27 s (endpoint already warm) |

## Result: functional PASS (quality flag — see below)

| metric | value |
| --- | --- |
| docs ok / total | **1 / 1** (`error_count=0`) |
| wall | 618.5 s (latency 618503 ms) |
| prompt / completion / total tokens | 6949 / **11676** / 18625 |
| decode rate | ≈ 18.9 tok/s |
| schema_valid_rate | **1.0** (parse errors 0) |
| overall_extraction_score / exact_match / extraction_f1 | **0.0** |

## Reading

- The 16k budget fixes the mechanism: 11,676 completion tokens (≈6× the Qwen
  ~2k assumption) — thinking + JSON now fit. This validates the decode-budget
  fix for all Granite legs (merger uses 16384/20000-char knobs;
  correspondence-50 uses 8192).
- Wall 618 s exceeds the 300 s probe criterion — Granite decode is slow
  (~19 tok/s) and full runs must be capped accordingly (merger caps resized
  to $1.20 / 6000 s).
- **Quality flag:** schema-valid JSON scored 0.0 extraction on this doc. n=1
  proves little, but Granite extraction quality (vs Qwen twins) is now the
  open question the merger/correspondence runs must answer — watch
  per-doc scores, not just ok counts.
