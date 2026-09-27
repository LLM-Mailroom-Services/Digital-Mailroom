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
_SYSTEM_OVERHEAD_TOKENS = 2000

# Conservative chars/token for dense legal text when converting token budgets
# into ``max_input_chars`` (overlay / taxonomy).
_CHARS_PER_TOKEN = 3.5


def _input_chars_for(max_tokens: int, prompt_tokens: int | None = None) -> int:
    """Chars that fit with max_tokens + system overhead under MAX_MODEL_LEN.

    When ``prompt_tokens`` is known, also cap at ~1.25× the assumed prompt so
    short doc classes (correspondence) do not over-prefill into empty context.
    """
    available = max(1024, MAX_MODEL_LEN - int(max_tokens) - _SYSTEM_OVERHEAD_TOKENS)
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
        "prompt_file": "correspondence_specialist_production",
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
        "prompt_file": "insurance_claims_specialist_production",
        "concurrency": 5,
        "max_tokens": 3072,
        "max_input_chars": _input_chars_for(3072, 4500),
        "cost_cap_usd": 0.50,
        "max_wall_seconds": 3000,
        "tokens_assumed": {"prompt": 4500, "completion": 1000},
        "sec_per_doc": {"low": 45.0, "likely": 95.0, "high": 200.0},
        "rationale": "Mid-length claims tables — moderate concurrency; decode capped below 8192.",
    },
    "run-30-corporate-records-specialist": {
        "task": "corporate_records_specialist",
        "doc_class": "corporate_record",
        "agent": "corporate_records_specialist",
        "prompt_file": "corporate_records_specialist_production",
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
        "prompt_file": "contracts_specialist_v33",
        "concurrency": 4,
        "max_tokens": 4096,
        "max_input_chars": _input_chars_for(4096, 8000),
        "cost_cap_usd": 0.80,
        "max_wall_seconds": 4800,
        "tokens_assumed": {"prompt": 8000, "completion": 2000},
        "sec_per_doc": {"low": 70.0, "likely": 160.0, "high": 360.0},
        "rationale": "Long CUAD contracts — context-fit input cap (was 100k chars, over 16k window).",
    },
    "run-30-merger-specialist": {
        "task": "merger_agreement_specialist",
        "doc_class": "merger_agreement",
        "agent": "merger_agreement_specialist",
        "prompt_file": "merger_agreement_specialist_production",
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

# Overlay agent → generation budget (applied for all profiles; Modal L4 is the
# design target). Includes merger_agreement_specialist for the 1:1 live map.
AGENT_GENERATION_BUDGETS: dict[str, dict[str, int]] = {
    row["agent"]: {
        "max_tokens": int(row["max_tokens"]),
        "max_input_chars": int(row["max_input_chars"]),
    }
    for row in SPECIALIST_POSTURE.values()
}


def posture_for_run(run_id: str | None) -> dict[str, Any] | None:
    if not run_id:
        return None
    row = SPECIALIST_POSTURE.get(str(run_id))
    return dict(row) if row else None


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


def context_fit_ok(max_tokens: int, max_input_chars: int) -> bool:
    """True when input chars + decode budget fit inside MAX_MODEL_LEN."""
    input_tokens = int(max_input_chars / _CHARS_PER_TOKEN)
    return (input_tokens + int(max_tokens) + _SYSTEM_OVERHEAD_TOKENS) <= MAX_MODEL_LEN


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
                "context_fit": context_fit_ok(row["max_tokens"], row["max_input_chars"]),
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
        if not context_fit_ok(mt, mic):
            errors.append(
                f"{run_id}: max_tokens={mt} + max_input_chars={mic} exceed "
                f"Qwen L4 window {MAX_MODEL_LEN}"
            )
        conc = int(row["concurrency"])
        if not 2 <= conc <= 6:
            errors.append(f"{run_id}: concurrency={conc} outside specialist band [2,6]")
        if float(row["cost_cap_usd"]) <= 0:
            errors.append(f"{run_id}: cost_cap_usd must be > 0")
        if int(row["max_wall_seconds"]) < 60:
            errors.append(f"{run_id}: max_wall_seconds too small")
    return errors
