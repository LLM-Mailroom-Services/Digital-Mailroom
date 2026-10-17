"""SAND-042: per-cell scorecards and the paired cross-cell comparison.

The SAND-037 suite card (``grid_cards.collect_suite``) is keyed on that grid's
run ids, n ∈ {20, 50} and its two fleet shapes; SAND-042 has five cells with the
same n, so it gets its own collector. Everything here reads the committed
``*.card.json`` written by ``sandbox run card --config …`` — no live run, no
network.

What it adds over the SAND-037 card, per docs/BENCHMARK-PROGRAM.md §5.2:

* **quality with an interval** — bootstrap 95% CI over the per-document scores;
* **reliability** — ok rate with a Wilson interval, schema-valid rate,
  length-capped share, over documents *attempted*;
* **document goodput at the class SLO** — docs/min/GPU with p95 document latency
  ≤ the class SLO (60 s short classes, 300 s contracts, 1800 s merger);
* **cost per usable record** — $/1k ok documents and $/1k *schema-valid* documents;
* **engine + GPU telemetry** — the vLLM /metrics deltas and the SAND-042
  in-container nvidia-smi series (util / power / temperature / memory).

``write_comparison`` then pairs each non-reference cell on the shared 250 documents
and reports each delta with a bootstrap CI and the better/worse counts — the format
the SAND-37 master card already uses for merger †.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import logging
import os
import random
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from mailroom_sandbox.job import grid_cards, metrics
from mailroom_sandbox.job.grid_cards import (
    SPECIALISTS,
    _f,
    _read_json,
    _usd,
    study_root,
)
from mailroom_sandbox.paths import repo_root

_log = logging.getLogger("mailroom_sandbox.job.sand42_cards")

SCHEMA_CELL = "sandbox.sand42-cell/v1"


def _atomic_text(path: Path, text: str) -> None:
    """Temp + replace, so a reader never sees a half-written report."""
    tmp = path.with_name(f".{path.name}.tmp{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


@contextlib.contextmanager
def report_lock(*, repo: Path | None = None, timeout_s: float = 900.0) -> Iterator[None]:
    """Exclusive lock over the study's report writes.

    Two parallel fleets, the sequential driver and the handoff all rebuild the
    cell/master cards, the comparison and ``figures/`` from the same tree; without
    this the master can be rewritten while another process is reading it (torn
    report) or two builders interleave. Held only across a card build, so the
    loser waits rather than failing.
    """
    root = study_root("sand42-", repo=repo)
    root.mkdir(parents=True, exist_ok=True)
    with open(root / ".report.lock", "w", encoding="utf-8") as fh:
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"SAND-042 report lock busy for {timeout_s:.0f}s: {root}")
                time.sleep(0.5)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
STUDY = "SAND42"
REFERENCE_CELL = "1l4-c8"

# Cell id -> (replicas, client concurrency). Mirrors specialist_posture.
CELLS: dict[str, tuple[int, int]] = {
    "1l4-c8": (1, 8),
    "1l4-c16": (1, 16),
    "2l4-c8": (2, 8),
    "2l4-c16": (2, 16),
    "2l4-c32": (2, 32),
}
# Order is the master report's section order; 2l4-c32 is last (it joins the
# saturation arm, not the {8,16} concurrency arm).
CELL_ORDER: tuple[str, ...] = ("1l4-c8", "1l4-c16", "2l4-c8", "2l4-c16", "2l4-c32")
# Cell stem for the suite artifact (the SAND-37 suite stems collide across cells).
CELL_STEMS: dict[str, str] = {
    "1l4-c8": "SAND42-1L4-C8-SCORE-COST-CARD",
    "1l4-c16": "SAND42-1L4-C16-SCORE-COST-CARD",
    "2l4-c8": "SAND42-2L4-C8-SCORE-COST-CARD",
    "2l4-c16": "SAND42-2L4-C16-SCORE-COST-CARD",
    "2l4-c32": "SAND42-2L4-C32-SCORE-COST-CARD",
}
# Class SLOs for document goodput (BENCHMARK-PROGRAM §5.2, set from SAND-40).
CLASS_SLO_SECONDS: dict[str, float] = {
    "correspondence_specialist": 60.0,
    "insurance_claims_specialist": 60.0,
    "corporate_records_specialist": 60.0,
    "contracts_specialist": 300.0,
    "merger_agreement_specialist": 1800.0,
}
NOISE_FLOOR_RUN = "sand42-noisefloor-correspondence-awq-1l4-c8"


def cell_run_ids(cell: str) -> list[str]:
    from mailroom_sandbox.job.specialist_posture import sand42_run_id

    return [
        sand42_run_id(cell, doc_class)
        for doc_class in ("correspondence", "insurance_claim", "corporate_record",
                          "contract", "merger_agreement")
    ]


def _task_of(run_id: str) -> str:
    """``sand42-50-<slug>-specialist-awq-<cell>`` → the specialist task name."""
    slug = run_id.split("-specialist-awq-", 1)[0].removeprefix("sand42-50-")
    return {
        "correspondence": "correspondence_specialist",
        "insurance-claims": "insurance_claims_specialist",
        "corporate-records": "corporate_records_specialist",
        "contracts": "contracts_specialist",
        "merger": "merger_agreement_specialist",
    }[slug]


def _cell_dir(cell: str, *, repo: Path | None = None) -> Path:
    """``reports/SAND42/<1L4-c8|1L4-c16|2L4-c8|2L4-c16>/`` — one folder per condition."""
    replicas = CELLS[cell][0]
    return study_root("sand42-", repo=repo) / grid_cards.condition_dir(
        f"sand42-x-{cell}", replicas
    )


def cell_paths(cell: str, *, repo: Path | None = None) -> dict[str, Path]:
    base = _cell_dir(cell, repo=repo)
    stem = CELL_STEMS[cell]
    return {"dir": base, "md": base / f"{stem}.md", "json": base / f"{stem}.json"}


def specialist_dir(cell: str, task: str, *, repo: Path | None = None) -> Path:
    folder = {t: f for t, f, _ in SPECIALISTS}.get(task, task)
    return _cell_dir(cell, repo=repo) / folder


def comparison_paths(*, repo: Path | None = None) -> dict[str, Path]:
    base = study_root("sand42-", repo=repo)
    return {
        "dir": base,
        "md": base / "SAND42-CELL-COMPARISON.md",
        "json": base / "SAND42-CELL-COMPARISON.json",
    }


def noise_floor_paths(*, repo: Path | None = None) -> dict[str, Path]:
    base = study_root("sand42-", repo=repo)
    return {"dir": base, "md": base / "SAND42-NOISE-FLOOR.md"}


# ── statistics ───────────────────────────────────────────────────────────────


def wilson(k: int, n: int, *, z: float = 1.96) -> tuple[float, float] | None:
    """95% Wilson score interval for a pass rate (BENCHMARK-PROGRAM §5.2)."""
    if n <= 0:
        return None
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _p95(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
    return ordered[idx]


def bootstrap_mean_ci(
    values: Sequence[float], *, iters: int = 4000, seed: int = 42
) -> tuple[float, float, float] | None:
    """(mean, lo, hi) 95% percentile bootstrap over per-document values."""
    if not values:
        return None
    mean = statistics.fmean(values)
    if len(values) == 1:
        return (mean, mean, mean)
    rng = random.Random(seed)
    n = len(values)
    draws = []
    for _ in range(iters):
        draws.append(statistics.fmean([values[rng.randrange(n)] for _ in range(n)]))
    draws.sort()
    lo = draws[int(0.025 * (iters - 1))]
    hi = draws[int(0.975 * (iters - 1))]
    return (mean, lo, hi)


def paired_delta(
    a: Mapping[str, Any], b: Mapping[str, Any], *, iters: int = 4000, seed: int = 42
) -> dict[str, Any] | None:
    """Paired per-document delta (b − a) with a bootstrap CI and better/worse.

    Pairing is the largest variance saving (BENCHMARK-PROGRAM §3): both arms are
    scored on the same document ids, so the difference of the per-document scores
    is the unit of analysis.
    """
    a_scores = _scores_by_id(a)
    b_scores = _scores_by_id(b)
    shared = sorted(set(a_scores) & set(b_scores))
    diffs = [b_scores[i] - a_scores[i] for i in shared]
    if not diffs:
        return None
    ci = bootstrap_mean_ci(diffs, iters=iters, seed=seed)
    return {
        "paired_documents": len(diffs),
        "delta_mean": statistics.fmean(diffs),
        "ci_low": ci[1] if ci else None,
        "ci_high": ci[2] if ci else None,
        "sd_diff": statistics.stdev(diffs) if len(diffs) > 1 else None,
        "better": sum(1 for d in diffs if d > 0),
        "worse": sum(1 for d in diffs if d < 0),
        "tie": sum(1 for d in diffs if d == 0),
    }


def paired_n_for(delta: float, sd_diff: float | None, *, power: float = 2.8) -> int | None:
    """Paired n to detect ``delta`` at 80% power, two-sided 5%: (2.8·SD/Δ)²."""
    if not delta or not sd_diff:
        return None
    return int(-(-(power * sd_diff / abs(delta)) ** 2 // 1))


def _scores_by_id(card: Mapping[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for doc in card.get("documents") or []:
        item = doc.get("item_id")
        score = doc.get("score")
        if item is None or not isinstance(score, (int, float)):
            continue
        out[str(item)] = float(score)
    return out


# ── cell collection ──────────────────────────────────────────────────────────


def _reliability(card: Mapping[str, Any]) -> dict[str, Any]:
    q = card.get("quality") or {}
    docs = int(q.get("documents") or 0)
    ok = int(q.get("ok") or 0)
    capped = sum(
        1
        for d in card.get("documents") or []
        if "length" in str(d.get("error") or "").lower()
    )
    ci = wilson(ok, docs)
    return {
        "attempted": docs,
        "ok": ok,
        "ok_rate": (ok / docs) if docs else None,
        "ok_rate_ci": ci,
        "schema_valid_rate": q.get("schema_valid_rate"),
        "parse_errors": q.get("parse_errors"),
        "length_capped": capped,
        "length_capped_share": (capped / docs) if docs else None,
        "error_kinds": q.get("error_kinds") or {},
    }


def _goodput(card: Mapping[str, Any], task: str) -> dict[str, Any]:
    """docs/min/GPU at the class SLO: throughput only counts a run that meets it."""
    replicas = max(1, int((card.get("conditions") or {}).get("replicas") or 1))
    wall = (card.get("time") or {}).get("wall_seconds")
    docs = int((card.get("quality") or {}).get("documents") or 0)
    p95 = (card.get("latency") or {}).get("p95")
    slo = CLASS_SLO_SECONDS.get(task)
    if not wall or not docs or p95 is None or slo is None:
        return {"documents_per_minute_per_gpu": None, "slo_seconds": slo, "meets_slo": None}
    dpm = docs / wall * 60.0
    return {
        "documents_per_minute_per_gpu": dpm / replicas,
        "slo_seconds": slo,
        "meets_slo": p95 <= slo,
        "goodput_documents_per_minute_per_gpu": (dpm / replicas) if p95 <= slo else 0.0,
    }


def _cost_per_usable(card: Mapping[str, Any]) -> dict[str, Any]:
    cost = card.get("cost") or {}
    busy = cost.get("busy_gpu_usd")
    # The numerator is the money actually spent, so it must be the BILLED figure
    # (the run's own container-telemetry window x replicas x rate). The denominator
    # is the useful output, so cost per usable record is billed / usable.
    billed = cost.get("billed_gpu_usd") or busy
    rel = _reliability(card)
    ok = rel["ok"]
    sv = rel["schema_valid_rate"]
    attempted = rel["attempted"]
    return {
        "busy_gpu_usd": busy,
        "billed_gpu_usd": billed,
        "billed_seconds": cost.get("billed_seconds"),
        "usd_per_1k_ok": (billed / ok * 1000.0) if billed and ok else None,
        "usd_per_1k_schema_valid": (
            billed / (sv * attempted) * 1000.0 if billed and sv and attempted else None
        ),
    }


def _gpu_block(card: Mapping[str, Any]) -> dict[str, Any]:
    eng = card.get("engine_telemetry") or {}
    gpu = eng.get("gpu") if isinstance(eng, dict) else None
    return gpu if isinstance(gpu, dict) else {"captured": False}


def _summary(run_id: str, card: Mapping[str, Any] | None, task: str) -> dict[str, Any]:
    if not card:
        return {"run_id": run_id, "task": task, "reported": False}
    docs = card.get("documents") or []
    scores = [float(d["score"]) for d in docs if isinstance(d.get("score"), (int, float))]
    quality_ci = bootstrap_mean_ci(scores)
    return {
        "run_id": run_id,
        "task": task,
        "reported": True,
        "quality": {
            "mean": statistics.fmean(scores) if scores else None,
            "ci_low": quality_ci[1] if quality_ci else None,
            "ci_high": quality_ci[2] if quality_ci else None,
            "sd": (card.get("quality") or {}).get("overall_sd"),
            "scoring_method": (card.get("quality") or {}).get("scoring_method"),
            "clause": (card.get("quality") or {}).get("clause"),
            "scored_documents": len(scores),
        },
        "reliability": _reliability(card),
        "cost": _cost_per_usable(card),
        "goodput": _goodput(card, task),
        "latency": card.get("latency") or {},
        "throughput": card.get("throughput") or {},
        "tokens": card.get("tokens") or {},
        "time": card.get("time") or {},
        "concurrency": card.get("concurrency") or {},
        "engine_telemetry": card.get("engine_telemetry") or {},
        "gpu": _gpu_block(card),
    }


def fleet_cost(cell: str, *, repo: Path | None = None) -> dict[str, Any]:
    """The cell's whole GPU burn, computed from its own recorded fleet window.

    ``min_containers=1`` pins the fleet warm from deploy to teardown, so Modal meters
    the ENTIRE window — the cold boot and the idle between specialists included, not
    just the five run windows. The window is recorded by the cell runner, so this is
    computed from the session itself rather than scraped from the billing CLI (whose
    figures are credits-based and workspace-wide, not per cell).
    """
    doc = _read_json(_cell_dir(cell, repo=repo) / "fleet_window.json")
    if not doc:
        return {"measured": False, "reason": "no fleet_window.json for this cell"}
    deploy = doc.get("deploy_ts")
    teardown = doc.get("teardown_ts")
    if not isinstance(deploy, (int, float)) or not isinstance(teardown, (int, float)):
        return {"measured": False, "reason": "fleet window is not closed (no deploy/teardown ts)"}
    if teardown <= deploy:
        return {"measured": False, "reason": "fleet window is inverted (teardown <= deploy)"}
    replicas = max(1, int(doc.get("replicas") or CELLS[cell][0]))
    gpu = str(doc.get("gpu") or "L4")
    rate = metrics.gpu_usd_per_hour(gpu)
    seconds = float(teardown - deploy)
    ready = doc.get("ready_ts")
    return {
        "measured": True,
        "deploy_ts": float(deploy),
        "ready_ts": float(ready) if isinstance(ready, (int, float)) else None,
        "teardown_ts": float(teardown),
        "replicas": replicas,
        "gpu": gpu,
        "gpu_usd_per_hour": rate,
        "fleet_seconds": round(seconds, 3),
        "cold_boot_seconds": round(float(ready) - float(deploy), 3) if isinstance(ready, (int, float)) else None,
        "fleet_gpu_hours": round(seconds * replicas / 3600.0, 4),
        "fleet_gpu_usd": round(seconds * replicas * rate / 3600.0, 4),
    }


def collect_cell(cell: str, *, repo: Path | None = None) -> dict[str, Any]:
    replicas, concurrency = CELLS[cell]
    rows = []
    cards: dict[str, Any] = {}
    for run_id in cell_run_ids(cell):
        task = _task_of(run_id)
        card = _read_json(
            specialist_dir(cell, task, repo=repo) / f"{run_id}.card.json"
        ) or None
        if card:
            cards[run_id] = card
        rows.append(_summary(run_id, card, task))
    return {
        "schema": SCHEMA_CELL,
        "kind": "cell",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cell": cell,
        "replicas": replicas,
        "concurrency": concurrency,
        "concurrency_per_replica": concurrency / replicas,
        "runbook": f"sand42-{cell}",
        "cells_reported": sum(1 for r in rows if r["reported"]),
        "specialists": rows,
        "cards": cards,
        "fleet": fleet_cost(cell, repo=repo),
    }


# ── rendering ────────────────────────────────────────────────────────────────


def _pct(v: float | None, digits: int = 1) -> str:
    return "—" if v is None else f"{100.0 * v:.{digits}f}%"


def _ci(lo: float | None, hi: float | None, digits: int = 3) -> str:
    if lo is None or hi is None:
        return "—"
    return f"[{lo:.{digits}f}, {hi:.{digits}f}]"


def _quality_text(q: Mapping[str, Any]) -> str:
    mean = q.get("mean")
    if mean is None:
        return "not captured"
    return f"{mean:.3f} {_ci(q.get('ci_low'), q.get('ci_high'))}"


def _reliability_text(rel: Mapping[str, Any]) -> str:
    rate = rel.get("ok_rate")
    ci = rel.get("ok_rate_ci")
    if rate is None:
        return "not captured"
    return f"{rel['ok']}/{rel['attempted']} {_pct(rate)} {_ci(ci[0], ci[1]) if ci else ''}".strip()


def _gpu_text(gpu: Mapping[str, Any]) -> str:
    if not gpu.get("captured"):
        return "not captured"
    util = gpu.get("util_mean_perc")
    peak = gpu.get("util_max_perc")
    n = gpu.get("samples")
    if util is None:
        return f"{n} samples, no util"
    return (
        f"{util:.1f}% mean / {_f(gpu.get('util_p95_perc'), 1)} p95 / "
        f"{_f(gpu.get('util_min_perc'), 1)}–{peak:.1f}% min–max (n={n})"
    )


def _coverage_text(gpu: Mapping[str, Any]) -> str:
    """#128's sampling-coverage gate: a cell below 90% is rejected, not reported."""
    cov = gpu.get("sampling_coverage_pct")
    if cov is None:
        return "not captured"
    flag = " ⚠ below the 90% gate (issue #128)" if cov < 90 else ""
    return f"{cov:.1f}%{flag}"


def _mem_used_text(gpu: Mapping[str, Any]) -> str:
    """nvidia-smi memory.used / memory.total — the GPU-memory utilization, on every cell."""
    used = (gpu.get("memory_used_mib") or {}).get("mean")
    total = (gpu.get("memory_total_mib") or {}).get("mean")
    if used is None:
        return "not captured"
    if total:
        return f"{_f(used, 0)} MiB ({_pct(used / total)} of {_f(total, 0)})"
    return f"{_f(used, 0)} MiB"


def _mem_bw_text(gpu: Mapping[str, Any]) -> str:
    """nvidia-smi memory-bandwidth utilization; absent on cells whose sampler predates it.

    `utilization.memory` only entered the sampler's nvidia-smi query after the
    1L4-c8/1L4-c16 cells had already been scraped, so those runs have no such
    field. Say so rather than emitting a bare "not captured": the value is
    recoverable only by re-running the cell.
    """
    bw = (gpu.get("utilization_memory_perc") or {}).get("mean")
    if isinstance(bw, (int, float)):
        return f"{_pct(bw / 100.0)} mean"
    if not gpu.get("captured"):
        return "not captured — no container telemetry for this run"
    return "not captured — scraped before the sampler read utilization.memory; needs a re-run"


def _figure_line(path: Path) -> str:
    """One embedded master figure; the stem is the caption (`cmp-cost` → `Cost`)."""
    caption = path.stem.removeprefix("cmp-").replace("-", " ").replace("_", " ").title()
    return f"![{caption}](figures/{path.name})"


def _master_figures(*, repo: Path | None = None) -> list[Path]:
    """Write the shared master figures. Lazy and never fatal: a missing module or a
    plotting error must not break a report write."""
    try:
        from mailroom_sandbox.job import sand42_figures

        return [Path(p) for p in sand42_figures.maybe_write_master_figures(repo=repo)]
    except Exception:  # noqa: BLE001
        _log.warning("SAND-042 master figures failed", exc_info=True)
        return []


def _cold_boot_text(fleet: Mapping[str, Any]) -> str:
    """The boot window, or WHY it is absent.

    Only the parallel-fleet launcher records ``ready_ts`` (the moment its health
    loop first saw the engine answer), so the sequential driver's cells have a
    closed fleet window but no boot boundary to subtract. Absent telemetry says
    why — it never becomes a fabricated number; a live re-run is the only real
    source for those cells.
    """
    seconds = fleet.get("cold_boot_seconds")
    if isinstance(seconds, (int, float)):
        return _f(seconds, 1, " s")
    return f"{_f(None)} — ready_ts is only written by the parallel-fleet launcher"


def _fleet_lines(cell_data: Mapping[str, Any]) -> list[str]:
    """The cell's whole burn, computed from its own recorded fleet window."""
    fleet = cell_data.get("fleet") or {}
    rows = cell_data.get("specialists") or []
    if not fleet.get("measured"):
        return [
            f"Fleet window not recorded ({fleet.get('reason') or 'unknown'}). Per-run costs "
            "still come from each run's own container-telemetry window.",
            "",
        ]
    run_seconds = sum(
        float((r.get("cost") or {}).get("billed_seconds") or 0.0)
        for r in rows
        if r.get("reported")
    )
    overhead = max(0.0, float(fleet["fleet_seconds"]) - run_seconds)
    return [
        f"The fleet is pinned warm (`min_containers=1`) from deploy to teardown, so Modal "
        f"meters the **whole window** — the cold boot and the idle between specialists "
        f"included. This is computed from the session's own timestamps, not scraped from "
        f"the billing CLI (whose figures are credits-based and workspace-wide).",
        "",
        "| Fleet cost | Value |",
        "| --- | ---: |",
        f"| Replicas × GPU | {fleet['replicas']} × {fleet['gpu']} @ "
        f"${fleet['gpu_usd_per_hour']:.2f}/GPU-hr |",
        f"| Cold boot (deploy → ready) | {_cold_boot_text(fleet)} |",
        f"| Fleet window (deploy → teardown) | {_f(fleet['fleet_seconds'], 1, ' s')} |",
        f"| Fleet GPU-hours | {fleet['fleet_gpu_hours']:.4f} |",
        f"| **Fleet GPU $** | **{_usd(fleet['fleet_gpu_usd'], 4)}** |",
        f"| Of which the five runs | {_f(run_seconds, 1, ' s')} "
        f"({_pct(run_seconds / fleet['fleet_seconds'] if fleet['fleet_seconds'] else None)}) |",
        f"| Boot + idle overhead | {_f(overhead, 1, ' s')} |",
        "",
    ]


def render_cell_md(
    cell_data: Mapping[str, Any], *, link_prefix: str = "", figure: str | None = None
) -> str:
    """One condition's card. ``link_prefix`` rebases the per-run links when this
    markdown is embedded a level up, in the master report at reports/SAND42/ — without
    it every link points at a path that only exists relative to the cell folder."""
    cell = cell_data["cell"]
    replicas = cell_data["replicas"]
    conc = cell_data["concurrency"]
    per = cell_data["concurrency_per_replica"]
    rows = cell_data["specialists"]
    cards = cell_data["cards"]
    first = next(iter(cards.values()), None)
    cond = (first or {}).get("conditions") or {}
    ds = cond.get("dataset") or {}

    lines = [
        f"# SAND-042 · {replicas}× L4 · client concurrency {conc}"
        + (f" ({per:g} per replica)" if replicas > 1 else "")
        + " · n=50 × 5 specialists",
        "",
        f"**Cells reported:** {cell_data['cells_reported']} of {len(rows)} · "
        f"**Runbook:** `{cell_data['runbook']}` · "
        "**Model:** Qwen/Qwen3-8B-AWQ · L4 @ $0.80/GPU-hr",
        "",
        "## Shared conditions",
        "",
        "| Condition | Value |",
        "| --- | --- |",
        f"| Engine | {cond.get('model') or cond.get('engine', {}).get('model', '—')} · "
        f"max_model_len {cond.get('engine', {}).get('max_model_len', '—')} · "
        f"max_num_seqs {cond.get('engine', {}).get('max_num_seqs', '—')}/replica · "
        f"max_inputs {cond.get('engine', {}).get('max_inputs', '—')} |",
        f"| Fleet | {replicas} replica(s) · client concurrency {conc} ({per:g} per replica) |",
        f"| Dataset | `{ds.get('repo', '—')}` {ds.get('config', '')} @ {str(ds.get('revision') or '—')[:8]}, "
        f"split={ds.get('split', '—')}, seed {ds.get('seed', '—')}, one class bucket, "
        "50 per class stratified over every subclass (min 1 per sub-type) |",
        f"| Prompt | v1 `*_simplified` stems only |",
        f"| Output cap | max_tokens {_f(cond.get('max_tokens'))} · temperature 0.7 contracts + merger, 0.1 elsewhere |",
        f"| GPU telemetry | in-container nvidia-smi series, label `sand42-{cell}` |",
        "",
        "## Per specialist",
        "",
        "| Metric | Correspondence | Insurance Claims | Corporate Records | Contracts | Merger Agreements |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    def row(label: str, fn) -> str:
        vals = []
        for r in rows:
            vals.append(fn(r) if r.get("reported") else "not run")
        return f"| {label} | " + " | ".join(vals) + " |"

    lines += [
        row("Quality (95% CI)", lambda r: _quality_text(r["quality"])),
        row("Scored documents", lambda r: str(r["quality"]["scored_documents"])),
        row("Quality SD", lambda r: _f(r["quality"].get("sd"), 3)),
        row("Scoring method", lambda r: str(r["quality"].get("scoring_method") or "—")),
        row("Clause metric", lambda r: _clause_text(r["quality"].get("clause"))),
        row("Ok rate (Wilson)", lambda r: _reliability_text(r["reliability"])),
        row("Schema-valid rate", lambda r: _pct(r["reliability"].get("schema_valid_rate"))),
        row("Parse errors", lambda r: _f(r["reliability"].get("parse_errors"), 0)),
        row("Length-capped", lambda r: str(r["reliability"].get("length_capped"))),
        row("Error kinds", lambda r: _error_kinds_text(r["reliability"].get("error_kinds"))),
        row("p50 latency (s)", lambda r: _f(r["latency"].get("p50"), 1)),
        row("p95 latency (s)", lambda r: _f(r["latency"].get("p95"), 1)),
        row("SLO (s) · met", lambda r: f"{_f(r['goodput'].get('slo_seconds'), 0)} · "
            + ("yes" if r["goodput"].get("meets_slo") else "no")),
        row("Documents/min", lambda r: _f(r["throughput"].get("documents_per_minute"), 2)),
        row("Documents/min/GPU", lambda r: _f(r["throughput"].get("documents_per_minute_per_gpu"), 2)),
        row("Goodput docs/min/GPU", lambda r: _f(r["goodput"].get("goodput_documents_per_minute_per_gpu"), 2)),
        row("Tokens/s/GPU", lambda r: _f(r["throughput"].get("tokens_per_second_per_gpu"), 1)),
        row("Mean TTFT (s)", lambda r: _replica_mean_text(r, "ttft_mean_seconds")),
        row("Prefix-cache hit", lambda r: _replica_mean_text(r, "prefix_cache_hit_rate", pct=True)),
        row("Wall (s)", lambda r: _f(r["time"].get("wall_seconds"), 1)),
        row("Billed GPU $ (run)", lambda r: _usd(r["cost"].get("billed_gpu_usd"), 4)),
        row("$ / 1k ok docs", lambda r: _usd(r["cost"].get("usd_per_1k_ok"))),
        row("$ / 1k schema-valid", lambda r: _usd(r["cost"].get("usd_per_1k_schema_valid"))),
        row("$ / doc", lambda r: _usd(_per_doc_usd(r), 6)),
        row("$ / ok doc", lambda r: _usd(_per_doc_usd(r, ok=True), 6)),
        row("$ / 1M tokens", lambda r: _usd(_per_1m_tokens_usd(r), 3)),
        row("GPU util (mean/p95/min–max)", lambda r: _gpu_text(r["gpu"])),
        row("GPU mem used (mean)", lambda r: _mem_used_text(r["gpu"])),
        row("GPU mem bandwidth (mean)", lambda r: _mem_bw_text(r["gpu"])),
        row("Sampling coverage", lambda r: _coverage_text(r["gpu"])),
        row("GPU power (W, mean)", lambda r: _f((r["gpu"].get("power_draw_w") or {}).get("mean"), 1)),
        row("GPU temp (C, mean)", lambda r: _f((r["gpu"].get("temperature_c") or {}).get("mean"), 1)),
        row("KV cache use, mid-run (max %)", lambda r: _midrun_kv_text(r)),
        row("Queue depth, mid-run (running/waiting)", lambda r: _midrun_queue_text(r)),
        row("Preemptions", lambda r: _replica_sum_text(r, "preemptions")),
        row("Length finishes", lambda r: _replica_sum_text(r, "length_finishes")),
    ]
    if figure:  # the per-cell deliverable, at reports/SAND42/figures/<cell>-dashboard.png
        lines += [
            "",
            "## Figure",
            "",
            f"![SAND-042 {cell} cell dashboard](../figures/{figure})",
        ]
    lines += [
        "",
        "## Cost (computed from the session)",
        "",
        *_fleet_lines(cell_data),
        "## Per-run cards",
        "",
        "| Specialist | Run ID | Card |",
        "| --- | --- | --- |",
    ]
    folder_of = {task: folder for task, folder, _ in SPECIALISTS}
    label_of = {task: label for task, _, label in SPECIALISTS}
    for r in rows:
        folder = folder_of[r["task"]]
        link = (
            f"[{r['run_id']}.card.md]({link_prefix}{folder}/{r['run_id']}.card.md)"
            if r.get("reported")
            else "not run"
        )
        lines.append(f"| {label_of[r['task']]} | `{r['run_id']}` | {link} |")
    lines += [
        "",
        "_Merger dominates pooled throughput (≈ 112k prompt tokens per agreement on the "
        "frozen settings), so no pooled column is reported here — compare per class._",
        "",
        f"_Generated {cell_data['generated_at']} by "
        f"`sandbox run card --runbook sand42-{cell}` from the committed per-run `*.card.json`._",
        "",
    ]
    return "\n".join(lines)


def _midrun(r: Mapping[str, Any]) -> Mapping[str, Any]:
    """The mid-run sample block (``scripts/sand42/midrun_kv.py``), or ``{}`` when absent."""
    m = (r.get("engine_telemetry") or {}).get("midrun")
    return m if isinstance(m, Mapping) else {}


def _midrun_kv_text(r: Mapping[str, Any]) -> str:
    """KV-cache use measured MID-RUN — the only reading that is not 0 by construction.

    The before/after scrapes fire at the drained edges, so a run
    nobody sampled mid-flight has no honest number here and says so with "—" rather
    than repeating the drained-edge 0. Reads either producer: the folded series
    (``cell_max``) or a single live ``scrape-metrics --label mid`` (per-replica gauge).
    """
    m = _midrun(r)
    cm = m.get("cell_max") or {}
    mx = cm.get("kv_cache_usage_perc", cm.get("vllm:kv_cache_usage_perc"))
    if not isinstance(mx, (int, float)):
        vals = [x.get("kv_cache_usage_perc") for x in (m.get("replicas") or {}).values()
                if isinstance(x, dict)]
        vals = [v for v in vals if isinstance(v, (int, float))]
        mx = max(vals) if vals else None
    return f"{float(mx) * 100:.1f}%" if isinstance(mx, (int, float)) else "—"


def _midrun_queue_text(r: Mapping[str, Any]) -> str:
    """Peak in-flight / queued requests per replica, mid-run.

    This is the saturation evidence the two-edge scrape cannot give: at the drained
    edges both gauges read 0, whatever the run actually did.
    """
    m = _midrun(r)
    cm = m.get("cell_max") or {}
    run = cm.get("num_requests_running", cm.get("vllm:num_requests_running"))
    wait = cm.get("num_requests_waiting", cm.get("vllm:num_requests_waiting"))
    if not isinstance(run, (int, float)):
        reps = [x for x in (m.get("replicas") or {}).values() if isinstance(x, dict)]
        runs = [x["num_requests_running"] for x in reps
                if isinstance(x.get("num_requests_running"), (int, float))]
        waits = [x["num_requests_waiting"] for x in reps
                 if isinstance(x.get("num_requests_waiting"), (int, float))]
        if runs:
            run, wait = max(runs), (max(waits) if waits else 0)
    if not isinstance(run, (int, float)):
        return "—"
    return f"{run:.0f} running / {wait if isinstance(wait, (int, float)) else 0:.0f} waiting"


def _replica_sum_text(r: Mapping[str, Any], key: str) -> str:
    reps = (r.get("engine_telemetry") or {}).get("replicas") or []
    vals = [x.get(key) for x in reps if isinstance(x, dict)]
    vals = [v for v in vals if isinstance(v, (int, float))]
    if not vals:
        return "—"
    return f"{sum(vals):.0f}"


def _replica_mean_text(
    r: Mapping[str, Any], key: str, *, pct: bool = False, digits: int = 2
) -> str:
    """Mean of a per-replica engine metric (TTFT, prefix-cache hit) across replicas."""
    reps = (r.get("engine_telemetry") or {}).get("replicas") or []
    vals = [x.get(key) for x in reps if isinstance(x, dict)]
    vals = [v for v in vals if isinstance(v, (int, float))]
    if not vals:
        return "—"
    mean = statistics.fmean(vals)
    return _pct(mean) if pct else _f(mean, digits)


def _clause_text(clause: Mapping[str, Any]) -> str:
    """The task-native clause metric: CUAD clause F1 (contracts) / MAUD accuracy (merger)."""
    clause = clause or {}
    if clause.get("kind") == "cuad":
        return f"CUAD F1 {_f(clause.get('f1'), 3)} · {clause.get('docs_labeled')} labeled"
    if clause.get("kind") == "maud":
        return (
            f"MAUD acc {_pct(clause.get('accuracy'))} · "
            f"{clause.get('answered')}/{clause.get('questions')} answered"
        )
    return "n/a (no clause scoring)"


def _error_kinds_text(kinds: Mapping[str, Any] | None) -> str:
    if not isinstance(kinds, Mapping) or not kinds:
        return "none"
    return ", ".join(f"{k}×{v}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]))


def _per_doc_usd(r: Mapping[str, Any], *, ok: bool = False) -> float | None:
    billed = (r.get("cost") or {}).get("billed_gpu_usd")
    n = (r.get("reliability") or {}).get("ok" if ok else "attempted")
    if not billed or not n:
        return None
    return billed / n


def _per_1m_tokens_usd(r: Mapping[str, Any]) -> float | None:
    billed = (r.get("cost") or {}).get("billed_gpu_usd")
    total = (r.get("tokens") or {}).get("total")
    if not billed or not total:
        return None
    return billed / total * 1_000_000


def write_cell(cell: str, *, repo: Path | None = None) -> dict[str, Path]:
    if cell not in CELLS:
        raise KeyError(f"unknown SAND-042 cell {cell!r} (want one of {sorted(CELLS)})")
    data = collect_cell(cell, repo=repo)
    paths = cell_paths(cell, repo=repo)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    _atomic_text(paths["json"], json.dumps(data, indent=2, sort_keys=True) + "\n")
    figure: str | None = None
    try:  # lazy: a missing module or a plotting error must never break the cell card
        from mailroom_sandbox.job import sand42_figures

        path = sand42_figures.maybe_write_cell_figure(cell, repo=repo)
        figure = path.name if path else None
    except Exception:  # noqa: BLE001
        _log.warning("SAND-042 cell figure failed for %s", cell, exc_info=True)
    _atomic_text(paths["md"], render_cell_md(data, figure=figure))
    return paths


# ── paired comparison across cells ───────────────────────────────────────────


def pairing_notes(cells: Mapping[str, Any]) -> list[str]:
    """Why a class's paired n can be below the class's document count.

    Generated from the cards, never hand-written: a reader who finds "Contracts 44" beside
    "Correspondence 50" in the comparison table has no way to tell a metrics gap from a
    ground-truth ceiling, and that ambiguity is exactly what a limitations section exists
    to remove.
    """
    notes: list[str] = []
    ref_cards = cells.get(REFERENCE_CELL, {}).get("cards") or {}
    for run_id, card in ref_cards.items():
        task = _task_of(run_id)
        quality = card.get("quality") or {}
        docs = int(quality.get("documents") or 0)
        ceiling = len(_scores_by_id(card))
        if not docs or ceiling >= docs:
            continue
        clause = quality.get("clause") or {}
        labeled = int(clause.get("docs_labeled") or 0)
        if labeled:
            notes.append(
                f"`{task}` — the paired n is capped at **{ceiling} of {docs}** documents: its "
                f"task-native metric (`{clause.get('kind')}`) is defined only for the {labeled} "
                "contracts that carry ground truth for it. The remainder ran successfully "
                "(`ok` true, no error) but score no numeric value in ANY arm, so they can never "
                "enter a paired delta. The cap is a property of the ground truth, not of these "
                "runs."
            )
        # A cell that scores less than the ceiling lost documents to its own errors.
        for cell in CELL_ORDER:
            if cell == REFERENCE_CELL:
                continue
            other = (cells.get(cell, {}).get("cards") or {}).get(
                run_id.replace(f"-{REFERENCE_CELL}", f"-{cell}")
            )
            if not other:
                continue
            got = len(_scores_by_id(other))
            if got < ceiling:
                kinds = (other.get("quality") or {}).get("error_kinds") or {}
                why = ", ".join(f"{k} ×{v}" for k, v in kinds.items()) or "no recorded error kind"
                notes.append(
                    f"`{task}` / `{cell}` — scores {got} of the {ceiling} available documents; "
                    f"the shortfall is this arm's own failure ({why}), so its paired n against "
                    f"`{REFERENCE_CELL}` is the intersection."
                )
    return notes


def collect_comparison(*, repo: Path | None = None) -> dict[str, Any]:
    cells = {cell: collect_cell(cell, repo=repo) for cell in CELL_ORDER}
    deltas: dict[str, Any] = {}
    reference = cells[REFERENCE_CELL]["cards"]
    for cell in CELL_ORDER:
        if cell == REFERENCE_CELL:
            continue
        against = cells[cell]["cards"]
        per_class = {}
        for run_id, card in against.items():
            ref = reference.get(run_id.replace(f"-{cell}", f"-{REFERENCE_CELL}"))
            if ref is None:
                continue
            d = paired_delta(ref, card)
            if d:
                d["n_for_delta_0_05"] = paired_n_for(0.05, d.get("sd_diff"))
                per_class[_task_of(run_id)] = d
        deltas[cell] = {"vs": REFERENCE_CELL, "per_class": per_class}
    return {
        "schema": SCHEMA_CELL,
        "kind": "comparison",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reference_cell": REFERENCE_CELL,
        "cells": {c: {"replicas": CELLS[c][0], "concurrency": CELLS[c][1]} for c in CELL_ORDER},
        "deltas": deltas,
        "pairing_notes": pairing_notes(cells),
        "draw_identity": _draw_identity(repo=repo),
        "noise_floor": _noise_floor(repo=repo),
    }


def _noise_floor(*, repo: Path | None = None) -> dict[str, Any] | None:
    twin = cell_run_ids("1l4-c8")[0]
    base = specialist_dir("1l4-c8", "correspondence_specialist", repo=repo)
    a = _read_json(base / f"{twin}.card.json")
    b = _read_json(base / f"{NOISE_FLOOR_RUN}.card.json")
    if not a or not b:
        return None
    d = paired_delta(a, b)
    if not d:
        return None
    d["n_for_delta_0_05"] = paired_n_for(0.05, d.get("sd_diff"))
    d["n_for_delta_0_03"] = paired_n_for(0.03, d.get("sd_diff"))
    d["twin"] = twin
    d["noise_floor_run"] = NOISE_FLOOR_RUN
    return d


def _draw_identity(*, repo: Path | None = None) -> dict[str, dict[str, list[str]]]:
    """Per class, the documents each cell actually ran — read from the run stores.

    Not from the cards: the comparison's card payload is trimmed to what the deltas need and
    carries no per-document ids, so a claim built on it could only ever say "cannot verify".
    The store is also the artifact the claim is about, rather than the config that was supposed
    to produce it. The dataset fingerprint cannot stand in for this — it pins the
    repo/revision, not the selection.
    """
    runs = (Path(repo) if repo else repo_root()) / "data" / "runtime" / "runs"
    out: dict[str, dict[str, list[str]]] = {}
    for cell in CELL_ORDER:
        for d in sorted(runs.glob(f"sand42-50-*-awq-{cell}")):
            store = d / "dataset.jsonl"
            if not store.is_file():
                continue
            cls = d.name.split("-specialist-awq-")[0]
            out.setdefault(cls, {})[cell] = [
                json.loads(x)["id"]
                for x in store.read_text(encoding="utf-8").splitlines() if x.strip()
            ]
    return out


def _draw_claim(identity: Mapping[str, Mapping[str, Sequence[str]]]) -> str:
    """The headline claim, generated from the documents the cells actually ran.

    Hardcoded, this read "the identical 250 documents" no matter which documents the cells
    scored — the one sentence in the report whose being wrong would invalidate every delta
    beneath it, and the claim the whole campaign exists to make true.
    """
    if not identity:
        return ("Draw identity: no run store yet — cannot verify which documents the cells "
                "scored.")
    split = {
        cls: by_cell
        for cls, by_cell in identity.items()
        if len({frozenset(ids) for ids in by_cell.values()}) > 1
    }
    if not split:
        per_class = next(iter(identity.values()))
        n_class = len(next(iter(per_class.values())))
        total = n_class * len(identity)
        return (
            f"All {len(CELL_ORDER)} cells score the **identical {total} documents** "
            f"({len(identity)} specialists × {n_class} documents, one subclass-stratified draw "
            "per class), so every cell-to-cell delta below is **paired**: the unit of analysis "
            "is the per-document score difference. Intervals are 95% percentile bootstrap over "
            "documents; the last column is the paired n that Δ = 0.05 would need at 80% power."
        )
    detail = "; ".join(
        f"`{cls}`: " + " vs ".join(
            f"{sorted(c for c, ids in by_cell.items() if set(ids) == draw)} ({len(draw)} docs)"
            for draw in {frozenset(ids) for ids in by_cell.values()}
        )
        for cls, by_cell in sorted(split.items())
    )
    return (
        f"**The cells do NOT all score the same documents.** {detail}. "
        "Any delta between cells on different draws is **not paired** — the per-document "
        "difference is undefined across a draw change, so those columns compare different "
        "documents and must not be read as a comparison until every cell re-runs on one draw. "
        "Everything else in this table (cost, throughput, engine telemetry) is unaffected."
    )


def render_comparison_md(
    data: Mapping[str, Any], *, figures: Sequence[Path] | None = None
) -> str:
    lines = [
        f"# SAND-042 · paired comparison across the {len(CELL_ORDER)} cells",
        "",
        _draw_claim(data.get("draw_identity") or _draw_identity()),
        "",
        f"Reference cell: **{data['reference_cell']}** "
        "(1×L4, client concurrency 8).",
        "",
    ]
    for cell, block in data["deltas"].items():
        reps = data["cells"][cell]["replicas"]
        conc = data["cells"][cell]["concurrency"]
        per = conc / reps
        lines += [
            f"## {cell} ({reps}× L4 · C{conc}"
            + (f" · {per:g}/replica" if reps > 1 else "")
            + f") vs {block['vs']}",
            "",
            "| Class | Paired n | Δ mean | 95% CI | SD_diff | better / worse / tie | n for Δ=0.05 |",
            "| --- | ---: | ---: | --- | ---: | --- | ---: |",
        ]
        if not block["per_class"]:
            lines.append("| _not run yet_ | | | | | | |")
        for task, d in sorted(block["per_class"].items()):
            label = dict((t, l) for t, _, l in SPECIALISTS).get(task, task)
            lines.append(
                f"| {label} | {d['paired_documents']} | {d['delta_mean']:+.3f} | "
                f"{_ci(d['ci_low'], d['ci_high'])} | "
                f"{_f(d.get('sd_diff'), 3)} | "
                f"{d['better']} / {d['worse']} / {d['tie']} | "
                f"{d.get('n_for_delta_0_05') or '—'} |"
            )
        lines.append("")
    nf = data.get("noise_floor")
    lines += ["## Noise floor (run-to-run, same 50 documents)", ""]
    if nf:
        lines += [
            f"`{nf['noise_floor_run']}` re-run against `{nf['twin']}` "
            "(identical settings, identical documents):",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Paired documents | {nf['paired_documents']} |",
            f"| Δ mean (should be ≈ 0) | {nf['delta_mean']:+.3f} |",
            f"| 95% CI | {_ci(nf['ci_low'], nf['ci_high'])} |",
            f"| SD of the difference | {_f(nf.get('sd_diff'), 3)} |",
            f"| better / worse / tie | {nf['better']} / {nf['worse']} / {nf['tie']} |",
            f"| Paired n for Δ=0.05 | {nf.get('n_for_delta_0_05') or '—'} |",
            f"| Paired n for Δ=0.03 | {nf.get('n_for_delta_0_03') or '—'} |",
            "",
            "**Quote no delta smaller than this floor.** Any cell-to-cell interval that "
            "contains 0 is inside the noise floor.",
            "",
        ]
    else:
        lines += [
            "_Not measured._ Run `sand42-noise-floor` (blocked until spend is approved) on "
            "the same 50 correspondence documents. Until then the SAND-037/39 floor in "
            "`docs/BENCHMARK-PROGRAM.md` §3 is the prior — it was measured on a different "
            "draw, so treat it as indicative only.",
            "",
        ]
    if figures:
        lines += ["## Figures", ""]
        lines += [_figure_line(p) for p in figures]
        lines += [""]
    notes = data.get("pairing_notes") or []
    if notes:
        lines += [
            "## Why a paired n can be below the class's document count",
            "",
            "The unit of analysis is the **per-document** score difference, so a class's paired n "
            "is the intersection of the documents both arms score. Where that is less than the "
            "50-document draw, this is why:",
            "",
        ]
        lines += [f"* {n}" for n in notes]
        lines += [""]
    lines += [
        f"_Generated {data['generated_at']} by `sandbox run card --runbook sand42`._",
        "",
    ]
    return "\n".join(lines)


def write_comparison(*, repo: Path | None = None) -> dict[str, Path]:
    data = collect_comparison(repo=repo)
    paths = comparison_paths(repo=repo)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    _atomic_text(paths["json"], json.dumps(data, indent=2, sort_keys=True) + "\n")
    _atomic_text(paths["md"], render_comparison_md(data, figures=_master_figures(repo=repo)))
    return paths


def write_noise_floor(*, repo: Path | None = None) -> dict[str, Path]:
    """Standalone noise-floor memo (the comparison card embeds the same numbers)."""
    nf = _noise_floor(repo=repo)
    paths = noise_floor_paths(repo=repo)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    body = [
        "# SAND-042 · noise floor",
        "",
        "Run-to-run spread on **identical documents and identical settings** — the "
        "number every SAND-042 delta must clear before it is called real.",
        "",
    ]
    if nf:
        body += [
            f"* Twin A: `{nf['twin']}`",
            f"* Twin B: `{nf['noise_floor_run']}`",
            "",
            f"* Paired documents: {nf['paired_documents']}",
            f"* Δ mean: {nf['delta_mean']:+.3f} (95% CI {_ci(nf['ci_low'], nf['ci_high'])})",
            f"* SD of the difference: {_f(nf.get('sd_diff'), 3)}",
            f"* better / worse / tie: {nf['better']} / {nf['worse']} / {nf['tie']}",
            f"* Paired n for Δ=0.05: {nf.get('n_for_delta_0_05') or '—'}",
            f"* Paired n for Δ=0.03: {nf.get('n_for_delta_0_03') or '—'}",
            "",
        ]
    else:
        body += ["_Not measured yet — both twin cards must exist first._", ""]
    _atomic_text(paths["md"], "\n".join(body))
    return paths


def write_all(*, repo: Path | None = None) -> dict[str, Path]:
    """Every SAND-042 report: one condition card per cell, comparison, noise floor, master."""
    out: dict[str, Path] = {}
    for cell in CELL_ORDER:
        paths = write_cell(cell, repo=repo)
        out[f"cell-{cell}"] = paths["md"]
    out["comparison"] = write_comparison(repo=repo)["md"]
    out["noise-floor"] = write_noise_floor(repo=repo)["md"]
    master = write_master(repo=repo)
    out["master-card"] = master["card_md"]
    out["master-report"] = master["report_md"]
    return out


# ── master cost card + master full report ────────────────────────────────────


MASTER_CARD_STEM = "SAND42-MASTER-SCORE-COST-CARD"
MASTER_REPORT_STEM = "SAND42-MASTER-REPORT"


def master_paths(*, repo: Path | None = None) -> dict[str, Path]:
    base = study_root("sand42-", repo=repo)
    return {
        "dir": base,
        "card_md": base / f"{MASTER_CARD_STEM}.md",
        "card_json": base / f"{MASTER_CARD_STEM}.json",
        "report_md": base / f"{MASTER_REPORT_STEM}.md",
        "metered": base / "metered-costs.json",
    }


def write_metered(study: str, metered_usd: float, billed_usd: float, *, repo: Path | None = None) -> Path:
    """Record a SAND-042 session's teardown spend check."""
    path = master_paths(repo=repo)["metered"]
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read_json(path)
    data[study] = {"metered_usd": round(float(metered_usd), 2), "billed_usd": round(float(billed_usd), 2)}
    _atomic_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")
    return path


def _mid_has_pressure(run_dir: Path) -> bool:
    """True when a mid-run sample caught the engine WORKING (a non-zero KV reading).

    The file merely existing is not what the completeness row claims: the mid loop can land
    its only sample on a drained edge, leaving a present-but-zero artifact that would be
    counted as a captured mid-run KV.
    """
    series = run_dir / "vllm_metrics_mid.series.jsonl"
    if not series.is_file():
        return False
    for line in series.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            reps = (json.loads(line).get("replicas") or {}).values()
        except ValueError:
            continue
        if any((r.get("kv_cache_usage_perc") or 0) > 0 for r in reps):
            return True
    return False


def metric_completeness(*, repo: Path | None = None) -> dict[str, Any]:
    """Per-cell coverage of every required metric, measured from the artifacts.

    Generated rather than hand-written on purpose: a hand-written limitations note goes
    stale the moment a cell is re-run, and a reader who finds "not captured" beside a
    captured value stops trusting the whole table. This reads the run store, so it is
    true by construction.
    """
    root = Path(repo) if repo else repo_root()
    runs_root = root / "data" / "runtime" / "runs"
    cfg_root = root / "config" / "runs"
    out: dict[str, Any] = {}
    for cell in CELL_ORDER:
        # The denominator comes from the CONFIGS, never from the directories that happen to
        # exist. A leg archives its run dirs while it re-runs them, and a denominator taken from
        # the directory turns four missing runs into "all" — a false "complete" for a cell that
        # lost most of its runs.
        expected = [p.stem for p in sorted(cfg_root.glob(f"sand42-*-awq-{cell}.yaml"))
                    if not p.name.startswith("sand42-check-")]
        dirs = [runs_root / rid for rid in expected if (runs_root / rid).is_dir()]
        # "verbatim /metrics" is the full exporter text at all three edges; counting only the
        # after-scrape would call a run complete whose mid scrape never happened.
        verbatim = sum(1 for d in dirs if all(
            (d / f"vllm_metrics_{lbl}.txt").is_file() for lbl in ("before", "mid", "after")))
        bandwidth = mid = 0
        for d in dirs:
            probe = d / "container_telemetry_after.json"
            if probe.is_file() and "utilization_memory_perc" in probe.read_text(encoding="utf-8"):
                bandwidth += 1
            if _mid_has_pressure(d):
                mid += 1
        window = _read_json(_cell_dir(cell, repo=repo) / "fleet_window.json")
        out[cell] = {
            "runs": len(expected),
            "verbatim_metrics": verbatim,
            "bandwidth": bandwidth,
            "mid_run_kv": mid,
            "cold_boot": bool(window.get("ready_ts")),
        }
    return out


def render_completeness_md(comp: Mapping[str, Any]) -> list[str]:
    """The master report's completeness section: the matrix, then what each gap means."""
    lines = [
        "## Metric completeness",
        "",
        "Measured from the artifacts rather than asserted — `verbatim /metrics` is the full",
        "exporter output preserved per replica; `bandwidth` is the in-container nvidia-smi",
        "series carrying `utilization.memory`; `mid-run KV` is a sample taken while the run was",
        "WORKING (the before/after scrapes bracket the run and read 0 by construction); `cold",
        "boot` is the fleet window having recorded `ready_ts`.",
        "",
        "| Cell | verbatim /metrics | GPU mem bandwidth | mid-run KV / queue | cold boot |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    def frac(cell_data: Mapping[str, Any], n: int, key: str) -> str:
        v = int(cell_data.get(key) or 0)
        return "—" if n == 0 else ("all" if v == n else f"{v}/{n}")

    for cell in CELL_ORDER:
        c = comp.get(cell) or {}
        n = int(c.get("runs") or 0)
        lines.append(
            f"| `{cell}` | {frac(c, n, 'verbatim_metrics')} | {frac(c, n, 'bandwidth')} | "
            f"{frac(c, n, 'mid_run_kv')} | {'yes' if c.get('cold_boot') else 'no'} |"
        )

    gaps: list[str] = []
    for cell in CELL_ORDER:
        c = comp.get(cell) or {}
        n = int(c.get("runs") or 0)
        if n == 0:
            continue
        for key, label in (("verbatim_metrics", "verbatim /metrics"),
                           ("bandwidth", "GPU memory bandwidth"),
                           ("mid_run_kv", "mid-run KV / queue")):
            miss = n - int(c.get(key) or 0)
            if miss:
                gaps.append(f"`{cell}` — {label}: {miss} of {n} run(s) not sampled")
        if not c.get("cold_boot"):
            gaps.append(f"`{cell}` — cold boot: `ready_ts` never written (the sequential "
                        "driver's cells record a fleet window without a boot boundary)")
    lines.append("")
    if gaps:
        lines += [
            "**Open coverage.** Every blank above carries its reason; a gap is never rendered "
            "as a number, and none of these blanks is a failed capture:",
            "",
        ]
        lines += [f"* {g}" for g in gaps]
    else:
        lines.append("No coverage gaps: every required metric is captured for every run.")
    lines += [
        "",
        "*Mid-run KV / queue is diagnostic telemetry, not a primary endpoint — it explains a "
        "throughput result rather than producing one, and no headline number depends on it. "
        "The primary endpoints (per-class throughput, $/1k ok documents, quality with CIs) and "
        "the verbatim engine telemetry are complete for every cell. Per-class pairing "
        "ceilings (e.g. contracts) are explained in the comparison's pairing note.*",
        "",
    ]
    return lines


def collect_master(*, repo: Path | None = None) -> dict[str, Any]:
    cells = {cell: collect_cell(cell, repo=repo) for cell in CELL_ORDER}
    return {
        "schema": SCHEMA_CELL,
        "kind": "master",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cells": cells,
        "comparison": collect_comparison(repo=repo),
        "metered": _read_json(master_paths(repo=repo)["metered"]),
        "completeness": metric_completeness(repo=repo),
        "draw_identity": _draw_identity(repo=repo),
    }


def _findings(cells: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    reported = {c: d["cells_reported"] for c, d in cells.items()}
    pending = [c for c, n in reported.items() if n == 0]
    if pending:
        # A cell that has not run narrows the claim; it must not void the cells that
        # have. Registering 2l4-c32 (SAND-047) put the grid at 4 of 5, and the old
        # early return would have replaced every finding with "not measured yet".
        out.append(
            "Pending — condition cards report "
            + ", ".join(f"{c} {n}/5" for c, n in reported.items())
            + f". The findings below cover the {len(CELL_ORDER) - len(pending)} completed "
            "condition(s) only; no claim here spans a pending condition."
        )
    ref = cells[REFERENCE_CELL]["specialists"]
    for cell in CELL_ORDER:
        if cell == REFERENCE_CELL or not cells[cell]["cells_reported"]:
            continue
        for r in cells[cell]["specialists"]:
            base = next((x for x in ref if x["task"] == r["task"]), None)
            if not base or not r.get("reported"):
                continue
            dpm_a = base["throughput"].get("documents_per_minute_per_gpu")
            dpm_b = r["throughput"].get("documents_per_minute_per_gpu")
            if dpm_a and dpm_b:
                out.append(
                    f"{cell} vs {REFERENCE_CELL} · {r['task']}: "
                    f"{dpm_b / dpm_a - 1:+.0%} documents/min/GPU"
                )
    return out


def _cell_table(cells: Mapping[str, Any], fn) -> list[str]:
    header = " | ".join(
        f"{cells[c]['replicas']}×L4 C{cells[c]['concurrency']}" for c in CELL_ORDER
    )
    lines = [f"| Metric | {header} |", "| --- |" + " ---: |" * len(CELL_ORDER)]
    for task, _folder, label in SPECIALISTS:
        vals = []
        for cell in CELL_ORDER:
            row = next((r for r in cells[cell]["specialists"] if r["task"] == task), None)
            vals.append(fn(row) if row and row.get("reported") else "not run")
        lines.append(f"| {label} | " + " | ".join(vals) + " |")
    return lines


def _coverage_line(comp: Mapping[str, Any]) -> str:
    """One line of metric coverage for the master card.

    The card is the deliberate two-page executive, so this is the whole completeness story
    at its scale: counts over every run in the study, with the detail (and every reason)
    in the master report's generated completeness table.
    """
    total = sum(int((c or {}).get("runs") or 0) for c in comp.values())
    if not total:
        return ""

    def got(key: str) -> int:
        return sum(int((c or {}).get(key) or 0) for c in comp.values())

    return (
        f"**Metric coverage:** verbatim /metrics {got('verbatim_metrics')}/{total} · "
        f"GPU memory bandwidth {got('bandwidth')}/{total} · mid-run KV/queue "
        f"{got('mid_run_kv')}/{total} · cold boot "
        f"{sum(1 for c in comp.values() if (c or {}).get('cold_boot'))}/{len(comp)} cells. "
        "Every blank states its reason (no substitute values); the full matrix is in the "
        "master report."
    )


def render_master_card_md(data: Mapping[str, Any]) -> str:
    cells = data["cells"]
    done = sum(1 for c in CELL_ORDER if cells[c]["cells_reported"] == 5)
    lines = [
        "# SAND-042 master score & cost card — paired concurrency × fleet grid",
        "",
        f"**Conditions measured:** {done} of {len(CELL_ORDER)} · **Documents per condition:** 250 "
        "(5 specialists × n=50, one shared subclass-stratified draw) · "
        "**Model:** Qwen/Qwen3-8B-AWQ · L4 @ $0.80/GPU-hr · **Prompts:** v1 `*_simplified` only.",
        "",
        _coverage_line(data.get("completeness") or {}),
        "",
        f"{len(CELL_ORDER)} conditions — {{1×L4, 2×L4}} × {{client concurrency 8, 16}} plus the 2×L4 "
        "C32 saturation point (16 per replica, the engine's `max_num_seqs` admission ceiling) — on "
        "the SAND-037 aligned spec.",
        "",
        _draw_claim(data.get("draw_identity") or _draw_identity()),
        "Design, metric contract and acceptance rules: "
        "[`docs/SAND42-EXPERIMENT-DESIGN.md`](../../docs/SAND42-EXPERIMENT-DESIGN.md).",
        "",
        "## Conditions",
        "",
        "| Condition | Runbook | GPUs | Client concurrency | Per replica | min=max |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for cell in CELL_ORDER:
        c = cells[cell]
        per = c["concurrency"] / c["replicas"]
        lines.append(
            f"| `{cell}` | `sandbox runbook show sand42-{cell}` | {c['replicas']} | "
            f"{c['concurrency']} | {per:g} | {c['replicas']} |"
        )
    lines += [
        "",
        "**Matched per-replica-load pair:** `1l4-c8` vs `2l4-c16` (8 per replica each) isolates "
        "replica count. `1l4-c8` vs `1l4-c16` isolates concurrency at fixed GPUs. The 2×L4 cells "
        "are *not* a load twin of the 1×L4 cells.",
        "",
        "## Quality (mean field score; contracts CUAD presence F1, merger MAUD accuracy)",
        "",
        *_cell_table(cells, lambda r: f"{r['quality']['mean']:.3f}"),
        "",
        "## Serving efficiency (per condition, per specialist)",
        "",
        "| Metric | " + " | ".join(
            f"{cells[c]['replicas']}×L4 C{cells[c]['concurrency']}" for c in CELL_ORDER
        ) + " |",
        "| --- |" + " ---: |" * len(CELL_ORDER),
    ]
    for task, _folder, label in SPECIALISTS:
        for metric, fn in (
            ("documents/min/GPU", lambda r: _f(r["throughput"].get("documents_per_minute_per_gpu"), 2)),
            ("goodput docs/min/GPU", lambda r: _f(r["goodput"].get("goodput_documents_per_minute_per_gpu"), 2)),
            ("tokens/s/GPU", lambda r: _f(r["throughput"].get("tokens_per_second_per_gpu"), 0)),
            ("GPU util % (mean)", lambda r: _f(r["gpu"].get("util_mean_perc"), 1)),
            ("GPU mem used", lambda r: _mem_used_text(r["gpu"])),
            ("GPU mem bandwidth", lambda r: _mem_bw_text(r["gpu"])),
            ("$/1k ok", lambda r: _usd(r["cost"].get("usd_per_1k_ok"))),
            ("$/1k schema-valid", lambda r: _usd(r["cost"].get("usd_per_1k_schema_valid"))),
        ):
            vals = []
            for cell in CELL_ORDER:
                row = next((r for r in cells[cell]["specialists"] if r["task"] == task), None)
                vals.append(fn(row) if row and row.get("reported") else "not run")
            lines.append(f"| {label} · {metric} | " + " | ".join(vals) + " |")
    lines += [
        "",
        "## Paired deltas vs `1l4-c8`",
        "",
        "Intervals are 95% percentile bootstrap over documents; a CI containing 0 is inside the "
        "noise floor. Full table: [`SAND42-CELL-COMPARISON.md`](SAND42-CELL-COMPARISON.md).",
        "",
    ]
    any_delta = False
    for cell, block in data["comparison"]["deltas"].items():
        for task, d in sorted(block["per_class"].items()):
            any_delta = True
            lines.append(
                f"* `{cell}` vs `{block['vs']}` · {task}: Δ {d['delta_mean']:+.3f} "
                f"({_ci(d['ci_low'], d['ci_high'])}, n={d['paired_documents']}, "
                f"{d['better']}/{d['worse']} better/worse)"
            )
    if not any_delta:
        lines.append("*_Not measured yet._*")
    lines += ["", "## Findings", ""]
    lines += [f"* {f}" for f in _findings(cells)]
    lines += ["", "## Cost", ""]
    metered = data.get("metered") or {}
    if metered:
        lines += ["| Session | Metered USD | Billed USD |", "| --- | ---: | ---: |"]
        for study, row in sorted(metered.items()):
            lines.append(f"| {study} | {row.get('metered_usd')} | {row.get('billed_usd')} |")
    else:
        lines.append("_No teardown spend recorded yet_ "
                     "(`sandbox run card --record-metered SAND-42 <metered> <billed>`).")
    lines += [
        "",
        "Per-condition detail and engine/GPU telemetry: "
        f"[`{MASTER_REPORT_STEM}.md`]({MASTER_REPORT_STEM}.md).",
        "",
        f"_Generated {data['generated_at']} by `sandbox run card --runbook sand42`._",
        "",
    ]
    return "\n".join(lines)


def render_master_report_md(
    data: Mapping[str, Any], *, figures: Sequence[Path] | None = None
) -> str:
    cells = data["cells"]
    lines = [
        "# SAND-042 master report — full detail",
        "",
        "Per-condition tables, engine and GPU telemetry, the paired comparison and the method. "
        "Executive summary: "
        f"[`{MASTER_CARD_STEM}.md`]({MASTER_CARD_STEM}.md).",
        "",
    ]
    for cell in CELL_ORDER:
        # Embedded a level up from the cell folder, so rebase every per-run link.
        prefix = f"{grid_cards.condition_dir(f'sand42-x-{cell}', cells[cell]['replicas'])}/"
        lines += [render_cell_md(cells[cell], link_prefix=prefix), "", "---", ""]
    lines += [render_comparison_md(data["comparison"]), "", "---", ""]
    if figures:
        lines += ["## Figures", ""]
        lines += [_figure_line(p) for p in figures]
        lines += ["", "---", ""]
    lines += [
        "## Method",
        "",
        f"* Engine, prompts, decode, dataset pin and draw are identical across the {len(CELL_ORDER)} conditions; "
        "only the replica count and the client concurrency differ (asserted in "
        "`tests/test_sand42_grid.py`).",
        "* Client concurrency is split equally across replicas: 2×L4 C8 → 4 per replica, "
        "2×L4 C16 → 8 per replica, 2×L4 C32 → 16 per replica (the engine's `max_num_seqs` ceiling).",
        "* One warm fleet per condition (`min_containers = max_containers = replicas`), five "
        "specialists chained, teardown after the fifth: one cold boot per condition.",
        "* Quality intervals are percentile bootstraps over per-document scores; deltas are paired "
        "on the shared 250 documents; ok rates use a Wilson interval.",
        "* GPU hardware telemetry is sampled inside the serving replica (nvidia-smi util / power / "
        "temperature / memory) and recorded per condition; vLLM `/metrics` gives the engine side "
        "(TTFT, prefix-cache hit rate, preemptions, length finishes, KV use) per replica.",
        "* Sample sizes, the noise floor and the contracts caveat: "
        "`docs/BENCHMARK-PROGRAM.md` §3 and `docs/SAND42-EXPERIMENT-DESIGN.md` §4.",
        "",
        *render_completeness_md(data.get("completeness") or {}),
        "## Open items",
        "",
        "* The noise-floor leg (`sand42-noise-floor`) runs with the 1L4-C8 re-run (spend approved "
        "2026-10-12), so the deltas above carry this campaign's own run-to-run floor rather than "
        "the SAND-037/39 prior, which was measured on a different draw.",
        "* Mid-run KV / queue is unsampled for `2l4-c8` and for four of the five `2l4-c32` runs. "
        "Both are re-runnable without changing the design; the completeness table above is "
        "generated from the run store, so it cannot go stale when they land.",
        "* Contracts at n=50 paired is marginal for Δ=0.05 and unpowered for Δ=0.03 — report as an "
        "interval, never a ranking.",
        "* OTel *metrics* export from the container is not wired (the telemetry is an nvidia-smi "
        "series); trace spans stay opt-in via `trace.sink`.",
        "* This grid shows the second L4 does not pay per GPU, but not whether that is a property "
        "of the L4s or of the client feeding them. The controlled test — data-parallel with a "
        "per-request feed, tensor-parallel on one endpoint, and a raised admission ceiling — is "
        "designed in [`docs/SAND42-FOLLOWUP-DESIGN.md`](../../docs/SAND42-FOLLOWUP-DESIGN.md).",
        "",
        f"_Generated {data['generated_at']} by `sandbox run card --runbook sand42`._",
        "",
    ]
    return "\n".join(lines)


def write_master(*, repo: Path | None = None) -> dict[str, Path]:
    data = collect_master(repo=repo)
    paths = master_paths(repo=repo)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    _atomic_text(paths["card_json"], json.dumps(data, indent=2, sort_keys=True) + "\n")
    _atomic_text(paths["card_md"], render_master_card_md(data))
    _atomic_text(paths["report_md"], render_master_report_md(data, figures=_master_figures(repo=repo)))
    return paths

