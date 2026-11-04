"""Re-lay committed SAND-032 figures with the current chart kit, from their own data.

The per-run inputs ``report.py`` reads (``data/runtime/runs/<rid>/items.jsonl``,
``data/runtime/sand032``) are machine-local and not committed. Every committed
figure embeds its data (one ``<title>`` per mark, reference-line labels,
legend names), so a layout fix in ``viz.py`` can be applied without re-running
GPU jobs: parse the figure, render it again, compare the data.

    python scripts/sand032/rerender.py            # rewrite every figure in place
    python scripts/sand032/rerender.py --check    # exit 1 if any figure would change

Only layout changes. Values, order, emphasis, units and number formats are
read back from the figure and asserted equal after rendering.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import viz  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIG_DIRS = sorted(p for p in (ROOT / "reports").glob("*/figures") if p.is_dir())

_TEXT = lambda cls: re.compile(rf'<text class="{cls}"[^>]*>(?:<title>[^<]*</title>)?([^<]*)</text>')  # noqa: E731
_TIP = re.compile(r"^(?P<label>.*): (?P<num>-?[\d,]*\.?\d+)(?P<unit>[^\s—]*)(?: — (?P<note>.*))?$", re.S)


def _u(s: str) -> str:
    return html.unescape(s)


def _fmt_for(num: str):
    nd = len(num.split(".", 1)[1]) if "." in num else 0
    return lambda v, nd=nd: f"{v:.{nd}f}"


def parse_hbar(svg: str) -> dict:
    title = _u(_TEXT("title").search(svg).group(1))
    sub = _u(_TEXT("sub").search(svg).group(1))
    width = int(re.search(r'viewBox="0 0 (\d+) ', svg).group(1))
    rows, unit, fmt, num0 = [], "", None, None
    for m in re.finditer(r'<path class="(s1|deemph)" d="[^"]*"><title>([^<]*)</title></path>', svg):
        tip = _TIP.match(_u(m.group(2)))
        if not tip:
            raise ValueError(f"unparsed bar title: {m.group(2)!r}")
        unit = tip["unit"]
        num0 = num0 or tip["num"]
        rows.append({"label": tip["label"], "value": float(tip["num"].replace(",", "")),
                     "emphasis": m.group(1) == "s1", **({"note": tip["note"]} if tip["note"] else {})})
    # "n/a" rows: a label with no bar (ladder panels with a missing metric)
    labels = [_u(x) for x in re.findall(r'<text class="lbl"[^>]*text-anchor="end">(?:<title>([^<]*)</title>)?', svg)]
    shown = [_u(x) for x in _TEXT("lbl").findall(svg)]
    full = [t or s for t, s in zip(labels, shown)]
    if len(full) != len(rows):
        byl = {r["label"]: r for r in rows}
        rows = [byl.get(lab, {"label": lab, "value": None}) for lab in full]
    refs = []
    for lab in (_u(x) for x in _TEXT("reflbl").findall(svg)):
        m = re.search(r"(-?[\d.]+)", lab)
        refs.append((float(m.group(1)), lab))
    label_w = 120 if width <= 520 else 190
    fmt = _fmt_for(num0 or "0")
    return {"title": title, "sub": sub, "rows": rows, "unit": unit, "fmt": fmt, "refs": refs,
            "width": 520 if width <= 520 else 720, "label_w": label_w}


def render_hbar(p: dict) -> str:
    return viz.hbar(p["title"], p["sub"], p["rows"], unit=p["unit"], fmt=p["fmt"], refs=p["refs"] or None,
                    width=p["width"], label_w=p["label_w"])


def parse_dumbbell(svg: str) -> dict:
    title = _u(_TEXT("title").search(svg).group(1))
    sub = _u(_TEXT("sub").search(svg).group(1))
    lbls = [_u(x) for x in _TEXT("lbl").findall(svg)]
    names = (lbls[0], lbls[1])
    rows: dict[str, dict] = {}
    unit, num0 = "", None
    for cls, tip in re.findall(r'<circle class="(s1|s2) ring"[^>]*><title>([^<]*)</title></circle>', svg):
        tip = _u(tip)
        label, rest = tip.rsplit(" · ", 1)
        name, val = rest.rsplit(": ", 1)
        m = re.match(r"(-?[\d.]+)(.*)$", val)
        unit, num0 = m.group(2), num0 or m.group(1)
        rows.setdefault(label, {"label": label, "a": None, "b": None})["a" if cls == "s1" else "b"] = float(m.group(1))
    return {"title": title, "sub": sub, "rows": list(rows.values()), "names": names, "unit": unit,
            "fmt": _fmt_for(num0 or "0")}


def render_dumbbell(p: dict) -> str:
    return viz.dumbbell(p["title"], p["sub"], p["rows"], p["names"], unit=p["unit"], fmt=p["fmt"])


def rerender(svg: str) -> str:
    if svg.count("<svg") > 1:  # small multiples: an outer grid of hbar panels
        title = _u(re.search(r'aria-label="([^"]*)"', svg).group(1))
        inner = re.findall(r'<g transform="translate\([^)]*\)">(<svg.*?</svg>)</g>', svg, re.S)
        cols = 2 if len(inner) > 1 else 1
        return viz.small_multiples(title, [render_hbar(parse_hbar(p)) for p in inner], cols=cols)
    if '<circle class="s1 ring"' in svg:
        return render_dumbbell(parse_dumbbell(svg))
    return render_hbar(parse_hbar(svg))


def _data(svg: str) -> list[str]:
    """Every mark's hover title: the figure's data, independent of layout."""
    return sorted(_u(t) for t in re.findall(r"<(?:path|circle)[^>]*><title>([^<]*)</title>", svg))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if any figure is stale")
    args = ap.parse_args()
    stale = []
    for d in FIG_DIRS:
        for f in sorted(d.glob("*.svg")):
            old = f.read_text(encoding="utf-8")
            new = rerender(old)
            if _data(new) != _data(old):
                raise SystemExit(f"{f}: data changed on re-render — refusing to write")
            if new != old:
                stale.append(f)
                if not args.check:
                    f.write_text(new, encoding="utf-8")
    for f in stale:
        print(("stale: " if args.check else "rewrote: ") + str(f.relative_to(ROOT)))
    return 1 if (args.check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
