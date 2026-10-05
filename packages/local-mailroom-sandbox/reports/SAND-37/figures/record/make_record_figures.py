"""L4 cost record figures (one chart per PNG), built from the committed grid cards.

Run from the repo root: python reports/SAND-37/figures/record/make_record_figures.py reports/SAND-37/figures/record
"""
import glob
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

ROOT = "reports/SAND-37"
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

# Two validated reference slots, keyed by GPU count: orange = 1× L4, blue = 2× L4.
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
C_1L4_50 = "#eb6834"   # Experiment 2: 1× L4 C8 n=50
C_2L4_50 = "#2a78d6"   # Experiment 3: 2× L4 C32 n=50
C_2L4_100 = "#2a78d6"  # Experiment 4: 2× L4 C32 n=100 — one color per GPU count
REF = "#898781"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "text.color": INK, "axes.labelcolor": INK2,
    "axes.edgecolor": AXIS, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
    "xtick.color": MUTED, "ytick.color": INK, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.titlecolor": INK, "grid.color": GRID, "grid.linewidth": 0.6,
    "savefig.facecolor": SURFACE, "savefig.dpi": 200,
})
import matplotlib.text as _mt
_orig_init = _mt.Text.__init__
def _init(self, *a, **k):
    k.setdefault("parse_math", False)
    _orig_init(self, *a, **k)
_mt.Text.__init__ = _init

CLASSES = [("insurance", "Insurance Claims"), ("contracts", "Contracts"),
           ("corporate", "Corporate Records"), ("correspondence", "Correspondence"),
           ("merger", "Merger Agreements")]

cards = {}
for f in glob.glob(f"{ROOT}/*L4/*/*.card.json"):
    d = json.load(open(f))
    cards[d["run_id"]] = d


def card(prefix, gpus, key):
    hits = [d for r, d in cards.items() if r.startswith(prefix) and gpus in r and key in r]
    assert len(hits) == 1, (prefix, gpus, key, [h["run_id"] for h in hits])
    return hits[0]


def pct(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def metrics(d):
    q, c, reps = d["quality"], d["cost"], d["engine_telemetry"]["replicas"]
    lats = [x["latency_seconds"] for x in d["documents"] if x["ok"]]
    maud = (q.get("clause") or {}).get("kind") == "maud"
    req = sum(r["requests"] for r in reps)
    return {
        "ok": q["ok"], "n": d["n"],
        "score": q["clause"]["accuracy"] if maud else q["overall_mean"], "sd": q["overall_sd"],
        "cost_1k": c["usd_per_ok_document"] * 1000, "dpm": d["throughput"]["documents_per_minute"],
        "p50": d["latency"]["p50"], "p95": d["latency"]["p95"], "p99": pct(lats, 0.99),
        "ttft": sum(r["requests"] * r["ttft_mean_seconds"] for r in reps) / req,
        "occ": d["concurrency"]["occupancy"], "busy": c["busy_gpu_usd"],
        "wall": d["time"]["wall_seconds"], "tok": d["tokens"]["total"], "gpus": len(reps),
    }


S39 = {k: metrics(card("grid-50", "1l4", k)) for k, _ in CLASSES}
S37_2 = {k: metrics(card("grid-50", "2l4", k)) for k, _ in CLASSES}
S40 = {k: metrics(card("sand40", "2l4", k)) for k, _ in CLASSES}

LABELS = [lab for _, lab in CLASSES]
KEYS = [k for k, _ in CLASSES]
SCORE_METRIC = {"contracts": "CUAD F1", "merger": "MAUD acc."}


def fmt_num(v):
    if v >= 100:
        return f"{v:,.0f}"
    if v >= 10:
        return f"{v:.1f}"
    if v >= 1:
        return f"{v:.2f}"
    return f"{v:.2f}"


def style(ax, log=False):
    ax.set_axisbelow(True)
    ax.grid(axis="x", which="major")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0, labelsize=8)
    if log:
        ax.set_xscale("log")
        ax.xaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))


def dots(ax, vals, color, label_fmt=fmt_num, log=False, xmax=None):
    ys = range(len(vals))[::-1]
    ax.scatter(vals, ys, s=46, color=color, edgecolor=SURFACE, linewidth=1.5, zorder=3)
    for v, y in zip(vals, ys):
        ax.annotate(label_fmt(v), (v, y), xytext=(7, 0), textcoords="offset points",
                    va="center", fontsize=8, color=INK2)
    ax.set_yticks(list(ys), LABELS)
    ax.set_ylim(-0.6, len(vals) - 0.4)
    style(ax, log)


from matplotlib.lines import Line2D

SRC = "Source: per-run grid cards (sandbox.grid-card/v1)."
DAGGER = "† Merger runs optimized settings on 50 agreements (chunked, 7.9 calls/agreement); not a serving comparison."


def new_fig(title, subtitle, note, legend=None, rows=5):
    H = 0.55 * rows + 2.3 + (0.3 if legend else 0)
    fig, ax = plt.subplots(figsize=(8, H))
    fig.subplots_adjust(left=0.25, right=0.95, top=1 - (1.25 if legend else 0.95) / H, bottom=0.95 / H)
    fig.text(0.02, 0.985, title, fontsize=13, fontweight="bold", va="top")
    fig.text(0.02, 0.985 - 0.34 / H, subtitle, fontsize=9, color=INK2, va="top")
    fig.text(0.02, 0.015, note, fontsize=7.5, color=MUTED, va="bottom")
    if legend:
        fig.legend(handles=[Line2D([], [], marker="o", ls="", ms=7, color=c, label=l) for c, l in legend],
                   loc="upper left", bbox_to_anchor=(0.012, 0.985 - 0.58 / H), ncol=len(legend), frameon=False,
                   fontsize=9, handletextpad=0.3, columnspacing=1.6)
    return fig, ax


# The report keeps one or two charts per table; the rest are drawn but not written.
KEEP = {
    "1xL4-C8-n50-cost", "1xL4-C8-n50-latency",        # 1x L4 score/cost table, latency/engine table
    "2xL4-C32-n100-cost", "2xL4-C32-n100-latency",    # 2x L4 score/cost table, latency/engine table
    "2xL4-C32-n50-cost", "2xL4-C32-n50-latency",      # Experiment 3, for the 2x L4 suite card
    "1x-vs-2xL4-cost", "1x-vs-2xL4-throughput",       # single vs double L4 table
    "cost-vs-score", "merger-frozen-vs-dagger", "2xL4-n50-vs-n100-cost",  # findings charts
}


def save(fig, name):
    if name in KEEP:
        fig.savefig(f"{OUT}/{name}.png")
    plt.close(fig)


def posture_set(data, color, tag, posture, dagger=False):
    labels = [lab + ("†" if dagger and k == "merger" else "") for k, lab in CLASSES]
    v = lambda m: [data[k][m] for k in KEYS]
    ys = list(range(len(KEYS)))[::-1]
    extra = ("\n" + DAGGER) if dagger else ""

    def finish(ax):
        ax.set_yticks(ys, labels)

    fig, ax = new_fig(f"Cost per 1,000 ok documents — {posture}", "Busy GPU $ ÷ ok docs × 1,000 at $0.80/GPU-hr (log scale)", SRC + extra)
    dots(ax, v("cost_1k"), color, lambda x: f"${x:.2f}", log=True); ax.set_xlim(0.06, 60); finish(ax)
    save(fig, f"{tag}-cost")

    fig, ax = new_fig(f"Throughput — {posture}", "Documents per minute (log scale)", SRC + extra)
    dots(ax, v("dpm"), color, log=True); ax.set_xlim(1, 900); finish(ax)
    save(fig, f"{tag}-throughput")

    fig, ax = new_fig(f"Score ± sd — {posture}",
                      "Field extraction score (insurance, corporate, correspondence) · CUAD F1 (contracts) · MAUD accuracy (merger)",
                      SRC + " Scores on different metrics are not comparable across classes." + extra)
    sc, sd = v("score"), v("sd")
    ax.errorbar(sc, ys, xerr=sd, fmt="none", ecolor=AXIS, elinewidth=1.4, capsize=0, zorder=2)
    dots(ax, sc, color, lambda x: "")
    for x, e, y in zip(sc, sd, ys):
        ax.annotate(f"{x:.3f}", (min(x + e, 1), y), xytext=(6, 0), textcoords="offset points", va="center", fontsize=8, color=INK2)
    ax.set_xlim(0, 1.1); ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0]); finish(ax)
    save(fig, f"{tag}-score")

    fig, ax = new_fig(f"Latency p50 → p99 — {posture}", "End-to-end seconds over ok docs (log scale)  ·  ● p50   | p95   ○ p99",
                      SRC + " p99 computed from per-document records." + extra)
    p50, p95, p99 = v("p50"), v("p95"), v("p99")
    ax.hlines(ys, p50, p99, color=AXIS, linewidth=2.2, zorder=2)
    ax.scatter(p95, ys, s=22, marker="|", color=INK2, linewidth=1.5, zorder=3)
    ax.scatter(p99, ys, s=26, marker="o", facecolor=SURFACE, edgecolor=INK2, linewidth=1.2, zorder=3)
    dots(ax, p50, color, lambda x: "", log=True)
    for a, b, c95, y in zip(p50, p99, p95, ys):
        far = b > 600
        ax.annotate(f"p50 {fmt_num(a)} · p95 {fmt_num(c95)} · p99 {fmt_num(b)} s", (a if far else b, y),
                    xytext=(-8 if far else 7, 0), textcoords="offset points", va="center",
                    ha="right" if far else "left", fontsize=7.5, color=INK2)
    ax.set_xlim(4, 5000); ax.set_xticks([5, 10, 30, 100, 300, 1000, 3000]); finish(ax)
    save(fig, f"{tag}-latency")

    fig, ax = new_fig(f"Mean time to first token — {posture}", "vLLM /metrics, request-weighted over replicas (s)", SRC + extra)
    dots(ax, v("ttft"), color, lambda x: f"{x:.2f} s"); ax.set_xlim(0, 14); finish(ax)
    save(fig, f"{tag}-ttft")

    fig, ax = new_fig(f"Client-slot occupancy — {posture}", "Σ per-doc latency ÷ (wall × client concurrency); dashed line = 1.0",
                      SRC + " Values above 1.0 suggest per-doc latency includes pre-dispatch wait; not a GPU utilization figure." + extra)
    ax.axvline(1.0, color=REF, linewidth=1, linestyle=(0, (3, 2)), zorder=1)
    dots(ax, v("occ"), color, lambda x: f"{x:.2f}"); ax.set_xlim(0, 2); finish(ax)
    save(fig, f"{tag}-occupancy")


posture_set(S39, C_1L4_50, "1xL4-C8-n50", "Experiment 2 (1× L4 · C=8 · n=50)")
posture_set(S40, C_2L4_100, "2xL4-C32-n100", "Experiment 4 (2× L4 · C=32 · n=100)", dagger=True)
posture_set(S37_2, C_2L4_50, "2xL4-C32-n50", "Experiment 3 (2× L4 · C=32 · n=50)")


def pooled(data):
    busy = sum(m["busy"] for m in data.values()); ok = sum(m["ok"] for m in data.values())
    n = sum(m["n"] for m in data.values()); wall = sum(m["wall"] for m in data.values())
    # Pooled cost uses the master card's basis: busy GPU $ per attempted document.
    return {"cost_1k": busy / n * 1000, "dpm": n / (wall / 60)}


P1, P2 = pooled(S39), pooled(S37_2)
ROWS = LABELS + ["Pooled (all docs)"]
LEG = [(C_1L4_50, "Exp. 2 · 1× L4 C8"), (C_2L4_50, "Exp. 3 · 2× L4 C32")]
CMP = "Same 250 documents: Experiment 2 (1× L4 · C=8 · n=50) → Experiment 3 (2× L4 · C=32 · n=50)"


def dumbbell(ax, a, b, labels, fmt, log=False, delta=True):
    ys = list(range(len(a)))[::-1]
    ax.hlines(ys, a, b, color=AXIS, linewidth=2.2, zorder=1)
    ax.scatter(a, ys, s=46, color=C_1L4_50, edgecolor=SURFACE, linewidth=1.5, zorder=3)
    ax.scatter(b, ys, s=46, color=C_2L4_50, edgecolor=SURFACE, linewidth=1.5, zorder=3)
    for x1, x2, y in zip(a, b, ys):
        txt = f"{fmt(x1)} → {fmt(x2)}"
        if delta:
            dv = (x2 / x1 - 1) * 100
            txt += f"  ({dv:+.1f}%)" if abs(dv) < 1 else f"  ({dv:+.0f}%)"
        ax.annotate(txt, (max(x1, x2), y), xytext=(8, 0), textcoords="offset points", va="center", fontsize=8, color=INK2)
    ax.set_yticks(ys, labels); ax.set_ylim(-0.6, len(a) - 0.4)
    style(ax, log)


g = lambda d, m: [d[k][m] for k in KEYS]
fig, ax = new_fig("Cost per 1,000 ok documents — 1× vs 2× L4", CMP + " (log scale)",
                  SRC + " Classes: per ok doc. Pooled: Σ busy GPU $ ÷ Σ attempted docs (master-card basis).", LEG, rows=6)
dumbbell(ax, g(S39, "cost_1k") + [P1["cost_1k"]], g(S37_2, "cost_1k") + [P2["cost_1k"]], ROWS, lambda x: f"${x:.2f}", log=True)
ax.set_xlim(0.08, 60)
save(fig, "1x-vs-2xL4-cost")

fig, ax = new_fig("Throughput — 1× vs 2× L4", CMP + " (docs/min, log scale)", SRC, LEG, rows=6)
dumbbell(ax, g(S39, "dpm") + [P1["dpm"]], g(S37_2, "dpm") + [P2["dpm"]], ROWS, fmt_num, log=True)
ax.set_xlim(2, 3000); ax.set_xticks([2, 5, 10, 30, 100, 300, 1000])
save(fig, "1x-vs-2xL4-throughput")

fig, ax = new_fig("Per-GPU scaling — 1× → 2× L4", "(2× docs/min ÷ 1× docs/min) ÷ 2; dashed line = 100% (linear)",
                  SRC + " Scaling above 100% is confounded with the client-concurrency change (8 → 32).", rows=6)
scal = [(S37_2[k]["dpm"] / S39[k]["dpm"]) / 2 * 100 for k in KEYS] + [(P2["dpm"] / P1["dpm"]) / 2 * 100]
ys = list(range(len(scal)))[::-1]
ax.barh(ys, scal, 0.56, color=C_2L4_50, edgecolor=SURFACE, linewidth=2)
ax.axvline(100, color=REF, linewidth=1, linestyle=(0, (3, 2)))
for v_, y in zip(scal, ys):
    ax.annotate(f"{v_:.0f}%", (v_, y), xytext=(5, 0), textcoords="offset points", va="center", fontsize=8, color=INK2)
ax.set_yticks(ys, ROWS); ax.set_ylim(-0.6, len(scal) - 0.4); ax.set_xlim(0, 200); style(ax)
save(fig, "1x-vs-2xL4-scaling")

fig, ax = new_fig("Latency p50 — 1× vs 2× L4", CMP + " (s, log scale)", SRC + " End-to-end over ok docs.", LEG)
dumbbell(ax, g(S39, "p50"), g(S37_2, "p50"), LABELS, lambda x: f"{x:.1f}", log=True)
ax.set_xlim(4, 1000); ax.set_xticks([5, 10, 30, 100, 300, 1000])
save(fig, "1x-vs-2xL4-latency-p50")

fig, ax = new_fig("Latency p95 — 1× vs 2× L4", CMP + " (s, log scale)", SRC + " End-to-end over ok docs.", LEG)
dumbbell(ax, g(S39, "p95"), g(S37_2, "p95"), LABELS, lambda x: f"{x:.1f}", log=True)
ax.set_xlim(8, 2000); ax.set_xticks([10, 30, 100, 300, 1000])
save(fig, "1x-vs-2xL4-latency-p95")

fig, ax = new_fig("Mean time to first token — 1× vs 2× L4", CMP + " (s)", SRC + " vLLM /metrics, request-weighted.", LEG)
dumbbell(ax, g(S39, "ttft"), g(S37_2, "ttft"), LABELS, lambda x: f"{x:.2f}", delta=False)
ax.set_xlim(0, 13)
save(fig, "1x-vs-2xL4-ttft")

fig, ax = new_fig("Score — 1× vs 2× L4", CMP,
                  SRC + " Field extraction (insurance, corporate, correspondence), CUAD F1 (contracts), MAUD accuracy (merger).", LEG)
dumbbell(ax, g(S39, "score"), g(S37_2, "score"), LABELS, lambda x: f"{x:.3f}", delta=False)
ax.set_xlim(0, 1.15); ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
save(fig, "1x-vs-2xL4-score")


# ---- Findings charts --------------------------------------------------------------------

# 1. Cost vs score, same 250 documents, 1× vs 2× L4.
fig, ax = new_fig("Cost vs score — same 250 documents",
                  "Cost per 1,000 ok docs (log) against score; each line joins one class on 1× and 2× L4",
                  SRC + "\nScore: field extraction (insurance, corporate, correspondence), CUAD F1 (contracts), MAUD accuracy (merger);"
                  "\nscores on different metrics are not comparable across classes.",
                  LEG, rows=7)
fig.subplots_adjust(left=0.1, bottom=0.17)
for k, lab in CLASSES:
    a, b = S39[k], S37_2[k]
    ax.plot([a["cost_1k"], b["cost_1k"]], [a["score"], b["score"]], color=AXIS, linewidth=1.6, zorder=1)
    ax.scatter(a["cost_1k"], a["score"], s=70, color=C_1L4_50, edgecolor=SURFACE, linewidth=1.8, zorder=3)
    ax.scatter(b["cost_1k"], b["score"], s=70, color=C_2L4_50, edgecolor=SURFACE, linewidth=1.8, zorder=3)
    x = max(a["cost_1k"], b["cost_1k"])
    y = (a["score"] + b["score"]) / 2
    ax.annotate(f"{lab}\n${a['cost_1k']:.2f} → ${b['cost_1k']:.2f} · {a['score']:.3f} → {b['score']:.3f}",
                (x, y), xytext=(10, 0), textcoords="offset points", va="center", fontsize=8, color=INK2)
style(ax, log=True)
ax.grid(axis="y")
ax.spines["left"].set_visible(True)
ax.tick_params(axis="y", labelsize=8, colors=MUTED)
ax.set_xlim(0.08, 40)
ax.set_ylim(-0.02, 0.8)
ax.set_xlabel("Cost per 1,000 ok documents ($, log scale)", fontsize=8.5)
ax.set_ylabel("Score", fontsize=8.5)
ax.text(0.09, 0.77, "cheaper, better ↖", fontsize=7.5, color=MUTED, va="top")
save(fig, "cost-vs-score")

# 2. Merger: frozen (Experiment 3) vs † (Experiment 4), same 50 agreements, indexed to frozen.
fz, dg = card("grid-50", "2l4", "merger"), card("sand40", "2l4", "merger")
mf, md = S37_2["merger"], S40["merger"]
cf, cd_ = fz["quality"]["clause"], dg["quality"]["clause"]
items = [
    ("MAUD accuracy", cf["accuracy"], cd_["accuracy"], lambda v: f"{v:.3f}"),
    ("Correct MAUD answers", cf["correct"], cd_["correct"], lambda v: f"{v:,.0f}"),
    ("Question coverage", cf["coverage"], cd_["coverage"], lambda v: f"{v:.0%}"),
    ("GPU $ per correct answer", mf["busy"] / cf["correct"], md["busy"] / cd_["correct"], lambda v: f"${v:.4f}"),
    ("GPU $ per ok agreement", fz["cost"]["usd_per_ok_document"], dg["cost"]["usd_per_ok_document"], lambda v: f"${v:.5f}"),
    ("Tokens per ok agreement", fz["tokens"]["per_document"], dg["tokens"]["per_document"], lambda v: f"{v:,.0f}"),
    ("Latency p50", mf["p50"], md["p50"], lambda v: f"{v:,.0f} s"),
]
fig, ax = new_fig("Merger agreements — frozen vs † settings",
                  "Same 50 agreements on 2× L4 C=32 · each bar is † ÷ frozen (dashed line = no change)",
                  SRC + " Frozen = Experiment 3 (46/50 ok); † = Experiment 4 (50/50 ok)."
                  "\n† = chunked whole agreement, maud_v1 prompt, 6,144-token cap, 1 length re-sample."
                  "\nSettings changed together, so the gain is not attributed to any one of them.",
                  rows=7)
fig.subplots_adjust(bottom=0.15)
ys = list(range(len(items)))[::-1]
ratios = [d / f for _, f, d, _ in items]
ax.barh(ys, ratios, 0.56, color=C_2L4_100, edgecolor=SURFACE, linewidth=2, zorder=2)
ax.axvline(1, color=REF, linewidth=1, linestyle=(0, (3, 2)), zorder=3)
for (name, f, d, fm), r, y in zip(items, ratios, ys):
    ax.annotate(f"{r:.1f}×   ({fm(f)} → {fm(d)})", (r, y), xytext=(6, 0), textcoords="offset points",
                va="center", fontsize=8, color=INK2)
ax.set_yticks(ys, [i[0] for i in items])
ax.set_ylim(-0.6, len(items) - 0.4)
ax.set_xlim(0, 16)
style(ax)
ax.axhline(3.5, color=GRID, linewidth=1)
ax.text(15.8, 5, "quality", fontsize=7.5, color=MUTED, ha="right", va="center")
ax.text(15.8, 2, "cost & time", fontsize=7.5, color=MUTED, ha="right", va="center")
save(fig, "merger-frozen-vs-dagger")

# 3. Batch size on 2× L4: n=50 (Experiment 3) → n=100 (Experiment 4), four unchanged classes + pooled.
C_N50, C_N100 = "#86b6ef", "#2a78d6"   # ordinal steps of the 2× L4 blue
four = [k for k in KEYS if k != "merger"]
labs4 = [lab for k, lab in CLASSES if k != "merger"] + ["Pooled (4 classes, all docs)"]
pool = lambda d: sum(d[k]["busy"] for k in four) / sum(d[k]["n"] for k in four) * 1000  # master-card basis
a = [S37_2[k]["cost_1k"] for k in four] + [pool(S37_2)]
b = [S40[k]["cost_1k"] for k in four] + [pool(S40)]
fig, ax = new_fig("Batch size on 2× L4 — n=50 → n=100",
                  "Cost per 1,000 ok docs, Experiment 3 (n=50) → Experiment 4 (n=100), C=32 (log scale; merger excluded)",
                  SRC + " Classes: per ok doc. Pooled: Σ busy GPU $ ÷ Σ attempted docs (master-card basis)."
                  "\nContracts' idle share of wall time fell 49% → 32%.",
                  [(C_N50, "Exp. 3 · n=50"), (C_N100, "Exp. 4 · n=100")], rows=5)
ys = list(range(len(a)))[::-1]
ax.hlines(ys, a, b, color=AXIS, linewidth=2.2, zorder=1)
ax.scatter(a, ys, s=50, color=C_N50, edgecolor=SURFACE, linewidth=1.5, zorder=3)
ax.scatter(b, ys, s=50, color=C_N100, edgecolor=SURFACE, linewidth=1.5, zorder=3)
for x1, x2, y in zip(a, b, ys):
    dv = (x2 / x1 - 1) * 100
    ax.annotate(f"${x1:.2f} → ${x2:.2f}  ({dv:+.0f}%)", (max(x1, x2), y), xytext=(8, 0), textcoords="offset points",
                va="center", fontsize=8, color=INK2)
ax.set_yticks(ys, labs4)
ax.set_ylim(-0.6, len(a) - 0.4)
style(ax, log=True)
ax.set_xlim(0.08, 10)
save(fig, "2xL4-n50-vs-n100-cost")
