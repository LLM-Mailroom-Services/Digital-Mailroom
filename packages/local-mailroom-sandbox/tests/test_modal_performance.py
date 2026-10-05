"""Modal specialist performance figures — hub_data + serving exports only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "reports" / "dashboard"
sys.path.insert(0, str(DASH))
sys.path.insert(0, str(ROOT / "scripts" / "sand032"))

import modal_performance as mp  # noqa: E402
import viz  # noqa: E402

D = json.loads((DASH / "hub_data.json").read_text())


def test_all_figures_render_and_contain_svg():
    figs = mp.render(D, viz)
    assert len(figs) == 9
    for path, body in figs.items():
        assert body.startswith("<svg"), path
        assert "class=\"viz\"" in body, path
        assert (DASH / path).is_file(), f"missing committed figure {path}; run scripts/sand032/render_modal_performance.py"


def test_matrix_cells_match_run_reports():
    _, _, cells = mp._collect_matrix(D)
    for (label, col), score in cells.items():
        if score is None:
            continue
        cls = next(c for c in D["classes"] if D["labels"][c] == label)
        rid = mp.MATRIX_RUNS[(cls, col)]
        run = D["runs"][rid]
        expected = mp._score(run)
        assert abs(score - expected) < 1e-4, f"{rid} matrix {score} vs report {expected}"


def test_qwen8b_table_matches_user_break_even_grid():
    import gpu_report

    rows = list(mp._same_model_rows(D, gpu_report.NOT_A_CONFIG))
    assert len(rows) == 4
    by_label = {r["label"]: r for r in rows}
    corr = by_label["Correspondence"]
    assert corr["run"] == "sand032-s3-corr50"
    assert abs(corr["modal_usd"] - 0.00014) < 0.00002
    assert abs(corr["ratio"] - 0.05) < 0.01
    assert corr["cold_n"] == 26


def test_cost_stack_sums_to_busy_plus_idle_plus_cold():
    rate = D["l4_usd_per_hour"]
    for rid in mp.COST_STACK_RUNS:
        fleet = D["fleet"][rid]
        parts = mp._cost_parts(rid, fleet, rate)
        per_doc = fleet["busy_usd"] / fleet["ok"]
        assert parts["busy"] <= per_doc + 1e-9
        assert sum(parts.values()) >= per_doc * 0.99
