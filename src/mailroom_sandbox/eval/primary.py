"""The two primary tasks: ``specialist [TARGET]`` and ``pipeline [--class CLASS]``.

Level 1 picks the family, level 2 narrows it to one target:

- ``specialist`` runs all five live-class specialists in isolation;
  ``specialist contract`` runs one.
- ``pipeline`` runs every document through the full connected graph;
  ``pipeline --class contract`` runs only that class's documents through it.

Targets accept the document class (``contract``), the specialist agent
(``contracts_specialist``) or its short name (``contracts``), so one
vocabulary works at both levels. Every other eval task stays runnable for old
run configs but is not listed as a primary operation.
"""

from __future__ import annotations

from typing import Any

PRIMARY_TASKS = ("specialist", "pipeline")

# 1:1 live-class specialists (HUB-015): document class -> specialist agent.
SPECIALISTS: dict[str, str] = {
    "contract": "contracts_specialist",
    "merger_agreement": "merger_agreement_specialist",
    "corporate_record": "corporate_records_specialist",
    "correspondence": "correspondence_specialist",
    "insurance_claim": "insurance_claims_specialist",
}
DOC_CLASSES = tuple(SPECIALISTS)

_ALIASES: dict[str, str] = {}
for _cls, _agent in SPECIALISTS.items():
    for _name in (_cls, _agent, _agent.removesuffix("_specialist"), _cls.split("_")[0]):
        _ALIASES[_name] = _cls


def target_names() -> tuple[str, ...]:
    """Every accepted spelling, for completion and error messages."""
    return tuple(sorted(_ALIASES))


def resolve_class(target: str | None) -> str | None:
    """Normalize any target spelling to its document class; ``None`` means all."""
    if target is None or not str(target).strip():
        return None
    key = str(target).strip().lower().replace("-", "_")
    if key not in _ALIASES:
        raise ValueError(f"unknown target {target!r}; use one of {', '.join(DOC_CLASSES)} (or the specialist name)")
    return _ALIASES[key]


def specialists_for(target: str | None) -> list[str]:
    cls = resolve_class(target)
    return list(SPECIALISTS.values()) if cls is None else [SPECIALISTS[cls]]


def row_class(row: dict[str, Any]) -> str:
    return str(row.get("expected_doc_class") or row.get("doc_type") or row.get("doc_class") or "")


def rows_for_class(rows: list[dict[str, Any]], target: str | None) -> list[dict[str, Any]]:
    cls = resolve_class(target)
    if cls is None:
        return rows
    kept = [row for row in rows if row_class(row) == cls]
    if not kept:
        raise ValueError(f"no {cls} documents in this dataset; drop --class or pick another class")
    return kept


def run_specialist_eval(target: str | None = None, *, progress_cb: Any = None, **kwargs: Any) -> dict[str, Any]:
    """Isolated eval of one specialist, or all five in a fixed order.

    One target returns that specialist's own result unchanged (same record and
    experiment name as ``eval <name>_specialist``). The sweep returns each
    result under its agent name plus a one-line summary per specialist.
    """
    from mailroom_sandbox.eval import runners

    agents = specialists_for(target)
    base_name = kwargs.pop("experiment_name", None)
    results: dict[str, Any] = {}
    for agent in agents:
        name = base_name if len(agents) == 1 else (f"{base_name}_{agent}" if base_name else None)
        results[agent] = runners.run_isolated_eval(agent, experiment_name=name, progress_cb=progress_cb, **kwargs)
    if len(agents) == 1:
        return results[agents[0]]
    return {
        "task": "specialist",
        "targets": agents,
        "summary": {agent: _headline(result) for agent, result in results.items()},
        "results": results,
    }


def _headline(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    scores = result.get("scores") if isinstance(result.get("scores"), dict) else {}
    keep = ("n", "accuracy", "overall_extraction_score", "field_f1", "error_count")
    out = {key: scores[key] for key in keep if key in scores}
    if "n" not in out and result.get("n") is not None:
        out["n"] = result["n"]
    return out
