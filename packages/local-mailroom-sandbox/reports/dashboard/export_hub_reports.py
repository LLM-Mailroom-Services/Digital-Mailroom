#!/usr/bin/env python3
"""Write the cross-repo cost comparison and master reports for the mailroom-issues hub.

LLM-Mailroom-Services/mailroom-issues holds no code (its law #1), so the
generator lives here, next to the hub extractor whose cross-checked figures it
reads. Only the outputs (markdown + SVG) are committed to the hub.

    python reports/dashboard/build_hub.py sync        # re-pin eval-environment + mailroom-ml
    python reports/dashboard/build_hub.py             # rebuild hub_data.json
    python reports/dashboard/export_hub_reports.py --out ../mailroom-issues/reports
    python reports/dashboard/export_hub_reports.py --out ../mailroom-issues/reports --check

Every number comes from ``hub_data.json`` (1,300+ source-quoted figures, 700+
automated cross-checks) or from a tracked serving export in this repo. The GPU
economics report (``MODAL-VLLM-GPU-REPORT.md``) is written by ``gpu_report.py``. Figures
are drawn with the SAND-032 chart kit (``scripts/sand032/viz.py``: validated
palette, light + dark) and each has a table twin in the report. Supporting
figures from the three source repos are copied verbatim with their commit.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import statistics
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "sand032"))
import viz  # noqa: E402

import breakeven  # noqa: E402
import source_charts  # noqa: E402

DATA = HERE / "hub_data.json"
SERVING = ROOT / "reports" / "serving"
SAND32_SERVING = SERVING / "SAND-32"
L4_USD_PER_HOUR = 0.80  # docs/RUN-COST-DERIVATION.md; the rate every SAND-032 $/doc uses
REPLICAS = 2  # SAND-032 class sweep: 2×L4, c32
ORDER = ["correspondence", "insurance_claim", "corporate_record", "contract", "merger_agreement"]
TASK_OF = {"correspondence": "correspondence", "insurance_claim": "insurance claims", "corporate_record": "corporate records",
           "contract": "contracts", "merger_agreement": "merger agreements"}
FAMILY_SHORT = {"Qwen3-8B-AWQ": "Modal · Qwen3-8B-AWQ", "Qwen3.7-Flash": "API · Qwen3.7-Flash", "Qwen3-8B": "API · Qwen3-8B",
                "Qwen3.7-Flash · frozen": "API · Qwen3.7-Flash (frozen prompts)",
                "DeepSeek-V4.1-Flash": "API · DeepSeek-V4.1-Flash", "Granite-4.2-8B": "API · Granite-4.2-8B"}
SORTER_NAME = {"qwen/qwen3.7-flash": "Qwen3.7-Flash", "deepseek/deepseek-v4.1-flash": "DeepSeek-V4.1-Flash",
               "ibm-granite/granite-4.2-8b": "Granite-4.2-8B", "qwen/qwen3-8b": "Qwen3-8B"}

# Figures copied from the sandbox's own SAND-032 set (drawn by the same kit; source path → figures/sources/<repo>/).
COPY = {
    "local-mailroom-sandbox": ["reports/serving/figures/sand032-ladder.svg", "reports/serving/figures/sand032-routing.svg",
                               "reports/serving/figures/sand032-admission.svg", "reports/serving/figures/sand032-v2-prompts.svg",
                               "reports/serving/figures/sand032-s6-sorter1000-per-class-f1.svg"],
}
# The eval-environment and mailroom-ml charts are redrawn from hub data in the same kit (source_charts.py),
# so every report figure shares one dark, high-contrast theme.


# ------------------------------------------------------------------ formatting
def usd(v: float | None) -> str:
    if v is None:
        return "—"
    if v >= 1:
        return f"${v:,.2f}"
    if v >= 0.01:
        return f"${v:.3f}"
    return f"${v:.{max(2, -int(f'{v:e}'.split('e')[1]) + 1)}f}"


def f3(v):
    return "—" if v is None else f"{v:.3f}"


def f4(v):
    return "—" if v is None else f"{v:.4f}"


def pct(v, d=1):
    return "—" if v is None else f"{v * 100:.{d}f}%"


def secs(v):
    return "—" if v is None else (f"{v:,.0f} s" if v >= 100 else f"{v:.1f} s")


def and_list(xs) -> str:
    xs = list(xs)
    return " and ".join(xs) if len(xs) < 3 else ", ".join(xs[:-1]) + " and " + xs[-1]


def api_name(rec: dict) -> str:
    """The model a hosted leg logged (eval-environment files one Qwen3.7-Flash merger leg under Qwen3-8B)."""
    name = SORTER_NAME.get(rec["model"], rec["family"])
    return name if name == rec["family"] else f"{name} · {rec['prompt_lineage']} (filed as {rec['family']})"


def s6_p95() -> str:
    m = re.search(r"latency p50 / p95 s \| [\d.]+ / ([\d.]+)", (SAND32_SERVING / "SAND032-S6-SORTER1000-REPORT.md").read_text())
    return f"{float(m.group(1)):.0f} s" if m else "n/a"


def table(head: list[str], rows: list[list], align: str | None = None) -> str:
    align = align or ("l" + "r" * (len(head) - 1))
    sep = ["---" if a == "l" else "---:" for a in align]
    out = ["| " + " | ".join(head) + " |", "| " + " | ".join(sep) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def git_sha(path: pathlib.Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(path), "rev-parse", "--short=12", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def serving(rid: str) -> dict:
    matches = sorted(SERVING.rglob(f"{rid}.serving.json"))
    if len(matches) > 1:
        raise ValueError(f"multiple serving exports found for {rid}: {matches}")
    p = matches[0] if matches else SAND32_SERVING / f"{rid}.serving.json"
    d = json.loads(p.read_text()) if p.is_file() else {}
    return d.get("metrics", d)


# ------------------------------------------------------------------ analysis
def route_rows(D: dict) -> dict[str, list[dict]]:
    """Per class: the Modal run first, then every hosted-API leg (from build_hub.route_points)."""
    return {c: D["route"]["points"][c] for c in ORDER}


# ------------------------------------------------------------------ figures
def entity_legend(labels) -> list[tuple[str, str]]:
    """Legend keys, in ENTITY order, for the models that appear in ``labels`` (color follows the model)."""
    labels = list(labels)
    names = {"Qwen3-8B-AWQ": "Modal · Qwen3-8B-AWQ", "ModernBERT": "ModernBERT (local)"}
    out = []
    for name, cls in viz.ENTITY.items():
        if any(viz.entity(lab) == cls for lab in labels):
            out.append((cls, names.get(name, f"API · {name}")))
    return out


def fig_cost(D, rows) -> str:
    panels = []
    for c in ORDER:
        pts = sorted(rows[c], key=lambda p: p["usd"])
        labs = [FAMILY_SHORT[p["family"]] for p in pts]
        panels.append(viz.hbar(D["labels"][c], "cost per completed document · lower is better",
                               [{"label": FAMILY_SHORT[p["family"]], "value": round(p["usd"], 6),
                                 "series": viz.entity(FAMILY_SHORT[p["family"]]), "note": f"n = {p['n']} · {p['run']}"} for p in pts],
                               fmt=lambda v: usd(v), width=560, label_w=200, legend=entity_legend(labs)))
    return viz.small_multiples("Cost per document by route and model — Modal L4 (SAND-032) vs hosted API", panels, cols=2)


def fig_score(D, rows) -> str:
    panels = []
    for c in ORDER:
        pts = sorted(rows[c], key=lambda p: -p["score"])
        sub = ("overall extraction score (0–1) · higher is better" if c != "contract"
               else "Modal: CUAD category F1 · API: pipeline rubric — not like-for-like")
        labs = [FAMILY_SHORT[p["family"]] for p in pts]
        panels.append(viz.hbar(D["labels"][c], sub,
                               [{"label": FAMILY_SHORT[p["family"]], "value": round(p["score"], 4),
                                 "series": viz.entity(FAMILY_SHORT[p["family"]]), "note": f"n = {p['n']} · {p['run']}"} for p in pts],
                               fmt=lambda v: f"{v:.3f}", width=560, label_w=200, legend=entity_legend(labs)))
    return viz.small_multiples("Extraction quality by route and model — same tasks, same scorer except contracts", panels, cols=2)


def fig_modal_vs_cheapest(E) -> str:
    return viz.dumbbell("Modal L4 vs the cheapest hosted model, cost per document",
                        "Modal = SAND-032 2×L4 busy-window · API = cheapest hosted model for the class · lower is better",
                        [{"label": r["label"], "a": round(r["modal"]["usd"], 6), "b": round(r["cheap"]["usd"], 6),
                          "api": r["cheap"]["family"]} for r in E["rows"]],
                        ("Modal L4", "cheapest API"), fmt=lambda v: usd(v), label_w=160,
                        val=lambda r: f"Modal {usd(r['a'])} · {r['api']} {usd(r['b'])}")


def fig_sorter(D, sorters) -> str:
    return viz.hbar("Sorter routes: document-type accuracy",
                    "every way the mailroom can sort · cost per document in each bar's hover and the table",
                    [{"label": s["label"], "value": round(s["acc"], 4), "series": viz.entity(s["label"]),
                      "note": f"{usd(s['usd'])} per document · n = {s['n']}"} for s in sorters],
                    fmt=lambda v: f"{v * 100:.1f}%", label_w=230, legend=entity_legend(s["label"] for s in sorters))


def sorters_of(D) -> list[dict]:
    s6 = D["route"]["sorter_modal"]
    out = [{"label": "Modal L4 · Qwen3-8B-AWQ (S6)", "kind": "modal", "acc": s6["acc"], "usd": s6["usd"], "n": int(s6["ok"]),
            "extra": f"macro-F1 {s6['macro_f1']:.4f}"}]
    # every hosted model's largest sorter run (Qwen3-8B only ran at n = 20)
    largest = {}
    for r in D["api"]["classification"]:
        if r["n"] > largest.get(r["model"], {}).get("n", 0):
            largest[r["model"]] = r
    for r in sorted(largest.values(), key=lambda r: -r["class_acc"]):
        name = SORTER_NAME.get(r["model"], r["model"])
        ece = (D["api"]["sorter"].get(r["model"]) or {}).get("ece") if r["n"] >= 100 else None
        out.append({"label": f"API · {name}" + (f" (n = {r['n']})" if r["n"] < 100 else ""), "kind": "api", "acc": r["class_acc"], "usd": r["cost"] / r["n"], "n": r["n"],
                    "extra": f"subclass {pct(r['subclass_acc'], 0)} · ECE {f3(ece)}"})
    mb = D["mb"]
    out.append({"label": "ModernBERT · Arm B (local)", "kind": "classifier", "acc": mb["armB"]["acc"],
                "usd": mb["run3_reeval"]["sorter"]["mb_usd"], "n": mb["armB"]["n"],
                "extra": f"subclass {pct(mb['armB']['subclass'])} · window ECE {mb['armB']['window_ece']}"})
    return out


# ------------------------------------------------------------------ break-even (numbers from breakeven.analyze)
def fleet_of(m: dict) -> str:
    return f"{m['replicas']}×L4"


def v2_verdict(cls: str) -> dict | None:
    """The v2 prompt-promotion verdict for a class, as its report states it."""
    for r in v2_rows():
        if r[0] == cls:
            return {"delta": r[4].strip("*"), "verdict": r[7].strip("*")}
    return None


def optimal_sentence(E) -> str:
    o = E["optimal"]
    if not o:
        return "No measured Modal configuration is both cheaper than and at least as good as the cheapest hosted model."
    m, a = o["modal"], o["cheap"]
    return (f"Run {o['label'].lower()} on self-hosted {m['model']} (Modal): the measured {fleet_of(m)} configuration `{m['run']}` "
            f"({m['prompts']} prompts) costs {usd(m['usd'])} per document against {a['family']} via the API at {usd(a['usd'])}, "
            f"{pct(o['save_pct'], 0)} less, and scores "
            f"{m['score']:.3f} against {a['score']:.3f}. It pays once one warm L4 sustains {o['l4x1']['docs_h_star']:,.0f} docs/h "
            f"or a cold batch holds {o['l4x1']['batch_star']:,} documents.")


def same_model_title(E) -> str:
    return f"{E['rows'][0]['modal']['model']} on Modal vs {breakeven.SAME_MODEL_API} via the API"


def same_model_block(E) -> str:
    rows = [r for r in E["rows"] if r["same"]]
    missing = [r["label"].lower() for r in E["rows"] if not r["same"]]
    body = [[r["label"], f"`{r['modal']['run']}`", usd(r["modal"]["usd"]), f3(r["modal"]["score"]),
             usd(r["same"]["api"]["usd"]), f3(r["same"]["api"]["score"]), f"{r['same']['ratio']:.2f}×",
             f"{1 / r['same']['ratio']:.1f}×", f"{r['same']['l4x1']['docs_h_star']:,.0f}" if r["same"]["cheaper"] else "never",
             f"{r['same']['l4x1']['batch_star']:,}" if r["same"]["cheaper"] else "never"] for r in rows]
    cheaper = [r for r in rows if r["same"]["cheaper"]]
    lo = min(1 / r["same"]["ratio"] for r in cheaper) if cheaper else None
    hi = max(1 / r["same"]["ratio"] for r in cheaper) if cheaper else None
    read = (f"Self-hosting the same model is {lo:.1f}–{hi:.1f}× cheaper per document than renting it through the API on "
            f"{and_list(r['label'].lower() for r in cheaper)}. A warm fleet breaks even at {pct(min(r['same']['ratio'] for r in cheaper), 0)}–"
            f"{pct(max(r['same']['ratio'] for r in cheaper), 0)} busy. "
            if cheaper else "")
    note = (f" The API leg has no {breakeven.SAME_MODEL_API} run for {and_list(missing)}." if missing else "")
    return (f"{table(['Class', 'Modal run', 'Modal $/doc', 'Modal score', f'API {breakeven.SAME_MODEL_API} $/doc', 'API score', 'Modal ÷ API', 'API ÷ Modal', 'Warm 1×L4 break-even docs/h', 'Cold batch ≥ N (1×L4)'], body, 'llrrrrrrrr')}\n\n"
            f"{read}Both legs ran the production prompt set (on the API, eval-environment's frozen copy of it). The scores still differ because Modal serves the 4-bit AWQ "
            f"quantization and the two legs drew different documents from different dataset revisions (§6).{note}")


def breakeven_section(D, E) -> str:
    rate, c1, c2 = E["rate"], E["rows"][0]["l4x1"]["cycle_usd"], E["rows"][0]["l4x2"]["cycle_usd"]
    dag = "†"

    def mark(x, n_l4, v):
        return f"{v}{dag}" if x[f"l4x{n_l4}"]["projected"] else v

    verdicts = [[r["label"], f"`{r['modal']['run']}` · {fleet_of(r['modal'])}", usd(r["modal"]["usd"]), f3(r["modal"]["score"]),
                 r["cheap"]["family"], usd(r["cheap"]["usd"]), f3(r["cheap"]["score"]), f"{r['ratio']:.2f}×",
                 usd(r["save_1k"]) if r["cheaper"] else f"−{usd(-r['save_1k'])}", breakeven.verdict(r)] for r in E["rows"]]
    cfgs = [[x["label"], f"`{x['modal']['run']}`", fleet_of(x["modal"]), x["modal"]["prompts"], usd(x["modal"]["usd"]),
             f3(x["modal"]["score"]), f"{x['ratio']:.2f}×", breakeven.verdict(x)] for x in E["configs"]]
    vol = []
    for r in E["rows"]:
        pick = E["pick"][r["cls"]]
        if not pick["cheaper"]:
            floor = pick
            vol.append([r["label"], f"`{floor['modal']['run']}`", f"never: Modal floor is {floor['ratio']:.2f}× the API"] + ["—"] * 5)
            continue
        w1, w2 = pick["l4x1"], pick["l4x2"]
        vol.append([r["label"], f"`{pick['modal']['run']}`",
                    f"{w1['docs_h_star']:,.0f} ({pct(pick['ratio'], 0)} busy)", mark(pick, 1, f"{w1['cap_docs_h']:,.0f}"),
                    f"{w2['docs_h_star']:,.0f} ({pct(pick['ratio'], 0)} busy)", mark(pick, 2, f"{w2['cap_docs_h']:,.0f}"),
                    f"{w1['batch_star']:,}", f"{w2['batch_star']:,}"])
    o = E["optimal"]
    s = E["sorter"]
    lines = []
    if o:
        m, a = o["modal"], o["cheap"]
        lines.append(f"- **Optimal: {o['label'].lower()} on self-hosted {m['model']}, {fleet_of(m)}** (`{m['run']}`, {m['prompts']} prompts). "
                     f"{usd(m['usd'])} per document against {a['family']} via the API at {usd(a['usd'])}: {pct(o['save_pct'], 0)} cheaper, "
                     f"{usd(o['save_1k'])} saved per 1,000 documents, at a score of {m['score']:.3f} against {a['score']:.3f}.")
        lines.append(f"  - **Warm:** one L4 (${rate:.2f}/h) beats the API from {o['l4x1']['docs_h_star']:,.0f} docs/h sustained "
                     f"({pct(o['ratio'], 0)} busy) up to its measured {o['l4x1']['cap_docs_h']:,.0f} docs/h"
                     f"{dag if o['l4x1']['projected'] else ''}. Above that, a second L4 keeps the same $/doc; its break-even "
                     f"is {o['l4x2']['docs_h_star']:,.0f} docs/h.")
        lines.append(f"  - **Cold:** scale-to-zero batches beat the API from {o['l4x1']['batch_star']:,} documents per start on 1×L4 "
                     f"({o['l4x2']['batch_star']:,} on 2×L4).")
        lines.append("  - **Below both thresholds** the hosted model is cheaper: idle GPU hours or the cold cycle cost more than the "
                     "per-document saving.")
        v2 = v2_verdict(o["cls"]) if m["prompts"] == "v2" else None
        if v2:
            prod = min((x for x in E["wins"] if x["cls"] == o["cls"] and x["modal"]["prompts"] == "production"),
                       key=lambda x: x["modal"]["usd"], default=None)
            alt = (f" On the production prompts the best winning configuration is `{prod['modal']['run']}` at "
                   f"{usd(prod['modal']['usd'])} per document ({pct(prod['save_pct'], 0)} cheaper, score {prod['modal']['score']:.3f})."
                   if prod else "")
            lines.append(f"  - **Prompt caveat:** the v2 {o['label'].lower()} prompt was marked {v2['verdict']} in the v2 promotion run "
                         f"(paired Δ {v2['delta']} against production).{alt}")
    for r in E["cost_only"]:
        best = min((x for x in E["configs"] if x["cls"] == r["cls"] and x["cheaper"]), key=lambda x: x["modal"]["usd"])
        lines.append(f"- **Cheaper but lower quality: {r['label'].lower()}.** Modal saves up to {pct(best['save_pct'], 0)} per document "
                     f"(`{best['modal']['run']}`), but its best score here is "
                     f"{max((x['modal']['score'] or 0) for x in E['configs'] if x['cls'] == r['cls']):.3f} against "
                     f"{r['cheap']['family']}'s {r['cheap']['score']:.3f}. Take it only where that quality gap is acceptable.")
    for r in E["never"]:
        floor = min((x for x in E["configs"] if x["cls"] == r["cls"]), key=lambda x: x["modal"]["usd"])
        why = " (and the two legs are scored differently)" if not r["comparable"] else ""
        lines.append(f"- **Never on Modal: {r['label'].lower()}.** The cheapest measured configuration costs {floor['ratio']:.2f}× "
                     f"{r['cheap']['family']} per document even when fully busy{why}, so no volume or batch size recovers it.")
    lines.append(f"- **Sorter.** The Modal LLM sorter (S6) costs {s['ratio']:.2f}× the cheapest hosted sorter "
                 f"({SORTER_NAME.get(s['cheap']['family'], s['cheap']['family'])}, {usd(s['cheap']['usd'])}) at "
                 f"{pct(s['modal']['score'])} against {pct(s['cheap']['score'])} accuracy. ModernBERT costs {usd(s['modernbert']['usd'])} "
                 f"per document at {pct(s['modernbert']['score'])}, so neither LLM route is the sorter to deploy.")
    return f"""## 3. When does Modal pay off? Break-even and the optimal scenario

Every comparison here is **per completed document**, because that is what the mailroom pays for.

**Which model runs where.** The only model self-hosted on Modal is **{E['rows'][0]['modal']['model']}** (vLLM, 4-bit AWQ). Every hosted model, including the pipeline's production model Qwen3.7-Flash, ran only through the API. §3.1 and §3.3–3.5 therefore compare Modal against the cheapest hosted *model*, which is a different model; §3.2 holds the model fixed and compares only the route.

- **Modal $/doc** is the measured busy-window GPU cost of the run: replicas × ${rate:.2f} per L4-hour × wall time ÷ documents.
- **API $/doc** is list price × the tokens each leg recorded.
- **Why per-token prices rank the routes differently** ([GPU report §3](MODAL-VLLM-GPU-REPORT.md#3-cost-per-token)): each leg sends its own prompts, so one document costs a different number of tokens on each route. Per document is the comparison that decides deployment.

Three measured quantities turn that per-document floor into a deployment decision:

- **A warm fleet** bills ${rate:.2f} per L4-hour whether it is busy or not.
- **A cold start** bills the L5 boot ({E['boot']:.0f} s deploy → ready) plus the {E['scaledown']:.0f} s scale-down tail on every replica: {usd(c1)} on 1×L4 and {usd(c2)} on 2×L4.
- **A second L4** doubles throughput at a flat cost per document: S2a ${E['s2a']:.6f} vs S2b ${E['s2b']:.6f} on the same 100 documents. A 1×L4 fleet therefore serves at the same $/doc for half the $/h.

Cells marked {dag} apply that measured result to a fleet size the class was not run on.

**Modal wins** where it is cheaper per document than the cheapest hosted model *and* scores at least as well as that model, so replacing it loses nothing. It becomes cheaper at either of two break-evens:

- **Warm fleet:** a sustained load of at least fleet $/h ÷ API $/doc documents per hour, which is a busy share of at least Modal $/doc ÷ API $/doc.
- **Cold batch:** at least cold cycle ÷ (API $/doc − Modal $/doc) documents per start.

### 3.1 Verdict per class (the scored run in §2)

{table(["Class", f"Modal ({E['rows'][0]['modal']['model']}) run · fleet", "Modal $/doc", "Modal score", "Cheapest API", "API $/doc", "API score", "Modal ÷ API", "Saved per 1,000 docs", "Verdict"], verdicts, "llrrlrrrrl")}

### 3.2 Same model, two routes: {same_model_title(E)}

{same_model_block(E)}

### 3.3 Every measured Modal configuration against the cheapest API

Each row's score comes from its own run report. Runs that are not deployable configurations (the ladder rungs, the bf16 control, and the S7 runs whose router sent nearly every request to one replica) are left out.

{table(["Class", "Run", "Fleet", "Prompts", "$/doc", "Score", "÷ cheapest API", "Verdict"], cfgs, "llllrrrl")}

### 3.4 Break-even volumes

Each class uses its deciding configuration: the cheapest one that wins, else the cheapest one that undercuts the API, else the cheapest one. The chart draws the same configurations.

{table(["Class", "Configuration", "Warm 1×L4 break-even docs/h", "1×L4 capacity docs/h", "Warm 2×L4 break-even docs/h", "2×L4 capacity docs/h", "Cold batch ≥ N (1×L4)", "Cold batch ≥ N (2×L4)"], vol, "llrrrrrr")}

![Modal cost per document relative to the cheapest API](figures/cost/modal-vs-api-breakeven.svg)

### 3.5 The optimal scenario

{chr(10).join(lines)}"""


# ------------------------------------------------------------------ reports
def cost_report(D, rows, E, sorters, shas) -> str:
    T = D["text"]
    head = ["Task", "Route · model", "n", "Score", "$/doc", "$ per 1k docs", "Run", "Revision"]
    body = []
    for c in ORDER:
        for p in sorted(rows[c], key=lambda p: p["usd"]):
            body.append([D["labels"][c], FAMILY_SHORT[p["family"]], p["n"], f4(p["score"]), usd(p["usd"]),
                         usd(p["usd"] * 1000), f"`{p['run']}`", p["revision"]])
    eff = []
    for c in ORDER:
        for p in sorted(rows[c], key=lambda p: p["usd"] / max(p["score"], 1e-9)):
            eff.append([D["labels"][c], FAMILY_SHORT[p["family"]], f4(p["score"]), usd(p["usd"]),
                        usd(p["usd"] / max(p["score"], 1e-9) * 0.1) if p["score"] > 0 else "—"])
    srows = [[s["label"], s["n"], pct(s["acc"], 1), usd(s["usd"]), s["extra"]] for s in sorters]
    ladder = [[r["rung"], r["change"], f4(r["score"]), secs(r["wall"]), f"{r['tps']:,.0f}", usd(r["usd"]),
               "—" if r["boot"] is None else f"{r['boot']:.0f} s", r["gate"]] for r in D["ladder"]]
    sp = D["spend"]
    legacy = [[s["b"], usd(s["v"]), s["d"]] for s in sp["legacy"]]
    cheaper = [r["label"].lower() for r in E["rows"] if r["cheaper"]]
    dearer = [r["label"].lower() for r in E["rows"] if not r["cheaper"]]
    return f"""# Cost comparison — Modal L4 (vLLM) vs hosted API

_Data {T['date_range']} · generated by sandbox `reports/dashboard/export_hub_reports.py` from the cross-checked reports hub · sources: {shas}_

**Bottom line.**

- Per document, the self-hosted Qwen3-8B-AWQ specialists on Modal L4 are cheaper than every hosted model for {and_list(cheaper) or 'no class'}.
- They cost more than the cheapest hosted model for {and_list(dearer) or 'no class'}.
- Quality is the stronger argument against Modal today: {T['route_head'].split('; ')[1]}.
- The sorter is decided on cost: ModernBERT matches the best hosted LLM sorter's document-type accuracy at about three orders of magnitude lower cost per document.

![Cost per document by route and model](figures/cost/cost-per-doc.svg)

![Modal vs the cheapest hosted model](figures/cost/modal-vs-cheapest-api.svg)

## 1. How each route is costed

| | Modal L4 · vLLM (sandbox, SAND-032) | Hosted API · OpenRouter (eval-environment) |
| --- | --- | --- |
| Model | Qwen3-8B-AWQ, the only model self-hosted: frozen L5 posture (awq_marlin, fp8 KV, thinking off, CUDA graphs) | API only, never self-hosted: Qwen3.7-Flash (the pipeline's production model), Qwen3-8B, DeepSeek-V4.1-Flash, Granite-4.2-8B |
| Unit price | ${L4_USD_PER_HOUR:.2f} per L4-hour, {REPLICAS}×L4 = ${REPLICAS * L4_USD_PER_HOUR:.2f}/h | OpenRouter list price × recorded prompt/completion tokens |
| Cost per document | busy-window GPU time ÷ completed documents (excludes cold boot and idle) | run cost total ÷ scored documents |
| Fixed cost | cold cycle = L5 boot ({E['boot']:.0f} s deploy→ready) + scale-down tail ({E['scaledown']:.0f} s) per replica = {usd(E['rows'][0]['l4x1']['cycle_usd'])} on 1×L4, {usd(E['rows'][0]['l4x2']['cycle_usd'])} on 2×L4 | none |
| Draw | 50 documents per class, `mailroom-dataset` revision `ed7576b6` | 20 per class (Qwen3.7-Flash: 50), revision `46a4d3c2`, train split |

Busy-window pricing is a **floor** for bursty traffic (every scale-up pays the boot, idle replicas are not counted) and close to the true price for a steady queue. Draws, dataset revisions and prompts differ between the legs. See §6.

## 2. Cost and quality per task

{table(head, body, "llrrrrll")}

![Extraction quality by route and model](figures/cost/score-by-route.svg)

**Cost per 0.1 of quality** (lower is better; $/doc ÷ score × 0.1). This shows what each route pays for the same quality increment:

{table(["Task", "Route · model", "Score", "$/doc", "$ per 0.1 score"], eff, "llrrr")}

{breakeven_section(D, E)}

## 4. Sorter routes

{table(["Route", "n", "Doc-type accuracy", "$/doc", "Detail"], srows, "lrrrl")}

![Sorter routes](figures/cost/sorter-routes.svg)

**Reading.**

- {T['route_sorter_head']}.
- The Modal-hosted LLM sorter (S6, {T['route_s6_acc']} on 457 documents) {'is the most expensive route at' if max(sorters, key=lambda s: s['usd'])['kind'] == 'modal' else 'costs'} {T['route_s6_usd']}/doc (busy-window basis). Its long-document tail (p95 {s6_p95()}) dominates the GPU time.
- ModernBERT's cost is the run-3 GPU estimate per document. Its fast path takes {pct(D['mb']['armB']['fast_path'])} of documents; the rest still go to an LLM sorter.

## 5. What the Modal leg cost, and what tuning bought

The serving ladder (1×L4, correspondence n = 20, same documents every rung):

{table(["Rung", "Change", "Score", "Wall", "tok/s", "$/doc", "Boot", "Gate"], ladder, "llrrrrrl")}

- The L5 posture cut wall time and cost per document by {T['l5_wall_cut']} / {T['l5_usd_cut']} at equal quality.
- A second L4 halved wall time at flat cost per document ({T['scale_usd_a']} vs {T['scale_usd_b']}).
- Cost per document fell {T['cost_red_lo']}–{T['cost_red_hi']}× against the 25–27 Sep runs.

**Spend.**

- SAND-032 used {usd(sp['sand032'])} of its {usd(sp['cap'])} cap (fleet-window ledger at close; {usd(sp['stage5'])} after stages 1–5). That includes a {usd(sp['incident'])} aborted sorter run. The ledger under-counts Modal billing; [MODAL-VLLM-GPU-REPORT.md](MODAL-VLLM-GPU-REPORT.md) breaks it down.
- Earlier tracked spend (16–27 Sep) totals {usd(sp['legacy_total'])}. Modal usage was credit-covered.

{table(["Bucket", "USD", "Detail"], legacy, "lrl")}

## 6. Caveats

- **Draws differ.** Modal: 50 documents per class on revision `ed7576b6` (split all). API: 20 per class (Qwen3.7-Flash 50) on `46a4d3c2`, train split. The per-class means are comparable in scale, not paired.
- **Prompts differ.** The Qwen3.7-Flash legs ran eval-environment's mutated lineage. The other API legs and the Modal runs ran the frozen production prompts, and the Modal merger run used the MAUD prompt.
- **Contracts are not like-for-like.** The Modal point is per-document CUAD category-presence F1. The pipeline rubric returns no score on label-native CUAD ground truth, so the API points use that rubric instead.
- **Busy-window Modal cost is a floor.** The MAUD merger run's summary row, which includes its 122.8 s boot, is 28% higher than its run report. This is documented as a hub data-quality issue.
- **eval-environment files one merger leg under Qwen3-8B**, but the logged model is `qwen/qwen3.7-flash` with the frozen prompts. These reports label it by the logged model ('API · Qwen3.7-Flash (frozen prompts)'), so there is no Qwen3-8B merger point.

## Sources

{sources_block(D, shas)}

Regenerate: in `Exios66/local-mailroom-sandbox`, run `python reports/dashboard/build_hub.py sync && python reports/dashboard/build_hub.py && python reports/dashboard/export_hub_reports.py --out <mailroom-issues>/reports`.
"""


def s6_per_class() -> list[list[str]]:
    text = (SAND32_SERVING / "SAND032-S6-SORTER1000-REPORT.md").read_text()
    sec = text.split("## Per-class", 1)[1].split("## ", 1)[0]
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in sec.splitlines() if ln.startswith("| ")]
    return [r for r in rows[1:] if not set("".join(r)) <= set("-: ")]


def v2_rows() -> list[list[str]]:
    text = (SAND32_SERVING / "SAND032-V2-PROMPT-PROMOTION.md").read_text()
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in text.splitlines() if ln.startswith("| ")]
    return [r for r in rows[1:] if not set("".join(r)) <= set("-: ")]


def sources_block(D, shas) -> str:
    return "\n".join(f"- `{k}` @ `{v[:12] if v != 'this commit' else shas.split('sandbox @ ')[-1].split(' ')[0]}`"
                     for k, v in D["sources"].items())


def master_report(D, rows, E, sorters, audit: dict, shas) -> str:
    T, R, mb = D["text"], D["runs"], D["mb"]
    ST = source_charts.tables(D)  # the table view of each redrawn chart
    api_rows = []
    for c in ORDER:
        task = TASK_OF[c]
        for key, rec in D["api"]["tasks"][task].items():
            api_rows.append([D["labels"][c], api_name(rec), rec["n"], f4(rec["score"]), usd(rec["cost"] / rec["n"]),
                             secs(rec["wall"]), secs(rec["p95_ms"] / 1000), f"`{rec['run']}`"])
        q = D["api"]["route50"][task]
        api_rows.append([D["labels"][c], "Qwen3.7-Flash (n = 50)", q["n"], f4(q["score"]), usd(q["cost"] / q["n"]),
                         secs(q["wall"]), secs(q["p95_ms"] / 1000), f"`{q['run']}`"])
    cls_rows = [[r["run"], SORTER_NAME.get(r["model"], r["model"]), r["n"], pct(r["class_acc"], 0), pct(r["subclass_acc"], 0),
                 usd(r["cost"] / r["n"]), f3((D["api"]["sorter"].get(r["model"]) or {}).get("ece")) if r["n"] >= 100 else "—"]
                for r in D["api"]["classification"]]
    sweep = []
    for c in ORDER:
        r = R[D["s3"][c]]
        sweep.append([r["label"], f"`{r['run']}`", f"{r['ok']}/{r['n']}", r["metric"], f4(r["headline"]),
                      f4(r["overall"]), pct(r["schema"], 0), secs(r["wall"]), f"{r['p50']:.1f} / {r['p95']:.1f} s",
                      f"{r['tps']:,.0f}", usd(r["usd_per_doc"])])
    scale = []
    for rid, lab in (("sand032-s2a-corr100-1rep", "1×L4 · c8"), ("sand032-s2b-corr100-2rep", "2×L4 · c16")):
        r = R[rid]
        scale.append([lab, secs(r["wall"]), f"{r['tps']:,.0f}", f"{r['p50']:.2f} / {r['p95']:.2f} s", usd(r["usd_per_doc"]), f4(r["overall"])])
    adm = []
    for lab, a, b in (("correspondence n=100", "sand032-s2b-corr100-2rep", "sand032-s9-corr100-bal"),
                      ("insurance n=50", "sand032-s3-insurance50", "sand032-s9-insurance50-bal"),
                      ("corporate n=50", "sand032-s3-corporate50", "sand032-s9-corporate50-bal"),
                      ("contracts n=50", "sand032-s3-contracts50", "sand032-s9-contracts50-bal")):
        sa, sb = serving(a), serving(b)
        if sa.get("wall_seconds") and sb.get("wall_seconds"):
            adm.append([lab, secs(float(sa["wall_seconds"])), secs(float(sb["wall_seconds"])),
                        f"{float(sa['wall_seconds']) / float(sb['wall_seconds']):.2f}×"])
    rel = [[r["run"], r["ok"], r["err"], r["na"], r.get("note") or "—"] for r in D["rel"]]
    for c in ("contract", "merger_agreement"):
        r = R[D["s3"][c]]
        errs = sorted({d["error"].split(":")[0] for d in r["docs"] if d.get("error")})
        rel.insert(0, [f"{r['label']} · SAND-032", r["ok"], r["n"] - r["ok"], 0, ", ".join(errs) or "—"])
    issues = [[f"`{i['key']}`", i["note"]] for i in D["issues"]]
    s6 = s6_per_class()
    v2 = v2_rows()
    mbr = [["run-2 (trainer test)", "20 Sep", pct(D["mb_run2"], 2), "—"],
           ["run-3 (GPU harness)", "21 Sep", pct(mb["run3"]["acc"], 2), pct(mb["run3"]["subclass"], 1)],
           ["run-3 (re-evaluated)", "27 Sep", pct(mb["run3_reeval"]["acc"], 2), pct(mb["run3_reeval"].get("subclass"), 1)],
           ["Arm A (1 epoch)", "27 Sep", pct(mb["armA"]["acc"], 2), pct(mb["armA"]["subclass"], 1)],
           ["Arm B (3 epochs)", "27 Sep", pct(mb["armB"]["acc"], 2), pct(mb["armB"]["subclass"], 1)]]
    aud = "\n".join(f"| {k} | {v['svgs']} | {v['overflow']} | {v['collisions']} | {v['markdown']} | {v['broken']} | {v['orphans']} |"
                    for k, v in audit.get("repos", {}).items())
    fixes = "\n".join(f"- **{k}:** {v}" for k, v in audit.get("fixes", {}).items())
    open_items = "\n".join(f"- {x}" for x in audit.get("open", []))
    best_api = {c: max((p for p in rows[c] if p["route"] == "api"), key=lambda p: p["score"]) for c in ORDER}
    return f"""# Mailroom evaluation — master status and research report

_Data {T['date_range']} · generated by sandbox `reports/dashboard/export_hub_reports.py` from the cross-checked reports hub ({T['n_figures']} source-quoted figures, {T['n_checks']} automated cross-checks, {T['n_issues']} documented source defects) · sources: {shas}_

The mailroom classifies incoming legal documents and extracts fields with class-specific specialists. It has been evaluated on two serving legs:

- **API leg** (`LLM-Mailroom-Services/eval-environment`): hosted models through OpenRouter.
- **Modal + vLLM leg** (`Exios66/local-mailroom-sandbox`, SAND-032): self-hosted Qwen3-8B-AWQ on Modal L4 GPUs.

A third workstream trains the **ModernBERT intake classifier** (`LLM-Mailroom-Services/mailroom-ml`). All three use the public `Lucius-Morningstar/mailroom-dataset` (v9.1 = `ed7576b`, 3,302 rows).

Companions: [COST-COMPARISON-MODAL-VS-API.md](COST-COMPARISON-MODAL-VS-API.md) and [MODAL-VLLM-GPU-REPORT.md](MODAL-VLLM-GPU-REPORT.md). Live hub: `local-mailroom-sandbox/reports/dashboard/mailroom-reports.html`.

## 1. Status at a glance

| Front | Where it stands | Gate |
| --- | --- | --- |
| Specialist extraction (Modal, SAND-032) | Insurance {f3(R[D['s3']['insurance_claim']]['overall'])} · corporate {f3(R[D['s3']['corporate_record']]['overall'])} · correspondence {f3(R[D['s3']['correspondence']]['overall'])} · contracts CUAD micro-F1 {f3(R[D['s3']['contract']]['headline'])} · merger MAUD accuracy {pct(R[D['s3']['merger_agreement']]['headline'])} | no extraction gate met; merger unsolved |
| Specialist extraction (API) | best per task: {', '.join(f"{D['labels'][c].lower()} {best_api[c]['family']} {f3(best_api[c]['score'])}" for c in ORDER)} | no model wins every task |
| Serving (Modal L4) | L5 posture frozen; 2×L4 scale-out at flat $/doc; SAND-032 spend {usd(D['spend']['sand032'])} of {usd(D['spend']['cap'])} | ✓ within cap |
| LLM sorter | API n = 100: {T['cls100_lo']}–{T['cls100_hi']}% class, {T['sub100_lo']}–{T['sub100_hi']}% subclass; Modal S6 {T['route_s6_acc']} (n = 457) | subclass far below 75% |
| ModernBERT intake | Arm B {pct(mb['armB']['acc'], 2)} doc type, {pct(mb['armB']['subclass'], 1)} subclass | ✓ P0 95% doc-type gate met · ✕ 75% subclass gate |

## 2. API leg — findings

{table(["Task", "Model", "n", "Score", "$/doc", "Wall", "p95 call", "Run"], api_rows, "llrrrrrl")}

![API extraction score by type](figures/api/extraction-score-by-type.svg)\n\n{ST['figures/api/extraction-score-by-type.svg']}

![API cost per document](figures/api/cost-per-document.svg)\n\n{ST['figures/api/cost-per-document.svg']}

- **No hosted model wins every task.** DeepSeek-V4.1-Flash leads insurance claims and corporate records. Qwen3-8B leads correspondence and contracts. Among the N = 20 merger legs, Granite-4.2-8B scores highest, at the highest cost.
- **The production model, Qwen3.7-Flash (API only; it was never self-hosted), holds up at n = 50** (mutated prompt lineage) and is the cheapest or near-cheapest hosted model on every class. On mergers it scores {f3(D['api']['route50']['merger agreements']['score'])}, the best merger result on any route.
- **DeepSeek-V4.1-Flash is the cheapest across the five N = 20 tasks**: {T['api_ds_cost']} in total vs {T['api_q_cost']} (Qwen3-8B, as filed, which includes the merger leg that ran on Qwen3.7-Flash) and {T['api_g_cost']} (Granite).

**LLM sorter (classification)**

{table(["Run", "Model", "n", "Class acc", "Subclass acc", "$/doc", "ECE"], cls_rows, "llrrrrr")}

![Sorter subclass accuracy](figures/api/sorter-subclass-accuracy.svg)\n\n{ST['figures/api/sorter-subclass-accuracy.svg']}

![Sorter calibration](figures/api/sorter-calibration.svg)\n\n{ST['figures/api/sorter-calibration.svg']}

- On 100 documents every hosted sorter routes {T['cls100_lo']}–{T['cls100_hi']}% of documents to the right class. The subclass is right only {T['sub100_lo']}–{T['sub100_hi']}% of the time.
- Stated confidence is informative: {T['sorter_head']}. Confidence can gate a fast path, but only for the class decision.

## 3. Modal + vLLM leg — findings

**Serving ladder.**

- The frozen **L5** posture cut wall time by {T['l5_wall_cut']} and cost per document by {T['l5_usd_cut']} against L0, at equal quality ({T['l5_score']} vs {T['l0_score']}).
- Throughput rose from {T['l0_tps']} to {T['l5_tps']} tok/s. The marlin kernel alone was reverted (quality drop).
- bf16 scored {T['bf16']} vs AWQ {T['l5_score']}, so there is no quality case for dropping AWQ.

![SAND-032 ladder](figures/sources/local-mailroom-sandbox/sand032-ladder.svg)

**Scale-out and admission.**

- A second L4 ran {T['scale_speed']}× faster at flat cost per document.
- The seqs32 balanced fleet cut wall time on every class.

{table(["Fleet (correspondence n = 100)", "Wall", "tok/s", "p50 / p95", "$/doc", "Score"], scale, "lrrrrr")}

{table(["Workload", "seqs16 fleet", "seqs32 balanced", "Speed-up"], adm, "lrrr")}

![Wall time by fleet](figures/sources/local-mailroom-sandbox/sand032-routing.svg)

![Admission](figures/sources/local-mailroom-sandbox/sand032-admission.svg)

**Five-class sweep (2×L4, c32, n = 50).**

{table(["Class", "Run", "Done", "Metric", "Headline", "Overall", "Schema", "Wall", "p50 / p95", "tok/s", "$/doc"], sweep, "lllrrrrrrrr")}

- A contract or merger takes {T['slow_lo']}–{T['slow_hi']}× longer than a letter.
- Output length drives latency {T['lat_ratio']}× more than input length.
- Insurance's 22% schema validity costs nothing in score.
- Mergers remain unsolved: the MAUD prompt doubled per-question accuracy from {T['maud0']} to {T['maud1']}, but coverage is only {T['maud_cov']}.

**Completion reliability.** Short documents never fail. Long contracts and mergers lose {T['err_lo']}–{T['err_hi']}% of documents.

{table(["Run", "Completed", "Errored", "Not attempted", "Cause"], rel, "lrrrl")}

**Prompt v2 (eval-environment GEPA) on Qwen3-8B-AWQ, paired 50.** Correspondence v2 is promoted. Insurance and corporate records are held.

{table(["Class", "v2 (75)", "v2 (paired 50)", "production (paired 50)", "Δ paired", "better / worse", "schema v2 / prod", "Verdict"], v2, "lrrrrrrl")}

![Production vs v2 prompts](figures/sources/local-mailroom-sandbox/sand032-v2-prompts.svg)

**Isolated LLM sorter on Modal (S6).** Accuracy {T['route_s6_acc']} on 457 documents, macro-F1 {D['route']['sorter_modal']['macro_f1']:.4f}, {T['route_s6_usd']}/doc. Mergers are under-recalled, and corporate records leak into contracts.

{table(["Class", "n", "Precision", "Recall", "F1"], s6, "lrrrr")}

![S6 per-class F1](figures/sources/local-mailroom-sandbox/sand032-s6-sorter1000-per-class-f1.svg)

## 4. ModernBERT intake classifier

{table(["Checkpoint", "Evaluated", "Doc-type acc", "Subclass (conditional)"], mbr, "llrr")}

- **Arm B is the first checkpoint over the 95% P0 doc-type gate.** It lifted corporate records from {T['corp_run3']} to {T['corp_armb']}.
- **Subclass stays at {pct(mb['armB']['subclass'], 1)}, below its 75% gate.** Contracts hold it down ({T['con_sub']} of contract subclasses right).
- **Selective prediction works.** At threshold {mb['armB']['pick']} Arm B accepts {pct(mb['armB']['pick_cov'])} of windows at {pct(mb['armB']['pick_acc'], 2)} accuracy (window ECE {mb['armB']['window_ece']}). {pct(mb['armB']['fast_path'])} of documents take the fast path, and {T['fp_b']} of them were routed correctly.
- Document length does not explain routing errors.

![ModernBERT recall by class](figures/modernbert/doc-type-recall.svg)\n\n{ST['figures/modernbert/doc-type-recall.svg']}

![Selective risk](figures/modernbert/selective-risk.svg)\n\n{ST['figures/modernbert/selective-risk.svg']}

![Subclass collapse](figures/modernbert/subclass-collapse.svg)\n\n{ST['figures/modernbert/subclass-collapse.svg']}

## 5. Cross-leg verdict

1. **Sort with ModernBERT.** It matches the best hosted LLM sorter's document-type accuracy at about three orders of magnitude lower cost. Keep the LLM sorter only behind the confidence gate, and fix subclass before relying on either for it.
2. **Extract via the API for insurance claims, contracts and mergers.** The cheapest hosted model costs less per document than Modal on all three. It also scores higher on insurance claims and mergers; contracts are scored differently on the two legs.
3. **Where Modal deployment pays.** {optimal_sentence(E)} Full break-even tables: [COST-COMPARISON-MODAL-VS-API.md §3](COST-COMPARISON-MODAL-VS-API.md#3-when-does-modal-pay-off-break-even-and-the-optimal-scenario).
4. **The quality ceiling is the prompt and scorer, not the serving.** Serving work cut cost per document {T['cost_red_lo']}–{T['cost_red_hi']}×. Prompts moved correspondence by +0.04 (v2), and no configuration fixes mergers or subclass.

## 6. Documented source defects

{table(["Key", "Defect"], issues, "ll")}

## 7. Report audit (this sweep)

Every committed SVG in the three repositories was rendered in Chromium and checked text box by text box, for overflow past the figure edge and for overlapping labels. Every relative link and image in their tracked markdown was resolved.

| Repository | SVGs | Overflow | Collisions | Markdown files | Broken links | Unreferenced figures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{aud}

Fixes made in this sweep:

{fixes}

Still open:

{open_items}

## Sources

{sources_block(D, shas)}
"""


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT.parent / "mailroom-issues" / "reports"))
    ap.add_argument("--eval-env", default=str(ROOT.parent / "eval-environment"))
    ap.add_argument("--mailroom-ml", default=str(ROOT.parent / "mailroom-ml"))
    ap.add_argument("--audit", default=str(HERE / "report_audit.json"),
                    help="JSON with the sweep results for the master report's audit section")
    ap.add_argument("--site", default=None,
                    help="static GitHub Pages site directory (default: <out>/../docs)")
    ap.add_argument("--check", action="store_true", help="exit 1 if the output directory is stale")
    args = ap.parse_args()

    D = json.loads(DATA.read_text())
    shas = (f"local-mailroom-sandbox @ {git_sha(ROOT)} · eval-environment @ {D['sources']['LLM-Mailroom-Services/eval-environment'][:12]}"
            f" · mailroom-ml @ {D['sources']['LLM-Mailroom-Services/mailroom-ml'][:12]}")
    audit = json.loads(pathlib.Path(args.audit).read_text()) if args.audit else {}

    import gpu_report  # noqa: PLC0415 — imports this module's helpers at call time
    import modal_performance  # noqa: PLC0415
    import pages_site  # noqa: PLC0415
    rows, sorters = route_rows(D), sorters_of(D)
    E = breakeven.analyze(D, gpu_report.NOT_A_CONFIG)
    gpu_md, gpu_figs, gpu_stats = gpu_report.report(D, sys.modules[__name__], shas)
    files: dict[str, str | bytes] = {
        **gpu_figs,
        "MODAL-VLLM-GPU-REPORT.md": gpu_md,
        "figures/cost/cost-per-doc.svg": fig_cost(D, rows),
        "figures/cost/score-by-route.svg": fig_score(D, rows),
        "figures/cost/modal-vs-cheapest-api.svg": fig_modal_vs_cheapest(E),
        "figures/cost/sorter-routes.svg": fig_sorter(D, sorters),
        "figures/cost/modal-vs-api-breakeven.svg": breakeven.fig(E, viz, usd),
        **source_charts.render(D, viz),
        **(modal_figs := modal_performance.render(D, viz, exclude=gpu_report.NOT_A_CONFIG)),
        "MODAL-PERFORMANCE-VISUALS.md": modal_performance.report_md(sorted(modal_figs)),
        "COST-COMPARISON-MODAL-VS-API.md": cost_report(D, rows, E, sorters, shas),
        "MASTER-REPORT.md": master_report(D, rows, E, sorters, audit, shas),
    }
    roots = {"local-mailroom-sandbox": ROOT, "eval-environment": pathlib.Path(args.eval_env),
             "mailroom-ml": pathlib.Path(args.mailroom_ml)}
    for repo, paths in COPY.items():
        for src in paths:
            p = roots[repo] / src
            if not p.is_file():
                raise SystemExit(f"missing source figure {repo}:{src}")
            files[f"figures/sources/{repo}/{pathlib.Path(src).name}"] = p.read_bytes()
    files["README.md"] = readme(files, shas)

    out = pathlib.Path(args.out)
    site_dir = pathlib.Path(args.site) if args.site else out.parent / "docs"
    site = pages_site.build(files, gpu_stats, shas)
    stale = []
    for root, tree, prefix in ((out, files, ""), (site_dir, site, "site: ")):
        for rel, body in tree.items():
            data = body.encode() if isinstance(body, str) else body
            dest = root / rel
            if not dest.is_file() or dest.read_bytes() != data:
                stale.append(prefix + rel)
                if not args.check:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)
    for rel in stale:
        print(("stale: " if args.check else "wrote: ") + rel)
    return 1 if (args.check and stale) else 0


def readme(files: dict, shas: str) -> str:
    figs = sorted(f for f in files if f.startswith("figures/"))
    fig_lines = "\n".join(f"- [`{f}`]({f})" for f in figs)
    return f"""# Reports

Cross-repository evaluation reports for the LLM-Mailroom constellation. These are generated outputs: no code lives here (see [AGENTS.md](../AGENTS.md)).

Prompt baselines cited in the reports: frozen v1 reference copies in
[`docs/prompts/frozen-v1/`](../docs/prompts/frozen-v1/) and lineage notes in
[`docs/PROMPTS.md`](../docs/PROMPTS.md).

| Report | What it answers |
| --- | --- |
| [MASTER-REPORT.md](MASTER-REPORT.md) | Where every front stands, the findings from the API leg (eval-environment), the Modal + vLLM leg (local-mailroom-sandbox, SAND-032) and the ModernBERT intake classifier (mailroom-ml), the cross-leg verdict, and this sweep's report audit |
| [COST-COMPARISON-MODAL-VS-API.md](COST-COMPARISON-MODAL-VS-API.md) | Cost per document and per unit of quality for every route and model, the break-even volumes and the optimal Modal deployment, sorter routes, and spend |
| [MODAL-VLLM-GPU-REPORT.md](MODAL-VLLM-GPU-REPORT.md) | The Modal + vLLM leg's GPU economics: cost per token, where the GPU spend went, how busy the GPUs were, and what adding the second L4 did |

**Provenance.** Generated by `reports/dashboard/export_hub_reports.py` in `Exios66/local-mailroom-sandbox` from the reports hub, where every figure is read from a tracked file and cross-checked. Built from {shas}. `figures/cost/`, `figures/gpu/`, `figures/api/` (eval-environment data) and `figures/modernbert/` (mailroom-ml data) are drawn for these reports from the hub; `figures/sources/local-mailroom-sandbox/` holds the SAND-032 charts, drawn by the same kit. Every figure is a dark, high-contrast card, and `viz/` holds each one as a 2× PNG for slides.

**Regenerate.** With `local-mailroom-sandbox`, `eval-environment`, `mailroom-ml` and `mailroom-issues` checked out side by side, run this in `local-mailroom-sandbox` (`--check` exits 1 if anything here is stale):

```bash
python reports/dashboard/build_hub.py sync
python reports/dashboard/build_hub.py
python reports/dashboard/export_hub_reports.py --out ../mailroom-issues/reports
python reports/dashboard/export_hub_reports.py --out ../mailroom-issues/reports --check
```

Figures:

{fig_lines}
"""


if __name__ == "__main__":
    sys.exit(main())
