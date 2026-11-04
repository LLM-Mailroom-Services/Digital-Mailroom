"""Build the Mailroom reports hub (``mailroom-reports.html``).

    python reports/dashboard/build_hub.py sync [--eval-env PATH] [--mailroom-ml PATH]
        Re-read eval-environment and mailroom-ml from sibling checkouts into
        external_snapshot.json (default paths: ../eval-environment, ../mailroom-ml).
    python reports/dashboard/build_hub.py            # rebuild the page from sources + snapshot
    python reports/dashboard/build_hub.py --check    # fail if the page, data or snapshot is stale
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import legacy_runs as legacy  # noqa: E402
import hub_extract as H  # noqa: E402

TEMPLATE = HERE / "hub.template.html"
PAGE = HERE / "mailroom-reports.html"
DATA = HERE / "hub_data.json"
SNAPSHOT = HERE / "external_snapshot.json"
EVAL_ENV = "LLM-Mailroom-Services/eval-environment"
MAILROOM_ML = "LLM-Mailroom-Services/mailroom-ml"


def sibling(flag: str | None, env: str, name: str) -> pathlib.Path:
    for cand in (flag, os.environ.get(env), H.SANDBOX.parent / name):
        if cand and (pathlib.Path(cand) / ".git").exists():
            return pathlib.Path(cand)
    raise SystemExit(f"{name} checkout not found (pass --{name} or set {env})")


def extract_external(ev_root: pathlib.Path, ml_root: pathlib.Path) -> dict:
    L = H.Ledger(H.KNOWN)
    ev = H.Repo(EVAL_ENV, ev_root, L, "reports")
    ml = H.Repo(MAILROOM_ML, ml_root, L)
    api = H.eval_env(ev)
    api["sorter"] = H.sorter_cases(H.Repo(EVAL_ENV, ev_root, L), api["classification"])
    api["route50"] = H.eval_env_route50(ev)
    mb = H.mailroom_ml(ml)
    mb["run3_reeval"] = H.eval_env_modernbert(ev)
    return {"sources": {EVAL_ENV: ev.sha, MAILROOM_ML: ml.sha}, "api": api, "mb": mb,
            "issues": L.issues, "checks": L.checks, "provenance": list(L.prov.values())}


def dumps(obj) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


CLS_LABEL = {"correspondence": "Correspondence", "insurance_claim": "Insurance claims", "corporate_record": "Corporate records",
             "contract": "Contracts", "merger_agreement": "Merger agreements"}
S3 = {"correspondence": "sand032-s3-corr50", "insurance_claim": "sand032-s3-insurance50", "corporate_record": "sand032-s3-corporate50",
      "contract": "sand032-s3-contracts50", "merger_agreement": "sand032-s5-merger50-maud"}


def assemble(ext: dict) -> dict:
    L = H.Ledger(H.KNOWN)
    sb = H.Repo("Exios66/local-mailroom-sandbox", H.SANDBOX, L, "reports")
    sb.sha = "this commit"  # sources ship in the same commit as the page
    s32 = H.sand032(sb)
    old = legacy.build()
    # ModernBERT run-2 trainer figure lives in the sandbox copy of the run-2 report
    run2 = sb.cell("mb.run2.acc", "modernbert/RUN-02-MODERNBERT-HELDOUT-TEST-REPORT.md", "| doc_type accuracy |", 1)
    runs = s32["runs"]
    for r in runs.values():
        r["label"] = CLS_LABEL[r["cls"]]

    # ---- history: every local Qwen run per class, oldest first
    hist = []
    for h in old["history"]:
        hist.append({"cls": "correspondence", "run": h["run"], "score": h["score"], "era": "earlier", "date": h["date"]})
    for t, key in [("insurance_claim", "Insurance claims"), ("corporate_record", "Corporate records")]:
        hist.append({"cls": t, "run": "run-20 (1×L4, c8)", "score": old["quality"][key]["modal"], "era": "earlier", "date": "27 Sep"})
    for rid, lab in [("sand032-l0-baseline", "L0 baseline"), ("sand032-l5-graphs", "L5 frozen config"),
                     ("sand032-s4-corr20-bf16", "bf16 arm"), ("sand032-s2a-corr100-1rep", "n=100 · 1×L4"),
                     ("sand032-s2b-corr100-2rep", "n=100 · 2×L4"), ("sand032-s3-corr50", "n=50 · 2×L4 c32"),
                     ("sand032-s3-corr50-repeat", "n=50 repeat")]:
        hist.append({"cls": "correspondence", "run": lab, "score": runs[rid]["overall"], "era": "sand032", "date": "27 Sep"})
    for t in ("insurance_claim", "corporate_record"):
        hist.append({"cls": t, "run": "n=50 · 2×L4 c32", "score": runs[S3[t]]["overall"], "era": "sand032", "date": "27 Sep"})

    # ---- cost per doc: earlier c8 run-20 vs SAND-032 sweep
    cost_cmp = []
    for t, key in [("correspondence", "Correspondence"), ("insurance_claim", "Insurance claims"), ("corporate_record", "Corporate records"),
                   ("contract", "Contracts"), ("merger_agreement", "Merger agreements")]:
        cost_cmp.append({"cls": t, "label": CLS_LABEL[t], "earlier": old["cost"][key]["modal"], "sand032": runs[S3[t] if t != "merger_agreement" else "sand032-s3-merger50"]["usd_per_doc"]})

    # ---- speedup vs concurrency, every run with a measured sum(latency)/wall
    conc = [{"run": c["run"], "c": c["c"], "s": c["s"], "eng": "granite" if c["eng"] == "granite" else "earlier"} for c in old["conc"]]
    for rid, r in runs.items():
        conc.append({"run": rid.replace("sand032-", ""), "c": r["conc"], "s": r["speedup"], "eng": "sand032"})

    # ---- GPU economics: every SAND-032 serving export against its run report
    fleet = H.sand032_fleet(sb, runs)
    billed = sum(r["billed_usd"] for r in fleet.values())
    L.check(s32["spend"] >= billed + s32["incident"],
            f"ledger ${s32['spend']} covers the runs' billed GPU ${billed:.3f} + incident ${s32['incident']}")

    # ---- route comparison: the isolated sorter on Modal (SAND-032 S6, n = 458 drawn)
    s6 = "serving/SAND-32/SAND032-S6-SORTER1000-REPORT.md"
    sorter_modal = {
        "run": "sand032-s6-sorter1000",
        "acc": sb.rx("route.s6.acc", s6, r"\| \*\*accuracy\*\* \| \*\*([0-9.]+)\*\* \|"),
        "macro_f1": sb.rx("route.s6.f1", s6, r"\| \*\*macro-F1\*\* \| \*\*([0-9.]+)\*\* \|"),
        "ok": sb.rx("route.s6.ok", s6, r"\| docs ok / total \| (\d+) / \d+ \|"),
        "n": sb.rx("route.s6.n", s6, r"\| docs ok / total \| \d+ / (\d+) \|"),
    }
    # busy-window basis like every other SAND-032 $/doc (the report's figure is billed; see KNOWN)
    sorter_modal["usd"] = fleet["sand032-s6-sorter1000"]["busy_usd"] / sorter_modal["ok"]

    ml = specialist_ml(runs)
    api = ext["api"]
    mb = ext["mb"]
    t = text(runs, s32, api, mb, old, run2, cost_cmp)
    t.update(ml_text(ml, mb))
    t.update(route_text(runs, api, mb, sorter_modal))
    issues = old["issues"] + L.issues + ext["issues"]
    prov = old["provenance"] + list(L.prov.values()) + ext["provenance"]
    for p in old["provenance"]:
        p.setdefault("repo", "Exios66/local-mailroom-sandbox")
        p.setdefault("sha", "this commit")
    sources = {"Exios66/local-mailroom-sandbox": sb.sha, **ext["sources"]}
    t["n_figures"] = f"{len(prov):,}"
    t["n_checks"] = f"{L.checks + ext['checks']:,}"
    t["n_issues"] = str(len(issues))
    t["sources"] = " · ".join(f"{k.split('/')[-1]} @ {v[:7]}" for k, v in ext["sources"].items())
    return {
        "classes": list(CLS_LABEL), "labels": CLS_LABEL, "s3": S3, "runs": runs, "ladder": s32["ladder"],
        "spend": {"sand032": s32["spend"], "stage5": s32["spend_stage5"], "cap": s32["cap"], "incident": s32["incident"],
                  "legacy": old["spend"], "legacy_total": old["total_spend"]},
        "fleet": fleet, "l4_usd_per_hour": H.L4_USD_PER_HOUR,
        "ml": ml, "history": hist, "cost_cmp": cost_cmp, "conc": conc, "rel": old["rel"], "api": api, "mb": mb, "mb_run2": run2,
        "route": {"sorter_modal": sorter_modal, "points": route_points(runs, api)},
        "issues": issues, "provenance": prov, "sources": sources, "text": t,
    }


TASK_OF = {"correspondence": "correspondence", "insurance_claim": "insurance claims", "corporate_record": "corporate records",
           "contract": "contracts", "merger_agreement": "merger agreements"}


LOGGED_FAMILY = {"qwen/qwen3.7-flash": "Qwen3.7-Flash", "qwen/qwen3-8b": "Qwen3-8B",
                 "deepseek/deepseek-v4.1-flash": "DeepSeek-V4.1-Flash", "ibm-granite/granite-4.2-8b": "Granite-4.2-8B"}


def route_points(runs, api) -> dict:
    """Per class: the Modal self-hosted run and every hosted-API leg, as (score, $/doc) points."""
    out = {}
    for c, task in TASK_OF.items():
        r = runs[S3[c]]
        pts = [{"route": "modal", "family": "Qwen3-8B-AWQ", "run": S3[c], "n": r["ok"], "score": r["overall"],
                "usd": r["usd_per_doc"], "revision": "ed7576b6", "prompts": "production" + (" (MAUD)" if "maud" in S3[c] else "")}]
        q = api["route50"][task]
        pts.append({"route": "api", "family": "Qwen3.7-Flash", "run": q["run"], "n": q["n"], "score": q["score"],
                    "usd": q["cost"] / q["n"], "revision": q["revision"], "prompts": q["prompt_lineage"]})
        for m, rec in api["tasks"][task].items():
            # Label by the model the run logged, not the folder it is filed under
            # (hub issue api.qwen_merger_model: a Qwen3.7-Flash leg filed as Qwen3-8B).
            fam = rec["family"]
            if LOGGED_FAMILY.get(rec["model"], fam) != fam:
                fam = f"{LOGGED_FAMILY[rec['model']]} · {rec['prompt_lineage']}"
            pts.append({"route": "api", "family": fam, "run": rec["run"], "n": rec["n"], "score": rec["score"],
                        "usd": rec["cost"] / rec["n"], "revision": rec["revision"], "prompts": rec["prompt_lineage"]})
        out[c] = pts
    return out


def _sig2(x: float) -> float:
    """Round to two significant figures (a ratio of estimates is not exact)."""
    return float(f"{x:.2g}")


def route_text(runs, api, mb, sorter_modal) -> dict:
    pts = route_points(runs, api)
    cheap_modal = [c for c, ps in pts.items() if ps[0]["usd"] <= min(p["usd"] for p in ps[1:])]
    # Contracts are scored differently on the two routes (Modal: CUAD category F1;
    # API: pipeline rubric), so quality is compared on the other four tasks only.
    comparable = {c: ps for c, ps in pts.items() if c != "contract"}
    best_modal = [c for c, ps in comparable.items() if ps[0]["score"] >= max(p["score"] for p in ps[1:])]
    n, nq = len(pts), len(comparable)
    ratio = {c: min(p["usd"] for p in ps[1:]) / ps[0]["usd"] for c, ps in pts.items()}
    gap = {c: max(p["score"] for p in ps[1:]) - ps[0]["score"] for c, ps in comparable.items()}
    worst = max(gap, key=gap.get)
    cls = sorted(api["classification"], key=lambda r: -r["class_acc"])
    best_api = next(r for r in cls if r["n"] >= 100)
    mb_usd = mb["run3_reeval"]["sorter"]["mb_usd"]
    # Newest run the page draws on (eval-environment run ids are UTC timestamps);
    # the program began with the 16 Sep runs.
    stamps = [r["run"][:8] for r in api["route50"].values()] + [r["run"][:8] for r in api["classification"]]
    stamps += [rec["run"][:8] for task in api["tasks"].values() for rec in task.values()]
    last = max(s for s in stamps if s.isdigit())
    return {
        "date_range": f"16–{int(last[6:8])} Sep {last[:4]}",
        "route_head": (f"Modal L4 is the cheaper route on {len(cheap_modal)} of {n} specialist tasks; "
                       f"a hosted model scores higher on {nq - len(best_modal)} of the {nq} tasks scored alike"),
        "route_cheap": ", ".join(CLS_LABEL[c].lower() for c in cheap_modal) or "none",
        "route_best": ", ".join(CLS_LABEL[c].lower() for c in best_modal) or "no task",
        "route_worst": CLS_LABEL[worst].lower(),
        "route_worst_gap": f"{gap[worst]:.2f}",
        "route_corr_ratio": f"{ratio['correspondence']:.1f}",
        "route_sorter_head": (f"ModernBERT matches the best hosted sorter ({mb['armB']['acc'] * 100:.1f}% vs "
                              f"{best_api['class_acc'] * 100:.1f}%) at about "
                              f"{_sig2(best_api['cost'] / best_api['n'] / mb_usd):,.0f}× lower cost per document"),
        "route_s6_acc": f"{sorter_modal['acc'] * 100:.1f}%",
        "route_s6_usd": f"${sorter_modal['usd']:.4f}",
    }


def specialist_ml(runs) -> dict:
    """Surrogate ALE + EDA over the SAND-032 class sweep (completed documents)."""
    import ale

    rows = []
    for c, rid in S3.items():
        for d in runs[rid]["docs"]:
            if d["error"]:
                continue
            rows.append({"cls": c, "lat": d["latency"], "pk": d["prompt"] / 1000, "ck": d["completion"] / 1000,
                         "score": d["overall"], "schema": d["schema"]})
    ext = [r for r in rows if r["cls"] in ("correspondence", "insurance_claim", "corporate_record")]
    schema = {}
    for c in ("correspondence", "insurance_claim", "corporate_record"):
        for flag in (True, False):
            v = [r["score"] for r in ext if r["cls"] == c and r["schema"] == flag]
            schema.setdefault(c, {})["valid" if flag else "invalid"] = {"n": len(v), "mean": round(sum(v) / len(v), 4) if v else None}
    return {
        "lat_prompt": ale.ale(rows, "lat", ["pk", "ck"], "pk", cat="cls"),
        "lat_compl": ale.ale(rows, "lat", ["pk", "ck"], "ck", cat="cls"),
        "score_prompt": {c: ale.ale(ext, "score", ["pk", "ck"], "pk", cat="cls", subset=lambda r, c=c: r["cls"] == c)
                         for c in ("correspondence", "insurance_claim", "corporate_record")},
        "schema": schema, "n_docs": len(rows),
    }


def ml_text(ml: dict, mb: dict) -> dict:
    B = mb["armB"]["eda"]
    lc, lp = ml["lat_compl"], ml["lat_prompt"]
    effects = {}
    for c, a in ml["score_prompt"].items():
        mid = (a["x"][0] + a["x"][-1]) / 2
        pts = [(x, v) for x, v, lo, hi in zip(a["x"], a["ale"], a["lo"], a["hi"]) if (lo > 0 or hi < 0) and abs(v) >= 0.05]
        if pts:
            rising = all((v < 0) == (x < mid) for x, v in pts)
            falling = all((v > 0) == (x < mid) for x, v in pts)
            effects[c] = "rise" if rising else "fall" if falling else "vary"
    none = [CLS_LABEL[c].lower() for c in ml["score_prompt"] if c not in effects]
    if not effects:
        head = "No length effect on extraction clears its 90% band"
    else:
        adj = {"correspondence": "correspondence", "insurance_claim": "insurance-claim", "corporate_record": "corporate-record"}
        parts = [f"{adj[c]} scores {'rise' if e == 'rise' else 'fall' if e == 'fall' else 'vary'} with document length" for c, e in effects.items()]
        head = "; ".join(parts)
        head = head[0].upper() + head[1:]
        if none:
            head += f"; length does not move {' or '.join(none)}"
    col = B["collapse"]
    over = [c for c in CLS_LABEL if c in col and (col[c]["top_pred"][1] - col[c]["top_true"][1]) / col[c]["n"] >= 0.25]
    names = [CLS_LABEL[c].lower().rstrip("s") for c in over]
    words = {0: "No", 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}
    collapse_head = (f"{words[len(over)]} of five Arm B heads over-predict one subclass"
                     + (f": {', '.join(names[:-1]) + ' and ' + names[-1] if len(names) > 1 else names[0]}" if names else ""))
    return {
        "collapse_head": collapse_head,
        "fp_b": f"{B['fast']['correct']}/{B['fast']['n']}",
        "con_sub": f"{B['subclass']['contract']['correct']}/{B['subclass']['contract']['n']}",
        "con_n": str(B["contract_n"]),
        "f1_con": f"{mb['armB']['macro_f1']['contract']:.3f}", "f1_corr": f"{mb['armB']['macro_f1']['correspondence']:.3f}",
        "lat_ck_range": f"{max(lc['ale']):.0f}", "lat_ratio": f"{lc['range'] / lp['range']:.1f}",
        "ml_n": str(ml["n_docs"]), "score_len_head": head,
    }


def text(runs, s32, api, mb, old, run2, cost_cmp) -> dict:
    l0, l5 = s32["ladder"][0], s32["ladder"][-1]
    a, b = runs["sand032-s2a-corr100-1rep"], runs["sand032-s2b-corr100-2rep"]
    corr, ins = runs["sand032-s3-corr50"], runs["sand032-s3-insurance50"]
    m0, m1 = runs["sand032-s3-merger50"], runs["sand032-s5-merger50-maud"]
    arm_b, run3 = mb["armB"], mb["run3"]
    tasks = api["tasks"]
    best = {tk: max(v.items(), key=lambda kv: kv[1]["score"]) for tk, v in tasks.items()}
    dsk = sum(1 for tk, (m, _) in best.items() if m.startswith("deepseek"))
    api_cost = {m: sum(tasks[tk][m]["cost"] for tk in tasks) for m in tasks["contracts"]}
    corr_drop = cost_cmp[0]["earlier"] / cost_cmp[0]["sand032"]
    # ---- claims made in headings, computed and asserted
    red = [r["earlier"] / r["sand032"] for r in cost_cmp]
    s3 = [runs[S3[c]] for c in S3]
    rel_runs = s3 + [runs["sand032-s3-merger50"]]
    err = [(r["n"] - r["ok"]) / r["n"] for r in rel_runs if r["n"] > r["ok"]]
    slow = [runs[S3[c]]["p50"] / runs[S3["correspondence"]]["p50"] for c in ("contract", "merger_agreement")]
    cheapest = {tk: min(v, key=lambda m: v[m]["cost"] / v[m]["n"]) for tk, v in tasks.items()}
    n_ds_cheap = sum(1 for m in cheapest.values() if m.startswith("deepseek"))
    cls100 = [c for c in api["classification"] if c["n"] == 100]
    corp3 = mb["run3"]["per_class"]["corporate_record"]
    corpb = mb["armB"]["per_class"]["corporate_record"]
    lead = {tk: m for tk, (m, _) in best.items()}
    assert lead["insurance claims"].startswith("deepseek") and lead["corporate records"].startswith("deepseek")
    assert lead["correspondence"] == "qwen3-8b" and lead["contracts"] == "qwen3-8b"
    assert all(r["n"] == r["ok"] for r in s3 if r["cls"] in ("correspondence", "insurance_claim", "corporate_record"))
    spread = {}
    for c in ("correspondence", "insurance_claim", "corporate_record"):
        big = [x["mean"] for x in runs[S3[c]]["strata"] if x["n"] >= 3]
        spread[c] = (min(big), max(big))
    wide = max(spread, key=lambda c: spread[c][1] - spread[c][0])
    sorter = api["sorter"]
    ece = sorted((v["ece"], m) for m, v in sorter.items())
    names = {"deepseek/deepseek-v4.1-flash": "DeepSeek-V4.1-Flash", "ibm-granite/granite-4.2-8b": "Granite-4.2-8B",
             "qwen/qwen3.7-flash": "Qwen3.7-Flash"}
    short = lambda m: names.get(m, m.split("/")[-1])  # noqa: E731
    sorter_head = (f"{short(ece[0][1])} states its confidence most honestly (ECE {ece[0][0]:.3f}); "
                   f"{short(ece[-1][1])} is furthest off ({ece[-1][0]:.3f})")
    return {
        "sorter_head": sorter_head,
        "sub_wide_cls": CLS_LABEL[wide].lower(), "sub_wide_lo": f"{spread[wide][0]:.2f}", "sub_wide_hi": f"{spread[wide][1]:.2f}",
        "cost_red_lo": f"{min(red):.1f}", "cost_red_hi": f"{max(red):.0f}",
        "err_lo": f"{min(err) * 100:.0f}", "err_hi": f"{max(err) * 100:.0f}",
        "slow_lo": f"{min(slow):.0f}", "slow_hi": f"{max(slow):.0f}",
        "api_ds_cheap": str(n_ds_cheap),
        "cls100_lo": f"{min(c['class_acc'] for c in cls100) * 100:.0f}", "cls100_hi": f"{max(c['class_acc'] for c in cls100) * 100:.0f}",
        "sub100_lo": f"{min(c['subclass_acc'] for c in cls100) * 100:.0f}", "sub100_hi": f"{max(c['subclass_acc'] for c in cls100) * 100:.0f}",
        "corp_run3": f"{corp3['correct'] / corp3['n'] * 100:.0f}%", "corp_armb": f"{corpb['correct'] / corpb['n'] * 100:.0f}%",
        "maud_cov": f"{runs['sand032-s5-merger50-maud']['maud_answered'] / runs['sand032-s5-merger50-maud']['maud_questions'] * 100:.0f}%",
        "ins_score": f"{ins['overall']:.3f}", "corr_score": f"{corr['overall']:.3f}",
        "corr_score_repeat": f"{runs['sand032-s3-corr50-repeat']['overall']:.3f}",
        "l5_wall_cut": f"{(1 - l5['wall'] / l0['wall']) * 100:.1f}%", "l5_usd_cut": f"{(1 - l5['usd'] / l0['usd']) * 100:.1f}%",
        "l5_tps": f"{l5['tps']:,.0f}", "l0_tps": f"{l0['tps']:,.0f}", "l5_usd": f"${l5['usd']:.6f}", "l5_score": f"{l5['score']:.4f}", "l0_score": f"{l0['score']:.4f}",
        "scale_speed": f"{a['wall'] / b['wall']:.2f}", "scale_usd_a": f"${a['usd_per_doc']:.6f}", "scale_usd_b": f"${b['usd_per_doc']:.6f}",
        "corr_usd": f"${corr['usd_per_doc']:.6f}", "corr_drop": f"{corr_drop:.0f}",
        "spend": f"${s32['spend']:.2f}", "cap": f"${s32['cap']:.2f}",
        "maud0": f"{m0['headline'] * 100:.1f}%", "maud1": f"{m1['headline'] * 100:.1f}%",
        "cuad_f1": f"{runs['sand032-s3-contracts50']['headline']:.3f}",
        "bf16": f"{runs['sand032-s4-corr20-bf16']['overall']:.4f}",
        "armb_acc": f"{arm_b['acc'] * 100:.2f}%", "run3_acc": f"{run3['acc'] * 100:.2f}%", "arma_acc": f"{mb['armA']['acc'] * 100:.2f}%",
        "reeval_acc": f"{mb['run3_reeval']['acc'] * 100:.2f}%", "run2_acc": f"{run2 * 100:.2f}%",
        "armb_pick": f"{arm_b['pick']:.2f}", "armb_cov": f"{arm_b['pick_cov'] * 100:.1f}%", "armb_pick_acc": f"{arm_b['pick_acc'] * 100:.2f}%",
        "armb_fast": f"{arm_b['fast_path'] * 100:.1f}%", "armb_ood": f"{arm_b['ood'] * 100:.1f}%",
        "armb_sub": f"{arm_b['subclass'] * 100:.1f}%",
        "api_best_ds": str(dsk), "api_ds_cost": f"${api_cost['deepseek-v4.1-flash']:.3f}",
        "api_q_cost": f"${api_cost['qwen3-8b']:.3f}", "api_g_cost": f"${api_cost['granite-4.2-8b']:.3f}",
        "api_ins_ds": f"{tasks['insurance claims']['deepseek-v4.1-flash']['score']:.3f}",
    }


def render(data: dict) -> str:
    html = TEMPLATE.read_text()
    for k, v in data["text"].items():
        html = html.replace("{{" + k + "}}", v)
    left = sorted(set(re.findall(r"\{\{[a-z_0-9]+\}\}", html)))
    if left:
        raise H.SourceError(f"unfilled placeholders: {left}")
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    return html.replace("/*__DATA__*/", payload)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the Mailroom reports hub")
    ap.add_argument("cmd", nargs="?", default="build", choices=["build", "sync"])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--eval-env")
    ap.add_argument("--mailroom-ml")
    args = ap.parse_args(argv)
    if args.cmd == "sync":
        ext = extract_external(sibling(args.eval_env, "EVAL_ENV_ROOT", "eval-environment"),
                               sibling(args.mailroom_ml, "MAILROOM_ML_ROOT", "mailroom-ml"))
        SNAPSHOT.write_text(dumps(ext))
        print(f"wrote {SNAPSHOT.name}: {len(ext['provenance'])} figures, {ext['checks']} checks, sources {ext['sources']}")
        return 0
    ext = json.loads(SNAPSHOT.read_text())
    data = assemble(ext)
    page, data_json = render(data), dumps(data)
    if args.check:
        stale = [p.name for p, body in ((PAGE, page), (DATA, data_json)) if not p.exists() or p.read_text() != body]
        try:
            fresh = extract_external(sibling(args.eval_env, "EVAL_ENV_ROOT", "eval-environment"),
                                     sibling(args.mailroom_ml, "MAILROOM_ML_ROOT", "mailroom-ml"))
            if dumps(fresh) != SNAPSHOT.read_text():
                stale.append(f"{SNAPSHOT.name} (sibling checkouts moved: run `build_hub.py sync`)")
        except SystemExit:
            pass  # siblings absent: the committed snapshot is the pinned source
        if stale:
            print("stale: " + ", ".join(stale), file=sys.stderr)
            return 1
        print(f"ok: {data['text']['n_figures']} figures, {data['text']['n_checks']} cross-checks, {len(data['issues'])} documented issues")
        return 0
    PAGE.write_text(page)
    DATA.write_text(data_json)
    print(f"wrote {PAGE.name}: {data['text']['n_figures']} figures, {data['text']['n_checks']} cross-checks, {len(data['issues'])} documented issues")
    return 0


if __name__ == "__main__":
    sys.exit(main())
