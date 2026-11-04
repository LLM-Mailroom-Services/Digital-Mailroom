"""SAND-032: turn measured unit costs into funding line items.

Every projection is a transparent formula over measured inputs. The spread
comes from measured run-to-run variance (``rel_spread``), never a guess.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UnitCost:
    doc_class: str
    usd_per_doc: float
    rel_spread: float  # e.g. 0.10 = ±10% from repeat / paired runs


def full_corpus_usd(
    units: dict[str, UnitCost],
    rows: dict[str, int],
    *,
    overhead_usd: float,
    seeds: int,
) -> tuple[float, float, float]:
    """(low, mid, high) = Σ rows × $/doc × seeds (± spread) + overhead."""
    low = mid = high = 0.0
    for cls, n in rows.items():
        if cls not in units:
            raise KeyError(f"no measured unit cost for class {cls}")
        u = units[cls]
        base = n * u.usd_per_doc * seeds
        mid += base
        low += base * (1 - u.rel_spread)
        high += base * (1 + u.rel_spread)
    return (low + overhead_usd, mid + overhead_usd, high + overhead_usd)


def eval_iteration_usd(unit: UnitCost, n: int, *, overhead_usd: float) -> float:
    """One prompt-optimization eval: n docs on a warm fleet + per-iteration overhead."""
    return n * unit.usd_per_doc + overhead_usd


def with_contingency(usd: float, rate: float) -> float:
    return usd * (1 + rate)


def tier_budget(
    tier_usd: float, *, contingency: float, line_items: dict[str, float]
) -> dict[str, int]:
    """Whole units of each line item that fit, greedily in the given order."""
    spendable = tier_usd / (1 + contingency)
    out: dict[str, int] = {}
    for name, cost in line_items.items():
        if cost <= 0:
            raise ValueError(f"line item {name} must have a positive measured cost")
        count = int(spendable // cost)
        out[name] = count
        spendable -= count * cost
    return out
