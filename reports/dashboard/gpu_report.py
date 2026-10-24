"""Modal + vLLM GPU economics report for the mailroom-issues hub (SAND-032, Qwen3-8B-AWQ on Modal L4).

Called by ``export_hub_reports.py``; it writes ``MODAL-VLLM-GPU-REPORT.md`` and ``figures/gpu/*.svg``.
Every SAND-032 number comes from ``hub_data.json["fleet"]``: each serving export
(``reports/serving/SAND-32/sand032-*.serving.json``) cross-checked against its run report by
``hub_extract.sand032_fleet``. The two pre-SAND-032 2×L4 runs are read from their tracked serving
exports and checked against their run reports here.

Cost basis (as in every SAND-032 report):
- busy GPU $ = wall × replicas × L4 $/h — the basis for $/doc and $/token;
- billed GPU $ = (wall + cold boot) × replicas × L4 $/h — a lower bound on the Modal bill for the run.
"""
from __future__ import annotations

import datetime
import json
import math
import posixpath
import re

SAND = "reports/"  # run-report paths in the fleet data are relative to the sandbox reports/ dir
# Classification rule, not a measurement: a run whose preflight probe waited at least this long started on a
# cold fleet (engine boot); anything shorter found the fleet already warm. Every SAND-032 export falls far to
# one side of it (warm probes answer in under a second, cold boots take minutes).
COLD_BOOT_MIN_S = 60

# Stage groups, in reading order. Labels are names only; every number is read from the fleet data.
GROUPS = [
    ("ladder", "1×L4 knob ladder · correspondence n = 20 · c8", [
        ("sand032-l0-baseline", "baseline"), ("sand032-l1-nothink", "+ thinking off"),
        ("sand032-l2-marlin", "+ awq_marlin (reverted)"), ("sand032-l5-graphs", "frozen config"),
        ("sand032-s4-corr20-bf16", "bf16 Qwen3-8B (quality arm)")]),
    ("scale", "Scale-out · correspondence n = 100 · same documents", [
        ("sand032-s2a-corr100-1rep", None), ("sand032-s2b-corr100-2rep", None),
        ("sand032-s7-corr100-seqs32", None), ("sand032-s9-corr100-bal", None)]),
    ("sweep", "Five-class sweep · 2×L4 · c32 · n = 50", [
        ("sand032-s3-corr50", "Correspondence"), ("sand032-s3-corr50-repeat", "Correspondence (repeat)"),
        ("sand032-s3-insurance50", "Insurance claims"), ("sand032-s3-corporate50", "Corporate records"),
        ("sand032-s3-contracts50", "Contracts"), ("sand032-s3-merger50", "Merger agreements"),
        ("sand032-s5-merger50-maud", "Merger agreements · MAUD prompt")]),
    ("c64", "Doubled admission · 2×L4 · c64 · n = 50", [
        ("sand032-s9-insurance50-bal", "Insurance claims"), ("sand032-s9-corporate50-bal", "Corporate records"),
        ("sand032-s9-contracts50-bal", "Contracts"), ("sand032-s7-insurance50-seqs32", "Insurance · max_inputs 64")]),
    ("v2", "v2 prompts · 1×L4 · c8 · n = 75", [
        ("sand032-s10-corr75-v2", "Correspondence"), ("sand032-s10-insurance75-v2", "Insurance claims"),
        ("sand032-s10-corporate75-v2", "Corporate records")]),
    ("sorter", "LLM sorter · 2×L4 · c32", [("sand032-s6-sorter1000", "LLM sorter")]),
]
SWEEP_BY_TASK = {"correspondence": "sand032-s3-corr50", "insurance claims": "sand032-s3-insurance50",
                 "corporate records": "sand032-s3-corporate50", "contracts": "sand032-s3-contracts50",
                 "merger agreements": "sand032-s3-merger50"}
# Pre-SAND-032 2×L4 runs: serving exports are on a 1-replica basis; the reports bill both replicas.
EARLY_2X = [("run-20-correspondence-specialist-awq", "SAND-32/correspondence/RUN-20-CORRESPONDENCE-SPECIALIST-AWQ-REPORT.md"),
            ("run-50-correspondence-specialist-awq", "SAND-32/correspondence/RUN-50-CORRESPONDENCE-SPECIALIST-AWQ-REPORT.md")]


# ------------------------------------------------------------------ derived metrics
def tok(r):
    return r["prompt_tokens"] + r["completion_tokens"]


def per_mtok(r):
    return r["busy_usd"] / tok(r) * 1e6


def per_mout(r):
    return r["busy_usd"] / r["completion_tokens"] * 1e6


def tps_l4(r):
    return r["tps"] / r["replicas"]


def fleet_name(r):
    mi = f" · max_inputs {r['max_inputs']}" if r.get("max_inputs") else ""
    return f"{r['replicas']}×L4 · c{r['conc']} · seqs {r['seqs']}{mi}"


def busier_share(r):
    req = [s["requests"] for s in r["replica_split"]]
    return max(req) / sum(req) if len(req) > 1 else None


def code(rid):
    c = rid.split("-")[1]
    return c[0].upper() + c[1:]


def lcfirst(s):
    return s if s[:2].isupper() else s[0].lower() + s[1:]


def run_label(r, lab):
    """Table/figure label: stage code plus a name (the fleet, for the scale-out runs)."""
    if lab is None:
        mi = f", max_inputs {r['max_inputs']}" if r["conc"] > 16 else ""
        lab = f"{r['replicas']}×L4, c{r['conc']}{mi}"
    return f"{code(r['run'])} · {lab}"


def describe(F, rid):
    """Prose name for a run: 'S6 (LLM sorter, 2×L4 at c32)'."""
    r = F[rid]
    lab = next(lab for _, _, members in GROUPS for r_id, lab in members if r_id == rid) or f"correspondence n = {r['n']}"
    return f"{code(rid)} ({lab}, {r['replicas']}×L4 at c{r['conc']})"


LABEL_FIELDS = [(r"(\d+)×L4", "replicas"), (r"\bc(\d+)\b", "conc"), (r"\bn = (\d+)", "n"), (r"max_inputs (\d+)", "max_inputs")]


def _check_labels(F):
    """Group titles and run labels are names, but any fleet figure they state must match the fleet data."""
    for _, title, members in GROUPS:
        for rid, lab in members:
            for text in (title, lab or ""):
                for pat, field in LABEL_FIELDS:
                    m = re.search(pat, text)
                    if m and int(m.group(1)) != F[rid][field]:
                        raise SystemExit(f"label {text!r} says {field} {m.group(1)}; {rid} has {F[rid][field]}")


def labelled(F):
    """(group key, group title, [(label, record)]) in reading order."""
    _check_labels(F)
    return [(key, title, [(run_label(F[rid], lab), F[rid]) for rid, lab in members]) for key, title, members in GROUPS]


def early_2x(X, rate) -> list[dict]:
    """Pre-SAND-032 2×L4 runs from their tracked serving exports, checked against their run reports.

    ``rate`` is the hub's ``l4_usd_per_hour``. Admission, engine mode and the run's sandbox commit are read from each
    report (the reports carry no run date).
    """
    out = []
    for rid, rep_path in EARLY_2X:
        d = X.serving(rid)
        text = (X.ROOT / "reports" / rep_path).read_text()
        eng = re.search(r"(\d+)× L4 \(data-parallel, one replica per L4\)", text)
        if not eng:
            raise SystemExit(f"{rep_path}: expected a data-parallel multi-L4 engine row")
        rep = int(eng.group(1))
        bill = re.search(r"estimated GPU cost \(billed, (\d+) replicas\) \| \*\*\$([\d.]+)\*\*", text)
        billed = float(bill.group(2))
        seqs = int(re.search(r"max_num_seqs=(\d+)", text).group(1))
        eager = re.search(r"enforce_eager=(\w+)", text).group(1)
        adm = re.search(r"\| concurrency \| (\d+) \(~(\d+) per replica\) \|", text)
        commit = re.search(r"^\| git \| `([0-9a-f]+)`", text, re.M)
        if int(bill.group(1)) != rep or abs(billed - rep * d["estimated_gpu_cost_usd"]) > 2e-6:
            raise SystemExit(f"{rep_path}: billed ${billed} is not {rep} × the 1-replica export")
        if not adm or int(adm.group(1)) != d["concurrency"] or int(adm.group(2)) != round(d["concurrency"] / rep):
            raise SystemExit(f"{rep_path}: concurrency row does not match the export over {rep} replicas")
        if not commit:
            raise SystemExit(f"{rep_path}: git row not found")
        out.append({"run": rid, "report": rep_path, "n": d["n"], "conc": d["concurrency"], "seqs": seqs, "replicas": rep,
                    "per_replica": int(adm.group(2)), "eager": eager, "commit": commit.group(1),
                    "wall": d["wall_seconds"], "tps": d["tokens_per_second"], "slot": d["slot_utilization"],
                    "busy_usd": rep * d["wall_seconds"] * rate / 3600,
                    "prompt_tokens": d["prompt_tokens"], "completion_tokens": d["completion_tokens"]})
    return out


# ------------------------------------------------------------------ setup (read from the fleet data)
def uniform(runs, key, what):
    """The one value every run that records ``key`` shares; aborts if the runs disagree."""
    vals = {r[key] for r in runs if r.get(key) is not None}
    if len(vals) != 1:
        raise SystemExit(f"runs disagree on {what}: {sorted(map(str, vals))}")
    return vals.pop()


def unrecorded(runs, key):
    return [code(r["run"]) for r in runs if r.get(key) is None]


def prov(D, key):
    return next(p for p in D["provenance"] if p["key"] == key)


def src_link(p):
    """Markdown link to a sandbox source file (absolute, so it resolves from mailroom-issues and the Pages site)."""
    from pages_site import SANDBOX_BLOB  # noqa: PLC0415

    path = posixpath.normpath(p["source"])
    return f"[`{path}`]({SANDBOX_BLOB}{path})"


def day_span(days):
    lo, hi = min(days), max(days)
    if lo == hi:
        return f"{lo.day} {lo:%b}"
    return f"{lo.day}–{hi.day} {hi:%b}" if (lo.year, lo.month) == (hi.year, hi.month) else f"{lo.day} {lo:%b}–{hi.day} {hi:%b}"


def setup_rows(D, all_runs, S):
    F = D["fleet"]
    l5 = F["sand032-l5-graphs"]
    models = sorted({r["model"] for r in all_runs}, key=lambda m: -sum(r["model"] == m for r in all_runs))
    by_model = {m: [r for r in all_runs if r["model"] == m] for m in models}
    vllm = uniform(all_runs, "vllm", "the vLLM version")
    miss = unrecorded(all_runs, "vllm")
    model_cell = "; ".join(
        f"`{m}` ({len(rs)} run{'s' if len(rs) != 1 else ''}, quant {', '.join(f'`{q}`' for q in sorted({r['quant'] for r in rs}))},"
        f" `max_model_len` {uniform(rs, 'max_model_len', f'max_model_len for {m}')})" for m, rs in by_model.items())
    model_cell += (f"; vLLM `{vllm}`" + (f" (not recorded in the {', '.join(miss)} report)" if miss else "")
                   + f", prefix caching {uniform(all_runs, 'prefix_caching', 'prefix caching')}")
    hi = [r for r in all_runs if r["seqs"] > l5["seqs"]]
    posture = (f"`{l5['quant']}`, {l5['kv_cache_dtype']} KV cache, thinking {l5['thinking']}, CUDA graphs "
               f"{'on' if l5['enforce_eager'] == 'off' else 'off'} (`enforce_eager={l5['enforce_eager']}`), `max_num_seqs` {l5['seqs']}"
               + (f" ({'/'.join(str(s) for s in sorted({r['seqs'] for r in hi}))} on the "
                  f"{'/'.join(f'c{c}' for c in sorted({r['conc'] for r in hi}))} runs)" if hi else ""))
    gpu, mem = uniform(all_runs, "gpu", "the GPU type"), prov(D, "fleet.gpu_spec.memory")
    pinned = [r for r in all_runs if r.get("containers_min") is not None]
    loose = [code(r["run"]) for r in pinned if r["containers_min"] != r["replicas"]]
    fleet = (f"Modal {gpu} ({mem['value']} VRAM per the deploy spec quoted below; not a run record), one vLLM replica per container, "
             + ("`min = max` containers pinned for each batch" if not loose else f"containers not pinned on {', '.join(loose)}")
             + f", scaledown {S:.0f} s")
    revs = {r["dataset_rev"] for r in all_runs if r.get("dataset_rev")}
    rev = max(revs, key=len)
    if not all(rev.startswith(v) for v in revs):
        raise SystemExit(f"runs disagree on the dataset revision: {sorted(revs)}")
    data = (f"public HF `{uniform(all_runs, 'dataset', 'the dataset')}` (`{uniform(all_runs, 'dataset_config', 'the dataset config')}`,"
            f" split {uniform(all_runs, 'dataset_split', 'the split')}) @ `{rev}`, seed {uniform(all_runs, 'seed', 'the seed')},"
            f" nested draws ({uniform(all_runs, 'draw_nesting', 'the draw nesting')})")
    spec = (f"The GPU memory is the one setup value no run records; it is quoted from the sandbox deploy spec "
            f"{src_link(mem)}: `{mem['quote'].replace('`', '')}`.")
    return {"model": model_cell, "posture": posture, "fleet": fleet, "data": data, "vllm": vllm, "gpu": gpu, "spec": spec}


def spend_parts(D):
    F, sp = D["fleet"], D["spend"]
    busy = sum(r["busy_usd"] for r in F.values())
    idle = sum(r["idle_usd"] for r in F.values())
    billed = sum(r["billed_usd"] for r in F.values())
    parts = [("Slots with a request in flight", busy - idle), ("Idle slots inside runs", idle),
             ("Cold boots", billed - busy), ("Aborted sorter run (incident)", sp["incident"]),
             ("Fleet time outside any run", sp["sand032"] - billed - sp["incident"])]
    if parts[-1][1] < 0:
        raise SystemExit("spend ledger below the runs' billed GPU $ — hub check should have caught this")
    return parts, busy, idle, billed


def api_tokens(D, X):
    """Hosted-API legs that logged token counts, per task (eval-environment): the n = 20 legs of every model, plus
    the Qwen3.7-Flash n = 50 legs."""
    out = {}
    for task, models in D["api"]["tasks"].items():
        rows = [r for r in [*models.values(), D["api"]["route50"].get(task, {})]
                if r.get("prompt_tokens") and r.get("completion_tokens")]
        out[task] = [{"name": X.api_name(r), "n": r["n"], "run": r["run"], "usd_mtok": r["cost"] / (r["prompt_tokens"] + r["completion_tokens"]) * 1e6,
                      "usd_mout": r["cost"] / r["completion_tokens"] * 1e6,
                      "out_share": r["completion_tokens"] / (r["prompt_tokens"] + r["completion_tokens"])} for r in rows]
    return out


# Warm/cold analytics: one representative configuration per workload class.
CLASS_OF_DIR = {"correspondence": "correspondence", "insurance": "insurance claims", "corporate": "corporate records",
                "contract": "contracts", "merger": "merger agreements", "serving": "sorter"}
# Runs that are not a production configuration: the pre-L5 ladder rungs, the bf16 quality arm, and the S7
# routing A/B (max_inputs 64 sent most requests to one replica).
NOT_A_CONFIG = {"sand032-l0-baseline", "sand032-l1-nothink", "sand032-l2-marlin", "sand032-s4-corr20-bf16",
                "sand032-s7-corr100-seqs32", "sand032-s7-insurance50-seqs32"}
UTIL_LEVELS = (1.0, 0.75, 0.5, 0.25, 0.1)
GAPS_MIN = (1, 2, 5, 10, 30, 60)
PREMIUMS = (0.5, 0.25, 0.1)


def workload(r):
    return next(CLASS_OF_DIR[part] for part in r["report"].split("/") if part in CLASS_OF_DIR)


def best_by_class(F) -> dict:
    """Lowest busy-window $/1M-token configuration measured for each workload class."""
    best = {}
    for r in F.values():
        if r["run"] in NOT_A_CONFIG:
            continue
        c = workload(r)
        if c not in best or per_mtok(r) < per_mtok(best[c]):
            best[c] = r
    order = list(CLASS_OF_DIR.values())
    return dict(sorted(best.items(), key=lambda kv: order.index(kv[0])))


def cheapest_api(D, X, api) -> dict:
    """Cheapest hosted $/1M tokens per workload: the n = 20 task legs, and the n = 100 sorter runs."""
    out = {task: min(rows, key=lambda a: a["usd_mtok"]) for task, rows in api.items() if rows}
    sorters = [r for r in D["api"]["classification"] if r["n"] >= 100 and r.get("prompt_tokens")]
    if sorters:
        s = min(sorters, key=lambda r: r["cost"] / (r["prompt_tokens"] + r["completion_tokens"]))
        out["sorter"] = {"name": X.SORTER_NAME.get(s["model"], s["model"]), "n": s["n"], "run": s["run"],
                         "usd_mtok": s["cost"] / (s["prompt_tokens"] + s["completion_tokens"]) * 1e6}
    return out


# ------------------------------------------------------------------ figures
def fig_util_cost(best, cheap, coeff, X):
    panels = []
    for c, r in best.items():
        ref = [(round(cheap[c]["usd_mtok"], 4), f"cheapest API {cheap[c]['usd_mtok']:.3f}")] if c in cheap else None
        panels.append(X.viz.hbar(f"{c.capitalize()} · {code(r['run'])}",
                                 f"warm fleet $ per 1M tokens by GPU utilization · {tps_l4(r):,.0f} tok/s per L4 at 100%",
                                 [{"label": f"{u * 100:.0f}% busy", "value": round(coeff / (tps_l4(r) * u), 4),
                                   "emphasis": c not in cheap or coeff / (tps_l4(r) * u) <= cheap[c]["usd_mtok"],
                                   "note": fleet_name(r)} for u in UTIL_LEVELS],
                                 fmt=lambda v: f"${v:.3f}", refs=ref, width=560, label_w=120))
    return X.viz.small_multiples("Warm-fleet cost per 1M tokens as utilization falls "
                                 "(blue = still at or below the cheapest API; each panel has its own scale)", panels, cols=2)


def fig_warm_cold(rows, S, X):
    return X.viz.dumbbell("Cost per 1M tokens: warm fleet vs one cold batch",
                          f"same measured batch · cold adds boot + the {S:.0f} s scale-down tail on every replica",
                          rows, ("warm fleet", "one cold batch"), fmt=lambda v: f"${v:.3f}", label_w=200,
                          val=lambda r: f"${r['a']:.3f} → ${r['b']:.3f} ({r['b'] / r['a']:.1f}×)")


def fig_keep_warm(rows, X):
    return X.viz.dumbbell("Idle gap between batches on 2×L4: stay warm or scale to zero",
                          "GPU $ for the gap · scale to zero pays the scale-down tail, then a cold boot",
                          rows, ("stay warm", "scale to zero"), fmt=lambda v: f"${v:.3f}", label_w=140,
                          val=lambda r: f"warm ${r['a']:.3f} · scale-to-zero ${r['b']:.3f}")


def fig_spend(parts, ledger, X):
    return X.viz.hbar("Where the SAND-032 GPU spend went",
                      f"fleet-window ledger ${ledger:.2f} at close · the five parts sum to the ledger",
                      [{"label": lab, "value": round(v, 4), "emphasis": i == 0,
                        "note": f"{v / ledger * 100:.0f}% of the ledger"} for i, (lab, v) in enumerate(parts)],
                      fmt=lambda v: f"${v:.2f}", label_w=230)


def fig_cost_mtok(groups, X):
    top = max(per_mtok(r) for _, _, rows in groups for _, r in rows)
    panels = [X.viz.hbar(title, "busy-window GPU $ per 1M tokens (prompt + completion) · lower is better",
                         [{"label": lab, "value": round(per_mtok(r), 4), "emphasis": r["replicas"] == 2,
                           "note": f"{tps_l4(r):,.0f} tok/s per L4 · ${per_mout(r):.2f} per 1M output tokens"}
                          for lab, r in rows], fmt=lambda v: f"${v:.3f}", width=560, label_w=200, domain_max=top)
              for _, title, rows in groups]
    return X.viz.small_multiples("Modal L4 cost per 1M tokens, every SAND-032 run (emphasis = 2×L4; one scale)", panels, cols=2)


def fig_occupancy(groups, X):
    panels = [X.viz.hbar(title, "client-slot occupancy = Σ request latency ÷ (concurrency × wall) · higher is better",
                         [{"label": lab, "value": round(r["slot"], 4), "emphasis": r["replicas"] == 2,
                           "note": f"{X.usd(r['idle_usd'])} of {X.usd(r['busy_usd'])} busy-window GPU $ spent on idle slots"}
                          for lab, r in rows], fmt=lambda v: f"{v * 100:.0f}%", domain_max=1.0,
                         width=560, label_w=200)
              for _, title, rows in groups]
    return X.viz.small_multiples("How full the fleet was: client-slot occupancy per run (emphasis = 2×L4)", panels, cols=2)


def fig_second_l4(scale, X):
    n = uniform([r for _, r in scale], "n", "scale-out documents")
    def panel(title, sub, val, fmt):
        return X.viz.hbar(title, sub, [{"label": lab, "value": round(val(r), 6),
                                        "emphasis": r["replicas"] == 2 and (busier_share(r) or 0) < 0.75,
                                        "note": fleet_name(r)} for lab, r in scale], fmt=fmt, width=560, label_w=250)
    return X.viz.small_multiples(f"Adding the second L4 · correspondence n = {n}, same documents (grey = one L4 or one replica doing the work)", [
        panel("Wall time", "seconds for the batch · lower is better", lambda r: r["wall"], lambda v: f"{v:.1f} s"),
        panel("Throughput per L4", "tokens per second per GPU · higher is better", tps_l4, lambda v: f"{v:,.0f}"),
        panel("Cost per 1M tokens", "busy-window GPU $ · lower is better", per_mtok, lambda v: f"${v:.3f}"),
        panel("p95 request latency", "seconds · lower is better", lambda r: r["p95"], lambda v: f"{v:.1f} s"),
    ], cols=2)


def fig_split(two, X):
    return X.viz.hbar("Load balance across the two L4 replicas",
                      "share of the run's requests on the busier replica (vLLM /metrics) · 50% = even · lower is better",
                      [{"label": lab, "value": round(busier_share(r), 4), "emphasis": busier_share(r) < 0.75,
                        "note": " / ".join(str(s["requests"]) for s in r["replica_split"]) + f" requests · {fleet_name(r)}"}
                       for lab, r in two], fmt=lambda v: f"{v * 100:.0f}%", refs=[(0.5, "even split")], label_w=250)


def fig_api(D, X, api):
    top = max([per_mtok(D["fleet"][rid]) for rid in SWEEP_BY_TASK.values()]
              + [a["usd_mtok"] for rows in api.values() for a in rows])
    panels = []
    for task, rid in SWEEP_BY_TASK.items():
        r = D["fleet"][rid]
        rows = [{"label": f"Modal · {r['model'].split('/')[-1]} ({r['replicas']}×L4 c{r['conc']})", "value": round(per_mtok(r), 4),
                 "series": X.viz.entity(r["model"]), "note": f"n = {r['ok']} · {rid}"}]
        rows += [{"label": f"API · {a['name'].split(' · ')[0]}" + (" (frozen prompts)" if "filed as" in a["name"] else "")
                  + f" · n = {a['n']}", "value": round(a["usd_mtok"], 4), "series": X.viz.entity(a["name"].split(" · ")[0]),
                  "note": f"{a['name']} · n = {a['n']} · {a['run']}"} for a in sorted(api.get(task, []), key=lambda a: a["usd_mtok"])]
        rows.sort(key=lambda x: x["value"])
        panels.append(X.viz.hbar(task.capitalize(), "$ per 1M tokens (prompt + completion) · lower is better",
                                 rows, fmt=lambda v: f"${v:.3f}", width=560, label_w=250, domain_max=top,
                                 legend=X.entity_legend(x["label"] for x in rows)))
    return X.viz.small_multiples("Cost per 1M tokens on the same tasks: Modal L4 (busy-window) vs hosted API · one scale", panels, cols=2)


# ------------------------------------------------------------------ report
def report(D, X, shas) -> tuple[str, dict[str, str], dict]:
    """Build the GPU spend report body, figures, and supporting tables."""
    F, sp, rate = D["fleet"], D["spend"], D["l4_usd_per_hour"]
    groups = labelled(F)
    by = {k: rows for k, _, rows in groups}
    parts, busy, idle, billed = spend_parts(D)
    api = api_tokens(D, X)
    early = early_2x(X, rate)
    usd, pct, table = X.usd, X.pct, X.table

    def d2(v):
        return f"${v:,.2f}"
    all_runs = list(F.values())
    tokens = sum(tok(r) for r in all_runs)
    docs = sum(r["ok"] for r in all_runs)
    cheapest = min(all_runs, key=per_mtok)
    dearest = max(all_runs, key=per_mtok)
    coeff = 1e6 * rate / 3600

    a, b = F["sand032-s2a-corr100-1rep"], F["sand032-s2b-corr100-2rep"]
    s7, s9 = F["sand032-s7-corr100-seqs32"], F["sand032-s9-corr100-bal"]
    one_l4 = [r for r in all_runs if r["replicas"] == 1]
    two = [(lab, r) for _, _, rows in groups for lab, r in rows if r["replicas"] == 2 and r["replica_split"]]
    sweep = [r for _, r in by["sweep"]]
    c64 = [r for _, r in by["c64"]] + [s7, s9]
    boots = [r["cold_boot"] for r in all_runs if r["cold_boot"] >= COLD_BOOT_MIN_S]  # cold fleets (classification rule)
    warm_probe = max(r["cold_boot"] for r in all_runs if r["cold_boot"] < COLD_BOOT_MIN_S)
    lad_boot = {r["rung"]: r["boot"] for r in D["ladder"]}
    boot_usd = billed - busy
    preempt = sum(s["preempt"] for r in all_runs for s in r["replica_split"])
    prefix = [s["prefix"] for r in all_runs for s in r["replica_split"]]
    l0, l5 = F["sand032-l0-baseline"], F["sand032-l5-graphs"]
    s2_boot_2x = lad_boot["l5-graphs"] * 2 * rate / 3600  # the L5 posture's deploy→ready boot on both L4s
    largest = max(sp["legacy"], key=lambda x: x["v"])
    ins_gain = tps_l4(F["sand032-s9-insurance50-bal"]) / tps_l4(F["sand032-s3-insurance50"]) - 1

    # Modal vs API per token, per task
    api_rows, beat, lose = [], [], []
    for task, rid in SWEEP_BY_TASK.items():
        r = F[rid]
        hosted = sorted(api.get(task, []), key=lambda x: x["usd_mtok"])
        if not hosted:
            continue
        cheap = hosted[0]
        (beat if per_mtok(r) < cheap["usd_mtok"] else lose).append(task)
        api_rows.append([task.capitalize(), f"${per_mtok(r):.3f}", f"{r['completion_tokens'] / tok(r) * 100:.0f}%",
                         f"{cheap['name']} ${cheap['usd_mtok']:.3f}", f"{cheap['out_share'] * 100:.0f}%",
                         " · ".join(f"{x['name']} ${x['usd_mtok']:.3f}" for x in hosted[1:]) or "—",
                         f"{cheap['usd_mtok'] / per_mtok(r):.1f}×"])
    qwen_api = [x["usd_mtok"] for t in api.values() for x in t if x["name"] == "Qwen3-8B"]
    load = sp["sand032"] / busy  # ledger ÷ busy-window GPU $: what boot, idle and warm time added on this program
    beat_loaded = [task for task, rid in SWEEP_BY_TASK.items() if api.get(task)
                   and per_mtok(F[rid]) * load < min(x["usd_mtok"] for x in api[task])]

    # ---- warm vs cold, and cost per token at real utilization
    B5 = lad_boot["l5-graphs"]  # L5 posture deploy→ready, the boot a cold fleet pays today
    S = next(r["scaledown"] for r in all_runs if r.get("scaledown"))
    if {r["scaledown"] for r in all_runs if r.get("scaledown")} != {S}:
        raise SystemExit("runs disagree on the Modal scale-down window")
    best = best_by_class(F)
    cheap = cheapest_api(D, X, api)
    setup = setup_rows(D, all_runs, S)

    # ---- configuration figures quoted in prose, read from the fleet data
    sweep_fleet = f"{uniform(sweep, 'replicas', 'sweep replicas')}×L4 c{uniform(sweep, 'conc', 'sweep concurrency')}"
    one_conc = uniform(one_l4, "conc", "single-L4 concurrency")
    sweep_conc = uniform(sweep, "conc", "sweep concurrency")
    per_rep = [x["conc"] / x["replicas"] for x in (a, b)]
    kv = sorted({s["kv_scrape"] for r in all_runs for s in r["replica_split"] if s.get("kv_scrape") is not None})
    kv_idle = pct(kv[0], 0) if len(kv) == 1 else f"{pct(kv[0], 0)}–{pct(kv[-1], 0)}"
    c64_conc = "/".join(f"c{c}" for c in sorted({r["conc"] for r in c64}))
    c64_seqs = "/".join(str(s) for s in sorted({r["seqs"] for r in c64}))
    contracts = [r for r in all_runs if workload(r) == "contracts" and r["replica_split"]]
    kv_top = max(contracts, key=lambda r: r["seqs"])
    api_n = "/".join(str(n) for n in sorted({x["n"] for rows in api.values() for x in rows}))
    started = {datetime.datetime.fromtimestamp(s["started"], datetime.timezone.utc).date()
               for r in all_runs for s in r["replica_split"] if s.get("started")}
    stages69 = prov(D, "fleet.summary.stages69_date")
    fleet_days = day_span(started | {datetime.date.fromisoformat(stages69["value"])})
    saturation = prov(D, "fleet.summary.saturation")
    e_commit = uniform(early, "commit", "the pre-SAND-032 run commit")
    e_conc, e_rep = uniform(early, "conc", "pre-SAND-032 concurrency"), uniform(early, "replicas", "pre-SAND-032 replicas")
    e_seqs, e_per = uniform(early, "seqs", "pre-SAND-032 max_num_seqs"), uniform(early, "per_replica", "pre-SAND-032 admission")
    e_eager = uniform(early, "eager", "pre-SAND-032 enforce_eager")

    def hdr(r, mi=False):
        return f"{r['replicas']}×L4 · c{r['conc']}" + (f", max_inputs {r['max_inputs']}" if mi else "")

    def boot_of(r):
        return (r["cold_boot"], "measured") if r["cold_boot"] >= COLD_BOOT_MIN_S else (B5, "L5 boot")

    def cold_usd(r):
        return r["busy_usd"] + (boot_of(r)[0] + S) * r["replicas"] * rate / 3600

    def per_doc(r):
        return r["busy_usd"] / r["ok"]

    cycle = {n: (S + B5) * n * rate / 3600 for n in (1, 2)}  # one scale-down tail + one cold boot, per fleet size
    g_star = S + B5
    base_rows, util_rows2, wc_rows, amort_rows, wc_fig, u_star = [], [], [], [], [], {}
    for c, r in best.items():
        lab = f"{code(r['run'])} · {fleet_name(r)}"
        api_c = cheap.get(c)
        cold_mtok = cold_usd(r) / tok(r) * 1e6
        base_rows.append([c.capitalize(), lab, f"${per_mtok(r):.3f}", f"${cold_mtok:.3f}", f"${per_mtok(r) * load:.3f}",
                          f"{api_c['name']} ${api_c['usd_mtok']:.3f}" if api_c else "—"])
        us = [coeff / (tps_l4(r) * u) for u in UTIL_LEVELS]
        u_star[c] = per_mtok(r) / api_c["usd_mtok"] if api_c else None
        util_rows2.append([c.capitalize(), code(r["run"]), f"{tps_l4(r):,.0f}"] + [f"${v:.3f}" for v in us]
                          + [f"${api_c['usd_mtok']:.3f}" if api_c else "—",
                             ("never (API cheaper at 100%)" if u_star[c] > 1 else f"{u_star[c] * 100:.0f}%") if api_c else "—"])
        bs, src = boot_of(r)
        wc_rows.append([c.capitalize(), lab, f"{r['ok']}", f"{r['wall']:.0f} s", f"{bs:.0f} s ({src})",
                        usd(per_doc(r)), usd(cold_usd(r) / r["ok"]), f"${per_mtok(r):.3f}", f"${cold_mtok:.3f}",
                        f"{cold_usd(r) / r['busy_usd']:.1f}×"])
        wc_fig.append({"label": f"{c.capitalize()} ({code(r['run'])})", "a": round(per_mtok(r), 4), "b": round(cold_mtok, 4)})
        amort_rows.append([c.capitalize(), usd(per_doc(r))]
                          + [f"{math.ceil(cycle[n] / (p * per_doc(r))):,}" for n in (1, 2) for p in PREMIUMS])
    gap_rows, gap_fig = [], []
    for g in GAPS_MIN:
        gs = g * 60
        warm = gs * 2 * rate / 3600
        stz = (gs if gs <= S else S + B5) * 2 * rate / 3600
        gap_rows.append([f"{g} min", usd(warm), usd(stz), "stay warm" if warm <= stz else "scale to zero",
                         "none" if gs <= S else f"+{B5:.0f} s cold boot"])
        gap_fig.append({"label": f"{g} min gap", "a": round(warm, 4), "b": round(stz, 4)})
    out_cycles = parts[-1][1] / cycle[2]
    never = [c for c, u in u_star.items() if u is not None and u > 1]
    wins = {c: u for c, u in u_star.items() if u is not None and u <= 1}

    figs = {
        "figures/gpu/gpu-spend.svg": fig_spend(parts, sp["sand032"], X),
        "figures/gpu/cost-per-mtok.svg": fig_cost_mtok(groups, X),
        "figures/gpu/slot-occupancy.svg": fig_occupancy(groups, X),
        "figures/gpu/second-l4.svg": fig_second_l4(by["scale"], X),
        "figures/gpu/replica-split.svg": fig_split(two, X),
        "figures/gpu/modal-vs-api-per-token.svg": fig_api(D, X, api),
        "figures/gpu/utilization-cost-per-mtok.svg": fig_util_cost(best, cheap, coeff, X),
        "figures/gpu/warm-vs-cold.svg": fig_warm_cold(wc_fig, S, X),
        "figures/gpu/keep-warm-vs-scale-to-zero.svg": fig_keep_warm(gap_fig, X),
    }

    run_rows = []
    for _, title, rows in groups:
        for lab, r in rows:
            run_rows.append([f"{lab}", fleet_name(r), f"{r['ok']}/{r['n']}", f"{tok(r):,}",
                             f"{r['completion_tokens'] / tok(r) * 100:.0f}%", f"{tps_l4(r):,.0f}", usd(r["busy_usd"]),
                             f"${per_mtok(r):.3f}", f"${per_mout(r):.2f}", usd(r["busy_usd"] / r["ok"])])
    util_rows = []
    for _, title, rows in groups:
        for lab, r in rows:
            split = r["replica_split"]
            util_rows.append([lab, fleet_name(r), pct(r["slot"], 0), f"{r['lat_sum'] / r['wall']:.1f}× of {r['conc']}",
                              f"{tps_l4(r):,.0f}", pct(r["idle_usd"] / r["busy_usd"], 0),
                              f"{r['cold_boot']:.0f} s" if r["cold_boot"] >= COLD_BOOT_MIN_S else "warm",
                              " / ".join(f"{s['prefix'] * 100:.0f}%" for s in split) or "—",
                              " / ".join(f"{s['ttft']:.1f}" for s in split) or "—"])
    split_rows = [[lab, fleet_name(r), " / ".join(str(s["requests"]) for s in r["replica_split"]), pct(busier_share(r), 0),
                   " / ".join(f"{s['ttft']:.1f} s" for s in r["replica_split"]),
                   " / ".join(f"{s['prefix'] * 100:.0f}%" for s in r["replica_split"]), f"{tps_l4(r):,.0f}"] for lab, r in two]
    spend_rows = [[lab, d2(v), pct(v / sp["sand032"], 0)] for lab, v in parts]
    legacy_rows = [[x["b"], usd(x["v"]), x["d"]] for x in sp["legacy"]]
    modal_legacy = sum(x["v"] for x in sp["legacy"] if not x["b"].startswith("API"))
    group_rows = []
    for key, title, rows in groups:
        rs = [r for _, r in rows]
        group_rows.append([title, str(len(rs)), f"{sum(r['ok'] for r in rs):,}", f"{sum(tok(r) for r in rs):,}",
                           usd(sum(r["busy_usd"] for r in rs)), usd(sum(r["billed_usd"] - r["busy_usd"] for r in rs)),
                           usd(sum(r["billed_usd"] for r in rs))])

    def ab(name, f):
        return [name, f(a), f(b), f(s7), f(s9)]
    ab_rows = [
        ab("Fleet", fleet_name),
        ab("Wall time", lambda r: f"{r['wall']:.1f} s"),
        ab("Throughput", lambda r: f"{r['tps']:,.0f} tok/s"),
        ab("Throughput per L4", lambda r: f"{tps_l4(r):,.0f} tok/s"),
        ab("Busy-window GPU $", lambda r: usd(r["busy_usd"])),
        ab("$ per 1M tokens", lambda r: f"${per_mtok(r):.4f}"),
        ab("$ per document", lambda r: usd(r["busy_usd"] / r["ok"])),
        ab("p50 / p95 latency", lambda r: f"{r['p50']:.1f} / {r['p95']:.1f} s"),
        ab("Client-slot occupancy", lambda r: pct(r["slot"], 0)),
        ab("Requests per replica", lambda r: " / ".join(str(s["requests"]) for s in r["replica_split"])),
        ab("Mean TTFT per replica", lambda r: " / ".join(f"{s['ttft']:.2f} s" for s in r["replica_split"])),
        ab("Prefix-cache hit per replica", lambda r: " / ".join(f"{s['prefix'] * 100:.1f}%" for s in r["replica_split"])),
    ]
    ins3, ins7, ins9 = F["sand032-s3-insurance50"], F["sand032-s7-insurance50-seqs32"], F["sand032-s9-insurance50-bal"]
    adm_rows = [[lab, fleet_name(r), f"{r['wall']:.1f} s", f"{tps_l4(r):,.0f}", f"${per_mtok(r):.3f}",
                 " / ".join(str(s["requests"]) for s in r["replica_split"]), f"{r['p50']:.1f} / {r['p95']:.1f} s"]
                for lab, r in [(f"Correspondence n = {x['n']}", x) for x in (b, s7, s9)]
                + [(f"Insurance n = {x['n']}", x) for x in (ins3, ins7, ins9)]]
    early_rows = [[e["run"], f"{e['replicas']}×L4 · c{e['conc']} · seqs {e['seqs']}", f"{e['n']}", f"{e['tps'] / e['replicas']:,.0f}",
                   pct(e["slot"], 0), f"${e['busy_usd'] / (e['prompt_tokens'] + e['completion_tokens']) * 1e6:.3f}"]
                  for e in early]

    sweep_slot = [r["slot"] for r in sweep]
    one_slot = [r["slot"] for r in one_l4]
    long_docs = [lab for lab, r in by["sweep"] if r["slot"] < 0.6]
    # one entry per class: "merger agreements" and "merger agreements · MAUD prompt" read as one class
    long_names = list(dict.fromkeys(lcfirst(lab.split(" · ", 1)[1]).split(" · ")[0] for lab in long_docs))
    spd = a["wall"] / b["wall"]
    s7_vs_b = per_mtok(s7) / per_mtok(b)
    s9_gain = tps_l4(s9) / tps_l4(b) - 1
    ladder_cut = 1 - per_mtok(l5) / per_mtok(l0)
    occupied = busy - idle

    md = f"""# Modal + vLLM GPU economics — SAND-032

_{cheapest['model'].split('/')[-1]} on vLLM {setup['vllm']}, Modal {setup['gpu']} GPUs at ${rate:.2f}/h each · {len(all_runs)} runs, {docs:,} documents, {tokens:,} tokens · generated by sandbox `reports/dashboard/export_hub_reports.py` from the cross-checked reports hub ({D['text']['n_figures']} source-quoted figures, {D['text']['n_checks']} automated cross-checks) · sources: {shas}_

This report covers what the self-hosted leg cost and how well it used the GPUs. It answers five questions: what a token costs on a Modal L4, where the GPU money went, when a warm fleet beats a cold one, how busy the GPUs were, and what adding a second L4 did. Its companions are [COST-COMPARISON-MODAL-VS-API.md](COST-COMPARISON-MODAL-VS-API.md) (cost per document against the hosted API) and [MASTER-REPORT.md](MASTER-REPORT.md).

## Summary

- **Spend.** SAND-032 used {d2(sp['sand032'])} of its {d2(sp['cap'])} cap (fleet-window ledger at close; it stood at {d2(sp['stage5'])} after stages 1–5). The runs themselves bill at least {d2(billed)}: {d2(busy)} while the batch ran and {d2(boot_usd)} of cold boots. The aborted sorter run cost {d2(sp['incident'])}. The remaining {d2(parts[-1][1])} ({pct(parts[-1][1] / sp['sand032'], 0)}) is fleet time outside any run: warm replicas waiting between runs and deploy windows. Only {d2(occupied)} ({pct(occupied / sp['sand032'], 0)} of the ledger) paid for GPU slots with a request in flight.
- **Cost per token.** A token costs ${per_mtok(cheapest):.3f} to ${per_mtok(dearest):.3f} per million on the busy-window basis. At a fixed L4 price the only variable is throughput per L4: $ per 1M tokens = {coeff:.1f} ÷ (tok/s per L4). The cheapest run is {describe(F, cheapest['run'])}: {pct(cheapest['prompt_tokens'] / tok(cheapest), 0)} of its tokens are input, and it ran at {tps_l4(cheapest):,.0f} tok/s per L4. The dearest is {describe(F, dearest['run'])}, at {tps_l4(dearest):,.0f} tok/s per L4 with long decodes and a long-document tail. Per million *output* tokens the range is ${min(map(per_mout, all_runs)):.2f}–${max(map(per_mout, all_runs)):.2f}.
- **Against the hosted API, per token.** On the same tasks, Modal at {sweep_fleet} is cheaper per token than every hosted model that logged tokens for {X.and_list(beat) or 'no task'}{'' if not lose else ', and dearer for ' + X.and_list(lose)}. Those are busy-window figures. This program's ledger was {load:.1f}× its busy-window GPU $ (boots, idle slots and warm time); {'at that load Modal stays cheaper per token only for ' + X.and_list(beat_loaded) if beat_loaded else 'at that load Modal is not cheaper per token for any task'}. Hosted Qwen3-8B, the same model that Modal serves as a 4-bit AWQ quantization, costs ${min(qwen_api):.3f}–${max(qwen_api):.3f} per 1M tokens.
- **Cost per token at real utilization.** A warm fleet bills by the hour whether or not it has work, so its cost per token is the busy-window figure divided by the share of time the GPUs are busy. Against the cheapest hosted model, a warm L4 fleet stays cheaper only while it is busy more than {X.and_list(f"{u * 100:.0f}% of the time for {c}" for c, u in wins.items()) or "never"}{'' if not never else '; for ' + X.and_list(never) + ' the API is cheaper even at 100% busy'}.
- **Where Modal deployment wins, per document.** §OPTIMAL§ The per-class break-evens are in [the cost comparison's §3](COST-COMPARISON-MODAL-VS-API.md#3-when-does-modal-pay-off-break-even-and-the-optimal-scenario).
- **Warm vs cold.** A cold 2×L4 cycle (the {S:.0f} s scale-down tail plus a {B5:.0f} s L5 boot) costs {usd(cycle[2])}, the same as {g_star / 60:.1f} minutes of a warm 2×L4 fleet. So stay warm when the next batch starts within {g_star / 60:.1f} minutes and scale to zero otherwise. A single cold batch costs {min(cold_usd(r) / r['busy_usd'] for r in best.values()):.1f}–{max(cold_usd(r) / r['busy_usd'] for r in best.values()):.1f}× its warm cost at the batch sizes measured; the boot stops mattering (under {min(PREMIUMS) * 100:.0f}% premium) only past {min(math.ceil(cycle[2] / (min(PREMIUMS) * per_doc(r))) for r in best.values()):,}–{max(math.ceil(cycle[2] / (min(PREMIUMS) * per_doc(r))) for r in best.values()):,} documents per cold 2×L4 batch.
- **Utilization.** GPU compute (SM) utilization was never sampled. The measured proxy is client-slot occupancy, the share of admitted request slots holding a request. It is {pct(min(one_slot), 0)}–{pct(max(one_slot), 0)} on one L4 at c{one_conc}, {pct(min(sweep_slot), 0)}–{pct(max(sweep_slot), 0)} across the {sweep_fleet} sweep, and lowest on {X.and_list(long_names)}, where one slow document holds the batch open while the other slots drain. Idle slots inside runs cost {d2(idle)} ({pct(idle / busy, 0)} of busy-window GPU $). {'vLLM recorded no preemptions on any scraped replica, so KV cache was never the constraint.' if preempt == 0 else f'vLLM recorded {preempt} preemptions across the scraped replicas.'}
- **The second L4.** On the same {a['n']} documents, {hdr(b)} finished in {b['wall']:.1f} s against {a['wall']:.1f} s on {hdr(a)} ({spd:.2f}× faster). Throughput per L4 held ({tps_l4(a):,.0f} → {tps_l4(b):,.0f} tok/s), so cost per token moved from ${per_mtok(a):.4f} to ${per_mtok(b):.4f} and cost per document stayed flat. p95 latency rose from {a['p95']:.1f} s to {b['p95']:.1f} s. The second L4 pays only if Modal's router spreads the load. With `max_inputs` {s7['max_inputs']}, it sent {max(s['requests'] for s in s7['replica_split'])} of {s7['n']} requests to one replica: throughput per L4 fell to {tps_l4(s7):,.0f} tok/s and cost per token rose {s7_vs_b:.1f}×. With `max_inputs` {s9['max_inputs']} at c{s9['conc']} the split was {' / '.join(str(s['requests']) for s in s9['replica_split'])}, and throughput per L4 reached {tps_l4(s9):,.0f} tok/s ({s9_gain * 100:+.0f}% on c{b['conc']}).
- **Boot.** {len(boots)} runs started on a cold fleet; each waited {min(boots):.0f}–{max(boots):.0f} s for the engine to answer its first request. CUDA-graph capture is most of the difference: deploy → ready went from {lad_boot['l1-nothink']:.0f} s at L1 to {lad_boot['l5-graphs']:.0f} s at L5. Boots cost {d2(boot_usd)}, {pct(boot_usd / billed, 0)} of the runs' billed GPU $; one cold 2×L4 start at L5 costs {usd(s2_boot_2x)}.

## 1. Setup and method

| | |
| --- | --- |
| Model / engine | {setup['model']} |
| Frozen serving posture (L5) | {setup['posture']} |
| Fleet | {setup['fleet']} |
| Price | ${rate:.2f} per L4-hour (`docs/RUN-COST-DERIVATION.md` in the sandbox) |
| Data | {setup['data']} |

Every other value in this table is read per run from the SAND-032 run reports' header rows and serving exports (`hub_data.json["fleet"]`) and must agree across the runs that record it. {setup['spec']}

**Definitions.**

- **Busy-window GPU $** = wall time of the batch × replicas × ${rate:.2f}/h. Every $/doc and $/token here uses it, as every SAND-032 run report does.
- **Billed GPU $** = (wall + cold boot) × replicas × ${rate:.2f}/h. It is a lower bound on what Modal bills for the run: warm time before and after the batch is not in it.
- **$ per 1M tokens** = busy-window GPU $ ÷ (prompt + completion tokens) × 10⁶. Because the GPU bills by time, this equals {coeff:.1f} ÷ (tokens per second per L4).
- **Client-slot occupancy** = Σ request latency ÷ (client concurrency × wall). 100% means every admitted slot held a request for the whole batch. The unused share, priced at the busy-window rate, is **idle-slot $**.
- **Effective parallelism** = Σ request latency ÷ wall: how many requests were in flight on average.
- **Per-replica vLLM figures** come from each replica's `/metrics` endpoint. Request counts are deltas over the run; TTFT means and prefix-cache hit rates are cumulative since the replica started.

**Not measured.** No run sampled GPU SM utilization, memory bandwidth or power (no DCGM or `nvidia-smi` sampling), and KV-cache usage was only scraped at idle, where it reads {kv_idle}. Occupancy and throughput per L4 are therefore the utilization evidence. See section 7.

## 2. GPU spend

![Where the SAND-032 GPU spend went](figures/gpu/gpu-spend.svg)

{table(["Part of the ledger", "USD", "Share"], spend_rows, "lrr")}

The five parts sum to the {usd(sp['sand032'])} ledger. The first three come from the runs' serving exports; the incident is the aborted sorter run; the last is the ledger minus everything attributable to a run. The fleet-window ledger itself under-counts Modal billing (the program summary's finding), so treat {usd(sp['sand032'])} as a floor and reconcile it against the Modal usage page.

**By stage.**

{table(["Stage", "Runs", "Docs", "Tokens", "Busy $", "Boot $", "Billed $"], group_rows, "lrrrrrr")}

**Before SAND-032.** Tracked spend from 16–27 Sep totals {usd(sp['legacy_total'])}, of which {usd(modal_legacy)} was Modal GPU time; the largest item was "{largest['b']}" at {usd(largest['v'])}. With SAND-032, tracked Modal GPU spend is at least {usd(modal_legacy + sp['sand032'])}.

{table(["Bucket", "USD", "Detail"], legacy_rows, "lrl")}

## 3. Cost per token

### 3.1 Every run

![Modal L4 cost per 1M tokens, every SAND-032 run](figures/gpu/cost-per-mtok.svg)

{table(["Run", "Fleet", "Docs ok", "Tokens", "Output share", "tok/s per L4", "Busy GPU $", "$ / 1M tokens", "$ / 1M output", "$ / doc"], run_rows, "llrrrrrrrr")}

**What drives it.**

- **Throughput per L4 is the whole story.** Cost per token is {coeff:.1f} ÷ (tok/s per L4), so every lever is a throughput lever. The L0 → L5 ladder raised throughput from {tps_l4(l0):,.0f} to {tps_l4(l5):,.0f} tok/s on the same 20 documents and cut cost per token {pct(ladder_cut, 0)}.
- **Prompt-heavy work is cheap.** Prefill is fast and prefix caching skips shared system prompts, so tasks dominated by input tokens run at high throughput. The LLM sorter ({pct(F['sand032-s6-sorter1000']['prompt_tokens'] / tok(F['sand032-s6-sorter1000']), 0)} input) reaches {tps_l4(F['sand032-s6-sorter1000']):,.0f} tok/s per L4.
- **Long documents are expensive.** Contracts and mergers run at {tps_l4(F['sand032-s3-contracts50']):,.0f} and {tps_l4(F['sand032-s3-merger50']):,.0f} tok/s per L4 at c{sweep_conc}. Long decodes are slow, and the last long document holds both GPUs while the other slots have drained (section 5).
- **The bf16 arm costs more for no quality gain.** Unquantised `Qwen/Qwen3-8B` ran at {tps_l4(F['sand032-s4-corr20-bf16']):,.0f} tok/s per L4, {per_mtok(F['sand032-s4-corr20-bf16']) / per_mtok(F['sand032-l1-nothink']):.1f}× the cost per token of the L1 AWQ rung on the same documents.

### 3.2 Three cost bases per workload

The same measured batch, priced three ways, for the cheapest measured configuration of each workload:

{table(["Workload", "Run and fleet", "Warm fleet (busy window)", "One cold batch", "Program-loaded", "Cheapest API"], base_rows, "llrrrl")}

- **Warm fleet** is the busy-window cost: the fleet was already up and fed.
- **One cold batch** adds the boot (the run's own when it started cold, else the L5 {B5:.0f} s) and the {S:.0f} s scale-down tail on every replica: what a single batch costs if the fleet is started for it and allowed to scale to zero after.
- **Program-loaded** multiplies the warm figure by this program's ledger ÷ busy-window GPU $ ({load:.2f}×): the average overhead SAND-032 actually carried in boots, idle slots and warm time between runs.

### 3.3 Warm-fleet utilization vs cost per token

![Warm-fleet cost per 1M tokens as utilization falls](figures/gpu/utilization-cost-per-mtok.svg)

A warm fleet bills {d2(rate)} per L4-hour busy or not, so at a GPU-busy share u its cost per token is {coeff:.1f} ÷ (tok/s per L4 × u). The last column is the break-even: the busy share below which the cheapest hosted model is cheaper per token.

{table(["Workload", "Run", "tok/s per L4", *[f"{u * 100:.0f}% busy" for u in UTIL_LEVELS], "Cheapest API", "Break-even busy share"], util_rows2, "llr" + "r" * len(UTIL_LEVELS) + "rr")}

These break-evens are per token. Per document, which is what decides deployment, the warm-fleet break-even busy share against the cheapest hosted model is §DOCSHARE§, and Modal is never cheaper for the other classes ([cost comparison §3](COST-COMPARISON-MODAL-VS-API.md#3-when-does-modal-pay-off-break-even-and-the-optimal-scenario)). The two differ because each route spends a different number of tokens on the same document.

Utilization here is the share of the fleet's paid hours spent running batches like the measured one. The measured throughput already includes the idle slots inside each batch (section 5); idle time between batches (section 2) is what moves a real fleet down this table.

### 3.4 Against the hosted API, per token

![Cost per 1M tokens on the same tasks: Modal L4 vs hosted API](figures/gpu/modal-vs-api-per-token.svg)

{table(["Task", "Modal $ / 1M", "Modal output share", "Cheapest API (per 1M)", "API output share", "Other API models", "Cheapest API ÷ Modal"], api_rows, "lrrlrlr")}

Hosted rows are the eval-environment n = {api_n} legs that logged token counts (list price × tokens). Modal rows are busy-window only; scaled by this program's ledger-to-busy ratio ({load:.1f}×), {'Modal stays cheaper per token for ' + X.and_list(beat_loaded) if beat_loaded else 'Modal is not cheaper per token for any task'}. Each leg counts tokens with its own prompts and tokenizer, and the API charges output tokens several times more than input, so the output share matters: Modal's GPU-time price does not care about the mix. The per-document comparison, with the break-even volumes and the optimal deployment, is in [COST-COMPARISON-MODAL-VS-API.md §3](COST-COMPARISON-MODAL-VS-API.md#3-when-does-modal-pay-off-break-even-and-the-optimal-scenario).

## 4. Warm vs cold GPUs

### 4.1 Boot measurements

- **Deploy → engine ready** on the knob ladder: {lad_boot['l1-nothink']:.0f} s at L1, {lad_boot['l2-marlin']:.0f} s at L2 and {lad_boot['l5-graphs']:.0f} s at L5. The L5 changes ({l5['kv_cache_dtype']} KV, `max_num_seqs` {l5['seqs']} and CUDA graphs; the program summary attributes the longer boot to graph capture) add about {lad_boot['l5-graphs'] - lad_boot['l1-nothink']:.0f} s to the boot and buy the L5 throughput (section 3).
- **Cold starts in the program:** {len(boots)} runs started on a cold fleet and waited {min(boots):.0f}–{max(boots):.0f} s for the engine to answer; the rest ran on a fleet already warm from the previous run (at most {warm_probe:.1f} s to first answer). A run counts as cold when its first answer took at least {COLD_BOOT_MIN_S} s (section 8).
- **Scale-down:** every fleet kept its containers {S:.0f} s after the last request before scaling to zero; that tail is billed.

### 4.2 Warm vs cold, per workload

![Cost per 1M tokens: warm fleet vs one cold batch](figures/gpu/warm-vs-cold.svg)

{table(["Workload", "Run and fleet", "Docs", "Batch wall", "Boot", "Warm $/doc", "Cold $/doc", "Warm $/1M", "Cold $/1M", "Cold ÷ warm"], wc_rows, "llrrrrrrrr")}

SAND-032's batches were small: {min(r['ok'] for r in all_runs)}–{max(r['ok'] for r in all_runs)} documents, and {sum(r['wall'] < 60 for r in all_runs)} of {len(all_runs)} runs finished in under a minute. At those sizes a cold start costs more than the batch itself for {X.and_list(c for c, r in best.items() if cold_usd(r) / r['busy_usd'] >= 2) or 'no workload'}; only {X.and_list(c for c, r in best.items() if cold_usd(r) / r['busy_usd'] < 1.5) or 'no workload'} ({X.and_list(f"{r['wall'] / 60:.0f} min" for c, r in best.items() if cold_usd(r) / r['busy_usd'] < 1.5)} of GPU work) absorbs its boot.

### 4.3 Batch size that amortizes a cold start

Documents per cold batch needed to bring the cold premium (scale-down tail + L5 boot) under {X.and_list(f'{p * 100:.0f}%' for p in PREMIUMS)} of the batch's own GPU cost, at each workload's measured busy $/doc (which the second L4 leaves flat, section 6):

{table(["Workload", "Busy $/doc", *[f"{n}×L4 · {p * 100:.0f}%" for n in (1, 2) for p in PREMIUMS]], amort_rows, "lr" + "r" * 2 * len(PREMIUMS))}

A 2×L4 cold start costs twice a 1×L4 one, so it needs twice the batch to amortize.

### 4.4 Keep warm or scale to zero

![Idle gap between batches on 2×L4: stay warm or scale to zero](figures/gpu/keep-warm-vs-scale-to-zero.svg)

Between two batches with an idle gap G, a pinned warm 2×L4 fleet costs G × {d2(2 * rate)}/h. A scale-to-zero fleet pays the gap while the {S:.0f} s scale-down tail runs; past that it pays the tail plus the next cold boot ({B5:.0f} s at L5), and the next batch starts that much later.

{table(["Idle gap", "Stay warm (2×L4)", "Scale to zero (2×L4)", "Cheaper", "Added wait"], gap_rows, "lrrll")}

**Rule:** stay warm while the next batch starts within {g_star:.0f} s ({g_star / 60:.1f} min, the scale-down tail plus one L5 boot); beyond that, scale to zero. One cold 2×L4 cycle costs {usd(cycle[2])}; a warm 2×L4 hour costs {d2(2 * rate * 1)}.

### 4.5 What SAND-032 paid

- **Cold boots:** {d2(boot_usd)} across {len(boots)} cold starts ({pct(boot_usd / billed, 0)} of the runs' billed GPU $).
- **Warm time outside any run:** {d2(parts[-1][1])}, the price of about {out_cycles:.1f} cold 2×L4 cycles, or {parts[-1][1] / (2 * rate) * 60:.0f} minutes of a warm 2×L4 fleet with no work. The run timestamps needed to split it gap by gap were not exported, so whether each gap should have scaled to zero is not measured here.

## 5. GPU utilization

![How full the fleet was: client-slot occupancy per run](figures/gpu/slot-occupancy.svg)

{table(["Run", "Fleet", "Slot occupancy", "Effective parallelism", "tok/s per L4", "Idle-slot share of busy $", "Cold boot", "Prefix-cache hit per replica", "Mean TTFT per replica (s)"], util_rows, "llrrrrrrr")}

**Findings.**

- **One L4 at c{one_conc} stays full.** Occupancy is {pct(min(one_slot), 0)}–{pct(max(one_slot), 0)} on the single-L4 runs: {one_conc} client slots feed one engine, so a straggler idles one slot in {one_conc} rather than most of {sweep_conc}.
- **Wide fleets idle on long tails.** At {sweep_fleet}, occupancy drops to {pct(min(sweep_slot), 0)}–{pct(max(sweep_slot), 0)}. On {X.and_list(long_names)}, one slow document is still decoding after the other slots have emptied, so both GPUs bill while mostly idle. Across all runs idle slots cost {d2(idle)}, {pct(idle / busy, 0)} of busy-window GPU $.
- **Doubling admission lowers occupancy.** At {c64_conc} (`max_num_seqs` {c64_seqs}) occupancy is {pct(min(r['slot'] for r in c64), 0)}–{pct(max(r['slot'] for r in c64), 0)}: requests queue inside vLLM, latency rises, and wall time falls by less than the extra admission.
- **KV cache was never the limit.** {f"vLLM reported no preemptions on any scraped replica, including the contracts runs at up to {kv_top['seqs']} sequences per replica (`max_num_seqs`) with {kv_top['kv_cache_dtype']} KV." if preempt == 0 else f'vLLM reported {preempt} preemptions across the scraped replicas.'} Prefix-cache hit rates were {pct(min(prefix), 0)}–{pct(max(prefix), 0)} per replica.
- **Boot is the other idle.** {len(boots)} runs started on a cold fleet and waited {min(boots):.0f}–{max(boots):.0f} s for the engine. At L5 the boot was {l5['cold_boot']:.0f} s for an {l5['wall']:.0f} s batch: {pct(l5['cold_boot'] / l5['gpu_seconds'], 0)} of that run's billed GPU time.

## 6. Adding the second L4

### 6.1 Same documents, one L4 vs two

![Adding the second L4](figures/gpu/second-l4.svg)

{table(["Metric", hdr(a), hdr(b), hdr(s7, True), hdr(s9, True)], ab_rows, "lrrrr")}

- **Near-linear scale-out.** With per-replica admission {'held at ' + format(per_rep[0], '.0f') if per_rep[0] == per_rep[1] else 'going from ' + format(per_rep[0], '.0f') + ' to ' + format(per_rep[1], '.0f')} (client concurrency ÷ replicas), the second L4 cut wall time {spd:.2f}× and held throughput per L4, so cost per token and per document stayed flat. The extra GPU buys time, not cost.
- **Tail latency got worse.** p95 rose from {a['p95']:.1f} s to {b['p95']:.1f} s while p50 fell from {a['p50']:.1f} s to {b['p50']:.1f} s. The prefix cache is per replica ({' / '.join(f"{s['prefix'] * 100:.1f}%" for s in b['replica_split'])} hit rates, against {a['replica_split'][0]['prefix'] * 100:.1f}% on one L4), so shared prompt prefixes are cached once per replica.
- **Routing decides whether the second L4 works.** Modal's `@web_server` router fills a container up to `max_inputs` before using the next. At `max_inputs` {s7['max_inputs']} and c{s7['conc']}, one replica got {max(s['requests'] for s in s7['replica_split'])} of {s7['n']} requests, its mean TTFT reached {max(s['ttft'] for s in s7['replica_split']):.1f} s, and the batch took {s7['wall']:.1f} s. At `max_inputs` {s9['max_inputs']} the same load split {' / '.join(str(s['requests']) for s in s9['replica_split'])} and took {s9['wall']:.1f} s.

### 6.2 Admission on two L4s

{table(["Task", "Fleet", "Wall", "tok/s per L4", "$ / 1M tokens", "Requests per replica", "p50 / p95"], adm_rows, "llrrrrr")}

Once the router is balanced, doubling admission (c{ins3['conc']} → c{ins9['conc']}, `max_num_seqs` {ins3['seqs']} → {ins9['seqs']}) buys a modest gain and costs median latency: on insurance claims throughput per L4 rose {ins_gain * 100:.0f}% while p50 went from {ins3['p50']:.1f} s to {ins9['p50']:.1f} s. The program summary's reading, not a separate measurement here: “{saturation['value']}” ({src_link(saturation)}).

### 6.3 Load balance on every 2×L4 run

![Load balance across the two L4 replicas](figures/gpu/replica-split.svg)

{table(["Run", "Fleet", "Requests per replica", "Busier replica", "Mean TTFT per replica", "Prefix-cache hit", "tok/s per L4"], split_rows, "llrrrrr")}

Even with `max_inputs` = `max_num_seqs`, short batches split unevenly; the program summary attributes this to Modal's router, not vLLM. The imbalance matters most on long-document classes, where the busier replica's last document sets the wall time.

### 6.4 The first second-L4 attempt (before SAND-032)

{table(["Run", "Fleet", "Docs", "tok/s per L4", "Slot occupancy", "$ / 1M tokens"], early_rows, "llrrrr")}

The pre-SAND-032 correspondence runs (both at sandbox commit `{e_commit}`, per their reports' git rows) added a second L4 without raising admission: c{e_conc} across {e_rep} replicas with `max_num_seqs` {e_seqs} and {'eager mode' if e_eager == 'on' else 'CUDA graphs'} (`enforce_eager={e_eager}`{', no CUDA graphs' if e_eager == 'on' else ''}). Each L4 was offered about {e_per} requests at a time (client concurrency ÷ replicas, as the reports state). Their prompts differ from SAND-032's, so this is not a paired comparison, but throughput per L4 was a small fraction of the {tps_l4(b):,.0f} tok/s SAND-032 later reached on two L4s. The lesson carried into the runbook: raise client concurrency with the replica count.

### 6.5 What the second L4 costs

- **Per batch, nothing extra while it runs.** Busy-window cost scales with wall × replicas, and wall halves.
- **Boot doubles.** Each cold replica boots separately; at the L5 posture's {lad_boot['l5-graphs']:.0f} s, a 2×L4 cold start costs {usd(s2_boot_2x)}, half of it for the second L4.
- **Warm idle doubles.** A pinned 2×L4 fleet costs ${2 * rate:.2f}/h whether or not it has work, which is how {usd(parts[-1][1])} of this program's ledger was spent outside any run.
- **Verdict.** Add the second L4 when wall time matters and the fleet is fed: client concurrency = replicas × `max_num_seqs`, and `max_inputs` = `max_num_seqs`. For a latency-insensitive batch it gains nothing per token, and it doubles boot and idle exposure.

## 7. Recommendations

1. **Keep the frozen L5 posture and the routing rule.** `max_inputs` = `max_num_seqs` per container, client concurrency = replicas × `max_num_seqs`. This is the largest cost lever measured here.
2. **Match fleet width to document length.** Short documents fill two L4s; long contracts and mergers leave them idle behind one straggler. Split long-document classes into their own batch, or cap their decode budget, before adding replicas.
3. **Stay warm only across short gaps.** {pct(parts[-1][1] / sp['sand032'], 0)} of the ledger bought no run. Queue runs back-to-back against one warm fleet; when the next batch starts more than {g_star:.0f} s ({g_star / 60:.1f} min) later, let the fleet scale to zero (section 4.4).
4. **Size cold batches to their boot.** A cold 2×L4 start is worth it only for batches large enough to amortize it: {X.and_list(f"{r_[0].lower()} ≥ {r_[2 + len(PREMIUMS) + PREMIUMS.index(min(PREMIUMS))]}" for r_ in amort_rows)} documents keep the cold premium under {min(PREMIUMS) * 100:.0f}% (section 4.3). Smaller jobs belong on an already-warm fleet or the hosted API.
5. **Cut sorter input, not sorter GPUs.** The LLM sorter is prefill-bound and already the cheapest work per token; head-truncating its input is what moves its cost per document.
6. **Measure real GPU utilization before the next spend.** Sample `nvidia-smi` or DCGM (SM %, memory bandwidth, power) and scrape vLLM KV usage under load. Slot occupancy shows when the fleet is starved; it cannot show how hard a busy GPU is working.
7. **Reconcile the ledger.** Compare {usd(sp['sand032'])} against the Modal usage page for {fleet_days} (UTC: the vLLM replica start times in the run reports, plus the program summary's stage 6–9 date, {stages69['value']}).

## 8. Source notes

- The SAND-032 program summary headed its spend line with the stage 1–5 figure ({usd(sp['stage5'])}) while its closing ledger read {usd(sp['sand032'])}. The runs alone bill {usd(billed)}, so {usd(sp['stage5'])} could not be the program total. The summary is corrected in the sandbox, and the hub now checks the header against the closing ledger and against the runs' billed GPU $.
- The S6 sorter report quotes {usd(F['sand032-s6-sorter1000']['billed_usd'] / F['sand032-s6-sorter1000']['ok'])}/doc on the billed basis (it includes the {F['sand032-s6-sorter1000']['cold_boot']:.0f} s cold boot). This report and the hub use the busy-window figure, {usd(F['sand032-s6-sorter1000']['busy_usd'] / F['sand032-s6-sorter1000']['ok'])}/doc, like every other run.
- The two pre-SAND-032 2×L4 serving exports are on a one-replica basis; their run reports bill both replicas. Section §EARLY§ uses both replicas and checks the report's billed figure against the replica count × the export.
- A run counts as starting on a cold fleet when its first answer took at least {COLD_BOOT_MIN_S} s (`COLD_BOOT_MIN_S`). That cutoff is a classification rule, not a measurement: every SAND-032 export is either under {warm_probe:.1f} s (warm) or at least {min(boots):.0f} s (cold), so any cutoff between the two gives the same split.

## Sources

| Source | What it gives |
| --- | --- |
| `local-mailroom-sandbox/reports/serving/SAND-32/sand032-*.serving.json` | per-run wall, boot, tokens, throughput, latency, slot occupancy, GPU $ |
| `local-mailroom-sandbox/reports/SAND-32/*/SAND032-*-REPORT.md` | engine flags, busy-window GPU $, per-replica vLLM `/metrics` |
| `local-mailroom-sandbox/reports/serving/QWEN3-L4-LADDER-SUMMARY.md` | spend ledger, incident, runbook findings |
| `local-mailroom-sandbox/reports/dashboard/hub_data.json` | the cross-checked extract every number here is read from |
| `eval-environment/reports/api-comparisons/` (via the hub) | hosted-API legs with token counts and cost |

{shas}
"""
    E = X.breakeven.analyze(D, NOT_A_CONFIG)
    o = E["optimal"]
    stats = {"tiles": [
        {"label": "SAND-032 GPU spend", "value": d2(sp["sand032"]),
         "sub": f"of the {d2(sp['cap'])} cap · fleet-window ledger at close"},
        {"label": "Cost per 1M tokens on Modal L4", "value": f"${per_mtok(cheapest):.2f}–{per_mtok(dearest):.2f}",
         "sub": f"busy-window, {len(all_runs)} runs · = {coeff:.1f} ÷ tok/s per L4"},
        {"label": "Speed-up from a second L4", "value": f"{spd:.2f}×",
         "sub": f"same 100 documents · ${per_mtok(a):.3f} → ${per_mtok(b):.3f} per 1M tokens"},
        {"label": "Keep warm or scale to zero", "value": f"{g_star / 60:.1f} min",
         "sub": f"idle gap past which a cold 2×L4 cycle ({usd(cycle[2])}) beats staying warm"},
    ] + ([{"label": "Modal saving per document, best case", "value": pct(o['save_pct'], 0),
           "sub": f"{o['modal']['model']} on {o['modal']['replicas']}×L4, {o['label'].lower()}, vs {o['cheap']['family']} "
                  f"(API) at a higher score · from {o['l4x1']['docs_h_star']:,.0f} docs/h"}] if o else [])}
    md = md.replace("§OPTIMAL§", X.optimal_sentence(E))
    md = md.replace("§DOCSHARE§", X.and_list(f"{pct(r['ratio'], 0)} for {r['label'].lower()}" for r in E["rows"] if r["cheaper"])
                    or "never")
    early_sec = re.search(r"^### ([\d.]+) The first second-L4 attempt", md, re.M)
    if not early_sec:
        raise SystemExit("pre-SAND-032 section heading not found")
    md = md.replace("§EARLY§", early_sec.group(1))
    return md, figs, stats
