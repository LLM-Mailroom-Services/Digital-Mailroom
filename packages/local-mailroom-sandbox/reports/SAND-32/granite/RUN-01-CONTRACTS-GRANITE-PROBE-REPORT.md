# Probe report — `run-01-contracts-granite-probe` (FAIL)

HALT-gated 1-doc probe of the Granite contracts leg. Separate instance from
`run-20-contracts-granite` (own run dir; metrics never merged).

| | |
| --- | --- |
| run_id | `run-01-contracts-granite-probe` |
| task / agent | `contracts_specialist` |
| prompt | `contracts_specialist_v33_simplified` (local DMR-074 pin) |
| engine | `ibm-granite/granite-4.2-8b-fp8`, vLLM `v0.29.0`, 1×L4, `compressed-tensors`, 32768 |
| decode budget | 4096 (overlay default — the `contracts_specialist` budget row) |
| dataset | 1 service doc, test split, rev `46a4d3c2`, seed 42, fingerprint `3c221950cc53` |
| concurrency | 1 (serial probe) |
| cold boot | 0.60 s (endpoint already warm) |

## Result: FAIL

| metric | value |
| --- | --- |
| docs ok / total | **0 / 1** |
| wall | 297 s |
| prompt / completion tokens | 6949 / 4096 (budget exhausted) |
| reasoning tokens (vLLM count) | 0 |

Full error string (preserved from stdout — the failed isolated run writes no
`items.jsonl`, so this is the record):

```text
LengthFinishReasonError: Could not parse response content as the length limit
was reached - CompletionUsage(completion_tokens=4096, prompt_tokens=6949,
total_tokens=11045, completion_tokens_details=CompletionTokensDetails(
accepted_prediction_tokens=None, audio_tokens=None, reasoning_tokens=0,
rejected_prediction_tokens=None))
```

## Reading

Granite-4.2 thinks out loud (smoke-proven) and the native `granite` parser does
not separate it (`reasoning_tokens=0` — thinking flows as content). The model
burned the entire 4096-token window on thinking and never emitted final JSON.
Fix: run-scoped 16384 decode budget → re-probed as `run-02-contracts-granite-probe2`.
