"""Typeset PDF of the plain-language reader report (``READER-REPORT.pdf``).

The PDF is a translation of ``READER-REPORT.md``: the same section text (from
``grid_reader._sections``), rendered to print HTML with vector charts and printed by
headless Chrome. ``sandbox run card --master`` rebuilds it with the Markdown and the
notebook. Because PDF bytes are not reproducible across machines, freshness is tracked
by ``READER-REPORT.pdf.sha256``: the fingerprint of the inputs the PDF was printed
from (report text, chart data, stylesheet, template version). The staleness test
compares that fingerprint with the current report, so an updated report with an
un-rebuilt PDF fails the suite.

Chrome is located via ``SANDBOX_CHROME`` or the usual install paths; without it the
Markdown and notebook are still written and the PDF step is skipped with a warning.
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from mailroom_sandbox.job import grid_master as gm
from mailroom_sandbox.job import grid_reader as gr

TEMPLATE_VERSION = "1"
LONG_TABLE_ROWS = 9  # longer tables may break across pages; shorter ones stay whole with their lead-in
TITLE = "Document Extraction on Low-Cost Cloud GPUs"

_CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
)

# Print palette: deep navy ink, one blue accent, cool neutrals.
CSS = """
:root {
  --ink: #1d2733; --muted: #5d6877; --rule: #d8dee6; --accent: #1f4e79;
  --accent-soft: #edf2f8; --zebra: #f7f9fb; --note: #f4f7f5; --note-rule: #2f8f83;
}
@page {
  size: Letter; margin: 0.8in 0.85in 0.85in;
  @bottom-left { content: "TITLE_PLACEHOLDER"; font: 500 7.5pt "Avenir Next", "Helvetica Neue", "Open Sans", sans-serif;
                 color: #8a94a1; letter-spacing: 0.02em; }
  @bottom-right { content: "Page " counter(page) " of " counter(pages);
                  font: 500 7.5pt "Avenir Next", "Helvetica Neue", "Open Sans", sans-serif; color: #8a94a1; }
}
@page :first { @bottom-left { content: none; } }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  margin: 0; color: var(--ink);
  font: 10.3pt/1.52 Charter, "Charis SIL", "Iowan Old Style", Georgia, serif;
  font-variant-numeric: lining-nums; hyphens: auto; orphans: 3; widows: 3;
}
.eyebrow {
  font: 600 7.8pt "Avenir Next", "Helvetica Neue", "Open Sans", sans-serif; letter-spacing: 0.16em;
  text-transform: uppercase; color: var(--accent); margin: 0 0 8pt;
}
h1 {
  font: 600 23pt/1.15 "Avenir Next", "Helvetica Neue", "Open Sans", sans-serif; letter-spacing: -0.01em;
  margin: 0 0 10pt; color: var(--ink);
}
.dek { font-size: 11.6pt; line-height: 1.5; color: #333d49; margin: 0 0 10pt; }
.datanote {
  font: 8.8pt/1.45 "Avenir Next", "Helvetica Neue", "Open Sans", sans-serif; color: #2c3a37;
  background: var(--note); border-left: 2.5pt solid var(--note-rule); padding: 6pt 9pt; margin: 0 0 16pt;
}
.datanote p { margin: 0; }
h2 {
  font: 600 12.6pt/1.25 "Avenir Next", "Helvetica Neue", "Open Sans", sans-serif; color: var(--accent);
  margin: 20pt 0 7pt; padding-bottom: 4pt; border-bottom: 0.75pt solid var(--rule);
}
p { margin: 0 0 7pt; }
strong { font-weight: 700; color: #121a24; }
code {
  font: 8.4pt "SF Mono", Menlo, monospace; background: #f1f3f6; padding: 0.5pt 3pt; border-radius: 2pt;
}
.findings {
  background: var(--accent-soft); border-radius: 4pt; padding: 10pt 14pt 6pt 12pt; margin: 0 0 6pt;
}
.findings h2 { margin-top: 0; border-bottom-color: #cfdbe8; }
.findings ol { counter-reset: f; list-style: none; padding: 0; margin: 0; }
.findings li { counter-increment: f; position: relative; padding-left: 20pt; margin: 0 0 6.5pt; }
.findings li::before {
  content: counter(f); position: absolute; left: 0; top: 1.5pt; width: 13pt; height: 13pt; border-radius: 50%;
  background: var(--accent); color: #fff; font: 600 7.4pt/13pt "Avenir Next", "Open Sans", sans-serif; text-align: center;
}
ul { padding-left: 14pt; margin: 0 0 8pt; }
ul li { margin: 0 0 5pt; }
ul li::marker { color: var(--accent); }
table {
  width: 100%; border-collapse: collapse; margin: 4pt 0 11pt;
  font: 8.5pt/1.38 "Avenir Next", "Helvetica Neue", "Open Sans", sans-serif; font-variant-numeric: tabular-nums;
}
thead th {
  font-weight: 600; color: var(--accent); text-align: left; vertical-align: bottom;
  border-bottom: 1.2pt solid var(--accent); padding: 4pt 6pt;
}
tbody td { padding: 3.6pt 6pt; border-bottom: 0.5pt solid var(--rule); vertical-align: top; }
tbody tr:nth-child(even) td { background: var(--zebra); }
tbody tr:last-child td { border-bottom: 0.9pt solid #b9c3cf; }
td:first-child { font-weight: 500; min-width: 6.4em; }
tr { break-inside: avoid; }
thead { display: table-header-group; }
.keep { break-inside: avoid; }
h2, .lead { break-after: avoid; }
figure { margin: 6pt 0 14pt; break-inside: avoid; }
figure svg { width: 100%; height: auto; display: block; }
figcaption {
  font: italic 8.6pt/1.4 Charter, "Charis SIL", Georgia, serif; color: var(--muted); margin-top: 4pt;
}
.small { font: 8.6pt/1.45 "Avenir Next", "Helvetica Neue", "Open Sans", sans-serif; color: var(--muted); }
""".replace("TITLE_PLACEHOLDER", TITLE)


def pdf_paths(repo: Path | None = None) -> dict[str, Path]:
    base = gr.reader_paths(repo)["md"].parent
    return {"pdf": base / f"{gr.READER_STEM}.pdf", "sha": base / f"{gr.READER_STEM}.pdf.sha256"}


def fingerprint(data: Mapping[str, Any]) -> str:
    """Hash of everything the PDF is printed from (text, chart data, styles), not of PDF bytes."""
    h = hashlib.sha256()
    for part in (TEMPLATE_VERSION, CSS, gr.render_reader_md(data), json.dumps(gr._chart_rows(data), sort_keys=True),
                 json.dumps(gr.CHART_COLORS, sort_keys=True)):
        h.update(part.encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def _md() -> Any:
    from markdown_it import MarkdownIt

    return MarkdownIt("commonmark", {"typographer": False}).enable("table")


def _blocks(lines: list[str]) -> list[str]:
    """Split Markdown lines into blank-line-separated blocks."""
    blocks, cur = [], []
    for line in lines:
        if line.strip():
            cur.append(line)
        elif cur:
            blocks.append("\n".join(cur))
            cur = []
    if cur:
        blocks.append("\n".join(cur))
    return blocks


def _keep_groups(blocks: list[str]) -> list[list[str]]:
    """Bind each lead-in paragraph to the table that follows it so neither is stranded across pages."""
    groups: list[list[str]] = []
    pending: list[str] = []
    for b in blocks:
        if b.startswith("|"):
            groups.append(pending + [b])
            pending = []
        else:
            if pending:
                groups.append(pending)
            pending = [b]
    if pending:
        groups.append(pending)
    return groups


def _svg(fig: Any) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", metadata={"Date": None})
    import matplotlib.pyplot as plt

    plt.close(fig)
    svg = buf.getvalue()
    return svg[svg.index("<svg"):]


def _chart_style() -> dict[str, Any]:
    return {
        "svg.fonttype": "none", "svg.hashsalt": "reader-report",
        "font.family": ["Avenir Next", "Helvetica Neue", "Open Sans", "DejaVu Sans"], "font.size": 8.5,
        "axes.edgecolor": "#b9c3cf", "axes.labelcolor": "#3b4652", "axes.titlecolor": "#1d2733",
        "axes.titlesize": 9.5, "axes.titleweight": 600, "axes.titlelocation": "left", "axes.titlepad": 8,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.axisbelow": True,
        "grid.color": "#e6eaef", "grid.linewidth": 0.6, "xtick.color": "#5d6877", "ytick.color": "#5d6877",
        "xtick.major.size": 0, "ytick.major.size": 0, "legend.frameon": False,
    }


def _charts(data: Mapping[str, Any]) -> tuple[str, str]:
    import logging

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Labels are emitted as SVG text and set by Chrome in the page fonts; matplotlib only needs metrics.
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    rows = gr._chart_rows(data)
    names = [n for _, n in gr.RUNS]
    runs = {r["run"]: r for r in rows}
    colors = [gr.CHART_COLORS[n] for n in names if n in runs]
    present = [n for n in names if n in runs]
    with plt.rc_context(_chart_style()):
        fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.5))
        for ax, key, title, fmt, scale in (
            (axes[0], "run_docs_per_min", "Documents per minute  (higher is better)", "{:.1f}", 1.0),
            (axes[1], "run_cost_per_doc", "GPU cost per document, cents  (lower is better)", "{:.3f}", 100.0),
        ):
            vals = [runs[n][key] * scale for n in present]
            bars = ax.bar(present, vals, color=colors, width=0.62)
            ax.set_xticks(range(len(present)), [n.removeprefix("Experiment ") for n in present])
            ax.set_xlabel("Experiment")
            ax.set_title(title)
            ax.grid(axis="x", visible=False)
            ax.set_ylim(0, max(vals) * 1.18)
            for b, v in zip(bars, vals, strict=True):
                ax.annotate(fmt.format(v), (b.get_x() + b.get_width() / 2, v), xytext=(0, 3),
                            textcoords="offset points", ha="center", fontsize=7.5, color="#3b4652")
        fig.tight_layout(w_pad=2.5)
        speed = _svg(fig)

        types = list(dict.fromkeys(r["doc_type"] for r in rows))[::-1]
        fig, ax = plt.subplots(figsize=(6.8, 3.3))
        h = 0.8 / len(present)
        for i, n in enumerate(present):
            vals = [next((r["score"] for r in rows if r["run"] == n and r["doc_type"] == t), 0.0) for t in types]
            ys = [y - 0.4 + h * (len(present) - 1 - i) + h / 2 for y in range(len(types))]
            ax.barh(ys, vals, height=h * 0.9, color=gr.CHART_COLORS[n], label=n)
        ax.set_yticks(range(len(types)), types)
        ax.set_xlabel("Score, 0–1 (scales differ by document type)")
        ax.set_title("Accuracy by document type and experiment")
        ax.grid(axis="y", visible=False)
        ax.legend(loc="upper center", ncols=4, fontsize=7.5, handlelength=1.0, columnspacing=1.2,
                  bbox_to_anchor=(0.5, -0.2))
        fig.tight_layout()
        quality = _svg(fig)
    return speed, quality


def _report_date(data: Mapping[str, Any]) -> str:
    stamps = [c.get("generated_at") for v in data["cards"].values() for c in v.values() if c.get("generated_at")]
    if not stamps:
        return ""
    d = datetime.fromisoformat(max(stamps))
    return f"{d.strftime('%B')} {d.year}"


def render_reader_html(data: Mapping[str, Any]) -> str:
    md = _md()
    speed, quality = _charts(data)
    figures = {
        "## Speed and cost by experiment": (speed, "Figure 1. Throughput and GPU cost per document for each experiment."),
        "## Results by document type": (
            quality, "Figure 2. Accuracy by document type and experiment. Each document type has its own scale; "
            "compare bars within a type, not across types."),
    }
    out: list[str] = []
    for heading, body in gr._sections(data):
        if not heading:  # title block: H1, dek, data note
            blocks = _blocks(body)
            title = blocks[0].lstrip("# ").strip()
            out.append(f'<p class="eyebrow">Research brief · {html.escape(_report_date(data))}</p>')
            out.append(f"<h1>{html.escape(title)}</h1>")
            out.append(f'<div class="dek">{md.render(blocks[1])}</div>')
            out += [f'<div class="datanote">{md.render(b)}</div>' for b in blocks[2:]]
            continue
        h2 = f"<h2>{html.escape(heading.lstrip('# ').strip())}</h2>"
        groups = _keep_groups(_blocks(body))
        if heading == "## Key findings":
            out.append(f'<section class="findings keep">{h2}{md.render(chr(10).join(groups[0]))}</section>')
            continue
        parts = [_group_html(md, g, h2 if i == 0 else "") for i, g in enumerate(groups)]
        if heading == "## Experiment cross-reference":
            parts = [p.replace('<div class="keep">', '<div class="keep small">', 1) if i else p
                     for i, p in enumerate(parts)]
        out.append("<section>" + "".join(parts) + "</section>")
        if heading in figures:
            svg, cap = figures[heading]
            out.append(f"<figure>{svg}<figcaption>{html.escape(cap)}</figcaption></figure>")
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(TITLE)}</title><style>{CSS}</style></head><body>"
        + "\n".join(out)
        + "</body></html>\n"
    )


def _group_html(md: Any, group: list[str], h2: str) -> str:
    """A lead-in + table pair stays on one page; a long table flows (header repeats) under its kept lead-in."""
    table = group[-1] if group[-1].startswith("|") else None
    if table and table.count("\n") - 1 > LONG_TABLE_ROWS:
        lead = "\n\n".join(group[:-1])
        return f'<div class="keep lead">{h2}{md.render(lead) if lead else ""}</div>{md.render(table)}'
    return f'<div class="keep">{h2}{md.render(chr(10).join(group))}</div>'


def find_chrome() -> str | None:
    env = os.environ.get("SANDBOX_CHROME")
    if env and Path(env).exists():
        return env
    for c in _CHROME_CANDIDATES:
        if Path(c).exists():
            return c
        found = shutil.which(c)
        if found:
            return found
    return None


def _print_with_chrome(chrome: str, src: Path, out: Path, profile: Path, timeout: float = 120.0) -> None:
    """Headless print; returns once the PDF is complete.

    Launched from Python, headless Chrome writes the PDF and then can linger instead of
    exiting, so completion is the file reaching a stable size, after which Chrome is stopped.
    """
    import time

    proc = subprocess.Popen(
        [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--no-first-run",
         f"--user-data-dir={profile}", f"--print-to-pdf={out}", src.as_uri()],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline, last, stable_since = time.monotonic() + timeout, -1, None
    try:
        while time.monotonic() < deadline:
            size = out.stat().st_size if out.exists() else 0
            if size and size == last:
                stable_since = stable_since or time.monotonic()
                if proc.poll() is not None or time.monotonic() - stable_since >= 1.0:
                    return
            else:
                stable_since = None
            if proc.poll() is not None and not size:
                raise RuntimeError(f"Chrome exited ({proc.returncode}) without writing a PDF")
            last = size
            time.sleep(0.25)
        raise TimeoutError(f"Chrome did not finish the PDF within {timeout:.0f} s")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


def write_pdf(repo: Path | None = None, data: Mapping[str, Any] | None = None) -> Path | None:
    """Print the reader report to PDF and record its input fingerprint; None when Chrome is absent."""
    chrome = find_chrome()
    if not chrome:
        return None
    data = data or gm.collect_master(repo)
    paths = pdf_paths(repo)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "reader.html"
        src.write_text(render_reader_html(data), encoding="utf-8")
        out = Path(tmp) / "reader.pdf"
        _print_with_chrome(chrome, src, out, Path(tmp) / "profile")
        shutil.copyfile(out, paths["pdf"])
    paths["sha"].write_text(fingerprint(data) + "\n", encoding="utf-8")
    return paths["pdf"]
