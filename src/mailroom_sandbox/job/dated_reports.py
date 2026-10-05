"""Dated specialist report tree for new Qwen3-8B-AWQ (and later) cells.

New runs write quality + serving artifacts under::

    reports/YYYY-MM-DD/<specialist>/...  # unassociated run
    reports/SAND-XX/YYYY-MM-DD/<specialist>/...  # associated sweep

``YYYY-MM-DD`` is the **local** calendar date. Machine-readable serving
exports use ``reports/serving/SAND-XX/<shape>/n=<N>/`` for associated sweeps;
unassociated runs use the general dated tree. Existing flat exports remain
readable by the scorecard command.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.paths import repo_root
from mailroom_sandbox.report_paths import experiment_prefix

_log = logging.getLogger("mailroom_sandbox.job.dated_reports")

# User-facing specialist dirs (do not reuse historical reports/{merger,contract}/).
SPECIALIST_DIRS: dict[str, str] = {
    "contracts_specialist": "contracts",
    "contract": "contracts",
    "merger_agreement_specialist": "merger_agreement",
    "merger_agreement": "merger_agreement",
    "corporate_records_specialist": "corporate_records",
    "corporate_record": "corporate_records",
    "correspondence_specialist": "correspondence",
    "correspondence": "correspondence",
    "insurance_claims_specialist": "insurance_claims",
    "insurance_claim": "insurance_claims",
}

_STEM_SHORT: dict[str, str] = {
    "contracts": "CONTRACTS",
    "merger_agreement": "MERGER",
    "corporate_records": "CORPORATE",
    "correspondence": "CORRESPONDENCE",
    "insurance_claims": "INSURANCE",
}


def local_report_date(*, now: datetime | None = None) -> str:
    stamp = now or datetime.now().astimezone()
    return stamp.strftime("%Y-%m-%d")


def specialist_dir_name(task: str | None, doc_class: str | None = None) -> str | None:
    for key in (task, doc_class):
        if key and str(key) in SPECIALIST_DIRS:
            return SPECIALIST_DIRS[str(key)]
    return None


def _quant_tag(model: str) -> str:
    upper = (model or "").upper()
    if "AWQ" in upper:
        return "AWQ"
    if "FP8" in upper:
        return "FP8"
    return "BF16"


def _cell_n(store: RunStore, lock: Mapping[str, Any], items: list) -> int:
    dataset = lock.get("dataset") if isinstance(lock.get("dataset"), dict) else {}
    limit = dataset.get("limit") if isinstance(dataset, dict) else None
    if isinstance(limit, int) and limit > 0:
        return limit
    cp = store.read_checkpoint() or {}
    total = cp.get("total")
    if isinstance(total, int) and total > 0:
        return total
    return max(len(items), 1)


def _dated_reports_root(store: RunStore, root: Path) -> Path:
    lock = store.read_lock() or {}
    prefix = experiment_prefix(store.run_id, lock)
    return root / "reports" / prefix if prefix else root / "reports"


def cell_stem(store: RunStore, *, lock: Mapping[str, Any] | None = None) -> tuple[str, str] | None:
    """Return ``(specialist_dir, filename_stem)`` or None if not a specialist cell."""
    lock = lock if lock is not None else (store.read_lock() or {})
    task = str(lock.get("task") or "")
    folder = specialist_dir_name(task)
    if folder is None:
        return None
    engine = lock.get("engine") if isinstance(lock.get("engine"), dict) else {}
    modal = engine.get("modal") if isinstance(engine, dict) else {}
    job = lock.get("job") if isinstance(lock.get("job"), dict) else {}
    items = store.load_items()
    n = _cell_n(store, lock, items)
    replicas = max(1, int((modal or {}).get("max_containers") or 1))
    conc = max(1, int((job or {}).get("concurrency") or 1))
    model = str((engine or {}).get("model") or "")
    short = _STEM_SHORT[folder]
    run_id = str(lock.get("run_id") or getattr(store, "run_id", "") or "")
    suffix = "-RETRY" if run_id.endswith("-retry") else ""
    stem = f"RUN-{n}-{short}-{_quant_tag(model)}-{replicas}L4-C{conc}{suffix}"
    return folder, stem


def dated_cell_dir(
    store: RunStore,
    *,
    repo: Path | None = None,
    now: datetime | None = None,
) -> Path | None:
    mapped = cell_stem(store)
    if mapped is None:
        return None
    folder, _stem = mapped
    root = repo or repo_root()
    return _dated_reports_root(store, root) / local_report_date(now=now) / folder


def dated_cell_paths(
    store: RunStore,
    *,
    repo: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Path] | None:
    mapped = cell_stem(store)
    if mapped is None:
        return None
    folder, stem = mapped
    root = repo or repo_root()
    day_dir = _dated_reports_root(store, root) / local_report_date(now=now) / folder
    return {
        "dir": day_dir,
        "report": day_dir / f"{stem}-REPORT.md",
        "serving_md": day_dir / f"{stem}-SERVING.md",
        "serving_json": day_dir / f"{stem}.serving.json",
        "stem": Path(stem),
    }


def serving_export_path(store: RunStore, *, repo: Path | None = None) -> Path | None:
    """Canonical machine-readable serving path for a stored run."""
    root = repo or repo_root()
    run_id = str(store.run_id)
    lock = store.read_lock() or {}
    prefix = experiment_prefix(run_id, lock)
    mapped = cell_stem(store)
    if mapped is not None and prefix:
        engine = lock.get("engine") if isinstance(lock.get("engine"), dict) else {}
        modal = engine.get("modal") if isinstance(engine.get("modal"), dict) else {}
        replicas = max(1, int(modal.get("max_containers") or 1))
        shape = f"{replicas}L4"
        if run_id.startswith(("sand40-probe-", "sand40-check-")):
            folder = "probes"
        else:
            folder = f"n={_cell_n(store, lock, store.load_items())}"
        return root / "reports" / "serving" / prefix / shape / folder / f"{run_id}.serving.json"
    if prefix:
        return root / "reports" / "serving" / prefix / f"{run_id}.serving.json"
    if mapped is not None:
        folder, _stem = mapped
        return root / "reports" / "serving" / local_report_date() / folder / f"{run_id}.serving.json"
    return None


def _fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}g}" if abs(value) < 0.01 else f"{value:.{min(digits, 6)}f}"
    return str(value)


def _mean_item_score(items: list[Mapping[str, Any]]) -> float | None:
    vals: list[float] = []
    for row in items:
        score = row.get("score")
        if isinstance(score, dict) and score.get("overall_extraction_score") is not None:
            try:
                vals.append(float(score["overall_extraction_score"]))
            except (TypeError, ValueError):
                continue
    if not vals:
        return None
    return sum(vals) / len(vals)


def render_quality_report(
    store: RunStore,
    rec: Mapping[str, Any],
    *,
    scores: Mapping[str, Any] | None = None,
) -> str:
    lock = store.read_lock() or {}
    engine = lock.get("engine") if isinstance(lock.get("engine"), dict) else {}
    modal = (engine or {}).get("modal") if isinstance(engine, dict) else {}
    job = lock.get("job") if isinstance(lock.get("job"), dict) else {}
    prompt = lock.get("prompt") if isinstance(lock.get("prompt"), dict) else {}
    items = store.load_items()
    n_ok = sum(1 for i in items if i.get("ok", True) is not False)
    n_err = sum(1 for i in items if i.get("ok") is False)
    mean_score = _mean_item_score(items)
    scores = scores or rec.get("scores") or {}
    overall = scores.get("overall_extraction_score")
    if overall is None:
        overall = mean_score
    mapped = cell_stem(store, lock=lock)
    stem = mapped[1] if mapped else store.run_id
    replicas = max(1, int((modal or {}).get("max_containers") or rec.get("replicas") or 1))
    conc = int((job or {}).get("concurrency") or rec.get("concurrency") or 1)
    model = str((engine or {}).get("model") or rec.get("model") or "")
    lines = [
        f"# Run report — `{store.run_id}`",
        "",
        f"Dated cell stem: `{stem}`. Written automatically under the local-date specialist tree.",
        "",
        "| | |",
        "| --- | --- |",
        f"| run_id | `{store.run_id}` |",
        f"| task / agent | `{lock.get('task')}` |",
        f"| prompt | `{rec.get('prompt_version') or (prompt.get('default') or {})}` |",
        f"| engine | `{model}` |",
        f"| GPU shape | **{replicas}×{(modal or {}).get('gpu') or rec.get('gpu') or 'L4'}** |",
        f"| concurrency | **{conc}** |",
        f"| n | **{_cell_n(store, lock, items)}** |",
        f"| profile | `{lock.get('profile')}` |",
        f"| spec_hash | `{store.spec_hash() or ''}` |",
        f"| dataset fingerprint | `{rec.get('dataset_fingerprint') or '—'}` |",
        "",
        "## Headline results",
        "",
        "| metric | value |",
        "| --- | --- |",
        f"| docs ok / failed / total | **{n_ok} / {n_err} / {len(items)}** |",
        f"| **overall_extraction_score** | **{_fmt(overall)}** |",
        f"| schema_valid_rate | {_fmt(scores.get('schema_valid_rate') or rec.get('schema_valid_rate'))} |",
        f"| error_count | {n_err} |",
        "",
        "## Serving / cost (see sibling `-SERVING.md`)",
        "",
        "| metric | value |",
        "| --- | --- |",
        f"| wall_seconds | {_fmt(rec.get('wall_seconds'), 3)} |",
        f"| gpu_seconds | {_fmt(rec.get('gpu_seconds'), 3)} |",
        f"| estimated GPU cost | {_fmt(rec.get('estimated_gpu_cost_usd'), 6)} |",
        f"| **GPU $/doc** | **{_fmt(rec.get('gpu_cost_per_document'), 8)}** |",
        f"| latency p50 / max (s) | {_fmt(rec.get('latency_p50_seconds'))} / {_fmt(rec.get('latency_max_seconds'))} |",
        f"| prompt / completion tokens | {rec.get('prompt_tokens')} / {rec.get('completion_tokens')} |",
        f"| concurrency speedup (Σlat/wall) | {_fmt(rec.get('latency_sum_over_wall'), 2)} |",
        "",
        "## Per-document scores",
        "",
        "| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i, row in enumerate(items, 1):
        score = row.get("score") if isinstance(row.get("score"), dict) else {}
        lat = row.get("latency_ms")
        lat_s = f"{float(lat) / 1000.0:.1f}" if lat is not None else "—"
        err = row.get("error") or ""
        lines.append(
            f"| {i} | `{row.get('item_id') or i}` | {row.get('ok')} | "
            f"{_fmt(score.get('overall_extraction_score') if score else None)} | "
            f"{lat_s} | {row.get('prompt_tokens') if row.get('prompt_tokens') is not None else '—'} | "
            f"{row.get('completion_tokens') if row.get('completion_tokens') is not None else '—'} | "
            f"{err or 'None'} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_serving_report(store: RunStore, rec: Mapping[str, Any]) -> str:
    lock = store.read_lock() or {}
    engine = lock.get("engine") if isinstance(lock.get("engine"), dict) else {}
    modal = (engine or {}).get("modal") if isinstance(engine, dict) else {}
    job = lock.get("job") if isinstance(lock.get("job"), dict) else {}
    replicas = max(1, int((modal or {}).get("max_containers") or rec.get("replicas") or 1))
    conc = int((job or {}).get("concurrency") or rec.get("concurrency") or 1)
    mapped = cell_stem(store, lock=lock)
    stem = mapped[1] if mapped else store.run_id
    return "\n".join(
        [
            f"# Serving — `{store.run_id}`",
            "",
            f"Stem `{stem}`. Model `{rec.get('model')}`. TTFT is never inferred.",
            "",
            "| metric | value |",
            "| --- | --- |",
            f"| run_id | `{store.run_id}` |",
            f"| task | `{rec.get('task') or lock.get('task')}` |",
            f"| model | `{rec.get('model')}` |",
            f"| GPU | `{rec.get('gpu') or (modal or {}).get('gpu')}` ×{replicas} |",
            f"| n | {_cell_n(store, lock, store.load_items())} |",
            f"| concurrency | {conc} |",
            f"| wall_seconds | {_fmt(rec.get('wall_seconds'), 3)} |",
            f"| cold_boot_seconds | {_fmt(rec.get('cold_boot_seconds'), 3)} |",
            f"| gpu_seconds | {_fmt(rec.get('gpu_seconds'), 3)} |",
            f"| estimated_gpu_cost_usd | {_fmt(rec.get('estimated_gpu_cost_usd'), 6)} |",
            f"| **gpu_cost_per_document** | **{_fmt(rec.get('gpu_cost_per_document'), 8)}** |",
            f"| token-proxy cost_usd | {_fmt(rec.get('cost_usd') or rec.get('estimated_cost_usd'), 6)} |",
            f"| latency mean / p50 / p95 / max (s) | {_fmt(rec.get('e2e_latency_seconds'))} / {_fmt(rec.get('latency_p50_seconds'))} / {_fmt(rec.get('latency_p95_seconds'))} / {_fmt(rec.get('latency_max_seconds'))} |",
            f"| latency_sum_seconds | {_fmt(rec.get('latency_sum_seconds'), 3)} |",
            f"| latency_sum_over_wall | {_fmt(rec.get('latency_sum_over_wall'), 2)} |",
            f"| prompt_tokens | {rec.get('prompt_tokens')} |",
            f"| completion_tokens | {rec.get('completion_tokens')} |",
            f"| total_tokens | {rec.get('total_tokens')} |",
            f"| tokens_per_second | {_fmt(rec.get('tokens_per_second'), 2)} |",
            f"| slot_utilization | {_fmt(rec.get('slot_utilization'), 4)} |",
            f"| busy_slot_seconds | {_fmt(rec.get('busy_slot_seconds'), 3)} |",
            f"| ttft_seconds | {_fmt(rec.get('ttft_seconds'))} |",
            f"| ttft_note | {rec.get('ttft_note') or '—'} |",
            "",
            "Machine-readable sibling: same stem with `.serving.json`.",
            "",
        ]
    )


def write_run_reports(
    store: RunStore,
    *,
    scores: Mapping[str, Any] | None = None,
    wall_seconds: float | None = None,
    repo: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Path]:
    """Write dated REPORT + SERVING artifacts. No-op for mock / non-specialist."""
    from mailroom_sandbox.job import metrics

    lock = store.read_lock() or {}
    job = lock.get("job") if isinstance(lock.get("job"), dict) else {}
    if job.get("mock"):
        return {}
    paths = dated_cell_paths(store, repo=repo, now=now)
    if paths is None:
        return {}
    items = store.load_items()
    if not items:
        return {}
    rec = metrics.serving_record_from_store(store, wall_seconds=wall_seconds, scores=scores)
    dest_dir = paths["dir"]
    dest_dir.mkdir(parents=True, exist_ok=True)
    json_path = paths["serving_json"]
    metrics._atomic_write_serving_json(json_path, rec)
    paths["report"].write_text(render_quality_report(store, rec, scores=scores), encoding="utf-8")
    paths["serving_md"].write_text(render_serving_report(store, rec), encoding="utf-8")
    tui = serving_export_path(store, repo=repo)
    if tui is None:
        tui = metrics.default_serving_json_path(store.run_id)
    if tui.resolve() != json_path.resolve():
        tui.parent.mkdir(parents=True, exist_ok=True)
        metrics._atomic_write_serving_json(tui, rec)
        paths["tui_serving_json"] = tui
    _log.info("dated reports written under %s", dest_dir)
    return paths


def maybe_write_run_reports(store: RunStore, **kwargs: Any) -> dict[str, Path]:
    """Runner hook: never fail the scored job if report I/O breaks."""
    try:
        return write_run_reports(store, **kwargs)
    except Exception:
        _log.exception("dated report write failed for %s", store.run_id)
        return {}
