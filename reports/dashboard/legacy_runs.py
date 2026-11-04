"""Source-verified extraction for the 16–27 Sep specialist runs (pre-SAND-032).

Every figure is read out of a tracked file under ``reports/`` (a markdown table
cell, a sentence, or a JSON key) and recorded with its source. Cross-checks
compare the per-document tables against the run-level figures each report
states; any mismatch fails unless it is a documented entry in ``KNOWN``.

Used by ``build_hub.py``; ``build()`` returns the data and provenance.
"""

from __future__ import annotations

import json
import math
import pathlib
import re
import statistics

HERE = pathlib.Path(__file__).resolve().parent
REPORTS = HERE.parent

L4_USD_PER_HOUR = 0.80

INS = "SAND-32/insurance/RUN-20-INSURANCE-CLAIMS-SPECIALIST-AWQ-REPORT.md"
CORP = "SAND-32/corporate/RUN-20-CORPORATE-RECORDS-SPECIALIST-AWQ-REPORT.md"
CORR_A = "SAND-32/correspondence/RUN-20-CORRESPONDENCE-SPECIALIST-AWQ-REPORT.md"
CORR_B = "SAND-32/correspondence/RUN-50-CORRESPONDENCE-SPECIALIST-AWQ-REPORT.md"
CORR_C5 = "SAND-32/correspondence/RUN-20-CORRESPONDENCE-AWQ-REPORT.md"
CORR_C8 = "SAND-32/correspondence/RUN-20-CORRESPONDENCE-AWQ-C8-REPORT.md"
CON_C8 = "SAND-32/contract/RUN-20-CONTRACTS-AWQ-C8-REPORT.md"
MERGER = "SAND-32/merger/RUN-20-MERGER-SPECIALIST-AWQ-REPORT.md"
MODAL_RUNS = "archive/MODAL-RUNS-REPORT.md"
SORTER_RUN = "archive/RUN50-MODAL-HF-REPORT.md"
FLASH = "archive/QWEN-FLASH-COST-REPORT.md"
G_HALT = "SAND-32/granite/RUN-20-CONTRACTS-GRANITE-HALT-REPORT.md"
G_MERGER = "SAND-32/granite/RUN-20-MERGER-GRANITE-REPORT.md"
G_CORR = "SAND-32/granite/RUN-50-CORRESPONDENCE-GRANITE-REPORT.md"
G_P1 = "SAND-32/granite/RUN-01-CONTRACTS-GRANITE-PROBE-REPORT.md"
G_P2 = "SAND-32/granite/RUN-02-CONTRACTS-GRANITE-PROBE2-REPORT.md"
MB_EVAL = "modernbert/eval_run3_20260921.json"
MB_SORTER = "modernbert/SORTER-VS-MODERNBERT-COST-PERF-323.md"

NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?(?:e-?\d+)?")
PROVENANCE: list[dict] = []
ISSUES: list[dict] = []

# Cross-check failures that are real, documented inconsistencies inside a
# tracked report. Each must still fail (a fixed report makes this entry stale
# and the build tells you to delete it); anything not listed here aborts.
KNOWN = {
    "correspondence_a.latency_sum": (
        "Run A's per-document latency column sums to {got}, but the report's run-level "
        "sum is {want} (the serving export agrees: latency_sum_seconds 503.369, "
        "p50 26.595 s vs a per-row median of 26.0 s). The report says its per-document "
        "rows were reconstructed from captured stdout; scores in the same table do match "
        "the stated mean. Latency dots for Run A come from that table."
    ),
}


class SourceError(RuntimeError):
    pass


def _text(path: str) -> str:
    return (REPORTS / path).read_text()


def _num(s: str, idx: int = 0) -> float:
    found = NUM.findall(s.replace("**", ""))
    if len(found) <= idx:
        raise SourceError(f"no number #{idx} in {s!r}")
    return float(found[idx].replace(",", ""))


def _record(key: str, value, path: str, quote: str):
    PROVENANCE.append({"key": key, "value": value, "source": path, "quote": quote.strip()})
    return value


def cell(key: str, path: str, row: str, col: int, idx: int = 0) -> float:
    """Number #idx in column ``col`` of the markdown table row starting with ``row``."""
    hits = [ln for ln in _text(path).splitlines() if ln.strip().startswith(row)]
    if not hits or len(set(hits)) != 1:
        raise SourceError(f"{path}: expected one row starting {row!r}, found {len(hits)}")
    cells = [c.strip() for c in hits[0].strip().strip("|").split("|")]
    return _record(key, _num(cells[col], idx), path, hits[0])


def rx(key: str, path: str, pattern: str) -> float:
    """First group of ``pattern`` in the whitespace-normalized source text."""
    flat = re.sub(r"\s+", " ", _text(path))
    m = re.search(pattern, flat)
    if not m:
        raise SourceError(f"{path}: pattern {pattern!r} not found")
    return _record(key, _num(m.group(1)), path, m.group(0))


def jkey(key: str, path: str, *keys):
    node = json.loads(_text(path))
    for k in keys:
        node = node[k]
    return _record(key, node, path, f"{'.'.join(map(str, keys))} = {json.dumps(node)[:80]}")


def check(cond: bool, msg: str, key: str | None = None, **fmt):
    if key in KNOWN:
        if cond:
            raise SourceError(f"known issue {key!r} no longer reproduces — remove it from KNOWN")
        ISSUES.append({"key": key, "note": KNOWN[key].format(**fmt)})
        return
    if not cond:
        raise SourceError(f"cross-check failed: {msg}")


# ---------------------------------------------------------------- per-doc rows
ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*`(DOC-[0-9a-f]+)`\s*\|(.*)\|\s*$")


def per_doc(path: str) -> list[dict]:
    def val(s):
        return None if s in ("None", "") else float(s)

    rows, in_section = [], False
    for line in _text(path).splitlines():
        if line.startswith("## "):
            in_section = line.startswith("## Per-document")
        m = ROW.match(line) if in_section else None
        if not m:
            continue
        subclass, overall, f1, lat, ptok, ctok, err = [c.strip() for c in m.group(3).split("|")]
        rows.append({
            "doc": m.group(2), "subclass": subclass, "overall": val(overall), "f1": val(f1),
            "latency": val(lat), "prompt": val(ptok), "completion": val(ctok),
            "error": None if err == "None" else err,
        })
    if not rows:
        raise SourceError(f"{path}: no per-document rows")
    return rows


def median(xs):
    return statistics.median(xs)


def build() -> dict:
    PROVENANCE.clear()
    ISSUES.clear()
    docs = {
        "insurance": per_doc(INS), "correspondence_a": per_doc(CORR_A),
        "correspondence_b": per_doc(CORR_B), "contracts_c8": per_doc(CON_C8),
        "correspondence_c5": per_doc(CORR_C5), "correspondence_c8": per_doc(CORR_C8),
    }

    # --- cross-check per-document tables against each report's run-level figures
    for key, path, n, score_row, lat_sum_pat in [
        ("insurance", INS, 20, "| **overall_extraction_score**", r"sum\(per-doc latency\) = ([\d.]+)"),
        ("correspondence_a", CORR_A, 20, "| **overall_extraction_score**", r"sum\(per-doc latency\) = ([\d.]+)"),
        ("correspondence_b", CORR_B, 50, "| **overall_extraction_score**", r"sum\(per-doc latency\) = ([\d.]+)"),
        ("correspondence_c5", CORR_C5, 20, "| **overall_extraction_score**", r"sum\(per-doc latency\) = ([\d.]+)"),
        ("correspondence_c8", CORR_C8, 20, "| **overall_extraction_score**", r"sum\(per-doc latency\) = ([\d.]+)"),
        ("contracts_c8", CON_C8, 20, "| **overall_extraction_score**", r"sum\(per-doc latency\) = ([\d.]+)"),
    ]:
        rows = docs[key]
        check(len(rows) == n, f"{path}: {len(rows)} per-doc rows, report n={n}")
        mean = sum(r["overall"] for r in rows) / n
        stated = cell(f"{key}.overall", path, score_row, 1)
        check(abs(mean - stated) < 0.0006, f"{path}: per-doc mean {mean:.5f} vs stated {stated}")
        lat_sum = sum(r["latency"] for r in rows)
        stated_sum = rx(f"{key}.latency_sum", path, lat_sum_pat)
        check(abs(lat_sum - stated_sum) < 0.1 * n, f"{path}: latency sum {lat_sum:.1f} vs stated {stated_sum}",
              key=f"{key}.latency_sum", got=f"{lat_sum:.1f} s", want=f"{stated_sum} s")

    for key, path in [("insurance", INS), ("correspondence_b", CORR_B), ("correspondence_a", CORR_A)]:
        by = {}
        for r in docs[key]:
            by.setdefault(r["subclass"], []).append(r["overall"])
        for sub, vals in by.items():
            stated = cell(f"{key}.strata.{sub}", path, f"| {sub} |", 2)
            check(abs(sum(vals) / len(vals) - stated) < 0.0006, f"{path}: stratum {sub}")

    con_ok = [r for r in docs["contracts_c8"] if not r["error"]]
    check(sum(r["prompt"] for r in con_ok) == cell("contracts_c8.prompt_tokens", CON_C8, "| prompt / completion / total tokens", 1, 0), "contracts prompt tokens")
    check(sum(r["completion"] for r in con_ok) == cell("contracts_c8.completion_tokens", CON_C8, "| prompt / completion / total tokens", 1, 1), "contracts completion tokens")
    check(abs(median([r["latency"] for r in docs["contracts_c8"]]) - cell("contracts_c8.p50", CON_C8, "| latency e2e / p50 / max", 1, 1)) < 0.1, "contracts p50")
    check(abs(median([r["latency"] for r in docs["insurance"]]) - cell("insurance.p50", INS, "| latency e2e / p50 / max", 1, 1)) < 0.1, "insurance p50")

    # --- quality (local vs API)
    api_row = {
        "Insurance claims": "| insurance_claims `", "Corporate records": "| corporate_records `",
        "Correspondence": "| correspondence `20260927T033031Z`", "Contracts": "| contracts `",
        "Merger agreements": "| merger_agreement `20260927T022750Z`",
    }
    types = list(api_row)
    quality = {
        "Insurance claims": {"modal": cell("quality.ins", INS, "| **overall_extraction_score**", 1)},
        "Corporate records": {"modal": cell("quality.corp", CORP, "| **overall_extraction_score**", 1)},
        "Correspondence": {"modal": cell("quality.corr_a", CORR_A, "| **overall_extraction_score**", 1)},
        "Contracts": {"modal": None, "why": "Not measurable: GT has no contract schema"},
        "Merger agreements": {"modal": None, "why": "Not measurable: CUAD prompt vs MAUD labels"},
    }
    cost, wall = {}, {}
    for t, row in api_row.items():
        quality[t]["api"] = cell(f"api.{t}.score", CORR_B, row, 3)
        wall[t] = {"api": cell(f"api.{t}.wall", CORR_B, row, 4)}
        cost[t] = {"api": cell(f"api.{t}.per_doc", CORR_B, row, 7)}
        check(cell(f"api.{t}.n", CORR_B, row, 2) == 20, f"API {t} n")
    check(rx("contracts.ok_rows_zero", CON_C8, r"ok rows: (\d+)/20; all ok rows score 0\.0") == 17, "contracts ok rows")

    cost["Insurance claims"]["modal"] = cell("cost.ins", MODAL_RUNS, "| run-20-insurance-claims-specialist-awq |", 11)
    cost["Correspondence"]["modal"] = cell("cost.corr_a", MODAL_RUNS, "| run-20-correspondence-specialist-awq |", 11)
    cost["Contracts"]["modal"] = cell("cost.con_c8", CON_C8, "| cost per document |", 1)
    cost["Corporate records"]["modal"] = cell("cost.corp", CORP, "| est. GPU cost (busy) |", 1, 1)
    cost["Merger agreements"]["modal"] = cell("cost.merger", MERGER, "| est. GPU cost (busy) |", 1, 1)
    wall["Insurance claims"]["modal"] = cell("wall.ins", MODAL_RUNS, "| run-20-insurance-claims-specialist-awq |", 6)
    wall["Correspondence"]["modal"] = cell("wall.corr_a", MODAL_RUNS, "| run-20-correspondence-specialist-awq |", 6)
    wall["Contracts"]["modal"] = cell("wall.con_c8", CON_C8, "| wall (busy interval) |", 1)
    wall["Corporate records"]["modal"] = cell("wall.corp", CORP, "| wall |", 1)
    wall["Merger agreements"]["modal"] = cell("wall.merger", MERGER, "| wall (harness busy) |", 1)

    # --- batching speedup = sum(latency) / wall
    conc = [
        {"run": "Merger (contracts prompt)", "eng": "modal", "c": 8, "s": rx("conc.merger", MERGER, r"= \*\*([\d.]+)× at c=8\*\*")},
        {"run": "Contracts c8", "eng": "modal", "c": 8, "s": rx("conc.con_c8", CON_C8, r"speedup \*\*([\d.]+)x\*\* at concurrency 8")},
        {"run": "Correspondence A · 2×L4", "eng": "modal", "c": 8, "s": rx("conc.corr_a", CORR_A, r"speedup \*\*([\d.]+)x\*\* at concurrency 8")},
        {"run": "Correspondence c8", "eng": "modal", "c": 8, "s": rx("conc.corr_c8", CORR_C8, r"speedup \*\*([\d.]+)x\*\* at concurrency 8")},
        {"run": "Corporate records", "eng": "modal", "c": 8, "s": rx("conc.corp", CORP, r"= \*\*([\d.]+)× at c=8\*\*")},
        {"run": "Insurance claims", "eng": "modal", "c": 8, "s": rx("conc.ins", INS, r"speedup \*\*([\d.]+)x\*\* at concurrency 8")},
        {"run": "Correspondence B · 2×L4", "eng": "modal", "c": 8, "s": rx("conc.corr_b", CORR_B, r"speedup \*\*([\d.]+)x\*\* at concurrency 8")},
        {"run": "Correspondence c5", "eng": "modal", "c": 5, "s": rx("conc.corr_c5", CORR_C5, r"speedup ([\d.]+)x at concurrency 5")},
        {"run": "Granite merger", "eng": "granite", "c": 3, "s": rx("conc.g_merger", G_MERGER, r"≈ \*\*~([\d.]+)×\*\*")},
        {"run": "Granite contracts (halted)", "eng": "granite", "c": 8, "s": rx("conc.g_halt", G_HALT, r"\*\*([\d.]+)× serialization\*\*")},
    ]

    # --- tokens per completed document (errored rows carry no usage)
    def toks(key, path, row, n_ok):
        return {"prompt": cell(f"{key}.prompt", path, row, 1, 0) / n_ok,
                "compl": cell(f"{key}.compl", path, row, 1, 1) / n_ok, "n_ok": n_ok}
    merger_ok = cell("merger.ok", MERGER, "| docs ok / failed / total |", 1, 0)
    tokens = [
        {"t": "Merger agreements", **toks("tok.merger", MERGER, "| prompt / completion / total tokens |", merger_ok)},
        {"t": "Contracts", **toks("tok.con", CON_C8, "| prompt / completion / total tokens |", len(con_ok))},
        {"t": "Corporate records", **toks("tok.corp", CORP, "| prompt / completion / total tokens |", 20)},
        {"t": "Insurance claims", **toks("tok.ins", INS, "| prompt / completion / total tokens |", 20)},
        {"t": "Correspondence", **toks("tok.corr_a", CORR_A, "| prompt / completion / total tokens |", 20)},
    ]

    # --- correspondence history
    history = [
        {"run": "c5 · 1×L4 · split all", "score": cell("hist.c5", CORR_C5, "| **overall_extraction_score**", 1), "cost": cell("hist.c5.cost", MODAL_RUNS, "| run-20-correspondence-awq |", 11), "date": "25 Sep", "sv": "not recorded"},
        {"run": "c8 · 1×L4 · split all", "score": cell("hist.c8", CORR_C8, "| **overall_extraction_score**", 1), "cost": cell("hist.c8.cost", CORR_C8, "| cost per document |", 1), "date": "25 Sep", "sv": "not recorded"},
        {"run": "Run A · 2×L4 · test, stratified", "score": cell("hist.a", CORR_A, "| **overall_extraction_score**", 1), "cost": cost["Correspondence"]["modal"], "date": "27 Sep", "sv": f"{cell('hist.a.sv', CORR_A, '| schema_valid_rate |', 1):.2f}"},
        {"run": "Run B · 2×L4 · test, n=50", "score": cell("hist.b", CORR_B, "| **overall_extraction_score**", 1), "cost": cell("hist.b.cost", MODAL_RUNS, "| run-50-correspondence-specialist-awq |", 11), "date": "27 Sep", "sv": f"{cell('hist.b.sv', CORR_B, '| schema_valid_rate |', 1):.2f}"},
    ]
    shared = {r["doc"]: r["overall"] for r in docs["correspondence_c5"]}
    overlap = [(r["doc"], shared[r["doc"]], r["overall"]) for r in docs["correspondence_b"] if r["doc"] in shared]

    # --- reliability
    def mr_err(run):
        return cell(f"rel.{run}.errors", MODAL_RUNS, f"| {run} |", 5)
    rel = []
    for label, run, n in [
        ("Insurance · Qwen AWQ", "run-20-insurance-claims-specialist-awq", 20),
        ("Corporate · Qwen AWQ", None, 20),
        ("Correspondence A · Qwen AWQ", "run-20-correspondence-specialist-awq", 20),
        ("Correspondence B · Qwen AWQ", "run-50-correspondence-specialist-awq", 50),
        ("Correspondence c5 · Qwen AWQ", "run-20-correspondence-awq", 20),
        ("Correspondence c8 · Qwen AWQ", None, 20),
        ("Contracts c4 · Qwen AWQ", "run-20-contracts-awq", 20),
        ("Contracts c8 · Qwen AWQ", None, 20),
        ("Merger · Qwen AWQ", None, 20),
        ("Contracts · Qwen bf16", "run-20-contracts-specialist", 20),
    ]:
        if run:
            err = mr_err(run)
        elif label.startswith("Corporate"):
            err = cell("rel.corp.failed", CORP, "| docs ok / failed / total |", 1, 1)
        elif label.startswith("Correspondence c8"):
            err = n - cell("rel.c8.ok", CORR_C8, "| docs ok / total |", 1, 0)
        elif label.startswith("Contracts c8"):
            err = n - len(con_ok)
        else:
            err = cell("rel.merger.failed", MERGER, "| docs ok / failed / total |", 1, 1)
        rel.append({"run": label, "ok": int(n - err), "err": int(err), "na": 0})
    notes = {
        "Contracts c4 · Qwen AWQ": "400 context overflow (16k window) and LengthFinish at 4,096 tokens",
        "Contracts c8 · Qwen AWQ": "LengthFinishReasonError at 8,192 tokens",
        "Merger · Qwen AWQ": "Transient connection drops at c=8",
        "Contracts · Qwen bf16": "Pre-AWQ run; error detail not archived",
    }
    for r in rel:
        r["note"] = notes.get(r["run"], "")
    g_att = cell("rel.g_merger.att", G_MERGER, "| docs attempted / ok / failed / unattempted |", 1, 0)
    rel += [
        {"run": "Merger · Granite", "ok": int(cell("rel.g_merger.ok", G_MERGER, "| docs attempted / ok / failed / unattempted |", 1, 1)),
         "err": int(cell("rel.g_merger.err", G_MERGER, "| docs attempted / ok / failed / unattempted |", 1, 2)),
         "na": int(cell("rel.g_merger.na", G_MERGER, "| docs attempted / ok / failed / unattempted |", 1, 3)),
         "note": "Thinking text broke the JSON parse; cost-cap abort"},
        {"run": "Correspondence-50 · Granite", "ok": int(cell("rel.g_corr.ok", G_CORR, "| docs ok / errors at kill |", 1, 0)),
         "err": int(cell("rel.g_corr.err", G_CORR, "| docs ok / errors at kill |", 1, 1)), "na": 0,
         "note": "Stopped on pace: projected cost over the cap"},
        {"run": "Contracts · Granite", "ok": 0, "err": int(rx("rel.g_halt.err", G_HALT, r"8/20 docs, \*\*0 ok / (\d+) errors\*\*")), "na": 0,
         "note": "Operator halt: output budget spent on thinking"},
    ]
    check(g_att == 16, "granite merger attempted")
    rel[-2]["na"] = 50 - rel[-2]["ok"] - rel[-2]["err"]
    rel[-1]["na"] = 20 - rel[-1]["err"]
    for r in rel:
        check(r["ok"] >= 0 and r["err"] >= 0 and r["na"] >= 0, f"reliability {r['run']}")

    # --- spend
    qwen_runs = [
        ("insurance", cell("spend.ins", MODAL_RUNS, "| run-20-insurance-claims-specialist-awq |", 10)),
        ("correspondence A", cell("spend.corr_a", MODAL_RUNS, "| run-20-correspondence-specialist-awq |", 10)),
        ("correspondence B", cell("spend.corr_b", MODAL_RUNS, "| run-50-correspondence-specialist-awq |", 10)),
        ("correspondence c5", cell("spend.c5", MODAL_RUNS, "| run-20-correspondence-awq |", 10)),
        ("correspondence c8", cell("spend.c8", CORR_C8, "| estimated GPU cost | **", 1)),
        ("contracts c4", cell("spend.con_c4", MODAL_RUNS, "| run-20-contracts-awq |", 10)),
        ("contracts c8", cell("spend.con_c8", CON_C8, "| estimated GPU cost |", 1)),
        ("corporate", cell("spend.corp", CORP, "| est. GPU cost (busy) |", 1, 0)),
        ("merger", cell("spend.merger", MERGER, "| est. GPU cost (busy) |", 1, 0)),
    ]
    probe_wall = cell("spend.g_p1.wall", G_P1, "| wall |", 1) + cell("spend.g_p2.wall", G_P2, "| wall |", 1)
    granite = [
        ("merger", cell("spend.g_merger", G_MERGER, "| est. GPU cost (guard accounting) |", 1)),
        ("correspondence-50", cell("spend.g_corr", G_CORR, "| sunk cost |", 1, 1)),
        ("contracts halt window (low end)", rx("spend.g_halt", G_HALT, r"≈ \*\*\$([\d.]+)–[\d.]+\*\*")),
        ("contracts probes (wall × L4 rate)", probe_wall / 3600 * L4_USD_PER_HOUR),
    ]
    api = [cell(f"spend.api.{t}", CORR_B, row, 6) for t, row in [
        ("corr", "| correspondence `20260927T033031Z`"), ("ins", "| insurance_claims `"), ("con", "| contracts `"),
        ("corp", "| corporate_records `"), ("m20", "| merger_agreement `20260927T022750Z`"),
        ("m2", "| merger_agreement `20260927T020724Z`"), ("cls", "| classification `")]]
    flash = rx("spend.flash", FLASH, r"\*\*total\*\* \| \*\*41\*\* \| \| \| \*\*≈ \$([\d.]+)\*\*")
    sorter = rx("spend.sorter", SORTER_RUN, r"metered \*\*\$([\d.]+)\*\*")
    spend = [
        {"b": "Sorter pipeline run (bf16)", "v": sorter, "d": "run-50-modal-hf: 50 docs, about 5 LLM calls each, up to 4×L4; metered"},
        {"b": "Granite specialist legs", "v": math.fsum(v for _, v in granite), "d": "; ".join(f"{k} ${v:.3f}" for k, v in granite)},
        {"b": f"Qwen AWQ specialist runs ({len(qwen_runs)})", "v": math.fsum(v for _, v in qwen_runs), "d": "; ".join(f"{k} ${v:.3f}" for k, v in qwen_runs)},
        {"b": "API legs (OpenRouter)", "v": math.fsum([*api, flash]), "d": f"{len(api)} eval-environment legs ${sum(api):.3f} + qwen-flash ledger ${flash:.3f}"},
    ]
    total_spend = math.fsum(s["v"] for s in spend)  # correctly rounded on every Python

    # --- ModernBERT
    conf = jkey("mb.confusion", MB_EVAL, "per_stratum_confusion")
    names = {"insurance_claim": "Insurance claims", "merger_agreement": "Merger agreements", "correspondence": "Correspondence", "contract": "Contracts", "corporate_record": "Corporate records"}
    mb_acc = []
    for k, label in names.items():
        tot = sum(v for kk, v in conf.items() if kk.startswith(k + "->"))
        mb_acc.append({"t": label, "c": conf[f"{k}->{k}"], "n": tot})
    mb_n = jkey("mb.n", MB_EVAL, "n_docs")
    mb_correct = sum(r["c"] for r in mb_acc)
    check(sum(r["n"] for r in mb_acc) == mb_n, "ModernBERT confusion totals")
    check(abs(mb_correct / mb_n - jkey("mb.acc", MB_EVAL, "doc_type_accuracy")) < 0.0001, "ModernBERT accuracy")
    ece = jkey("mb.ece", MB_EVAL, "head_ece")
    risk_rows = jkey("mb.risk", MB_EVAL, "selective_risk", "rows")
    pick_t = jkey("mb.pick", MB_EVAL, "selective_risk", "recommended_threshold")
    pick = next(r for r in risk_rows if abs(r["threshold"] - pick_t) < 1e-9)
    check(pick["n"] == jkey("mb.n_at_pick", MB_EVAL, "selective_risk", "n_at_pick"), "selective-risk pick row")
    sorter_lat = cell("mb.sorter_lat", MB_SORTER, "| sorter | Qwen/Qwen3-8B |", 3)
    mb_lat = cell("mb.lat", MB_SORTER, "| modernbert | Lucius-Morningstar/mailroom-modernbert-classifier | 323 | 0.075", 3)
    sorter_cost = cell("mb.sorter_cost", MB_SORTER, "| sorter | Qwen/Qwen3-8B |", 4)
    mb_cost = cell("mb.cost", MB_SORTER, "| modernbert | Lucius-Morningstar/mailroom-modernbert-classifier | 323 | 0.075", 4)
    sorter_acc = cell("mb.sorter_acc", MB_SORTER, "| accuracy | 0.98 |", 1)
    multi = jkey("mb.multi", MB_EVAL, "cohorts", "multi-window", "doc_type_accuracy")
    single = jkey("mb.single", MB_EVAL, "cohorts", "single-window", "doc_type_accuracy")

    # --- headline numbers used in text
    qwen_docs = sum(r["ok"] + r["err"] for r in rel if "Qwen AWQ" in r["run"])
    qwen_ok = sum(r["ok"] for r in rel if "Qwen AWQ" in r["run"])
    lat_med = {k: median([r["latency"] for r in docs[k]]) for k in ("contracts_c8", "correspondence_a")}
    corr_scores = [h["score"] for h in history]
    t = {
        "best_score": f"{quality['Insurance claims']['modal']:.3f}",
        "cheapest": f"${cost['Correspondence']['modal']:.4f}",
        "total_spend": f"${total_spend:.2f}",
        "qwen_ok": str(qwen_ok), "qwen_docs": str(qwen_docs), "qwen_err": str(qwen_docs - qwen_ok),
        "qwen_runs": str(len(qwen_runs)),
        "qwen_spend": f"${sum(v for _, v in qwen_runs):.2f}",
        "qwen_per_doc": f"${sum(v for _, v in qwen_runs) / qwen_docs:.4f}",
        "corr_wall_ratio": f"{wall['Correspondence']['api'] / wall['Correspondence']['modal']:.0f}",
        "granite_cost_ratio": f"{granite[0][1] / cost_of(qwen_runs, 'merger'):.1f}",
        "con_gap": f"{cost['Contracts']['modal'] / cost['Contracts']['api']:.1f}",
        "lat_ratio": f"{lat_med['contracts_c8'] / lat_med['correspondence_a']:.0f}",
        "corr_lift_lo": f"{min(corr_scores[2:]) / max(corr_scores[:2]):.1f}",
        "corr_lift_hi": f"{max(corr_scores[2:]) / min(corr_scores[:2]):.1f}",
        "mb_acc": f"{mb_correct / mb_n * 100:.1f}%", "mb_correct": str(mb_correct), "mb_n": str(mb_n),
        "mb_lat_ratio": f"{sorter_lat / mb_lat:.0f}", "mb_cost_ratio": f"{sorter_cost / mb_cost:.0f}",
        "sorter_acc": f"{sorter_acc * 100:.0f}%", "sorter_lat": f"{sorter_lat:g} s", "mb_lat": f"{mb_lat:g} s",
        "sorter_cost": f"${sorter_cost:.6f}", "mb_cost": f"${mb_cost:.6f}",
        "pick_cov": f"{pick['coverage'] * 100:.1f}%", "pick_acc": f"{pick['accuracy'] * 100:.2f}%", "pick_t": f"{pick_t:.2f}",
        "mb_corp": f"{next(r['c'] / r['n'] for r in mb_acc if r['t'] == 'Corporate records') * 100:.0f}%",
        "multi": f"{multi * 100:.1f}%", "single": f"{single * 100:.1f}%",
        "api_merger_model": "qwen/qwen3.7-flash",
        "overlap_doc": overlap[0][0] if len(overlap) == 1 else "",
        "overlap_old": f"{overlap[0][1]:.4f}" if overlap else "", "overlap_new": f"{overlap[0][2]:.4f}" if overlap else "",
        "n_figures": "", "n_sources": "",
    }
    check(len(overlap) == 1, f"expected one doc shared by c5 and Run B, found {len(overlap)}")

    data = {
        "types": types, "quality": quality, "cost": cost, "wall": wall, "conc": conc, "tokens": tokens,
        "history": history, "rel": rel, "spend": spend, "total_spend": total_spend,
        "mb_acc": mb_acc, "mb_ece": [{"h": k, "v": v} for k, v in sorted(ece.items(), key=lambda kv: kv[1])],
        "mb_risk": [[r["threshold"], r["coverage"], r["accuracy"], r["n"]] for r in risk_rows],
        "mb_pick": pick_t, "per_doc": {k: docs[k] for k in ("insurance", "correspondence_a", "correspondence_b", "contracts_c8")},
        "text": t,
    }
    sources = sorted({p["source"] for p in PROVENANCE})
    t["n_figures"], t["n_sources"] = str(len({p["key"] for p in PROVENANCE})), str(len(sources))
    data["issues"] = list(ISSUES)
    data["provenance"] = list({p["key"]: p for p in PROVENANCE}.values())
    return data


def cost_of(rows, name):
    return next(v for k, v in rows if k == name)
