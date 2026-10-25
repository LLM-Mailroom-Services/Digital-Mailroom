"""Plain-language reader report for the specialist-grid results (external audience).

The master card (``grid_master``) is written for the team: it names experiments with posture
shorthand (``2×L4 C32 n=100``). This module renders the same numbers for readers outside the
project — Experiment 1–4 in plain words, every metric defined before it is used, shorthand only
in a closing cross-reference — as two files next to the master card:

    reports/SAND-37/READER-REPORT.md      paste-ready Markdown (Bear → PDF; no links,
                                          no local images, GitHub-style tables)
    reports/SAND-37/READER-REPORT.ipynb   the same text as notebook cells, plus charts
                                          built from an inline data table (pre-rendered,
                                          runs anywhere with pandas + matplotlib)
    reports/SAND-37/READER-REPORT.pdf     typeset print version (``grid_reader_pdf``),
                                          fingerprinted in READER-REPORT.pdf.sha256

All three regenerate with ``sandbox run card --master``; a staleness test keeps them in sync.
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any, Mapping

from mailroom_sandbox.job import grid_master as gm

READER_STEM = "READER-REPORT"

# Plain run names, in the order the master card lists the postures.
RUNS: tuple[tuple[str, str], ...] = (
    ("s37-1l4-n20", "Experiment 1"),
    ("s39-1l4-n50", "Experiment 2"),
    ("s37-2l4-n50", "Experiment 3"),
    ("s40-2l4", "Experiment 4"),
)
_NAME = dict(RUNS)
# Harmonized print palette: blues for the 1-GPU runs, teal and amber for the 2-GPU runs.
CHART_COLORS = {"Experiment 1": "#9dbbdb", "Experiment 2": "#3f73a8", "Experiment 3": "#2f8f83", "Experiment 4": "#d99a4e"}
# Non-breaking spaces keep run labels on one line in narrow table cells (PDF and Bear alike).
_STUDY_RUNS = {"SAND-37": "Experiments\u00a01\u00a0and\u00a03", "SAND-39": "Experiment\u00a02", "SAND-40": "Experiment\u00a04"}

_TYPE_TEXT = {
    "insurance_claims": "Insurance claim forms and notices",
    "contracts": "Commercial contracts",
    "corporate_records": "Corporate filings and records",
    "correspondence": "Business letters and email",
    "merger_agreement": "Merger agreements (often 100+ pages)",
}
_SCORE_TEXT = {
    "insurance_claims": "Extraction score",
    "contracts": "Clause F1 (CUAD)",
    "corporate_records": "Extraction score",
    "correspondence": "Extraction score",
    "merger_agreement": "Question accuracy (MAUD)",
}


def reader_paths(repo: Path | None = None) -> dict[str, Path]:
    base = gm.master_paths(repo)["md"].parent
    return {"md": base / f"{READER_STEM}.md", "ipynb": base / f"{READER_STEM}.ipynb"}


def _pct(new: float | None, old: float | None) -> float | None:
    return (new / old - 1.0) if new is not None and old else None


def _usd(v: float | None, digits: int = 4) -> str:
    return f"${v:.{digits}f}" if v is not None else "—"


def _facts(data: Mapping[str, Any]) -> dict[str, Any]:
    """Every number the report quotes, computed once from the committed cards."""
    cards: dict[str, dict[str, Any]] = data["cards"]
    metered: Mapping[str, Any] = data.get("metered") or {}
    present = [p for p in gm.POSTURES if cards[p.key]]
    pooled = {p.key: gm._pooled(cards[p.key], p.replicas) for p in gm.POSTURES}
    by_key = {p.key: p for p in gm.POSTURES}
    f: dict[str, Any] = {"cards": cards, "pooled": pooled, "present": present, "by_key": by_key, "metered": metered}
    first = next((c for p in present for c in cards[p.key].values()), None)
    f["conditions"] = first["conditions"] if first else None

    b, c = pooled.get("s39-1l4-n50"), pooled.get("s37-2l4-n50")
    if b and c:
        lat = [
            cards["s37-2l4-n50"][t]["latency"]["p50"] / cards["s39-1l4-n50"][t]["latency"]["p50"]
            for t in gm._ORDER
            if t in cards["s37-2l4-n50"] and t in cards["s39-1l4-n50"] and cards["s39-1l4-n50"][t]["latency"]["p50"]
        ]
        f["scale"] = {
            "docs": c["documents"],
            "speed": _pct(c["docs_per_minute"], b["docs_per_minute"]),
            "cost": _pct(c["usd_per_document"], b["usd_per_document"]),
            "lat_lo": min(lat), "lat_hi": max(lat),
        }
    if cards.get("s37-2l4-n50") and cards.get("s40-2l4"):
        a4, d4 = gm._pooled_four(cards["s37-2l4-n50"], 2), gm._pooled_four(cards["s40-2l4"], 2)
        if a4 and d4:
            f["batch"] = {"cost": _pct(d4["usd_per_document"], a4["usd_per_document"]),
                          "speed": _pct(d4["docs_per_minute"], a4["docs_per_minute"]),
                          "errors": d4["errors"], "docs": d4["documents"]}
    pairs = []
    if cards.get("s39-1l4-n50") and cards.get("s37-2l4-n50"):
        pairs += [gm._paired(cards["s39-1l4-n50"].get(t), cards["s37-2l4-n50"].get(t)) for t in gm._ORDER]
    if cards.get("s37-2l4-n50") and cards.get("s40-2l4"):
        pairs += [gm._paired(cards["s37-2l4-n50"].get(t), cards["s40-2l4"].get(t))
                  for t in gm._ORDER if t != "merger_agreement"]
    pairs = [x for x in pairs if x]
    if pairs:
        f["quality"] = {
            "n": sum(x["n"] for x in pairs),
            "lo": min(x["mean"] for x in pairs), "hi": max(x["mean"] for x in pairs),
            "zero": all(x["lo"] <= 0 <= x["hi"] for x in pairs),
            "widest": max(x["half"] for x in pairs),
        }
    before = (cards.get("s37-2l4-n50") or {}).get("merger_agreement")
    after = (cards.get("s40-2l4") or {}).get("merger_agreement")
    if before and after:
        cb, ca = before["quality"].get("clause") or {}, after["quality"].get("clause") or {}
        m = gm._matched_merger(before, after)
        f["merger"] = {
            "acc_before": cb.get("accuracy") or 0.0, "acc_after": ca.get("accuracy") or 0.0,
            "cov_before": cb.get("coverage") or 0.0, "cov_after": ca.get("coverage") or 0.0,
            "ok_before": before["quality"]["ok"], "ok_after": after["quality"]["ok"], "n": after["n"],
            "cost_before": before["cost"]["usd_per_ok_document"], "cost_after": after["cost"]["usd_per_ok_document"],
            "lat_before": before["latency"]["p50"], "lat_after": after["latency"]["p50"],
            "matched": m,
        }
    kinds = {k for p in present for c in cards[p.key].values() for k in (c["quality"].get("error_kinds") or {})}
    f["errors_all_length"] = bool(kinds) and all("Length" in k for k in kinds)
    f["total_errors"] = sum(pooled[p.key]["errors"] for p in present)
    f["total_docs"] = sum(pooled[p.key]["documents"] for p in present)

    rows = []
    for study in dict.fromkeys(p.study for p in present):
        rec = metered.get(study)
        if not isinstance(rec, Mapping):
            continue
        legs = [pooled[p.key] for p in present if p.study == study]
        rows.append({
            "label": _STUDY_RUNS.get(study, study),
            "docs": sum(x["documents"] for x in legs),
            "busy": sum(x["busy_usd"] or 0.0 for x in legs),
            "metered": float(rec.get("metered_usd", 0)),
            "billed": float(rec.get("billed_usd", 0)),
        })
    f["cost_rows"] = rows
    f["unmetered"] = [_STUDY_RUNS.get(s, s) for s in dict.fromkeys(p.study for p in present) if s not in metered]
    return f


def _sections(data: Mapping[str, Any]) -> list[tuple[str, list[str]]]:
    """(heading, lines) pairs; the Markdown file joins them, the notebook makes one cell each."""
    f = _facts(data)
    cards, pooled, by_key = f["cards"], f["pooled"], f["by_key"]
    cond = f["conditions"] or {}
    ds = cond.get("dataset") or {}
    gpu_hr = cond.get("gpu_usd_per_hour", 0.0)
    out: list[tuple[str, list[str]]] = []

    intro = [
        "# Document Extraction on Low-Cost Cloud GPUs: Speed, Quality and Cost",
        "",
        "We ran an open-source language model on rented cloud GPUs to pull structured information out of "
        "five kinds of business documents. We varied the hardware and the batch size across four experiments and "
        "measured speed, accuracy and cost.",
        "",
        f"**Data:** every result uses the public Hugging Face dataset `{ds.get('repo', '')}`. "
        "No American Family Insurance data was used or shared.",
        "",
    ]
    out.append(("", intro))

    key: list[str] = []
    if "scale" in f:
        s = f["scale"]
        key.append(
            f"**Adding a second GPU doubles speed at the same cost per document.** On the same {s['docs']} "
            f"documents, moving from 1 GPU to 2 GPUs processed {s['speed']:.0%} more documents per minute, and "
            f"GPU cost per document changed by only {s['cost']:+.1%}. The trade-off: each document waited "
            f"{s['lat_lo']:.1f}–{s['lat_hi']:.1f} times longer for its answer, because more documents shared "
            "the GPUs at once. This setup suits batch processing; latency-sensitive use would need different tuning."
        )
    if "batch" in f:
        bt = f["batch"]
        key.append(
            f"**Larger batches are cheaper.** On the 2-GPU setup, processing 100 documents of each type "
            f"instead of 50 cut GPU cost per document by {-bt['cost']:.0%} (four document types; merger "
            f"agreements excluded because their settings changed). {bt['errors']} of {bt['docs']} documents failed."
        )
    if "quality" in f:
        q = f["quality"]
        verdict = "did not change" if q["zero"] else "changed for at least one document type"
        key.append(
            f"**Hardware choice {verdict} accuracy.** Comparing the same documents across experiments "
            f"({q['n']} document pairs), the average score change per document type was between "
            f"{q['lo']:+.3f} and {q['hi']:+.3f} on a 0–1 scale, and every 95% confidence interval includes "
            f"zero. Effects smaller than about ±{q['widest']:.2f} cannot be ruled out at this sample size."
        )
    if "merger" in f:
        m = f["merger"]
        key.append(
            f"**Merger agreements are the weak spot; reading the whole agreement helps.** These contracts "
            "are far longer than the model can read in one pass. Splitting each agreement into overlapping "
            f"sections and combining the answers raised accuracy from {m['acc_before']:.1%} to "
            f"{m['acc_after']:.1%} and the share of questions answered from {m['cov_before']:.0%} to "
            f"{m['cov_after']:.0%}, at {m['cost_after'] / m['cost_before']:.1f} times the cost per agreement."
        )
    if f["cost_rows"]:
        tm = sum(r["metered"] for r in f["cost_rows"])
        td = sum(r["docs"] for r in f["cost_rows"])
        tb = sum(r["billed"] for r in f["cost_rows"])
        key.append(
            f"**The full study cost ${tm:.2f} in cloud charges for {td:,} documents** (about "
            f"{tm / td * 100:.2f} cents each, all-in), and ${tb:.2f} was billed after the provider's free credits."
        )
    out.append(("## Key findings", [f"{i}. {t}" for i, t in enumerate(key, 1)] + [""]))

    setup = [
        "**The task.** An automated mailroom reads each incoming document and returns its key facts as "
        "structured data (for example parties, dates, amounts, and which contract clauses are present). "
        "Each of the five document types has its own extraction instructions:",
        "",
        "| Document type | What it contains | How accuracy is measured |",
        "| --- | --- | --- |",
    ]
    for t in gm._ORDER:
        setup.append(f"| {gm._LABEL[t]} | {_TYPE_TEXT[t]} | {_SCORE_TEXT[t]} |")
    setup += [
        "",
        f"**The model.** {cond.get('model', 'Qwen3-8B')}: an open-weights model with 8 billion parameters, "
        "compressed to 4-bit weights (AWQ) so it fits on a single 24 GB GPU. It ran on vLLM, an open-source "
        f"model server, on NVIDIA L4 GPUs rented from Modal at ${gpu_hr:.2f} per GPU-hour.",
        "",
        f"**The sample.** Documents were drawn at random with a fixed seed ({ds.get('seed', '')}), so every "
        "run is reproducible. Smaller samples are subsets of larger ones, so runs can be compared on the "
        "same documents.",
        "",
    ]
    out.append(("## What we tested", setup))

    runs = [
        "| Experiment | GPUs | Documents processed at once | Documents per type | Total documents |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for k, name in RUNS:
        p = by_key[k]
        n_total = sum(p.expected_n(t) for t in gm._ORDER)
        per_type = f"{p.n} (merger agreements: {p.expected_n('merger_agreement')})" if p.n_by_folder else str(p.n)
        runs.append(f"| {name} | {p.replicas} | {p.concurrency} | {per_type} | {n_total} |")
    runs += [
        "",
        "Experiments 2 and 3 use the identical 250 documents and differ only in GPU count and documents processed at "
        "once, so they give the cleanest hardware comparison. Experiment 4 repeats Experiment 3's hardware on twice as many documents and also tests "
        "improved settings for merger agreements (described below).",
        "",
    ]
    out.append(("## The four experiments", runs))

    glossary = [
        "| Term | Meaning |",
        "| --- | --- |",
        "| Token | The unit a language model reads and writes; roughly three-quarters of an English word. |",
        "| Documents per minute | Overall throughput for the run: documents finished ÷ total run time. |",
        "| Tokens per second per GPU | Text processed (read plus written) per second by each GPU; a hardware-efficiency measure. |",
        "| Median time per document | Half of documents finished faster than this, half slower (seconds from submission to answer). |",
        f"| GPU cost per document | GPU time the documents actually used × ${gpu_hr:.2f}/hour ÷ documents. Excludes start-up and idle time. |",
        "| Session cost | What the cloud provider metered for the whole session, including start-up, waiting and shut-down. |",
        "| Failed document | The model's answer exceeded the output length limit (8,192 tokens) and was cut off, so no result was returned. |",
        "| Extraction score | 0–1. Average agreement between extracted fields and the dataset's answer key, per document. |",
        "| Clause F1 (CUAD) | 0–1. CUAD is a public set of commercial contracts with lawyer-labeled clause types. F1 balances finding the clauses that are present against flagging clauses that are not. |",
        "| Question accuracy (MAUD) | 0–1. MAUD is a public set of merger agreements with lawyer-written multiple-choice questions. Accuracy is the share of all labeled questions answered correctly; coverage is the share the model answered at all. |",
        "| 95% confidence interval | The range that likely contains the true difference; if it includes zero, the data show no reliable difference. |",
        "",
        "The three scores use different scales, so compare them across experiments, not across document types.",
        "",
    ]
    out.append(("## How to read the numbers", glossary))

    head = " | ".join(n for _, n in RUNS)
    eff = [f"| Measure | {head} |", "| --- |" + " ---: |" * len(RUNS)]
    eff_rows = (
        ("Documents per minute", lambda q: f"{q['docs_per_minute']:.1f}"),
        ("Tokens per second per GPU", lambda q: f"{q['tps_per_gpu']:,.0f}"),
        ("GPU cost per document", lambda q: _usd(q["usd_per_document"], 5)),
        ("Failed documents", lambda q: f"{q['errors']} of {q['documents']}"),
    )
    for label, fn in eff_rows:
        eff.append(f"| {label} | " + " | ".join(fn(pooled[k]) if pooled.get(k) else "—" for k, _ in RUNS) + " |")
    eff += [""]
    if f["errors_all_length"]:
        eff += ["Every failure was an answer cut off at the output length limit, all on contracts or merger "
                "agreements (the longest documents).", ""]
    if pooled.get("s40-2l4"):
        eff += ["Experiment 4's cost and throughput include the slower, more thorough merger-agreement settings; "
                "the like-for-like batch-size comparison is in Key finding 2.", ""]
    out.append(("## Speed and cost by experiment", eff))

    per_type = [f"Scores by document type (0–1, higher is better):", "", f"| Document type | Measure | {head} |",
                "| --- | --- |" + " ---: |" * len(RUNS)]
    for t in gm._ORDER:
        vals = []
        for k, _ in RUNS:
            c = cards[k].get(t)
            if not c:
                vals.append("—")
            elif t == "merger_agreement":
                cl = c["quality"].get("clause") or {}
                vals.append(f"{cl.get('accuracy', 0):.3f}" + ("*" if k == "s40-2l4" else ""))
            elif t == "contracts":
                vals.append(f"{(c['quality'].get('clause') or {}).get('f1', 0):.3f}")
            else:
                vals.append(f"{c['quality']['overall_mean']:.3f}")
        per_type.append(f"| {gm._LABEL[t]} | {_SCORE_TEXT[t]} | " + " | ".join(vals) + " |")
    per_type += ["", "\\* Experiment 4 uses the improved merger-agreement settings.", "",
                 "Cost per successfully processed document (US dollars):", "",
                 f"| Document type | {head} |", "| --- |" + " ---: |" * len(RUNS)]
    for t in gm._ORDER:
        vals = [_usd(cards[k][t]["cost"]["usd_per_ok_document"], 5) if cards[k].get(t) else "—" for k, _ in RUNS]
        per_type.append(f"| {gm._LABEL[t]} | " + " | ".join(vals) + " |")
    per_type += ["", "Median seconds per document:", "",
                 f"| Document type | {head} |", "| --- |" + " ---: |" * len(RUNS)]
    for t in gm._ORDER:
        vals = [f"{cards[k][t]['latency']['p50']:,.0f}" if cards[k].get(t) else "—" for k, _ in RUNS]
        per_type.append(f"| {gm._LABEL[t]} | " + " | ".join(vals) + " |")
    per_type.append("")
    out.append(("## Results by document type", per_type))

    if "merger" in f:
        from mailroom_sandbox.job.specialist_posture import posture_for_run

        (_, base_id), (_, opt_id) = gm._SETTINGS_RUNS
        base, opt = posture_for_run(base_id) or {}, posture_for_run(opt_id) or {}
        m = f["merger"]
        merger = [
            f"Merger agreements are long: the median agreement in the sample runs to hundreds of thousands of "
            f"characters, while the standard settings read only the first and last "
            f"{int(base.get('max_input_chars', 0)):,} characters combined. In Experiment 4 we changed the settings for "
            f"this document type only, on the same {m['n']} agreements as Experiment 3:",
            "",
            "| Setting | Standard (Experiments 1–3) | Improved (Experiment 4) |",
            "| --- | --- | --- |",
            "| What the model reads | Start and end of the agreement; the middle is skipped | The whole "
            f"agreement, in overlapping sections of about {int(opt.get('chunk_chars', 0)):,} characters, with "
            "answers combined |",
            "| Instructions | General extraction instructions | Instructions written around the MAUD question set |",
            f"| Output length limit | {int(base.get('max_tokens', 0)):,} tokens | "
            f"{int(opt.get('max_tokens', 0)):,} tokens, with one retry if an answer is cut off |",
            f"| Sampling | {gm._sampling_text(base)} | {gm._sampling_text(opt)} |",
            f"| Question accuracy | {m['acc_before']:.1%} | {m['acc_after']:.1%} |",
            f"| Questions answered | {m['cov_before']:.0%} | {m['cov_after']:.0%} |",
            f"| Agreements returning a result | {m['ok_before']} of {m['n']} | {m['ok_after']} of {m['n']} |",
            f"| Cost per agreement | {_usd(m['cost_before'])} | {_usd(m['cost_after'])} |",
            f"| Median time per agreement | {m['lat_before']:,.0f} s | {m['lat_after']:,.0f} s |",
            "",
        ]
        if m["matched"]:
            delta, n, better, worse = m["matched"]
            merger += [
                f"On the {n} agreements scored under both settings, {better} improved and {worse} got worse "
                f"(average change {delta:+.3f} on the 0–1 scale). Several settings changed together, so this "
                "run does not show which change drove the gain.",
                "",
            ]
        out.append(("## Merger agreements: what changed", merger))

    if f["cost_rows"]:
        cost = [
            "GPU cost counts only the time the GPUs spent on documents. Session cost is the provider's "
            "metered charge for the whole session, including start-up, waiting between runs and shut-down.",
            "",
            "| Experiments | Documents | GPU cost on documents | Session cost | Share of session spent on documents | Session cost per document | Billed |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        tot = {"docs": 0, "busy": 0.0, "metered": 0.0, "billed": 0.0}
        for r in f["cost_rows"]:
            for k2 in tot:
                tot[k2] += r[k2]
            cost.append(_cost_line(r["label"], r["docs"], r["busy"], r["metered"], r["billed"]))
        if len(f["cost_rows"]) > 1:
            cost.append(_cost_line("**All experiments**", tot["docs"], tot["busy"], tot["metered"], tot["billed"]))
        cost += [
            "",
            "Billed is zero because the provider's monthly free credits covered the charges. Session costs "
            "exclude short exploratory test deployments run between the main runs.",
            "",
        ]
        if f["unmetered"]:
            cost += [f"Session cost not yet recorded for {', '.join(f['unmetered'])}.", ""]
        out.append(("## Total cost", cost))

    limits = [
        "- **One sample per run.** Each run used one random draw of 20–100 documents per type; small "
        "differences between experiments may be noise.",
        "- **Hardware and load changed together.** Going from 1 to 2 GPUs also raised the number of documents "
        "processed at once (8 to 32), so the speed gain cannot be split between the two.",
        "- **Some outputs vary between runs.** Contracts and merger agreements are generated with some "
        "randomness (temperature 0.7), so repeated runs give slightly different answers.",
        "- **Strict format checks.** Most insurance-claim outputs did not pass strict data-format validation "
        "even though their extraction scores are the highest; a system that rejects malformed records would "
        "need that fixed first.",
        "- **Public data only.** Results describe this public dataset; performance on other document "
        "collections has not been measured.",
        "",
    ]
    out.append(("## Limitations", limits))

    xref = [
        "For readers comparing against the project's internal records:",
        "",
        "| Experiment | Internal shorthand |",
        "| --- | --- |",
    ]
    for k, name in RUNS:
        p = by_key[k]
        xref.append(f"| {name} | {p.label} |")
    xref += [
        "",
        "Shorthand key: `2×L4` = two NVIDIA L4 GPUs; `C32` = 32 documents processed at once; `n=100` = "
        "documents per type. Detailed tables and charts: `SAND-37-MASTER-APPENDIX.md` in the project repository.",
        "",
    ]
    out.append(("## Experiment cross-reference", xref))
    return out


def _cost_line(label: str, docs: int, busy: float, metered: float, billed: float) -> str:
    share = f"{busy / metered:.0%}" if metered else "—"
    per = f"${metered / docs:.4f}" if docs else "—"
    return f"| {label} | {docs:,} | ${busy:.2f} | ${metered:.2f} | {share} | {per} | ${billed:.2f} |"


def render_reader_md(data: Mapping[str, Any]) -> str:
    lines: list[str] = []
    for heading, body in _sections(data):
        if heading:
            lines += [heading, ""]
        lines += body
    return "\n".join(lines).rstrip() + "\n"


# --- notebook ---------------------------------------------------------------------------

def _chart_rows(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    cards = data["cards"]
    rows = []
    for k, name in RUNS:
        p = next(x for x in gm.POSTURES if x.key == k)
        q = gm._pooled(cards[k], p.replicas) if cards[k] else None
        for t in gm._ORDER:
            c = cards[k].get(t)
            if not c:
                continue
            cl = c["quality"].get("clause") or {}
            score = (cl.get("accuracy") if t == "merger_agreement"
                     else cl.get("f1") if t == "contracts" else c["quality"]["overall_mean"])
            rows.append({
                "run": name, "doc_type": gm._LABEL[t], "score": round(score or 0.0, 4),
                "cost_per_doc": round(c["cost"]["usd_per_ok_document"], 6),
                "median_seconds": round(c["latency"]["p50"], 1),
                "run_docs_per_min": round(q["docs_per_minute"], 2) if q else None,
                "run_cost_per_doc": round(q["usd_per_document"], 6) if q else None,
            })
    return rows


_CHART_SETUP = """import pandas as pd
import matplotlib.pyplot as plt

COLORS = {colors}
df = pd.DataFrame({rows})
plt.rcParams.update({{"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False}})
df.head()"""

_CHART_SPEED = """runs = df.drop_duplicates("run").set_index("run")
fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
axes[0].bar(runs.index, runs["run_docs_per_min"], color=[COLORS[r] for r in runs.index])
axes[0].set_title("Documents per minute (higher is better)")
axes[1].bar(runs.index, runs["run_cost_per_doc"] * 100, color=[COLORS[r] for r in runs.index])
axes[1].set_title("GPU cost per document, cents (lower is better)")
for ax in axes:
    ax.set_xticks(range(len(runs)), [r.removeprefix("Experiment ") for r in runs.index])
    ax.set_xlabel("Experiment")
fig.tight_layout()"""

_CHART_QUALITY = """pivot = df.pivot(index="doc_type", columns="run", values="score")
ax = pivot.plot.barh(figsize=(9, 4), color=[COLORS[r] for r in pivot.columns], width=0.8)
ax.set_xlabel("Score (0-1; scales differ by document type)")
ax.set_ylabel("")
ax.set_title("Accuracy by document type and experiment")
ax.legend(title="", loc="lower right")
plt.tight_layout()"""


def _png_output(code: str, env: dict[str, Any]) -> list[dict[str, Any]]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    exec(code, env)  # noqa: S102 - our own chart code, rendered once so the notebook opens with figures
    buf = io.BytesIO()
    plt.gcf().savefig(buf, format="png", bbox_inches="tight")
    plt.close("all")
    return [{"output_type": "display_data", "metadata": {},
             "data": {"image/png": base64.b64encode(buf.getvalue()).decode("ascii"), "text/plain": ["<Figure>"]}}]


def render_reader_ipynb(data: Mapping[str, Any]) -> str:
    def md(text: str) -> dict[str, Any]:
        return {"cell_type": "markdown", "metadata": {}, "source": text.rstrip("\n").splitlines(keepends=True)}

    def code(src: str, outputs: list[dict[str, Any]]) -> dict[str, Any]:
        return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": outputs,
                "source": src.splitlines(keepends=True)}

    cells = []
    for heading, body in _sections(data):
        cells.append(md("\n".join(([heading, ""] if heading else []) + body)))
        if heading == "## Speed and cost by experiment":
            rows = _chart_rows(data)
            setup = _CHART_SETUP.format(colors=json.dumps(CHART_COLORS), rows=json.dumps(rows, indent=1))
            env: dict[str, Any] = {}
            exec(setup.rsplit("\n", 1)[0], env)  # noqa: S102 - builds df for the chart cells below
            cells.append(md("The charts below are drawn from this data table (re-run the cells to edit them)."))
            cells.append(code(setup, []))
            cells.append(code(_CHART_SPEED, _png_output(_CHART_SPEED, env)))
        if heading == "## Results by document type":
            cells.append(code(_CHART_QUALITY, _png_output(_CHART_QUALITY, env)))
    nb = {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    for i, c in enumerate(nb["cells"]):
        c["id"] = f"cell-{i:02d}"
    return json.dumps(nb, indent=1, ensure_ascii=False) + "\n"


def write_reader(repo: Path | None = None, *, pdf: bool = True) -> dict[str, Path | None]:
    """Write the Markdown and notebook, then the typeset PDF (``None`` when Chrome is unavailable)."""
    from mailroom_sandbox.job.grid_reader_pdf import write_pdf

    data = gm.collect_master(repo)
    paths: dict[str, Path | None] = dict(reader_paths(repo))
    paths["md"].write_text(render_reader_md(data), encoding="utf-8")
    paths["ipynb"].write_text(render_reader_ipynb(data), encoding="utf-8")
    paths["pdf"] = write_pdf(repo, data) if pdf else None
    return paths
