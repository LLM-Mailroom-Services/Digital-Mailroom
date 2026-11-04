#!/usr/bin/env python3
"""Build the decision-reviewer report assets under ``reports/decisions/``.

Everything here is derived from files tracked in this repository; nothing is
fetched and no model is called.

  python reports/decisions/build_decisions_report.py           # write figures, data, dashboard
  python reports/decisions/build_decisions_report.py --check   # exit 1 if any output is stale

Inputs
  reports/reviewer-calibration/*.json      cutoffs, routing, per-class results
  reports/extraction-gate/*.calibration.json
  data/handoff/sorter-qwen3.7-flash/*      per-document Qwen tokens, latency, confidence
  config/api_prices.yaml                   OpenRouter price sheet (Qwen tiers)
Figures that restate numbers which only exist in the prose reports
(reviewer-calibration-luna-decisions.md, config/decisions/LINEAGE.yaml,
sorter-qwen3.7-flash-audit.md) take them from ``RECORDED`` below, each with the
file it comes from.

Stdlib only. Colour roles follow the dataviz skill's reference palette
(see data/palette-validation.txt).
"""
from __future__ import annotations

import argparse
import csv
import html
import io
import json
import math
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
REPORTS = REPO / "reports"
HANDOFF = REPO / "data" / "handoff" / "sorter-qwen3.7-flash"

CLASSES = ["contract", "corporate_record", "correspondence", "insurance_claim", "merger_agreement"]
CLASS_LABEL = {
    "contract": "contract",
    "corporate_record": "corporate record",
    "correspondence": "correspondence",
    "insurance_claim": "insurance claim",
    "merger_agreement": "merger agreement",
}

# --------------------------------------------------------------------------- #
# Qwen 3.7 Flash price sheet (config/api_prices.yaml, checked 2026-11-01).
# A tier applies to a whole call whose prompt reaches min_prompt_tokens.
# --------------------------------------------------------------------------- #
QWEN_TIERS = [(256_000, 0.20, 0.80), (32_000, 0.10, 0.40), (0, 0.03, 0.13)]  # USD / 1M tokens
QWEN_FLAT = (0.03, 0.13)


def qwen_call_usd(prompt_tokens: int, completion_tokens: int, tiered: bool = True) -> float:
    if not tiered:
        return (prompt_tokens * QWEN_FLAT[0] + completion_tokens * QWEN_FLAT[1]) / 1e6
    for floor, p_in, p_out in QWEN_TIERS:
        if prompt_tokens >= floor:
            return (prompt_tokens * p_in + completion_tokens * p_out) / 1e6
    raise AssertionError


# --------------------------------------------------------------------------- #
# Numbers that exist only in prose reports. Every entry names its source.
# --------------------------------------------------------------------------- #
CAL = "reports/reviewer-calibration/reviewer-calibration-luna-decisions.md"
LIN = "config/decisions/LINEAGE.yaml"
AUD = "reports/sorter-handoff/sorter-qwen3.7-flash-audit.md"

# family: agent = Qwen agent call, qwen = Qwen LLM reviewer (measured separately), dec = Decisions model
RUNS = [
    # label, family, split, n, correct, wrong at confidence >= 0.90 (wrong, n_wrong), cost_usd, source
    dict(run="reviewer-calibration-luna-decisions", label="Decisions model, question set v1", family="dec", split="train", n=735, correct=723,
         hi=(0, 12), cost=0.71, src=CAL),
    dict(run="reviewer-calibration-luna-decisions-v2", label="Decisions model, question set v2", family="dec", split="train", n=735, correct=735,
         hi=None, cost=0.86, src=CAL),
    dict(run="reviewer-validation-luna-decisions-v2-test", label="Decisions model, question set v2", family="dec", split="test", n=323, correct=318,
         hi=(2, 5), cost=0.24, src=CAL),
    dict(run="reviewer-validation-luna-decisions-v3.0.0-test", label="Decisions model, question set v3.0.0", family="dec", split="test", n=323, correct=318,
         hi=None, cost=0.1905, src=LIN),
]

# Subclass accuracy before/after the v1 -> v2 question-set rewrite (train draw), CAL "Improvement loop".
SUBCLASS_V1_V2 = [
    ("contract / collaboration", 1, 6, 6, 6),
    ("contract / supply", 1, 6, 5, 6),
    ("contract / affiliate", 2, 5, 5, 5),
    ("correspondence / demand", 4, 21, 15, 21),
    ("correspondence / notice", 10, 21, 14, 21),
    ("correspondence / memo", 12, 21, 18, 21),
    ("correspondence / meeting_request", 18, 21, 14, 21),
]

# Sorter (Qwen agent) class errors by pattern on train, AUD "Is the sorter output fit ...".
SORTER_ERRORS = [
    ("corporate record -> contract (indentures)", 49),
    ("corporate record -> contract (rights instruments)", 40),
    ("correspondence -> unknown (bare URLs, stubs)", 30),
    ("all other patterns", 8),
]

# Decisions latency (seconds) at concurrency 16 on the 735-document train draw (CAL); Qwen runs are measured below.
LATENCY_RECORDED = {"dec": (0.5, 0.9)}


# --------------------------------------------------------------------------- #
# Loading and derived numbers
# --------------------------------------------------------------------------- #
def jload(p: Path):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def rows_jsonl(p: Path):
    with open(p, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def pctl(sorted_vals, q):
    return sorted_vals[min(len(sorted_vals) - 1, int(len(sorted_vals) * q))]


def fisher_two_sided(a, b, c, d):
    """Two-sided Fisher exact p for [[a, b], [c, d]] (stdlib, hypergeometric)."""
    n = a + b + c + d
    r1, c1 = a + b, a + c
    prob = lambda x: math.comb(r1, x) * math.comb(n - r1, c1 - x) / math.comb(n, c1)
    p0 = prob(a)
    return sum(prob(x) for x in range(max(0, c1 - (n - r1)), min(r1, c1) + 1) if prob(x) <= p0 + 1e-12)


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


HALF = "reviewer-calibration-luna-decisions-v3.1.0-train-half"


def half_train(N):
    """Question set 3.1.0 with the sorter handoff on 1,491 train documents: accuracy, routing outcomes, cost."""
    D = REPORTS / "reviewer-calibration"
    meta = jload(D / f"{HALF}.run.json")
    rows = rows_jsonl(D / f"{HALF}.items.jsonl")
    cal = jload(D / f"{HALF}.json")
    out = {"meta": meta, "rows": rows, "calibration": cal["classes"], "own_cutoffs": meta["cutoffs_own_crossfit"], "v2_cutoffs": meta["cutoffs_v2"]}

    def acc_block(sel):
        cls = [r for r in sel if r["use_for_class"]]
        rc = [r for r in cls if r["reviewer_class"] == r["target_class"]]
        sc = [r for r in cls if r["sorter_class"] == r["target_class"]]
        rcs, scs = {r["id"] for r in rc}, {r["id"] for r in sc}
        b, c = len(rcs - scs), len(scs - rcs)
        sub = [r for r in sel if r["use_for_subclass"]]
        rs = {r["id"] for r in sub if r["reviewer_subclass"] == r["target_subclass"]}
        ss = {r["id"] for r in sub if r["sorter_subclass_correct"]}
        b2, c2 = len(rs - ss), len(ss - rs)
        per = {}
        for k in CLASSES:
            ci = [r for r in cls if r["target_class"] == k]
            si = [r for r in sub if r["target_class"] == k]
            if ci:
                per[k] = dict(n=len(ci), class_reviewer=sum(r["id"] in rcs for r in ci), class_sorter=sum(r["id"] in scs for r in ci),
                              sub_n=len(si), sub_reviewer=sum(r["id"] in rs for r in si), sub_sorter=sum(r["id"] in ss for r in si))
        return dict(documents=len(sel), class_scored=len(cls), class_reviewer=len(rc), class_sorter=len(sc), class_fixed=b, class_broke=c,
                    class_p=mcnemar_exact(b, c), sub_scored=len(sub), sub_reviewer=len(rs), sub_sorter=len(ss), sub_fixed=b2, sub_broke=c2,
                    sub_p=mcnemar_exact(b2, c2), per_class=per)

    out["all"] = acc_block(rows)
    out["clean"] = acc_block([r for r in rows if not r["prior_reviewer_evidence"]])
    out["prior_evidence_docs"] = sum(r["prior_reviewer_evidence"] for r in rows)

    def decompose(flag, gated):
        c = {"routed_correct_sorter_right": 0, "routed_correct_sorter_wrong": 0, "misrouted": 0, "parked_sorter_wrong": 0, "parked_sorter_right": 0}
        for r in rows:
            if not r["use_for_class"]:
                continue
            parked = r[flag] or (gated and r["reviewer_class"] != r["sorter_class"])
            rc, sr = r["reviewer_class"] == r["target_class"], r["sorter_class"] == r["target_class"]
            if parked:
                c["parked_sorter_right" if sr else "parked_sorter_wrong"] += 1
            elif rc:
                c["routed_correct_sorter_right" if sr else "routed_correct_sorter_wrong"] += 1
            else:
                c["misrouted"] += 1
        c["scored"] = sum(c.values())
        c["routed_correctly"] = c["routed_correct_sorter_right"] + c["routed_correct_sorter_wrong"]
        c["sent_unattended"] = c["routed_correctly"] + c["misrouted"]
        c["parked"] = c["parked_sorter_right"] + c["parked_sorter_wrong"]
        c["sorter_errors"] = c["routed_correct_sorter_wrong"] + c["parked_sorter_wrong"] + sum(
            1 for r in rows if r["use_for_class"] and r["sorter_class"] != r["target_class"] and r["reviewer_class"] != r["target_class"]
            and not (r[flag] or (gated and r["reviewer_class"] != r["sorter_class"])))
        return c

    out["routing"] = {"v2_pipeline_rule": decompose("parked_at_v2_cutoffs", True), "v2_reviewer_alone": decompose("parked_at_v2_cutoffs", False),
                      "own_pipeline_rule": decompose("parked_at_own_cutoffs", True), "own_reviewer_alone": decompose("parked_at_own_cutoffs", False)}
    out["sorter_alone_wrong"] = sum(1 for r in rows if r["use_for_class"] and r["sorter_class"] != r["target_class"])
    out["sorter_confidence_ge_0_95"] = sum(r["sorter_confidence"] >= 0.95 for r in rows)
    out["sorter_confidence_lt_0_90"] = sum(r["sorter_confidence"] < 0.90 for r in rows)
    out["cost_usd"] = meta["cost_usd_from_usage"]
    out["unit_usd_doc"] = meta["cost_usd_from_usage"] / meta["documents"]
    out["x_vs_qwen_agent_train"] = out["unit_usd_doc"] / (N["qwen_train"]["tiered_usd"] / N["qwen_train"]["n"])
    lat = sorted(r["latency_ms"] / 1000 for r in rows)
    out["latency_s"] = {"p50": lat[len(lat) // 2], "p95": lat[int(len(lat) * 0.95)]}
    need = {}
    for r in rows:
        if not r["use_for_class"]:
            continue
        k = ("class_wrong" if r["sorter_class"] != r["target_class"] else
             "subclass_wrong" if r["use_for_subclass"] and not r["sorter_subclass_correct"] else "sorter_right")
        need.setdefault(k, {})
        need[k][r["verdict"]] = need[k].get(r["verdict"], 0) + 1
    out["verdict_by_need"] = need
    out["human_verdict_docs"] = sum(r["route_to_human"] for r in rows)
    out["multiple_documents"] = sum(r["verdict"] == "multiple_documents" for r in rows)
    return out


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n)


def compute():
    N = {}
    # ---- Qwen agent (sorter) per-document tokens, tiered and flat cost ---------------------------
    for split in ("test", "train"):
        rows = [r for r in rows_jsonl(HANDOFF / f"{split}.jsonl") if r["ok"]]
        tiered = sum(qwen_call_usd(r["prompt_tokens"], r["completion_tokens"]) for r in rows)
        flat = sum(qwen_call_usd(r["prompt_tokens"], r["completion_tokens"], tiered=False) for r in rows)
        lat = sorted(r["latency_ms"] / 1000 for r in rows)
        by_class = {}
        for r in rows:
            c = by_class.setdefault(r["expected_doc_class"], dict(n=0, tiered=0.0, flat=0.0, ptok=0))
            c["n"] += 1
            c["tiered"] += qwen_call_usd(r["prompt_tokens"], r["completion_tokens"])
            c["flat"] += qwen_call_usd(r["prompt_tokens"], r["completion_tokens"], tiered=False)
            c["ptok"] += r["prompt_tokens"]
        pt = [r["prompt_tokens"] for r in rows]
        N[f"qwen_{split}"] = dict(
            n=len(rows), tiered_usd=tiered, flat_usd=flat, prompt_tokens=sum(pt),
            completion_tokens=sum(r["completion_tokens"] for r in rows),
            docs_ge_32k=sum(p >= 32_000 for p in pt), docs_ge_256k=sum(p >= 256_000 for p in pt),
            p50_s=pctl(lat, 0.50), p95_s=pctl(lat, 0.95), by_class=by_class,
        )
    man = jload(HANDOFF / "manifest.json")["splits"]
    for split in ("test", "train"):
        N[f"qwen_{split}"]["manifest_flat_usd"] = man[split]["list_cost_usd"]
        N[f"qwen_{split}"]["class_correct"] = man[split]["class_correct"]
        N[f"qwen_{split}"]["class_n"] = man[split]["documents"]
        N[f"qwen_{split}"]["human_review_rate"] = man[split]["routed_to_human_review_sorter_alone"]["routed_to_human_review_rate"]

    # ---- the measured 1x LLM reviewer: Qwen 3.7 Flash on the sorter_reviewer route, same 323 test documents ----
    qr = jload(REPORTS / "reviewer-calibration/reviewer-validation-qwen-flash-test.json")
    qrows = rows_jsonl(REPORTS / "reviewer-calibration/reviewer-validation-qwen-flash-test.items.jsonl")
    qr["tiered_usd"] = sum(qwen_call_usd(r["prompt_tokens"], r["completion_tokens"]) for r in qrows)
    qr["flat_usd"] = sum(qwen_call_usd(r["prompt_tokens"], r["completion_tokens"], tiered=False) for r in qrows)
    assert abs(qr["tiered_usd"] - qr["list_cost_usd_tiered"]) < 5e-4 and abs(qr["flat_usd"] - qr["list_cost_usd_flat"]) < 5e-4
    N["qwen_reviewer"] = qr
    N["qwen_reviewer_rows"] = qrows

    # ---- 1x unit and pipeline multiples on the 323-document held-out test split ---------------
    t = N["qwen_test"]
    unit = t["tiered_usd"] / t["n"]            # USD per document for one Qwen agent call
    unit_flat = t["flat_usd"] / t["n"]
    reviewers = {
        "qwen_reviewer": dict(label="Qwen 3.7 Flash reviewer, default prompt", usd_doc=N["qwen_reviewer"]["tiered_usd"] / t["n"], measured=True),
        "decisions_v2": dict(label="Decisions model, question set v2", usd_doc=0.24 / 323, measured=True),
        "decisions_v3_0_0": dict(label="Decisions model, question set v3.0.0", usd_doc=0.1905 / 323, measured=True),
    }
    for k, v in reviewers.items():
        v["x_tiered"] = v["usd_doc"] / unit
        # under the flat sensitivity a Qwen reviewer is priced from its own tokens at the lowest tier
        v["x_flat"] = (N["qwen_reviewer"]["flat_usd"] / t["n"] if k == "qwen_reviewer" else v["usd_doc"]) / unit_flat
    N["unit_usd_doc"] = unit
    N["unit_flat_usd_doc"] = unit_flat
    N["reviewers"] = reviewers
    trad = 1 + reviewers["qwen_reviewer"]["x_tiered"]          # Qwen agent + measured Qwen reviewer
    trad_flat = 1 + reviewers["qwen_reviewer"]["x_flat"]
    N["traditional_x"], N["traditional_x_flat"] = trad, trad_flat
    for k in ("decisions_v2", "decisions_v3_0_0"):
        N[f"{k}_pipeline_x"] = 1 + reviewers[k]["x_tiered"]
        N[f"{k}_saving_vs_traditional"] = 1 - N[f"{k}_pipeline_x"] / trad
        N[f"{k}_pipeline_x_flat"] = 1 + reviewers[k]["x_flat"]
        N[f"{k}_saving_vs_traditional_flat"] = 1 - N[f"{k}_pipeline_x_flat"] / trad_flat
        N[f"{k}_vs_qwen_reviewer"] = reviewers[k]["usd_doc"] / reviewers["qwen_reviewer"]["usd_doc"]

    # ---- human-review load (documents a person must touch per 1,000) ------------------------
    v2 = jload(REPORTS / "reviewer-calibration/reviewer-validation-luna-decisions-v2-test.routing.json")
    v3 = jload(REPORTS / "reviewer-calibration/reviewer-validation-luna-decisions-v3.0.0-test.routing.json")
    N["routing"] = {"v2": v2, "v3": v3}
    qcov = N["qwen_reviewer"]["unattended_if_unknown_parks"]["0.9"]
    person = {
        "Qwen agent alone": t["human_review_rate"],
        "Qwen reviewer (default prompt)": qcov["parked_for_a_person"] / t["n"],
        "Decisions v2": v2["routed_to_human_review_rate"],
        "Decisions v3.0.0": v3["routed_to_human_review_rate"],
    }
    N["person_per_1000"] = {k: v * 1000 for k, v in person.items()}
    extra_v2 = (reviewers["decisions_v2"]["usd_doc"]) * 1000       # USD per 1,000 documents for the Decisions call
    avoided_v2 = (person["Qwen agent alone"] - person["Decisions v2"]) * 1000
    N["breakeven_v2_usd_per_review"] = extra_v2 / avoided_v2
    extra_v3 = (reviewers["decisions_v3_0_0"]["usd_doc"]) * 1000
    avoided_v3 = (person["Qwen agent alone"] - person["Decisions v3.0.0"]) * 1000
    N["breakeven_v3_usd_per_review"] = extra_v3 / avoided_v3
    N["avoided_v2_per_1000"] = avoided_v2
    N["avoided_v3_per_1000"] = avoided_v3
    N["extra_v2_per_1000"] = extra_v2
    N["extra_v3_per_1000"] = extra_v3

    # ---- calibration cutoffs ----------------------------------------------------------------
    cal_files = [
        ("Decisions\nv1", "reviewer-calibration-luna-decisions"),
        ("Decisions\nv2", "reviewer-calibration-luna-decisions-v2"),
    ]
    N["cutoffs"] = []
    for lab, name in cal_files:
        d = jload(REPORTS / f"reviewer-calibration/{name}.json")
        N["cutoffs"].append((lab, name, {c: d["classes"][c] for c in CLASSES}))

    # ---- extraction gate ---------------------------------------------------------------------
    gate = {}
    for key, name in (("v1.0.0 baseline", "extraction-gate-luna-v1.0.0-baseline"),
                      ("v1.1.0 baseline", "extraction-gate-luna-v1.1.0-baseline"),
                      ("v1.1.0 round 2", "extraction-gate-luna-v1.1.0-r2"),
                      ("v1.1.0 pooled", "extraction-gate-luna-v1.1.0-pooled")):
        gate[key] = jload(REPORTS / f"extraction-gate/{name}.calibration.json")
    N["gate"] = gate
    N["half"] = half_train(N)
    return N


# --------------------------------------------------------------------------- #
# Chart kit: tokens, SVG helpers
# --------------------------------------------------------------------------- #
LIGHT = dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781", grid="#e1e0d9", axis="#c3c2b7",
             s1="#2a78d6", s2="#eb6834", s3="#1baf7a", oth="#b9b8b0", crit="#d03b3b")
DARK = dict(surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", muted="#898781", grid="#2c2c2a", axis="#383835",
            s1="#3987e5", s2="#d95926", s3="#199e70", oth="#5f5e5a", crit="#d03b3b")
# Sequential blue: five bins. Light mode: light = low. Dark mode flips the anchor: dark = low.
SEQ_LIGHT = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
SEQ_DARK = ["#0d366b", "#184f95", "#2a78d6", "#6da7ec", "#cde2fb"]


def _lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _ink_on(fill):
    L = _lum(fill)
    white = 1.05 / (L + 0.05)
    black = (L + 0.05) / (0.0 + 0.05 + _lum("#0b0b0b"))
    return "#ffffff" if white >= black else "#0b0b0b"


def theme_css():
    def block(t, seq):
        s = ";".join(f"--{k}:{v}" for k, v in t.items())
        s += ";" + ";".join(f"--h{i}:{c};--ht{i}:{_ink_on(c)}" for i, c in enumerate(seq))
        return s

    return (
        f".viz{{color-scheme:light;{block(LIGHT, SEQ_LIGHT)}}}"
        f"@media (prefers-color-scheme:dark){{:root:not([data-theme=\"light\"]) .viz{{color-scheme:dark;{block(DARK, SEQ_DARK)}}}}}"
        f":root[data-theme=\"dark\"] .viz{{color-scheme:dark;{block(DARK, SEQ_DARK)}}}"
        ".viz text{font-family:system-ui,-apple-system,'Segoe UI',sans-serif}"
        ".bg{fill:var(--surface)}"
        ".ti{fill:var(--ink);font-size:15px;font-weight:600}"
        ".su{fill:var(--ink2);font-size:12px}"
        ".lb{fill:var(--ink2);font-size:12px}"
        ".tk{fill:var(--muted);font-size:11px}"
        ".vl{fill:var(--ink);font-size:12px;font-weight:600}"
        ".fn{fill:var(--muted);font-size:10.5px}"
        ".grid{stroke:var(--grid);stroke-width:1;fill:none}"
        ".axis{stroke:var(--axis);stroke-width:1;fill:none}"
        ".s1{fill:var(--s1)}.s2{fill:var(--s2)}.s3{fill:var(--s3)}.oth{fill:var(--oth)}.crit{fill:var(--crit)}"
        ".k1{stroke:var(--s1)}.k2{stroke:var(--s2)}.k3{stroke:var(--s3)}.ko{stroke:var(--oth)}"
        ".ring{stroke:var(--surface);stroke-width:2}"
        ".hollow{fill:var(--surface);stroke-width:2}"
        + "".join(f".h{i}{{fill:var(--h{i})}}.ht{i}{{fill:var(--ht{i});font-size:12px;font-weight:600}}" for i in range(5))
        + ".mk{outline:none}.mk:hover .m,.mk:focus .m{opacity:.82}.mk:focus .hit{stroke:var(--ink);stroke-width:1.5}"
        ".hit{fill:transparent;stroke:transparent}"
    )


def esc(s):
    return html.escape(str(s), quote=True)


def tw(s, size=12):
    """Rough rendered width of s in px."""
    return sum(0.62 if ch.isupper() or ch in "mw" else 0.30 if ch in "il.,:;'|! " else 0.54 for ch in str(s)) * size


class Fig:
    def __init__(self, fid, title, sub, w=760, left=190, right=70, foot=None, legend=None):
        self.fid, self.title, self.sub, self.w, self.left, self.right = fid, title, sub, w, left, right
        self.foot = foot
        self.body = []
        self.table = None            # (headers, rows) - the table-view twin
        self.caption = ""
        sub_lines = textwrap.wrap(sub, width=int((w - 32) / 6.1)) if sub else []
        self.sub_lines = sub_lines
        y = 24 + 18 * len(sub_lines) + 10
        self.legend_y = y if legend else None
        self.legend = legend
        self.top = y + (40 if legend else 20)

    def add(self, s):
        self.body.append(s)

    def legend_svg(self):
        if not self.legend:
            return ""
        out, x = [], 16
        for name, cls in self.legend:
            if cls == "line":
                continue
            out.append(f'<rect x="{x}" y="{self.legend_y}" width="12" height="12" rx="3" class="{cls}"/>')
            out.append(f'<text x="{x + 18}" y="{self.legend_y + 10.5}" class="lb">{esc(name)}</text>')
            x += 18 + tw(name) + 22
        return "".join(out)

    def svg(self, h, standalone=True):
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {h}" width="{self.w}" height="{h}" '
                f'role="img" aria-labelledby="{self.fid}-t {self.fid}-d" font-family="system-ui,sans-serif">')
        desc = f'<title id="{self.fid}-t">{esc(self.title)}</title><desc id="{self.fid}-d">{esc(self.sub)}</desc>'
        style = f"<style>{theme_css()}</style>"
        g = [f'<g class="viz"><rect class="bg" x="0" y="0" width="{self.w}" height="{h}" rx="10"/>',
             f'<text x="16" y="24" class="ti">{esc(self.title)}</text>']
        for i, ln in enumerate(self.sub_lines):
            g.append(f'<text x="16" y="{42 + 18 * i}" class="su">{esc(ln)}</text>')
        g.append(self.legend_svg())
        g.extend(self.body)
        if self.foot:
            g.append(f'<text x="16" y="{h - 10}" class="fn">{esc(self.foot)}</text>')
        g.append("</g></svg>")
        return head + desc + style + "".join(g)


def mark(tip, inner, hit=None):
    """A hoverable / focusable mark group. `tip` lines are separated by newline."""
    h = ""
    if hit:
        x, y, w, hh = hit
        h = f'<rect class="hit" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{hh:.1f}"/>'
    return (f'<g class="mk" tabindex="0" data-tip="{esc(tip)}"><title>{esc(tip.replace(chr(10), " — "))}</title>'
            f'{h}{inner}</g>')


def rbar(x, y, w, h, cls, r=4, round_end=True):
    """Bar growing from x to the right: square at the baseline, r-rounded data end."""
    if w <= 0:
        return ""
    if not round_end or w < r * 2:
        return f'<rect class="m {cls}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"/>'
    return (f'<path class="m {cls}" d="M{x:.1f},{y:.1f}h{w - r:.1f}a{r},{r} 0 0 1 {r},{r}v{h - 2 * r:.1f}'
            f'a{r},{r} 0 0 1 -{r},{r}h-{w - r:.1f}z"/>')


def xscale(lo, hi, x0, x1):
    return lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)


def vgrid(fig, sx, ticks, y0, y1, fmt):
    for t in ticks:
        x = sx(t)
        fig.add(f'<line class="grid" x1="{x:.1f}" x2="{x:.1f}" y1="{y0}" y2="{y1}"/>')
        fig.add(f'<text class="tk" x="{x:.1f}" y="{y1 + 15}" text-anchor="middle">{esc(fmt(t))}</text>')
    fig.add(f'<line class="axis" x1="{sx(ticks[0]):.1f}" x2="{sx(ticks[-1]):.1f}" y1="{y1}" y2="{y1}"/>')


def hbars(fig, rows, series, xmax, ticks, fmt, vfmt, pitch=34, thick=18, gap=2, stacked=True):
    """Horizontal bar rows. rows: dict(label, sub, vals[list per series], tips[list], total_label).
    stacked=True: segments end to end; stacked=False: one thin bar per series inside the row."""
    x0, x1 = fig.left, fig.w - fig.right
    sx = xscale(0, xmax, x0, x1)
    n = len(rows)
    per = len(series) if not stacked else 1
    pitch = pitch if stacked else (per * (thick + 2) + 16)
    y_top = fig.top
    y_bot = y_top + n * pitch
    vgrid(fig, sx, ticks, y_top - 4, y_bot, fmt)
    for i, r in enumerate(rows):
        yc = y_top + i * pitch + pitch / 2
        fig.add(f'<text class="lb" x="{x0 - 10}" y="{yc + 4:.1f}" text-anchor="end">{esc(r["label"])}</text>')
        if r.get("sub"):
            fig.add(f'<text class="tk" x="{x0 - 10}" y="{yc + 17:.1f}" text-anchor="end">{esc(r["sub"])}</text>')
        if stacked:
            cx = x0
            vals = r["vals"]
            last = max(j for j, v in enumerate(vals) if v > 0) if any(v > 0 for v in vals) else -1
            for j, v in enumerate(vals):
                if v <= 0:
                    continue
                w = sx(v) - x0
                draw_w = w - (gap if j != last else 0)
                bar = rbar(cx, yc - thick / 2, draw_w, thick, series[j][1], round_end=(j == last))
                fig.add(mark(r["tips"][j], bar, hit=(cx, yc - pitch / 2 + 2, w, pitch - 4)))
                cx += w
            fig.add(f'<text class="vl" x="{cx + 8:.1f}" y="{yc + 4:.1f}">{esc(r["total_label"])}</text>')
        else:
            th = thick - 4
            y = yc - (per * (th + 2)) / 2
            for j, v in enumerate(r["vals"]):
                w = max(0.0, sx(v) - x0)
                fig.add(mark(r["tips"][j], rbar(x0, y, w, th, series[j][1]), hit=(x0, y - 1, max(w, 24), th + 2)))
                fig.add(f'<text class="vl" x="{x0 + w + 7:.1f}" y="{y + th - 3:.1f}">{esc(vfmt(v))}</text>')
                y += th + 2
    fig.add(f'<line class="axis" x1="{x0}" x2="{x0}" y1="{y_top - 4}" y2="{y_bot}"/>')
    return y_bot + 22


def hdots(fig, rows, lo, hi, ticks, fmt, pitch=30, hit=24, ref=None):
    """Dot plot rows. rows: dict(label, sub, line=(a,b)|None, pts=[dict(v, cls, hollow, r, tip)])."""
    x0, x1 = fig.left, fig.w - fig.right
    sx = xscale(lo, hi, x0, x1)
    y_top = fig.top
    y_bot = y_top + len(rows) * pitch
    vgrid(fig, sx, ticks, y_top - 4, y_bot, fmt)
    if ref is not None:
        v, name = ref
        fig.add(f'<line class="axis" x1="{sx(v):.1f}" x2="{sx(v):.1f}" y1="{y_top - 4}" y2="{y_bot}" stroke-width="1.5"/>')
        fig.add(f'<text class="tk" x="{sx(v):.1f}" y="{y_top - 8}" text-anchor="middle">{esc(name)}</text>')
    for i, r in enumerate(rows):
        yc = y_top + i * pitch + pitch / 2
        fig.add(f'<text class="lb" x="{x0 - 10}" y="{yc + 4:.1f}" text-anchor="end">{esc(r["label"])}</text>')
        if r.get("line"):
            a, b = r["line"]
            fig.add(f'<line x1="{sx(a):.1f}" x2="{sx(b):.1f}" y1="{yc:.1f}" y2="{yc:.1f}" class="{r.get("line_cls", "ko")}" stroke-width="2" stroke-linecap="round"/>')
        for p in r["pts"]:
            cx = sx(p["v"])
            rr = p.get("r", 5)
            if p.get("hollow"):
                dot = f'<circle class="m hollow k{p["cls"][1:] if p["cls"] != "oth" else "o"}" cx="{cx:.1f}" cy="{yc:.1f}" r="{rr}"/>'
            else:
                dot = f'<circle class="m ring {p["cls"]}" cx="{cx:.1f}" cy="{yc:.1f}" r="{rr}"/>'
            fig.add(mark(p["tip"], dot, hit=(cx - hit / 2, yc - hit / 2, hit, hit)))
            if p.get("label"):
                lx = sx(p.get("label_at", p["v"])) + rr + 7
                if p.get("label_left"):
                    fig.add(f'<text class="vl" x="{cx - rr - 7:.1f}" y="{yc + 4:.1f}" text-anchor="end">{esc(p["label"])}</text>')
                else:
                    fig.add(f'<text class="vl" x="{lx:.1f}" y="{yc + 4:.1f}">{esc(p["label"])}</text>')
    fig.add(f'<line class="axis" x1="{x0}" x2="{x0}" y1="{y_top - 4}" y2="{y_bot}"/>')
    return y_bot + 22


def heatmap(fig, row_labels, col_labels, vals, texts, tips, bins, cw=92, ch=40, col_w_label=None):
    """Cells coloured by sequential bin (0..4); text printed in each cell."""
    x0 = fig.left
    y0 = fig.top + 34
    for j, cl in enumerate(col_labels):
        for k, part in enumerate(cl.split("\n")):
            fig.add(f'<text class="lb" x="{x0 + j * cw + cw / 2:.1f}" y="{y0 - 22 + k * 13:.1f}" text-anchor="middle">{esc(part)}</text>')
    for i, rl in enumerate(row_labels):
        fig.add(f'<text class="lb" x="{x0 - 10}" y="{y0 + i * ch + ch / 2 + 4:.1f}" text-anchor="end">{esc(rl)}</text>')
        for j in range(len(col_labels)):
            b = bins[i][j]
            x, y = x0 + j * cw, y0 + i * ch
            if b is None:
                fig.add(f'<text class="tk" x="{x + cw / 2:.1f}" y="{y + ch / 2 + 4:.1f}" text-anchor="middle">–</text>')
                continue
            cell = (f'<rect class="m h{b}" x="{x + 1:.1f}" y="{y + 1:.1f}" width="{cw - 2}" height="{ch - 2}" rx="4"/>'
                    f'<text class="ht{b}" x="{x + cw / 2:.1f}" y="{y + ch / 2 + 4:.1f}" text-anchor="middle">{esc(texts[i][j])}</text>')
            fig.add(mark(tips[i][j], cell))
    return y0 + len(row_labels) * ch + 14


def scale_legend(fig, x, y, labels):
    """Five-step sequential key with end captions."""
    for i in range(5):
        fig.add(f'<rect class="h{i}" x="{x + i * 26}" y="{y}" width="24" height="10" rx="2"/>')
    fig.add(f'<text class="tk" x="{x - 6}" y="{y + 9}" text-anchor="end">{esc(labels[0])}</text>')
    fig.add(f'<text class="tk" x="{x + 5 * 26 + 4}" y="{y + 9}">{esc(labels[1])}</text>')


def fmt_pct(v, d=0):
    return f"{v * 100:.{d}f}%"


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def fig_cost_stack(N):
    """F01: pipelines in multiples of one Qwen agent call (the 1x), held-out test split."""
    R = N["reviewers"]
    rows_spec = [
        ("Qwen agent alone", "no reviewer", None, None),
        ("Agent + Qwen reviewer", "Qwen 3.7 Flash · measured", "qwen_reviewer", "s2"),
        ("Agent + Decisions v2", "measured", "decisions_v2", "s3"),
        ("Agent + Decisions v3.0.0", "measured", "decisions_v3_0_0", "s3"),
    ]
    f = Fig("f01", "A Decisions review costs about what a Qwen review costs",
            "Cost per document in multiples of one Qwen 3.7 Flash agent call (1x = $%.5f, tiered OpenRouter price). "
            "Same 323 held-out test documents." % N["unit_usd_doc"],
            legend=[("Qwen agent call (1x)", "s1"), ("Qwen reviewer call", "s2"), ("Decisions model call", "s3")],
            left=210, right=70, foot="Every reviewer cost is a recorded or measured run on the same 323 test documents.")
    rows, tab = [], []
    for lab, sub, key, cls in rows_spec:
        if key is None:
            vals = [1.0]
            segs = ["Qwen agent call: 1.00x"]
            tot = "1.00x"
            usd = N["unit_usd_doc"] * 1000
        else:
            x = R[key]["x_tiered"]
            vals = [1.0, x]
            segs = ["Qwen agent call: 1.00x", f"{R[key]['label']}: {x:.2f}x ({'measured' if R[key]['measured'] else 'modelled'})"]
            tot = f"{1 + x:.2f}x"
            usd = (N["unit_usd_doc"] + R[key]["usd_doc"]) * 1000
        series = [("a", "s1")] + ([("r", cls)] if key else [])
        rows.append(dict(label=lab, sub=sub, vals=vals, tips=[f"{lab}\n{s}\n${usd:,.2f} per 1,000 documents" for s in segs],
                         total_label=tot, series=series))
        tab.append([lab, "measured" if key and R[key]["measured"] else ("modelled" if key else "measured"),
                    f"{vals[0]:.2f}", f"{(vals[1] if key else 0):.2f}", tot.rstrip("x"), f"{usd:,.2f}"])
    # hbars takes one series list; draw per row manually to keep segment colours per row
    x0, x1 = f.left, f.w - f.right
    sx = xscale(0, 2.2, x0, x1)
    pitch, thick, gap = 40, 18, 2
    y_top = f.top
    y_bot = y_top + len(rows) * pitch
    vgrid(f, sx, [0, 0.5, 1.0, 1.5, 2.0], y_top - 4, y_bot, lambda t: f"{t:g}x")
    for i, r in enumerate(rows):
        yc = y_top + i * pitch + pitch / 2
        f.add(f'<text class="lb" x="{x0 - 10}" y="{yc + 1:.1f}" text-anchor="end">{esc(r["label"])}</text>')
        f.add(f'<text class="tk" x="{x0 - 10}" y="{yc + 14:.1f}" text-anchor="end">{esc(r["sub"])}</text>')
        cx = x0
        for j, v in enumerate(r["vals"]):
            w = sx(v) - x0
            last = j == len(r["vals"]) - 1
            f.add(mark(r["tips"][j], rbar(cx, yc - thick / 2, w - (0 if last else gap), thick, r["series"][j][1], round_end=last),
                       hit=(cx, yc - pitch / 2 + 2, w, pitch - 4)))
            cx += w
        f.add(f'<text class="vl" x="{cx + 8:.1f}" y="{yc + 4:.1f}">{esc(r["total_label"])}</text>')
    f.add(f'<line class="axis" x1="{x0}" x2="{x0}" y1="{y_top - 4}" y2="{y_bot}"/>')
    f.add(f'<text class="tk" x="{sx(N["traditional_x"]):.1f}" y="{y_top - 8}" text-anchor="middle">agent + Qwen reviewer</text>')
    f.add(f'<line class="axis" x1="{sx(N["traditional_x"]):.1f}" x2="{sx(N["traditional_x"]):.1f}" y1="{y_top - 4}" y2="{y_bot}"/>')
    f.table = (["pipeline", "basis", "agent (x)", "reviewer (x)", "total (x)", "USD per 1,000 docs"], tab)
    return f, y_bot + 40


def fig_sensitivity(N):
    """F02: pipelines priced with Qwen at its tiered sheet and at the flat lowest tier."""
    R = N["reviewers"]
    f = Fig("f02", "Against a measured Qwen reviewer, Decisions saves only on v3.0.0, and only at tiered prices",
            "Total cost, agent + reviewer, in multiples of one Qwen agent call. The Qwen price sheet charges 3.3x per token "
            "once a call's prompt reaches 32k tokens (24 of 323 agent calls, 23 of 323 reviewer calls).",
            legend=[("Tiered Qwen price (price sheet)", "s1"), ("Flat $0.03 / $0.13 (lowest tier for every call)", "oth")],
            left=210, right=70, foot="Decisions is billed at $0.10 per 1M input tokens with no output charge in both columns.")
    rows, tab = [], []
    trad_t, trad_f = N["traditional_x"], N["traditional_x_flat"]
    rows.append(dict(label="Agent + Qwen reviewer", vals=[trad_t, trad_f],
                     tips=[f"Agent + Qwen reviewer (measured)\nTiered Qwen price: {trad_t:.2f}x",
                           f"Agent + Qwen reviewer (measured)\nFlat Qwen price: {trad_f:.2f}x"]))
    tab.append(["Agent + Qwen reviewer (measured)", f"{trad_t:.2f}", "base", f"{trad_f:.2f}", "base"])
    for key, lab in (("decisions_v3_0_0", "Agent + Decisions v3.0.0"), ("decisions_v2", "Agent + Decisions v2")):
        xt, xf = 1 + R[key]["x_tiered"], 1 + R[key]["x_flat"]
        st_, sf = 1 - xt / trad_t, 1 - xf / trad_f
        rows.append(dict(label=lab, vals=[xt, xf],
                         tips=[f"{lab}\nTiered Qwen price: {xt:.2f}x vs {trad_t:.2f}x ({st_ * 100:+.1f}% saving)",
                               f"{lab}\nFlat Qwen price: {xf:.2f}x vs {trad_f:.2f}x ({sf * 100:+.1f}% saving)"]))
        tab.append([lab, f"{xt:.2f}", f"{st_ * 100:+.1f}", f"{xf:.2f}", f"{sf * 100:+.1f}"])
    ser = [("tiered", "s1"), ("flat", "oth")]
    bottom = hbars(f, [dict(label=r["label"], vals=r["vals"], tips=r["tips"]) for r in rows], ser, 3.0, [0, 1, 2, 3],
                   lambda t: f"{t:g}x", lambda v: f"{v:.2f}x", stacked=False, thick=20)
    f.table = (["pipeline", "tiered total (x)", "tiered saving vs Qwen reviewer (%)", "flat total (x)", "flat saving vs Qwen reviewer (%)"], tab)
    return f, bottom + 22


def fig_qwen_by_class(N):
    """F03: where the Qwen agent bill goes, by document class (test split)."""
    t = N["qwen_test"]
    f = Fig("f03", "17 merger agreements are 53% of the Qwen agent bill",
            "Qwen 3.7 Flash agent cost on the 323 test documents, tiered price, by true class. "
            "The Decisions model reads at most 120,000 characters, so one document cannot cross a price tier.",
            left=190, right=90, foot="Token counts are the saved Qwen sorter pass (data/handoff/sorter-qwen3.7-flash).")
    total = t["tiered_usd"]
    rows, tab = [], []
    for c in sorted(CLASSES, key=lambda c: -t["by_class"][c]["tiered"]):
        b = t["by_class"][c]
        share = b["tiered"] / total
        rows.append(dict(label=CLASS_LABEL[c], sub=f"{b['n']} documents", vals=[b["tiered"]],
                         tips=[f"{CLASS_LABEL[c]}\n${b['tiered']:.4f} tiered ({share * 100:.0f}% of the bill)\n"
                               f"{b['n']} documents · {b['ptok'] / b['n']:,.0f} prompt tokens each on average\n"
                               f"flat-price cost would be ${b['flat']:.4f}"],
                         total_label=f"${b['tiered']:.3f} · {share * 100:.0f}%"))
        tab.append([CLASS_LABEL[c], b["n"], f"{b['ptok'] / b['n']:,.0f}", f"{b['tiered']:.4f}", f"{b['flat']:.4f}", f"{share * 100:.1f}"])
    bottom = hbars(f, rows, [("c", "s1")], 0.16, [0, 0.04, 0.08, 0.12, 0.16], lambda t: f"${t:.2f}", None)
    f.table = (["class", "documents", "mean prompt tokens", "tiered USD", "flat USD", "share of bill (%)"], tab)
    return f, bottom + 22


def fig_person_load(N):
    """F04: documents needing a person per 1,000 - effectiveness of each reviewer arm."""
    P = N["person_per_1000"]
    f = Fig("f04", "A reviewer cuts the people-needed load from 356 to under 75 per 1,000",
            "Documents a person must look at per 1,000, on the held-out test split. The Qwen agent's own confidence cannot "
            "separate its errors: 122 of its 127 train errors sit at 0.95 or higher.",
            left=250, right=60, legend=[("Decisions model", "s3"), ("Other arms", "oth")],
            foot="All arms: the 323 held-out documents. Fewer is not better on its own: see f15 for wrong answers.")
    order = [("Qwen agent alone", "oth"), ("Decisions v3.0.0", "s3"), ("Decisions v2", "s3"),
             ("Qwen reviewer (default prompt)", "oth")]
    order.sort(key=lambda r: -P[r[0]])
    tab = []
    bars = []
    for lab, cls in order:
        v = P[lab]
        bars.append((lab, cls, v))
        tab.append([lab, f"{v:.1f}", f"{v / 10:.1f}"])
    x0, x1 = f.left, f.w - f.right
    sx = xscale(0, 400, x0, x1)
    pitch, thick = 34, 18
    y_top = f.top
    y_bot = y_top + pitch * len(bars)
    vgrid(f, sx, [0, 100, 200, 300, 400], y_top - 4, y_bot, lambda t: f"{t:g}")
    for i, (lab, cls, v) in enumerate(bars):
        yc = y_top + i * pitch + pitch / 2
        f.add(f'<text class="lb" x="{x0 - 10}" y="{yc + 4:.1f}" text-anchor="end">{esc(lab)}</text>')
        w = sx(v) - x0
        f.add(mark(f"{lab}\n{v:.0f} of every 1,000 documents need a person ({v / 10:.1f}%)", rbar(x0, yc - thick / 2, w, thick, cls),
                   hit=(x0, yc - pitch / 2 + 2, max(w, 24), pitch - 4)))
        f.add(f'<text class="vl" x="{x0 + w + 8:.1f}" y="{yc + 4:.1f}">{v:.0f}</text>')
    f.add(f'<line class="axis" x1="{x0}" x2="{x0}" y1="{y_top - 4}" y2="{y_bot}"/>')
    f.table = (["arm", "documents needing a person per 1,000", "share (%)"], tab)
    return f, y_bot + 38


def fig_latency(N):
    """F05: latency p50 / p95."""
    q = N["qwen_test"]
    qr = N["qwen_reviewer"]["latency_s"]
    data = [("Qwen agent (323 test docs)", "s1", q["p50_s"], q["p95_s"]),
            ("Qwen reviewer (323 test docs)", "s2", qr["p50"], qr["p95"]),
            ("Decisions model (735 train docs)", "s3", *LATENCY_RECORDED["dec"])]
    f = Fig("f05", "A Decisions call returns in about half a second",
            "Seconds per document at the 95th and 50th percentile. Load differs: the Qwen pass ran whole documents of up to "
            "106k tokens; the Decisions run used 735 train documents at concurrency 16.",
            left=230, right=60, legend=[("Median (p50)", "s1"), ("95th percentile (p95)", "oth")],
            foot="Latency is operational colour, not a controlled benchmark; sources: the handoff and Qwen reviewer rows, reviewer-calibration-luna-decisions.md.")
    x0, x1 = f.left, f.w - f.right
    sx = xscale(0, 8, x0, x1)
    pitch, th = 48, 14
    y_top = f.top
    y_bot = y_top + pitch * len(data)
    vgrid(f, sx, [0, 2, 4, 6, 8], y_top - 4, y_bot, lambda t: f"{t:g}s")
    tab = []
    for i, (lab, cls, p50, p95) in enumerate(data):
        yc = y_top + i * pitch + pitch / 2
        f.add(f'<text class="lb" x="{x0 - 10}" y="{yc + 4:.1f}" text-anchor="end">{esc(lab)}</text>')
        for k, (nm, v, c) in enumerate((("p50", p50, cls), ("p95", p95, "oth"))):
            y = yc - th - 1 + k * (th + 2)
            w = sx(v) - x0
            f.add(mark(f"{lab}\n{nm}: {v:.2f} s", rbar(x0, y, w, th, c), hit=(x0, y - 1, max(w, 24), th + 2)))
            f.add(f'<text class="vl" x="{x0 + w + 7:.1f}" y="{y + th - 2:.1f}">{v:.1f}s</text>')
        tab.append([lab, f"{p50:.2f}", f"{p95:.2f}"])
    f.add(f'<line class="axis" x1="{x0}" x2="{x0}" y1="{y_top - 4}" y2="{y_bot}"/>')
    f.table = (["call", "p50 (s)", "p95 (s)"], tab)
    return f, y_bot + 38


def fig_accuracy(N):
    """F06: class accuracy per run, filled = held-out test, hollow = train (in-sample)."""
    fam = {"qwen": ("s2", "Qwen reviewer"), "dec": ("s3", "Decisions model")}
    f = Fig("f06", "Class accuracy on held-out documents: Decisions 98.5%, Qwen reviewer 93.8%",
            "Share of documents given the right class. Filled dots are held-out test runs; hollow dots are train runs, "
            "where the question set was tuned. The axis starts at 92%.",
            left=270, right=70, legend=[("Qwen agent", "s1"), ("Qwen reviewer", "s2"), ("Decisions model", "s3")],
            foot="The axis starts at 92% on purpose: compare dot positions, not lengths.")
    rows, tab = [], []
    q = N["qwen_test"]
    qt = N["qwen_train"]
    items = [("Qwen agent · train (2,979)", "s1", True, qt["class_correct"] / qt["class_n"], f"{qt['class_correct']:,} / {qt['class_n']:,}"),
             ("Qwen agent · test (323)", "s1", False, q["class_correct"] / q["class_n"], f"{q['class_correct']} / {q['class_n']}")]
    qr = N["qwen_reviewer"]
    for r in RUNS + [dict(run=qr["run_id"], label="Qwen reviewer, default prompt", family="qwen", split="test", n=qr["documents"],
                          correct=qr["class_correct"], hi=(qr["wrong_at_confidence_ge_0_90"], qr["wrong_answers"]), cost=qr["list_cost_usd_tiered"],
                          src="reports/reviewer-calibration/reviewer-validation-qwen-flash-test.json")]:
        acc = r["correct"] / r["n"] if r["correct"] is not None else r["pct"]
        det = f"{r['correct']} / {r['n']}" if r["correct"] is not None else f"{r['pct'] * 100:.1f}% as reported, n={r['n']}"
        items.append((f"{r['label'].replace('Decisions model, question set ', 'Decisions · ')} · {r['split']} ({r['n']})",
                      fam[r["family"]][0], r["split"] == "train", acc, det))
    # order: held-out first within family
    items.sort(key=lambda it: (0 if it[1] == "s1" else 1 if it[1] == "s2" else 2, it[2]))
    for lab, cls, hollow, acc, det in items:
        tip = f"{lab}\n{acc * 100:.1f}% class accuracy\n{det}\n{'train: tuned on these documents' if hollow else 'held-out test split'}"
        rows.append(dict(label=lab, pts=[dict(v=acc * 100, cls=cls, hollow=hollow, r=5.5, tip=tip, label=f"{acc * 100:.1f}%")]))
        tab.append([lab, "train" if hollow else "test", det, f"{acc * 100:.1f}"])
    bottom = hdots(f, rows, 92, 100.5, [92, 94, 96, 98, 100], lambda t: f"{t:g}%", pitch=26)
    f.table = (["run", "split", "correct / n", "class accuracy (%)"], tab)
    return f, bottom + 22


def fig_wrong_conf(N):
    """F07: share of wrong answers that sit at high confidence."""
    f = Fig("f07", "Decisions errors sit lower in confidence than Qwen errors",
            "Share of each run's wrong answers carrying confidence of 0.90 or higher - errors no cutoff can separate from right answers.",
            left=290, right=90, legend=[("Qwen agent", "s1"), ("Qwen reviewer", "s2"), ("Decisions model", "s3")],
            foot="Qwen agent row uses the 0.95 threshold (122 of 127 train errors); all others 0.90. Small n on some rows - see tooltips.")
    rows = [("Qwen agent · train", "s1", 122, 127, "0.95")]
    qr = N["qwen_reviewer"]
    qrun = dict(label="Qwen reviewer, default prompt", family="qwen", split="test", hi=(qr["wrong_at_confidence_ge_0_90"], qr["wrong_answers"]))
    for r in RUNS + [qrun]:
        if r["hi"] is None:
            continue
        hi, nw = r["hi"]
        cls = "s2" if r["family"] == "qwen" else "s3"
        lab = r["label"].replace("Decisions model, question set ", "Decisions · ")
        rows.append((f"{lab} · {r['split']}", cls, hi, nw, "0.90"))
    rows.sort(key=lambda r: -(r[2] / r[3]))
    x0, x1 = f.left, f.w - f.right
    sx = xscale(0, 1, x0, x1)
    pitch, thick = 32, 16
    y_top = f.top
    y_bot = y_top + pitch * len(rows)
    vgrid(f, sx, [0, 0.25, 0.5, 0.75, 1.0], y_top - 4, y_bot, lambda t: f"{t * 100:.0f}%")
    tab = []
    for i, (lab, cls, hi, nw, thr) in enumerate(rows):
        yc = y_top + i * pitch + pitch / 2
        share = hi / nw
        f.add(f'<text class="lb" x="{x0 - 10}" y="{yc + 4:.1f}" text-anchor="end">{esc(lab)}</text>')
        w = sx(share) - x0
        if w > 0:
            f.add(mark(f"{lab}\n{hi} of {nw} wrong answers at confidence >= {thr}\n{share * 100:.0f}%", rbar(x0, yc - thick / 2, w, thick, cls),
                       hit=(x0, yc - pitch / 2 + 2, max(w, 24), pitch - 4)))
        else:
            f.add(mark(f"{lab}\n0 of {nw} wrong answers at confidence >= {thr}", f'<rect class="m {cls}" x="{x0}" y="{yc - 1:.1f}" width="2" height="2"/>',
                       hit=(x0, yc - pitch / 2 + 2, 24, pitch - 4)))
        f.add(f'<text class="vl" x="{x0 + w + 8:.1f}" y="{yc + 4:.1f}">{hi}/{nw}</text>')
        tab.append([lab, hi, nw, thr, f"{share * 100:.0f}"])
    f.add(f'<line class="axis" x1="{x0}" x2="{x0}" y1="{y_top - 4}" y2="{y_bot}"/>')
    f.table = (["run", "wrong answers at high confidence", "wrong answers", "threshold", "share (%)"], tab)
    return f, y_bot + 38



def fig_cutoffs(N):
    """F08: per-class cutoff, the two Decisions question sets."""
    cols = [c[0] for c in N["cutoffs"]]
    bins_edges = [0.5, 0.7, 0.85, 0.95]

    def b(v):
        return sum(v >= e for e in bins_edges)

    f = Fig("f08", "Decisions cutoffs moved by up to 0.30 between question sets, so they need the full train split",
            "Per-class cutoff that reaches 95% held-out accuracy (five-fold cross-fit, 735-document train draw). With no wrong answers, "
            "the cutoff is just the lowest probability of a right answer, so small draws set it.",
            left=190, right=20, w=760,
            foot="Cutoffs apply to the Decisions model's probabilities; a Qwen reviewer has none (its confidence is self-reported).")
    vals, texts, tips, bins = [], [], [], []
    tab = []
    for c in CLASSES:
        rv, rt, rp, rb = [], [], [], []
        row = [CLASS_LABEL[c]]
        for lab, name, d in N["cutoffs"]:
            x = d[c]
            rv.append(x["cutoff"]); rt.append(f"{x['cutoff']:.2f}"); rb.append(b(x["cutoff"]))
            rp.append(f"{CLASS_LABEL[c]} · {lab.replace(chr(10), ' ')}\ncutoff {x['cutoff']:.2f}\n"
                      f"held-out accuracy {x['holdout_accuracy'] * 100:.1f}% (95% CI {x['holdout_accuracy_ci'][0] * 100:.1f}-{x['holdout_accuracy_ci'][1] * 100:.1f}%)\n"
                      f"{x['documents']} documents · {'meets' if x['meets_target'] else 'misses'} the 95% target")
            row.append(f"{x['cutoff']:.2f}")
        vals.append(rv); texts.append(rt); tips.append(rp); bins.append(rb); tab.append(row)
    bottom = heatmap(f, [CLASS_LABEL[c] for c in CLASSES], cols, vals, texts, tips, bins, cw=170, ch=38)
    scale_legend(f, f.left + 40, bottom + 4, ("0.5", "1.0"))
    f.table = (["class"] + [c.replace("\n", " ") for c in cols], tab)
    return f, bottom + 54


def fig_dumbbell(N):
    """F09: subclass accuracy, question set v1 -> v2."""
    f = Fig("f09", "Question set v2 lifted six of seven weak subclasses",
            "Subclass accuracy on the train draw before and after the v1 -> v2 rewrite. Hollow = v1, filled = v2. "
            "One subclass, meeting_request, got worse.",
            left=240, right=60, legend=[("Question set v1", "oth"), ("Question set v2", "s3")],
            foot="Counts are correct / documents in the 735-document train draw (in-sample).")
    rows, tab = [], []
    for lab, a, na, b, nb in SUBCLASS_V1_V2:
        va, vb = a / na * 100, b / nb * 100
        rows.append(dict(label=lab, line=(va, vb), line_cls="ko",
                         pts=[dict(v=va, cls="oth", hollow=True, r=5, tip=f"{lab}\nv1: {a} / {na} ({va:.0f}%)"),
                              dict(v=vb, cls="s3", r=5.5, tip=f"{lab}\nv2: {b} / {nb} ({vb:.0f}%)\nchange {vb - va:+.0f} points",
                                   label=f"{vb:.0f}%", label_at=max(va, vb))]))
        tab.append([lab, f"{a}/{na}", f"{va:.0f}", f"{b}/{nb}", f"{vb:.0f}", f"{vb - va:+.0f}"])
    bottom = hdots(f, rows, 0, 105, [0, 25, 50, 75, 100], lambda t: f"{t:g}%", pitch=30)
    f.table = (["subclass", "v1 correct", "v1 (%)", "v2 correct", "v2 (%)", "change (points)"], tab)
    return f, bottom + 22


def fig_verdict(N):
    """F10: v3.0.0 verdict question vs what the sorter handoff actually needed."""
    v = N["routing"]["v3"]["verdicts_by_expected"]
    rows_k = [("continue_sorter_correct", "sorter was right"), ("continue_with_subclass_correction", "subclass was wrong"),
              ("reclassify", "class was wrong")]
    cols_k = ["continue_sorter_correct", "continue_with_subclass_correction", "reclassify", "multiple_documents", "route_to_human_review"]
    col_l = ["continue", "correct\nsubclass", "reclassify", "multiple\ndocuments", "human\nreview"]
    f = Fig("f10", "Question set v3.0.0's verdict mostly answered 'continue'",
            "Held-out test, 323 documents. Rows: what the sorter handoff needed. Columns: the verdict the Decisions model gave. "
            "The right answer sits on the diagonal. Cell colour is the share of the row.",
            left=210, right=20,
            foot="Of 14 handoffs with the wrong class, 10 were told to continue as correct.")
    texts, tips, bins, tab = [], [], [], []
    for rk, rl in rows_k:
        tot = sum(v[rk].values())
        rt, rp, rb, trow = [], [], [], [rl, tot]
        for ck in cols_k:
            n = v[rk].get(ck, 0)
            share = n / tot
            rt.append(str(n) if n else "0")
            rp.append(f"needed: {rl}\ngave: {ck}\n{n} of {tot} ({share * 100:.0f}% of the row)")
            rb.append(min(4, int(share * 5)) if n else 0)
            trow.append(n)
        texts.append(rt); tips.append(rp); bins.append(rb); tab.append(trow)
    bottom = heatmap(f, [f"{r[1]} ({sum(v[r[0]].values())})" for r in rows_k], col_l, [[0] * 5] * 3, texts, tips, bins, cw=92, ch=44)
    scale_legend(f, f.left + 30, bottom + 4, ("0%", "100% of row"))
    f.table = (["needed", "documents"] + cols_k, tab)
    return f, bottom + 54


def fig_human_by_class(N):
    """F11: human-review rate by class, question set v2 vs v3.0.0."""
    a, b = N["routing"]["v2"], N["routing"]["v3"]
    f = Fig("f11", "The v3.0.0 verdict question parked 23 documents for a person, up from 5",
            "Share of held-out test documents parked for human review, by true class, at the same v2 cutoffs. "
            "Overall: 1.5% on v2, 7.1% on v3.0.0.",
            left=190, right=60, legend=[("Question set v2", "oth"), ("Question set v3.0.0", "s3")],
            foot="'unknown' (2-3 documents, always parked) is left out of the chart; it is in the table.")
    rows, tab = [], []
    for c in CLASSES:
        ra, rb = a["routed_to_human_review_by_class"][c], b["routed_to_human_review_by_class"][c]
        rows.append(dict(label=CLASS_LABEL[c], vals=[ra["rate"] * 100, rb["rate"] * 100],
                         tips=[f"{CLASS_LABEL[c]} · v2\n{ra['routed']} of {ra['n']} parked ({ra['rate'] * 100:.1f}%)",
                               f"{CLASS_LABEL[c]} · v3.0.0\n{rb['routed']} of {rb['n']} parked ({rb['rate'] * 100:.1f}%)"]))
        tab.append([CLASS_LABEL[c], f"{ra['routed']}/{ra['n']}", f"{ra['rate'] * 100:.1f}", f"{rb['routed']}/{rb['n']}", f"{rb['rate'] * 100:.1f}"])
    ua, ub = a["routed_to_human_review_by_class"]["unknown"], b["routed_to_human_review_by_class"]["unknown"]
    tab.append(["unknown", f"{ua['routed']}/{ua['n']}", "100.0", f"{ub['routed']}/{ub['n']}", "100.0"])
    tab.append(["all documents", f"{a['routed_to_human_review']}/323", f"{a['routed_to_human_review_rate'] * 100:.1f}",
                f"{b['routed_to_human_review']}/323", f"{b['routed_to_human_review_rate'] * 100:.1f}"])
    bottom = hbars(f, rows, [("v2", "oth"), ("v3", "s3")], 32, [0, 10, 20, 30], lambda t: f"{t:g}%", lambda v: f"{v:.1f}%", stacked=False, thick=20)
    f.table = (["class", "v2 parked", "v2 rate (%)", "v3.0.0 parked", "v3.0.0 rate (%)"], tab)
    return f, bottom + 22


def fig_sorter_errors(N):
    """F12: what the Qwen agent gets wrong."""
    f = Fig("f12", "The Qwen agent's errors are patterns, not noise",
            "127 wrong classes on the 2,979 train documents, by pattern. All but a handful are reading a corporate record as a contract "
            "or a mailbox fragment as 'unknown'.",
            left=300, right=60, foot="Source: reports/sorter-handoff/sorter-qwen3.7-flash-audit.md. 121 of 122 patched-target errors were label-confirmed.")
    rows, tab = [], []
    total = sum(v for _, v in SORTER_ERRORS)
    for lab, v in SORTER_ERRORS:
        rows.append(dict(label=lab, vals=[v], tips=[f"{lab}\n{v} of {total} class errors ({v / total * 100:.0f}%)"], total_label=str(v)))
        tab.append([lab, v, f"{v / total * 100:.0f}"])
    bottom = hbars(f, rows, [("e", "s1")], 60, [0, 20, 40, 60], lambda t: f"{t:g}", None, pitch=36)
    f.table = (["pattern", "errors", "share (%)"], tab)
    return f, bottom + 22


def fig_gate_accept(N):
    """F13: the extraction gate's accept rate vs the share of extractions that really were good."""
    g = N["gate"]["v1.1.0 pooled"]["classes"]
    f = Fig("f13", "The extraction gate says 'accept' where extractions are not good",
            "Pooled 910 documents. Gate accept rate against the share of extractions that really scored 0.80 or higher. "
            "Corporate records: 28% accepted, 0.5% good.",
            left=190, right=70, legend=[("Gate said accept", "s3"), ("Extraction really good (score >= 0.80)", "oth")],
            foot="Source: reports/extraction-gate/extraction-gate-luna-v1.1.0-pooled.calibration.json.")
    keys = CLASSES + ["all"]
    rows, tab = [], []
    for c in keys:
        d = g[c]
        n = d["n"]
        acc = d["verdicts"].get("accept", 0) / n * 100
        good = d["good_rate"] * 100
        lab = "all classes" if c == "all" else CLASS_LABEL[c]
        rows.append(dict(label=lab, sub=f"{n} documents",
                         vals=[acc, good],
                         tips=[f"{lab}\ngate said accept on {d['verdicts'].get('accept', 0)} of {n} ({acc:.1f}%)",
                               f"{lab}\n{good:.1f}% of extractions really scored >= 0.80 (mean score {d['mean_extraction_score']:.2f})"]))
        tab.append([lab, n, d["verdicts"].get("accept", 0), f"{acc:.1f}", d["verdicts"].get("retry_extraction", 0),
                    d["verdicts"].get("human_review", 0), f"{good:.1f}", f"{d['mean_extraction_score']:.3f}"])
    bottom = hbars(f, rows, [("accept", "s3"), ("good", "oth")], 40, [0, 10, 20, 30, 40], lambda t: f"{t:g}%", lambda v: f"{v:.1f}%", stacked=False, thick=20)
    f.table = (["class", "documents", "gate accept", "accept rate (%)", "gate retry", "gate human review", "really good (%)", "mean extraction score"], tab)
    return f, bottom + 22


def fig_gate_auroc(N):
    """F14: does the gate rank good extractions above bad ones? AUROC per class."""
    G = N["gate"]
    f = Fig("f14", "The gate's accept confidence does not rank good extractions above bad",
            "AUROC of the gate's accept confidence against extraction score. 0.5 is a coin flip. Large dot: pooled 910 documents; small dots: single rounds.",
            left=190, right=60, legend=[("Pooled (910 documents)", "s3"), ("Single rounds", "oth")],
            foot="No class reached the 90% precision target at any cutoff. Merger agreements: AUROC undefined (no good extraction).")
    rounds = ["v1.0.0 baseline", "v1.1.0 baseline", "v1.1.0 round 2"]
    rows, tab = [], []
    for c in CLASSES + ["all"]:
        lab = "all classes" if c == "all" else CLASS_LABEL[c]
        pts, trow = [], [lab]
        for r in rounds:
            d = G[r]["classes"].get(c)
            v = d.get("accept_auroc") if d else None
            trow.append("" if v is None else f"{v:.3f}")
            if v is not None:
                pts.append(dict(v=v, cls="oth", r=4, tip=f"{lab} · {r}\nAUROC {v:.3f} (n={d['n']})"))
        d = G["v1.1.0 pooled"]["classes"][c]
        v = d.get("accept_auroc")
        trow.append("n/a" if v is None else f"{v:.3f}")
        if v is not None:
            right_busy = any(0 < q["v"] - v < 0.13 for q in pts)
            pts.append(dict(v=v, cls="s3", r=6, tip=f"{lab} · pooled\nAUROC {v:.3f} (n={d['n']})", label=f"{v:.2f}",
                            label_left=right_busy))
        else:
            pts.append(dict(v=0.5, cls="oth", r=0.01, label="undefined: no extraction scored good",
                            tip=f"{lab} · pooled\nAUROC undefined: no extraction scored good"))
        rows.append(dict(label=lab, pts=pts))
        tab.append(trow)
    bottom = hdots(f, rows, 0, 1, [0, 0.25, 0.5, 0.75, 1.0], lambda t: f"{t:g}", pitch=32, ref=(0.5, "chance"))
    f.table = (["class"] + rounds + ["pooled"], tab)
    return f, bottom + 22


def fig_silent_errors(N):
    """F15: documents routed with no person and wrong, per 1,000 test documents."""
    qr = N["qwen_reviewer"]
    q9 = qr["unattended_if_unknown_parks"]["0.9"]
    v2, v3 = N["routing"]["v2"], N["routing"]["v3"]
    arms = [("Qwen reviewer, default prompt", "s2", q9["misrouted"], qr["documents"], "no calibration; any cutoff from 0.0 to 0.9"),
            ("Decisions v2", "s3", v2["misrouted"], 323, f"v2 cutoffs, {v2['sent_on_unattended']} routed"),
            ("Decisions v3.0.0", "s3", v3["misrouted"], 323, f"v2 cutoffs, {v3['sent_on_unattended']} routed")]
    f = Fig("f15", "A Qwen reviewer lets about 25 wrong documents per 1,000 through; Decisions lets 3",
            "Documents routed with no person that were wrong, per 1,000 held-out documents. All 20 wrong Qwen answers carry "
            "confidence of 0.90 or higher, so no cutoff catches them.",
            left=270, right=70, legend=[("Qwen reviewer", "s2"), ("Decisions model", "s3")],
            foot="Misrouted = a decision-class answer that disagrees with the label. 'unknown' answers always park, so they are not counted.")
    x0, x1 = f.left, f.w - f.right
    sx = xscale(0, 30, x0, x1)
    pitch, thick = 36, 18
    y_top = f.top
    y_bot = y_top + pitch * len(arms)
    vgrid(f, sx, [0, 10, 20, 30], y_top - 4, y_bot, lambda t: f"{t:g}")
    tab = []
    for i, (lab, cls, n, tot, basis) in enumerate(arms):
        v = n / tot * 1000
        yc = y_top + i * pitch + pitch / 2
        f.add(f'<text class="lb" x="{x0 - 10}" y="{yc + 1:.1f}" text-anchor="end">{esc(lab)}</text>')
        f.add(f'<text class="tk" x="{x0 - 10}" y="{yc + 14:.1f}" text-anchor="end">{esc(basis)}</text>')
        w = sx(v) - x0
        f.add(mark(f"{lab}\n{n} of {tot} documents routed wrong with no person ({v:.1f} per 1,000)\n{basis}",
                   rbar(x0, yc - thick / 2, w, thick, cls), hit=(x0, yc - pitch / 2 + 2, max(w, 24), pitch - 4)))
        f.add(f'<text class="vl" x="{x0 + w + 8:.1f}" y="{yc + 4:.1f}">{v:.1f}</text>')
        tab.append([lab, n, tot, f"{v:.1f}", basis])
    f.add(f'<line class="axis" x1="{x0}" x2="{x0}" y1="{y_top - 4}" y2="{y_bot}"/>')
    f.table = (["arm", "misrouted", "documents", "per 1,000", "basis"], tab)
    return f, y_bot + 38


def fig_routing_outcomes(N):
    """F16: what happens to each of the 1,488 scored train documents when the Decisions reviewer routes it."""
    h = N["half"]
    R = h["routing"]
    f = Fig("f16", "The Decisions reviewer routes 92% to 96% of documents correctly with no person",
            "Question set 3.1.0 with the sorter handoff, 1,488 scored train documents. 'Pipeline rule': any disagreement with the sorter "
            "parks, as in the live pipeline (1,485 of 1,491 sorter answers are at 0.95 or higher). 'Reviewer alone': its answer decides.",
            left=230, right=215,
            legend=[("Routed correctly", "s3"), ("Parked: sorter wrong", "s1"), ("Parked: sorter right", "oth"), ("Misrouted", "crit")],
            foot="Cutoffs: v2 were fixed before this run; 3.1.0 were cross-fitted on this same run, so treat them as optimistic.")
    series = [("c", "s3"), ("pw", "s1"), ("pr", "oth"), ("m", "crit")]
    spec = [("v2 cutoffs · pipeline rule", "v2_pipeline_rule"), ("v2 cutoffs · reviewer alone", "v2_reviewer_alone"),
            ("3.1.0 cutoffs · pipeline rule", "own_pipeline_rule"), ("3.1.0 cutoffs · reviewer alone", "own_reviewer_alone")]
    rows, tab = [], []
    for lab, key in spec:
        c = R[key]
        sc = c["scored"]
        vals = [c["routed_correctly"], c["parked_sorter_wrong"], c["parked_sorter_right"], c["misrouted"]]
        names = ["Routed correctly with no person", "Parked and the sorter was wrong (error caught)", "Parked and the sorter was right (unnecessary)",
                 "Misrouted: wrong class, no person"]
        extra = f" ({c['routed_correct_sorter_right']} sorter right, {c['routed_correct_sorter_wrong']} sorter wrong and corrected)"
        tips = [f"{lab}\n{names[j]}: {v:,} of {sc:,} ({v / sc * 100:.1f}%)" + (extra if j == 0 else "") for j, v in enumerate(vals)]
        rows.append(dict(label=lab, vals=vals, tips=tips, total_label=f"{c['routed_correctly']:,} ok · {c['parked']} parked · {c['misrouted']} wrong"))
        tab.append([lab, sc, c["routed_correctly"], f"{c['routed_correctly'] / sc * 100:.1f}", c["routed_correct_sorter_wrong"], c["misrouted"],
                    c["parked"], c["parked_sorter_wrong"], c["parked_sorter_right"]])
    bottom = hbars(f, rows, series, 1500, [0, 500, 1000, 1500], lambda t: f"{t:,}", None, pitch=36)
    f.table = (["routing", "scored", "routed correctly", "routed correctly (%)", "of which sorter wrong, corrected", "misrouted",
                "parked", "parked, sorter wrong", "parked, sorter right"], tab)
    return f, bottom + 22


def fig_sorter_vs_reviewer(N):
    """F17: the sorter's accuracy against the reviewer's, per primary type and subclass."""
    a = N["half"]["all"]
    f = Fig("f17", "The reviewer lifts subclass accuracy from 72% to 84%, and primary type from 96% to 99%",
            "Hollow = the saved Qwen sorter, filled = the Decisions reviewer (question set 3.1.0), both scored against the verified targets. "
            "Train documents; 395 of 1,491 were in question-set tuning, see the report.",
            left=250, right=60, legend=[("Qwen sorter", "s1"), ("Decisions reviewer", "s3")],
            foot="Subclass: 1,463 scored documents; merger agreements 43 (the rest are unannotated 'other').")
    rows, tab = [], []

    def add(label, n, rv, sv, group):
        pr, ps = rv / n * 100, sv / n * 100
        rows.append(dict(label=label, line=(ps, pr), line_cls="ko",
                         pts=[dict(v=ps, cls="s1", hollow=True, r=5, tip=f"{label}\nsorter: {sv:,} of {n:,} ({ps:.1f}%)"),
                              dict(v=pr, cls="s3", r=5.5, tip=f"{label}\nreviewer: {rv:,} of {n:,} ({pr:.1f}%)\nchange {pr - ps:+.1f} points",
                                   label=f"{pr:.0f}%", label_at=max(ps, pr))]))
        tab.append([label, n, sv, f"{ps:.1f}", rv, f"{pr:.1f}", f"{pr - ps:+.1f}"])

    add("Primary type · all", a["class_scored"], a["class_reviewer"], a["class_sorter"], "t")
    add("Subclass · all", a["sub_scored"], a["sub_reviewer"], a["sub_sorter"], "t")
    for k in CLASSES:
        c = a["per_class"][k]
        add(f"Subclass · {CLASS_LABEL[k]}", c["sub_n"], c["sub_reviewer"], c["sub_sorter"], k)
    bottom = hdots(f, rows, 40, 105, [40, 60, 80, 100], lambda t: f"{t:g}%", pitch=30)
    f.table = (["measure", "scored", "sorter correct", "sorter (%)", "reviewer correct", "reviewer (%)", "change (points)"], tab)
    return f, bottom + 22


FIGURES = [fig_cost_stack, fig_sensitivity, fig_qwen_by_class, fig_person_load, fig_latency, fig_accuracy, fig_wrong_conf,
           fig_cutoffs, fig_dumbbell, fig_verdict, fig_human_by_class, fig_sorter_errors, fig_gate_accept, fig_gate_auroc, fig_silent_errors, fig_routing_outcomes, fig_sorter_vs_reviewer]


# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #
def csv_text(headers, rows):
    s = io.StringIO()
    w = csv.writer(s, lineterminator="\n")
    w.writerow(headers)
    w.writerows(rows)
    return s.getvalue()


def table_html(headers, rows):
    out = ["<table><thead><tr>" + "".join(f"<th>{esc(h)}</th>" for h in headers) + "</tr></thead><tbody>"]
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


HTML_CSS = """
:root{color-scheme:light dark;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--line:#e1e0d9;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--line:#2c2c2a;--s1:#3987e5;--s2:#d95926;--s3:#199e70}}
:root[data-theme="dark"]{--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--line:#2c2c2a;--s1:#3987e5;--s2:#d95926;--s3:#199e70}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--ink);font:15px/1.5 system-ui,-apple-system,'Segoe UI',sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:26px;margin:0 0 6px}h2{font-size:19px;margin:44px 0 6px}p.lede{color:var(--ink2);margin:0 0 20px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:22px 0}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.tile .v{font-size:30px;font-weight:600;line-height:1.1}.tile .l{color:var(--ink2);font-size:13px;margin-top:4px}
.tile .s{color:var(--muted);font-size:12px;margin-top:2px}
figure{margin:16px 0;background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:8px}
figure svg{width:100%;height:auto;display:block}
figcaption{color:var(--ink2);font-size:13px;padding:8px 8px 4px}
details{margin:6px 8px 4px}summary{cursor:pointer;color:var(--ink2);font-size:13px}
table{border-collapse:collapse;width:100%;font-size:12.5px;margin-top:8px;display:block;overflow-x:auto}
th,td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;white-space:nowrap}th{color:var(--ink2);font-weight:600}
td{font-variant-numeric:tabular-nums}
#tip{position:fixed;z-index:10;pointer-events:none;background:var(--surface);color:var(--ink);border:1px solid var(--line);border-radius:8px;
 padding:8px 10px;font-size:12.5px;line-height:1.4;max-width:300px;box-shadow:0 4px 18px rgba(0,0,0,.18);display:none}
#tip b{display:block;font-size:13px;margin-bottom:2px}#tip span{display:block;color:var(--ink2)}
nav a{color:var(--ink2);margin-right:14px;font-size:13px}
.note{background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--s3);border-radius:8px;padding:10px 14px;color:var(--ink2);font-size:13.5px;margin:14px 0}
"""

HTML_JS = """
(function(){var tip=document.getElementById('tip');
function show(g,x,y){var lines=g.getAttribute('data-tip').split('\\n');tip.textContent='';
var b=document.createElement('b');b.textContent=lines[0];tip.appendChild(b);
for(var i=1;i<lines.length;i++){var s=document.createElement('span');s.textContent=lines[i];tip.appendChild(s);}
tip.style.display='block';var w=tip.offsetWidth,h=tip.offsetHeight;
tip.style.left=Math.max(8,Math.min(x+14,innerWidth-w-8))+'px';tip.style.top=Math.max(8,Math.min(y+14,innerHeight-h-8))+'px';}
function hide(){tip.style.display='none';}
document.querySelectorAll('.mk').forEach(function(g){
g.addEventListener('pointermove',function(e){show(g,e.clientX,e.clientY)});
g.addEventListener('pointerleave',hide);
g.addEventListener('focus',function(){var r=g.getBoundingClientRect();show(g,r.left+r.width/2,r.top+r.height/2)});
g.addEventListener('blur',hide);});})();
"""


def build_all():
    N = compute()
    out = {}
    figs = []
    for fn in FIGURES:
        f, h = fn(N)
        figs.append((f, h))
        out[f"figures/{f.fid}-{fn.__name__.replace('fig_', '').replace('_', '-')}.svg"] = f.svg(h)
        out[f"data/{f.fid}-{fn.__name__.replace('fig_', '').replace('_', '-')}.csv"] = csv_text(*f.table)
    out["data/summary.json"] = json.dumps(summary(N), indent=2, sort_keys=True) + "\n"
    out["decisions-dashboard.html"] = dashboard(N, figs)
    return out, N, figs


def summary(N):
    R = N["reviewers"]
    t, tr = N["qwen_test"], N["qwen_train"]
    r2 = lambda x: round(x, 4)
    return {
        "generated_by": "reports/decisions/build_decisions_report.py",
        "qwen_price_sheet_usd_per_1m": {"<32k": [0.03, 0.13], ">=32k": [0.10, 0.40], ">=256k": [0.20, 0.80]},
        "qwen_agent": {
            "test": {"documents": t["n"], "tiered_usd": r2(t["tiered_usd"]), "flat_usd": r2(t["flat_usd"]), "manifest_flat_usd": t["manifest_flat_usd"],
                     "prompt_tokens": t["prompt_tokens"], "docs_ge_32k": t["docs_ge_32k"], "p50_s": round(t["p50_s"], 2), "p95_s": round(t["p95_s"], 2),
                     "class_correct": t["class_correct"], "human_review_rate": t["human_review_rate"]},
            "train": {"documents": tr["n"], "tiered_usd": r2(tr["tiered_usd"]), "flat_usd": r2(tr["flat_usd"]), "manifest_flat_usd": tr["manifest_flat_usd"],
                      "prompt_tokens": tr["prompt_tokens"], "docs_ge_32k": tr["docs_ge_32k"], "docs_ge_256k": tr["docs_ge_256k"]},
            "unit_usd_per_document_tiered": round(N["unit_usd_doc"], 6),
            "unit_usd_per_document_flat": round(N["unit_flat_usd_doc"], 6),
            "test_cost_by_class_tiered_usd": {c: r2(t["by_class"][c]["tiered"]) for c in CLASSES},
        },
        "reviewer_cost_in_qwen_calls": {k: {"usd_per_document": round(v["usd_doc"], 6), "x_tiered": round(v["x_tiered"], 3),
                                            "x_flat": round(v["x_flat"], 3), "measured": v["measured"]} for k, v in R.items()},
        "pipeline_x_tiered": {"traditional_qwen_agent_plus_measured_qwen_reviewer": round(N["traditional_x"], 3),
                              "agent_plus_decisions_v2": round(N["decisions_v2_pipeline_x"], 3),
                              "agent_plus_decisions_v3_0_0": round(N["decisions_v3_0_0_pipeline_x"], 3)},
        "saving_vs_traditional_tiered": {"decisions_v2": round(N["decisions_v2_saving_vs_traditional"], 4),
                                         "decisions_v3_0_0": round(N["decisions_v3_0_0_saving_vs_traditional"], 4)},
        "saving_vs_traditional_flat": {"decisions_v2": round(N["decisions_v2_saving_vs_traditional_flat"], 4),
                                       "decisions_v3_0_0": round(N["decisions_v3_0_0_saving_vs_traditional_flat"], 4)},
        "decisions_review_vs_qwen_review": {"decisions_v2": round(N["decisions_v2_vs_qwen_reviewer"], 3),
                                            "decisions_v3_0_0": round(N["decisions_v3_0_0_vs_qwen_reviewer"], 3)},
        "qwen_reviewer_measured": {k: N["qwen_reviewer"][k] for k in (
            "run_id", "documents", "class_correct", "class_accuracy", "prompt_tokens", "completion_tokens", "list_cost_usd_tiered",
            "list_cost_usd_flat", "openrouter_billed_usd", "wrong_answers", "wrong_at_confidence_ge_0_90")},
        "pipeline_x_flat": {"traditional_qwen_agent_plus_measured_qwen_reviewer": round(N["traditional_x_flat"], 3),
                            "agent_plus_decisions_v2": round(N["decisions_v2_pipeline_x_flat"], 3),
                            "agent_plus_decisions_v3_0_0": round(N["decisions_v3_0_0_pipeline_x_flat"], 3)},
        "people_needed_per_1000": {k: round(v, 1) for k, v in N["person_per_1000"].items()},
        "breakeven_usd_per_person_review": {"decisions_v2": round(N["breakeven_v2_usd_per_review"], 5),
                                            "decisions_v3_0_0": round(N["breakeven_v3_usd_per_review"], 5)},
        "extra_usd_per_1000_docs": {"decisions_v2": round(N["extra_v2_per_1000"], 3), "decisions_v3_0_0": round(N["extra_v3_per_1000"], 3)},
        "people_avoided_per_1000_vs_qwen_alone": {"decisions_v2": round(N["avoided_v2_per_1000"], 1), "decisions_v3_0_0": round(N["avoided_v3_per_1000"], 1)},
        "evidence_held_out_323": {
            "method": "two-sided Fisher exact test on counts; Wilson 95% intervals; unpaired (per-document pairing is not tracked)",
            "class_accuracy": {k: {"correct": c, "n": n, "ci95": [round(x, 4) for x in wilson(c, n)]}
                               for k, (c, n) in {"qwen_agent": (309, 323), "qwen_reviewer": (303, 323), "decisions_v2": (318, 323), "decisions_v3_0_0": (318, 323)}.items()},
            "p_wrong_qwen_reviewer_vs_decisions_v2": round(fisher_two_sided(20, 303, 5, 318), 4),
            "p_wrong_qwen_agent_vs_decisions_v2": round(fisher_two_sided(14, 309, 5, 318), 4),
            "p_wrong_qwen_reviewer_vs_qwen_agent": round(fisher_two_sided(20, 303, 14, 309), 4),
            "silent_errors": {"qwen_reviewer": {"k": 8, "n": 311, "ci95": [round(x, 4) for x in wilson(8, 311)]},
                              "decisions_v2": {"k": 1, "n": 318, "ci95": [round(x, 4) for x in wilson(1, 318)]},
                              "p": round(fisher_two_sided(8, 303, 1, 317), 4)},
        },
        "half_train_v3_1_0": {
            "run_id": HALF, "documents": N["half"]["meta"]["documents"], "answered": N["half"]["meta"]["answered"], "failures": N["half"]["meta"]["failures"],
            "cost_usd": N["half"]["cost_usd"], "input_tokens": N["half"]["meta"]["input_tokens"], "latency_s": {k: round(v, 2) for k, v in N["half"]["latency_s"].items()},
            "cost_vs_qwen_agent_unit_train": round(N["half"]["x_vs_qwen_agent_train"], 3),
            "accuracy_all": {k: v for k, v in N["half"]["all"].items() if k != "per_class"},
            "accuracy_clean_no_prior_reviewer_evidence": {k: v for k, v in N["half"]["clean"].items() if k != "per_class"},
            "per_class_all": N["half"]["all"]["per_class"], "routing": N["half"]["routing"], "sorter_alone_wrong": N["half"]["sorter_alone_wrong"],
            "prior_evidence_documents": N["half"]["prior_evidence_docs"], "verdict_by_need": N["half"]["verdict_by_need"],
            "human_verdict_documents": N["half"]["human_verdict_docs"], "multiple_documents_verdicts": N["half"]["multiple_documents"],
            "cutoffs_v2": N["half"]["v2_cutoffs"], "cutoffs_own_crossfit": N["half"]["own_cutoffs"],
        },
        "recorded_inputs": [{"run": r["run"], "split": r["split"], "n": r["n"], "correct": r["correct"], "cost_usd": r["cost"], "source": r["src"]} for r in RUNS],
    }


def dashboard(N, figs):
    t = N["qwen_test"]
    kp = [
        (f"{N['decisions_v3_0_0_pipeline_x']:.2f}-{N['decisions_v2_pipeline_x']:.2f}x", "agent + Decisions reviewer",
         f"vs {N['traditional_x']:.2f}x for agent + a measured Qwen reviewer: "
         f"{N['decisions_v3_0_0_saving_vs_traditional'] * 100:.0f}% cheaper to {-N['decisions_v2_saving_vs_traditional'] * 100:.0f}% dearer"),
        (f"{N['person_per_1000']['Decisions v2']:.0f} / 1,000", "documents needing a person",
         f"Decisions v2 vs {N['person_per_1000']['Qwen agent alone']:.0f} for the Qwen agent alone"),
        ("98.5% vs 93.8%", "class accuracy, held out", "Decisions v2 (318 of 323) vs the Qwen reviewer (303 of 323)"),
        ("0.5 s", "median Decisions call", f"vs {t['p50_s']:.1f} s for the Qwen agent"),
    ]
    parts = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<title>Decision Reviewer Report</title><style>{HTML_CSS}</style></head><body><main>",
             "<h1>Decision reviewer: cost and effectiveness</h1>",
             "<p class='lede'>Experiments with the Decisions model (<code>openai/gpt-6-luna-decisions</code>) as a reviewer, "
             "priced against a Qwen 3.7 Flash agent call as 1x. Every figure is rebuilt from tracked files by "
             "<code>build_decisions_report.py</code>.</p>",
             "<nav><a href='README.md'>Report index</a><a href='01-executive-summary.md'>Executive summary</a>"
             "<a href='02-cost-and-effectiveness.md'>Cost vs 1x Qwen</a></nav>",
             "<div class='kpis'>"]
    for v, l, s in kp:
        parts.append(f"<div class='tile'><div class='v'>{esc(v)}</div><div class='l'>{esc(l)}</div><div class='s'>{esc(s)}</div></div>")
    parts.append("</div>")
    parts.append("<div class='note'>Hover, or tab to, any mark for its numbers. Every chart has a table view below it.</div>")
    groups = [("Cost against the 1x Qwen agent call", ["f01", "f02", "f03", "f05"]),
              ("Effectiveness of the reviewer", ["f04", "f15", "f06", "f07", "f08"]),
              ("Question-set experiments", ["f09", "f10", "f11", "f12"]),
              ("Question set 3.1.0 on half the train split", ["f16", "f17"]),
              ("Extraction gate", ["f13", "f14"])]
    byid = {f.fid: (f, h) for f, h in figs}
    for title, ids in groups:
        parts.append(f"<h2>{esc(title)}</h2>")
        for i in ids:
            f, h = byid[i]
            parts.append(f"<figure>{f.svg(h)}<details><summary>Table view</summary>{table_html(*f.table)}</details></figure>")
    parts.append("<div id='tip' role='tooltip'></div>")
    parts.append(f"<script>{HTML_JS}</script></main></body></html>")
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if any generated file differs from disk")
    a = ap.parse_args()
    out, N, figs = build_all()
    stale = []
    for rel, text in out.items():
        p = HERE / rel
        if a.check:
            if not p.exists() or p.read_text(encoding="utf-8") != text:
                stale.append(rel)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
    if a.check:
        if stale:
            print("stale:", *stale, sep="\n  ")
            return 1
        print(f"ok: {len(out)} files up to date")
        return 0
    print(f"wrote {len(out)} files under {HERE.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
