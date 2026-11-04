"""Static GitHub Pages site for LLM-Mailroom-Services/mailroom-issues (served from ``main`` → ``/docs``).

Called by ``export_hub_reports.py``. It renders the three generated reports to HTML
with every figure inlined, plus a landing page, from the same in-memory markdown and
SVG the exporter writes to ``reports/`` — nothing is recomputed here.

mailroom-issues holds no code (its law #1), so the site is plain HTML + CSS: no
JavaScript, no external fonts or CDNs, no build step on GitHub's side (``.nojekyll``).
"""
from __future__ import annotations

import html
import posixpath
import re

from markdown_it import MarkdownIt

SITE_URL = "https://llm-mailroom-services.github.io/mailroom-issues/"
REPO_BLOB = "https://github.com/LLM-Mailroom-Services/mailroom-issues/blob/main/"
REPO_TREE = "https://github.com/LLM-Mailroom-Services/mailroom-issues/tree/main/"
SANDBOX_BLOB = "https://github.com/Exios66/local-mailroom-sandbox/blob/main/"

# (source markdown, page, nav label, card blurb)
REPORTS = [
    ("MASTER-REPORT.md", "master.html", "Master report",
     "Where every front stands: the hosted-API leg, the Modal + vLLM leg (SAND-032), the ModernBERT intake "
     "classifier, the cross-leg verdict, and the report audit."),
    ("COST-COMPARISON-MODAL-VS-API.md", "cost-comparison.html", "Cost comparison",
     "Self-hosted Qwen3-8B-AWQ on Modal against four hosted API models: cost and quality per document, the same "
     "model on both routes, break-even volumes and the optimal deployment, sorter routes and spend."),
    ("MODAL-VLLM-GPU-REPORT.md", "gpu-economics.html", "GPU economics",
     "The Modal + vLLM leg in depth: cost per 1M tokens, where the GPU spend went, warm vs cold fleets, "
     "GPU utilization, and what adding the second L4 did."),
]
PAGE_OF = {src: page for src, page, _, _ in REPORTS}

CSS = """
:root {
  /* One dark, high-contrast theme for the whole site, matching the figures (the /dataviz reference
     palette's dark chrome: page #0d0d0d, surface #1a1a19). Text contrast on the page: ink 19.4:1,
     ink-2 13.2:1, muted 8.1:1, links 8.9:1. */
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff; --ink-2: #d6d5cc; --muted: #a9a89f;
  --grid: #2c2c2a; --axis: #4a4a46; --ring: rgba(255,255,255,0.14); --wash: #262624; --accent: #7cb4f2;
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --mono: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--page); color: var(--ink); font-family: var(--sans); font-size: 16px;
  line-height: 1.6; padding: 0 16px 64px; overflow-wrap: break-word; }
a { color: var(--accent); text-underline-offset: 2px; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }
code { font-family: var(--mono); font-size: .88em; background: var(--wash); padding: .08em .35em; border-radius: 4px; }
.wrap { max-width: 1160px; margin: 0 auto; }
.skip { position: absolute; left: -9999px; }
.skip:focus { left: 16px; top: 8px; background: var(--surface); padding: 6px 10px; z-index: 10; }
header.site { border-bottom: 1px solid var(--grid); margin-bottom: 28px; }
header.site .row { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 16px; padding: 14px 0; }
header.site .brand { font-weight: 650; color: var(--ink); text-decoration: none; margin-right: auto; }
header.site nav { display: flex; flex-wrap: wrap; gap: 2px; }
header.site nav a { color: var(--ink-2); text-decoration: none; font-size: 14px; padding: 6px 10px; border-radius: 7px; }
header.site nav a:hover { background: var(--wash); color: var(--ink); }
header.site nav a[aria-current="page"] { background: var(--ink); color: var(--surface); }
.eyebrow { font-family: var(--mono); font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-2); }
h1 { font-size: clamp(28px, 5vw, 42px); line-height: 1.1; letter-spacing: -.02em; margin: 6px 0 14px; text-wrap: balance; }
h2 { font-size: 24px; line-height: 1.25; letter-spacing: -.01em; margin: 44px 0 12px; padding-top: 8px;
  border-top: 1px solid var(--grid); text-wrap: balance; }
h3 { font-size: 18px; line-height: 1.3; margin: 30px 0 8px; }
h2 a.anchor, h3 a.anchor { color: var(--muted); text-decoration: none; margin-left: 6px; font-weight: 400; opacity: 0; }
h2:hover a.anchor, h3:hover a.anchor, a.anchor:focus { opacity: 1; }
p, li { max-width: 80ch; }
.lede { color: var(--ink-2); font-size: 17px; max-width: 72ch; }
nav.toc { font-size: 14px; background: var(--surface); border: 1px solid var(--ring); border-radius: 10px;
  padding: 12px 16px; margin: 18px 0 8px; }
nav.toc ul { margin: 6px 0 0; padding: 0; list-style: none; display: flex; flex-wrap: wrap; gap: 4px 18px; }
nav.toc a { color: var(--ink-2); text-decoration: none; }
nav.toc a:hover { color: var(--ink); text-decoration: underline; }
article > p:first-of-type em { color: var(--ink-2); font-size: 14px; }
.table-scroll { overflow-x: auto; margin: 14px 0 20px; border: 1px solid var(--ring); border-radius: 10px; background: var(--surface); }
table { border-collapse: collapse; width: 100%; font-size: 14px; font-variant-numeric: tabular-nums; }
th, td { padding: 8px 12px; border-bottom: 1px solid var(--grid); vertical-align: top; }
th { text-align: left; font-weight: 600; background: var(--wash); white-space: nowrap; }
tr:last-child td { border-bottom: 0; }
figure.fig { margin: 18px 0 24px; }
figure.fig .frame { overflow-x: auto; width: fit-content; max-width: 100%; border: 1px solid var(--ring); border-radius: 10px; background: var(--surface); }
figure.fig .frame > svg { display: block; height: auto; }  /* width set per chart: its natural width, scaled down to fit */
figure.fig figcaption { font-size: 13px; color: var(--muted); margin-top: 6px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin: 22px 0 30px; }
.tile { background: var(--surface); border: 1px solid var(--ring); border-radius: 10px; padding: 16px 18px; }
.tile .label { font-size: 13px; color: var(--ink-2); }
.tile .value { font-size: 30px; font-weight: 650; letter-spacing: -.02em; line-height: 1.15; margin: 4px 0; }
.tile .sub { font-size: 13px; color: var(--muted); }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)); gap: 14px; }
.card { display: block; background: var(--surface); border: 1px solid var(--ring); border-radius: 12px; padding: 18px 20px;
  color: var(--ink); text-decoration: none; }
.card:hover { border-color: var(--axis); }
.card h2 { border: 0; margin: 0 0 6px; padding: 0; font-size: 19px; }
.card p { margin: 0 0 10px; color: var(--ink-2); font-size: 15px; }
.card .more { font-size: 14px; color: var(--accent); }
footer.site { margin-top: 48px; padding-top: 16px; border-top: 1px solid var(--grid); color: var(--muted); font-size: 13px; }
footer.site p { max-width: none; }
"""


def _slug(text: str, seen: set[str]) -> str:
    base = re.sub(r"[^\w\s-]", "", html.unescape(re.sub(r"<[^>]+>", "", text)).lower(), flags=re.UNICODE)
    base = re.sub(r"\s+", "-", base.strip()) or "section"
    slug, i = base, 2
    while slug in seen:
        slug, i = f"{base}-{i}", i + 1
    seen.add(slug)
    return slug


def _svg_text(body) -> str:
    s = body.decode("utf-8") if isinstance(body, bytes) else body
    return re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", s)


def _href(href: str) -> str:
    """Rewrite a link from a report (relative to mailroom-issues/reports/) for the site."""
    if re.match(r"^[a-z][a-z0-9+.-]*:", href) or href.startswith("#"):
        return href
    path, _, frag = href.partition("#")
    frag = f"#{frag}" if frag else ""
    if not path:
        return href
    if path in PAGE_OF:
        return PAGE_OF[path] + frag
    if path == "README.md":
        return "../index.html" + frag
    target = posixpath.normpath(posixpath.join("reports", path))
    return (REPO_TREE if path.endswith("/") else REPO_BLOB) + target + frag


def render_report(md_text: str, files: dict) -> tuple[str, str, list[tuple[str, str]]]:
    """Markdown → (title, article HTML, [(h2 id, h2 text)])."""
    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    out = md.render(md_text)

    def figure(m):
        src, alt = html.unescape(m.group(1)), m.group(2)
        body = files.get(src)
        if body is None:
            raise SystemExit(f"report references a missing figure: {src}")
        svg = _svg_text(body)
        w = int(float(re.search(r'<svg\b[^>]*?\swidth="([\d.]+)"', svg).group(1)))
        svg = re.sub(r"<svg\b", f'<svg style="width:min(100%,{w}px);min-width:{min(w, 560)}px"', svg, count=1)
        # the chart carries its own title; a caption only when the alt text says something the chart doesn't
        cap = "" if html.unescape(alt) in html.unescape(svg) else f"<figcaption>{alt}</figcaption>"
        return f'<figure class="fig"><div class="frame">{svg}</div>{cap}</figure>'
    out = re.sub(r'<p><img src="([^"]+)" alt="([^"]*)"\s*/?></p>', figure, out)
    if "<img " in out:
        raise SystemExit("an image was not inlined (only whole-paragraph figures are supported)")
    out = re.sub(r'href="([^"]+)"', lambda m: f'href="{html.escape(_href(html.unescape(m.group(1))), quote=True)}"', out)
    for src, page, label, _ in REPORTS:  # a bare filename as link text reads as the report's name on the site
        out = re.sub(rf'(<a href="{re.escape(page)}[^"]*">){re.escape(src)}</a>', rf"\g<1>{label}</a>", out)
    out = out.replace("<table>", '<div class="table-scroll"><table>').replace("</table>", "</table></div>")
    seen: set[str] = set()
    toc: list[tuple[str, str]] = []

    def heading(m):
        level, inner = m.group(1), m.group(2)
        sid = _slug(inner, seen)
        if level == "2":
            toc.append((sid, re.sub(r"<[^>]+>", "", inner)))
        return f'<h{level} id="{sid}">{inner}<a class="anchor" href="#{sid}" aria-label="Link to this section">#</a></h{level}>'
    out = re.sub(r"<h([23])>(.*?)</h\1>", heading, out)
    m = re.search(r"<h1>(.*?)</h1>", out)
    title = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))) if m else "Report"
    return title, out, toc


def _page(title: str, body: str, *, current: str | None, depth: int, provenance: str) -> str:
    up = "../" * depth
    cur = ' aria-current="page"'
    nav = "".join(f'<a href="{up}reports/{page}"{cur if page == current else ""}>{label}</a>'
                  for _, page, label, _ in REPORTS)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>{html.escape(title)} · Mailroom evaluation reports</title>
<meta name="description" content="Cross-repository evaluation reports for the LLM-Mailroom constellation.">
<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site"><div class="wrap row">
<a class="brand" href="{up}index.html">Mailroom evaluation reports</a>
<nav aria-label="Reports">{nav}<a href="{REPO_TREE}reports">Markdown sources</a></nav>
</div></header>
<div class="wrap">
{body}
<footer class="site">
<p>Generated from the cross-checked reports hub by <a href="{SANDBOX_BLOB}reports/dashboard/export_hub_reports.py">export_hub_reports.py</a> in local-mailroom-sandbox. Sources: {html.escape(provenance)}. Static HTML, no scripts; do not hand-edit — regenerate from the sandbox.</p>
</footer>
</div>
</body>
</html>
"""


def build(files: dict, stats: dict, provenance: str) -> dict[str, str]:
    """Site files keyed by their path under ``docs/``."""
    site: dict[str, str] = {".nojekyll": ""}
    for src, page, label, _ in REPORTS:
        title, article, toc = render_report(files[src], files)
        toc_html = "".join(f'<li><a href="#{sid}">{html.escape(text)}</a></li>' for sid, text in toc)
        toc_nav = (f'<nav class="toc" aria-label="On this page"><strong>On this page</strong>'
                   f"<ul>{toc_html}</ul></nav>")
        # the contents box goes right after the report's provenance line (the first paragraph after the title)
        article = re.sub(r"(</h1>\s*<p>.*?</p>)", lambda m: m.group(1) + toc_nav, article, count=1, flags=re.S)
        body = f'<article id="main">{article}</article>'
        site[f"reports/{page}"] = _page(title, body, current=page, depth=1, provenance=provenance)

    tiles = "".join(
        f'<div class="tile"><div class="label">{html.escape(t["label"])}</div><div class="value">{html.escape(t["value"])}</div>'
        f'<div class="sub">{html.escape(t["sub"])}</div></div>' for t in stats["tiles"])
    cards = "".join(
        f'<a class="card" href="reports/{page}"><h2>{html.escape(label)}</h2><p>{html.escape(blurb)}</p>'
        f'<span class="more">Open {html.escape(label)} →</span></a>'
        for _, page, label, blurb in REPORTS)
    index_body = f"""<main id="main">
<div class="eyebrow">LLM-Mailroom-Services · mailroom-issues</div>
<h1>Mailroom evaluation reports</h1>
<p class="lede">Cross-repository findings for the LLM-Mailroom pipeline: the hosted-API leg (eval-environment), self-hosted Qwen3-8B-AWQ on Modal L4 GPUs with vLLM (local-mailroom-sandbox, SAND-032), and the ModernBERT intake classifier (mailroom-ml). Every number is quoted from a tracked source file and cross-checked before it is published here.</p>
<div class="tiles">{tiles}</div>
<div class="cards">{cards}</div>
</main>"""
    site["index.html"] = _page("Home", index_body, current=None, depth=0, provenance=provenance)
    return site
