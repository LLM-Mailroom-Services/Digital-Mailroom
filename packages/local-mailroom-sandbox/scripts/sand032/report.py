#!/usr/bin/env python3
"""SAND-032 report generator — every number is computed from recorded artifacts.

Per run  → reports/SAND-32/<class-dir>/SAND032-<RUN>-REPORT.md
Ladder   → reports/serving/SAND-32/SAND032-LADDER.md
Usage:
  scripts/sand032/report.py run  <run-id> [<run-id> ...]
  scripts/sand032/report.py ladder
Inputs (all local): config/runs/<run>.yaml, data/runtime/runs/<run>/{spec.lock.json,
dataset.jsonl,items.jsonl,cold_boot.json,vllm_metrics_{before,after}.json},
reports/serving/SAND-32/<run>.serving.json, data/runtime/sand032/{logs/<run>.times,fleets.json}.
Public HF mailroom-dataset only — no partner / proprietary data.
"""
from __future__ import annotations

import json
import math
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import viz  # noqa: E402  (/dataviz chart kit, validated palette)

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "data" / "runtime" / "runs"
RT = ROOT / "data" / "runtime" / "sand032"
SERVING = ROOT / "reports" / "serving" / "SAND-32"
L4_USD_PER_HOUR = 0.80
CLASS_DIR = {
    "correspondence": "correspondence",
    "insurance_claim": "insurance",
    "corporate_record": "corporate",
    "merger_agreement": "merger",
    "contract": "contract",
}
LADDER = ["sand032-l0-baseline", "sand032-l1-nothink", "sand032-l2-marlin",
          "sand032-l3-fp8kv", "sand032-l4-seqs16", "sand032-l5-graphs"]
RUNG_CHANGE = {
    "sand032-l0-baseline": "baseline (current AWQ posture)",
    "sand032-l1-nothink": "+ Qwen3 thinking off",
    "sand032-l2-marlin": "+ awq_marlin kernel",
    "sand032-l3-fp8kv": "+ fp8 KV cache (pinned for 2×L4)",
    "sand032-l4-seqs16": "+ max_num_seqs 16",
    "sand032-l5-graphs": "+ CUDA graphs (eager off)",
}


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _times(rid: str) -> dict[str, float]:
    out = {}
    p = RT / "logs" / f"{rid}.times"
    if p.is_file():
        for line in p.read_text().splitlines():
            k, _, v = line.partition(":")
            try:
                out[k.strip().strip('"')] = float(v.strip().rstrip(","))
            except ValueError:
                pass
    return out


def p95(xs: list[float]) -> float:
    s = sorted(xs)
    return s[max(1, math.ceil(0.95 * len(s))) - 1]


def load(rid: str) -> dict:
    run = RUNS / rid
    spec = yaml.safe_load((ROOT / "config" / "runs" / f"{rid}.yaml").read_text())
    items = {i["item_id"]: i for i in _jsonl(run / "items.jsonl")}
    ds = _jsonl(run / "dataset.jsonl")
    sub = {r["id"]: r.get("expected_subclass") or "?" for r in ds}
    lock = _json(run / "spec.lock.json")
    return {
        "rid": rid, "spec": spec, "items": items, "sub": sub, "lock": lock,
        "serving": _json(SERVING / f"{rid}.serving.json"),
        "before": _json(run / "vllm_metrics_before.json"),
        "after": _json(run / "vllm_metrics_after.json"),
        "cold": _json(run / "cold_boot.json"), "times": _times(rid),
        "dataset_sha": (lock.get("dataset") or {}).get("sha256", ""),
    }


def metrics(d: dict) -> dict:
    items = list(d["items"].values())
    ok = [i for i in items if i.get("ok")]
    sc = [float(i["score"]["overall_extraction_score"]) for i in ok
          if isinstance((i.get("score") or {}).get("overall_extraction_score"), (int, float))]
    lat = [float(i["latency_ms"]) / 1000 for i in ok if i.get("latency_ms") is not None]
    sv = [bool(i["score"].get("schema_valid")) for i in ok if "schema_valid" in (i.get("score") or {})]
    pe = sum(1 for i in ok if (i.get("score") or {}).get("parse_error"))
    s = d["serving"]
    rep = int((d["spec"]["engine"]["modal"]).get("max_containers") or 1)
    wall = s.get("wall_seconds")
    busy_usd = wall / 3600 * L4_USD_PER_HOUR * rep if wall else None
    ptok = sum(int(i.get("prompt_tokens") or 0) for i in ok)
    ctok = sum(int(i.get("completion_tokens") or 0) for i in ok)
    t = d["times"]
    fleet = None
    if "deploy_done" in t and "stopped" in t:
        fleet = t["stopped"] - t.get("deploy_start", t["deploy_done"])
    return {
        "n": len(items), "ok": len(ok), "err": len(items) - len(ok),
        "score": statistics.mean(sc) if sc else None, "score_sd": statistics.pstdev(sc) if len(sc) > 1 else None,
        "score_min": min(sc) if sc else None, "score_max": max(sc) if sc else None,
        "schema_valid": (sum(sv) / len(sv)) if sv else None, "parse_errors": pe,
        "wall": wall, "p50": statistics.median(lat) if lat else None, "p95": p95(lat) if lat else None,
        "lat_max": max(lat) if lat else None, "lat_sum": sum(lat), "ptok": ptok, "ctok": ctok,
        "tps": s.get("tokens_per_second"), "rep": rep, "conc": d["spec"]["job"]["concurrency"],
        "busy_usd": busy_usd, "usd_doc": busy_usd / len(ok) if busy_usd and ok else None,
        "cold": (d["cold"] or {}).get("cold_boot_seconds"),
        "boot_ready_s": (t["ready"] - t["deploy_done"]) if "ready" in t and "deploy_done" in t else None,
        "fleet_s": fleet, "fleet_usd": fleet / 3600 * L4_USD_PER_HOUR * rep if fleet else None,
    }


def _f(x, nd=4, suf=""):
    return "—" if x is None else (f"{x:.{nd}f}{suf}" if isinstance(x, float) else f"{x}{suf}")


def _metrics_block(d: dict) -> list[str]:
    out = []
    a, b = d["after"].get("replicas") or {}, d["before"].get("replicas") or {}
    out.append(f"- `/metrics` coverage after the run: **{d['after'].get('coverage', '—')}** "
               "(sampled through the Modal router; replica = vLLM process start time).")
    for key, r in sorted(a.items()):
        rb = b.get(key, {})
        dreq = (r.get("requests") or 0) - (rb.get("requests") or 0)
        out.append(
            f"- replica `{key}`: requests Δ {dreq:.0f} (cumulative {r.get('requests', 0):.0f}), "
            f"measured TTFT mean {_f(r.get('ttft_mean_seconds'), 3, ' s')} (vLLM histogram, cumulative), "
            f"prefix-cache hit {_f((r.get('prefix_cache_hit_rate') or 0) * 100, 1, '%')}, "
            f"preemptions {_f(r.get('preemptions'), 0)}, length-capped finishes {_f(r.get('length_finishes'), 0)}, "
            f"KV usage at scrape {_f((r.get('kv_cache_usage_perc') or 0) * 100, 1, '%')}.")
    return out


def insights(d: dict, m: dict) -> list[str]:
    ok = [i for i in d["items"].values() if i.get("ok")]
    out = []
    if m["wall"] and m["lat_sum"]:
        sp = m["lat_sum"] / m["wall"]
        out.append(f"- **Concurrency efficiency:** Σ latency {m['lat_sum']:.1f} s over wall {m['wall']:.1f} s = "
                   f"**{sp:.2f}×** effective parallelism at c{m['conc']} "
                   f"({100 * sp / m['conc']:.0f}% of the ideal {m['conc']}×).")
    if ok:
        slow = max(ok, key=lambda i: i.get("latency_ms") or 0)
        share = (slow["latency_ms"] / 1000) / m["wall"] if m["wall"] else None
        out.append(f"- **Tail:** slowest doc `{slow['item_id']}` ({d['sub'].get(slow['item_id'], '?')}) "
                   f"{slow['latency_ms'] / 1000:.1f} s = {_f(share and 100 * share, 0, '%')} of wall — "
                   f"p95/p50 = {_f(m['p95'] / m['p50'] if m['p50'] else None, 2)}×.")
        pts = [(int(i.get("prompt_tokens") or 0), i["latency_ms"] / 1000) for i in ok if i.get("latency_ms")]
        if len(pts) > 2:
            xs, ys = zip(*pts)
            try:
                r = statistics.correlation(xs, ys)
                out.append(f"- **Prompt length vs latency:** Pearson r = {r:.2f} across {len(pts)} docs "
                           f"({'prefill-bound' if r > 0.5 else 'not prefill-dominated'}).")
            except statistics.StatisticsError:
                pass
        out.append(f"- **Decode budget:** mean completion {m['ctok'] / len(ok):.0f} tok/doc, "
                   f"mean prompt {m['ptok'] / len(ok):.0f} tok/doc.")
    by = defaultdict(list)
    for i in ok:
        s = (i.get("score") or {}).get("overall_extraction_score")
        if isinstance(s, (int, float)):
            by[d["sub"].get(i["item_id"], "?")].append(s)
    if len(by) > 1:
        best = max(by, key=lambda k: statistics.mean(by[k]))
        worst = min(by, key=lambda k: statistics.mean(by[k]))
        out.append(f"- **Subclass spread:** best `{best}` {statistics.mean(by[best]):.3f} (n={len(by[best])}), "
                   f"worst `{worst}` {statistics.mean(by[worst]):.3f} (n={len(by[worst])}).")
    zeros = sum(1 for i in ok if (i.get("score") or {}).get("extraction_f1") == 0)
    if ok:
        out.append(f"- **Field-level extraction:** {zeros}/{len(ok)} docs have extraction_f1 = 0 — the overall "
                   "score is carried by entity/structure components, not exact field values.")
    if m["cold"] is not None and m["boot_ready_s"]:
        out.append(f"- **Boot:** deploy→engine-ready {m['boot_ready_s']:.0f} s (driver stamps); "
                   f"preflight probe measured {m['cold']:.1f} s once the engine answered.")
    return out


def figures(d: dict, m: dict, cls: str, by: dict) -> list[str]:
    """/dataviz figures (static SVG, light+dark selected); tables below are their twins."""
    rid = d["rid"]
    fig_dir = ROOT / "reports" / CLASS_DIR[cls] / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    ok = sorted((i for i in d["items"].values() if i.get("ok") and i.get("latency_ms")),
                key=lambda i: -i["latency_ms"])
    lat_rows = [{"label": f"{i['item_id'][-8:]} · {d['sub'].get(i['item_id'], '?')}",
                 "value": round(i["latency_ms"] / 1000, 1),
                 "note": f"{i.get('prompt_tokens')} prompt / {i.get('completion_tokens')} completion tok"}
                for i in ok]
    refs = [(round(m["p50"], 1), f"p50 {m['p50']:.1f}s"), (round(m["p95"], 1), f"p95 {m['p95']:.1f}s")] if m["p50"] else []
    lat_svg = viz.hbar(f"Per-document latency · {rid}",
                       f"{m['ok']} docs, slowest first · c{m['conc']} on {m['rep']}×L4 · wall {m['wall']:.1f}s",
                       lat_rows, unit="s", fmt=lambda v: f"{v:.1f}", refs=refs)
    (fig_dir / f"{rid}-latency.svg").write_text(lat_svg)
    if m["score"] is None:  # merger/contracts: suite scorer emits no overall score
        return ["## Figures", "",
                f"![Per-document latency, slowest first, with p50/p95 reference lines](figures/{rid}-latency.svg)", "",
                "_No overall extraction score for this class (suite scorer returns none), so there is no "
                "score-by-subclass figure. Table view: **Per-document scores** below._", ""]
    sub_rows = [{"label": f"{k} (n={len(v)})", "value": round(statistics.mean(v), 4)}
                for k, v in sorted(by.items(), key=lambda kv: -statistics.mean(kv[1]))]
    sub_svg = viz.hbar(f"Mean overall extraction score by subclass · {rid}",
                       f"overall mean {m['score']:.4f} across {m['ok']} docs (0–1, higher is better)",
                       sub_rows, fmt=lambda v: f"{v:.3f}")
    (fig_dir / f"{rid}-subclass.svg").write_text(sub_svg)
    return ["## Figures", "",
            f"![Per-document latency, slowest first, with p50/p95 reference lines](figures/{rid}-latency.svg)", "",
            f"![Mean overall extraction score by subclass](figures/{rid}-subclass.svg)", "",
            "_Table views of both figures: **Per-document scores** and **Strata** below._", ""]


def scoring_section(d: dict) -> list[str]:
    """Merger/contract rows carry MAUD/CUAD label maps only — say what the headline means."""
    sc = [i["score"] for i in d["items"].values() if i.get("ok") and isinstance(i.get("score"), dict)]
    method = next((x.get("scoring_method") for x in sc if x.get("scoring_method")), "")
    tot = lambda k: sum(int(x.get(k) or 0) for x in sc)  # noqa: E731
    if method.endswith("+maud"):
        q, a, c = tot("maud_questions"), tot("maud_answered"), tot("maud_correct")
        cq, cc = tot("maud_clean_questions"), tot("maud_clean_correct")
        return ["## Scoring method — MAUD answer accuracy", "",
                "The pinned Hub merger rows carry ground truth only as `maud_clause_labels` (LegalBench MAUD "
                "question → answer). The suite field map scores document_name/parties/…, which those rows never "
                "populate, so field F1 is 0 by construction. The headline here is **per-question MAUD accuracy** "
                "(`src/mailroom_sandbox/eval/maud_scoring.py`); an unanswered question counts as wrong.", "",
                "| metric | value |", "| --- | --- |",
                f"| labeled MAUD questions | {q} |",
                f"| answered | {a} ({a / q:.1%} coverage) |" if q else "| answered | — |",
                f"| correct | {c} → **micro accuracy {c / q:.1%}** |" if q else "| correct | — |",
                f"| precision on answered | {c / a:.1%} |" if a else "| precision on answered | — |",
                f"| clean subset (single MAUD sub-question per name) | {cc}/{cq} = {cc / cq:.1%} |" if cq else "| clean subset | — |",
                "",
                "**Dataset caveat:** the corpus collapses several MAUD sub-questions under one name (e.g. `No-Shop` "
                "answers include `Yes`, `Strict liability`, `Reasonable standard`), so a per-doc target on those "
                "names is ambiguous; the clean subset excludes them.", ""]
    if method.endswith("+cuad"):
        tp, fp, fn = tot("cuad_tp"), tot("cuad_fp"), tot("cuad_fn")
        P = tp / (tp + fp) if tp + fp else 0.0
        R = tp / (tp + fn) if tp + fn else 0.0
        F = 2 * P * R / (P + R) if P + R else 0.0
        vc, vk = tot("cuad_value_correct"), tot("cuad_value_checked")
        labeled = sum(1 for x in sc if x.get("cuad_presence_f1") is not None)
        return ["## Scoring method — CUAD clause detection", "",
                "The pinned Hub contract rows carry ground truth only as `cuad_clause_labels` (CUAD category → "
                "annotated spans). The suite field map never meets them, so field F1 was 0 and the overall score "
                "null by construction. The headline here is **per-doc CUAD category-presence F1** within each "
                "row's labeled universe (`src/mailroom_sandbox/eval/cuad_scoring.py`).", "",
                "| metric | value |", "| --- | --- |",
                f"| docs with CUAD labels (scored) | {labeled} of {len(sc)} ok |",
                f"| micro precision / recall / F1 | {P:.3f} / {R:.3f} / **{F:.3f}** |",
                f"| metadata value checks (name, parties, governing law) | {vc}/{vk} = {vc / vk:.1%} |" if vk else "| metadata value checks | — |",
                f"| predicted categories outside the labeled universe (ignored, scored docs) | {sum(int(x.get('cuad_out_of_universe') or 0) for x in sc if x.get('cuad_presence_f1') is not None)} |", ""]
    return []


def sorter_report(rid: str) -> Path:
    """Isolated LLM sorter run: doc-class accuracy, per-class P/R/F1, confusion, serving."""
    d = load(rid)
    exp = {r["id"]: r.get("expected_doc_class") for r in _jsonl(RUNS / rid / "dataset.jsonl")}
    items = list(d["items"].values())
    ok = [i for i in items if i.get("ok")]
    pairs = [(exp[i["item_id"]], (i.get("score") or {}).get("predicted", "")) for i in ok]
    classes = sorted({e for e, _ in pairs})
    acc = sum(e == p for e, p in pairs) / len(pairs) if pairs else 0.0
    rows, f1s, f1_rows = [], [], []
    for c in classes:
        tp = sum(e == c and p == c for e, p in pairs)
        fp = sum(e != c and p == c for e, p in pairs)
        fn = sum(e == c and p != c for e, p in pairs)
        P = tp / (tp + fp) if tp + fp else 0.0
        R = tp / (tp + fn) if tp + fn else 0.0
        F = 2 * P * R / (P + R) if P + R else 0.0
        f1s.append(F)
        f1_rows.append({"label": f"{c} (n={tp + fn})", "value": round(F, 4), "note": f"P {P:.3f} · R {R:.3f}"})
        rows.append(f"| {c} | {tp + fn} | {P:.3f} | {R:.3f} | {F:.3f} |")
    preds = sorted({p for _, p in pairs} | set(classes))
    conf = ["| expected ↓ / predicted → | " + " | ".join(preds) + " |", "| --- |" + " --- |" * len(preds)]
    conf += [f"| {c} | " + " | ".join(str(sum(e == c and p == q for e, p in pairs)) for q in preds) + " |"
             for c in classes]
    s = d["serving"].get("metrics", d["serving"]) if d["serving"] else {}
    lat = sorted(float(i["latency_ms"]) / 1000 for i in ok if i.get("latency_ms"))
    pt = sorted(int(i.get("prompt_tokens") or 0) for i in ok)
    ct = sorted(int(i.get("completion_tokens") or 0) for i in ok)
    med = lambda xs: xs[len(xs) // 2] if xs else None  # noqa: E731
    v, mo = d["spec"]["engine"]["vllm"], d["spec"]["engine"]["modal"]
    lines = [f"# SAND-032 {rid} — isolated LLM sorter (SorterAgent only)", "",
             "Public HF `mailroom-dataset` @ `ed7576b` only (no partner or proprietary data). "
             "`task: isolated` calls `SorterAgent` alone — no reviewer, specialist, or judge prompts.", "",
             "| field | value |", "| --- | --- |",
             f"| engine | `{d['spec']['engine']['model']}`, {mo.get('max_containers')}× L4, "
             f"seqs {v.get('max_num_seqs')}, kv `{v.get('kv_cache_dtype')}`, `{v.get('quantization')}`, "
             f"graphs {v.get('cudagraph_capture_sizes')}, batched tokens {v.get('max_num_batched_tokens') or 'default'} |",
             f"| concurrency | {d['spec']['job']['concurrency']} |",
             f"| docs ok / total | {len(ok)} / {len(items)} |",
             f"| **accuracy** | **{acc:.4f}** |",
             f"| **macro-F1** | **{(sum(f1s) / len(f1s) if f1s else 0):.4f}** |",
             f"| wall s | {_f(s.get('wall_seconds'), 1)} |",
             f"| tok/s | {_f(s.get('tokens_per_second'), 0)} |",
             f"| GPU $/doc | {_f(s.get('gpu_cost_per_document'), 6)} |",
             f"| latency p50 / p95 s | {_f(med(lat), 1)} / {_f(p95(lat) if lat else None, 1)} |",
             f"| prompt tokens p50 / max | {med(pt)} / {pt[-1] if pt else None} |",
             f"| completion tokens p50 / max | {med(ct)} / {ct[-1] if ct else None} |", "",
             "## Figures", "",
             f"![Per-class F1 for the isolated sorter](figures/{rid}-per-class-f1.svg)", "",
             "_Table view: **Per-class** below._", "",
             "## Per-class", "", "| class | n | precision | recall | F1 |", "| --- | --- | --- | --- | --- |", *rows, "",
             "## Confusion matrix", "", *conf, "",
             "## Findings", "",
             "- The vendored sorter reads whole documents: a ~5.4k-token base prompt plus chunked long docs "
             "(prompt tokens scale with document length). This run is prefill-bound; a head-truncated sorter "
             "input is the main cost lever for the runbook.",
             "- Items recorded before the storage fix carry `SorterAgent.classify`'s tuple as a string; scores "
             "here come from `scripts/sand032/rescore.py` (post hoc, no LLM calls).", ""]
    fig_dir = ROOT / "reports" / "serving" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    (fig_dir / f"{rid}-per-class-f1.svg").write_text(viz.hbar(
        f"Per-class F1 · {rid}", f"isolated sorter · {len(ok)} docs · accuracy {acc:.3f} (0–1, higher is better)",
        sorted(f1_rows, key=lambda r: -r["value"]), fmt=lambda v: f"{v:.3f}", label_w=230))
    out = ROOT / "reports" / "serving" / f"SAND032-{rid.removeprefix('sand032-').upper()}-REPORT.md"
    out.write_text("\n".join(lines))
    return out


def run_report(rid: str) -> Path:
    if "sorter" in rid:
        return sorter_report(rid)
    d = load(rid)
    m = metrics(d)
    spec = d["spec"]
    v, mo = spec["engine"]["vllm"], spec["engine"]["modal"]
    cls = spec["dataset"]["strata"]["buckets"][0]["doc_class"]
    agent = spec["task"]
    prompt = next(iter(spec["prompt"]["agents"].values()))["file"]
    # provenance = the commit the RUN used (spec lock), not whatever HEAD is when the report is rebuilt
    run_git = (d["lock"].get("git") or {}) if isinstance(d.get("lock"), dict) else {}
    git = run_git.get("commit") or subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if run_git.get("dirty"):
        git += " (dirty)"
    lines = [
        f"# Run report — `{rid}`",
        "",
        f"SAND-032 Modal × vLLM specialist extract: **{m['n']} {cls} docs** on **{spec['engine']['model']}** at "
        f"**concurrency {m['conc']}** on **{m['rep']}×L4** (MIN=MAX={m['rep']} pinned, dedicated app "
        f"`{mo['app']}`). Public HF `mailroom-dataset` only.",
        "",
        "| | |", "| --- | --- |",
        f"| run_id | `{rid}` |",
        f"| task / agent | `{agent}` |",
        f"| prompt | `{prompt}` (local pin) |",
        f"| engine | `{spec['engine']['model']}`, vLLM `{mo['image_tag']}`, {m['rep']}× L4 "
        f"({'data-parallel replicas' if m['rep'] > 1 else 'single replica'}) |",
        f"| context / quant | `max_model_len={v['max_model_len']}`, quant=`{v['quantization'] or 'bf16'}`, "
        f"gpu_util={v['gpu_memory_utilization']}, max_num_seqs={v['max_num_seqs']} |",
        f"| engine flags | prefix_caching=on, enforce_eager={'on' if v['enforce_eager'] else 'off'}, "
        f"kv_cache_dtype=`{v.get('kv_cache_dtype') or 'auto'}`, thinking="
        f"{'default' if v.get('enable_thinking') is None else ('on' if v['enable_thinking'] else 'off')}, "
        f"cudagraph sizes={v.get('cudagraph_capture_sizes') or '—'}, max_inputs={v.get('max_inputs')} |",
        f"| modal | `{mo['app']}`, max/min containers {mo['max_containers']}/{mo['min_containers']}, "
        f"scaledown {mo['scaledown_seconds']} s, profile `exios66` |",
        f"| dataset | mailroom-dataset `ground_truth`, split={spec['dataset']['split']}, "
        f"rev `{spec['dataset']['revision'][:8]}`, seed {spec['dataset']['sample_seed']} |",
        f"| draw | {m['n']} docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `{d['dataset_sha'][:12]}` |",
        f"| git | `{git}` |",
        f"| spec_hash | `{(d['lock'].get('spec_hash') or '')}` |",
        "",
        "## Headline results", "",
        "| metric | value |", "| --- | --- |",
        f"| docs ok / total | **{m['ok']} / {m['n']}** (errors {m['err']}) |",
        f"| **overall_extraction_score** | **{_f(m['score'])}** (sd {_f(m['score_sd'])}, "
        f"min {_f(m['score_min'])}, max {_f(m['score_max'])}) |",
        f"| schema_valid_rate | {_f(m['schema_valid'], 3)} |",
        f"| parse errors | {m['parse_errors']} |",
        "",
        "## Serving / cost metrics", "",
        "| metric | value |", "| --- | --- |",
        f"| wall (runner busy interval) | {_f(m['wall'], 3, ' s')} |",
        f"| concurrency | {m['conc']} ({m['conc'] // m['rep']} per replica) |",
        f"| cold boot — deploy→engine ready (driver stamps) | {_f(m['boot_ready_s'], 1, ' s')} |",
        f"| preflight probe (engine answering) | {_f(m['cold'], 3, ' s')} |",
        f"| latency p50 / p95 / max | {_f(m['p50'], 2)} / {_f(m['p95'], 2)} / {_f(m['lat_max'], 2)} s |",
        f"| prompt / completion tokens | {m['ptok']} / {m['ctok']} |",
        f"| throughput | {_f(m['tps'], 1, ' tok/s')} |",
        f"| GPU $ over busy wall (×{m['rep']} L4 @ ${L4_USD_PER_HOUR}/h) | {_f(m['busy_usd'], 6, '')} |",
        f"| **$ per doc (busy)** | **{_f(m['usd_doc'], 6)}** |",
        f"| fleet window deploy→stop (upper est.) | {_f(m['fleet_s'], 0, ' s')} → {_f(m['fleet_usd'], 4)} USD |",
        f"| cost cap | ${spec['job']['cost_cap_usd']} (config) |",
        "",
        "## Engine observations (vLLM `/metrics`, measured — never inferred)", "",
        *_metrics_block(d), "",
        "## Analyst insights & findings", "",
        *insights(d, m), "",
    ]
    by = defaultdict(list)
    for i in d["items"].values():
        s = (i.get("score") or {}).get("overall_extraction_score")
        if i.get("ok") and isinstance(s, (int, float)):
            by[d["sub"].get(i["item_id"], "?")].append(s)
    lines += scoring_section(d)
    lines += figures(d, m, cls, by)
    lines += ["## Strata (subclass)", "", "| subclass | n | mean overall |", "| --- | --- | --- |"]
    for k in sorted(by, key=lambda k: -len(by[k])):
        lines.append(f"| {k} | {len(by[k])} | {statistics.mean(by[k]):.4f} |")
    lines += [f"| **total** | **{sum(len(x) for x in by.values())}** | **{_f(m['score'])}** |", "",
              "## Per-document scores", "",
              "| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for n, i in enumerate(d["items"].values(), 1):
        s = i.get("score") or {}
        lines.append(
            f"| {n} | `{i['item_id']}` | {d['sub'].get(i['item_id'], '?')} | {_f(s.get('overall_extraction_score'))} | "
            f"{_f(s.get('extraction_f1'))} | {'✓' if s.get('schema_valid') else '✗'} | "
            f"{_f((i.get('latency_ms') or 0) / 1000, 1)} | {i.get('prompt_tokens')} | {i.get('completion_tokens')} | "
            f"{(i.get('error') or '')[:60]} |")
    lines += ["", "## Reproduce", "", "```bash",
              "modal profile activate exios66",
              f"scripts/sand032/run_one.sh config/runs/{rid}.yaml deploy stop   # or: warm (reuse fleet)",
              f"scripts/mailroom-tui score {rid}",
              "```", "",
              "## Artifacts", "",
              "| path | role |", "| --- | --- |",
              f"| `config/runs/{rid}.yaml` | run spec |",
              f"| `reports/serving/{rid}.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |",
              f"| `data/runtime/runs/{rid}/` | run store (lock, dataset, items, /metrics before/after) — gitignored |",
              f"| `data/runtime/bt_experiments/{rid}/` | offline Braintrust-shaped rows — disposed after this report is committed |",
              ""]
    out = ROOT / "reports" / CLASS_DIR[cls] / f"SAND032-{rid.removeprefix('sand032-').upper()}-REPORT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    return out


def ladder_report() -> Path:
    rows, base = [], None
    for rid in LADDER:
        if not (RUNS / rid / "items.jsonl").is_file():
            continue
        d = load(rid)
        m = metrics(d)
        sc = {k: (v.get("score") or {}).get("overall_extraction_score") for k, v in d["items"].items()}
        rows.append((rid, m, sc))
        if base is None:
            base = (m, sc)
    lines = ["# SAND-032 Stage 1 — 1×L4 knob ladder (correspondence n=20, c8, same 20 docs every rung)", "",
             "Gate per rung (paired on identical doc ids): ok 20/20 · mean score ≥ L0 − 0.02 · "
             "schema_valid ≥ L0 − 0.05 · $/doc (busy) not worse than the previous kept rung. "
             "L3 (fp8 KV) is pinned for 2×L4 regardless.", "",
             "| rung | change | ok | score | Δ vs L0 (paired) | schema | wall s | p50 s | p95 s | tok/s | "
             "TTFT s | prefix % | boot→ready s | $/doc busy | gate |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    prev_usd = None
    for rid, m, sc in rows:
        rep = next(iter((load(rid)["after"].get("replicas") or {}).values()), {})
        paired = [sc[k] - base[1][k] for k in sc if k in base[1] and sc[k] is not None and base[1][k] is not None]
        delta = statistics.mean(paired) if paired else None
        ok_gate = (m["ok"] == m["n"] and (delta is None or delta >= -0.02)
                   and (m["schema_valid"] or 0) >= (base[0]["schema_valid"] or 0) - 0.05
                   and (prev_usd is None or m["usd_doc"] is None or m["usd_doc"] <= prev_usd * 1.0001))
        verdict = "PASS" if ok_gate else ("PINNED" if rid == "sand032-l3-fp8kv" else "REVERT")
        if ok_gate or rid == "sand032-l3-fp8kv":
            prev_usd = m["usd_doc"]
        lines.append(
            f"| {rid.removeprefix('sand032-')} | {RUNG_CHANGE[rid]} | {m['ok']}/{m['n']} | {_f(m['score'])} | "
            f"{_f(delta, 4)} | {_f(m['schema_valid'], 2)} | {_f(m['wall'], 1)} | {_f(m['p50'], 2)} | "
            f"{_f(m['p95'], 2)} | {_f(m['tps'], 0)} | {_f(rep.get('ttft_mean_seconds'), 2)} | "
            f"{_f((rep.get('prefix_cache_hit_rate') or 0) * 100, 1)} | {_f(m['boot_ready_s'], 0)} | "
            f"{_f(m['usd_doc'], 6)} | **{verdict}** |")
    fig = SERVING / "figures"
    fig.mkdir(parents=True, exist_ok=True)
    kept = {rid for rid, m, sc in rows}  # verdicts shown in the table; emphasis = measured rungs
    def panel(title, key, unit="", nd=2, lower_better=True):
        vals = [(rid.removeprefix("sand032-"), m[key]) for rid, m, _ in rows]
        best = (min if lower_better else max)((v for _, v in vals if v is not None), default=None)
        return viz.hbar(title, ("lower is better" if lower_better else "higher is better") + " · emphasis = best rung",
                        [{"label": r, "value": None if v is None else round(v, 6), "emphasis": v == best}
                         for r, v in vals], unit=unit, fmt=lambda v, nd=nd: f"{v:.{nd}f}", width=520, label_w=120)
    sm = viz.small_multiples("SAND-032 Stage 1 ladder — one axis per metric (same 20 docs every rung)", [
        panel("Mean overall score", "score", nd=4, lower_better=False),
        panel("Wall (s)", "wall", "s", 1),
        panel("Latency p50 (s)", "p50", "s", 2),
        panel("Latency p95 (s)", "p95", "s", 2),
        panel("$ per doc (busy GPU)", "usd_doc", "", 6),
        panel("Throughput (tok/s)", "tps", "", 0, lower_better=False),
    ], cols=2)
    (fig / "sand032-ladder.svg").write_text(sm)
    lines += ["", "![SAND-032 ladder small multiples](figures/sand032-ladder.svg)", "",
              "_The table above is the figure's table view._"]
    out = SERVING / "SAND032-LADDER.md"
    out.write_text("\n".join(lines) + "\n")
    return out


def _serving(rid: str) -> dict:
    d = _json(SERVING / f"{rid}.serving.json")
    return d.get("metrics", d) if d else {}


def _paired_means(a: str, b: str) -> tuple[float, float, int]:
    """(baseline mean, variant mean, n) over docs both runs scored (a = variant, b = baseline)."""
    ia = {i["item_id"]: i for i in _jsonl(RUNS / a / "items.jsonl")}
    ib = {i["item_id"]: i for i in _jsonl(RUNS / b / "items.jsonl")}
    sc = lambda i: (i.get("score") or {}).get("overall_extraction_score")  # noqa: E731
    keys = [k for k in ib if k in ia and ia[k].get("ok") and ib[k].get("ok")
            and isinstance(sc(ia[k]), (int, float)) and isinstance(sc(ib[k]), (int, float))]
    if not keys:
        return 0.0, 0.0, 0
    return statistics.mean(sc(ib[k]) for k in keys), statistics.mean(sc(ia[k]) for k in keys), len(keys)


SUMMARY_FIGS = "<!-- sand032-program-figures -->"


def program_figures() -> Path:
    """Summary-level figures (routing, admission ×2, v2 prompts) + one link block in the summary."""
    fig_dir = ROOT / "reports" / "serving" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    routing = [
        ("1×L4 · c8 (s2a)", "sand032-s2a-corr100-1rep"),
        ("2×L4 · c16 · max_inputs 32 (s2b)", "sand032-s2b-corr100-2rep"),
        ("2×L4 · c64 · max_inputs 64 (s7)", "sand032-s7-corr100-seqs32"),
        ("2×L4 · c64 · max_inputs 32 (s9)", "sand032-s9-corr100-bal"),
    ]
    rrows = []
    for label, rid in routing:
        m = _serving(rid)
        if m.get("wall_seconds"):
            rrows.append({"label": label, "value": round(float(m["wall_seconds"]), 1),
                          "emphasis": "(s7)" in label or "(s9)" in label,
                          "note": f"{float(m.get('tokens_per_second') or 0):.0f} tok/s"})
    (fig_dir / "sand032-routing.svg").write_text(viz.hbar(
        "Correspondence n=100 wall time by fleet",
        "same 100 docs · lower is better · s7 routed 97/100 requests to one replica",
        rrows, unit="s", fmt=lambda v: f"{v:.1f}", label_w=250))
    adm = [
        ("correspondence n=100", "sand032-s2b-corr100-2rep", "sand032-s9-corr100-bal"),
        ("insurance n=50", "sand032-s3-insurance50", "sand032-s9-insurance50-bal"),
        ("corporate n=50", "sand032-s3-corporate50", "sand032-s9-corporate50-bal"),
        ("contracts n=50", "sand032-s3-contracts50", "sand032-s9-contracts50-bal"),
    ]
    arows = [{"label": lab, "a": round(float(_serving(a)["wall_seconds"]), 1),
              "b": round(float(_serving(b)["wall_seconds"]), 1)}
             for lab, a, b in adm if _serving(a).get("wall_seconds") and _serving(b).get("wall_seconds")]
    (fig_dir / "sand032-admission.svg").write_text(viz.dumbbell(
        "Wall time: seqs16 fleet → seqs32 balanced fleet", "2×L4 · lower is better",
        arows, ("seqs16", "seqs32 balanced"), unit="s", fmt=lambda v: f"{v:.0f}"))
    v2 = [("correspondence", "sand032-s10-corr75-v2", "sand032-s3-corr50"),
          ("insurance_claim", "sand032-s10-insurance75-v2", "sand032-s3-insurance50"),
          ("corporate_record", "sand032-s10-corporate75-v2", "sand032-s3-corporate50")]
    vrows = []
    for lab, a, b in v2:
        prod, new, n = _paired_means(a, b)
        if n:
            vrows.append({"label": f"{lab} (paired n={n})", "a": round(prod, 4), "b": round(new, 4)})
    (fig_dir / "sand032-v2-prompts.svg").write_text(viz.dumbbell(
        "Production prompt → eval-environment v2 prompt",
        "same docs · overall extraction score (0–1, higher is better)",
        vrows, ("production", "v2"), fmt=lambda v: f"{v:.3f}", label_w=230))
    summary = ROOT / "reports" / "serving" / "QWEN3-L4-LADDER-SUMMARY.md"
    text = summary.read_text()
    block = "\n".join([
        SUMMARY_FIGS, "## Figures", "",
        "![SAND-032 knob ladder small multiples](figures/sand032-ladder.svg)", "",
        "![Correspondence n=100 wall time by fleet](figures/sand032-routing.svg)", "",
        "![Wall time, seqs16 fleet vs seqs32 balanced fleet](figures/sand032-admission.svg)", "",
        "![Production vs v2 prompt, paired](figures/sand032-v2-prompts.svg)", "",
        "_Table views: sections 1, 2 and 7 above, and [SAND032-V2-PROMPT-PROMOTION.md](SAND032-V2-PROMPT-PROMOTION.md)._", "",
    ])
    head = text[: text.index(SUMMARY_FIGS)].rstrip() if SUMMARY_FIGS in text else text.rstrip()
    summary.write_text(head + "\n\n" + block)
    return summary


if __name__ == "__main__":
    cmd, *args = sys.argv[1:] or ["ladder"]
    if cmd == "run":
        for rid in args:
            print(run_report(rid))
    elif cmd == "ladder":
        print(ladder_report())
    elif cmd == "program":
        print(program_figures())
    elif cmd == "all":  # every SAND-032 run report + ladder + program figures
        for run in sorted((RUNS).glob("sand032-*")):
            if (run / "items.jsonl").is_file() and not run.name.endswith(".aborted-404"):
                try:
                    print(run_report(run.name))
                except Exception as exc:  # noqa: BLE001 — report which run could not render
                    print(f"SKIP {run.name}: {type(exc).__name__}: {exc}")
        print(ladder_report())
        print(program_figures())
