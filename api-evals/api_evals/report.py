"""api_evals.report — markdown + JSON report generation for api-evals runs.

Writes ``api-evals/reports/<stamp>/`` with:
* ``report.json``  — the machine-readable full result (per run + per item)
* ``report.md``    — the human-readable cost comparison tables
* ``costs.csv``    — per-run one-line summary (for spreadsheets)

Also prints a compact console table via ``render_console``.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api_evals.registry import REPORTS_DIR
from api_evals.scoring import extraction_score, headline_scores


def _fmt_usd(value: float | None) -> str:
    if value is None:
        return "-"
    if value == 0:
        return "$0.000000"
    if value < 0.01:
        return f"${value:.6f}"
    if value < 100:
        return f"${value:.4f}"
    return f"${value:,.2f}"


def _fmt_num(value: float | None, digits: int = 2) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_report(
    results: list[dict[str, Any]],
    *,
    model: str,
    prices: tuple[float, float] | None,
    caveats: list[str] | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Assemble the full report dict from per-run results."""
    runs = []
    for r in results:
        cost = r.get("cost") or {}
        runs.append(
            {
                "run_id": r["run_id"],
                "task": r["task"],
                "n": r["n"],
                "model": r.get("model"),
                "n_ok": cost.get("n_ok"),
                "prompt_tokens": cost.get("prompt_tokens"),
                "completion_tokens": cost.get("completion_tokens"),
                "total_tokens": cost.get("total_tokens"),
                "tokens_per_document": cost.get("tokens_per_document"),
                "cost_usd": cost.get("cost_usd"),
                "cost_per_document": cost.get("cost_per_document"),
                "price_per_million_in": cost.get("price_per_million_in"),
                "price_per_million_out": cost.get("price_per_million_out"),
                "scores": headline_scores(r.get("scores")),
                "extraction_score": extraction_score(r.get("scores")),
                "wall_seconds": r.get("wall_seconds"),
                "spec_hash": r.get("spec_hash"),
                "dataset_fingerprint": r.get("dataset_fingerprint"),
                "cost_gaps": cost.get("honest_gaps") or [],
            }
        )
    return {
        "provider": "openrouter",
        "model": model,
        "price_per_million_in": prices[0] if prices else None,
        "price_per_million_out": prices[1] if prices else None,
        "generated_at": _now_stamp(),
        "run_count": len(runs),
        "runs": runs,
        "source": source,
        "caveats": list(caveats or []),
    }


def _group_by_doc_class(runs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for r in runs:
        cls = str(r.get("task") or "?").replace("_specialist", "").replace("_", " ")
        out.setdefault(cls, []).append(r)
    for key in out:
        out[key].sort(key=lambda r: int(r.get("n") or 0))
    return out


def markdown(report: dict[str, Any], *, unit_cost_min: float | None = None, unit_cost_max: float | None = None) -> str:
    """Render the human-readable cost comparison markdown."""
    price_note = (
        f"- List price: **${report.get('price_per_million_in')}/1M in · "
        f"${report.get('price_per_million_out')}/1M out** (verified OpenRouter /models)"
        if report.get("price_per_million_in") is not None
        else "- List price: **unknown** (gaps on every run)"
    )
    lines = [
        "# api-evals — OpenRouter API cost comparison",
        "",
        f"- Provider: **{report.get('provider')}** · model: **{report.get('model')}**",
        f"- Generated: {report.get('generated_at')} UTC · runs: {report.get('run_count')}",
        price_note,
    ]
    if report.get("source"):
        lines.append(f"- Data source: `{report.get('source')}`")
    lines.append("")
    for caveat in report.get("caveats") or []:
        lines.append(f"- **Caveat:** {caveat}")
    if report.get("caveats"):
        lines.append("")

    for cls, runs in _group_by_doc_class(report.get("runs") or []).items():
        lines += [
            f"## {cls} specialist",
            "",
            "| n docs | ok | prompt tok | completion tok | total tok | tok/doc | **total $** | **$/doc** | extract | wall (s) |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for r in runs:
            lines.append(
                f"| {r['n']} | {r.get('n_ok') or '-'} | {r.get('prompt_tokens') or '-'} | "
                f"{r.get('completion_tokens') or '-'} | {r.get('total_tokens') or '-'} | "
                f"{_fmt_num(r.get('tokens_per_document'))} | {_fmt_usd(r.get('cost_usd'))} | "
                f"{_fmt_usd(r.get('cost_per_document'))} | "
                f"{_fmt_num(r.get('extraction_score'), 4) if r.get('extraction_score') is not None else '-'} | "
                f"{_fmt_num(r.get('wall_seconds'), 1)} |"
            )
        # N-scaling linearity check: $/doc should be ~flat as N grows.
        costs = [r.get("cost_usd") for r in runs]
        ns = [r.get("n") for r in runs]
        if len(runs) >= 2 and all(c is not None for c in costs) and all(n for n in ns):
            cpd = [c / n for c, n in zip(costs, ns)]
            spread = (max(cpd) - min(cpd)) / min(cpd) * 100.0 if min(cpd) else None
            if spread is not None:
                lines += [
                    "",
                    f"- $/doc spread across N: **{spread:.1f}%** "
                    + ("(linear — cost scales with docs)" if spread < 15 else "(non-linear — investigate)"),
                ]
        gaps = [g for r in runs for g in (r.get("cost_gaps") or [])]
        if gaps:
            lines += ["", "Honest gaps:"]
            lines += [f"  - {g}" for g in sorted(set(gaps))]
        lines.append("")

    # Aggregate across both specialists.
    total_cost = sum(r.get("cost_usd") or 0.0 for r in report.get("runs") or [])
    total_docs = sum(r.get("n") or 0 for r in report.get("runs") or [])
    lines += [
        "## Aggregate",
        "",
        f"- **Total API spend across all {report.get('run_count')} runs: {_fmt_usd(total_cost)}** "
        f"({total_docs} docs)",
    ]
    agg_cpd = total_cost / total_docs if (total_cost and total_docs) else None
    if agg_cpd is not None:
        lines.append(f"- Blended $/doc: {_fmt_usd(agg_cpd)}")
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, Any], *, model: str) -> dict[str, Path]:
    """Persist report.json / report.md / costs.csv under reports/<stamp>/."""
    stamp = _now_stamp()
    out_dir = REPORTS_DIR / f"{stamp}-{model.replace('/', '-')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(markdown(report), encoding="utf-8")

    rows = report.get("runs") or []
    with (out_dir / "costs.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "run_id", "task", "n", "n_ok", "prompt_tokens", "completion_tokens",
                "total_tokens", "tokens_per_document", "cost_usd", "cost_per_document",
                "extraction_score", "wall_seconds", "dataset_fingerprint",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k) for k in writer.fieldnames})
    return {
        "json": out_dir / "report.json",
        "markdown": out_dir / "report.md",
        "csv": out_dir / "costs.csv",
        "dir": out_dir,
    }


def render_console(report: dict[str, Any]) -> str:
    lines = ["api-evals report:"]
    for r in report.get("runs") or []:
        lines.append(
            f"  {r['run_id']:28s} n={r['n']:4d} tok/doc={_fmt_num(r.get('tokens_per_document')):>10s} "
            f"total={_fmt_usd(r.get('cost_usd')):>12s} $/doc={_fmt_usd(r.get('cost_per_document')):>12s} "
            f"extract={_fmt_num(r.get('extraction_score'), 4)}"
        )
    return "\n".join(lines)
