"""SAND-042 figures, generated automatically after each run / per cell / for the master card.

Rendered from the committed per-run cards (``sandbox.grid-card/v1``) under
``reports/SAND42/<CELL>/<specialist>/<run_id>.card.json`` — no live run, no network.
Outputs, all under ``reports/SAND42/``::

    <CELL>/<specialist>/<run_id>.card.png   per-run dashboard (written after each run)
    figures/<cell>-dashboard.png            per-cell dashboard over the five specialists
    figures/cmp-{quality,cost,latency,throughput,gpu}.png
                                            master comparison suite (one PNG per metric)

Partial or missing cards are normal while the campaign fills the cells in: what is
present is drawn, what is absent is skipped. Rendering is deterministic — the same cards
give byte-identical PNGs — because the matplotlib version stamp is stripped on save.

Style follows the SAND-037 record figures (``reports/SAND-37/figures/record``): the
left-aligned title/subtitle/footnote frame and the horizontal dot charts; the
``metadata={"Software": None}`` save follows ``grid_figures``.
"""

from __future__ import annotations

import logging
import statistics
from pathlib import Path
from typing import Any, Mapping

from mailroom_sandbox.job import sand42_cards
from mailroom_sandbox.job.grid_cards import SPECIALISTS, _read_json, study_root

_log = logging.getLogger("mailroom_sandbox.job.sand42_figures")

# Palette + frame constants from the SAND-037 record figures.
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"

# Categorical slots of the dataviz reference palette, one per cell. Slots 1-4 are the
# original validated set; slot 5 (#d55181, the reference's fifth step) was added for the
# 2l4-c32 saturation cell, whose absence here made write_master_figures raise KeyError.
CELL_COLORS: dict[str, str] = {
    "1l4-c8": "#eb6834",
    "1l4-c16": "#2a78d6",
    "2l4-c8": "#1baf7a",
    "2l4-c16": "#eda100",
    "2l4-c32": "#d55181",
}

FIG_SUBDIR = "figures"

_SHORT = {
    "correspondence_specialist": "Correspondence",
    "insurance_claims_specialist": "Insurance\nclaims",
    "corporate_records_specialist": "Corporate\nrecords",
    "contracts_specialist": "Contracts",
    "merger_agreement_specialist": "Merger\nagreements",
}
_SOURCE = "Source: per-run grid cards (sandbox.grid-card/v1)."

_MASTER = {
    "quality": {
        "title": "Overall extraction score by specialist and cell",
        "subtitle": "Overall extraction score (mean over documents) · 0–1, higher is better",
        "note": _SOURCE + " CUAD clause F1 (contracts) and MAUD accuracy (merger) are separate "
                          "clause metrics on the run cards.",
        "fmt": lambda v: f"{v:.3f}",
        "value": lambda card, cell: _primary(card),
        "log": False,
        "xlim": (0.0, 1.05),
    },
    "cost": {
        "title": "GPU cost per 1,000 ok documents by specialist and cell",
        "subtitle": "Billed GPU $ ÷ ok docs × 1,000 (log scale, lower is better)",
        "note": _SOURCE,
        "fmt": lambda v: f"${v:,.2f}",
        "value": lambda card, cell: _per_1k(card),
        "log": True,
        "xlim": None,
    },
    "latency": {
        "title": "Per-document latency p50 by specialist and cell",
        "subtitle": "End-to-end seconds (log scale, lower is better)",
        "note": _SOURCE,
        "fmt": lambda v: f"{v:,.1f} s",
        "value": lambda card, cell: _num(_mapping(card.get("latency")).get("p50")),
        "log": True,
        "xlim": None,
    },
    "throughput": {
        "title": "Throughput by specialist and cell",
        "subtitle": "Documents per minute per GPU (log scale, higher is better)",
        "note": _SOURCE,
        "fmt": lambda v: f"{v:,.2f}",
        "value": lambda card, cell: _dpm_per_gpu(card, cell),
        "log": True,
        "xlim": None,
    },
    "gpu": {
        "title": "GPU utilization by specialist and cell",
        "subtitle": "nvidia-smi mean utilization (%) across the run (higher = more work in flight)",
        "note": _SOURCE,
        "fmt": lambda v: f"{v:,.1f}%",
        "value": lambda card, cell: _num(_mapping(_mapping(card.get("engine_telemetry")).get("gpu")).get("util_mean_perc")),
        "log": False,
        "xlim": (0.0, 105.0),
    },
}


# ── small accessors (never raise on a partial card) ──────────────────────────


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _docs(card: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [d for d in (card.get("documents") or []) if isinstance(d, Mapping)]


def _cell_of_run(run_id: str) -> str | None:
    for cell in sand42_cards.CELL_ORDER:
        if str(run_id).endswith(f"-{cell}"):
            return cell
    return None


def _usable(card: Any) -> bool:
    """A drawable run card: an id plus at least one scored document."""
    if not isinstance(card, Mapping) or not isinstance(card.get("run_id"), str):
        return False
    return any(_num(d.get("score")) is not None for d in _docs(card))


def _primary(card: Mapping[str, Any]) -> float | None:
    """Primary quality metric — the card's "Overall extraction score".

    A single scale across every specialist: the mean suite extraction score over
    documents (matching the per-run card and the cell/master report table). The
    task-native CUAD clause F1 (contracts) and MAUD accuracy (merger) live in the
    run card's clause section, so the comparison axis is not a mix of metrics.
    """
    return _num(_mapping(card.get("quality")).get("overall_mean"))


def _replicas(card: Mapping[str, Any], cell: str) -> int:
    value = _num(_mapping(card.get("conditions")).get("replicas"))
    if value is None:
        value = float((sand42_cards.CELLS.get(cell) or (1, 0))[0])
    return max(1, int(value))


def _dpm_per_gpu(card: Mapping[str, Any], cell: str) -> float | None:
    dpm = _num(_mapping(card.get("throughput")).get("documents_per_minute"))
    return None if dpm is None else dpm / _replicas(card, cell)


def _cell_label(cell: str) -> str:
    replicas, concurrency = sand42_cards.CELLS[cell]
    return f"{replicas}xL4 C{concurrency}"


def _cell_cards(cell: str, *, repo: Path | None = None) -> dict[str, Mapping[str, Any]]:
    """``task -> card`` for one cell, from its canonical run ids (skips check runs)."""
    cards: dict[str, Mapping[str, Any]] = {}
    for run_id in sand42_cards.cell_run_ids(cell):
        task = sand42_cards._task_of(run_id)
        card = _read_json(sand42_cards.specialist_dir(cell, task, repo=repo) / f"{run_id}.card.json")
        if card:
            cards[task] = card
    return cards


# ── drawing primitives ───────────────────────────────────────────────────────


def _plt():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _style(plt) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans", "font.size": 9, "text.color": INK, "axes.labelcolor": INK2,
            "axes.edgecolor": AXIS, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
            "xtick.color": MUTED, "ytick.color": INK, "axes.titlesize": 10, "axes.titleweight": "bold",
            "axes.titlelocation": "left", "axes.titlecolor": INK, "grid.color": GRID, "grid.linewidth": 0.6,
            "savefig.facecolor": SURFACE, "savefig.dpi": 200, "text.parse_math": False,
            "legend.frameon": False,
        }
    )


def _save(fig, path: Path, plt) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Strip the matplotlib version stamp so re-renders of unchanged data are byte-stable.
    fig.savefig(path, bbox_inches="tight", metadata={"Software": None}, facecolor=SURFACE)
    plt.close(fig)


def _frame(plt, title: str, subtitle: str, note: str, *, figsize=(10.0, 7.0)):
    """2×2 frame with the SAND-037 title/subtitle/footnote layout."""
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    fig.subplots_adjust(left=0.075, right=0.975, top=0.85, bottom=0.115, hspace=0.46, wspace=0.20)
    fig.text(0.012, 0.985, title, fontsize=13, fontweight="bold", va="top")
    fig.text(0.012, 0.938, subtitle, fontsize=9, color=INK2, va="top")
    fig.text(0.012, 0.02, note, fontsize=7.5, color=MUTED, va="bottom")
    return fig, axes


def _row_frame(plt, title: str, subtitle: str, note: str, *, rows: int, legend=None):
    """One-axes horizontal dot frame; ``legend`` is a list of ``(color, label)``."""
    height = 0.55 * rows + 2.1 + (0.3 if legend else 0)
    fig, ax = plt.subplots(figsize=(8.6, height))
    fig.subplots_adjust(left=0.22, right=0.95, top=1 - (1.2 if legend else 0.95) / height, bottom=0.95 / height)
    fig.text(0.02, 0.985, title, fontsize=13, fontweight="bold", va="top")
    fig.text(0.02, 0.985 - 0.34 / height, subtitle, fontsize=9, color=INK2, va="top")
    fig.text(0.02, 0.015, note, fontsize=7.5, color=MUTED, va="bottom")
    if legend:
        from matplotlib.lines import Line2D

        fig.legend(
            handles=[Line2D([], [], marker="o", ls="", ms=7, color=c, label=l) for c, l in legend],
            loc="upper left", bbox_to_anchor=(0.012, 0.985 - 0.58 / height), ncol=len(legend),
            fontsize=9, handletextpad=0.3, columnspacing=1.6,
        )
    return fig, ax


def _axis_style(ax, log: bool = False) -> None:
    ax.set_axisbelow(True)
    ax.grid(axis="x", which="major")
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0, labelsize=8)
    if log:
        _log_axis(ax)


def _log_axis(ax) -> None:
    """Plain-number log ticks (``parse_math`` is off, so the mathtext default would not render)."""
    from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

    ax.set_xscale("log")
    ax.xaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))


def _note_at(ax, text: str) -> None:
    ax.annotate(text, (0.02, 0.96), xycoords="axes fraction", va="top", ha="left", fontsize=8, color=INK2)


# ── A. per-run dashboard ─────────────────────────────────────────────────────


def run_figure_name(run_id: str) -> str:
    return f"{run_id}.card.png"


def write_run_figure(card, out_dir) -> Path | None:
    """Write the 2×2 dashboard for one run card; ``None`` when the card is not drawable."""
    if not _usable(card):
        return None
    path = Path(out_dir) / run_figure_name(str(card["run_id"]))
    plt = _plt()
    _style(plt)
    _draw_run(plt, card, path)
    return path


def _draw_run(plt, card: Mapping[str, Any], path: Path) -> None:
    import numpy as np

    cond = _mapping(card.get("conditions"))
    quality = _mapping(card.get("quality"))
    cost = _mapping(card.get("cost"))
    latency = _mapping(card.get("latency"))
    gpu = _mapping(_mapping(card.get("engine_telemetry")).get("gpu"))
    docs = _docs(card)

    cell = _cell_of_run(str(card["run_id"]))
    color = CELL_COLORS.get(cell or "", INK2)

    replicas = _num(cond.get("replicas")) or len(_mapping(card.get("engine_telemetry")).get("replicas") or []) or 1
    concurrency = cond.get("concurrency")
    model = cond.get("model") or "—"
    specialist = card.get("specialist") or card.get("task") or "—"
    spec_hash = str(cond.get("spec_hash") or "")
    subtitle = (
        f"{specialist} · {int(replicas)}xL4 · C{concurrency} · n={card.get('n')} · {model}"
    )
    note = _SOURCE + (f" · spec {spec_hash[:12]}" if spec_hash else "")

    fig, axes = _frame(plt, str(card["run_id"]), subtitle, note)

    # 1. score histogram, mean line.
    scores = [s for s in (_num(d.get("score")) for d in docs) if s is not None]
    ax = axes[0][0]
    counts, _bins, _patches = ax.hist(scores, bins=[i / 10 for i in range(11)], color=color,
                                      edgecolor=SURFACE, linewidth=0.6, zorder=2)
    if len(counts):
        ax.set_ylim(0, max(counts) * 1.35)  # headroom so the mean/sd note never sits on a tall bar
    mean = _num(quality.get("overall_mean"))
    if mean is None and scores:
        mean = statistics.fmean(scores)
    sd = _num(quality.get("overall_sd"))
    if mean is not None:
        ax.axvline(mean, color=INK, linewidth=1.2, linestyle=(0, (4, 2)), zorder=3)
        _note_at(ax, f"mean {mean:.3f}\nsd {sd:.3f}" if sd is not None else f"mean {mean:.3f}")
    ax.annotate(
        f"{quality.get('ok', '—')}/{card.get('n', '—')} ok",
        (0.98, 0.96), xycoords="axes fraction", ha="right", va="top", fontsize=8, color=INK2,
    )
    ax.set_xlim(0, 1)
    ax.set_title("Per-document score")
    ax.set_xlabel("Score (0–1)")
    ax.set_ylabel("Documents")

    # 2. latency histogram, log x, p50/p95 markers.
    ax = axes[0][1]
    latencies = [v for v in (_num(d.get("latency_seconds")) for d in docs) if v and v > 0]
    if latencies:
        lo, hi = min(latencies), max(latencies)
        bins = np.logspace(np.log10(lo), np.log10(hi), 16) if hi > lo else 8
        counts, _bins, _patches = ax.hist(latencies, bins=bins, color=color, edgecolor=SURFACE,
                                          linewidth=0.6, zorder=2)
        if len(counts):
            ax.set_ylim(0, max(counts) * 1.35)
    for key, label, dy in (("p50", "p50", 0.96), ("p95", "p95", 0.86)):
        value = _num(latency.get(key))
        if value:
            ax.axvline(value, color=INK, linewidth=1.2, linestyle=(0, (4, 2)), zorder=3)
            ax.annotate(f"{label} {value:,.1f}s", (0.02, dy), xycoords="axes fraction", va="top",
                        fontsize=8, color=INK2)
    if latencies:
        _log_axis(ax)
    ax.set_title("Per-document latency")
    ax.set_xlabel("Seconds (log scale)")
    ax.set_ylabel("Documents")

    # 3. one cost bar.
    ax = axes[1][0]
    per_ok = _num(cost.get("usd_per_ok_document"))
    value = (per_ok or 0.0) * 1000.0
    ax.bar([0], [value], 0.5, color=color, edgecolor=SURFACE, linewidth=1.5, zorder=2)
    ax.annotate(f"${value:,.2f}" if per_ok is not None else "not captured",
                (0, value), xytext=(0, 4), textcoords="offset points", ha="center", va="bottom",
                fontsize=9, color=INK2)
    busy = _num(cost.get("busy_gpu_usd"))
    parts = []
    if per_ok is not None:
        parts.append(f"${per_ok:.5f} / doc")
    if busy is not None:
        parts.append(f"busy GPU ${busy:,.4f}")
    if parts:
        _note_at(ax, " · ".join(parts))
    ax.set_xticks([])
    ax.margins(y=0.25)
    ax.set_title("GPU cost per 1,000 ok documents")
    ax.set_ylabel("$ / 1k ok docs")

    # 4. GPU telemetry bars.
    ax = axes[1][1]
    util = [_num(gpu.get(k)) for k in ("util_mean_perc", "util_p95_perc", "util_peak_perc")]
    if gpu.get("captured") and any(v is not None for v in util):
        xs = list(range(3))
        ax.bar(xs, [v or 0.0 for v in util], 0.6, color=color, edgecolor=SURFACE, linewidth=1.5, zorder=2)
        for x, v in zip(xs, util):
            if v is not None:
                ax.annotate(f"{v:.0f}%", (x, v), xytext=(0, 3), textcoords="offset points", ha="center",
                            va="bottom", fontsize=8, color=INK2)
        ax.set_xticks(xs, ["mean", "p95", "peak"])
        ax.set_ylim(0, 132)
        parts = []
        cov = _num(gpu.get("sampling_coverage_pct"))
        power = _num(_mapping(gpu.get("power_draw_w")).get("mean"))
        temp = _num(_mapping(gpu.get("temperature_c")).get("mean"))
        if cov is not None:
            parts.append(f"coverage {cov:.0f}%")
        if power is not None:
            parts.append(f"power {power:,.1f} W")
        if temp is not None:
            parts.append(f"temp {temp:,.1f} C")
        if parts:
            _note_at(ax, " · ".join(parts))
    else:
        ax.text(0.5, 0.5, "GPU telemetry not captured", ha="center", va="center", color=MUTED, fontsize=9)
        ax.set_xticks([])
    ax.set_title("GPU utilization")
    ax.set_ylabel("%")

    _save(fig, path, plt)


# ── B. per-cell dashboard ────────────────────────────────────────────────────


def cell_figure_name(cell: str) -> str:
    return f"{cell}-dashboard.png"


def write_cell_figure(cell: str, *, repo: Path | None = None) -> Path | None:
    """One 2×2 dot dashboard across the cell's specialists; ``None`` when it has no cards."""
    if cell not in sand42_cards.CELLS:
        return None
    cards = _cell_cards(cell, repo=repo)
    if not cards:
        return None
    path = study_root("sand42-", repo=repo) / FIG_SUBDIR / cell_figure_name(cell)
    plt = _plt()
    _style(plt)
    _draw_cell(plt, cell, cards, path)
    return path


def _draw_cell(plt, cell: str, cards: Mapping[str, Mapping[str, Any]], path: Path) -> None:
    color = CELL_COLORS.get(cell, INK2)
    tasks = [task for task, _folder, _label in SPECIALISTS if task in cards]
    labels = [_SHORT[task] for task in tasks]
    n = next((c.get("n") for c in cards.values() if c.get("n")), 50)
    subtitle = ("Five specialists · overall extraction score (mean over documents) · "
                "dot = value, whisker = spread")
    fig, axes = _frame(plt, f"SAND-042 · {_cell_label(cell)} · n={n}", subtitle, _SOURCE)

    # primary score ± sd
    ax = axes[0][0]
    scores = [_primary(cards[t]) for t in tasks]
    sds = [_num(_mapping(cards[t].get("quality")).get("overall_sd")) for t in tasks]
    _dot_rows(ax, labels, scores, color, lambda v: f"{v:.3f}", err=sds, xlim=(0, 1.05))
    ax.set_title("Overall extraction score")

    # cost per 1k ok docs
    ax = axes[0][1]
    cost = [_per_1k(cards[t]) for t in tasks]
    _dot_rows(ax, labels, cost, color, lambda v: f"${v:,.2f}", log=True)
    ax.set_title("GPU $ per 1,000 ok docs")

    # latency p50 with p95 whisker
    ax = axes[1][0]
    p50 = [_num(_mapping(cards[t].get("latency")).get("p50")) for t in tasks]
    p95 = [_num(_mapping(cards[t].get("latency")).get("p95")) for t in tasks]
    _dot_rows(ax, labels, p50, color, lambda v: f"{v:,.1f} s", log=True, err=p95, err_kind="range")
    ax.set_title("Latency (p50 · p95 whisker)")

    # documents/min/GPU
    ax = axes[1][1]
    dpm = [_dpm_per_gpu(cards[t], cell) for t in tasks]
    _dot_rows(ax, labels, dpm, color, lambda v: f"{v:,.2f}", log=True)
    ax.set_title("Documents / min / GPU")

    _save(fig, path, plt)


def _per_1k(card: Mapping[str, Any]) -> float | None:
    per_ok = _num(_mapping(card.get("cost")).get("usd_per_ok_document"))
    return None if per_ok is None else per_ok * 1000.0


def _dot_rows(ax, labels, values, color, fmt, *, log=False, xlim=None, err=None, err_kind="sd") -> None:
    """Horizontal dot chart; rows whose value is ``None`` are dropped, not drawn as gaps."""
    rows = [(y, v, e) for y, (v, e) in enumerate(zip(values, err or [None] * len(values)), start=1) if v is not None]
    ys = [len(values) - y for y, _v, _e in rows]
    vals = [v for _y, v, _e in rows]
    errs = [e for _y, _v, e in rows]
    if err is not None and any(e is not None for e in errs):
        if err_kind == "range":
            highs = [max((e - v), 0.0) if e is not None else 0.0 for v, e in zip(vals, errs)]
            ax.errorbar(vals, ys, xerr=[[0.0 for _ in vals], highs], fmt="none",
                        ecolor=AXIS, elinewidth=1.4, zorder=2)
        else:
            ax.errorbar(vals, ys, xerr=[e or 0 for e in errs], fmt="none", ecolor=AXIS, elinewidth=1.4, zorder=2)
    ax.scatter(vals, ys, s=46, color=color, edgecolor=SURFACE, linewidth=1.5, zorder=3)
    for v, y in zip(vals, ys):
        ax.annotate(fmt(v), (v, y), xytext=(7, 0), textcoords="offset points", va="center", fontsize=8, color=INK2)
    ax.set_yticks([len(values) - y for y in range(1, len(values) + 1)], labels)
    ax.set_ylim(0.4, len(values) + 0.6)
    _axis_style(ax, log)
    if xlim:
        ax.set_xlim(*xlim)


# ── C. master / comparison figures ───────────────────────────────────────────


def master_figure_paths(*, repo: Path | None = None) -> dict[str, Path]:
    base = study_root("sand42-", repo=repo) / FIG_SUBDIR
    return {key: base / f"cmp-{key}.png" for key in _MASTER}


def write_master_figures(*, repo: Path | None = None) -> list[Path]:
    """One PNG per metric under ``reports/SAND42/figures/``; ``[]`` when no cell has cards."""
    data = {cell: _cell_cards(cell, repo=repo) for cell in sand42_cards.CELL_ORDER}
    if not any(data.values()):
        return []
    plt = _plt()
    _style(plt)
    paths = master_figure_paths(repo=repo)
    written = []
    for key, spec in _MASTER.items():
        _draw_master(plt, spec, data, paths[key])
        written.append(paths[key])
    return written


def _draw_master(plt, spec: Mapping[str, Any], data: Mapping[str, Mapping[str, Any]], path: Path) -> None:
    present = [cell for cell in sand42_cards.CELL_ORDER if data[cell]]
    legend = [(CELL_COLORS[cell], _cell_label(cell)) for cell in present]
    fig, ax = _row_frame(plt, spec["title"], spec["subtitle"], spec["note"],
                         rows=len(SPECIALISTS), legend=legend)

    ys = list(range(len(SPECIALISTS)))[::-1]
    order = {cell: i for i, cell in enumerate(present)}
    for y, (task, _folder, _label) in zip(ys, SPECIALISTS):
        for cell in present:
            card = data[cell].get(task)
            if not card:
                continue
            value = spec["value"](card, cell)
            if value is None:
                continue
            ax.scatter([value], [y], s=52, color=CELL_COLORS[cell], edgecolor=SURFACE, linewidth=1.5, zorder=3)
            # Fan the per-cell labels apart so near-equal values do not overprint.
            dy = (order[cell] - (len(present) - 1) / 2) * 8
            ax.annotate(spec["fmt"](value), (value, y), xytext=(7, dy), textcoords="offset points",
                        va="center", fontsize=7.5, color=INK2)
    ax.set_yticks(ys, [label for _task, _folder, label in SPECIALISTS])
    ax.set_ylim(-0.6, len(SPECIALISTS) - 0.4)
    _axis_style(ax, spec["log"])
    if spec["xlim"]:
        ax.set_xlim(*spec["xlim"])
    _save(fig, path, plt)


# ── never-raise wrappers (called from the LIVE card path) ────────────────────


def maybe_write_run_figure(card, out_dir) -> Path | None:
    try:
        return write_run_figure(card, out_dir)
    except Exception:
        _log.exception("SAND-042 run figure failed")
        return None


def maybe_write_cell_figure(cell: str, *, repo: Path | None = None) -> Path | None:
    try:
        return write_cell_figure(cell, repo=repo)
    except Exception:
        _log.exception("SAND-042 cell figure failed for %s", cell)
        return None


def maybe_write_master_figures(*, repo: Path | None = None) -> list[Path]:
    try:
        return write_master_figures(repo=repo)
    except Exception:
        _log.exception("SAND-042 master figures failed")
        return []
