"""SAND-032 chart kit — /dataviz method, reference palette (validated light + dark).

Forms (chosen before color, per choosing-a-form.md):
  * hbar      — one series of magnitudes (single hue slot 1; no legend box — the
                title names it); optional EMPHASIS (kept = accent, rest = gray)
  * dumbbell  — before → after per item (two series, slots 1 & 2, legend + labels)
  * small_multiples — one axis per metric, never a dual axis
Marks (marks-and-anatomy.md): bars <= 24px thick (we use 14), 4px rounded data-end,
square at the baseline, 2px surface gap between adjacent bars, 1px solid hairline
grid, clean ticks, text in text tokens (never the series color), selective labels
(value at bar tip only). Every mark has a <title> (native hover); every figure is
paired with a markdown table (the table-view twin). Every figure is a self-contained
DARK card (the reference palette's dark steps on the #1a1a19 surface, high-contrast ink),
so all report figures read the same on any page theme.
Palette validated with scripts/validate_palette.js --mode dark:
  #3987e5,#d95926,#199e70,#c98500,#d55181,#9085e9 → ALL PASS (CVD ΔE 8.4, normal 19.3, contrast ≥3:1)
"""
from __future__ import annotations

import html
import math

STYLE = """
<style>
  .viz { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; color-scheme: dark;
    --surface:#1a1a19; --ink:#ffffff; --ink2:#d6d5cc; --muted:#a9a89f;
    --grid:#2c2c2a; --axis:#4a4a46; --deemph:#76756f;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --s6:#9085e9;
    --good:#0ca30c; --critical:#d03b3b; }
  .viz .bg { fill: var(--surface); }
  .viz .title { fill: var(--ink); font-size: 15px; font-weight: 600; }
  .viz .sub { fill: var(--ink2); font-size: 12px; }
  .viz .lbl { fill: var(--ink2); font-size: 12px; }
  .viz .val { fill: var(--ink); font-size: 12px; font-variant-numeric: tabular-nums;
    paint-order: stroke; stroke: var(--surface); stroke-width: 4px; stroke-linejoin: round; }
  .viz .tick { fill: var(--muted); font-size: 11px; font-variant-numeric: tabular-nums; }
  .viz .grid { stroke: var(--grid); stroke-width: 1; }
  .viz .axis { stroke: var(--axis); stroke-width: 1; }
  .viz .ref { stroke: var(--ink2); stroke-width: 1; stroke-dasharray: 4 3; }
  .viz .reflbl { fill: var(--ink2); font-size: 11px; paint-order: stroke; stroke: var(--surface); stroke-width: 3px; }
  .viz .s1 { fill: var(--s1); } .viz .s2 { fill: var(--s2); } .viz .s3 { fill: var(--s3); }
  .viz .s4 { fill: var(--s4); } .viz .s5 { fill: var(--s5); } .viz .s6 { fill: var(--s6); }
  .viz .ln1 { stroke: var(--s1); } .viz .ln2 { stroke: var(--s2); } .viz .ln3 { stroke: var(--s3); }
  .viz .ln4 { stroke: var(--s4); } .viz .ln5 { stroke: var(--s5); } .viz .ln6 { stroke: var(--s6); }
  .viz .deemph { fill: var(--deemph); }
  .viz .conn { stroke: var(--axis); stroke-width: 2; }
  .viz .ring { stroke: var(--surface); stroke-width: 2; }
</style>
"""

# Fixed entity -> categorical slot (color follows the entity, never its rank). The mailroom's routes and
# models keep the same color in every figure. Slots 1-6 of the reference palette's dark steps, validated
# with scripts/validate_palette.js --mode dark on the #1a1a19 surface: ALL PASS (worst adjacent CVD ΔE 8.4,
# normal-vision ΔE 19.3, every slot >= 3:1). Identity is never color alone: every bar is direct-labeled.
ENTITY = {"Qwen3-8B-AWQ": "s1", "Qwen3.7-Flash": "s2", "DeepSeek-V4.1-Flash": "s3", "Granite-4.2-8B": "s4",
          "Qwen3-8B": "s5", "ModernBERT": "s6"}


def entity(name: str) -> str:
    """Series class for a model/route name (matched on the model family inside the label)."""
    for k in sorted(ENTITY, key=len, reverse=True):
        if k in name:
            return ENTITY[k]
    return "s1"


BAR = 14          # bar thickness (<= 24)
GAP = 2           # surface gap between adjacent bars
ROW = BAR + 10    # band per row (leftover band is air)


def _esc(s) -> str:
    return html.escape(str(s), quote=True)


def sentence(s: str) -> str:
    """Sentence case for titles and subtitles: capitalize a leading plain lowercase word (never an
    identifier such as ``max_inputs`` or ``c32``, which keep their exact spelling)."""
    head = s.split(" ", 1)[0]
    return s[:1].upper() + s[1:] if head.isalpha() and head.islower() else s


# Approximate advance widths (em) for system-ui sans. Deliberately a little
# generous: labels are laid out from these, so an under-estimate clips text
# (the 0.x figures cut doc-id labels off the left edge at a fixed 190px).
_NARROW = set("il.,:;|!'`·()[]{} ")
_WIDE = set("MWmw@%")


def text_w(s: str, px: float = 12) -> float:
    """Estimated rendered width of ``s`` at font size ``px``."""
    em = 0.0
    for ch in str(s):
        # Calibrated against DejaVu Sans (the widest common system-ui fallback,
        # used by headless Chromium on Linux), so other platforms only gain air.
        if ch in _NARROW:
            em += 0.34
        elif ch in _WIDE:
            em += 0.92
        elif ch.isupper() or ch in "_—–×":
            em += 0.72
        elif ch.isdigit():
            em += 0.64
        else:
            em += 0.61
    return em * px


def fit_label(s: str, max_w: float, px: float = 12) -> str:
    """Middle-truncate with an ellipsis so ``s`` fits ``max_w`` (full text stays in the <title>)."""
    s = str(s)
    if text_w(s, px) <= max_w:
        return s
    keep = len(s)
    while keep > 4 and text_w(s[: keep // 2] + "…" + s[len(s) - keep // 2:], px) > max_w:
        keep -= 1
    return s[: keep // 2] + "…" + s[len(s) - keep // 2:]


def _ref_lane(refs_px: list[tuple[float, str]], plot_r: float, px: float = 11) -> list[tuple[float, int, str]]:
    """Place reference-line labels in a lane above the plot: (x, row, text).

    Labels sit right of their line unless that would run off the plot, and drop
    to a second row when they would collide (p50/p95 on a tight distribution)."""
    placed: list[tuple[float, float, int, str]] = []
    for x, lab in sorted(refs_px):
        w = text_w(lab, px)
        x0 = x + 4 if x + 4 + w <= plot_r + 60 else x - 4 - w
        row = 0
        for (a, b, r, _) in placed:
            if r == row and not (x0 + w + 6 < a or x0 > b + 6):
                row = 1
        placed.append((x0, x0 + w, row, lab))
    return [(a, r, lab) for a, _, r, lab in placed]


def nice_ticks(vmax: float, n: int = 4) -> list[float]:
    """Clean round ticks 0..>=vmax (1/2/2.5/5 × 10^k)."""
    if vmax <= 0:
        return [0.0, 1.0]
    raw = vmax / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    ticks, t = [], 0.0
    while t < vmax - 1e-12:
        ticks.append(round(t, 10))
        t += step
    ticks.append(round(t, 10))
    return ticks


def _fmt_tick(v: float) -> str:
    if v >= 1000:
        return f"{v:,.0f}"
    if v == int(v):
        return f"{int(v)}"
    return f"{v:g}"


def _bar_path(x0: float, y: float, length: float, h: float, r: float = 4) -> str:
    """Horizontal bar: square at the baseline (x0), 4px rounded data-end."""
    if length <= 0:
        return ""
    r = min(r, length, h / 2)
    x1 = x0 + length
    return (f"M{x0:.1f},{y:.1f} H{x1 - r:.1f} Q{x1:.1f},{y:.1f} {x1:.1f},{y + r:.1f} "
            f"V{y + h - r:.1f} Q{x1:.1f},{y + h:.1f} {x1 - r:.1f},{y + h:.1f} H{x0:.1f} Z")


def hbar(title: str, subtitle: str, rows: list[dict], *, unit: str = "", fmt=None,
         refs: list[tuple[float, str]] | None = None, width: int = 720, label_w: int = 190,
         max_label_w: int = 320, domain_max: float | None = None,
         legend: list[tuple[str, str]] | None = None) -> str:
    """rows: [{label, value, emphasis(bool, default True), series(optional slot class), note(optional)}].

    ``series`` colors a bar by its entity (see ENTITY); ``legend`` [(slot class, name)] draws a key row
    under the subtitle (required whenever the bars carry more than one color).

    ``label_w`` is a minimum: the label column grows to fit the longest label
    (capped at ``max_label_w``, beyond which labels are middle-ellipsized with
    the full text kept in the hover <title>), and the figure widens with it so
    the plot keeps its length. ``domain_max`` extends the value axis to at least
    that value, so small multiples can share one scale."""
    fmt = fmt or (lambda v: f"{v:g}")
    vals = [r["value"] for r in rows if r.get("value") is not None]
    ticks = nice_ticks(max(vals + [x for x, _ in (refs or [])] + ([domain_max] if domain_max else []) or [1]))
    vmax = ticks[-1]
    need = max([text_w(r["label"]) for r in rows] or [0]) + 12  # label sits 8px left of the axis
    label_w = math.ceil(max(label_w, min(need + 2, max_label_w)))
    plot_len = width - 70 - 190  # the plot length a default-label figure gets
    width = max(width, label_w + plot_len + 70, int(text_w(title, 15)) + 32, int(text_w(subtitle)) + 32)
    lane = 30 if refs else 0  # reference labels get their own lane under the subtitle
    key = 22 if legend else 0
    if legend:
        width = max(width, int(16 + sum(22 + text_w(nm) for _, nm in legend)) + 16)
    top, plot_l, plot_r = 58 + lane + key, label_w, width - 70
    plot_h = len(rows) * ROW
    h = top + plot_h + 34
    sx = lambda v: plot_l + (plot_r - plot_l) * (v / vmax if vmax else 0)  # noqa: E731
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" class="viz" viewBox="0 0 {width} {h}" width="{width}" '
         f'height="{h}" role="img" aria-label="{_esc(title)}">', STYLE,
         f'<rect class="bg" width="{width}" height="{h}" rx="8"/>',
         f'<text class="title" x="16" y="24">{_esc(title)}</text>',
         f'<text class="sub" x="16" y="42">{_esc(sentence(subtitle))}</text>']
    lx = 16
    for cls, nm in legend or []:  # legend: marker key + text-token label
        o.append(f'<rect class="{cls}" x="{lx}" y="53" width="10" height="10" rx="2"/>'
                 f'<text class="lbl" x="{lx + 15}" y="62">{_esc(nm)}</text>')
        lx += 22 + text_w(nm)
    for t in ticks:
        x = sx(t)
        o.append(f'<line class="grid" x1="{x:.1f}" y1="{top - 4}" x2="{x:.1f}" y2="{top + plot_h}"/>')
        o.append(f'<text class="tick" x="{x:.1f}" y="{top + plot_h + 16}" text-anchor="middle">{_fmt_tick(t)}{unit}</text>')
    o.append(f'<line class="axis" x1="{plot_l}" y1="{top - 4}" x2="{plot_l}" y2="{top + plot_h}"/>')
    for x, _lab in refs or []:  # reference lines sit BEHIND the marks
        px = sx(x)
        o.append(f'<line class="ref" x1="{px:.1f}" y1="{top - lane + 4}" x2="{px:.1f}" y2="{top + plot_h}"/>')
    for x0, row, lab in _ref_lane([(sx(x), lab) for x, lab in refs or []], plot_r):
        o.append(f'<text class="reflbl" x="{x0:.1f}" y="{top - lane + 12 + row * 13}">{_esc(lab)}</text>')
    for i, r in enumerate(rows):
        y = top + i * ROW + (ROW - BAR) / 2
        shown = fit_label(r["label"], plot_l - 12)
        full = f'<title>{_esc(r["label"])}</title>' if shown != r["label"] else ""
        o.append(f'<text class="lbl" x="{plot_l - 8}" y="{y + BAR - 3}" text-anchor="end">{full}{_esc(shown)}</text>')
        v = r.get("value")
        if v is None:
            o.append(f'<text class="tick" x="{plot_l + 6}" y="{y + BAR - 3}">n/a</text>')
            continue
        cls = r.get("series") or ("s1" if r.get("emphasis", True) else "deemph")
        tip = f'{r["label"]}: {fmt(v)}{unit}' + (f' — {r["note"]}' if r.get("note") else "")
        o.append(f'<path class="{cls}" d="{_bar_path(plot_l, y, sx(v) - plot_l, BAR)}"><title>{_esc(tip)}</title></path>')
        o.append(f'<text class="val" x="{sx(v) + 6:.1f}" y="{y + BAR - 3}">{_esc(fmt(v))}{_esc(unit)}</text>')
    o.append("</svg>")
    return "\n".join(o)


def dumbbell(title: str, subtitle: str, rows: list[dict], names: tuple[str, str], *, unit: str = "",
             fmt=None, width: int = 720, label_w: int = 190, val=None) -> str:
    """rows: [{label, a, b}] — before (slot 1) → after (slot 2) on ONE axis.

    ``val(row) -> str`` overrides the end-of-row value label (default: the
    slot-2 value); the right margin grows to fit the longest one.
    """
    fmt = fmt or (lambda v: f"{v:g}")
    val = val or (lambda r: f"{fmt(r['b'])}{unit}")
    vals = [v for r in rows for v in (r["a"], r["b"]) if v is not None]
    ticks = nice_ticks(max(vals or [1]))
    vmax = ticks[-1]
    label_w = math.ceil(max(label_w, min(max([text_w(r["label"]) for r in rows] or [0]) + 14, 320)))
    width = max(width, label_w + 450, int(text_w(title, 15)) + 32, int(text_w(subtitle)) + 32)
    right_w = max(80, math.ceil(max([text_w(val(r)) for r in rows] or [0])) + 24)
    width = max(width, label_w + 370 + right_w)
    top, plot_l, plot_r = 78, label_w, width - right_w
    leg2 = 22 + 10 + text_w(names[0]) + 20
    plot_h = len(rows) * (ROW + 6)
    h = top + plot_h + 34
    sx = lambda v: plot_l + (plot_r - plot_l) * (v / vmax if vmax else 0)  # noqa: E731
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" class="viz" viewBox="0 0 {width} {h}" width="{width}" '
         f'height="{h}" role="img" aria-label="{_esc(title)}">', STYLE,
         f'<rect class="bg" width="{width}" height="{h}" rx="8"/>',
         f'<text class="title" x="16" y="24">{_esc(title)}</text>',
         f'<text class="sub" x="16" y="42">{_esc(sentence(subtitle))}</text>',
         # legend (always present for >= 2 series): marker keys + text-token labels
         f'<circle class="s1" cx="22" cy="58" r="5"/><text class="lbl" x="32" y="62">{_esc(names[0])}</text>',
         f'<circle class="s2" cx="{leg2:.0f}" cy="58" r="5"/>'
         f'<text class="lbl" x="{leg2 + 10:.0f}" y="62">{_esc(names[1])}</text>']
    for t in ticks:
        x = sx(t)
        o.append(f'<line class="grid" x1="{x:.1f}" y1="{top - 4}" x2="{x:.1f}" y2="{top + plot_h}"/>')
        o.append(f'<text class="tick" x="{x:.1f}" y="{top + plot_h + 16}" text-anchor="middle">{_fmt_tick(t)}{unit}</text>')
    for i, r in enumerate(rows):
        cy = top + i * (ROW + 6) + (ROW + 6) / 2
        o.append(f'<text class="lbl" x="{plot_l - 8}" y="{cy + 4}" text-anchor="end">{_esc(fit_label(r["label"], plot_l - 12))}</text>')
        if r["a"] is None or r["b"] is None:
            continue
        xa, xb = sx(r["a"]), sx(r["b"])
        o.append(f'<line class="conn" x1="{xa:.1f}" y1="{cy}" x2="{xb:.1f}" y2="{cy}"/>')
        for cls, x, v, nm in (("s1", xa, r["a"], names[0]), ("s2", xb, r["b"], names[1])):
            o.append(f'<circle class="{cls} ring" cx="{x:.1f}" cy="{cy}" r="5"><title>'
                     f'{_esc(r["label"])} · {_esc(nm)}: {_esc(fmt(v))}{_esc(unit)}</title></circle>')
        right = max(xa, xb)
        o.append(f'<text class="val" x="{right + 10:.1f}" y="{cy + 4}">{_esc(val(r))}</text>')
    o.append("</svg>")
    return "\n".join(o)


def small_multiples(title: str, panels: list[str], cols: int = 2) -> str:
    """Stack independent single-axis panels (each its own <svg>) in a grid SVG."""
    import re

    sizes = [tuple(int(x) for x in re.search(r'viewBox="0 0 (\d+) (\d+)"', p).groups()) for p in panels]
    pw = max(w for w, _ in sizes)
    rows_h, y, out = [], 36, []
    for i in range(0, len(panels), cols):
        chunk = panels[i:i + cols]
        rh = max(sizes[i + j][1] for j in range(len(chunk)))
        for j, p in enumerate(chunk):
            out.append(f'<g transform="translate({j * (pw + 16)},{y})">{p}</g>')
        y += rh + 16
    W = cols * pw + (cols - 1) * 16
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="viz" viewBox="0 0 {W} {y}" width="{W}" height="{y}" '
            f'role="img" aria-label="{_esc(title)}">{STYLE}<rect class="bg" width="{W}" height="{y}" rx="8"/>'
            f'<text class="title" x="16" y="24">{_esc(title)}</text>{"".join(out)}</svg>')


# ---------------------------------------------------------------------------------------------------------
# Forms added for the redrawn source-repo charts (append-only: the forms above are unchanged).
#   * grouped_hbar — magnitudes grouped by a category (e.g. model × document type): one axis, a group
#                    heading row per group, every bar direct-labeled with its series name, legend row
#   * lines        — y vs x on one pair of axes (calibration curves, coverage/accuracy trade-offs):
#                    2px lines, >= 10px markers with a surface ring, optional y = x reference
# Same STYLE, card, title/subtitle positions, hairline grid and text tokens as the forms above.

EXTRA_STYLE = """
<style>
  .viz .grp { fill: var(--ink); font-size: 12px; font-weight: 600; }
  .viz .axt { fill: var(--ink2); font-size: 11px; }
  .viz .line { fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
  .viz .lndeemph { stroke: var(--deemph); }
  .viz .lead { stroke: var(--ink2); stroke-width: 1; }
  .viz .hit { fill: transparent; }
</style>
"""

_LN = {"s1": "ln1", "s2": "ln2", "s3": "ln3", "s4": "ln4", "s5": "ln5", "s6": "ln6", "deemph": "lndeemph"}


def _open(width: float, h: float, title: str, subtitle: str) -> list[str]:
    return [f'<svg xmlns="http://www.w3.org/2000/svg" class="viz" viewBox="0 0 {width:.0f} {h:.0f}" width="{width:.0f}" '
            f'height="{h:.0f}" role="img" aria-label="{_esc(title)}">', STYLE, EXTRA_STYLE,
            f'<rect class="bg" width="{width:.0f}" height="{h:.0f}" rx="8"/>',
            f'<text class="title" x="16" y="24">{_esc(title)}</text>',
            f'<text class="sub" x="16" y="42">{_esc(sentence(subtitle))}</text>']


def _marker(shape: str | None, cls: str, x: float, y: float) -> str:
    """A >= 10px marker with a 2px surface ring (circle, square or diamond — shape is a second identity channel)."""
    if shape == "square":
        return f'<rect class="{cls} ring" x="{x - 4.5:.1f}" y="{y - 4.5:.1f}" width="9" height="9" rx="1.5"/>'
    if shape == "diamond":
        return (f'<path class="{cls} ring" d="M{x:.1f},{y - 6:.1f} L{x + 6:.1f},{y:.1f} L{x:.1f},{y + 6:.1f} '
                f'L{x - 6:.1f},{y:.1f} Z"/>')
    return f'<circle class="{cls} ring" cx="{x:.1f}" cy="{y:.1f}" r="5"/>'


def _key_w(name: str, line: bool = False) -> float:
    return (30 if line else 22) + text_w(name)


def grouped_hbar(title: str, subtitle: str, groups: list[dict], *, legend: list[tuple[str, str]],
                 unit: str = "", fmt=None, tick_fmt=None, refs: list[tuple[float, str]] | None = None,
                 width: int = 720, domain_max: float | None = None) -> str:
    """groups: [{label, rows: [{label, value, series(slot class or 'deemph'), note(optional), text(optional)}]}].

    Each group gets a heading row, then one bar per row on ONE shared value axis. Every bar carries its
    series name in the label column (identity is never color alone) and ``legend`` [(class, name)] keys
    the colors under the subtitle. ``text`` overrides a bar's tip label (default ``fmt(value)+unit``)."""
    fmt = fmt or (lambda v: f"{v:g}")
    tick_fmt = tick_fmt or (lambda t: f"{_fmt_tick(t)}{unit}")
    tip_txt = lambda r: r.get("text") or f"{fmt(r['value'])}{unit}"  # noqa: E731
    rows = [r for g in groups for r in g["rows"]]
    vals = [r["value"] for r in rows if r.get("value") is not None]
    ticks = nice_ticks(max(vals + [x for x, _ in refs or []] + ([domain_max] if domain_max else []) or [1]))
    vmax = ticks[-1]
    label_w = math.ceil(max([text_w(r["label"]) + 28 for r in rows] + [text_w(g["label"]) * 1.08 + 24 for g in groups]
                            + [120]))
    right_w = math.ceil(max([text_w(tip_txt(r)) + 20 for r in rows if r.get("value") is not None] + [56]))
    key_w = 16 + sum(_key_w(nm) for _, nm in legend) + 16
    width = math.ceil(max(width, label_w + 380 + right_w, text_w(title, 15) + 32, text_w(subtitle) + 32, key_w))
    lane = 30 if refs else 0
    key = 22 if legend else 0
    top, plot_l, plot_r = 58 + lane + key, label_w, width - right_w
    HEAD, GGAP = 22, 10
    plot_h = sum(HEAD + len(g["rows"]) * ROW for g in groups) + GGAP * (len(groups) - 1)
    h = top + plot_h + 34
    sx = lambda v: plot_l + (plot_r - plot_l) * (v / vmax if vmax else 0)  # noqa: E731
    o = _open(width, h, title, subtitle)
    lx = 16
    for cls, nm in legend:
        o.append(f'<rect class="{cls}" x="{lx}" y="53" width="10" height="10" rx="2"/>'
                 f'<text class="lbl" x="{lx + 15}" y="62">{_esc(nm)}</text>')
        lx += _key_w(nm)
    for t in ticks:
        x = sx(t)
        o.append(f'<line class="grid" x1="{x:.1f}" y1="{top - 4}" x2="{x:.1f}" y2="{top + plot_h}"/>')
        o.append(f'<text class="tick" x="{x:.1f}" y="{top + plot_h + 16}" text-anchor="middle">{_esc(tick_fmt(t))}</text>')
    o.append(f'<line class="axis" x1="{plot_l}" y1="{top - 4}" x2="{plot_l}" y2="{top + plot_h}"/>')
    for x, _lab in refs or []:
        px = sx(x)
        o.append(f'<line class="ref" x1="{px:.1f}" y1="{top - lane + 4}" x2="{px:.1f}" y2="{top + plot_h}"/>')
    for x0, row, lab in _ref_lane([(sx(x), lab) for x, lab in refs or []], plot_r):
        o.append(f'<text class="reflbl" x="{x0:.1f}" y="{top - lane + 12 + row * 13}">{_esc(lab)}</text>')
    y0 = top
    for g in groups:
        o.append(f'<text class="grp" x="16" y="{y0 + 15}">{_esc(g["label"])}</text>')
        y0 += HEAD
        for r in g["rows"]:
            y = y0 + (ROW - BAR) / 2
            o.append(f'<text class="lbl" x="{plot_l - 8}" y="{y + BAR - 3}" text-anchor="end">{_esc(r["label"])}</text>')
            v = r.get("value")
            if v is None:
                o.append(f'<text class="tick" x="{plot_l + 6}" y="{y + BAR - 3}">n/a</text>')
            else:
                tip = f'{g["label"]} · {r["label"]}: {tip_txt(r)}' + (f' — {r["note"]}' if r.get("note") else "")
                o.append(f'<path class="{r.get("series") or "s1"}" d="{_bar_path(plot_l, y, sx(v) - plot_l, BAR)}">'
                         f'<title>{_esc(tip)}</title></path>')
                # surface knockout behind the tip label, so a reference line never runs through its text
                o.append(f'<rect class="bg" x="{sx(v) + 3:.1f}" y="{y - 1:.1f}" width="{text_w(tip_txt(r)) + 6:.1f}" '
                         f'height="{BAR + 2}"/>')
                o.append(f'<text class="val" x="{sx(v) + 6:.1f}" y="{y + BAR - 3}">{_esc(tip_txt(r))}</text>')
            y0 += ROW
        y0 += GGAP
    o.append("</svg>")
    return "\n".join(o)


def _span_ticks(lo: float, hi: float, step: float | None = None) -> list[float]:
    """Clean ticks from lo to hi inclusive (step: 1/2/2.5/5 × 10^k unless given)."""
    if step is None:
        raw = (hi - lo) / 5
        mag = 10 ** math.floor(math.log10(raw))
        step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    out, t = [], lo
    while t <= hi + 1e-9:
        out.append(round(t, 10))
        t += step
    return out


def lines(title: str, subtitle: str, series: list[dict], *, x_label: str, y_label: str,
          x_domain: tuple[float, float], y_domain: tuple[float, float], x_step: float | None = None,
          y_step: float | None = None, unit_x: str = "", unit_y: str = "", fmt_x=None, fmt_y=None,
          diagonal: str | None = None, notes: list[dict] | None = None, width: int = 720, plot_h: int = 300) -> str:
    """series: [{name, cls (slot class or 'deemph'), marker ('circle'|'square'|'diamond'|None),
    points: [{x, y, tip}]}] on ONE x axis and ONE y axis (never dual).

    A legend (line key + marker shape) is drawn for >= 2 series; one series is named by the title.
    Points without a visible marker still get a 24px hover target with the <title>. ``diagonal`` draws
    the y = x reference with that label; ``notes`` [{x, y, text, dx, dy, anchor}] add a leader-lined
    annotation from a data point to a label (selective labels, never one per point)."""
    fmt_x = fmt_x or _fmt_tick
    fmt_y = fmt_y or _fmt_tick
    xt, yt = _span_ticks(*x_domain, x_step), _span_ticks(*y_domain, y_step)
    ylabs = [f"{fmt_y(t)}{unit_y}" for t in yt]
    key = 22 if len(series) >= 2 else 0
    key_w = 16 + sum(_key_w(s["name"], True) for s in series) + 16 if key else 0
    width = math.ceil(max(width, text_w(title, 15) + 32, text_w(subtitle) + 32, key_w))
    ytitle_y = 58 + key + 10
    top = ytitle_y + 16
    plot_l = 16 + math.ceil(max(text_w(s, 11) for s in ylabs)) + 8
    plot_r = width - 28
    plot_b = top + plot_h
    h = plot_b + 50
    (x0, x1), (y0, y1) = x_domain, y_domain
    sx = lambda v: plot_l + (plot_r - plot_l) * (v - x0) / (x1 - x0)  # noqa: E731
    sy = lambda v: plot_b - plot_h * (v - y0) / (y1 - y0)  # noqa: E731
    o = _open(width, h, title, subtitle)
    lx = 16
    for s in series if key else []:
        cls = s["cls"]
        o.append(f'<line class="line {_LN[cls]}" x1="{lx}" y1="58" x2="{lx + 18}" y2="58"/>')
        if s.get("marker"):
            o.append(_marker(s["marker"], cls, lx + 9, 58))
        o.append(f'<text class="lbl" x="{lx + 24}" y="62">{_esc(s["name"])}</text>')
        lx += _key_w(s["name"], True)
    for t, lab in zip(yt, ylabs):
        y = sy(t)
        o.append(f'<line class="grid" x1="{plot_l}" y1="{y:.1f}" x2="{plot_r}" y2="{y:.1f}"/>')
        o.append(f'<text class="tick" x="{plot_l - 6}" y="{y + 4:.1f}" text-anchor="end">{_esc(lab)}</text>')
    for t in xt:
        x = sx(t)
        o.append(f'<line class="grid" x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{plot_b}"/>')
        o.append(f'<text class="tick" x="{x:.1f}" y="{plot_b + 16}" text-anchor="middle">{_esc(fmt_x(t))}{_esc(unit_x)}</text>')
    o.append(f'<line class="axis" x1="{plot_l}" y1="{plot_b}" x2="{plot_r}" y2="{plot_b}"/>')
    o.append(f'<line class="axis" x1="{plot_l}" y1="{top}" x2="{plot_l}" y2="{plot_b}"/>')
    o.append(f'<text class="axt" x="16" y="{ytitle_y}">{_esc(y_label)}</text>')
    o.append(f'<text class="axt" x="{(plot_l + plot_r) / 2:.1f}" y="{plot_b + 36}" text-anchor="middle">{_esc(x_label)}</text>')
    if diagonal:
        lo, hi = max(x0, y0), min(x1, y1)
        o.append(f'<line class="ref" x1="{sx(lo):.1f}" y1="{sy(lo):.1f}" x2="{sx(hi):.1f}" y2="{sy(hi):.1f}"/>')
        # label above-left of the rising line, starting just inside the y axis: the line sits below the
        # label's whole width, because it only climbs further to the right
        w = text_w(diagonal, 11)
        x_end = plot_l + 10 + w
        at = x0 + (x_end - plot_l) / (plot_r - plot_l) * (x1 - x0)
        o.append(f'<text class="reflbl" x="{plot_l + 10}" y="{sy(at) - 8:.1f}">{_esc(diagonal)}</text>')
    for s in series:
        cls, pts = s["cls"], s["points"]
        d = " ".join(f'{"M" if i == 0 else "L"}{sx(p["x"]):.1f},{sy(p["y"]):.1f}' for i, p in enumerate(pts))
        o.append(f'<path class="line {_LN[cls]}" d="{d}"/>')
    for s in series:  # markers + hover targets above every line
        for p in s["points"]:
            x, y = sx(p["x"]), sy(p["y"])
            mark = _marker(s["marker"], s["cls"], x, y) if s.get("marker") else ""
            o.append(f'<g><title>{_esc(p.get("tip") or s["name"])}</title>'
                     f'<circle class="hit" cx="{x:.1f}" cy="{y:.1f}" r="12"/>{mark}</g>')
    for n in notes or []:  # text vertically centred on (x + dx, y + dy); the leader stops at its near edge
        x, y = sx(n["x"]), sy(n["y"])
        tx, ty = x + n.get("dx", 0), y + n.get("dy", 0)
        anchor = n.get("anchor", "start")
        if n.get("leader", True):
            lx2, ly2 = {"end": (tx + 4, ty), "start": (tx - 4, ty)}.get(anchor, (tx, ty - 9 if ty > y else ty + 7))
            o.append(f'<line class="lead" x1="{x:.1f}" y1="{y:.1f}" x2="{lx2:.1f}" y2="{ly2:.1f}"/>')
        if n.get("cls"):
            o.append(_marker(n.get("marker") or "circle", n["cls"], x, y))
        o.append(f'<text class="{n.get("style", "reflbl")}" x="{tx:.1f}" y="{ty + 4:.1f}" text-anchor="{anchor}">'
                 f'{_esc(n["text"])}</text>')
    o.append("</svg>")
    return "\n".join(o)


def scatter(title: str, subtitle: str, points: list[dict], *, x_label: str, y_label: str,
            x_domain: tuple[float, float], y_domain: tuple[float, float], legend: list[tuple[str, str, str | None]] | None = None,
            unit_x: str = "", unit_y: str = "", fmt_x=None, fmt_y=None, width: int = 720, plot_h: int = 320) -> str:
    """points: [{x, y, cls, marker, tip, label(optional)}] — efficiency scatter (no connecting lines)."""
    fmt_x = fmt_x or _fmt_tick
    fmt_y = fmt_y or _fmt_tick
    xt, yt = _span_ticks(*x_domain), _span_ticks(*y_domain)
    ylabs = [f"{fmt_y(t)}{unit_y}" for t in yt]
    key = 22 if legend else 0
    key_w = 16 + sum(_key_w(nm, False) for _, nm, _ in legend or []) + 16 if key else 0
    width = math.ceil(max(width, text_w(title, 15) + 32, text_w(subtitle) + 32, key_w))
    ytitle_y = 58 + key + 10
    top = ytitle_y + 16
    plot_l = 16 + math.ceil(max(text_w(s, 11) for s in ylabs)) + 8
    plot_r = width - 28
    plot_b = top + plot_h
    h = plot_b + 50
    (x0, x1), (y0, y1) = x_domain, y_domain
    sx = lambda v: plot_l + (plot_r - plot_l) * (v - x0) / (x1 - x0)  # noqa: E731
    sy = lambda v: plot_b - plot_h * (v - y0) / (y1 - y0)  # noqa: E731
    o = _open(width, h, title, subtitle)
    lx = 16
    for cls, nm, mark in legend or []:
        o.append(_marker(mark or "circle", cls, lx + 5, 58))
        o.append(f'<text class="lbl" x="{lx + 16}" y="62">{_esc(nm)}</text>')
        lx += _key_w(nm, False)
    for t, lab in zip(yt, ylabs):
        y = sy(t)
        o.append(f'<line class="grid" x1="{plot_l}" y1="{y:.1f}" x2="{plot_r}" y2="{y:.1f}"/>')
        o.append(f'<text class="tick" x="{plot_l - 6}" y="{y + 4:.1f}" text-anchor="end">{_esc(lab)}</text>')
    for t in xt:
        x = sx(t)
        o.append(f'<line class="grid" x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{plot_b}"/>')
        o.append(f'<text class="tick" x="{x:.1f}" y="{plot_b + 16}" text-anchor="middle">{_esc(fmt_x(t))}{_esc(unit_x)}</text>')
    o.append(f'<line class="axis" x1="{plot_l}" y1="{plot_b}" x2="{plot_r}" y2="{plot_b}"/>')
    o.append(f'<line class="axis" x1="{plot_l}" y1="{top}" x2="{plot_l}" y2="{plot_b}"/>')
    o.append(f'<text class="axt" x="16" y="{ytitle_y}">{_esc(y_label)}</text>')
    o.append(f'<text class="axt" x="{(plot_l + plot_r) / 2:.1f}" y="{plot_b + 36}" text-anchor="middle">{_esc(x_label)}</text>')
    for p in points:
        x, y = sx(p["x"]), sy(p["y"])
        mark = _marker(p.get("marker") or "circle", p["cls"], x, y)
        tip = p.get("tip") or p.get("label") or ""
        o.append(f'<g><title>{_esc(tip)}</title><circle class="hit" cx="{x:.1f}" cy="{y:.1f}" r="12"/>{mark}</g>')
        if p.get("label"):
            o.append(f'<text class="reflbl" x="{x + 7:.1f}" y="{y - 7:.1f}">{_esc(p["label"])}</text>')
    o.append("</svg>")
    return "\n".join(o)


def heatmap(title: str, subtitle: str, rows: list[str], cols: list[str], cells: dict[tuple[str, str], float | None],
            *, fmt=None, unit: str = "", width: int = 720) -> str:
    """Matrix heat: rows × cols; cell color = value on global min–max scale; text = raw value."""
    fmt = fmt or (lambda v: f"{v:.3f}")
    vals = [v for v in cells.values() if v is not None]
    vmin, vmax = (min(vals), max(vals)) if vals else (0.0, 1.0)
    cw, ch, pad = 72, 32, 8
    label_w = math.ceil(max([text_w(r) for r in rows] + [120]))
    top = 58
    plot_l = label_w + pad
    plot_w = len(cols) * cw
    h = top + len(rows) * ch + 44
    width = max(width, plot_l + plot_w + 24, text_w(title, 15) + 32)
    o = _open(width, h, title, subtitle)
    for j, c in enumerate(cols):
        x = plot_l + j * cw + cw / 2
        o.append(f'<text class="tick" x="{x:.1f}" y="{top - 6}" text-anchor="middle">{_esc(fit_label(c, cw - 4))}</text>')
    for i, row in enumerate(rows):
        y = top + i * ch
        o.append(f'<text class="lbl" x="{plot_l - pad}" y="{y + ch - 10}" text-anchor="end">{_esc(row)}</text>')
        for j, col in enumerate(cols):
            v = cells.get((row, col))
            x = plot_l + j * cw
            if v is None:
                o.append(f'<rect class="deemph" x="{x + 2:.1f}" y="{y + 2:.1f}" width="{cw - 4}" height="{ch - 4}" rx="3"/>'
                         f'<text class="tick" x="{x + cw / 2:.1f}" y="{y + ch - 10}" text-anchor="middle">—</text>')
                continue
            t = 0.5 if vmax == vmin else (v - vmin) / (vmax - vmin)
            fill = f"rgb({int(26 + t * 31)},{int(44 + t * 91)},{int(42 + t * 187)})"
            o.append(f'<rect fill="{fill}" x="{x + 2:.1f}" y="{y + 2:.1f}" width="{cw - 4}" height="{ch - 4}" rx="3">'
                     f'<title>{_esc(row)} · {_esc(col)}: {fmt(v)}{unit}</title></rect>')
            o.append(f'<text class="val" x="{x + cw / 2:.1f}" y="{y + ch - 10}" text-anchor="middle">{_esc(fmt(v))}</text>')
    o.append("</svg>")
    return "\n".join(o)


def stacked_vbar(title: str, subtitle: str, categories: list[str], segments: list[dict], *, unit: str = "$",
                 fmt=None, width: int = 720, plot_h: int = 260) -> str:
    """Vertical stacked bars. segments: [{name, cls, values: {category: magnitude}}]."""
    fmt = fmt or (lambda v: f"{v:.4f}")
    totals = {c: sum(s["values"].get(c, 0) or 0 for s in segments) for c in categories}
    ticks = nice_ticks(max(totals.values() or [1]))
    ymax = ticks[-1]
    key_w = 16 + sum(22 + text_w(s["name"]) for s in segments) + 16
    width = math.ceil(max(width, 80 * len(categories) + 120, key_w, text_w(title, 15) + 32))
    top = 58 + 22 + 10
    plot_l, plot_r = 56, width - 24
    plot_b = top + plot_h
    h = plot_b + 50
    bw = max(24, (plot_r - plot_l) / max(len(categories), 1) - 16)
    sx = lambda i: plot_l + i * ((plot_r - plot_l) / max(len(categories), 1)) + 8  # noqa: E731
    sy = lambda v: plot_b - plot_h * (v / ymax if ymax else 0)  # noqa: E731
    o = _open(width, h, title, subtitle)
    lx = 16
    for s in segments:
        o.append(f'<rect class="{s["cls"]}" x="{lx}" y="53" width="10" height="10" rx="2"/>'
                 f'<text class="lbl" x="{lx + 15}" y="62">{_esc(s["name"])}</text>')
        lx += 22 + text_w(s["name"])
    for t in ticks:
        y = sy(t)
        o.append(f'<line class="grid" x1="{plot_l}" y1="{y:.1f}" x2="{plot_r}" y2="{y:.1f}"/>')
        o.append(f'<text class="tick" x="{plot_l - 6}" y="{y + 4:.1f}" text-anchor="end">{_esc(fmt(t))}{unit}</text>')
    o.append(f'<line class="axis" x1="{plot_l}" y1="{plot_b}" x2="{plot_r}" y2="{plot_b}"/>')
    o.append(f'<line class="axis" x1="{plot_l}" y1="{top}" x2="{plot_l}" y2="{plot_b}"/>')
    for i, cat in enumerate(categories):
        x0 = sx(i)
        base = plot_b
        for s in segments:
            v = s["values"].get(cat) or 0
            if v <= 0:
                continue
            y1 = sy(v)
            hseg = base - y1
            o.append(f'<rect class="{s["cls"]}" x="{x0:.1f}" y="{y1:.1f}" width="{bw:.1f}" height="{hseg:.1f}" rx="2">'
                     f'<title>{_esc(cat)} · {_esc(s["name"])}: {fmt(v)}{unit}</title></rect>')
            base = y1
        o.append(f'<text class="tick" x="{x0 + bw / 2:.1f}" y="{plot_b + 16}" text-anchor="middle">{_esc(fit_label(cat, bw + 20))}</text>')
        tot = totals[cat]
        o.append(f'<text class="val" x="{x0 + bw / 2:.1f}" y="{sy(tot) - 4:.1f}" text-anchor="middle">{_esc(fmt(tot))}</text>')
    o.append("</svg>")
    return "\n".join(o)


def grouped_vbar(title: str, subtitle: str, categories: list[str], series: list[dict], *, unit: str = "",
                 fmt=None, width: int = 720, plot_h: int = 260) -> str:
    """Vertical grouped bars. series: [{name, cls, values: {category: magnitude}}]."""
    fmt = fmt or (lambda v: f"{v:.3f}")
    vals = [v for s in series for v in s["values"].values() if v is not None]
    ticks = nice_ticks(max(vals or [1]))
    ymax = ticks[-1]
    ns = max(len(series), 1)
    key_w = 16 + sum(22 + text_w(s["name"]) for s in series) + 16
    width = math.ceil(max(width, 90 * len(categories) + 120, key_w, text_w(title, 15) + 32))
    top = 58 + 22 + 10
    plot_l, plot_r = 56, width - 24
    plot_b = top + plot_h
    h = plot_b + 50
    group_w = (plot_r - plot_l) / max(len(categories), 1)
    bar_w = max(8, (group_w - 8) / ns - 2)
    sy = lambda v: plot_b - plot_h * (v / ymax if ymax else 0)  # noqa: E731
    o = _open(width, h, title, subtitle)
    lx = 16
    for s in series:
        o.append(f'<rect class="{s["cls"]}" x="{lx}" y="53" width="10" height="10" rx="2"/>'
                 f'<text class="lbl" x="{lx + 15}" y="62">{_esc(s["name"])}</text>')
        lx += 22 + text_w(s["name"])
    for t in ticks:
        y = sy(t)
        o.append(f'<line class="grid" x1="{plot_l}" y1="{y:.1f}" x2="{plot_r}" y2="{y:.1f}"/>')
        o.append(f'<text class="tick" x="{plot_l - 6}" y="{y + 4:.1f}" text-anchor="end">{_esc(fmt(t))}{unit}</text>')
    o.append(f'<line class="axis" x1="{plot_l}" y1="{plot_b}" x2="{plot_r}" y2="{plot_b}"/>')
    o.append(f'<line class="axis" x1="{plot_l}" y1="{top}" x2="{plot_l}" y2="{plot_b}"/>')
    for i, cat in enumerate(categories):
        gx = plot_l + i * group_w + 4
        o.append(f'<text class="tick" x="{gx + group_w / 2 - 4:.1f}" y="{plot_b + 16}" text-anchor="middle">{_esc(fit_label(cat, group_w - 8))}</text>')
        for j, s in enumerate(series):
            v = s["values"].get(cat)
            if v is None:
                continue
            x = gx + j * (bar_w + 2)
            y = sy(v)
            o.append(f'<rect class="{s["cls"]}" x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{plot_b - y:.1f}" rx="2">'
                     f'<title>{_esc(cat)} · {_esc(s["name"])}: {fmt(v)}{unit}</title></rect>')
            o.append(f'<text class="val" x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" text-anchor="middle">{_esc(fmt(v))}</text>')
    o.append("</svg>")
    return "\n".join(o)


def data_table(title: str, subtitle: str, columns: list[str], rows: list[list[str]], *, width: int = 960) -> str:
    """Readable dark-card table for report metrics (every cell is literal text, not color alone)."""
    col_n = len(columns)
    pad_x, row_h, hdr_h = 10, 28, 32
    col_w = max(72, (width - 32) // col_n)
    width = col_w * col_n + 32
    h = 58 + hdr_h + len(rows) * row_h + 16
    o = _open(width, h, title, subtitle)
    y = 58
    o.append(f'<rect class="axis" x="16" y="{y}" width="{width - 32}" height="{hdr_h}" rx="4" fill="none"/>')
    for j, col in enumerate(columns):
        x = 16 + j * col_w + pad_x
        o.append(f'<text class="grp" x="{x}" y="{y + 20}">{_esc(fit_label(col, col_w - 2 * pad_x))}</text>')
    y += hdr_h
    for i, row in enumerate(rows):
        if i % 2 == 0:
            o.append(f'<rect class="deemph" x="16" y="{y}" width="{width - 32}" height="{row_h}" rx="2" opacity="0.25"/>')
        for j, cell in enumerate(row):
            x = 16 + j * col_w + pad_x
            cls = "val" if j > 0 else "lbl"
            anchor = "end" if j >= len(row) - 4 and j > 0 else "start"
            tx = x + (col_w - 2 * pad_x if anchor == "end" else 0)
            o.append(f'<text class="{cls}" x="{tx}" y="{y + 19}" text-anchor="{anchor}">{_esc(fit_label(cell, col_w - 2 * pad_x))}</text>')
        y += row_h
    o.append("</svg>")
    return "\n".join(o)
