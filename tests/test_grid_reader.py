"""The plain-language reader report stays in sync with the cards and free of internal shorthand."""

from __future__ import annotations

import json
import re

from mailroom_sandbox.job import grid_master, grid_reader


def test_reader_md_is_current():
    paths = grid_reader.reader_paths()
    expected = grid_reader.render_reader_md(grid_master.collect_master())
    assert paths["md"].read_text(encoding="utf-8") == expected, "run: sandbox run card --master"


def test_reader_notebook_text_is_current_and_charts_are_rendered():
    nb = json.loads(grid_reader.reader_paths()["ipynb"].read_text(encoding="utf-8"))
    md_cells = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "markdown"]
    report = grid_reader.render_reader_md(grid_master.collect_master())
    for text in md_cells:
        if not text.startswith("The charts below"):
            assert text in report
    pngs = [o for c in nb["cells"] for o in c.get("outputs", []) if "image/png" in o.get("data", {})]
    assert len(pngs) == 2


def test_reader_body_has_no_internal_shorthand():
    md = grid_reader.render_reader_md(grid_master.collect_master())
    body = md.split("## Experiment cross-reference")[0]
    for pattern in (r"SAND-\d", r"×L4", r"\bC(8|32)\b", r"\bn=\d", "†", "posture", "specialist"):
        assert not re.search(pattern, body), pattern
    assert "No American Family Insurance data was used or shared." in body
    assert "| **All experiments** | 1,050 |" in md


def test_reader_pdf_is_printed_from_the_current_report():
    from mailroom_sandbox.job import grid_reader_pdf

    paths = grid_reader_pdf.pdf_paths()
    assert paths["pdf"].read_bytes()[:5] == b"%PDF-"
    recorded = paths["sha"].read_text(encoding="utf-8").strip()
    assert recorded == grid_reader_pdf.fingerprint(grid_master.collect_master()), (
        "READER-REPORT.pdf is stale: run sandbox run card --master (needs Chrome; SANDBOX_CHROME overrides)"
    )


def test_reader_pdf_html_keeps_every_heading_with_its_content():
    from mailroom_sandbox.job import grid_reader_pdf

    page = grid_reader_pdf.render_reader_html(grid_master.collect_master())
    assert page.count("<h2>") == 10
    assert page.count("<h2>") == len(re.findall(r'class="(?:findings )?keep[^"]*">(?:<div[^>]*>)?<h2>', page))
    assert page.count("<figure><svg") == 2
    assert "Research brief · " in page
