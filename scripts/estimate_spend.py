#!/usr/bin/env python3
"""Estimate the OpenRouter spend of planned runs and check it fits the key's remaining limit
less the untouchable reserve (``spend.KEY_RESERVE_USD``).

For each run config: documents (the locked dataset.jsonl when preflighted, else the spec's
local file), calls per document (chunked agents read a long document in windows), prompt
overhead per call, and output per call give input/output tokens; priced at the engine model's
list price, and at the cap price the spend gate charges (every token at the run's highest
route). The total is compared with the key's live ``limit_remaining``
(``OPENROUTER_API_KEY``; never printed).

    OPENROUTER_API_KEY=... python scripts/estimate_spend.py config/runs/a.yaml config/runs/b.yaml
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import yaml

from mailroom_sandbox.paths import repo_root

CHARS_PER_TOKEN = 4.0
# System prompt chars per call, measured on the vendored agents (2026-11-01).
PROMPT_CHARS = {
    "sorter": 3_681 + 5_490,  # sorter_condensed_v1 rendered + the subclass catalog (V15: 25,074 + 5,490)
    "contracts_specialist": 9_882, "merger_agreement_specialist": 6_116, "corporate_records_specialist": 5_865,
    "correspondence_specialist": 6_113, "insurance_claims_specialist": 6_277,
}
OUTPUT_TOKENS = {"sorter": 150, "specialist": 1_500, "decisions": 0}
V15_SORTER_CHARS = 25_074 + 5_490


def _rows(spec: dict, root: Path) -> list[dict]:
    locked = root / "data" / "runtime" / "runs" / spec["run_id"] / "dataset.jsonl"
    path = locked if locked.exists() else root / str((spec.get("dataset") or {}).get("local_path") or "")
    if not path.is_file():
        raise SystemExit(f"{spec['run_id']}: no documents (preflight it, or give dataset.local_path)")
    with path.open(encoding="utf-8", newline="\n") as handle:
        return [json.loads(line) for line in handle.read().split("\n") if line.strip()]


def _sorter_prompt_chars(spec: dict) -> int:
    agents = ((spec.get("prompt") or {}).get("agents") or {})
    return PROMPT_CHARS["sorter"] if (agents.get("sorter") or {}).get("file") else V15_SORTER_CHARS


def _specialist_prompt_chars(spec: dict, agent: str, root: Path) -> int:
    """System prompt chars: a pinned local file's own length, else the frozen default's."""
    pinned = (((spec.get("prompt") or {}).get("agents") or {}).get(agent) or {}).get("file")
    path = root / "config" / "prompts" / f"{pinned}.txt" if pinned else None
    if path is not None and path.is_file():
        return len(path.read_text(encoding="utf-8"))
    return PROMPT_CHARS.get(agent, 6_000)


def _price(model: str | None, prompt_tokens: float) -> tuple[float, float]:
    """``call_price`` at this call size; an unpriced model fails closed instead of costing $0."""
    from mailroom_sandbox.job.metrics import call_price

    price = call_price(model, prompt_tokens)
    if price is None:
        raise SystemExit(f"no token price for {model!r}: add it to config/api_prices.yaml or set "
                         "SANDBOX_TOKEN_PRICE_IN_PER_M and SANDBOX_TOKEN_PRICE_OUT_PER_M")
    return price


def estimate(spec: dict, root: Path) -> dict:

    task = spec.get("task")
    # An isolated run's agent is job.task (default sorter, as the spec model fills it).
    job_task = (spec.get("job") or {}).get("task") or ("sorter" if task == "isolated" else task)
    model = (spec.get("engine") or {}).get("model")
    rows = _rows(spec, root)
    lengths = [len(r.get("doc_text") or "") for r in rows]
    reviewer = spec.get("reviewer") or {}
    if reviewer.get("backend") == "decisions":
        from mailroom_sandbox.decision_backends import decision_questions, gate_questions, load_question_set

        qset = load_question_set(reviewer["questions"])
        limit_by = qset.get("max_input_chars_by_class") or {}
        limit = int(qset.get("max_input_chars") or 120_000)
        tokens_in = usd = 0.0
        for row, n in zip(rows, lengths):
            cls = row.get("expected_doc_class")
            q = gate_questions(qset, cls) if task == "extraction_gate" else decision_questions(qset)
            handoff = 1_500 if task == "extraction_gate" else 200   # extraction / sorter answer, chars
            t = (min(n, int(limit_by.get(cls) or limit)) + len(json.dumps(q)) + handoff) / CHARS_PER_TOKEN
            tokens_in += t
            usd += t * _price(model, t)[0] / 1e6
        tokens_out, calls = 0.0, len(rows)
    else:
        agent = job_task if job_task in PROMPT_CHARS else task
        knobs = ((spec.get("agent_knobs") or {}).get(agent) or {})
        prompt = _sorter_prompt_chars(spec) if agent == "sorter" else _specialist_prompt_chars(spec, agent, root)
        window = int(knobs.get("chunk_chars") or 0)
        cap = int(knobs.get("max_input_chars") or 10**9)
        calls = 0
        tokens_in = usd = 0.0
        out_per_call = OUTPUT_TOKENS["sorter" if agent == "sorter" else "specialist"]
        for n in lengths:
            k = max(1, math.ceil(n / window)) if window and n > cap else 1
            read = n + (k - 1) * int(knobs.get("overlap_chars") or 0) if k > 1 else min(n, cap)
            calls += k
            t = (read + k * prompt) / CHARS_PER_TOKEN
            tokens_in += t
            p_in, p_out = _price(model, t / k)   # each call priced at its own tier
            usd += (t * p_in + k * out_per_call * p_out) / 1e6
        tokens_out = calls * out_per_call
    list_usd = usd
    return {"run_id": spec["run_id"], "model": model, "documents": len(rows), "calls": calls,
            "input_tokens_m": round(tokens_in / 1e6, 3), "output_tokens_m": round(tokens_out / 1e6, 3),
            "list_usd": round(list_usd, 3), "api_cap_usd": (spec.get("job") or {}).get("api_cost_cap_usd")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("configs", nargs="+")
    parser.add_argument("--margin", type=float, default=1.25, help="safety factor on the list estimate")
    args = parser.parse_args()
    root = repo_root()
    out = [estimate(yaml.safe_load(Path(c).read_text(encoding="utf-8")), root) for c in args.configs]
    print(f"{'run_id':52} {'docs':>5} {'calls':>6} {'in(M)':>7} {'out(M)':>7} {'list$':>7} {'cap$':>6}")
    for r in out:
        print(f"{r['run_id']:52} {r['documents']:>5} {r['calls']:>6} {r['input_tokens_m']:>7} {r['output_tokens_m']:>7} "
              f"{r['list_usd']:>7} {r['api_cap_usd'] if r['api_cap_usd'] is not None else '-':>6}")
    total = sum(r["list_usd"] for r in out)
    caps = sum(float(r["api_cap_usd"] or 0) for r in out)
    print(f"{'TOTAL':52} {'':>5} {'':>6} {'':>7} {'':>7} {total:>7.3f} {caps:>6.2f}")
    if os.environ.get("OPENROUTER_API_KEY", "").strip():
        from mailroom_sandbox.job.spend import key_headroom, key_reserve_usd, spendable_usd

        head = key_headroom()
        remaining = head.get("limit_remaining")
        spendable = spendable_usd(remaining)
        fits = spendable is None or total * args.margin <= spendable
        print(f"key remaining: {remaining} USD (limit {head.get('limit')}, reset {head.get('limit_reset')}); "
              f"reserve {key_reserve_usd():.2f} USD -> spendable {spendable if spendable is None else round(spendable, 2)} USD; "
              f"estimate x{args.margin} = {total * args.margin:.2f} USD -> {'FITS' if fits else 'DOES NOT FIT'}")
        if spendable is not None and caps > spendable:
            print(f"note: the caps sum to {caps:.2f} USD, above what is spendable; each run is checked at its own start")
        return 0 if fits else 1
    print("OPENROUTER_API_KEY not set: key headroom not checked", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
