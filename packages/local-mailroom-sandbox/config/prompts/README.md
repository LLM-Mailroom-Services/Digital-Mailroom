# Local prompt variants

These templates override mailroom's Langfuse-managed prompts (`get_managed_prompt`)
or the LangChain `PROMPT_VERSIONS` dict (Family B: sorter / contracts_specialist)
for a single experiment cell.

## Specialist production pins (DMR-074)

Synced from vendored `llm-mailroom` code-default (byte-identical to the
Digital-Mailroom monorepo workspace). Used by `config/runs/run-30-*-specialist.yaml`
so Modal L4 cost-evals are reproducible offline — **not** a floating Langfuse
`production` label.

| Stem | Agent | Source of truth | Notes |
| --- | --- | --- | --- |
| `contracts_specialist_v33` | `contracts_specialist` | `langchain_agents.prompts.PROMPT_VERSIONS["contracts_specialist_v33"]` | Mailroom production pin (entity-extraction has experimental v34–v41; **not** promoted) |
| `merger_agreement_specialist_production` | `merger_agreement_specialist` | `agents.merger_agreement_specialist.SYSTEM_PROMPT` | MAUD production (V0 + doctrine); **not** CUAD v33 |
| `corporate_records_specialist_production` | `corporate_records_specialist` | `agents.corporate_records_specialist.SYSTEM_PROMPT` | Base + `llm.prompt_doctrine` |
| `correspondence_specialist_production` | `correspondence_specialist` | `agents.correspondence_specialist.SYSTEM_PROMPT` | Base + doctrine |
| `insurance_claims_specialist_production` | `insurance_claims_specialist` | `agents.insurance_claims_specialist.SYSTEM_PROMPT` | Base + doctrine |

Refresh after a vendor sync:

```bash
python scripts/sync_specialist_prompts.py
```

## Local 7B/8B smoke variants

Shorter JSON-strict templates for Ollama smoke (`sorter_local_v0`,
`sorter_reviewer_local_v0`, `judge_local_v0`, `extract_local_v0`). Pass
`--prompt sorter_local_v0` to `sandbox eval` / `sandbox matrix`.
Unset = mailroom in-code fallbacks.
