"""Modal L4 vs hosted API, per document: break-even volumes and the scenario where Modal wins.

One calculation that the cost comparison (its break-even section), the GPU economics report and the
Pages site all quote, so no two reports can disagree. Every input is a measured figure in
``hub_data.json`` (cross-checked against the run reports); the only modelling steps are arithmetic:

* warm fleet at busy share u:  $/doc = busy $/doc ÷ u  (the fleet bills ``replicas × rate`` per hour busy or not)
* cold batch of N documents:   $/doc = busy $/doc + cycle ÷ N, cycle = (L5 boot + scale-down tail) × replicas × rate
* one L4 instead of two:        same busy $/doc at half the fleet $/h and half the throughput. This is the
  measured result of adding the second L4 (S2a 1×L4 vs S2b 2×L4, same 100 documents), and is marked as a
  projection wherever it is applied to a class that was only measured on 2×L4.
"""
from __future__ import annotations

import math

SAME_MODEL_API = "Qwen3-8B"  # hosted leg of the model Modal self-hosts (as Qwen3-8B-AWQ)
LOAD_SHARES = (1.0, 0.5, 0.25)  # busy shares drawn in the figure (scenario grid, not measurements)
COLD_BATCH = 1000  # cold-batch size drawn in the figure (scenario grid)


def _boot(D) -> float:
    return next(r["boot"] for r in D["ladder"] if r["rung"].startswith("l5"))


def _scaledown(D) -> float:
    s = {r["scaledown"] for r in D["fleet"].values() if r.get("scaledown")}
    assert len(s) == 1, s
    return s.pop()


CLS_OF_DIR = {"correspondence": "correspondence", "insurance": "insurance_claim", "corporate": "corporate_record",
              "contract": "contract", "merger": "merger_agreement"}


def prompts_of(run: str) -> str:
    return "v2" if run.endswith("-v2") else "MAUD" if run.endswith("-maud") else "production"


def _modal(D, run: str) -> dict:
    f, r = D["fleet"][run], D["runs"].get(run, {})
    return {"run": run, "model": f["model"].split("/")[-1], "replicas": f["replicas"], "usd": f["busy_usd"] / f["ok"],
            "score": f.get("score", r.get("overall")), "n": f["ok"], "docs_h": f["ok"] / f["wall"] * 3600,
            "prompts": prompts_of(run), "seqs": f.get("seqs"), "conc": f.get("conc")}


def _economics(m: dict, a: float, rate: float, cycle_s: float) -> dict:
    """Break-evens of one measured Modal configuration against a hosted $/doc ``a``."""
    out = {"ratio": m["usd"] / a, "save_1k": (a - m["usd"]) * 1000, "save_pct": 1 - m["usd"] / a,
           "cheaper": m["usd"] < a}
    for n_l4 in (1, 2):
        cycle = cycle_s * n_l4 * rate / 3600
        out[f"l4x{n_l4}"] = {
            "fleet_h": n_l4 * rate, "cap_docs_h": m["docs_h"] * n_l4 / m["replicas"], "cycle_usd": cycle,
            "projected": n_l4 != m["replicas"],
            "docs_h_star": n_l4 * rate / a if out["cheaper"] else None,
            "batch_star": math.ceil(cycle / (a - m["usd"])) if out["cheaper"] else None,
        }
    return out


def analyze(D, exclude=frozenset()) -> dict:
    """Per class: the scored Modal run vs every hosted leg; break-evens; the verdict; the optimal scenario.

    ``exclude`` names runs that are not deployable configurations (ladder rungs, the bf16 control, misrouted runs).
    """
    rate = D["l4_usd_per_hour"]
    boot, sd = _boot(D), _scaledown(D)
    s2a, s2b = (D["fleet"][k]["busy_usd"] / D["fleet"][k]["ok"] for k in ("sand032-s2a-corr100-1rep", "sand032-s2b-corr100-2rep"))
    by_cls: dict[str, list[dict]] = {}
    for run, f in D["fleet"].items():
        c = next((CLS_OF_DIR[part] for part in f["report"].split("/") if part in CLS_OF_DIR), None)
        if c and run not in exclude:
            by_cls.setdefault(c, []).append(_modal(D, run))
    rows, configs = [], []
    for c, pts in D["route"]["points"].items():
        mp = next(p for p in pts if p["route"] == "modal")
        m = _modal(D, mp["run"])
        m["score"] = mp["score"]
        api = [p for p in pts if p["route"] == "api"]
        cheap = min(api, key=lambda p: p["usd"])
        comparable = c != "contract"  # Modal: CUAD category F1; API: pipeline rubric
        row = {"cls": c, "label": D["labels"][c], "modal": m, "cheap": cheap, "api": sorted(api, key=lambda p: p["usd"]),
               "comparable": comparable, **_economics(m, cheap["usd"], rate, boot + sd)}
        # "wins on quality": at least the score of the hosted model it would replace (the cheapest one)
        row["quality_ok"] = comparable and m["score"] >= cheap["score"]
        row["best_api_score"] = max(p["score"] for p in api)
        # the same model on both routes: self-hosted AWQ on Modal vs the hosted API's Qwen3-8B
        same = next((p for p in api if p["family"] == SAME_MODEL_API), None)
        row["same"] = same and {"api": same, **_economics(m, same["usd"], rate, boot + sd)}
        rows.append(row)
        for cm in sorted(by_cls.get(c, []), key=lambda x: x["usd"]):
            cfg = {"cls": c, "label": row["label"], "modal": cm, "cheap": cheap, "comparable": comparable,
                   "canonical": cm["run"] == m["run"], **_economics(cm, cheap["usd"], rate, boot + sd)}
            cfg["quality_ok"] = comparable and cm["score"] is not None and cm["score"] >= cheap["score"]
            configs.append(cfg)

    s6 = D["route"]["sorter_modal"]
    api_s = [{"family": r["model"], "usd": r["cost"] / r["n"], "score": r["class_acc"], "n": r["n"], "run": r["run"]}
             for r in D["api"]["classification"] if r["n"] >= 100]
    cheap_s = min(api_s, key=lambda p: p["usd"])
    sorter = {"modal": {"run": s6["run"], "usd": s6["usd"], "score": s6["acc"], "n": int(s6["ok"])}, "cheap": cheap_s,
              "api": sorted(api_s, key=lambda p: p["usd"]), "ratio": s6["usd"] / cheap_s["usd"],
              "modernbert": {"usd": D["mb"]["run3_reeval"]["sorter"]["mb_usd"], "score": D["mb"]["armB"]["acc"],
                             "n": D["mb"]["armB"]["n"]}}

    wins = [r for r in configs if r["cheaper"] and r["quality_ok"]]
    pick = {}
    for r in rows:
        xs = [x for x in configs if x["cls"] == r["cls"]]
        pick[r["cls"]] = (min((x for x in xs if x["cheaper"] and x["quality_ok"]), key=lambda x: x["modal"]["usd"], default=None)
                          or min((x for x in xs if x["cheaper"]), key=lambda x: x["modal"]["usd"], default=None)
                          or min(xs, key=lambda x: x["modal"]["usd"]))
    optimal = max(wins, key=lambda r: r["save_pct"]) if wins else None
    return {"rate": rate, "boot": boot, "scaledown": sd, "cycle_s": boot + sd, "s2a": s2a, "s2b": s2b,
            "rows": rows, "configs": configs, "pick": pick, "sorter": sorter, "wins": wins, "optimal": optimal,
            "win_classes": [r for r in rows if any(w["cls"] == r["cls"] for w in wins)],
            "cost_only": [r for r in rows if not any(w["cls"] == r["cls"] for w in wins)
                          and any(x["cheaper"] for x in configs if x["cls"] == r["cls"])],
            "never": [r for r in rows if not any(x["cheaper"] for x in configs if x["cls"] == r["cls"])]}


def verdict(r) -> str:
    if not r["cheaper"]:
        return "API cheaper at any volume"
    if not r["comparable"]:
        return "Modal cheaper; scores not comparable"
    if r["quality_ok"]:
        return "Modal wins on cost and quality"
    return "Modal cheaper, lower quality"


def fig(E, viz, usd) -> str:
    """Modal cost relative to the cheapest hosted model (1.0 = parity), warm at falling load and as a cold batch.

    One panel per class, drawn for that class's deciding configuration (``pick``: its cheapest configuration that
    wins, else its cheapest one that undercuts the API, else its cheapest one).
    """
    panels = []
    picks = [E["pick"][r["cls"]] for r in E["rows"]]
    dom = max(r["ratio"] / min(LOAD_SHARES) for r in picks)
    for r in picks:
        a, m = r["cheap"]["usd"], r["modal"]["usd"]
        bars = [{"label": f"warm · {u * 100:.0f}% busy", "value": round(m / u / a, 3), "emphasis": m / u <= a,
                 "note": f"{usd(m / u)} per doc vs {usd(a)}"} for u in LOAD_SHARES]
        for n_l4 in (1, 2):
            v = (m + r[f"l4x{n_l4}"]["cycle_usd"] / COLD_BATCH) / a
            bars.append({"label": f"cold {n_l4}×L4 · {COLD_BATCH:,} docs", "value": round(v, 3), "emphasis": v <= 1,
                         "note": f"cold cycle {usd(r[f'l4x{n_l4}']['cycle_usd'])}"})
        panels.append(viz.hbar(f"{r['label']} · {r['modal']['run']} vs {r['cheap']['family']} (API)",
                               f"Modal $/doc ÷ cheapest API $/doc · below 1.0 Modal is cheaper · {verdict(r)}",
                               bars, fmt=lambda v: f"{v:.2f}×", refs=[(1.0, "parity")], width=560, label_w=170,
                               domain_max=dom))
    model = E["rows"][0]["modal"]["model"]
    return viz.small_multiples(f"Self-hosted {model} (Modal) vs the cheapest API model, cost per document "
                               "(blue = Modal cheaper; one shared scale)", panels, cols=2)
