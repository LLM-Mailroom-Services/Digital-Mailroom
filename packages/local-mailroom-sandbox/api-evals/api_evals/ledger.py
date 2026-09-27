"""Tracked QWEN-flash cost ledger (issue #40).

``reports/qwen-flash-cost-source.json`` holds the three known OpenRouter flash
runs so cost reports rebuild from a clean checkout without the gitignored
``reports/experiment_log.jsonl``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from api_evals.cost import cost_from_aggregate

_LEDGER_REL = Path("reports") / "qwen-flash-cost-source.json"


def ledger_path(root: Path | None = None) -> Path:
    if root is None:
        root = Path(__file__).resolve().parent.parent.parent
    return root / _LEDGER_REL


def load_ledger(path: Path | None = None) -> dict[str, Any]:
    src = path or ledger_path()
    if not src.is_file():
        raise FileNotFoundError(
            f"cost ledger not found at {src} — commit reports/qwen-flash-cost-source.json "
            "or pass an alternate path"
        )
    data = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "records" not in data:
        raise ValueError(f"{src}: ledger must be an object with a records array")
    return data


def price_pin(ledger: dict[str, Any]) -> tuple[float, float] | None:
    pin = ledger.get("price_pin") or {}
    pin_in = pin.get("price_per_million_in_usd")
    pin_out = pin.get("price_per_million_out_usd")
    if pin_in is None or pin_out is None:
        return None
    return float(pin_in), float(pin_out)


def price_mismatch_warnings(
    ledger: dict[str, Any],
    *,
    active_prices: tuple[float, float] | None,
) -> list[str]:
    """Surface when live/--prices values differ from the ledger pin."""
    pin = price_pin(ledger)
    if pin is None or active_prices is None:
        return []
    if pin == active_prices:
        return []
    return [
        "price mismatch: active prices "
        f"${active_prices[0]}/1M in · ${active_prices[1]}/1M out "
        f"≠ ledger pin ${pin[0]}/1M in · ${pin[1]}/1M out "
        f"({(ledger.get('price_pin') or {}).get('verified_at', 'unknown')} /models snapshot) "
        "— report uses active prices; reconcile before publishing"
    ]


def ledger_to_results(
    ledger: dict[str, Any],
    *,
    prices: tuple[float, float] | None,
) -> list[dict[str, Any]]:
    """Convert ledger records into api-evals result dicts (real API $ from tokens)."""
    model = str(ledger.get("model") or "qwen/qwen3.7-flash")
    gaps = price_mismatch_warnings(ledger, active_prices=prices)
    out: list[dict[str, Any]] = []
    for rec in ledger.get("records") or []:
        if not isinstance(rec, dict):
            continue
        n = int(rec.get("n") or 0)
        cost = cost_from_aggregate(
            prompt_tokens=int(rec.get("prompt_tokens") or 0),
            completion_tokens=int(rec.get("completion_tokens") or 0),
            n=n,
            model=str(rec.get("model") or model),
            prices=prices,
        )
        if gaps:
            cost["honest_gaps"] = list(cost.get("honest_gaps") or []) + gaps
        out.append(
            {
                "run_id": str(rec.get("run_id") or ""),
                "task": str(rec.get("task") or ""),
                "n": n,
                "model": rec.get("model") or model,
                "scores": rec.get("scores") or {},
                "wall_seconds": rec.get("wall_seconds"),
                "spec_hash": rec.get("spec_hash") or "",
                "dataset_fingerprint": rec.get("dataset_fingerprint") or "",
                "ledger": {
                    "experiment_name": rec.get("experiment_name"),
                    "timestamp": rec.get("timestamp"),
                    "estimated_gpu_cost_usd": rec.get("estimated_gpu_cost_usd"),
                    "prompt_version": rec.get("prompt_version"),
                },
                "cost": cost,
            }
        )
    return out
