"""api_evals.cost — REAL OpenRouter API cost accounting.

Cost honesty contract
---------------------
* The billed amount for an OpenRouter call is ``prompt_tokens x in_price/1M +
  completion_tokens x out_price/1M`` — that is EXACTLY how OpenRouter computes
  the response's ``usage.cost`` (verified on 2026-09-25: a 17-prompt/5-completion
  call at $0.03/$0.13 per 1M reported ``usage.cost = 1.16e-06``).
* ``live_prices()`` refreshes the per-1M list prices from
  ``GET https://openrouter.ai/api/v1/models`` at run time; the registry's
  ``DEFAULT_LIST_PRICES`` is the offline/fallback pin (same values verified
  against the live payload).
* Never fabricate $0 or a price: when neither live nor fallback prices resolve
  for the model, cost fields stay ``None`` and an honest gap is reported.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

from api_evals.registry import DEFAULT_API_MODEL, DEFAULT_LIST_PRICES

_log = logging.getLogger("api_evals.cost")

PRICES_URL = "https://openrouter.ai/api/v1/models"


def live_prices(model: str = DEFAULT_API_MODEL, timeout: float = 15.0) -> tuple[float, float] | None:
    """Refresh per-1M USD (prompt, completion) for the model from OpenRouter.

    OpenRouter's /models payload prices per TOKEN; we normalize to per-1M so
    the returned tuple is directly comparable to the sandbox cost table (and
    every cost formula divides by 1e6). Returns None when the refresh fails
    (offline / non-2xx / unknown model) — callers fall back to
    ``DEFAULT_LIST_PRICES``.
    """
    try:
        with urllib.request.urlopen(PRICES_URL, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        for entry in payload.get("data", []):
            if entry.get("id") == model:
                pricing = entry.get("pricing") or {}
                pin = pricing.get("prompt")
                pout = pricing.get("completion")
                if pin is not None and pout is not None:
                    # OpenRouter /models reports PRICE PER TOKEN (e.g. 3.0e-08);
                    # the sandbox/dojo price table is per-1M tokens. Normalize
                    # to per-1M so every downstream multiply divides by 1e6
                    # consistently (a per-token value divided by 1e6 again
                    # would understate cost by 1e6x).
                    return round(float(pin) * 1_000_000, 6), round(float(pout) * 1_000_000, 6)
        _log.warning("live price refresh: model %r not in OpenRouter /models", model)
    except Exception as exc:  # noqa: BLE001 — offline refresh must never crash a run
        _log.warning("live price refresh failed for %r — falling back to pin: %s", model, exc)
    return None


def resolve_prices(model: str = DEFAULT_API_MODEL) -> tuple[float, float] | None:
    """Live prices first, then the verified registry pin (offline-safe)."""
    live = live_prices(model)
    if live is not None:
        return live
    return DEFAULT_LIST_PRICES.get(model)


def price_or_gap(model: str, *, prices: tuple[float, float] | None) -> dict[str, Any]:
    """Price + source marker for a model; honest gap when unknown."""
    resolved = prices or resolve_prices(model)
    if resolved is None:
        return {"model": model, "price_per_million_in": None, "price_per_million_out": None, "price_gap": True}
    return {
        "model": model,
        "price_per_million_in": resolved[0],
        "price_per_million_out": resolved[1],
        "price_gap": False,
    }


def item_cost_usd(
    prompt_tokens: int,
    completion_tokens: int,
    prices: tuple[float, float] | None,
) -> float | None:
    """OpenRouter-style USD for one item; None when tokens or prices missing."""
    if prices is None:
        return None
    prompt = int(prompt_tokens or 0)
    completion = int(completion_tokens or 0)
    if prompt + completion <= 0:
        return None
    per_million_in, per_million_out = prices
    return round(prompt * per_million_in / 1_000_000 + completion * per_million_out / 1_000_000, 8)


def cost_from_aggregate(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    n: int,
    model: str = DEFAULT_API_MODEL,
    prices: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Cost summary from an AGGREGATE record (no per-item rows available).

    Used when a run is resumed from a terminal store / experiment-log record
    whose per-item rows were not persisted. Same price math as
    ``cost_from_rows`` — real OpenRouter tokens x list price.
    """
    prices = prices or resolve_prices(model)
    prompt = int(prompt_tokens or 0)
    completion = int(completion_tokens or 0)
    total = prompt + completion
    cost_total = item_cost_usd(prompt, completion, prices) if total else None
    return {
        "model": model,
        "n": int(n or 0),
        "n_ok": int(n or 0),
        "price_per_million_in": prices[0] if prices else None,
        "price_per_million_out": prices[1] if prices else None,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
        "prompt_tokens_per_document": round(prompt / n, 2) if n else None,
        "completion_tokens_per_document": round(completion / n, 2) if n else None,
        "tokens_per_document": round(total / n, 2) if n else None,
        "cost_usd": cost_total,
        "cost_per_document": round(cost_total / n, 8) if (cost_total is not None and n) else None,
        "cost_per_item": None,
        "honest_gaps": (["no price resolved"] if prices is None else []),
    }


def cost_from_rows(
    rows: list[dict[str, Any]],
    *,
    model: str = DEFAULT_API_MODEL,
    prices: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Aggregate per-item rows (from the run's result) into a cost summary.

    ``rows`` entries carry ``prompt_tokens`` / ``completion_tokens`` /
    ``latency_ms`` per item (the sandbox isolated runner's merge_item_metrics).
    Failed items still count their tokens (cost is real even for failures).
    """
    prices = prices or resolve_prices(model)
    ok_rows = [r for r in rows if not r.get("error")]
    prompt_total = sum(int(r.get("prompt_tokens") or 0) for r in rows)
    completion_total = sum(int(r.get("completion_tokens") or 0) for r in rows)
    total_tokens = prompt_total + completion_total
    n = len(rows)
    n_ok = len(ok_rows)

    cost_total = item_cost_usd(prompt_total, completion_total, prices) if total_tokens else None
    per_item: list[float | None] = [
        item_cost_usd(int(r.get("prompt_tokens") or 0), int(r.get("completion_tokens") or 0), prices)
        for r in rows
    ]
    per_doc = round(cost_total / n_ok, 8) if (cost_total is not None and n_ok) else None
    tokens_per_doc = round(total_tokens / n, 2) if n else None
    prompt_per_doc = round(prompt_total / n, 2) if n else None
    completion_per_doc = round(completion_total / n, 2) if n else None

    gaps: list[str] = []
    if prices is None:
        gaps.append(f"no price resolved for model {model!r} (live + registry pin) — cost fields ABSENT")
    if total_tokens <= 0 and n:
        gaps.append("0 tokens recorded — check that the OpenAI-compatible server returns usage")

    return {
        "model": model,
        "n": n,
        "n_ok": n_ok,
        "price_per_million_in": prices[0] if prices else None,
        "price_per_million_out": prices[1] if prices else None,
        "prompt_tokens": prompt_total,
        "completion_tokens": completion_total,
        "total_tokens": total_tokens,
        "prompt_tokens_per_document": prompt_per_doc,
        "completion_tokens_per_document": completion_per_doc,
        "tokens_per_document": tokens_per_doc,
        "cost_usd": cost_total,
        "cost_per_document": per_doc,
        "cost_per_item": per_item,
        "honest_gaps": gaps,
    }
