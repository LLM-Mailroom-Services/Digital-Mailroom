"""Figures for the specialist-grid master card (SAND-037 / SAND-039).

Rendered from the same ``collect_master()`` data as the Markdown, so a later leg
fills its series in on the next ``sandbox run card --master``::

    reports/SAND-37/figures/cmp-*.png          posture comparison suite (master card body)
    reports/SAND-37/<1L4|2L4>/figures/*.png    one dashboard per posture (master card appendix)

``figure_specs()`` decides which figures exist from the data alone, so the
Markdown links are deterministic and testable without rendering; ``write_figures()``
draws them with matplotlib (Agg, no display).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from mailroom_sandbox.job.grid_cards import ROOT_REL, SPECIALISTS

# Categorical slots 1–4 of the dataviz reference palette, in fixed order by posture (validated:
# lightness band, chroma floor, CVD ΔE ≥ 9, normal-vision ΔE ≥ 22; sub-3:1 contrast is relieved by
# value labels and the master card's tables).
COLORS = {
    "s37-1l4-n20": "#2a78d6",
    "s39-1l4-n50": "#eb6834",
    "s37-2l4-n50": "#1baf7a",
    "s40-2l4": "#eda100",
}
# Token parts use slots 7, 5 and 6 so they never collide with a posture hue (validated as a set).
TOKEN_PARTS = (
    ("instruction", "Instructions + template", "#4a3aa7"),
    ("document", "Document text", "#e87ba4"),
    ("completion", "Output", "#008300"),
)
_ORDER = ("insurance_claims", "contracts", "corporate_records", "correspondence", "merger_agreement")
_SHORT = {
    "insurance_claims": "Insurance\nclaims",
    "contracts": "Contracts",
    "corporate_records": "Corporate\nrecords",
    "correspondence": "Correspondence",
    "merger_agreement": "Merger\nagreements",
}
_LABEL = {folder: label for _, folder, label in SPECIALISTS}


def _postures():
    from mailroom_sandbox.job.grid_master import POSTURES

    return POSTURES


def figure_specs(data: Mapping[str, Any]) -> list[dict[str, str]]:
    """Figures to render, as ``{"key", "path" (relative to reports/SAND-37), "caption", "section"}``."""
    cards = data["cards"]
    present = [p for p in _postures() if cards[p.key]]
    specs: list[dict[str, str]] = []
    if not present:
        return specs
    specs += [
        {
            "key": "cmp-efficiency",
            "path": "figures/cmp-efficiency.png",
            "section": "comparison",
            "caption": "Pooled serving efficiency by posture: GPU cost per 1,000 documents, tokens per second per GPU, "
            "and documents per minute. The Experiment 4 bar includes the † merger cell, which dominates its busy time; "
            "the like-for-like scale check is the table under *Serving efficiency*.",
        },
        {
            "key": "cmp-quality",
            "path": "figures/cmp-quality.png",
            "section": "comparison",
            "caption": "Primary quality metric by specialist and posture; labels mark failed documents. Merger "
            "is MAUD accuracy, a different scale from the field scores; † (hatched) marks the optimized Experiment 4 "
            "merger cell.",
        },
        {
            "key": "cmp-latency-cost",
            "path": "figures/cmp-latency-cost.png",
            "section": "comparison",
            "caption": "Per-document latency (bar p50, whisker p95) and GPU cost per 1,000 successful documents, "
            "by specialist and posture, on log scales; † (hatched) marks the optimized Experiment 4 merger cell.",
        },
    ]
    if cards.get("s39-1l4-n50") and cards.get("s37-2l4-n50"):
        specs.append(
            {
                "key": "cmp-matched",
                "path": "figures/cmp-matched.png",
                "section": "comparison",
                "caption": "Matched-sample check: each point is one document scored under Experiment 2 (1×L4 C8) and "
                "Experiment 3 (2×L4 C32). Points on the diagonal mean the posture did not change the output's score.",
            }
        )
    if any((c.get("tokens") or {}).get("split") for p in present for c in cards[p.key].values()):
        specs.append(
            {
                "key": "cmp-tokens",
                "path": "figures/cmp-tokens.png",
                "section": "comparison",
                "caption": "Where the tokens go, per document: instructions and template (resent on every model "
                "call), document text, and output. Left: share of each document's tokens; right: total tokens "
                "per document on a log scale. Instruction tokens are fitted per run across documents of "
                "different lengths (see *Token composition*).",
            }
        )
    if (cards.get("s37-2l4-n50") or {}).get("merger_agreement") and (cards.get("s40-2l4") or {}).get(
        "merger_agreement"
    ):
        specs.append(
            {
                "key": "cmp-merger-dagger",
                "path": "figures/cmp-merger-dagger.png",
                "section": "comparison",
                "caption": "Merger † effect on the same agreements: per-agreement MAUD accuracy under Experiment 3 "
                "(frozen settings) and Experiment 4 † (optimized settings). Points above the diagonal improved.",
            }
        )
    for p in present:
        specs.append(
            {
                "key": f"posture-{p.key}",
                "path": f"{p.shape_dir}/figures/{p.study}-{p.replicas}xL4-C{p.concurrency}-n{p.n}.png",
                "section": "posture",
                "caption": f"{p.exp_label} · {p.label}: per-document score and latency distributions, cost per "
                "1,000 successful documents, and token mix by specialist.",
            }
        )
    return specs


# ── drawing ──────────────────────────────────────────────────────────────────


def _style(plt) -> None:
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.color": "#e5e5e5",
            "grid.linewidth": 0.6,
            "axes.axisbelow": True,
            "legend.frameon": False,
            "savefig.dpi": 160,
        }
    )


def _save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Strip the matplotlib version stamp so re-renders of unchanged data are byte-stable.
    fig.savefig(path, bbox_inches="tight", metadata={"Software": None}, facecolor="white")


DAGGER = {("s40-2l4", "merger_agreement")}  # optimized merger cell (Experiment 4 †)
DAGGER_NOTE = (
    "† (hatched bar) Experiment 4 merger with optimized settings (whole agreement read in chunks, MAUD v1 prompt, Qwen3 sampling, "
    "6,144-token cap with one re-sample); same 50 agreements as Experiment 3."
)


def _posture_name(p) -> str:
    suffix = " (merger † n=50)" if p.key == "s40-2l4" else ""
    return f"{p.exp_label} · {p.replicas}×L4 C{p.concurrency} · n={p.n}{suffix}"


def _legend_handles(postures):
    from matplotlib.patches import Patch

    return [Patch(facecolor=COLORS[p.key], label=_posture_name(p)) for p in postures]


def _footer(fig, present, *, dagger: bool, extra: str = "") -> None:
    """Shared legend row and footnote under a figure; nothing overlaps the axes."""
    handles = _legend_handles(present)
    ncol = 2 if len(handles) == 4 else min(len(handles), 3)
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=ncol,
               fontsize=8, handlelength=1.4, columnspacing=2.0)
    notes = [n for n in (extra, DAGGER_NOTE if dagger and any(p.key == "s40-2l4" for p in present) else "") if n]
    if notes:
        rows = -(-len(handles) // ncol)
        fig.text(0.5, -0.045 - 0.05 * rows, "\n".join(notes), ha="center", va="top", fontsize=7, color="#555555")


def _bar_note(ax, x, y, text, *, color="#333333") -> None:
    """A short label just above a bar or its whisker, offset in points so it works on log axes."""
    ax.annotate(text, (x, y), xytext=(0, 2), textcoords="offset points", ha="center", va="bottom",
                fontsize=7, color=color, annotation_clip=False)


def _grouped(ax, present, cards, value, *, err=None, errors_mark=False):
    """Grouped bars: one group per specialist, one bar per posture; † cells hatched."""
    width = 0.8 / max(len(present), 1)
    for i, p in enumerate(present):
        for j, folder in enumerate(_ORDER):
            card = cards[p.key].get(folder)
            if not card:
                continue
            x = j - 0.4 + width * (i + 0.5)
            v = value(card)
            top = v
            kw = {}
            if err:
                hi = err(card)
                if hi:
                    kw = {"yerr": [[0], [max(hi - v, 0)]], "capsize": 2, "error_kw": {"lw": 0.8, "color": "#333333"}}
                    top = max(hi, v)
            dagger = (p.key, folder) in DAGGER
            ax.bar(x, v, width * 0.9, color=COLORS[p.key], hatch="///" if dagger else None,
                   edgecolor="white", linewidth=0.4, **kw)
            marks = []
            if dagger:
                marks.append("†")
            n_err = card["quality"]["errors"] if errors_mark else 0
            if n_err:
                marks.append(f"×{n_err}")
            if marks:
                _bar_note(ax, x, top, " ".join(marks), color="#b00020" if n_err else "#222222")
    ax.set_xticks(range(len(_ORDER)), [_SHORT[f] for f in _ORDER])
    ax.tick_params(axis="x", length=0)


def _pooled_bars(ax, present, pooled, key, fmt):
    xs = range(len(present))
    for x, p in zip(xs, present):
        v = pooled[p.key][key] or 0
        dagger = p.key == "s40-2l4"
        ax.bar(x, v, 0.65, color=COLORS[p.key], hatch="///" if dagger else None, edgecolor="white", linewidth=0.4)
        _bar_note(ax, x, v, fmt(v) + (" †" if dagger else ""))
    ax.set_xticks([])
    ax.margins(y=0.18)


def _fig_efficiency(plt, present, pooled, path):
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.2))
    _pooled_bars(axes[0], present, pooled, "usd_per_kdoc", lambda v: f"${v:.2f}")
    axes[0].set_title("GPU $ per 1,000 documents")
    axes[0].yaxis.set_major_formatter(lambda v, _: f"${v:.2f}")
    _pooled_bars(axes[1], present, pooled, "tps_per_gpu", lambda v: f"{v:,.0f}")
    axes[1].set_title("Tokens per second per GPU")
    _pooled_bars(axes[2], present, pooled, "docs_per_minute", lambda v: f"{v:.1f}")
    axes[2].set_title("Documents per minute")
    fig.suptitle("Serving efficiency, pooled across the five specialists (lower cost, higher throughput is better)",
                 fontweight="bold", fontsize=10)
    fig.tight_layout()
    _footer(fig, present, dagger=True,
            extra="The Experiment 4 bars include the † merger cell, which dominates its busy time; "
                  "see the scale-check table for the like-for-like comparison.")
    _save(fig, path)
    plt.close(fig)


def _primary(card) -> float:
    clause = card["quality"].get("clause") or {}
    if clause.get("kind") == "maud":
        return float(clause.get("accuracy") or 0.0)
    return float(card["quality"]["overall_mean"] or 0.0)


def _fig_quality(plt, present, cards, path):
    fig, ax = plt.subplots(figsize=(10.5, 3.6))
    _grouped(ax, present, cards, _primary, errors_mark=True)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Primary score (0–1)")
    ax.set_title("Primary quality score by specialist and posture")
    fig.tight_layout()
    _footer(fig, present, dagger=True,
            extra="Field score for insurance claims, corporate records and correspondence; CUAD clause F1 for "
                  "contracts; MAUD accuracy for merger. ×N = failed documents.")
    _save(fig, path)
    plt.close(fig)


def _fig_latency_cost(plt, present, cards, path):
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.6))
    _grouped(axes[0], present, cards, lambda c: c["latency"]["p50"], err=lambda c: c["latency"]["p95"])
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Seconds per document (log scale)")
    axes[0].set_title("Latency per document (bar p50, whisker p95)")
    _grouped(axes[1], present, cards, lambda c: c["cost"]["usd_per_ok_document"] * 1000)
    axes[1].set_yscale("log")
    axes[1].yaxis.set_major_formatter(lambda v, _: f"${v:g}")
    axes[1].set_ylabel("GPU $ (log scale)")
    axes[1].set_title("GPU cost per 1,000 successful documents")
    for ax in axes:
        ax.tick_params(axis="x", labelsize=8)
    fig.tight_layout()
    _footer(fig, present, dagger=True)
    _save(fig, path)
    plt.close(fig)


def _fig_matched(plt, cards, path):
    a, b = cards["s39-1l4-n50"], cards["s37-2l4-n50"]
    folders = [f for f in _ORDER if f in a and f in b]
    fig, axes = plt.subplots(1, len(folders), figsize=(2.2 * len(folders), 2.6), squeeze=False)
    total = 0
    for ax, folder in zip(axes[0], folders):
        sa = {d["item_id"]: d["score"] for d in a[folder]["documents"]}
        sb = {d["item_id"]: d["score"] for d in b[folder]["documents"]}
        ids = [i for i in sa if i in sb and sa[i] is not None and sb[i] is not None]
        xs, ys = [sa[i] for i in ids], [sb[i] for i in ids]
        ax.plot([0, 1], [0, 1], color="#bbbbbb", lw=0.8, zorder=1)
        ax.scatter(xs, ys, s=12, alpha=0.75, color=COLORS["s37-2l4-n50"], zorder=2)
        same = sum(abs(x - y) < 1e-9 for x, y in zip(xs, ys))
        mad = sum(abs(x - y) for x, y in zip(xs, ys)) / max(len(ids), 1)
        total += len(ids)
        ax.set_title(_LABEL[folder], fontsize=9)
        ax.text(0.04, 0.96, f"{same}/{len(ids)} identical\nmean |Δ| {mad:.3f}", transform=ax.transAxes,
                va="top", fontsize=7)
        ax.set_xlim(-0.03, 1.03)
        ax.set_ylim(-0.03, 1.03)
        ax.set_xticks([0, 0.5, 1])
        ax.set_yticks([0, 0.5, 1])
        ax.set_aspect("equal")
        ax.grid(True, axis="both")
    fig.supxlabel("Score under Experiment 2 · 1×L4 C8", fontsize=8)
    fig.supylabel("Score under Experiment 3 · 2×L4 C32", fontsize=8)
    fig.suptitle(f"Same documents under both postures ({total} scored pairs); points on the diagonal are unchanged",
                 fontweight="bold", fontsize=10)
    fig.tight_layout()
    _save(fig, path)
    plt.close(fig)


def _fig_merger_dagger(plt, cards, path):
    a = cards["s37-2l4-n50"]["merger_agreement"]
    b = cards["s40-2l4"]["merger_agreement"]
    sa = {d["item_id"]: d["score"] for d in a["documents"] if d["ok"]}
    sb = {d["item_id"]: d["score"] for d in b["documents"] if d["ok"]}
    ids = [i for i in sb if i in sa and sa[i] is not None and sb[i] is not None]
    xs, ys = [sa[i] for i in ids], [sb[i] for i in ids]
    fig, ax = plt.subplots(figsize=(4.6, 4.6))
    hi = max(xs + ys + [0.1]) * 1.1
    ax.plot([0, hi], [0, hi], color="#bbbbbb", lw=0.8, zorder=1)
    ax.scatter(xs, ys, s=18, alpha=0.75, color=COLORS["s40-2l4"], zorder=2)
    better = sum(y > x for x, y in zip(xs, ys))
    worse = sum(y < x for x, y in zip(xs, ys))
    ax.text(0.04, 0.96, f"{better} better · {worse} worse\nof {len(ids)} agreements", transform=ax.transAxes,
            va="top", fontsize=8)
    ax.set_xlim(-0.01, hi)
    ax.set_ylim(-0.01, hi)
    ax.set_aspect("equal")
    ax.grid(True, axis="both")
    ax.set_xlabel("Experiment 3 · 2×L4 (frozen settings)")
    ax.set_ylabel("Experiment 4 † (optimized settings)")
    ax.set_title("Merger: MAUD accuracy per agreement")
    fig.tight_layout()
    _save(fig, path)
    plt.close(fig)


def _split(card) -> dict[str, float] | None:
    split = (card.get("tokens") or {}).get("split")
    return dict(split["per_document"]) if split else None


def _token_share_bars(ax, rows, *, label_min=0.07):
    """Horizontal 100% stacked bars, one per row label; segment shares labeled when wide enough."""
    ys = range(len(rows))
    for y, (_, per) in zip(ys, rows):
        total = sum(per[k] for k, _, _ in TOKEN_PARTS) or 1.0
        left = 0.0
        for key, _, color in TOKEN_PARTS:
            share = per[key] / total
            ax.barh(y, share, 0.62, left=left, color=color, edgecolor="white", linewidth=1.5)
            if share >= label_min:
                ax.text(left + share / 2, y, f"{share:.0%}", ha="center", va="center", fontsize=7.5, color="white",
                        fontweight="bold")
            left += share
    ax.set_yticks(list(ys), [label for label, _ in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.grid(False)
    ax.tick_params(axis="y", length=0)


def _token_rows(cards) -> list[tuple[str, dict[str, float]]]:
    """SAND-40 for the four unchanged classes, then merger frozen (SAND-37 2×L4) and merger †."""
    rows: list[tuple[str, dict[str, float]]] = []
    s40, s37 = cards.get("s40-2l4") or {}, cards.get("s37-2l4-n50") or {}
    for folder in _ORDER:
        if folder == "merger_agreement":
            continue
        card = s40.get(folder) or s37.get(folder)
        per = _split(card) if card else None
        if per:
            rows.append((_LABEL[folder], per))
    for label, card in (("Merger agreements (frozen)", s37.get("merger_agreement")),
                        ("Merger agreements †", s40.get("merger_agreement"))):
        per = _split(card) if card else None
        if per:
            rows.append((label, per))
    return rows


def _fig_tokens(plt, cards, path):
    from matplotlib.patches import Patch

    rows = _token_rows(cards)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 0.48 * len(rows) + 1.6), gridspec_kw={"width_ratios": [1.7, 1]})
    _token_share_bars(axes[0], rows)
    axes[0].set_title("Share of tokens per document")
    ys = range(len(rows))
    totals = [sum(per[k] for k, _, _ in TOKEN_PARTS) for _, per in rows]
    axes[1].barh(list(ys), totals, 0.62, color="#8a8a85")
    for y, t in zip(ys, totals):
        axes[1].annotate(f"{t / 1000:.1f}K", (t, y), xytext=(3, 0), textcoords="offset points", va="center",
                         fontsize=7.5, color="#333333")
    axes[1].set_xscale("log")
    axes[1].set_yticks(list(ys), [""] * len(rows))
    axes[1].invert_yaxis()
    axes[1].xaxis.set_major_formatter(lambda v, _: f"{v / 1000:g}K")
    axes[1].set_title("Total tokens per document (log scale)")
    axes[1].grid(True, axis="x")
    axes[1].grid(False, axis="y")
    axes[1].tick_params(axis="y", length=0)
    axes[1].margins(x=0.2)
    fig.suptitle("Where the tokens go: instructions are resent on every call", fontweight="bold", fontsize=10)
    fig.tight_layout()
    fig.legend(handles=[Patch(facecolor=c, label=l) for _, l, c in TOKEN_PARTS], loc="upper center",
               bbox_to_anchor=(0.5, 0.0), ncol=3, fontsize=8)
    fig.text(0.5, -0.07, "Experiment 4 cells for the four unchanged specialists; merger shown frozen (Experiment 3 · 2×L4, "
             "head + tail 30,000 chars) and † (whole agreement in ~8 chunk calls).",
             ha="center", va="top", fontsize=7, color="#555555")
    _save(fig, path)
    plt.close(fig)


def _fig_posture(plt, p, cards, path):
    folders = [f for f in _ORDER if f in cards]
    labels = [_SHORT[f] + (" †" if (p.key, f) in DAGGER else "") for f in folders]
    color = COLORS[p.key]
    fig, axes = plt.subplots(2, 2, figsize=(12, 6.8))

    scores = [[d["score"] for d in cards[f]["documents"] if d["score"] is not None] for f in folders]
    bp = axes[0][0].boxplot(scores, tick_labels=labels, patch_artist=True, widths=0.55,
                            medianprops={"color": "black"}, flierprops={"markersize": 3})
    for box, f in zip(bp["boxes"], folders):
        box.set(facecolor=color, alpha=0.75, hatch="///" if (p.key, f) in DAGGER else None)
    axes[0][0].set_ylim(0, 1)
    axes[0][0].set_ylabel("Score (0–1)")
    axes[0][0].set_title("Per-document score (merger: MAUD accuracy)")

    lat = [[d["latency_seconds"] for d in cards[f]["documents"] if d.get("latency_seconds")] for f in folders]
    bp = axes[0][1].boxplot(lat, tick_labels=labels, patch_artist=True, widths=0.55,
                            medianprops={"color": "black"}, flierprops={"markersize": 3})
    for box, f in zip(bp["boxes"], folders):
        box.set(facecolor=color, alpha=0.75, hatch="///" if (p.key, f) in DAGGER else None)
    axes[0][1].set_yscale("log")
    axes[0][1].set_ylabel("Seconds (log scale)")
    axes[0][1].set_title("Per-document latency")

    xs = range(len(folders))
    cost = [cards[f]["cost"]["usd_per_ok_document"] * 1000 for f in folders]
    for x, f, v in zip(xs, folders, cost):
        axes[1][0].bar(x, v, 0.6, color=color, hatch="///" if (p.key, f) in DAGGER else None,
                       edgecolor="white", linewidth=0.4)
        _bar_note(axes[1][0], x, v, f"${v:.2f}")
    ok_labels = [f"{lab}\n{cards[f]['quality']['ok']}/{cards[f]['n']} ok" for lab, f in zip(labels, folders)]
    axes[1][0].set_xticks(list(xs), ok_labels)
    axes[1][0].set_yscale("log")
    axes[1][0].yaxis.set_major_formatter(lambda v, _: f"${v:g}")
    axes[1][0].set_ylabel("GPU $ (log scale)")
    axes[1][0].set_title("GPU cost per 1,000 successful documents")
    axes[1][0].margins(y=0.15)

    rows = [(lab.replace("\n", " "), _split(cards[f])) for lab, f in zip(labels, folders) if _split(cards[f])]
    if rows:
        _token_share_bars(axes[1][1], rows)
        for y, (_, per) in enumerate(rows):
            total = sum(per[k] for k, _, _ in TOKEN_PARTS)
            axes[1][1].annotate(f"{total / 1000:.1f}K tokens", (1.0, y), xytext=(4, 0), textcoords="offset points",
                                va="center", fontsize=7, color="#333333", annotation_clip=False)
        from matplotlib.patches import Patch

        axes[1][1].legend(handles=[Patch(facecolor=c, label=l) for _, l, c in TOKEN_PARTS], fontsize=7,
                          loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3, frameon=False)
    axes[1][1].set_title("Tokens per document: instructions, document, output")

    for row in axes:
        for ax in row:
            ax.tick_params(axis="x", labelsize=7.5, length=0)
    fig.suptitle(f"{p.exp_label} · {p.replicas}×L4 C{p.concurrency} · n={p.n}: posture dashboard", fontweight="bold")
    fig.tight_layout()
    if any((p.key, f) in DAGGER for f in folders):
        fig.text(0.5, -0.01, DAGGER_NOTE, ha="center", va="top", fontsize=7, color="#555555")
    _save(fig, path)
    plt.close(fig)


def write_figures(data: Mapping[str, Any], repo: Path | None = None) -> list[Path]:
    """Render every figure in ``figure_specs(data)``; returns the written paths."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from mailroom_sandbox.job.grid_master import _pooled
    from mailroom_sandbox.paths import repo_root

    _style(plt)
    root = (repo or repo_root()) / ROOT_REL
    cards = data["cards"]
    present = [p for p in _postures() if cards[p.key]]
    pooled = {p.key: _pooled(cards[p.key], p.replicas) for p in present}
    for q in pooled.values():
        q["usd_per_kdoc"] = (q["usd_per_document"] or 0) * 1000
    by_key = {p.key: p for p in present}
    written: list[Path] = []
    for spec in figure_specs(data):
        path = root / spec["path"]
        key = spec["key"]
        if key == "cmp-efficiency":
            _fig_efficiency(plt, present, pooled, path)
        elif key == "cmp-quality":
            _fig_quality(plt, present, cards, path)
        elif key == "cmp-latency-cost":
            _fig_latency_cost(plt, present, cards, path)
        elif key == "cmp-matched":
            _fig_matched(plt, cards, path)
        elif key == "cmp-tokens":
            _fig_tokens(plt, cards, path)
        elif key == "cmp-merger-dagger":
            _fig_merger_dagger(plt, cards, path)
        elif key.startswith("posture-"):
            p = by_key[key.removeprefix("posture-")]
            _fig_posture(plt, p, cards[p.key], path)
        written.append(path)
    return written
