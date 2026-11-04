"""SAND-039: the master card is generated from committed cards and fills in SAND-39."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from mailroom_sandbox.job import grid_master
from mailroom_sandbox.paths import repo_root

SAND37 = repo_root() / "reports" / "SAND-37"


def _seed(tmp: Path, with_sand39: bool) -> Path:
    root = tmp / "reports" / "SAND-37"
    for shape in ("1L4", "2L4"):
        for card in (SAND37 / shape).glob("*/*.card.json"):
            if shape == "1L4" and card.name.startswith("grid-50-"):
                continue  # real SAND-39 cells; the fixture controls whether SAND-39 is present
            dst = root / shape / card.parent.name / card.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(card, dst)
    if with_sand39:
        # Stand-in SAND-39 cells: the 2×L4 n=50 cards re-keyed to the 1×L4 C8 run ids.
        for card in (SAND37 / "2L4").glob("*/grid-50-*.card.json"):
            data = json.loads(card.read_text())
            stem = data["run_id"].replace("-2l4-rerun", "-1l4").replace("-2l4", "-1l4")
            data["run_id"] = stem
            data["conditions"].update(replicas=1, concurrency=8)
            dst = root / "1L4" / card.parent.name / f"{stem}.card.json"
            dst.write_text(json.dumps(data))
    return tmp


def test_sand39_pending_before_its_cells_exist(tmp_path):
    md = grid_master.render_master_md(grid_master.collect_master(_seed(tmp_path, False)))
    assert "| Experiment 2 | 1×L4 C8 n=50 | 1 | 8 | 50 | pending |" in md
    assert "Experiment 2 pending" in md
    assert "| Experiment 3 | 2×L4 C32 n=50 | 2 | 32 | 50 | 5 of 5 cells |" in md


def test_sand39_populates_and_becomes_the_matched_sample_baseline(tmp_path):
    md = grid_master.render_master_md(grid_master.collect_master(_seed(tmp_path, True)))
    assert "| Experiment 2 | 1×L4 C8 n=50 | 1 | 8 | 50 | 5 of 5 cells |" in md
    assert "identical 250 documents" in md
    assert "Experiment 2 pending" not in md


def test_master_ignores_legacy_cells(tmp_path):
    repo = _seed(tmp_path, False)
    legacy = SAND37 / "2L4" / "contracts" / "grid-50-contracts-specialist-awq-2l4-rerun.card.json"
    data = json.loads(legacy.read_text())
    data["run_id"] = "grid-50-contracts-specialist-awq-2l4"  # superseded legacy id
    (repo / "reports/SAND-37/2L4/contracts/legacy.card.json").write_text(json.dumps(data))
    cards = grid_master.collect_master(repo)["cards"]["s37-2l4-n50"]
    assert cards["contracts"]["run_id"] == "grid-50-contracts-specialist-awq-2l4-rerun"


def test_sand40_column_is_measured_with_the_optimized_merger_mark():
    md = grid_master.render_master_md(grid_master.collect_master())
    assert "| Experiment 4 | 2×L4 C32 n=100 | 2 | 32 | 100 (merger 50†) | 5 of 5 cells |" in md
    assert ")†" in md  # merger score carries the dagger
    assert "pending" not in md.lower().split("quality and cost")[1]
    assert "**Larger runs cost less per document.** Running n = 100 per specialist instead of n = 50" in md
    assert "**Merger is the quality gap; the † settings narrow it.** They raise MAUD accuracy 0.035 → 0.140" in md
    appendix = grid_master.render_appendix_md(grid_master.collect_master())
    assert "### Scale check: four unchanged specialists (merger excluded)" in appendix
    assert "| Documents ok / total | 199 / 200 | 399 / 400 | — |" in appendix
    assert "answers only 13%–24% of labeled MAUD questions" in appendix


def test_pooled_four_requires_all_four_unchanged_specialists():
    cards = grid_master.collect_master()["cards"]["s40-2l4"]
    four = grid_master._pooled_four(cards, 2)
    assert four and four["cells"] == 4 and four["documents"] == 400
    assert grid_master._pooled_four({k: v for k, v in cards.items() if k != "contracts"}, 2) is None


def test_merger_settings_table_shows_what_the_dagger_changes():
    md = grid_master.render_master_md(grid_master.collect_master())
    assert "## Merger † settings" in md
    assert "Serving window" not in md  # unchanged settings are stated once, not tabled
    assert "| Input | head + tail, 30,000 chars (rest of the agreement unread) | whole agreement, chunked: 47,000-char" in md
    assert "| `merger_agreement_specialist_maud_v1` |" in md
    assert "| Result | MAUD accuracy 0.035, coverage 23%, 46/50 ok" in md


def test_committed_master_card_is_current():
    """Committed master + appendix must match a fresh render (regenerate with `sandbox run card --master`)."""
    committed = (SAND37 / f"{grid_master.MASTER_STEM}.md").read_text(encoding="utf-8")
    assert committed == grid_master.render_master_md(grid_master.collect_master())
    appendix = (SAND37 / f"{grid_master.APPENDIX_STEM}.md").read_text(encoding="utf-8")
    assert appendix == grid_master.render_appendix_md(grid_master.collect_master())


def test_master_stays_executive_length():
    """The master card is a two-page executive summary; detail lives in the appendix."""
    md = grid_master.render_master_md(grid_master.collect_master())
    assert len(md.splitlines()) <= grid_master.EXECUTIVE_MAX_LINES
    for heading in (
        "## Per-cell detail",
        "## Clause scoring detail",
        "## Engine telemetry",
        "## Run conditions by specialist",
        "## SAND-40 validation probes",
        "## Figures: posture comparison",
        "## Appendix: posture dashboards",
    ):
        assert heading not in md
    assert f"{grid_master.APPENDIX_STEM}.md" in md


def test_record_metered_round_trips(tmp_path):
    (tmp_path / "reports" / "SAND-37").mkdir(parents=True)
    grid_master.record_metered("SAND-39", 0.623, 0.0, "note", repo=tmp_path)
    data = json.loads((tmp_path / "reports/SAND-37/metered-costs.json").read_text())
    assert data["SAND-39"] == {"metered_usd": 0.62, "billed_usd": 0.0, "note": "note"}


def test_cost_table_reconciles_busy_window_against_metered_session():
    pooled = {
        "s37-1l4-n20": {"documents": 100, "busy_usd": 0.15},
        "s37-2l4-n50": {"documents": 250, "busy_usd": 0.30},
        "s39-1l4-n50": {"documents": 250, "busy_usd": 0.25},
    }
    present = [p for p in grid_master.POSTURES if p.key in pooled]
    metered = {"SAND-37": {"metered_usd": 0.90, "billed_usd": 0.0}, "SAND-39": {"metered_usd": 0.50, "billed_usd": 0.0}}
    rows = grid_master._cost_table(present, pooled, metered)
    assert "| Experiments 1 + 3 | 350 | $0.45 | $0.90 | 50% | $0.00257 | $0.00 |" in rows
    assert "| Experiment 2 | 250 | $0.25 | $0.50 | 50% | $0.00200 | $0.00 |" in rows
    assert "| **Total** | 600 | $0.70 | $1.40 | 50% | $0.00233 | $0.00 |" in rows
    assert grid_master._cost_table(present, pooled, {}) == []


def test_figures_embed_in_master_and_matched_panel_waits_for_sand39(tmp_path):
    from mailroom_sandbox.job import grid_figures

    before = grid_master.collect_master(_seed(tmp_path / "a", False))
    keys = [s["key"] for s in grid_figures.figure_specs(before)]
    assert "cmp-matched" not in keys and "posture-s39-1l4-n50" not in keys
    after = grid_master.collect_master(_seed(tmp_path / "b", True))
    specs = grid_figures.figure_specs(after)
    assert {"cmp-efficiency", "cmp-quality", "cmp-latency-cost", "cmp-matched", "posture-s39-1l4-n50"} <= {
        s["key"] for s in specs
    }
    md = grid_master.render_appendix_md(after)
    assert "](figures/cmp-matched.png)" in md
    assert "](2L4/figures/SAND-37-2xL4-C32-n50.png)" in md
    assert "](1L4/figures/SAND-39-1xL4-C8-n50.png)" in md


def test_write_master_renders_every_linked_figure(tmp_path):
    repo = _seed(tmp_path, True)
    paths = grid_master.write_master(repo)
    md = paths["appendix"].read_text()
    assert grid_master.APPENDIX_STEM in str(paths["appendix"])
    from mailroom_sandbox.job import grid_figures

    for spec in grid_figures.figure_specs(grid_master.collect_master(repo)):
        png = repo / "reports" / "SAND-37" / spec["path"]
        assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        assert f"]({spec['path']})" in md


def test_master_is_fully_detailed():
    md = grid_master.render_appendix_md(grid_master.collect_master())
    for heading in (
        "## Per-cell detail",
        "### Experiment 1 · 1×L4 C8 n=20",
        "### Experiment 2 · 1×L4 C8 n=50",
        "### Experiment 3 · 2×L4 C32 n=50",
        "### Experiment 4 · 2×L4 C32 n=100",
        "## Clause scoring detail",
        "## Engine telemetry (vLLM /metrics, this run's delta)",
        "## Run conditions by specialist",
    ):
        assert heading in md
    # contracts is defined as what it is: CUAD presence F1 over labeled documents
    assert "per-document CUAD clause-presence F1 averaged over the successful documents" in md
    assert "## Quality and cost by specialist" not in md  # the scorecard lives on the master only
    assert "| Experiment 3 · 2×L4 C32 n=50 | 40 of 49 ok |" in md


def test_probes_are_reported_matched_but_never_pooled():
    data = grid_master.collect_master()
    assert set(data["probes"]) == {"contracts", "merger_agreement"}
    assert all("probe" not in c["run_id"] for p in data["cards"].values() for c in p.values())
    for md in (grid_master.render_master_md(data), grid_master.render_appendix_md(data)):
        assert "validation probes" not in md and "65,536" not in md


def test_dagger_figure_and_markers_follow_the_sand40_merger_cell():
    from mailroom_sandbox.job import grid_figures

    data = grid_master.collect_master()
    specs = {s["key"]: s for s in grid_figures.figure_specs(data)}
    assert "cmp-merger-dagger" in specs
    assert "†" in specs["cmp-quality"]["caption"] and "†" in specs["cmp-latency-cost"]["caption"]
    assert ("s40-2l4", "merger_agreement") in grid_figures.DAGGER
    md = grid_master.render_appendix_md(data)
    assert "](figures/cmp-merger-dagger.png)" in md


def test_token_split_fits_instructions_per_call_and_falls_back_when_unidentifiable():
    from mailroom_sandbox.job.grid_cards import FALLBACK_CHARS_PER_TOKEN, token_split

    # 2,000 instruction tokens per call + 4 chars/token over documents of varied length
    docs = [
        {"ok": True, "calls": 1, "input_chars": c, "prompt_tokens": 2000 + c / 4, "completion_tokens": 100}
        for c in (800, 1600, 3000, 5000, 9000, 12000, 15000, 20000)
    ]
    sp = token_split(docs)
    assert sp["method"] == "fit"
    assert abs(sp["chars_per_token"] - 4.0) < 1e-6 and abs(sp["instruction_per_call"] - 2000) < 1e-6
    # every document cut to the same cap: not identifiable → fallback ratio, instructions are the remainder
    capped = [dict(d, input_chars=30000, prompt_tokens=9000) for d in docs]
    sp = token_split(capped)
    assert sp["method"] == "fallback" and sp["chars_per_token"] == FALLBACK_CHARS_PER_TOKEN
    assert abs(sp["per_document"]["document"] - 30000 / FALLBACK_CHARS_PER_TOKEN) < 1e-6
    # chunked runs never fit (re-samples add calls the profile cannot see)
    assert token_split(docs, chunked=True)["method"] == "fallback"
    assert token_split([{"ok": False}]) is None


def test_master_reports_token_composition_and_figure():
    from mailroom_sandbox.job import grid_figures

    data = grid_master.collect_master()
    md = grid_master.render_appendix_md(data)
    assert "## Token composition" in md
    assert "| Merger Agreements † (Experiment 4) |" in md
    assert "**Fixed instructions, not document text, account for most tokens in the short classes.**" in md
    assert "cmp-tokens" in {s["key"] for s in grid_figures.figure_specs(data)}


def test_master_embeds_the_record_figures_that_exist(tmp_path):
    """Executive card carries only the three key-finding charts; every other record figure is in the appendix."""
    data = grid_master.collect_master()
    md, appendix = grid_master.render_master_md(data), grid_master.render_appendix_md(data)
    assert md.count("](figures/record/") == 3
    for section, stems in grid_master.RECORD_FIGURES.items():
        home, other = (md, appendix) if section in grid_master.MASTER_FIG_SECTIONS else (appendix, md)
        for stem, _ in stems:
            link = f"]({grid_master.RECORD_FIG_DIR}/{stem}.png)"
            assert (SAND37 / grid_master.RECORD_FIG_DIR / f"{stem}.png").is_file()
            assert home.count(link) == 1 and link not in other
    head, tail = md.split("## Quality and cost by specialist")
    assert "](figures/record/1x-vs-2xL4-throughput.png)" in head
    assert "](figures/record/2xL4-n50-vs-n100-cost.png)" in head
    assert "](figures/record/merger-frozen-vs-dagger.png)" in tail.split("## Merger † settings")[1]
    exp4 = appendix.split("### Experiment 4 · 2×L4 C32 n=100")[1].split("## Clause scoring detail")[0]
    assert "](figures/record/2xL4-C32-n100-latency.png)" in exp4
    assert "| Experiment | Posture |" in md
    bare = grid_master.collect_master(_seed(tmp_path, True))
    assert "figures/record/" not in grid_master.render_master_md(bare)
    assert "figures/record/" not in grid_master.render_appendix_md(bare)


def test_master_reports_carry_experiment_labels_not_study_ids():
    """Executive card and appendix name postures Experiment 1-4; SAND ids survive only in file paths."""
    import re

    data = grid_master.collect_master()
    for md in (grid_master.render_master_md(data), grid_master.render_appendix_md(data)):
        visible = re.sub(r"\]\([^)]*\)", "]()", md)  # drop link targets (file names)
        assert "SAND" not in visible
        assert "Experiment 4" in visible
