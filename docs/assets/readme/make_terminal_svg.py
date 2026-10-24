"""Render docs/assets/readme/terminal.svg for the root README.

    python3 docs/assets/readme/make_terminal_svg.py docs/assets/readme/terminal.svg
"""
import html, sys
lines = [
    ("cmd", "git clone https://github.com/LLM-Mailroom-Services/Digital-Mailroom.git"),
    ("cmd", "cd Digital-Mailroom && uv sync"),
    ("note", "# one workspace · one lockfile · one .venv"),
    ("cmd", "uv run pytest packages/llm-dojo-scoring/tests -q"),
    ("note", "# one package per pytest run — your local run is the gate"),
    ("cmd", "python scripts/sync_packages.py status"),
    ("note", "# drift report: hub copies vs. their standalone sources"),
    ("cmd", "python scripts/board_state.py status"),
    ("note", "# who is working on what, straight from governance/TASKS.md"),
]
CW, FS, TOP, STEP = 9.2, 15, 92, 30
W, H = 900, TOP + STEP * len(lines) + 30
out = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d"
     font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace">
  <title id="t">Quickstart terminal</title>
  <desc id="d">Animated terminal typing the Digital Mailroom quickstart: clone, uv sync, run a package suite, check package sync status and the board status.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#161b2e"/></linearGradient>
  </defs>
  <rect id="cyc" width="1" height="1" fill="none"><animate id="loop" attributeName="x" from="0" to="0" dur="22s" begin="0s;loop.end"/></rect>
  <rect x="1" y="1" width="{W-2}" height="{H-2}" rx="16" fill="url(#bg)" stroke="#30363d" stroke-width="2"/>
  <rect x="1" y="1" width="{W-2}" height="44" rx="16" fill="#1c2230"/>
  <rect x="1" y="30" width="{W-2}" height="15" fill="#1c2230"/>
  <circle cx="30" cy="23" r="7" fill="#ff5f57"/><circle cx="54" cy="23" r="7" fill="#febc2e"/><circle cx="78" cy="23" r="7" fill="#28c840"/>
  <text x="{W//2}" y="28" text-anchor="middle" font-size="13" fill="#8b949e">~/Digital-Mailroom — zsh</text>''']
t = 0.6
for i, (kind, text) in enumerate(lines):
    y = TOP + i * STEP
    prefix = "$ " if kind == "cmd" else "  "
    full = prefix + text
    width = len(full) * CW + 24
    dur = round(len(full) * 0.04, 2) if kind == "cmd" else 0.35
    out.append(f'''  <clipPath id="c{i}"><rect x="30" y="{y-20}" height="28" width="0">
    <set attributeName="width" to="0" begin="loop.begin"/>
    <animate attributeName="width" from="0" to="{width:.0f}" dur="{dur}s" begin="loop.begin+{t:.2f}s" fill="freeze"/></rect></clipPath>''')
    if kind == "cmd":
        out.append(f'  <text x="32" y="{y}" font-size="{FS}" clip-path="url(#c{i})"><tspan fill="#7ee787">$ </tspan><tspan fill="#e6edf3">{html.escape(text)}</tspan></text>')
    else:
        out.append(f'  <text x="32" y="{y}" font-size="{FS}" clip-path="url(#c{i})" fill="#8b949e" font-style="italic">{html.escape(full)}</text>')
    t += dur + (0.9 if kind == "cmd" else 0.5)
assert t < 19, t
y = TOP + len(lines) * STEP
out.append(f'''  <rect x="32" y="{y-16}" width="9" height="19" fill="#e6edf3"><animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect>
</svg>''')
open(sys.argv[1], "w").write("\n".join(out) + "\n")
print("cycle used", round(t, 2))
