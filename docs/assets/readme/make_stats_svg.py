"""Render docs/assets/readme/stats.svg for the root README.

    python3 docs/assets/readme/make_stats_svg.py docs/assets/readme/stats.svg
"""
import sys
stats = [
    ("5", "core packages", "#38bdf8"),
    ("13", "pipeline nodes", "#22c55e"),
    ("5", "document classes", "#a3e635"),
    ("3,302", "corpus rows (v9)", "#facc15"),
    ("15", "specialist agents", "#c084fc"),
    ("1", "lockfile to rule them", "#f472b6"),
]
W, H, PAD = 1200, 170, 20
cw = (W - PAD * 2) / len(stats)
o = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d"
     font-family="ui-sans-serif,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif">
  <title id="t">Digital Mailroom by the numbers</title>
  <desc id="d">{"; ".join(f"{v} {l}" for v, l, _ in stats)}.</desc>
  <rect width="{W}" height="{H}" rx="22" fill="#0b1220"/>''']
for i, (v, label, c) in enumerate(stats):
    x = PAD + i * cw
    cx = x + cw / 2
    d = 0.15 * i
    o.append(f'''  <g>
    <animateTransform attributeName="transform" type="translate" values="0 0;0 -4;0 0" dur="3s" begin="{d:.2f}s" repeatCount="indefinite"/>
    <rect x="{x+8:.0f}" y="20" width="{cw-16:.0f}" height="130" rx="16" fill="#111a2e" stroke="#1f2a44"/>
    <text x="{cx:.0f}" y="86" text-anchor="middle" font-size="46" font-weight="800" fill="{c}">{v}</text>
    <text x="{cx:.0f}" y="116" text-anchor="middle" font-size="14" fill="#94a3b8">{label}</text>
    <rect x="{cx-22:.0f}" y="130" width="44" height="4" rx="2" fill="{c}">
      <animate attributeName="width" values="44;84;44" dur="3s" begin="{d:.2f}s" repeatCount="indefinite"/>
      <animate attributeName="x" values="{cx-22:.0f};{cx-42:.0f};{cx-22:.0f}" dur="3s" begin="{d:.2f}s" repeatCount="indefinite"/>
    </rect>
  </g>''')
o.append("</svg>")
open(sys.argv[1], "w").write("\n".join(o) + "\n")
