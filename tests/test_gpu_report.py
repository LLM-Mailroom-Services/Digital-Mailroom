"""GPU economics report and the mailroom-issues Pages site: derived numbers and static-site integrity.

Driven by the committed ``reports/dashboard/hub_data.json`` (no sibling checkouts needed).
"""

from __future__ import annotations

import json
import math
import posixpath
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "reports" / "dashboard"
sys.path.insert(0, str(DASH))
import export_hub_reports as X  # noqa: E402
import gpu_report  # noqa: E402
import pages_site  # noqa: E402

D = json.loads((DASH / "hub_data.json").read_text())
F = D["fleet"]
RATE = D["l4_usd_per_hour"]


def _report():
    return gpu_report.report(D, X, "test-shas")


def test_cost_per_token_is_the_throughput_identity():
    coeff = 1e6 * RATE / 3600
    for r in F.values():
        assert r["busy_usd"] == r["wall"] * r["replicas"] * RATE / 3600
        # $ per 1M tokens = rate / 3600 / (tok/s per L4) × 1e6, up to tok/s rounding in the export
        assert math.isclose(gpu_report.per_mtok(r), coeff / gpu_report.tps_l4(r), rel_tol=2e-3), r["run"]


def test_keep_warm_threshold_is_scaledown_plus_l5_boot():
    boot = next(x["boot"] for x in D["ladder"] if x["rung"] == "l5-graphs")
    scaledowns = {r["scaledown"] for r in F.values() if r.get("scaledown")}
    assert len(scaledowns) == 1
    g_star = scaledowns.pop() + boot
    md, _, stats = _report()
    assert f"within {g_star:.0f} s ({g_star / 60:.1f} min" in md
    assert any(t["value"] == f"{g_star / 60:.1f} min" for t in stats["tiles"])


def test_amortizing_batch_is_the_smallest_that_meets_each_premium():
    boot = next(x["boot"] for x in D["ladder"] if x["rung"] == "l5-graphs")
    scaledown = next(r["scaledown"] for r in F.values() if r.get("scaledown"))
    md, _, _ = _report()
    for c, r in gpu_report.best_by_class(F).items():
        per_doc = r["busy_usd"] / r["ok"]
        for n_l4 in (1, 2):
            cycle = (scaledown + boot) * n_l4 * RATE / 3600
            for p in gpu_report.PREMIUMS:
                n = math.ceil(cycle / (p * per_doc))
                assert cycle / (n * per_doc) <= p < cycle / ((n - 1) * per_doc)
        row = next(ln for ln in md.splitlines() if ln.startswith(f"| {c.capitalize()} | {X.usd(per_doc)} |"))
        assert f"{math.ceil((scaledown + boot) * 2 * RATE / 3600 / (0.1 * per_doc)):,}" in row


def test_best_config_skips_the_ladder_bf16_and_misrouted_runs():
    best = gpu_report.best_by_class(F)
    assert set(best) == set(gpu_report.CLASS_OF_DIR.values())
    assert not {r["run"] for r in best.values()} & gpu_report.NOT_A_CONFIG


def test_site_is_static_self_contained_and_links_resolve():
    md, figs, stats = _report()
    files = {**figs, "MODAL-VLLM-GPU-REPORT.md": md,
             "MASTER-REPORT.md": "# Master\n\nSee [GPU](MODAL-VLLM-GPU-REPORT.md#summary).\n\n## One\n",
             "COST-COMPARISON-MODAL-VS-API.md": "# Cost\n\nBack to [the index](README.md) or [AGENTS](../AGENTS.md).\n"}
    site = pages_site.build(files, stats, "test-shas")
    assert set(site) == {".nojekyll", "index.html", "reports/master.html", "reports/cost-comparison.html",
                         "reports/gpu-economics.html"}
    gpu_page = site["reports/gpu-economics.html"]
    assert gpu_page.count('<figure class="fig">') == md.count("![")
    for path, page in site.items():
        if not path.endswith(".html"):
            continue
        assert "<script" not in page and "<img" not in page and "<link" not in page, path
        ids = set(re.findall(r'\sid="([^"]+)"', page))
        for href in re.findall(r'href="([^"]+)"', page):
            if href.startswith("https://"):
                continue
            target, _, frag = href.partition("#")
            if not target:
                assert frag in ids, (path, href)
                continue
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
            assert resolved in site, (path, href)


def _row(md, name):
    return next(ln for ln in md.splitlines() if ln.startswith(f"| {name} |"))


def test_setup_table_is_read_from_the_fleet_data():
    md, _, _ = _report()
    model, posture = _row(md, "Model / engine"), _row(md, "Frozen serving posture (L5)")
    fleet, data = _row(md, "Fleet"), _row(md, "Data")
    runs = list(F.values())
    for r in runs:
        assert f"`{r['model']}`" in model, r["run"]
        if r["vllm"] is not None:
            assert f"vLLM `{r['vllm']}`" in model, r["run"]
            assert f"`{r['model']}` (" in model and f"`max_model_len` {r['max_model_len']}" in model, r["run"]
        assert f"`{r['quant']}`" in model, r["run"]
        assert f"Modal {r['gpu']} (" in fleet, r["run"]
        if r.get("scaledown"):
            assert f"scaledown {r['scaledown']:.0f} s" in fleet, r["run"]
        if r.get("containers_min") is not None:
            assert r["containers_min"] == r["replicas"] and "`min = max` containers pinned" in fleet, r["run"]
        if r["seed"] is not None:
            assert f"seed {r['seed']}," in data and f"`{r['dataset_rev']}`" in data, r["run"]
            assert f"nested draws ({r['draw_nesting']})" in data and f"split {r['dataset_split']}" in data, r["run"]
        assert f"`{r['dataset']}`" in data and any(f"@ `{v}" in data for v in [r["dataset_rev"]]), r["run"]
    l5 = F["sand032-l5-graphs"]
    assert posture.startswith(f"| Frozen serving posture (L5) | `{l5['quant']}`, {l5['kv_cache_dtype']} KV cache, thinking {l5['thinking']}")
    assert f"`max_num_seqs` {l5['seqs']} (" in posture
    hi = sorted({r["seqs"] for r in runs if r["seqs"] > l5["seqs"]})
    assert f"({'/'.join(map(str, hi))} on the " in posture
    # the table carries no hard-coded setup values any more
    for stale in ("v0.29.0`, `max_model_len` 32768, prefix", "Modal L4 (24 GB)", "`ed7576b`, seed 42"):
        assert stale not in md
    mem = next(p for p in D["provenance"] if p["key"] == "fleet.gpu_spec.memory")
    assert f"({mem['value']} VRAM per the deploy spec" in fleet


def test_l4_rate_comes_only_from_the_hub_data(monkeypatch):
    import copy

    base_md, base_figs, base_stats = _report()
    monkeypatch.setattr(X, "L4_USD_PER_HOUR", 123456.0)  # junk: must not reach the report
    md, figs, stats = _report()
    assert (md, figs, stats) == (base_md, base_figs, base_stats)

    d2 = copy.deepcopy(D)
    d2["l4_usd_per_hour"] = 1.6
    md2, figs2, _ = gpu_report.report(d2, X, "test-shas")
    assert md2 != base_md
    assert f"${RATE:.2f} per L4-hour" in base_md and "$1.60 per L4-hour" in md2
    coeff, coeff2 = 1e6 * RATE / 3600, 1e6 * 1.6 / 3600
    assert f"= {coeff:.1f} ÷ (tok/s per L4)" in base_md and f"= {coeff2:.1f} ÷ (tok/s per L4)" in md2
    e1, e2 = gpu_report.early_2x(X, RATE), gpu_report.early_2x(X, 1.6)
    for x, y in zip(e1, e2):
        assert math.isclose(y["busy_usd"], x["busy_usd"] * 1.6 / RATE)
    assert figs2["figures/gpu/keep-warm-vs-scale-to-zero.svg"] != base_figs["figures/gpu/keep-warm-vs-scale-to-zero.svg"]


def test_cold_boot_cutoff_is_a_named_rule_and_cross_refs_resolve():
    md, _, _ = _report()
    cold = [r for r in F.values() if r["cold_boot"] >= gpu_report.COLD_BOOT_MIN_S]
    warm = [r for r in F.values() if r["cold_boot"] < gpu_report.COLD_BOOT_MIN_S]
    assert max(r["cold_boot"] for r in warm) < gpu_report.COLD_BOOT_MIN_S <= min(r["cold_boot"] for r in cold)
    assert "classification rule, not a measurement" in md
    sec = re.search(r"^### ([\d.]+) The first second-L4 attempt", md, re.M).group(1)
    assert f"Section {sec} uses both replicas" in md and "§EARLY§" not in md


def _breakeven():
    import breakeven  # noqa: PLC0415
    return breakeven, breakeven.analyze(D, gpu_report.NOT_A_CONFIG)


def test_breakevens_reproduce_from_measured_inputs():
    B, E = _breakeven()
    boot = next(x["boot"] for x in D["ladder"] if x["rung"] == "l5-graphs")
    for x in E["configs"]:
        f = F[x["modal"]["run"]]
        m, a = f["busy_usd"] / f["ok"], x["cheap"]["usd"]
        assert math.isclose(x["ratio"], m / a)
        for n_l4 in (1, 2):
            w = x[f"l4x{n_l4}"]
            cycle = (f["scaledown"] + boot) * n_l4 * RATE / 3600
            assert math.isclose(w["cycle_usd"], cycle)
            if m < a:
                n = w["batch_star"]
                # smallest cold batch whose total cost is no more than the API's
                assert cycle + n * m <= n * a < cycle + (n - 1) * m + a
                # warm fleet: at the break-even rate the hourly bill equals the API bill
                assert math.isclose(w["docs_h_star"] * a, n_l4 * RATE)
            else:
                assert w["batch_star"] is None and w["docs_h_star"] is None


def test_optimal_is_the_best_saving_that_keeps_quality():
    _, E = _breakeven()
    ok = [x for x in E["configs"] if x["cheaper"] and x["comparable"] and x["modal"]["score"] >= x["cheap"]["score"]]
    assert E["optimal"] is max(ok, key=lambda x: x["save_pct"])
    assert all(x["modal"]["score"] is not None for x in E["configs"])


def test_reports_quote_the_same_break_even():
    _, E = _breakeven()
    md, _, stats = _report()
    cost = X.cost_report(D, X.route_rows(D), E, X.sorters_of(D), "test-shas")
    assert X.optimal_sentence(E) in md
    o = E["optimal"]
    tile = next(t for t in stats["tiles"] if t["label"] == "Modal saving per document, best case")
    assert f"{o['save_pct'] * 100:.0f}%" in tile["value"] and f"{o['l4x1']['docs_h_star']:,.0f} docs/h" in tile["sub"]
    assert f"{o['l4x1']['docs_h_star']:,.0f} docs/h sustained" in cost
