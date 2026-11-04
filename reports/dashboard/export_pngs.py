#!/usr/bin/env python3
"""Render every report figure in mailroom-issues to a presentation-ready PNG.

    python reports/dashboard/export_pngs.py --reports ../mailroom-issues/reports           # write reports/viz/
    python reports/dashboard/export_pngs.py --reports ../mailroom-issues/reports --check   # exit 1 if stale

Each ``reports/figures/**/*.svg`` becomes ``reports/viz/<same path>.png``, rendered in headless Chromium
at 2× device pixels (a 1,100 px figure becomes 2,200 px wide), so it stays sharp on a projected slide.
The figures are self-contained dark cards, so the PNGs carry their own background. PNG bytes vary with
the renderer, so staleness is judged by ``reports/viz/MANIFEST.json``, which records the SHA-256 of the
SVG each PNG was rendered from; ``--check`` needs no browser. Writing needs Playwright with Chromium
(``CHROMIUM_PATH=/path/to/chromium`` selects a pre-installed build).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCALE = 2


def sources(reports: pathlib.Path) -> dict[str, str]:
    """PNG path (relative to reports/) → SHA-256 of its source SVG."""
    out = {}
    for svg in sorted((reports / "figures").rglob("*.svg")):
        rel = svg.relative_to(reports / "figures").with_suffix(".png")
        out[f"viz/{rel.as_posix()}"] = hashlib.sha256(svg.read_bytes()).hexdigest()
    return out


def render(reports: pathlib.Path, todo: list[str]) -> None:
    from playwright.sync_api import sync_playwright  # noqa: PLC0415 — only needed to write

    with sync_playwright() as p:
        # CHROMIUM_PATH points at a pre-installed Chromium when Playwright's own download is absent
        exe = os.environ.get("CHROMIUM_PATH")
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        page = browser.new_page(device_scale_factor=SCALE)
        for png in todo:
            svg = (reports / "figures" / pathlib.Path(png).relative_to("viz")).with_suffix(".svg").read_text()
            w, h = (int(x) for x in re.search(r'viewBox="0 0 (\d+) (\d+)"', svg).groups())
            page.set_viewport_size({"width": w, "height": h})
            page.set_content(f'<!doctype html><html style="margin:0;background:#0d0d0d"><body style="margin:0">{svg}</body></html>')
            dest = reports / png
            dest.parent.mkdir(parents=True, exist_ok=True)
            page.locator("svg").first.screenshot(path=str(dest), omit_background=False)
        browser.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reports", default=str(ROOT.parent / "mailroom-issues" / "reports"))
    ap.add_argument("--check", action="store_true", help="exit 1 if any PNG is missing, stale or orphaned")
    args = ap.parse_args()
    reports = pathlib.Path(args.reports)
    want = sources(reports)
    man_path = reports / "viz" / "MANIFEST.json"
    have = json.loads(man_path.read_text())["figures"] if man_path.is_file() else {}
    stale = [p for p, h in want.items() if have.get(p) != h or not (reports / p).is_file()]
    on_disk = {p.relative_to(reports).as_posix() for p in (reports / "viz").rglob("*.png")}
    orphans = sorted((set(have) | on_disk) - set(want))
    if args.check:
        for p in stale:
            print(f"stale: {p}")
        for p in orphans:
            print(f"orphan: {p}")
        return 1 if (stale or orphans) else 0
    render(reports, stale)
    for p in orphans:
        f = reports / p
        if f.is_file():
            f.unlink()
    man_path.parent.mkdir(parents=True, exist_ok=True)
    man_path.write_text(json.dumps({"scale": SCALE, "generator": "local-mailroom-sandbox reports/dashboard/export_pngs.py",
                                    "figures": want}, indent=1, sort_keys=True) + "\n")
    for p in stale:
        print(f"wrote: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
