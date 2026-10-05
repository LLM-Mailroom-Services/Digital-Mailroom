#!/usr/bin/env python3
"""Render Modal specialist performance SVGs (+ PNGs) under reports/dashboard/."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DASH = ROOT / "reports" / "dashboard"
sys.path.insert(0, str(ROOT / "scripts" / "sand032"))
sys.path.insert(0, str(DASH))

import viz  # noqa: E402
import modal_performance as mp  # noqa: E402

DATA = DASH / "hub_data.json"
DOC = DASH / "MODAL-PERFORMANCE-VISUALS.md"
VIZ_PNG = DASH / "viz" / "modal-performance"
MANIFEST = VIZ_PNG / "MANIFEST.json"
PNG_SCALE = 2


def _png_rel(svg_rel: str) -> str:
    name = pathlib.Path(svg_rel).name.replace(".svg", ".png")
    return f"viz/modal-performance/{name}"


def export_pngs(svg_rels: list[str], check: bool) -> list[str]:
    want = {_png_rel(rel): hashlib.sha256((DASH / rel).read_bytes()).hexdigest() for rel in svg_rels}
    have = json.loads(MANIFEST.read_text())["figures"] if MANIFEST.is_file() else {}
    stale = [k for k, h in want.items() if have.get(k) != h or not (DASH / k).is_file()]
    if check:
        for k in stale:
            print(f"stale png: {k}")
        return stale
    if not stale:
        return []
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    exe = os.environ.get("CHROMIUM_PATH", "/usr/local/bin/google-chrome")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe)
        page = browser.new_page(device_scale_factor=PNG_SCALE)
        for png_rel in stale:
            svg_rel = f"figures/modal-performance/{pathlib.Path(png_rel).name.replace('.png', '.svg')}"
            svg = (DASH / svg_rel).read_text()
            w, h = (int(x) for x in re.search(r'viewBox="0 0 (\d+) (\d+)"', svg).groups())
            page.set_viewport_size({"width": w, "height": h})
            page.set_content(
                f'<!doctype html><html style="margin:0;background:#0d0d0d"><body style="margin:0">{svg}</body></html>')
            dest = DASH / png_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            page.locator("svg").first.screenshot(path=str(dest), omit_background=False)
        browser.close()
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({"scale": PNG_SCALE, "figures": want}, indent=1, sort_keys=True) + "\n")
    for k in stale:
        print(f"wrote png: {k}")
    return stale


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="exit 1 if SVG or PNG outputs are stale")
    ap.add_argument("--no-png", action="store_true", help="skip PNG export")
    args = ap.parse_args()
    import gpu_report  # noqa: PLC0415

    D = json.loads(DATA.read_text())
    figs = mp.render(D, viz, exclude=gpu_report.NOT_A_CONFIG)
    stale_svg = []
    svg_files: list[pathlib.Path] = []
    for rel, body in figs.items():
        dest = DASH / rel
        svg_files.append(dest)
        if not dest.is_file() or dest.read_text() != body:
            stale_svg.append(rel)
            if not args.check:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(body)
    md = mp.report_md(sorted(figs))
    if not DOC.is_file() or DOC.read_text() != md:
        stale_svg.append(str(DOC.relative_to(DASH)))
        if not args.check:
            DOC.write_text(md)
    for s in stale_svg:
        print(("stale: " if args.check else "wrote: ") + s)

    stale_png: list[str] = []
    if not args.no_png:
        # Ensure SVGs exist on disk before PNG pass (check mode may skip writes).
        for rel in figs:
            p = DASH / rel
            if not p.is_file():
                p.write_text(figs[rel])
        try:
            stale_png = export_pngs(list(figs), args.check)
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: PNG export skipped: {exc}", file=sys.stderr)
            if args.check:
                stale_png = ["png-export-unavailable"]

    if args.check and (stale_svg or stale_png):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
