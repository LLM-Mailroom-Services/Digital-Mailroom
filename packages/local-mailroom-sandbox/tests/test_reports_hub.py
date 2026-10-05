"""Reports hub stays in sync with the tracked reports it is built from."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "reports" / "dashboard"
sys.path.insert(0, str(DASH))
_SPEC = importlib.util.spec_from_file_location("build_hub", DASH / "build_hub.py")
build_hub = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(build_hub)
import hub_extract  # noqa: E402
import legacy_runs  # noqa: E402


def _data():
    return build_hub.assemble(json.loads(build_hub.SNAPSHOT.read_text()))


def test_every_sandbox_figure_resolves_and_cross_checks_pass():
    data = _data()
    assert len(data["provenance"]) > 500
    for p in data["provenance"]:
        if p["repo"] == "Exios66/local-mailroom-sandbox":
            assert (ROOT / "reports" / p["source"].removeprefix("reports/")).is_file(), p


def test_documented_issues_are_exactly_the_known_ones():
    keys = {i["key"] for i in _data()["issues"]}
    assert keys <= set(hub_extract.KNOWN) | set(legacy_runs.KNOWN)
    assert set(legacy_runs.KNOWN) <= keys


def test_snapshot_pins_both_sibling_repos():
    snap = json.loads(build_hub.SNAPSHOT.read_text())
    assert set(snap["sources"]) == {build_hub.EVAL_ENV, build_hub.MAILROOM_ML}
    assert all(p["sha"] == snap["sources"][p["repo"]] for p in snap["provenance"])


def test_committed_page_is_current():
    assert build_hub.main(["--check"]) == 0


def test_collapse_signal_counts_top_prediction_share():
    rows = [("contract", t, "license", t == "license") for t in ["service", "license", "supply", "service"]]
    got = hub_extract.collapse_signal(rows + [("correspondence", "email", "email", True)])
    assert got["contract"] == {"n": 4, "correct": 1, "top_pred": ["license", 4], "top_true": ["service", 2]}
    assert got["correspondence"]["correct"] == 1
    assert "insurance_claim" not in got


def test_collapse_and_sorter_views_match_their_sources():
    snap = json.loads(build_hub.SNAPSHOT.read_text())
    for arm in ("armA", "armB"):
        eda = snap["mb"][arm]["eda"]
        for c, g in eda["collapse"].items():
            assert g["n"] == eda["subclass"][c]["n"] and g["correct"] == eda["subclass"][c]["correct"]
            assert g["top_true"][1] <= g["n"] and g["top_pred"][1] <= g["n"]
    sorter = snap["api"]["sorter"]
    assert set(sorter) == {r["model"] for r in snap["api"]["classification"] if r["n"] == 100}
    for m, s in sorter.items():
        assert sum(s["confusion"].values()) == s["n"] == 100
        assert all(b["n"] >= hub_extract.SORTER_BIN_MIN for b in s["bins"])
        run = next(r for r in snap["api"]["classification"] if r["model"] == m and r["n"] == 100)
        right = sum(v for k, v in s["confusion"].items() if k.split("->")[0] == k.split("->")[1])
        assert right / 100 == run["class_acc"]
