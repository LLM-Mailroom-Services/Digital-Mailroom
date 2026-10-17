"""Per-doc-type Modal L4 Qwen specialist posture (DMR-078).

Single source of truth for the run-30 specialist suite: generation budgets
sized to fit ``Qwen/Qwen3-8B`` on 1×L4 ``max_model_len=16384``, concurrency
tuned by typical prompt length, and cost/wall abort caps so a misconfigured
or runaway 30-doc run cannot burn the wallet.

Shared warm-app rule still applies (DMR-076/077): one ``sandbox-vllm`` per
track; these knobs differ **per sequential class run**, not by redeploying
the engine. ``max_model_len`` stays 16384 across all five (L4-bf16 boot cap).
"""

from __future__ import annotations

from typing import Any, Mapping

# Designated Modal specialist model (bf16 default; AWQ optional via matrix).
BENCHMARK_MODEL = "Qwen/Qwen3-8B"
MAX_MODEL_LEN = 16384

# Rough system/prompt overhead reserved inside the context window (tokens).
# SAND-018: the v33 contract prompt carries ~3100 tokens of instruction/schema/
# few-shot overhead, so a doc at the old 35000-char cap produced 14337 input
# tokens and 400'd. Reserve 4000 for margin.
_SYSTEM_OVERHEAD_TOKENS = 4000

# Conservative chars/token for dense legal text when converting token budgets
# into ``max_input_chars`` (overlay / taxonomy). SAND-018 measured ~2.44
# chars/token on real contract filings — the old 3.5 under-estimated tokens, so
# a 35000-char cap produced 14337 input tokens and 400'd against the 16k window.
_CHARS_PER_TOKEN = 2.4


def _input_chars_for(
    max_tokens: int, prompt_tokens: int | None = None, max_model_len: int = MAX_MODEL_LEN
) -> int:
    """Chars that fit with max_tokens + system overhead under the window.

    When ``prompt_tokens`` is known, also cap at ~1.25× the assumed prompt so
    short doc classes (correspondence) do not over-prefill into empty context.
    SAND-019: ``max_model_len`` lets an AWQ 32768 run size a larger input cap.
    """
    available = max(1024, int(max_model_len) - int(max_tokens) - _SYSTEM_OVERHEAD_TOKENS)
    fit = int(available * _CHARS_PER_TOKEN)
    if prompt_tokens is None:
        return fit
    need = int(int(prompt_tokens) * _CHARS_PER_TOKEN * 1.25)
    return min(fit, max(need, 12000))


# Per run_id posture. Concurrency: short docs fill continuous batching higher;
# long MAUD/CUAD filings stay lower so KV/TTFT does not thrash the shared L4.
# max_tokens: ~2–3× assumed completion from SPECIALIST_TOKENS_PER_DOC, capped
# so prompt+completion still fit 16k. cost_cap / max_wall: likely estimate +
# ~40–60% headroom (Modal L4 ≈ $0.80/hr).
SPECIALIST_POSTURE: dict[str, dict[str, Any]] = {
    "run-30-correspondence-specialist": {
        "task": "correspondence_specialist",
        "doc_class": "correspondence",
        "agent": "correspondence_specialist",
        "prompt_file": "correspondence_specialist_simplified",
        "concurrency": 5,
        "max_tokens": 2048,
        "max_input_chars": _input_chars_for(2048, 3500),
        "cost_cap_usd": 0.40,
        "max_wall_seconds": 2400,
        "tokens_assumed": {"prompt": 3500, "completion": 600},
        "sec_per_doc": {"low": 30.0, "likely": 70.0, "high": 150.0},
        "rationale": "Short narrative docs — higher concurrency fills L4 batching; tight decode budget.",
    },
    "run-30-insurance-claims-specialist": {
        "task": "insurance_claims_specialist",
        "doc_class": "insurance_claim",
        "agent": "insurance_claims_specialist",
        "prompt_file": "insurance_claims_specialist_simplified",
        "concurrency": 5,
        "max_tokens": 3072,
        "max_input_chars": _input_chars_for(3072, 4500),
        "cost_cap_usd": 0.50,
        "max_wall_seconds": 3000,
        "tokens_assumed": {"prompt": 4500, "completion": 1000},
        "sec_per_doc": {"low": 45.0, "likely": 95.0, "high": 200.0},
        "rationale": "Mid-length claims tables — moderate concurrency; decode capped below 8192.",
    },
    # AWQ + concurrency 8: 20 insurance_claim docs, subclass quotas scaled 2/3
    # from run-30 (6→4 / 3→2). Aligns with improved-awq-c8 / legacy Qwen3-8B
    # AWQ completion posture (32768 window, scaledown 120, 1×L4).
    "run-20-insurance-claims-specialist-awq": {
        "task": "insurance_claims_specialist",
        "doc_class": "insurance_claim",
        "agent": "insurance_claims_specialist",
        "prompt_file": "insurance_claims_specialist_simplified",
        "concurrency": 8,
        "max_model_len": 32768,
        "max_tokens": 3072,
        "max_input_chars": _input_chars_for(3072, 4500, 32768),
        "cost_cap_usd": 0.40,
        "max_wall_seconds": 2400,
        "tokens_assumed": {"prompt": 4500, "completion": 1000},
        "sec_per_doc": {"low": 25.0, "likely": 55.0, "high": 130.0},
        "rationale": (
            "20-doc AWQ insurance run at concurrency 8 (legacy AWQ completion "
            "posture): subclass-stratified 2/3 scale of run-30 quotas; 32768 "
            "window; caps ~2/3 of the 30-doc insurance posture."
        ),
    },
    # Follow-up Qwen experiments: correspondence_specialist on AWQ, 2×L4
    # data-parallel (MIN=MAX=2 pinned during runs, one warm app for both),
    # concurrency 8, DMR-074 production prompt pin, 32768 window. Run A (20
    # docs) scales run-30 quotas 2/3 (12→8 / 3→2); Run B (50 docs) fills the
    # 62-row test pool (demand/notice pools exhaust at 3).
    "run-20-correspondence-specialist-awq": {
        "task": "correspondence_specialist",
        "doc_class": "correspondence",
        "agent": "correspondence_specialist",
        "prompt_file": "correspondence_specialist_production",
        "concurrency": 8,
        "max_model_len": 32768,
        "max_tokens": 2048,
        "max_input_chars": _input_chars_for(2048, 3500, 32768),
        "cost_cap_usd": 0.40,
        "max_wall_seconds": 2400,
        "tokens_assumed": {"prompt": 3500, "completion": 600},
        "sec_per_doc": {"low": 15.0, "likely": 35.0, "high": 95.0},
        "rationale": (
            "Run A: 20-doc AWQ correspondence at concurrency 8 on 2×L4 "
            "(data-parallel replicas); subclass-stratified 2/3 scale of "
            "run-30 quotas; 32768 window; DMR-074 production prompt pin."
        ),
    },
    "run-50-correspondence-specialist-awq": {
        "task": "correspondence_specialist",
        "doc_class": "correspondence",
        "agent": "correspondence_specialist",
        "prompt_file": "correspondence_specialist_production",
        "concurrency": 8,
        "max_model_len": 32768,
        "max_tokens": 2048,
        "max_input_chars": _input_chars_for(2048, 3500, 32768),
        "cost_cap_usd": 0.80,
        "max_wall_seconds": 3600,
        "tokens_assumed": {"prompt": 3500, "completion": 600},
        "sec_per_doc": {"low": 15.0, "likely": 35.0, "high": 95.0},
        "rationale": (
            "Run B: 50-doc AWQ correspondence at concurrency 8 on 2×L4 "
            "(data-parallel replicas); fills the 62-row test pool; caps "
            "scaled ~2.5× the 20-doc run for docs + 2-replica billing."
        ),
    },
    # ── Qwen AWQ merger cross-agent leg ─────────────────────────────────────
    # PLACEMENT MATTERS: AGENT_GENERATION_BUDGETS is last-writer-wins per
    # agent, so this contracts_specialist row (4096 Qwen decode) sits BEFORE
    # run-20-contracts-granite (16384) to leave the Granite-proven budget as
    # the global default. Run-scoped SANDBOX_AGENT_KNOBS overrides either.
    "run-20-merger-specialist-awq": {
        "task": "contracts_specialist",
        "doc_class": "merger_agreement",
        "agent": "contracts_specialist",
        "prompt_file": "contracts_specialist_v33_simplified",
        "concurrency": 8,
        "max_model_len": 32768,
        "max_tokens": 4096,
        "max_input_chars": _input_chars_for(4096, 10000, 32768),
        "cost_cap_usd": 0.70,
        "max_wall_seconds": 3600,
        "tokens_assumed": {"prompt": 10000, "completion": 2000},
        "sec_per_doc": {"low": 40.0, "likely": 120.0, "high": 300.0},
        "rationale": (
            "Qwen AWQ cross-agent merger baseline (contracts_specialist on "
            "MAUD docs) at c=8 on 1×L4 like all Qwen AWQ legs: no measured "
            "Qwen-merger pile-up evidence exists (Qwen AWQ c=8 measured "
            "5–7× speedups on insurance/correspondence); Granite c=3 KV "
            "evidence does not transfer (AWQ weight pool ~2× FP8)."
        ),
    },
    # ── Granite 4.2-8B FP8 sweep (1×L4, concurrency 8) ──────────────────────
    # Apples-to-apples twin of the Qwen AWQ 20-doc posture (DMR-075..077 +
    # correspondence 20/50 b3e1e2b): same strata scaled to 20, same DMR-074
    # local prompt pins as each class's Qwen AWQ comparator (production for
    # correspondence, simplified/v33-simplified elsewhere), 32768 window,
    # scaledown 120, MIN=MAX=1 pinned warm across the five-run chain.
    # Engine: ibm-granite/granite-4.2-8b-fp8 (compressed-tensors W8A8,
    # ~9.5GiB — the L4 workhorse row in config/models.yaml; no AWQ exists
    # for granite-4.2 and bf16 32k FAILS on 1×L4). Caps mirror the Qwen AWQ
    # 20-doc values where a comparator exists, else ~2/3 of run-30.
    "run-20-contracts-granite": {
        "task": "contracts_specialist",
        "doc_class": "contract",
        "agent": "contracts_specialist",
        "prompt_file": "contracts_specialist_v33_simplified",
        "concurrency": 3,
        "max_model_len": 32768,
        "max_tokens": 16384,
        "max_input_chars": _input_chars_for(16384, 8000, 32768),
        "cost_cap_usd": 0.55,
        "max_wall_seconds": 3200,
        "tokens_assumed": {"prompt": 8000, "completion": 4000},
        "sec_per_doc": {"low": 120.0, "likely": 450.0, "high": 900.0},
        "rationale": (
            "Granite twin of run-20-contracts-awq-c8 on 1×L4 FP8 at c=3 "
            "(HALT revision from 8). run-02 probe proved 16384 decode "
            "(11676 completion tokens vs 4096 LengthFinish); run-scoped "
            "SANDBOX_AGENT_KNOBS carries the budget, Qwen rows untouched."
        ),
    },
    "run-20-merger-granite": {
        "task": "merger_agreement_specialist",
        "doc_class": "merger_agreement",
        "agent": "merger_agreement_specialist",
        "prompt_file": "merger_agreement_specialist_simplified",
        "concurrency": 3,
        "max_model_len": 32768,
        "max_tokens": 16384,
        "max_input_chars": 20000,
        "cost_cap_usd": 1.20,
        "max_wall_seconds": 6000,
        "tokens_assumed": {"prompt": 10000, "completion": 5000},
        "sec_per_doc": {"low": 120.0, "likely": 450.0, "high": 900.0},
        "rationale": (
            "Granite merger leg on 1×L4 FP8 at c=3. run-02 probe proved "
            "Granite needs ~6x Qwen decode (16384 run-scoped knobs; input "
            "20000 chars keeps prompt+decode+overhead inside 32768). Caps "
            "resized from probe-measured ~19 tok/s (was 0.70/3600)."
        ),
    },
    "run-20-corporate-records-granite": {
        "task": "corporate_records_specialist",
        "doc_class": "corporate_record",
        "agent": "corporate_records_specialist",
        "prompt_file": "corporate_records_specialist_simplified",
        "concurrency": 3,
        "max_model_len": 32768,
        "max_tokens": 4096,
        "max_input_chars": _input_chars_for(4096, 5000, 32768),
        "cost_cap_usd": 0.40,
        "max_wall_seconds": 2400,
        "tokens_assumed": {"prompt": 5000, "completion": 1200},
        "sec_per_doc": {"low": 30.0, "likely": 65.0, "high": 150.0},
        "rationale": (
            "Granite corporate leg: 2/3 scale of run-30-corporate-records "
            "quotas at concurrency 8 on 1×L4 FP8; caps ~2/3 of the 30-doc "
            "corporate posture."
        ),
    },
    "run-20-correspondence-granite": {
        "task": "correspondence_specialist",
        "doc_class": "correspondence",
        "agent": "correspondence_specialist",
        "prompt_file": "correspondence_specialist_production",
        "concurrency": 3,
        "max_model_len": 32768,
        "max_tokens": 2048,
        "max_input_chars": _input_chars_for(2048, 3500, 32768),
        "cost_cap_usd": 0.40,
        "max_wall_seconds": 2400,
        "tokens_assumed": {"prompt": 3500, "completion": 600},
        "sec_per_doc": {"low": 15.0, "likely": 35.0, "high": 95.0},
        "rationale": (
            "Granite twin of run-20-correspondence-specialist-awq: identical "
            "20-doc strata + DMR-074 production prompt pin at concurrency 8 "
            "on 1×L4 FP8 (Qwen twin ran 2×L4; GPU $ scales accordingly)."
        ),
    },
    # 50-doc correspondence Granite eval (scope revision: correspondence-50 on
    # 1×L4 at c=8 per user; short docs keep KV within budget where contracts
    # serialized). Decode 8192 run-scoped: probe-measured ~6x Qwen thinking
    # inflation (600 → ~3600 + headroom); window fits (3.5k+8k+4k).
    "run-50-correspondence-granite": {
        "task": "correspondence_specialist",
        "doc_class": "correspondence",
        "agent": "correspondence_specialist",
        "prompt_file": "correspondence_specialist_production",
        "concurrency": 8,
        "max_model_len": 32768,
        "max_tokens": 8192,
        "max_input_chars": _input_chars_for(8192, 3500, 32768),
        "cost_cap_usd": 0.80,
        "max_wall_seconds": 3600,
        "tokens_assumed": {"prompt": 3500, "completion": 1500},
        "sec_per_doc": {"low": 40.0, "likely": 120.0, "high": 300.0},
        "rationale": (
            "Granite twin of run-50-correspondence-specialist-awq (fills the "
            "62-row test pool) on 1×L4 at c=8; caps mirror the Qwen twin "
            "(1-replica billing gives headroom for slower Granite decode)."
        ),
    },
    "run-20-insurance-claims-granite": {
        "task": "insurance_claims_specialist",
        "doc_class": "insurance_claim",
        "agent": "insurance_claims_specialist",
        "prompt_file": "insurance_claims_specialist_simplified",
        "concurrency": 3,
        "max_model_len": 32768,
        "max_tokens": 3072,
        "max_input_chars": _input_chars_for(3072, 4500, 32768),
        "cost_cap_usd": 0.40,
        "max_wall_seconds": 2400,
        "tokens_assumed": {"prompt": 4500, "completion": 1000},
        "sec_per_doc": {"low": 25.0, "likely": 55.0, "high": 130.0},
        "rationale": (
            "Granite twin of run-20-insurance-claims-specialist-awq: "
            "identical 20-doc strata (4/4/4/4/2/2) at concurrency 8 on 1×L4 "
            "FP8."
        ),
    },
    # ── Qwen AWQ corporate leg ────────────────────────────────────────────
    # Sibling of the insurance/correspondence AWQ 20-doc runs (c=8, 4096 Qwen
    # decode, hard retry cap). Values match the current global
    # corporate_records_specialist budget, so overlay behavior is unchanged.
    "run-20-corporate-records-specialist-awq": {
        "task": "corporate_records_specialist",
        "doc_class": "corporate_record",
        "agent": "corporate_records_specialist",
        "prompt_file": "corporate_records_specialist_simplified",
        "concurrency": 8,
        "max_model_len": 32768,
        "max_tokens": 4096,
        "max_input_chars": _input_chars_for(4096, 5000, 32768),
        "cost_cap_usd": 0.40,
        "max_wall_seconds": 2400,
        "tokens_assumed": {"prompt": 5000, "completion": 1200},
        "sec_per_doc": {"low": 30.0, "likely": 65.0, "high": 150.0},
        "rationale": (
            "Qwen AWQ corporate baseline at c=8 on 1×L4 (mid-length docs fill "
            "batching); max_retries hard-capped at 1 in the YAML — fail fast "
            "on repeated errors rather than burning credits."
        ),
    },
    # ── Probe instances (tracked separately from full runs) ─────────────────
    # Single-doc live probes get their own run_id / run dir / items / serving
    # record — probe metrics must never merge into full-run aggregates.
    # Serial by design (concurrency 1); benchmark_check exempts the c>=2 floor
    # for *-probe ids but still enforces caps / walls / limits / prompt pins.
    "run-01-contracts-granite-probe": {
        "task": "contracts_specialist",
        "doc_class": "contract",
        "agent": "contracts_specialist",
        "prompt_file": "contracts_specialist_v33_simplified",
        "concurrency": 1,
        "max_model_len": 32768,
        "max_tokens": 8192,
        "max_input_chars": _input_chars_for(8192, 8000, 32768),
        "cost_cap_usd": 0.10,
        "max_wall_seconds": 900,
        "tokens_assumed": {"prompt": 8000, "completion": 2000},
        "sec_per_doc": {"low": 60.0, "likely": 195.0, "high": 400.0},
        "rationale": (
            "HALT-gated 1-doc probe: same engine/strata family as "
            "run-20-contracts-granite (service doc, seed 42) at concurrency 1; "
            "sec/doc bands from the halted run's measured ~195s serial generations."
        ),
    },
    "run-02-contracts-granite-probe2": {
        "task": "contracts_specialist",
        "doc_class": "contract",
        "agent": "contracts_specialist",
        "prompt_file": "contracts_specialist_v33_simplified",
        "concurrency": 1,
        "max_model_len": 32768,
        "max_tokens": 16384,
        "max_input_chars": 18000,
        "cost_cap_usd": 0.15,
        "max_wall_seconds": 1800,
        "tokens_assumed": {"prompt": 8000, "completion": 4000},
        "sec_per_doc": {"low": 120.0, "likely": 400.0, "high": 900.0},
        "rationale": (
            "Fix re-probe after run-01 LengthFinishReasonError at 4096 "
            "completion tokens: run-scoped SANDBOX_AGENT_KNOBS raises decode "
            "to 16384 (prompt 6949 + 16384 + 4000 overhead fits the 32768 "
            "window); Qwen rows untouched."
        ),
    },
    "run-30-corporate-records-specialist": {        "task": "corporate_records_specialist",
        "doc_class": "corporate_record",
        "agent": "corporate_records_specialist",
        "prompt_file": "corporate_records_specialist_simplified",
        "concurrency": 4,
        "max_tokens": 4096,
        "max_input_chars": _input_chars_for(4096, 5000),
        "cost_cap_usd": 0.55,
        "max_wall_seconds": 3600,
        "tokens_assumed": {"prompt": 5000, "completion": 1200},
        "sec_per_doc": {"low": 50.0, "likely": 110.0, "high": 240.0},
        "rationale": "Hierarchical corporate filings — baseline concurrency 4.",
    },
    "run-30-contracts-specialist": {
        "task": "contracts_specialist",
        "doc_class": "contract",
        "agent": "contracts_specialist",
        "prompt_file": "contracts_specialist_v33_simplified",
        "concurrency": 4,
        "max_tokens": 4096,
        "max_input_chars": _input_chars_for(4096, 8000),
        "cost_cap_usd": 0.80,
        "max_wall_seconds": 4800,
        "tokens_assumed": {"prompt": 8000, "completion": 2000},
        "sec_per_doc": {"low": 70.0, "likely": 160.0, "high": 360.0},
        "rationale": "Long CUAD contracts — context-fit input cap (was 100k chars, over 16k window).",
    },
    # SAND-018: single-class 20-contract run drawn from the FULL corpus
    # (split=all, seeded random draw) — the runbook's 5×30 suite scaled to one
    # class at N=20. Same generation budget as run-30 contracts; cost/wall caps
    # scaled ~2/3 for 20 docs. bench gate keys on this row so the smaller run
    # cannot silently escape the DMR-078 pins.
    "run-20-contracts-specialist": {
        "task": "contracts_specialist",
        "doc_class": "contract",
        "agent": "contracts_specialist",
        "prompt_file": "contracts_specialist_v33_simplified",
        "concurrency": 4,
        # SAND-018: 2048 truncated some contract JSON (LengthFinishReasonError),
        # so decode stays 4096 now the harness honors the 600s call timeout;
        # input chars sized for the real ~2.4 chars/token of dense filings.
        "max_tokens": 4096,
        "max_input_chars": _input_chars_for(4096, 8000),
        "cost_cap_usd": 0.55,
        "max_wall_seconds": 3200,
        "tokens_assumed": {"prompt": 8000, "completion": 2000},
        "sec_per_doc": {"low": 70.0, "likely": 160.0, "high": 360.0},
        "rationale": (
            "SAND-018: 20-contract single-class run from the full corpus "
            "(split=all, seeded draw); caps scaled ~2/3 of the 30-doc "
            "contracts posture."
        ),
    },
    "run-20-contracts-awq": {
        "task": "contracts_specialist",
        "doc_class": "contract",
        "agent": "contracts_specialist",
        "prompt_file": "contracts_specialist_v33_simplified",
        "concurrency": 4,
        "max_tokens": 4096,
        "max_input_chars": _input_chars_for(4096, 8000),
        "cost_cap_usd": 0.55,
        "max_wall_seconds": 3200,
        "tokens_assumed": {"prompt": 8000, "completion": 2000},
        "sec_per_doc": {"low": 30.0, "likely": 70.0, "high": 150.0},
        "rationale": (
            "SAND-018 AWQ variant: Qwen/Qwen3-8B-AWQ on L4 halves weight bytes, "
            "so decode is ~2x faster and the KV cache fits concurrency 4; "
            "20-contract draw identical to run-20-contracts-specialist."
        ),
    },
    # SAND-019: corrected + 8-way concurrency AWQ contracts run. Two fixes over
    # run-20-contracts-awq: (1) the deploy is AWQ at max_model_len=32768, which
    # clears the 16384-window 400 (prompt 12289 + 4096 output = 16385 > 16384);
    # (2) max_tokens raised 4096 -> 8192 (run-scoped SANDBOX_AGENT_KNOBS) so the
    # doc that hit LengthFinishReasonError at 4096 can finish. Identical draw to
    # run-20-contracts-awq (seed 42).
    "run-20-contracts-awq-c8": {
        "task": "contracts_specialist",
        "doc_class": "contract",
        "agent": "contracts_specialist",
        "prompt_file": "contracts_specialist_v33_simplified",
        "concurrency": 8,
        "max_model_len": 32768,
        "max_tokens": 8192,
        "max_input_chars": _input_chars_for(8192, 8000, 32768),
        "cost_cap_usd": 0.55,
        "max_wall_seconds": 3200,
        "tokens_assumed": {"prompt": 8000, "completion": 2000},
        "sec_per_doc": {"low": 25.0, "likely": 55.0, "high": 130.0},
        "rationale": (
            "SAND-019 corrected AWQ contracts run at 8-way concurrency: 32768 "
            "window clears the 16k 400, and a run-scoped 8192 max_tokens clears "
            "the LengthFinishReasonError; draw identical to run-20-contracts-awq."
        ),
    },
    # SAND-019: single-class 20-correspondence run drawn from the FULL corpus
    # (split=all, seeded draw). Short narrative docs → higher concurrency, tight
    # decode. Caps scaled ~2/3 of the 30-doc correspondence posture; AWQ halves
    # decode so the likely wall is a fraction of bf16.
    "run-20-correspondence-awq": {
        "task": "correspondence_specialist",
        "doc_class": "correspondence",
        "agent": "correspondence_specialist",
        "prompt_file": "correspondence_specialist_simplified",
        "concurrency": 5,
        "max_tokens": 2048,
        "max_input_chars": _input_chars_for(2048, 3500),
        "cost_cap_usd": 0.35,
        "max_wall_seconds": 1800,
        "tokens_assumed": {"prompt": 3500, "completion": 600},
        "sec_per_doc": {"low": 20.0, "likely": 45.0, "high": 110.0},
        "rationale": (
            "SAND-019: 20-correspondence single-class run from the full corpus "
            "(split=all, seeded draw); short docs fill L4 batching, AWQ halves "
            "decode; caps scaled ~2/3 of the 30-doc correspondence posture."
        ),
    },
    # SAND-019: 8-way concurrency variant. Same 20-correspondence draw (seed 42)
# as run-20-correspondence-awq so the dataset fingerprint matches; the only
# change is concurrency, to log a measured 8-wide batched run for comparison.
# AWQ + short correspondence prompts leave enough KV headroom on one L4.
    "run-20-correspondence-awq-c8": {
        "task": "correspondence_specialist",
        "doc_class": "correspondence",
        "agent": "correspondence_specialist",
        "prompt_file": "correspondence_specialist_simplified",
        "concurrency": 8,
        "max_tokens": 2048,
        "max_input_chars": _input_chars_for(2048, 3500),
        "cost_cap_usd": 0.35,
        "max_wall_seconds": 1800,
        "tokens_assumed": {"prompt": 3500, "completion": 600},
        "sec_per_doc": {"low": 15.0, "likely": 35.0, "high": 95.0},
        "rationale": (
            "SAND-019: 8-concurrency correspondence run (identical draw to "
            "run-20-correspondence-awq) to log 8-wide batching on one L4; "
            "short AWQ prompts keep KV within budget."
        ),
    },
    # issue #21: FP16 twin of run-20-correspondence-awq-c8. Same draw (seed 42,
    # fingerprint 285f423d3708) and prompt; engine is non-AWQ Qwen3-8B so the
    # L4 window is 16384 (bf16 boot cap). PREPARED ONLY — do not deploy or
    # start this run until spend/auth are explicitly approved.
    "run-20-correspondence-fp16-c8": {
        "task": "correspondence_specialist",
        "doc_class": "correspondence",
        "agent": "correspondence_specialist",
        "prompt_file": "correspondence_specialist_production",
        "concurrency": 8,
        "max_tokens": 2048,
        "max_input_chars": _input_chars_for(2048, 3500),
        "cost_cap_usd": 0.50,
        "max_wall_seconds": 2400,
        "tokens_assumed": {"prompt": 3500, "completion": 600},
        "sec_per_doc": {"low": 25.0, "likely": 70.0, "high": 150.0},
        "rationale": (
            "issue #21: FP16 isolation twin of run-20-correspondence-awq-c8 "
            "(identical seed-42 correspondence draw). Not run in the diagnosis "
            "PR; live compare is blocked until spend/auth go. Window 16384 is "
            "the L4-bf16 boot cap (AWQ c8 used 32768)."
        ),
    },
    "run-30-merger-specialist": {
        "task": "merger_agreement_specialist",
        "doc_class": "merger_agreement",
        "agent": "merger_agreement_specialist",
        "prompt_file": "merger_agreement_specialist_simplified",
        "concurrency": 3,
        "max_tokens": 4096,
        "max_input_chars": _input_chars_for(4096, 10000),
        "cost_cap_usd": 1.00,
        "max_wall_seconds": 5400,
        "tokens_assumed": {"prompt": 10000, "completion": 2800},
        "sec_per_doc": {"low": 100.0, "likely": 220.0, "high": 420.0},
        "rationale": (
            "Longest MAUD filings — lower concurrency protects KV; dedicated "
            "merger_agreement_specialist (not contracts); chunked extract for overflow."
        ),
    },
}

# Expected prepared-row count per specialist run (DMR-078 / SAND-018).
# run-30-* rows are the 5×30 suite; run-20-contracts-specialist is the SAND-018
# single-class 20-doc variant. benchmark_check enforces this per run_id, so a
# mis-sized YAML (e.g. a 20-doc config that forgot to lower the limit) cannot
# pass the loud gate by escaping the run-30-* heuristic.
SPECIALIST_LIMIT_BY_RUN: dict[str, int] = {
    "run-30-correspondence-specialist": 30,
    "run-30-insurance-claims-specialist": 30,
    "run-30-corporate-records-specialist": 30,
    "run-30-contracts-specialist": 30,
    "run-30-merger-specialist": 30,
    "run-20-contracts-specialist": 20,
    "run-20-contracts-awq": 20,
    "run-20-contracts-awq-c8": 20,
    "run-20-correspondence-awq": 20,
    "run-20-correspondence-awq-c8": 20,
    "run-20-correspondence-fp16-c8": 20,
    "run-20-insurance-claims-specialist-awq": 20,
    "run-20-correspondence-specialist-awq": 20,
    "run-50-correspondence-specialist-awq": 50,
    "run-20-contracts-granite": 20,
    "run-20-merger-granite": 20,
    "run-20-corporate-records-granite": 20,
    "run-20-correspondence-granite": 20,
    "run-20-insurance-claims-granite": 20,
    "run-50-correspondence-granite": 50,
    "run-01-contracts-granite-probe": 1,
    "run-02-contracts-granite-probe2": 1,
    # Qwen AWQ merger cross-agent leg (contracts_specialist on MAUD docs).
    "run-20-merger-specialist-awq": 20,
    # Qwen AWQ corporate leg (c=8 sibling of the insurance/correspondence AWQ runs).
    "run-20-corporate-records-specialist-awq": 20,
}


# ── SAND-032: ladder / scale-out / sweep / bf16 rows ─────────────────────────
# Generated from one table so caps/limits stay consistent with
# config/runs/sand032/sand032-*.yaml. max_tokens mirrors config/taxonomy.overlay.yaml
# (the runtime source of generation budgets — no run-scoped override), and
# tokens_assumed comes from the latest measured 20-doc AWQ runs.
_SAND032_AGENTS: dict[str, tuple[str, str, int, int, int]] = {
    # doc_class: (agent, prompt_file, max_tokens, prompt_tok, completion_tok)
    "correspondence": ("correspondence_specialist", "correspondence_specialist_production", 2048, 2300, 200),
    "insurance_claim": ("insurance_claims_specialist", "insurance_claims_specialist_simplified", 3072, 5000, 900),
    "corporate_record": ("corporate_records_specialist", "corporate_records_specialist_simplified", 4096, 8000, 1530),
    "merger_agreement": ("merger_agreement_specialist", "merger_agreement_specialist_simplified", 4096, 11300, 1200),
    "contract": ("contracts_specialist", "contracts_specialist_v33_simplified", 4096, 12000, 1200),
}
_SAND032_LADDER = ("l0-baseline", "l1-nothink", "l2-marlin", "l3-fp8kv", "l4-seqs16", "l5-graphs")
_SAND032_TABLE: tuple[tuple[str, str, int, int, int, float, int, int], ...] = (
    # run_id, doc_class, n, replicas, concurrency, cost_cap_usd, max_wall_seconds, max_model_len
    *((f"sand032-{rung}", "correspondence", 20, 1, 8, 0.15, 1800, 32768) for rung in _SAND032_LADDER),
    ("sand032-s2a-corr100-1rep", "correspondence", 100, 1, 8, 0.60, 3600, 32768),
    ("sand032-s2b-corr100-2rep", "correspondence", 100, 2, 16, 0.60, 3600, 32768),
    ("sand032-s3-corr50", "correspondence", 50, 2, 32, 0.30, 2400, 32768),
    ("sand032-s3-insurance50", "insurance_claim", 50, 2, 32, 0.60, 3600, 32768),
    ("sand032-s3-corporate50", "corporate_record", 50, 2, 32, 0.70, 3600, 32768),
    ("sand032-s3-merger50", "merger_agreement", 50, 2, 32, 1.40, 5400, 32768),
    ("sand032-s3-contracts50", "contract", 50, 2, 32, 1.40, 5400, 32768),
    ("sand032-s3-corr50-repeat", "correspondence", 50, 2, 32, 0.30, 2400, 32768),
    ("sand032-s4-corr20-bf16", "correspondence", 20, 1, 8, 0.20, 2400, 16384),
    ("sand032-s5-merger50-maud", "merger_agreement", 50, 2, 32, 1.40, 5400, 32768),
    # Stage 7 (B fleet): admission ×2 — max_num_seqs 32/replica, c64.
    ("sand032-s7-corr100-seqs32", "correspondence", 100, 2, 64, 0.60, 3600, 32768),
    ("sand032-s7-insurance50-seqs32", "insurance_claim", 50, 2, 64, 0.60, 3600, 32768),
    ("sand032-s7-corporate50-seqs32", "corporate_record", 50, 2, 64, 0.70, 3600, 32768),
    ("sand032-s7-corr100-seqs32-c48", "correspondence", 100, 2, 48, 0.60, 3600, 32768),
    ("sand032-s7-corr100-seqs32-c32", "correspondence", 100, 2, 32, 0.60, 3600, 32768),
    ("sand032-s7-contracts50-seqs32", "contract", 50, 2, 64, 1.40, 5400, 32768),
    # Stage 8 (C fleet): seqs32 + max_num_batched_tokens 16384 + gpu_memory_utilization 0.93.
    ("sand032-s8-corr100-bt16k", "correspondence", 100, 2, 64, 0.60, 3600, 32768),
    ("sand032-s8-contracts50-bt16k", "contract", 50, 2, 64, 1.40, 5400, 32768),
    # Stage 9 (balanced B): max_inputs 32 = max_num_seqs → router splits c64 32/32.
    ("sand032-s9-corr100-bal", "correspondence", 100, 2, 64, 0.60, 3600, 32768),
    ("sand032-s9-insurance50-bal", "insurance_claim", 50, 2, 64, 0.60, 3600, 32768),
    ("sand032-s9-corporate50-bal", "corporate_record", 50, 2, 64, 0.70, 3600, 32768),
    ("sand032-s9-contracts50-bal", "contract", 50, 2, 64, 1.40, 5400, 32768),
    # Stage 10: eval-environment v2 prompts, 1×L4 c8 (promotion check at larger n).
    ("sand032-s10-corr75-v2", "correspondence", 75, 1, 8, 0.15, 3600, 32768),
    ("sand032-s10-insurance75-v2", "insurance_claim", 75, 1, 8, 0.20, 3600, 32768),
    ("sand032-s10-corporate75-v2", "corporate_record", 75, 1, 8, 0.20, 3600, 32768),
)
# Stage 5 re-runs a class with a revised prompt; everything else stays frozen.
_SAND032_PROMPT_OVERRIDE = {
    "sand032-s5-merger50-maud": "merger_agreement_specialist_maud_v1",
    "sand032-s10-corr75-v2": "correspondence_specialist_v2_evalenv",
    "sand032-s10-insurance75-v2": "insurance_claims_specialist_v2_evalenv",
    "sand032-s10-corporate75-v2": "corporate_records_specialist_v2_evalenv",
}
SAND032_RUNS: frozenset[str] = frozenset(row[0] for row in _SAND032_TABLE)
for _rid, _cls, _n, _rep, _conc, _cap, _wall, _ctx in _SAND032_TABLE:
    _agent, _prompt, _mt, _pt, _ct = _SAND032_AGENTS[_cls]
    _prompt = _SAND032_PROMPT_OVERRIDE.get(_rid, _prompt)
    SPECIALIST_POSTURE[_rid] = {
        "task": _agent,
        "doc_class": _cls,
        "agent": _agent,
        "prompt_file": _prompt,
        "concurrency": _conc,
        "replicas": _rep,
        **({"max_num_seqs": 16} if _rid.startswith(("sand032-s3-", "sand032-s5-", "sand032-s10-")) else {}),
        **({"max_num_seqs": 32} if _rid.startswith(("sand032-s7-", "sand032-s8-", "sand032-s9-")) else {}),
        "max_model_len": _ctx,
        "max_tokens": _mt,
        "max_input_chars": _input_chars_for(_mt, _pt, _ctx),
        "cost_cap_usd": _cap,
        "max_wall_seconds": _wall,
        "tokens_assumed": {"prompt": _pt, "completion": _ct},
        "sec_per_doc": {"low": 5.0, "likely": 15.0, "high": 60.0},
        "rationale": (
            "SAND-032 ladder / scale-out / sweep "
            "(docs/superpowers/specs/2026-09-27-qwen3-l4-serving-ladder-design.md)"
        ),
    }
    SPECIALIST_LIMIT_BY_RUN[_rid] = _n

# SAND-032 Stage 6: LLM sorter at scale on the frozen 2×L4 fleet (not a specialist —
# the sorter reads the capped head of every doc class; overlay max_tokens 2048).
SAND032_SORTER_RUNS: frozenset[str] = frozenset({"sand032-s6-sorter1000", "sand032-s7-sorter1000-seqs32", "sand032-s8-sorter1000-bt16k"})
SPECIALIST_POSTURE["sand032-s6-sorter1000"] = {
    "task": "isolated",  # sorter agent alone, not the pipeline graph
    "doc_class": "all (sorter)",
    "agent": "sorter",
    "max_input_chars": 12000,  # config/taxonomy.overlay.yaml sorter cap
    "concurrency": 32,
    "replicas": 2,
    "max_num_seqs": 16,
    "max_model_len": 32768,
    "max_tokens": 2048,
    "cost_cap_usd": 0.8,
    "max_wall_seconds": 3600,
    "tokens_assumed": {"prompt": 1450, "completion": 150},
    "sec_per_doc": {"low": 0.15, "likely": 0.25, "high": 1.0},
    "rationale": "SAND-032 Stage 6 — 1000-doc train sorter on the frozen 2×L4 config",
}
SPECIALIST_LIMIT_BY_RUN["sand032-s6-sorter1000"] = 1000
# Stage 7 (B fleet): same sorter draw at admission ×2.
SPECIALIST_POSTURE["sand032-s7-sorter1000-seqs32"] = dict(
    SPECIALIST_POSTURE["sand032-s6-sorter1000"], concurrency=64, max_num_seqs=32,
    rationale="SAND-032 Stage 7 — sorter at max_num_seqs 32/replica, c64 (vs s6 seqs16 c32)",
)
SPECIALIST_LIMIT_BY_RUN["sand032-s7-sorter1000-seqs32"] = 1000
SPECIALIST_POSTURE["sand032-s8-sorter1000-bt16k"] = dict(
    SPECIALIST_POSTURE["sand032-s7-sorter1000-seqs32"],
    rationale="SAND-032 Stage 8 — sorter at seqs32 + max_num_batched_tokens 16384 + gpu_mem 0.93",
)
SPECIALIST_LIMIT_BY_RUN["sand032-s8-sorter1000-bt16k"] = 1000


# ── Qwen3-8B-AWQ specialist grid (missing 1×L4 / 2×L4 × n=20/50 cells) ────
# Decode 8192 (above the 4096 LengthFinishReasonError that truncated
# merger JSON on grid-20-merger-specialist-awq-1l4). Applied at
# `sandbox run start` via run-scoped SANDBOX_AGENT_KNOBS — do not raise
# the global overlay (bf16 16k window still uses 4096).
_GRID_AGENTS: dict[str, tuple[str, str, int, int, int]] = {
    "correspondence": ("correspondence_specialist", "correspondence_specialist_simplified", 8192, 3500, 800),
    "insurance_claim": ("insurance_claims_specialist", "insurance_claims_specialist_simplified", 8192, 4500, 1200),
    "corporate_record": ("corporate_records_specialist", "corporate_records_specialist_simplified", 8192, 5000, 1500),
    "merger_agreement": ("merger_agreement_specialist", "merger_agreement_specialist_simplified", 8192, 10000, 2500),
    "contract": ("contracts_specialist", "contracts_specialist_v33_simplified", 8192, 8000, 2500),
}
_GRID_TABLE: tuple[tuple[str, str, int, int, int, float, int, int], ...] = (
    # run_id, doc_class, n, replicas, concurrency, cost_cap, wall, max_num_seqs
    # ── Executed legacy cells (historical posture; superseded, see _GRID_LEGACY) ──
    ("grid-20-merger-specialist-awq-1l4", "merger_agreement", 20, 1, 8, 0.70, 3600, 8),
    # Clean 20-doc rerun: 4096 LengthFinish on the first 1×L4 cell; 8192 still
    # truncated contracts JSON — merger decode 16384 (fits 32768 − prompt).
    ("grid-20-merger-specialist-awq-1l4-retry", "merger_agreement", 20, 1, 8, 0.70, 3600, 8),
    ("grid-50-contracts-specialist-awq-2l4", "contract", 50, 2, 32, 1.20, 3600, 16),
    # ── SAND-037 aligned grid: 5 classes × n=20/50 × 1×L4 C8 / 2×L4 C32 ──────
    # One spec for every cell except n / replicas / concurrency: SAND-032 frozen
    # L5 engine (awq_marlin, fp8 KV, CUDA graphs, max_num_seqs 16 per replica,
    # thinking off, max_inputs 32), split=all single-class nested draws, frozen
    # v1 simplified prompts, decode 8192 at GRID_TEMPERATURE.
    ("grid-20-correspondence-specialist-awq-1l4", "correspondence", 20, 1, 8, 0.30, 2400, 16),
    ("grid-20-insurance-claims-specialist-awq-1l4", "insurance_claim", 20, 1, 8, 0.40, 2400, 16),
    ("grid-20-corporate-records-specialist-awq-1l4", "corporate_record", 20, 1, 8, 0.40, 2400, 16),
    ("grid-20-contracts-specialist-awq-1l4", "contract", 20, 1, 8, 0.70, 3600, 16),
    ("grid-20-merger-specialist-awq-1l4-rerun", "merger_agreement", 20, 1, 8, 0.70, 3600, 16),
    ("grid-50-correspondence-specialist-awq-1l4", "correspondence", 50, 1, 8, 0.40, 3600, 16),
    ("grid-50-insurance-claims-specialist-awq-1l4", "insurance_claim", 50, 1, 8, 0.50, 3600, 16),
    ("grid-50-corporate-records-specialist-awq-1l4", "corporate_record", 50, 1, 8, 0.50, 3600, 16),
    ("grid-50-contracts-specialist-awq-1l4", "contract", 50, 1, 8, 0.80, 4800, 16),
    ("grid-50-merger-specialist-awq-1l4", "merger_agreement", 50, 1, 8, 1.00, 5400, 16),
    ("grid-20-correspondence-specialist-awq-2l4", "correspondence", 20, 2, 32, 0.40, 2400, 16),
    ("grid-20-insurance-claims-specialist-awq-2l4", "insurance_claim", 20, 2, 32, 0.50, 2400, 16),
    ("grid-20-corporate-records-specialist-awq-2l4", "corporate_record", 20, 2, 32, 0.50, 2400, 16),
    ("grid-20-contracts-specialist-awq-2l4", "contract", 20, 2, 32, 0.80, 3200, 16),
    ("grid-20-merger-specialist-awq-2l4", "merger_agreement", 20, 2, 32, 1.00, 3600, 16),
    ("grid-50-correspondence-specialist-awq-2l4", "correspondence", 50, 2, 32, 0.60, 2400, 16),
    ("grid-50-insurance-claims-specialist-awq-2l4", "insurance_claim", 50, 2, 32, 0.80, 2400, 16),
    ("grid-50-corporate-records-specialist-awq-2l4", "corporate_record", 50, 2, 32, 0.80, 2400, 16),
    ("grid-50-contracts-specialist-awq-2l4-rerun", "contract", 50, 2, 32, 1.20, 3600, 16),
    ("grid-50-merger-specialist-awq-2l4", "merger_agreement", 50, 2, 32, 1.60, 4000, 16),
)
# Executed before SAND-037 aligned the grid; kept for their committed reports.
_GRID_LEGACY: frozenset[str] = frozenset({
    "grid-20-merger-specialist-awq-1l4",
    "grid-20-merger-specialist-awq-1l4-retry",
    "grid-50-contracts-specialist-awq-2l4",
})
# SAND-037 runaway-decode fix. Contracts and merger are the two specialists that
# decode under the JSON-schema grammar (langchain with_structured_output); at
# temperature 0.1 (near-greedy) they looped until every cap they were given —
# 4096, 8192 and 16384 — while their longest successful outputs were 1,695
# (merger, simplified) / 3,423 (merger, MAUD) / 4,055 (contracts) tokens, and job
# retries replayed the same loop. 0.7 is Qwen3's documented non-thinking setting
# ("do not use greedy decoding … endless repetitions"). The json_object classes
# (correspondence, insurance, corporate records) never hit a cap and keep the
# 0.1 every SAND-032 run used. Applied by mailroom_sandbox.sampling because the
# vendored call sites pass temperature=0.1 as a literal.
GRID_TEMPERATURE = 0.7
GRID_TEMPERATURE_BY_CLASS: dict[str, float] = {
    "contract": GRID_TEMPERATURE,
    "merger_agreement": GRID_TEMPERATURE,
}
GRID_RUNS: frozenset[str] = frozenset(row[0] for row in _GRID_TABLE)
GRID_TWO_GPU_RUNS: frozenset[str] = frozenset(r[0] for r in _GRID_TABLE if r[3] == 2)
GRID_ONE_GPU_RUNS: frozenset[str] = frozenset(r[0] for r in _GRID_TABLE if r[3] == 1)
# The 20 cells of the aligned grid (the runbooks run exactly these).
GRID_CELLS: frozenset[str] = GRID_RUNS - _GRID_LEGACY
for _rid, _cls, _n, _rep, _conc, _cap, _wall, _seqs in _GRID_TABLE:
    _agent, _prompt, _mt, _pt, _ct = _GRID_AGENTS[_cls]
    SPECIALIST_POSTURE[_rid] = {
        "task": _agent,
        "doc_class": _cls,
        "agent": _agent,
        "prompt_file": _prompt,
        "concurrency": _conc,
        "replicas": _rep,
        "max_num_seqs": _seqs,
        "max_model_len": 32768,
        "max_tokens": _mt,
        "max_input_chars": _input_chars_for(_mt, _pt, 32768),
        "cost_cap_usd": _cap,
        "max_wall_seconds": _wall,
        "tokens_assumed": {"prompt": _pt, "completion": _ct},
        "sec_per_doc": {"low": 10.0, "likely": 40.0, "high": 180.0},
        "rationale": "Qwen3-8B-AWQ specialist grid cell (v1 / simplified stem)",
    }
    if _rid in GRID_CELLS:
        _temp = GRID_TEMPERATURE_BY_CLASS.get(_cls)
        if _temp is not None:
            SPECIALIST_POSTURE[_rid]["temperature"] = _temp
        SPECIALIST_POSTURE[_rid]["rationale"] = (
            "SAND-037 aligned grid cell (frozen L5 engine, nested split=all draw, "
            f"v1 simplified stem, decode 8192 @ temperature {_temp or 0.1})"
        )
    SPECIALIST_LIMIT_BY_RUN[_rid] = _n

# Merger 1×L4 retry: raise decode above the 8192 contracts LengthFinish.
_MERGER_1L4_RETRY = "grid-20-merger-specialist-awq-1l4-retry"
if _MERGER_1L4_RETRY in SPECIALIST_POSTURE:
    SPECIALIST_POSTURE[_MERGER_1L4_RETRY]["max_tokens"] = 16384
    SPECIALIST_POSTURE[_MERGER_1L4_RETRY]["max_input_chars"] = _input_chars_for(
        16384, 10000, 32768
    )


def expected_limit(run_id: str | None, default: int = 30) -> int:
    """Expected prepared-row count for a specialist run (DMR-078 / SAND-018)."""
    if not run_id:
        return int(default)
    return int(SPECIALIST_LIMIT_BY_RUN.get(str(run_id), default))


# Overlay agent → generation budget (applied for all profiles; Modal L4 is the
# design target). Includes merger_agreement_specialist for the 1:1 live map.
AGENT_GENERATION_BUDGETS: dict[str, dict[str, int]] = {
    row["agent"]: {
        "max_tokens": int(row["max_tokens"]),
        "max_input_chars": int(row["max_input_chars"]),
    }
    for run_id, row in SPECIALIST_POSTURE.items()
    # SAND-032 / grid / SAND-040 / SAND-042 rows mirror overlay budgets; keep them
    # out of this last-writer-wins map so pre-existing agent budgets are unchanged.
    if not run_id.startswith(("sand032-", "grid-", "sand40-", "sand42-"))
}


def posture_for_run(run_id: str | None) -> dict[str, Any] | None:
    if not run_id:
        return None
    row = SPECIALIST_POSTURE.get(str(run_id))
    return dict(row) if row else None


def agent_knobs_for_run(run_id: str | None) -> dict[str, dict[str, Any]] | None:
    """Run-scoped generation budget for ``activate(..., agent_knobs=)``."""
    row = posture_for_run(run_id)
    if row is None:
        return None
    knobs: dict[str, Any] = {
        "max_tokens": int(row["max_tokens"]),
        "max_input_chars": int(row["max_input_chars"]),
    }
    if row.get("temperature") is not None:
        knobs["temperature"] = float(row["temperature"])
    # SAND-040 optimized cells: Qwen3 sampling, length re-sample, chunked extraction.
    for key in ("top_p", "top_k", "presence_penalty", "length_retries", "chunk_chars", "overlap_chars"):
        if row.get(key) is not None:
            knobs[key] = row[key]
    return {str(row["agent"]): knobs}


def expected_concurrency(run_id: str | None, default: int = 4) -> int:
    row = posture_for_run(run_id)
    if row is None:
        return int(default)
    return int(row["concurrency"])


def overlay_agent_knobs() -> dict[str, dict[str, Any]]:
    """Taxonomy overlay fragment for specialist generation budgets + Qwen effort."""
    out: dict[str, dict[str, Any]] = {}
    for agent, budget in AGENT_GENERATION_BUDGETS.items():
        out[agent] = {
            "temperature": 0.1,
            "max_tokens": budget["max_tokens"],
            "max_input_chars": budget["max_input_chars"],
            "reasoning_effort": "none",
        }
    return out


def context_fit_ok(
    max_tokens: int, max_input_chars: int, max_model_len: int = MAX_MODEL_LEN
) -> bool:
    """True when input chars + decode budget fit inside the run's context window.

    SAND-019: the window is per-run (bf16 default 16384; AWQ runs deploy at
    32768), so callers pass the row's ``max_model_len`` (default 16384).
    """
    input_tokens = int(max_input_chars / _CHARS_PER_TOKEN)
    return (input_tokens + int(max_tokens) + _SYSTEM_OVERHEAD_TOKENS) <= int(max_model_len)


def summarize_posture() -> list[dict[str, Any]]:
    """Table rows for docs / CLI."""
    rows = []
    for run_id, row in SPECIALIST_POSTURE.items():
        rows.append(
            {
                "run_id": run_id,
                "task": row["task"],
                "doc_class": row["doc_class"],
                "concurrency": row["concurrency"],
                "max_tokens": row["max_tokens"],
                "max_input_chars": row["max_input_chars"],
                "cost_cap_usd": row["cost_cap_usd"],
                "max_wall_seconds": row["max_wall_seconds"],
                "context_fit": context_fit_ok(
                    row["max_tokens"],
                    row["max_input_chars"],
                    int(row.get("max_model_len", MAX_MODEL_LEN)),
                ),
                "rationale": row["rationale"],
            }
        )
    return rows


def as_metrics_sec_tables() -> tuple[dict[str, dict[str, float]], dict[str, dict[str, int]]]:
    """Export sec/doc + token tables for ``job.metrics`` (single source)."""
    sec = {rid: dict(row["sec_per_doc"]) for rid, row in SPECIALIST_POSTURE.items()}
    tok = {rid: dict(row["tokens_assumed"]) for rid, row in SPECIALIST_POSTURE.items()}
    return sec, tok


def validate_mapping(mapping: Mapping[str, Any] | None = None) -> list[str]:
    """Return errors if posture rows fail context-fit or basic invariants."""
    errors: list[str] = []
    source = mapping or SPECIALIST_POSTURE
    for run_id, row in source.items():
        mt = int(row["max_tokens"])
        mic = int(row["max_input_chars"])
        window = int(row.get("max_model_len", MAX_MODEL_LEN))
        if not context_fit_ok(mt, mic, window):
            errors.append(
                f"{run_id}: max_tokens={mt} + max_input_chars={mic} exceed "
                f"Qwen L4 window {window}"
            )
        conc = int(row["concurrency"])
        # SAND-032: the band is per L4 replica — pinned data-parallel replicas
        # each admit up to 8, or up to the row's vLLM max_num_seqs when it
        # declares a larger admission (frozen seqs16 → 2×L4 best case c32).
        per_replica = max(8, int(row.get("max_num_seqs", 8)))
        ceiling = per_replica * max(1, int(row.get("replicas", 1)))
        # Single-doc probe instances (*-probe*) are serial by design — the same
        # exemption benchmark_check applies to the c>=2 throughput floor.
        floor = 1 if "-probe" in run_id else 2
        if not floor <= conc <= ceiling:
            errors.append(
                f"{run_id}: concurrency={conc} outside specialist band [{floor},{ceiling}]"
            )
        if float(row["cost_cap_usd"]) <= 0:
            errors.append(f"{run_id}: cost_cap_usd must be > 0")
        if int(row["max_wall_seconds"]) < 60:
            errors.append(f"{run_id}: max_wall_seconds too small")
    return errors


# ── SAND-042: paired concurrency × fleet grid on the SAND-037 aligned spec ────
# Five cells = {1×L4, 2×L4} × {client concurrency 8, 16} plus the 2×L4 C32
# saturation point (SAND-047), one warm fleet each
# (one cold boot per cell), five specialists per cell, n=50 per specialist on ONE
# shared subclass-stratified draw, so every cell scores the identical 250
# documents (paired). Client concurrency is split equally across replicas:
# 2×L4 C8 = 4 per replica, 2×L4 C16 = 8 per replica (the SAND-042 operator rule),
# so on 2×L4 the cell label is the per-replica load.
#
# The spec is the SAND-037 aligned grid unchanged — frozen L5 engine (awq_marlin,
# fp8 KV, CUDA graphs [1,2,4,8,16], max_num_seqs 16/replica, thinking off,
# max_inputs 32), v1 simplified stems, decode 8192, temperature 0.7 on the
# JSON-schema classes (contracts, merger) and the vendored 0.1 elsewhere. What
# SAND-042 adds is the measurement layer (container GPU telemetry: nvidia-smi
# util/power/temp/mem sampled inside the serving replica) and two postures
# SAND-037 never ran (C16 at all, and C8 on 2×L4 — SAND-037 ran C32 there).
#
# The 2×L4 cells are NOT a per-replica-load twin of the 1×L4 cells (C8/2 = 4,
# C16/2 = 8 per replica); the matched-load pairs are 1×L4 C8 vs 2×L4 C16 and
# 1×L4 C16 vs 2×L4 C32 (8 and 16 per replica each). See
# docs/SAND42-EXPERIMENT-DESIGN.md §3.
#
# C32 is the admitted amendment (SAND-047): 32 total = 16 per replica = the
# engine's own ``max_num_seqs``, i.e. the admission ceiling, and the exact
# per-replica load 1l4-c16 already ran — so 1l4-c16 vs 2l4-c32 is the
# matched-load scale-out pair AT saturation, and it replicates SAND-037's 2×L4
# C32 point. It was added after the four-cell grid landed, so it is the only
# cell whose row order postdates the others (the two original matched-load pairs
# keep the {8,16} concurrency arm). Its caps are the 2-replica row of
# ``_SAND42_CAPS`` — caps are keyed by replicas, not concurrency.
SAND42_N = 50
SAND42_CELLS_BY_ID: dict[str, tuple[int, int]] = {
    # cell id: (replicas, client concurrency)
    "1l4-c8": (1, 8),
    "1l4-c16": (1, 16),
    "2l4-c8": (2, 8),
    "2l4-c16": (2, 16),
    "2l4-c32": (2, 32),
}
# v1 simplified stems + decode 8192. Written out literally (not inherited from the
# grid table) so a future grid edit can never leak a production/v2/MAUD stem into
# SAND-042; ``_assert_sand42_prompts`` enforces the ``_simplified`` suffix.
_SAND42_AGENTS: dict[str, tuple[str, str, int, int, int]] = {
    # doc_class: (agent, prompt_file, max_tokens, prompt_tok, completion_tok)
    "correspondence": ("correspondence_specialist", "correspondence_specialist_simplified", 8192, 3500, 800),
    "insurance_claim": ("insurance_claims_specialist", "insurance_claims_specialist_simplified", 8192, 4500, 1200),
    "corporate_record": ("corporate_records_specialist", "corporate_records_specialist_simplified", 8192, 5000, 1500),
    "merger_agreement": ("merger_agreement_specialist", "merger_agreement_specialist_simplified", 8192, 10000, 2500),
    "contract": ("contracts_specialist", "contracts_specialist_v33_simplified", 8192, 8000, 2500),
}


def _assert_sand42_prompts(agents: dict[str, tuple[str, str, int, int, int]]) -> None:
    """SAND-042 is the v1 simplified stem family, nothing else."""
    bad = {cls: row[1] for cls, row in agents.items() if not row[1].endswith("_simplified")}
    if bad:
        raise ValueError(f"SAND-042 prompts must all be *_simplified stems; got {bad}")


_assert_sand42_prompts(_SAND42_AGENTS)

# Long-document classes. ``_input_chars_for`` sizes ``max_input_chars`` from an
# ASSUMED prompt length (``1.25 x prompt_tokens``), which is right for short classes
# but wrong for contracts: it yields 24,000 chars while the real SAND-042 draw runs to
# 300,768 chars. Measured on that draw, the cap silently dropped **62 % of all
# contract text** — and, per the truncation marker in ``base_agent.truncate_input``,
# the omitted span is the middle, which is where the operative clauses live.
#
# Contracts therefore run the pipeline's own chunked pass (overlapping
# paragraph-aware windows + deterministic merge: list fields union with dedupe,
# scalars keep the first non-null, confidence takes the max) instead of a head+tail
# truncation. ``extract_chunked`` falls through to plain single-pass ``extract`` when
# the document fits one window, so small-document output is unchanged.
#
# Sizing: every request must fit the 32K window, because ``extract_chunked`` skips a
# failed chunk *silently*. The context-fit guard (2.4 chars/token + 4,000 system
# tokens) therefore allows 49,382 chars beside the 8,192 output cap; ``chunk_window``
# then holds each window to ``budget - overlap`` so a chunk plus its overlap tail
# still fits. Measured cost: 50 -> 85 calls, 1.09M input tokens (~2.8x), ~$0.26 and
# ~18 min — inside the existing $0.90 / 4800 s abort cap, so the cap does not move.
#
# Merger is here too, on the operator's instruction: its defect is far worse — 50/50
# documents exceed the cap, 93 % of text is dropped, and a run saw 7 % of each
# 270k-505k-char agreement. This cell measured the consequence directly: MAUD accuracy
# 0.0 with 0-1 of 13-17 questions answered, extraction F1 0.0, plus degenerate
# `No-Shop: Yes` x 22 repetition and 3/50 (6 %) LengthFinishReasonError hard failures.
# Those are not merger-quality measurements. Merger therefore takes the SAND-040
# optimised posture (see below) rather than a head+tail truncation.
_SAND42_CHUNKED: dict[str, dict[str, Any]] = {
    "contract": {"max_input_chars": 49_000, "chunk_chars": 43_000, "overlap_chars": 6_000},
    # Merger adopts the SAND-040 optimised long-document posture verbatim — the most
    # efficient method this repo has for whole-document merger extraction, and the one
    # the A100-era merger cards converged on (95 % util, ~$0.004/doc):
    #   chunked whole-document windows (47k / 6.5k overlap), Qwen3 non-thinking
    #   sampling (0.7 / top_p 0.8 / top_k 20 / presence 1.0) to suppress the runaway
    #   repetition this cell just measured (`No-Shop: Yes` x 22), a 6144 output cap,
    #   and ONE re-sample on LengthFinishReasonError — which is what produced the
    #   3/50 (6 %) hard failures at 8192 with no retry.
    # Fits the 32K window exactly: 54000/2.4 + 6144 + 4000 = 32644 <= 32768.
    "merger_agreement": {
        "max_input_chars": 54_000,
        "chunk_chars": 47_000,
        "overlap_chars": 6_500,
        "max_tokens": 6_144,
        "top_p": 0.8,
        "top_k": 20,
        "presence_penalty": 1.0,
        "length_retries": 1,
    },
}

_SAND42_CLASS_SLUG: dict[str, str] = {
    "correspondence": "correspondence",
    "insurance_claim": "insurance-claims",
    "corporate_record": "corporate-records",
    "contract": "contracts",
    "merger_agreement": "merger",
}
# Abort guards (not estimates). 1×L4 mirrors the SAND-037 C8 n=50 caps; 2×L4 bills
# two GPUs so its caps are ~1.5×; the C16 legs carry extra headroom on the long
# classes because a wider batch lengthens the tail on contracts and merger.
# Merger's cap is derived from the MEASURED probe (2026-10-12): 5 merger agreements
# = 1,702,602 chars took 438 s warm on one L4, so the 18,160,427-char draw is
# 438 x 10.66 = 4,671 s ~= 1.30 h ~= $1.04 of GPU. The cap is that with ~55 %
# headroom; the pre-probe $1.25 / 5400 s guard would have aborted a legitimate run.
_SAND42_CAPS: dict[int, dict[str, float]] = {
    1: {"correspondence": 0.45, "insurance_claim": 0.55, "corporate_record": 0.55,
        "contract": 0.90, "merger_agreement": 1.70},
    2: {"correspondence": 0.65, "insurance_claim": 0.85, "corporate_record": 0.85,
        "contract": 1.30, "merger_agreement": 2.55},
}
_SAND42_WALLS: dict[str, int] = {
    "correspondence": 2400, "insurance_claim": 2400, "corporate_record": 2400,
    "contract": 4800, "merger_agreement": 7200,
}


def sand42_run_id(cell: str, doc_class: str) -> str:
    """Run id for one SAND-042 cell × specialist (cell ∈ ``SAND42_CELLS_BY_ID``)."""
    if cell not in SAND42_CELLS_BY_ID:
        raise KeyError(f"unknown SAND-042 cell {cell!r}")
    return f"sand42-50-{_SAND42_CLASS_SLUG[doc_class]}-specialist-awq-{cell}"


SAND42_RUNS: frozenset[str] = frozenset(
    sand42_run_id(cell, dc) for cell in SAND42_CELLS_BY_ID for dc in _SAND42_AGENTS
)
for _cell, (_rep, _conc) in SAND42_CELLS_BY_ID.items():
    for _cls, (_agent, _prompt, _mt, _pt, _ct) in _SAND42_AGENTS.items():
        _rid = sand42_run_id(_cell, _cls)
        _chunk = _SAND42_CHUNKED.get(_cls)
        _mt_eff = int(_chunk.get("max_tokens") or _mt) if _chunk else _mt
        SPECIALIST_POSTURE[_rid] = {
            "task": _agent,
            "doc_class": _cls,
            "agent": _agent,
            "prompt_file": _prompt,
            "concurrency": _conc,
            "replicas": _rep,
            "max_num_seqs": 16,
            "max_model_len": 32768,
            "max_tokens": _mt_eff,
            "max_input_chars": (
                _chunk["max_input_chars"] if _chunk else _input_chars_for(_mt, _pt, 32768)
            ),
            "cost_cap_usd": _SAND42_CAPS[_rep][_cls],
            "max_wall_seconds": _SAND42_WALLS[_cls],
            "tokens_assumed": {"prompt": _pt, "completion": _ct},
            "sec_per_doc": {"low": 10.0, "likely": 40.0, "high": 180.0},
            "rationale": (
                f"SAND-042 paired grid cell ({_rep}×L4, client concurrency {_conc}"
                + (f", {_conc // _rep} per replica" if _rep > 1 else "")
                + ") — SAND-037 aligned spec, v1 simplified stem, decode 8192"
                + (", whole-document chunked extract (no truncation)" if _chunk else "")
            ),
        }
        _temp = GRID_TEMPERATURE_BY_CLASS.get(_cls)
        if _temp is not None:
            SPECIALIST_POSTURE[_rid]["temperature"] = _temp
        if _chunk:
            # chunk_chars / overlap_chars plus any optimised sampling knobs
            # (top_p, top_k, presence_penalty, length_retries).
            for _key, _val in _chunk.items():
                if _key != "max_input_chars":
                    SPECIALIST_POSTURE[_rid][_key] = _val
        SPECIALIST_LIMIT_BY_RUN[_rid] = SAND42_N

SAND42_TWO_GPU_RUNS: frozenset[str] = frozenset(
    sand42_run_id(cell, dc)
    for cell, (rep, _conc) in SAND42_CELLS_BY_ID.items()
    if rep == 2
    for dc in _SAND42_AGENTS
)
SAND42_ONE_GPU_RUNS: frozenset[str] = SAND42_RUNS - SAND42_TWO_GPU_RUNS

# Noise-floor leg: a second identical run of one cell on the same 50 documents, so
# the run-to-run SD of the difference is re-measured on the SAND-042 draw before
# any delta is quoted (docs/SAND42-EXPERIMENT-DESIGN.md §4).
SAND42_NOISE_FLOOR_RUN = "sand42-noisefloor-correspondence-awq-1l4-c8"
SPECIALIST_POSTURE[SAND42_NOISE_FLOOR_RUN] = {
    **SPECIALIST_POSTURE[sand42_run_id("1l4-c8", "correspondence")],
    "rationale": (
        "SAND-042 noise-floor leg — same 50 correspondence documents and settings as "
        f"{sand42_run_id('1l4-c8', 'correspondence')}; the per-document score "
        "differences between the two are the run-to-run noise floor for every "
        "SAND-042 delta"
    ),
}
SPECIALIST_LIMIT_BY_RUN[SAND42_NOISE_FLOOR_RUN] = SAND42_N

# Smoke leg: 5 corporate records drawn as a STRICT SUBSET of the 1L4-c8 condition's
# 50 (each sub-quota <= its 50-draw quota, and a smaller quota is a seeded prefix of
# the larger one). Same engine, prompt, decode and gates as the condition, at n=5, to
# prove the deploy env, the draw, the scored path and the GPU telemetry before the
# four scored conditions spend. Not a benchmark cell.
SAND42_CHECK_RUN = "sand42-check-5-corporate-records-awq-1l4-c8"
SPECIALIST_POSTURE[SAND42_CHECK_RUN] = {
    "task": "corporate_records_specialist",
    "doc_class": "corporate_record",
    "agent": "corporate_records_specialist",
    "prompt_file": "corporate_records_specialist_simplified",
    "concurrency": 8,
    "replicas": 1,
    "max_num_seqs": 16,
    "max_model_len": 32768,
    "max_tokens": 8192,
    "max_input_chars": _input_chars_for(8192, 5000, 32768),
    "cost_cap_usd": 0.20,
    "max_wall_seconds": 1800,
    "tokens_assumed": {"prompt": 5000, "completion": 1500},
    "sec_per_doc": {"low": 10.0, "likely": 40.0, "high": 180.0},
    "rationale": (
        "SAND-042 live smoke leg — 5 corporate records, a strict subset of the "
        "1L4-c8 condition's 50-document draw"
    ),
}
SPECIALIST_LIMIT_BY_RUN[SAND42_CHECK_RUN] = 5

# Merger probe leg: 5 merger agreements drawn as a STRICT SUBSET of the 1L4-c8
# condition's 50. It exists to MEASURE the chunked whole-document path's real wall
# before the four scored conditions commit ~2 GPU-hours per merger cell — the
# extrapolation from the truncated run's throughput was not good enough to spend on.
# It inherits the condition's knobs wholesale (chunking, 6144 cap, sampling, length
# re-sample), so it cannot drift from the path it is measuring; only the caps differ.
SAND42_CHECK_MERGER_RUN = "sand42-check-5-merger-specialist-awq-1l4-c8"
SPECIALIST_POSTURE[SAND42_CHECK_MERGER_RUN] = {
    **SPECIALIST_POSTURE[sand42_run_id("1l4-c8", "merger_agreement")],
    "cost_cap_usd": 0.60,
    "max_wall_seconds": 3600,
    "rationale": (
        "SAND-042 merger probe — 5 merger agreements, a strict subset of the 1L4-c8 "
        "condition's 50-document draw, measuring the chunked whole-document wall"
    ),
}
SPECIALIST_LIMIT_BY_RUN[SAND42_CHECK_MERGER_RUN] = 5
SAND42_CHECK_RUNS: frozenset[str] = frozenset({SAND42_CHECK_RUN, SAND42_CHECK_MERGER_RUN})
# It rides the same pinned single-L4 fleet as the C8 condition.
SAND42_ONE_GPU_RUNS = SAND42_ONE_GPU_RUNS | SAND42_CHECK_RUNS | {SAND42_NOISE_FLOOR_RUN}


def sand42_cell_label(run_id: str | None) -> str:
    """Telemetry volume label for a SAND-042 cell (one deploy = one series).

    Every run in a cell derives the same label, so the scraper finds the cell's
    time series whichever of the five configs it is pointed at.
    """
    rid = str(run_id or "")
    if not rid.startswith("sand42-"):
        return ""
    for cell in SAND42_CELLS_BY_ID:
        if rid.endswith(f"-{cell}"):
            return f"sand42-{cell}"
    return ""


# ── SAND-040: 2×L4 · C32 scale run on one 32K deploy ──────────────────────────
# One deploy of the SAND-037 2×L4 engine (native 32768 window), no redeploy:
#   * correspondence, insurance claims, corporate records, contracts: n=100 on the SAND-037
#     aligned spec unchanged (pure scale, nested 20 ⊂ 50 ⊂ 100);
#   * merger agreements: n=50 (the SAND-37 2×L4 agreements) with the optimized † settings —
#     chunked whole-document extraction (the pipeline's own pass: overlapping windows,
#     deterministic merge) instead of a 30,000-char head+tail, the MAUD v1 prompt, Qwen3
#     non-thinking sampling (0.7 / top_p 0.8 / top_k 20 / presence 1.0), a 6144 output cap
#     and one re-sample on LengthFinishReasonError.
# The 64K YaRN window is dropped: on matched documents the n=20 probes showed no contracts
# gain (−0.002) and a merger gain (+0.081 MAUD accuracy) that comes from chunking, which
# the 32K window can carry with smaller chunks.
#
# 32K chunk sizing. vLLM rejects a request whose prompt + max_tokens exceeds the window, and
# extract_chunked() skips a failed chunk silently, so every request must fit. The posture
# context-fit guard (2.4 chars/token + 4,000 system tokens) allows 54,000 chars beside a
# 6,144 output cap; SAND-37 merger requests measured ≥ 3.3 chars/token, so the real margin
# is wider. max_input_chars 54,000 → window 47,000 + overlap 6,500 (≤ budget / 8); a chunk
# plus its overlap tail stays ≤ 54,000 chars.
# A 5-agreement gate cell (the seeded prefix of the 50) runs first on the same deploy;
# `sandbox run card --gate` checks every expected chunk reached vLLM before the n=50 cell.
SAND40_MAX_MODEL_LEN = 65536  # executed 64K probes only
SAND40_HF_OVERRIDES: dict[str, Any] = {
    "rope_parameters": {
        "rope_type": "yarn",
        "factor": 2.0,
        "original_max_position_embeddings": 32768,
        "rope_theta": 1000000,
    }
}
SAND40_OPTIMIZED_KNOBS: dict[str, Any] = {
    "max_tokens": 6144,
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 20,
    "presence_penalty": 1.0,
    "length_retries": 1,
}
SAND40_LONG_KNOBS: dict[str, Any] = {  # 64K probes (2026-10-01)
    **SAND40_OPTIMIZED_KNOBS,
    "max_input_chars": 128000,
    "chunk_chars": 120000,
    "overlap_chars": 8000,
}
SAND40_MERGER_32K_KNOBS: dict[str, Any] = {
    **SAND40_OPTIMIZED_KNOBS,
    "max_input_chars": 54000,
    "chunk_chars": 47000,
    "overlap_chars": 6500,
}
SAND40_PROMPTS: dict[str, str] = {"merger_agreement": "merger_agreement_specialist_maud_v1"}
# variant: "aligned" = SAND-037 spec unchanged; "opt32k" = † merger on 32K; "probe64k" = executed probe.
_SAND40_TABLE: tuple[tuple[str, str, int, str, float, int], ...] = (
    # run_id, doc_class, n, variant, cost_cap, max_wall
    ("sand40-100-correspondence-specialist-awq-2l4", "correspondence", 100, "aligned", 1.00, 3600),
    ("sand40-100-insurance-claims-specialist-awq-2l4", "insurance_claim", 100, "aligned", 1.20, 3600),
    ("sand40-100-corporate-records-specialist-awq-2l4", "corporate_record", 100, "aligned", 1.20, 3600),
    ("sand40-100-contracts-specialist-awq-2l4", "contract", 100, "aligned", 1.20, 3600),
    ("sand40-50-merger-specialist-awq-2l4", "merger_agreement", 50, "opt32k", 2.50, 5400),
    # Gate: first 5 of the 50 agreements, same settings, runs before the n=50 cell.
    ("sand40-check-5-merger-specialist-awq-2l4", "merger_agreement", 5, "opt32k", 0.40, 1800),
    # Validation probes (executed 2026-10-01): nested n=20 on the 64K engine.
    ("sand40-probe-20-contracts-specialist-awq-2l4-64k", "contract", 20, "probe64k", 0.80, 2400),
    ("sand40-probe-20-merger-specialist-awq-2l4-64k", "merger_agreement", 20, "probe64k", 1.00, 3600),
)
SAND40_CELLS: frozenset[str] = frozenset(
    r[0] for r in _SAND40_TABLE if "-probe-" not in r[0] and "-check-" not in r[0]
)
SAND40_CHECK_CELLS: frozenset[str] = frozenset(r[0] for r in _SAND40_TABLE if "-check-" in r[0])
SAND40_PROBE_CELLS: frozenset[str] = frozenset(r[0] for r in _SAND40_TABLE if "-probe-" in r[0])
SAND40_LONG_CELLS: frozenset[str] = frozenset(r[0] for r in _SAND40_TABLE if r[3] == "probe64k")
SAND40_OPTIMIZED_CELLS: frozenset[str] = frozenset(r[0] for r in _SAND40_TABLE if r[3] != "aligned")
for _rid, _cls, _n, _variant, _cap, _wall in _SAND40_TABLE:
    _agent, _prompt, _mt, _pt, _ct = _GRID_AGENTS[_cls]
    _optimized = _variant != "aligned"
    _row: dict[str, Any] = {
        "task": _agent,
        "doc_class": _cls,
        "agent": _agent,
        "prompt_file": SAND40_PROMPTS.get(_cls, _prompt) if _optimized else _prompt,
        "concurrency": 32,
        "replicas": 2,
        "max_num_seqs": 16,
        "max_model_len": SAND40_MAX_MODEL_LEN if _variant == "probe64k" else 32768,
        "max_tokens": _mt,
        "max_input_chars": _input_chars_for(_mt, _pt, 32768),
        "cost_cap_usd": _cap,
        "max_wall_seconds": _wall,
        "tokens_assumed": {"prompt": _pt, "completion": _ct},
        "sec_per_doc": {"low": 10.0, "likely": 40.0, "high": 240.0},
        "rationale": "SAND-040 scale cell: SAND-037 aligned spec unchanged at n=100 (nested 50 ⊂ 100)",
    }
    _temp = GRID_TEMPERATURE_BY_CLASS.get(_cls)
    if _temp is not None:
        _row["temperature"] = _temp
    if _optimized:
        _row.update(SAND40_LONG_KNOBS if _variant == "probe64k" else SAND40_MERGER_32K_KNOBS)
        _row["optimized"] = True
        _row["tokens_assumed"] = {"prompt": 30000 if _cls == "contract" else 140000, "completion": 2500 if _cls == "contract" else 4500}
        _window = "64K YaRN window, 128k-char input" if _variant == "probe64k" else "32K window, 54k-char chunks"
        _row["rationale"] = (
            f"SAND-040 optimized long-document cell: {_window}, pipeline chunked extraction, "
            "Qwen3 sampling (0.7 / top_p 0.8 / top_k 20 / presence 1.0), 6144 cap + one length re-sample"
            + ("; MAUD v1 prompt" if _cls in SAND40_PROMPTS else "")
        )
    SPECIALIST_POSTURE[_rid] = _row
    SPECIALIST_LIMIT_BY_RUN[_rid] = _n
