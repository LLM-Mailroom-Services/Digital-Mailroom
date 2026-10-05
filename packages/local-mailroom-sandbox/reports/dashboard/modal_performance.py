"""Modal specialist experiment visuals — drawn from committed run reports + serving exports.

Every number is read from ``hub_data.json`` (``runs``, ``fleet``) and
``reports/serving/SAND-32/sand032-*.serving.json``. No live Modal spend.

    python scripts/sand032/render_modal_performance.py
    python scripts/sand032/render_modal_performance.py --check
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASH = Path(__file__).resolve().parent
FIG_DIR = DASH / "figures" / "modal-performance"

ORDER = ["correspondence", "insurance_claim", "corporate_record", "contract", "merger_agreement"]
SPECIALIST_MARKERS = {
    "correspondence": "circle",
    "insurance_claim": "square",
    "corporate_record": "diamond",
    "contract": "square",
    "merger_agreement": "diamond",
}
HW_SLOTS = ["s1", "s2", "s3", "s4", "s5", "s6"]

# Canonical SAND-032 five-class sweep (2×L4 c32) + common hardware variants for the matrix.
MATRIX_RUNS = {
    ("correspondence", "1×L4 c8"): "sand032-s10-corr75-v2",
    ("correspondence", "2×L4 c32"): "sand032-s3-corr50",
    ("correspondence", "2×L4 c64"): "sand032-s9-corr100-bal",
    ("insurance_claim", "1×L4 c8"): "sand032-s10-insurance75-v2",
    ("insurance_claim", "2×L4 c32"): "sand032-s3-insurance50",
    ("insurance_claim", "2×L4 c64"): "sand032-s9-insurance50-bal",
    ("corporate_record", "1×L4 c8"): "sand032-s10-corporate75-v2",
    ("corporate_record", "2×L4 c32"): "sand032-s3-corporate50",
    ("corporate_record", "2×L4 c64"): "sand032-s9-corporate50-bal",
    ("contract", "2×L4 c32"): "sand032-s3-contracts50",
    ("contract", "2×L4 c64"): "sand032-s9-contracts50-bal",
    ("merger_agreement", "2×L4 c32"): "sand032-s3-merger50",
    ("merger_agreement", "2×L4 c32 MAUD"): "sand032-s5-merger50-maud",
}

CONCURRENCY_RUNS: dict[str, list[str]] = {
    "correspondence": [
        "sand032-l0-baseline", "sand032-l5-graphs", "sand032-s2a-corr100-1rep", "sand032-s2b-corr100-2rep",
        "sand032-s3-corr50", "sand032-s7-corr100-seqs32", "sand032-s9-corr100-bal",
    ],
    "insurance_claim": ["sand032-s3-insurance50", "sand032-s7-insurance50-seqs32", "sand032-s9-insurance50-bal"],
    "corporate_record": ["sand032-s3-corporate50", "sand032-s9-corporate50-bal"],
    "contract": ["sand032-s3-contracts50", "sand032-s9-contracts50-bal"],
    "merger_agreement": ["sand032-s3-merger50", "sand032-s5-merger50-maud"],
}

COST_STACK_RUNS = [
    "sand032-s3-corr50", "sand032-s3-insurance50", "sand032-s3-corporate50",
    "sand032-s3-contracts50", "sand032-s5-merger50-maud",
]

PREFIX_RUNS = COST_STACK_RUNS + ["sand032-s9-insurance50-bal"]

SAME_MODEL_CLASSES = ["correspondence", "insurance_claim", "corporate_record", "contract"]

REPLICA_LINE = re.compile(
    r"^- replica `([^`]*)`: requests Δ (\d+) \(cumulative \d+\), measured TTFT mean [\d.]+ s "
    r"\(vLLM histogram, cumulative\), prefix-cache hit ([\d.]+)%,", re.M)


def _score(run: dict) -> float:
    return float(run.get("headline", run.get("overall")))


def _label(D: dict, cls: str) -> str:
    return D["labels"][cls]


def _hw_label(fleet: dict) -> str:
    mi = fleet.get("max_inputs")
    extra = f" mi{mi}" if mi and mi * fleet["replicas"] != fleet["conc"] else ""
    return f"{fleet['replicas']}×L4 c{fleet['conc']}{extra}"


def _load_serving(rid: str) -> dict:
    serving_dir = ROOT / "reports" / "serving"
    matches = sorted(serving_dir.rglob(f"{rid}.serving.json"))
    if len(matches) != 1:
        raise FileNotFoundError(f"expected one serving export for {rid}, found {len(matches)}")
    return json.loads(matches[0].read_text())


def _cost_parts(rid: str, fleet: dict, rate: float) -> dict[str, float]:
    s = _load_serving(rid)
    n = max(int(s["n"]), 1)
    busy = fleet["busy_usd"] / n
    idle = float(s.get("idle_estimated_usd") or 0) / n
    cold = float(s.get("cold_boot_seconds") or fleet.get("cold_boot") or 0) * fleet["replicas"] * rate / 3600 / n
    boot = float(s.get("boot_estimated_usd") or 0) / n
    cold = max(cold, boot)
    return {"busy": busy, "idle": idle, "cold": cold}


def _matrix_cols() -> list[str]:
    return ["1×L4 c8", "2×L4 c32", "2×L4 c64", "2×L4 c32 MAUD"]


def _collect_matrix(D: dict) -> tuple[list[str], list[str], dict[tuple[str, str], float | None]]:
    rows = [_label(D, c) for c in ORDER]
    cols = _matrix_cols()
    cells: dict[tuple[str, str], float | None] = {}
    for cls in ORDER:
        for col in cols:
            rid = MATRIX_RUNS.get((cls, col))
            if not rid or rid not in D["runs"]:
                cells[(_label(D, cls), col)] = None
                continue
            cells[(_label(D, cls), col)] = _score(D["runs"][rid])
    return rows, cols, cells


def fig_score_grouped(D: dict, viz) -> str:
    rows, cols, cells = _collect_matrix(D)
    categories = [_label(D, c) for c in ORDER]
    series = []
    for i, col in enumerate(cols):
        vals = {cat: cells.get((cat, col)) for cat in categories}
        if not any(v is not None for v in vals.values()):
            continue
        series.append({"name": col, "cls": HW_SLOTS[i % len(HW_SLOTS)], "values": vals})
    return viz.grouped_vbar(
        "Specialist extraction score by hardware config",
        "Grouped bars: document-type specialist on the x-axis, Modal fleet shape on color · SAND-032 run reports",
        categories, series, unit="", fmt=lambda v: f"{v:.3f}")


def fig_cost_grouped(D: dict, viz) -> str:
    categories = [_label(D, c) for c in ORDER]
    cols_present = [c for c in _matrix_cols() if any(MATRIX_RUNS.get((cls, c)) for cls in ORDER)]
    series = []
    for i, col in enumerate(cols_present):
        vals = {}
        for cls in ORDER:
            rid = MATRIX_RUNS.get((cls, col))
            cat = _label(D, cls)
            if not rid or rid not in D["fleet"]:
                vals[cat] = None
                continue
            f = D["fleet"][rid]
            vals[cat] = f["busy_usd"] / f["ok"]
        series.append({"name": col, "cls": HW_SLOTS[i % len(HW_SLOTS)], "values": vals})
    return viz.grouped_vbar(
        "Busy-window cost per document by specialist and hardware",
        "Same matrix as the score chart; y-axis is GPU busy $/doc (wall × replicas × L4 rate ÷ ok docs)",
        categories, series, unit="$", fmt=lambda v: f"{v:.4f}")


def fig_heatmap(D: dict, viz) -> str:
    rows, cols, cells = _collect_matrix(D)
    return viz.heatmap(
        "Specialist × hardware extraction score matrix",
        "Cell color spans the observed score range; cell text is the raw overall extraction score from each run report",
        rows, cols, cells, fmt=lambda v: f"{v:.3f}")


def fig_scatter(D: dict, viz) -> str:
    points, legend = [], []
    hw_seen: dict[str, str] = {}
    for cls in ORDER:
        mark = SPECIALIST_MARKERS[cls]
        for col in _matrix_cols():
            rid = MATRIX_RUNS.get((cls, col))
            if not rid or rid not in D["runs"] or rid not in D["fleet"]:
                continue
            run, fleet = D["runs"][rid], D["fleet"][rid]
            x = fleet["busy_usd"] / fleet["ok"]
            y = _score(run)
            hw = col
            cls_slot = hw_seen.setdefault(hw, HW_SLOTS[len(hw_seen) % len(HW_SLOTS)])
            tip = f"{_label(D, cls)} · {hw} · {rid}: score {y:.3f}, ${x:.4f}/doc"
            points.append({"x": x, "y": y, "cls": cls_slot, "marker": mark,
                           "tip": tip, "label": _label(D, cls)[:4]})
            if hw not in [nm for _, nm, _ in legend]:
                legend.append((cls_slot, hw, "circle"))
    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    return viz.scatter(
        "Cost vs quality — Modal specialist runs",
        "Pareto view: x = busy $/doc, y = extraction score · point color = hardware config, marker shape = specialist class",
        points, x_label="Cost per successful document (USD)", y_label="Overall extraction score",
        x_domain=(0, max(xs) * 1.08), y_domain=(0, max(ys) * 1.05 if ys else 1),
        legend=legend, fmt_x=lambda v: f"{v:.4f}", fmt_y=lambda v: f"{v:.2f}")


def _hw_series_key(fleet: dict) -> str:
    return _hw_label(fleet)


def fig_throughput_concurrency(D: dict, viz) -> str:
    panels = []
    for cls in ORDER:
        rids = [r for r in CONCURRENCY_RUNS.get(cls, []) if r in D["fleet"]]
        if len(rids) < 2:
            continue
        by_hw: dict[str, list[dict]] = {}
        for rid in rids:
            f = D["fleet"][rid]
            by_hw.setdefault(_hw_series_key(f), []).append(
                {"x": f["conc"], "y": f["tps"], "tip": f"{rid}: c{f['conc']} → {f['tps']:.0f} tok/s"})
        series = []
        for i, (name, pts) in enumerate(sorted(by_hw.items())):
            pts = sorted(pts, key=lambda p: p["x"])
            series.append({"name": name, "cls": HW_SLOTS[i % len(HW_SLOTS)], "marker": "circle", "points": pts})
        if not series:
            continue
        xs = [p["x"] for s in series for p in s["points"]]
        ys = [p["y"] for s in series for p in s["points"]]
        panels.append(viz.lines(
            _label(D, cls),
            f"Throughput vs client concurrency · {len(rids)} committed runs",
            series, x_label="Client concurrency", y_label="Throughput (tok/s)",
            x_domain=(0, max(xs) * 1.05), y_domain=(0, max(ys) * 1.08),
            fmt_x=lambda v: f"{int(v)}", fmt_y=lambda v: f"{v:,.0f}", width=520, plot_h=220))
    if not panels:
        return viz.hbar("Throughput vs concurrency", "No concurrency ladder data in hub", [], unit="")
    return viz.small_multiples("Throughput vs concurrency by specialist", panels, cols=2)


def fig_cost_stack(D: dict, viz) -> str:
    rate = D["l4_usd_per_hour"]
    categories, busy_v, idle_v, cold_v = [], {}, {}, {}
    for rid in COST_STACK_RUNS:
        if rid not in D["runs"] or rid not in D["fleet"]:
            continue
        cls = D["runs"][rid]["cls"]
        cat = _label(D, cls)
        categories.append(cat)
        parts = _cost_parts(rid, D["fleet"][rid], rate)
        busy_v[cat], idle_v[cat], cold_v[cat] = parts["busy"], parts["idle"], parts["cold"]
    segments = [
        {"name": "GPU busy (wall)", "cls": "s1", "values": busy_v},
        {"name": "Idle slots", "cls": "s3", "values": idle_v},
        {"name": "Cold boot (amortized)", "cls": "s2", "values": cold_v},
    ]
    return viz.stacked_vbar(
        "Cost per document breakdown — five-class sweep",
        "Stacked busy GPU, idle-slot, and cold-boot $/doc from serving exports (2×L4 c32 sweep + MAUD merger)",
        categories, segments, unit="$", fmt=lambda v: f"{v:.4f}")


def _prefix_curve(run: dict, fleet: dict, final: float) -> list[dict]:
    """Approximate prefix-cache hit vs wall time from per-doc prompt volume (no committed scrape series)."""
    docs = [d for d in run.get("docs", []) if not d.get("error") and d.get("prompt")]
    if not docs:
        return [{"x": fleet["wall"], "y": final, "tip": f"end-of-run /metrics {final * 100:.1f}%"}]
    docs = sorted(docs, key=lambda d: float(d.get("latency") or 0))
    lat_sum = sum(float(d.get("latency") or 0) for d in docs) or 1.0
    ptok = sum(float(d["prompt"]) for d in docs)
    wall = float(fleet["wall"])
    out = [{"x": 0.0, "y": 0.0, "tip": "engine ready"}]
    cum_p, cum_lat = 0.0, 0.0
    for d in docs:
        cum_p += float(d["prompt"])
        cum_lat += float(d.get("latency") or 0)
        out.append({
            "x": wall * cum_lat / lat_sum,
            "y": final * cum_p / ptok,
            "tip": f"t={wall * cum_lat / lat_sum:.1f}s · ~{100 * final * cum_p / ptok:.1f}% (prompt-mass proxy)",
        })
    out[-1]["y"] = final
    return out


def _same_model_rows(D: dict, exclude: frozenset) -> list[dict]:
    import breakeven
    import gpu_report

    ex = exclude if exclude is not None else gpu_report.NOT_A_CONFIG
    for row in breakeven.analyze(D, ex)["rows"]:
        if row["cls"] not in SAME_MODEL_CLASSES:
            continue
        same = row.get("same")
        if not same:
            continue
        yield {
            "label": row["label"],
            "run": row["modal"]["run"],
            "modal_usd": row["modal"]["usd"],
            "modal_score": row["modal"]["score"],
            "api_usd": same["api"]["usd"],
            "api_score": same["api"]["score"],
            "ratio": same["ratio"],
            "warm_docs_h": same["l4x1"]["docs_h_star"],
            "cold_n": same["l4x1"]["batch_star"],
        }


def fig_modal_api_qwen8b_table(D: dict, viz, exclude=None) -> str:
    import breakeven as be

    cols = [
        "Class", "Modal run", "Modal $/doc", "Modal score", f"API {be.SAME_MODEL_API} $/doc",
        "API score", "Modal ÷ API", "API ÷ Modal", "Warm 1×L4 docs/h", "Cold batch ≥ N",
    ]
    body = []
    for r in _same_model_rows(D, exclude):
        body.append([
            r["label"],
            r["run"],
            f"${r['modal_usd']:.4f}",
            f"{r['modal_score']:.3f}",
            f"${r['api_usd']:.4f}",
            f"{r['api_score']:.3f}",
            f"{r['ratio']:.2f}×",
            f"{1 / r['ratio']:.1f}×",
            str(int(round(r["warm_docs_h"]))),
            str(r["cold_n"]),
        ])
    return viz.data_table(
        "Modal L4 vs hosted Qwen3-8B — same-model route comparison",
        "SAND-032 sweep runs vs eval-environment API legs on Qwen3-8B · break-even docs/h at warm 1×L4",
        cols, body, width=1040)


def fig_modal_api_qwen8b_cost(D: dict, viz, exclude=None) -> str:
    groups = []
    for r in _same_model_rows(D, exclude):
        groups.append({
            "label": r["label"],
            "rows": [
                {"label": "Modal L4 (AWQ)", "value": r["modal_usd"] * 1000, "series": "s1",
                 "note": f"score {r['modal_score']:.3f}"},
                {"label": "API Qwen3-8B", "value": r["api_usd"] * 1000, "series": "s2",
                 "note": f"score {r['api_score']:.3f}"},
            ],
        })
    return viz.grouped_hbar(
        "Cost per 1,000 documents — Modal L4 vs API Qwen3-8B",
        "Horizontal bars per class; tip notes extraction score · values from hub break-even analysis",
        groups, legend=[("s1", "Modal L4"), ("s2", "API Qwen3-8B")], unit=" USD", fmt=lambda v: f"{v:.2f}")


def fig_prefix_cache(D: dict, viz) -> str:
    panels = []
    for rid in PREFIX_RUNS:
        if rid not in D["runs"] or rid not in D["fleet"]:
            continue
        run, fleet = D["runs"][rid], D["fleet"][rid]
        splits = fleet.get("replica_split") or []
        if not splits:
            continue
        series = []
        for i, rep in enumerate(splits):
            final = float(rep.get("prefix") or 0)
            pts = _prefix_curve(run, fleet, final)
            series.append({
                "name": f"replica {i + 1} ({final * 100:.1f}% end)",
                "cls": HW_SLOTS[i % len(HW_SLOTS)],
                "marker": "circle",
                "points": [{"x": p["x"], "y": p["y"] * 100, "tip": p["tip"]} for p in pts],
            })
        wall = fleet["wall"]
        panels.append(viz.lines(
            _label(D, run["cls"]),
            f"{rid} · y rises with prompt mass processed (proxy); end points match vLLM /metrics cumulative hit",
            series, x_label="Wall time (s)", y_label="Prefix-cache hit (%)",
            x_domain=(0, wall * 1.02), y_domain=(0, max(float(r.get('prefix') or 0) for r in splits) * 100 * 1.15 + 5),
            fmt_x=lambda v: f"{v:.0f}", fmt_y=lambda v: f"{v:.0f}", width=520, plot_h=220))
    return viz.small_multiples(
        "Prefix-cache hit rate over wall time",
        panels, cols=2)


CAPTIONS = {
    "figures/modal-performance/score-by-specialist-hardware.svg": (
        "Grouped bar chart of overall extraction score per specialist, with one bar per Modal hardware config."),
    "figures/modal-performance/cost-by-specialist-hardware.svg": (
        "Grouped bar chart of busy-window GPU cost per document for the same specialist × hardware matrix."),
    "figures/modal-performance/score-heatmap.svg": (
        "Heatmap of extraction score: rows = specialists, columns = hardware configs, cell text = raw score."),
    "figures/modal-performance/cost-vs-quality-scatter.svg": (
        "Scatter of busy $/doc vs extraction score; color = hardware, marker shape = specialist family."),
    "figures/modal-performance/throughput-vs-concurrency.svg": (
        "Throughput vs client concurrency, faceted by specialist; one line per fleet shape."),
    "figures/modal-performance/cost-doc-breakdown.svg": (
        "Stacked $/doc: GPU busy wall time, idle slots, and amortized cold boot for the five-class sweep."),
    "figures/modal-performance/prefix-cache-over-time.svg": (
        "Prefix-cache hit vs wall time; lines per replica with end points from vLLM /metrics (42.8% / 43.2% on s9 insurance bal)."),
    "figures/modal-performance/modal-api-qwen8b-table.svg": (
        "Modal vs API Qwen3-8B per class: $/doc, scores, cost ratios, warm break-even docs/h and cold-batch N."),
    "figures/modal-performance/modal-api-qwen8b-cost.svg": (
        "Grouped horizontal bars: Modal L4 vs API Qwen3-8B cost per 1,000 documents, four specialist classes."),
}


def render(D: dict, viz, *, exclude=None) -> dict[str, str]:
    return {
        "figures/modal-performance/score-by-specialist-hardware.svg": fig_score_grouped(D, viz),
        "figures/modal-performance/cost-by-specialist-hardware.svg": fig_cost_grouped(D, viz),
        "figures/modal-performance/score-heatmap.svg": fig_heatmap(D, viz),
        "figures/modal-performance/cost-vs-quality-scatter.svg": fig_scatter(D, viz),
        "figures/modal-performance/throughput-vs-concurrency.svg": fig_throughput_concurrency(D, viz),
        "figures/modal-performance/cost-doc-breakdown.svg": fig_cost_stack(D, viz),
        "figures/modal-performance/prefix-cache-over-time.svg": fig_prefix_cache(D, viz),
        "figures/modal-performance/modal-api-qwen8b-table.svg": fig_modal_api_qwen8b_table(D, viz, exclude),
        "figures/modal-performance/modal-api-qwen8b-cost.svg": fig_modal_api_qwen8b_cost(D, viz, exclude),
    }


def report_md(fig_paths: list[str]) -> str:
    lines = [
        "# Modal specialist performance visuals",
        "",
        "Deterministic SVGs from committed SAND-032 run reports and serving exports (`hub_data.json`). "
        "Regenerate with `python scripts/sand032/render_modal_performance.py` (also writes 2× PNGs under `viz/modal-performance/`).",
        "",
    ]
    titles = {
        "score-by-specialist-hardware.svg": "Extraction score by specialist and hardware",
        "cost-by-specialist-hardware.svg": "Cost per document by specialist and hardware",
        "score-heatmap.svg": "Score heatmap (specialist × hardware)",
        "cost-vs-quality-scatter.svg": "Cost vs quality scatter",
        "throughput-vs-concurrency.svg": "Throughput vs concurrency",
        "cost-doc-breakdown.svg": "Cost breakdown stacked bar",
        "prefix-cache-over-time.svg": "Prefix-cache hit over wall time",
        "modal-api-qwen8b-table.svg": "Modal vs API Qwen3-8B comparison table",
        "modal-api-qwen8b-cost.svg": "Modal vs API Qwen3-8B cost per 1,000 docs",
    }
    for rel in fig_paths:
        name = Path(rel).name
        cap = CAPTIONS.get(rel, "")
        png = f"viz/modal-performance/{name.replace('.svg', '.png')}"
        lines += [f"## {titles.get(name, name)}", "", f"![{cap}]({rel})", "", f"PNG (2×): [`{png}`]({png})", "", cap, ""]
    return "\n".join(lines)
