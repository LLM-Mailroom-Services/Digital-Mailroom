"""Redraws of the seven source-repo charts the mailroom-issues reports embed, in the sandbox chart kit.

The reports used to copy these SVGs verbatim from `eval-environment` (web/data/charts/) and
`mailroom-ml` (reports/charts/m9a-local-20260927-014429/), each in its own light theme. This module
redraws them from the cross-checked hub data (`reports/dashboard/hub_data.json`, loaded as ``D``) with
`scripts/sand032/viz.py`, so every figure is a dark, high-contrast card in the same visual system and
every number is read from ``D`` (nothing is typed in).

    render(D, viz)  -> {figure path: SVG string}
    tables(D)       -> {figure path: markdown table}   (the table-view twin of each figure)
    CAPTIONS        -> {figure path: alt text}

Model identity follows ``viz.ENTITY`` (Qwen3.7-Flash s2, DeepSeek-V4.1-Flash s3, Granite-4.2-8B s4,
Qwen3-8B s5, ModernBERT s6) and is never color alone: every bar is labeled with its series name, and the
calibration markers differ in shape as well as color.
"""
from __future__ import annotations

import math

ORDER = ["correspondence", "insurance_claim", "corporate_record", "contract", "merger_agreement"]
# Display names for the logged model ids (names, not measurements).
MODEL_NAME = {"qwen/qwen3.7-flash": "Qwen3.7-Flash", "deepseek/deepseek-v4.1-flash": "DeepSeek-V4.1-Flash",
              "ibm-granite/granite-4.2-8b": "Granite-4.2-8B", "qwen/qwen3-8b": "Qwen3-8B"}
CHECKPOINTS = [("run3", "Run 3"), ("armA", "Arm A · 1 epoch"), ("armB", "Arm B · 3 epochs")]
MIN_BIN = 5  # calibration bins with fewer documents are not drawn (they stay in the table)
Z95 = 1.959964  # two-sided 95% normal quantile, for the Wilson lower bound

K_SCORE = "figures/api/extraction-score-by-type.svg"
K_COST = "figures/api/cost-per-document.svg"
K_SUB = "figures/api/sorter-subclass-accuracy.svg"
K_CAL = "figures/api/sorter-calibration.svg"
K_RECALL = "figures/modernbert/doc-type-recall.svg"
K_RISK = "figures/modernbert/selective-risk.svg"
K_COLLAPSE = "figures/modernbert/subclass-collapse.svg"
KEYS = [K_SCORE, K_COST, K_SUB, K_CAL, K_RECALL, K_RISK, K_COLLAPSE]

CAPTIONS = {
    K_SCORE: "Grouped bar chart of mean extraction score (0 to 1) per document type for each hosted model. "
             "No model wins every task: DeepSeek-V4.1-Flash leads insurance claims and corporate records, "
             "Qwen3-8B leads correspondence and contracts, and Qwen3.7-Flash at n = 50 posts the best merger score.",
    K_COST: "Grouped bar chart of API cost in US dollars per 1,000 documents, per document type and hosted model. "
            "DeepSeek-V4.1-Flash and Qwen3.7-Flash are the cheapest on most types; merger agreements cost the most.",
    K_SUB: "Grouped bar chart of LLM sorter subclass accuracy among documents whose class was right, per class, "
           "for the three n = 100 sorter runs, against the 75% P0 subclass gate. Only insurance claims clear it.",
    K_CAL: "Calibration plot of the three n = 100 LLM sorters: mean stated confidence per bin against observed "
           "class accuracy, with the perfect-calibration diagonal. Points below the diagonal are overconfident.",
    K_RECALL: "Grouped bar chart of ModernBERT document-type recall per class for Run 3, Arm A and Arm B, plus "
              "overall accuracy against the 95% P0 doc-type gate. Arm B is the first checkpoint over the gate.",
    K_RISK: "Line chart of ModernBERT Arm B selective prediction: accuracy of accepted windows against the share "
            "of windows accepted as the confidence threshold rises, with the Wilson 95% lower bound.",
    K_COLLAPSE: "Grouped bar chart of ModernBERT Arm B subclass accuracy per class against the 75% P0 gate, with "
                "the share of predictions on the single most common predicted subclass and the most common true "
                "subclass's share. Contracts collapse onto one predicted subclass.",
}


# ------------------------------------------------------------------------------------------ data
def _label(D, c: str) -> str:
    return D["labels"][c]


def _task(D, c: str) -> str:
    return D["labels"][c].lower()  # hub task keys are the lower-cased class labels ("insurance claims")


def _api_legs(D, c: str) -> list[dict]:
    """Every hosted extraction leg for one class: the N = 20 legs, then the Qwen3.7-Flash n = 50 route."""
    task = _task(D, c)
    legs = [dict(rec, name=MODEL_NAME.get(rec["model"], rec["family"])) for rec in D["api"]["tasks"][task].values()]
    legs.sort(key=lambda r: r["name"])
    q = D["api"]["route50"][task]
    legs.append(dict(q, name=MODEL_NAME.get(q["model"], q["family"])))
    return legs


def _leg_label(rec: dict, base_n: int) -> str:
    name = rec["name"]
    if name != rec["family"]:  # a leg filed under another family: label it by the logged model
        name += f" · {rec['prompt_lineage']} prompts"
    if rec["n"] != base_n:
        name += f" · n = {rec['n']}"
    return name


def _leg_note(rec: dict) -> str:
    filed = f"; filed as {rec['family']}" if rec["name"] != rec["family"] else ""
    return f"n = {rec['n']}, {rec['prompt_lineage']} prompts, run {rec['run']}{filed}"


def _base_n(D) -> int:
    ns = [rec["n"] for t in D["api"]["tasks"].values() for rec in t.values()]
    return max(set(ns), key=ns.count)


def _sorters(D) -> list[tuple[str, dict]]:
    """The n >= 100 hosted sorter runs that carry calibration/collapse detail, by display name."""
    runs = [r for r in D["api"]["classification"] if r["n"] >= 100 and r["model"] in D["api"]["sorter"]]
    return sorted(((MODEL_NAME.get(r["model"], r["model"]), D["api"]["sorter"][r["model"]]) for r in runs))


def _gate(D, key: str) -> float:
    return D["mb"]["armB"]["gates"][key]["threshold"]


def _wilson_lo(p: float, n: int, z: float = Z95) -> float:
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    return (c - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def _pct(v: float, nd: int = 0) -> str:
    return f"{v * 100:.{nd}f}%"


def _share(x: int, n: int) -> float:
    return x / n if n else 0.0


def _nice(s: str) -> str:
    return s.replace("_", " ")


# ------------------------------------------------------------------------------------------ charts
def _score(D, viz) -> str:
    base = _base_n(D)
    groups = [{"label": _label(D, c), "rows": [
        {"label": _leg_label(r, base), "value": r["score"], "series": viz.entity(r["name"]), "note": _leg_note(r)}
        for r in _api_legs(D, c)]} for c in ORDER]
    names = sorted({r["name"] for c in ORDER for r in _api_legs(D, c)})
    return viz.grouped_hbar(
        "Extraction score by document type",
        f"Mean overall score per document (0 to 1), hosted API models, n = {base} documents per bar unless marked",
        groups, legend=[(viz.entity(n), n) for n in names], fmt=lambda v: f"{v:.2f}",
        tick_fmt=lambda t: f"{t:.2f}", domain_max=1.0)


def _cost(D, viz) -> str:
    base = _base_n(D)
    groups = [{"label": _label(D, c), "rows": [
        {"label": _leg_label(r, base), "value": r["cost"] / r["n"] * 1000, "series": viz.entity(r["name"]),
         "note": f"${r['cost']:.4f} total over {r['n']} documents; {_leg_note(r)}"}
        for r in _api_legs(D, c)]} for c in ORDER]
    names = sorted({r["name"] for c in ORDER for r in _api_legs(D, c)})
    return viz.grouped_hbar(
        "API cost per 1,000 documents",
        "US dollars per 1,000 documents: each run's billed cost divided by its scored documents",
        groups, legend=[(viz.entity(n), n) for n in names], fmt=lambda v: f"${v:.2f}",
        tick_fmt=lambda t: f"${viz._fmt_tick(t)}")


def _subclass(D, viz) -> str:
    sorters = _sorters(D)
    groups = []
    for c in ORDER:
        rows = []
        for name, s in sorters:
            col = s["collapse"].get(c)
            if not col:
                continue
            v = _share(col["correct"], col["n"])
            rows.append({"label": name, "value": v * 100, "series": viz.entity(name),
                         "text": f"{v * 100:.0f}% ({col['correct']}/{col['n']})",
                         "note": f"{col['correct']} of {col['n']} correctly classed documents got the right subclass"})
        groups.append({"label": _label(D, c), "rows": rows})
    g = _gate(D, "P0_subclass")
    n = sorters[0][1]["n"]
    return viz.grouped_hbar(
        "LLM sorter subclass accuracy by class",
        f"Share of correctly classed documents that also got the right subclass, n = {n} documents per model",
        groups, legend=[(viz.entity(nm), nm) for nm, _ in sorters], unit="%", domain_max=100,
        refs=[(g * 100, f"P0 subclass gate {g * 100:.0f}%")])


def _calibration(D, viz) -> str:
    shapes = ["circle", "square", "diamond", "circle", "square", "diamond"]
    series, lo = [], 1.0
    for i, (name, s) in enumerate(_sorters(D)):
        pts = [b for b in s["bins"] if b["n"] >= MIN_BIN]
        lo = min([lo] + [b["conf"] for b in pts] + [b["acc"] for b in pts])
        series.append({"name": f"{name} · ECE {s['ece']:.3f}", "cls": viz.entity(name), "marker": shapes[i],
                       "points": [{"x": b["conf"] * 100, "y": b["acc"] * 100,
                                   "tip": f"{name}: {b['n']} documents, stated {b['conf'] * 100:.1f}%, "
                                          f"observed {b['acc'] * 100:.1f}%"} for b in pts]})
    lo = math.floor(lo * 10) / 10 * 100
    n = _sorters(D)[0][1]["n"]
    # Direct labels at each curve's lowest-confidence bin: left of the point when the point sits well below the
    # diagonal (the label then clears the reference line), otherwise dropped below the point on a leader line.
    notes = []
    for (name, _), sr in zip(_sorters(D), series):
        if not sr["points"]:
            continue
        p = sr["points"][0]
        clear = p["x"] - p["y"] > 4
        notes.append({"x": p["x"], "y": p["y"], "text": name, "style": "lbl", "leader": not clear,
                      "dx": -10 if clear else 0, "dy": 0 if clear else 90, "anchor": "end" if clear else "middle"})
    return viz.lines(
        "LLM sorter calibration",
        f"Stated confidence against observed class accuracy per confidence bin, n = {n} documents per model",
        series, x_label="Stated confidence (bin mean)", y_label="Observed class accuracy",
        x_domain=(lo, 100), y_domain=(lo, 100), x_step=10, y_step=10, unit_x="%", unit_y="%",
        diagonal="Perfect calibration: points below the line are overconfident", notes=notes)


def _recall(D, viz) -> str:
    mb = D["mb"]
    last = CHECKPOINTS[-1][0]
    cls = lambda k: "s6" if k == last else "deemph"  # noqa: E731
    groups = [{"label": "All documents (accuracy)", "rows": [
        {"label": lab, "value": mb[k]["acc"] * 100, "series": cls(k), "note": f"n = {mb[k]['n']} documents"}
        for k, lab in CHECKPOINTS]}]
    for c in ORDER:
        rows = []
        for k, lab in CHECKPOINTS:
            pc = mb[k]["per_class"][c]
            rows.append({"label": lab, "value": _share(pc["correct"], pc["n"]) * 100, "series": cls(k),
                         "note": f"{pc['correct']} of {pc['n']} routed to their true class"})
        groups.append({"label": _label(D, c), "rows": rows})
    g = _gate(D, "P0_doc_type")
    return viz.grouped_hbar(
        "ModernBERT document-type recall by class",
        f"Share of each true class routed to it, n = {mb[last]['n']} test documents per checkpoint",
        groups, legend=[("s6", CHECKPOINTS[-1][1]), ("deemph", "Earlier checkpoints")], unit="%",
        fmt=lambda v: f"{v:.1f}", domain_max=100, refs=[(g * 100, f"P0 doc-type gate {g * 100:.0f}% (all documents)")])


def _risk_rows(D) -> list[dict]:
    return [{"thr": t, "cov": cov, "acc": acc, "n": n, "lo": _wilson_lo(acc, n)} for t, cov, acc, n in D["mb"]["armB"]["risk"]]


def _risk(D, viz) -> str:
    b = D["mb"]["armB"]
    rows = _risk_rows(D)
    tip = lambda r: (f"Threshold {r['thr']:.2f}: {r['n']} windows accepted ({r['cov'] * 100:.1f}%), "  # noqa: E731
                     f"accuracy {r['acc'] * 100:.2f}%, Wilson lower bound {r['lo'] * 100:.2f}%")
    series = [{"name": "Accuracy of accepted windows", "cls": "s6", "marker": None,
               "points": [{"x": r["cov"] * 100, "y": r["acc"] * 100, "tip": tip(r)} for r in rows]},
              {"name": "Wilson 95% lower bound", "cls": "deemph", "marker": None,
               "points": [{"x": r["cov"] * 100, "y": r["lo"] * 100, "tip": tip(r)} for r in rows]}]
    x_lo = math.floor(min(r["cov"] for r in rows) * 10) * 10
    y_lo = math.floor(min(r["lo"] for r in rows) * 100)
    pick = min(rows, key=lambda r: abs(r["thr"] - b["pick"]))
    notes = [{"x": pick["cov"] * 100, "y": pick["acc"] * 100, "cls": "s6", "dx": -40, "dy": 34, "anchor": "end",
              "text": f"Threshold {pick['thr']:.2f}: {_pct(pick['cov'])} accepted at {_pct(pick['acc'], 1)} accuracy"}]
    return viz.lines(
        "ModernBERT selective prediction, Arm B",
        f"Each step is a confidence threshold, from {rows[0]['thr']:.2f} (right) to {rows[-1]['thr']:.2f} (left); "
        f"{b['windows']} test windows",
        series, x_label="Share of windows accepted (coverage)", y_label="Accuracy of accepted windows",
        x_domain=(x_lo, 100), y_domain=(y_lo, 100), x_step=10, y_step=1, unit_x="%", unit_y="%", notes=notes)


def _collapse(D, viz) -> str:
    col = D["mb"]["armB"]["eda"]["collapse"]
    groups = []
    for c in ORDER:
        x = col[c]
        acc, pred, true = (_share(x["correct"], x["n"]), _share(x["top_pred"][1], x["n"]), _share(x["top_true"][1], x["n"]))
        groups.append({"label": _label(D, c), "rows": [
            {"label": "Subclass accuracy", "value": acc * 100, "series": "s6",
             "note": f"{x['correct']} of {x['n']} documents with the right type"},
            {"label": "Top predicted subclass", "value": pred * 100, "series": "deemph",
             "text": f"{pred * 100:.0f}% · {_nice(x['top_pred'][0])}",
             "note": f"{x['top_pred'][1]} of {x['n']} predictions"},
            {"label": "Top true subclass", "value": true * 100, "series": "deemph",
             "text": f"{true * 100:.0f}% · {_nice(x['top_true'][0])}",
             "note": f"{x['top_true'][1]} of {x['n']} documents"}]})
    g = _gate(D, "P0_subclass")
    return viz.grouped_hbar(
        "ModernBERT subclass accuracy and collapse, Arm B",
        "Documents whose type was right. A top predicted share far above the top true share means collapse",
        groups, legend=[("s6", "Subclass accuracy"), ("deemph", "Share on the single most common subclass")],
        unit="%", fmt=lambda v: f"{v:.0f}", domain_max=100, refs=[(g * 100, f"P0 subclass gate {g * 100:.0f}%")])


def render(D: dict, viz) -> dict[str, str]:
    """Figure path -> SVG string for the seven redrawn source charts."""
    return {K_SCORE: _score(D, viz), K_COST: _cost(D, viz), K_SUB: _subclass(D, viz), K_CAL: _calibration(D, viz),
            K_RECALL: _recall(D, viz), K_RISK: _risk(D, viz), K_COLLAPSE: _collapse(D, viz)}


# ------------------------------------------------------------------------------------------ table twins
def _md(head: list[str], rows: list[list], align: str) -> str:
    sep = ["---" if a == "l" else "---:" for a in align]
    out = ["| " + " | ".join(head) + " |", "| " + " | ".join(sep) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def tables(D: dict) -> dict[str, str]:
    """Figure path -> markdown table carrying every value the figure plots (its table-view twin)."""
    base = _base_n(D)
    score, cost = [], []
    for c in ORDER:
        for r in _api_legs(D, c):
            lab = _leg_label(r, base)
            score.append([_label(D, c), lab, r["n"], f"{r['score']:.4f}", f"`{r['run']}`"])
            cost.append([_label(D, c), lab, r["n"], f"${r['cost']:.6f}", f"${r['cost'] / r['n'] * 1000:.2f}"])
    sub, cal = [], []
    for c in ORDER:
        for name, s in _sorters(D):
            col = s["collapse"].get(c)
            if col:
                sub.append([_label(D, c), name, col["n"], col["correct"], _pct(_share(col["correct"], col["n"]), 1)])
    for name, s in _sorters(D):
        for i, b in enumerate(s["bins"], 1):
            cal.append([name, i, b["n"], f"{b['conf'] * 100:.2f}%", f"{b['acc'] * 100:.2f}%",
                        "yes" if b["n"] >= MIN_BIN else "no", f"{s['ece']:.4f}"])
    mb = D["mb"]
    rec = [["All documents (accuracy)", lab, "—", mb[k]["n"], f"{mb[k]['acc'] * 100:.2f}%"] for k, lab in CHECKPOINTS]
    for c in ORDER:
        for k, lab in CHECKPOINTS:
            pc = mb[k]["per_class"][c]
            rec.append([_label(D, c), lab, pc["correct"], pc["n"], f"{_share(pc['correct'], pc['n']) * 100:.2f}%"])
    risk = [[f"{r['thr']:.2f}", r["n"], f"{r['cov'] * 100:.2f}%", f"{r['acc'] * 100:.2f}%", f"{r['lo'] * 100:.2f}%"]
            for r in _risk_rows(D)]
    col = mb["armB"]["eda"]["collapse"]
    coll = [[_label(D, c), col[c]["n"], col[c]["correct"], f"{_share(col[c]['correct'], col[c]['n']) * 100:.1f}%",
             f"{_nice(col[c]['top_pred'][0])} ({col[c]['top_pred'][1]}, {_share(col[c]['top_pred'][1], col[c]['n']) * 100:.1f}%)",
             f"{_nice(col[c]['top_true'][0])} ({col[c]['top_true'][1]}, {_share(col[c]['top_true'][1], col[c]['n']) * 100:.1f}%)"]
            for c in ORDER]
    return {
        K_SCORE: _md(["Document type", "Model", "n", "Mean score", "Run"], score, "llrrl"),
        K_COST: _md(["Document type", "Model", "n", "Run cost (USD)", "USD per 1,000 documents"], cost, "llrrr"),
        K_SUB: _md(["Class", "Model", "Correctly classed", "Right subclass", "Subclass accuracy"], sub, "llrrr"),
        K_CAL: _md(["Model", "Bin", "Documents", "Mean stated confidence", "Observed accuracy", "Drawn", "ECE"], cal,
                   "lrrrrlr"),
        K_RECALL: _md(["Class", "Checkpoint", "Correct", "n", "Recall"], rec, "llrrr"),
        K_RISK: _md(["Threshold", "Windows accepted", "Coverage", "Accuracy", "Wilson 95% lower bound"], risk, "rrrrr"),
        K_COLLAPSE: _md(["Class", "Right type", "Right subclass", "Subclass accuracy", "Top predicted subclass (count, share)",
                         "Top true subclass (count, share)"], coll, "lrrrll"),
    }
