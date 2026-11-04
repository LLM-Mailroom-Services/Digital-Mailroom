"""The redrawn source-repo charts render in the dark kit, and their table twins carry the hub data's values."""

from __future__ import annotations

import importlib.util
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "reports" / "dashboard"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


viz = _load("sand032_viz", ROOT / "scripts" / "sand032" / "viz.py")
sc = _load("source_charts", DASH / "source_charts.py")
D = json.loads((DASH / "hub_data.json").read_text())
SVGS = sc.render(D, viz)
TABLES = sc.tables(D)
KEYS = ["figures/api/extraction-score-by-type.svg", "figures/api/cost-per-document.svg",
        "figures/api/sorter-subclass-accuracy.svg", "figures/api/sorter-calibration.svg",
        "figures/modernbert/doc-type-recall.svg", "figures/modernbert/selective-risk.svg",
        "figures/modernbert/subclass-collapse.svg"]
LIGHT = ("#fcfcfb", "#ffffff", "#fff\"", "#fafafa", "#f8f8f7", "white")


def _rows(md: str) -> list[list[str]]:
    lines = md.strip().splitlines()
    assert re.fullmatch(r"\|( ?-{3,}:? \|)+", lines[1].replace("---:", "---")), lines[1]
    return [[c.strip() for c in ln.strip("|").split("|")] for ln in lines[2:]]


def test_every_key_renders_a_well_formed_dark_card():
    assert list(SVGS) == KEYS and set(TABLES) == set(KEYS) and set(sc.CAPTIONS) == set(KEYS)
    for k, svg in SVGS.items():
        root = ET.fromstring(svg)  # well-formed XML
        assert root.get("role") == "img" and root.get("aria-label"), k
        assert viz.STYLE in svg and "--surface:#1a1a19" in svg, k
        bg = re.search(r'<rect class="bg" width="(\d+)" height="(\d+)"', svg)
        assert bg and root.get("viewBox") == f"0 0 {bg.group(1)} {bg.group(2)}", k  # card fills the figure
        low = svg.lower()
        for c in LIGHT:  # no light surfaces or light-theme fills
            assert f'fill="{c}' not in low and f"background:{c}" not in low and f"background: {c}" not in low, (k, c)
        assert "<title>" in svg, k  # hover titles on marks
        assert sc.CAPTIONS[k].strip(), k


def test_legends_name_every_model_by_its_entity_color():
    for k in ("figures/api/extraction-score-by-type.svg", "figures/api/cost-per-document.svg"):
        svg = SVGS[k]
        for fam in ("DeepSeek-V4.1-Flash", "Granite-4.2-8B", "Qwen3-8B", "Qwen3.7-Flash"):
            cls = viz.ENTITY[fam]
            assert re.search(rf'<rect class="{cls}"[^>]*/><text class="lbl"[^>]*>{re.escape(fam)}</text>', svg), (k, fam)
    cal = SVGS["figures/api/sorter-calibration.svg"]
    for fam in ("DeepSeek-V4.1-Flash", "Granite-4.2-8B", "Qwen3.7-Flash"):
        assert f'class="line {viz._LN[viz.ENTITY[fam]]}"' in cal
        assert f">{fam}</text>" in cal  # direct label, not color alone


def test_extraction_and_cost_tables_match_hub():
    score = _rows(TABLES["figures/api/extraction-score-by-type.svg"])
    cost = _rows(TABLES["figures/api/cost-per-document.svg"])
    recs = [r for c in sc.ORDER for r in list(D["api"]["tasks"][D["labels"][c].lower()].values())]
    r50 = [D["api"]["route50"][D["labels"][c].lower()] for c in sc.ORDER]
    want_scores = sorted(f"{r['score']:.4f}" for r in recs + r50)
    assert sorted(r[3] for r in score) == want_scores
    assert sorted(r[4] for r in cost) == sorted(f"${r['cost'] / r['n'] * 1000:.2f}" for r in recs + r50)
    assert sorted(r[3] for r in cost) == sorted(f"${r['cost']:.6f}" for r in recs + r50)
    # the one leg eval-environment files under Qwen3-8B is labeled by the model it logged
    merger = [r for r in score if r[0] == D["labels"]["merger_agreement"]]
    assert not any(r[1] == "Qwen3-8B" for r in merger)
    for label in (r[1] for r in merger):
        assert label.split(" · ")[0] in sc.MODEL_NAME.values()
    for row in score:  # every score is drawn as a bar tip label
        assert f">{float(row[3]):.2f}</text>" in SVGS["figures/api/extraction-score-by-type.svg"]


def test_sorter_tables_match_hub():
    sub = _rows(TABLES["figures/api/sorter-subclass-accuracy.svg"])
    got = {(r[0], r[1]): (int(r[2]), int(r[3]), r[4]) for r in sub}
    for m, s in D["api"]["sorter"].items():
        name = sc.MODEL_NAME[m]
        for c, col in s["collapse"].items():
            assert got[(D["labels"][c], name)] == (col["n"], col["correct"], f"{col['correct'] / col['n'] * 100:.1f}%")
    gate = D["mb"]["armB"]["gates"]["P0_subclass"]["threshold"]
    assert f"P0 subclass gate {gate * 100:.0f}%" in SVGS["figures/api/sorter-subclass-accuracy.svg"]
    cal = _rows(TABLES["figures/api/sorter-calibration.svg"])
    want = sorted((sc.MODEL_NAME[m], b["n"], f"{b['conf'] * 100:.2f}%", f"{b['acc'] * 100:.2f}%", f"{s['ece']:.4f}")
                  for m, s in D["api"]["sorter"].items() for b in s["bins"])
    assert sorted((r[0], int(r[2]), r[3], r[4], r[6]) for r in cal) == want


def test_modernbert_tables_match_hub():
    mb = D["mb"]
    rec = _rows(TABLES["figures/modernbert/doc-type-recall.svg"])
    for key, lab in sc.CHECKPOINTS:
        assert ["All documents (accuracy)", lab, "—", str(mb[key]["n"]), f"{mb[key]['acc'] * 100:.2f}%"] in rec
        for c, pc in mb[key]["per_class"].items():
            assert [D["labels"][c], lab, str(pc["correct"]), str(pc["n"]),
                    f"{pc['correct'] / pc['n'] * 100:.2f}%"] in rec
    risk = _rows(TABLES["figures/modernbert/selective-risk.svg"])
    assert len(risk) == len(mb["armB"]["risk"])
    for row, (t, cov, acc, n) in zip(risk, mb["armB"]["risk"]):
        assert row[:4] == [f"{t:.2f}", str(n), f"{cov * 100:.2f}%", f"{acc * 100:.2f}%"]
        assert float(row[4].rstrip("%")) <= acc * 100  # Wilson lower bound sits under the point estimate
    pick = min(mb["armB"]["risk"], key=lambda r: abs(r[0] - mb["armB"]["pick"]))
    assert f"Threshold {pick[0]:.2f}: {pick[1] * 100:.0f}% accepted at {pick[2] * 100:.1f}% accuracy" in \
        SVGS["figures/modernbert/selective-risk.svg"]
    coll = _rows(TABLES["figures/modernbert/subclass-collapse.svg"])
    col = mb["armB"]["eda"]["collapse"]
    for row, c in zip(coll, sc.ORDER):
        x = col[c]
        assert row[:4] == [D["labels"][c], str(x["n"]), str(x["correct"]), f"{x['correct'] / x['n'] * 100:.1f}%"]
        assert row[4].startswith(x["top_pred"][0].replace("_", " ")) and f"({x['top_pred'][1]}, " in row[4]
        assert row[5].startswith(x["top_true"][0].replace("_", " ")) and f"({x['top_true'][1]}, " in row[5]


@pytest.mark.parametrize("key", KEYS)
def test_text_stays_inside_the_card(key):
    """Estimated text extents (kit's text_w) stay within the viewBox — the Chromium audit is the full check."""
    svg = SVGS[key]
    W, H = (float(v) for v in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg).groups())
    for m in re.finditer(r'<text class="(\w+)" x="([\d.]+)" y="([\d.]+)"(?: text-anchor="(\w+)")?>(?:<title>.*?</title>)?([^<]*)</text>', svg):
        cls, x, y, anchor, txt = m.group(1), float(m.group(2)), float(m.group(3)), m.group(4) or "start", m.group(5)
        px = 15 if cls == "title" else 11 if cls in ("tick", "reflbl", "axt") else 12
        w = viz.text_w(txt, px) * (1.08 if cls in ("grp", "title") else 1)
        x0 = x - w if anchor == "end" else x - w / 2 if anchor == "middle" else x
        assert x0 >= 0 and x0 + w <= W + 1 and 0 < y <= H, (key, txt)
