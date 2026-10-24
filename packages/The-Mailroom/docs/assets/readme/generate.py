#!/usr/bin/env python3
"""Generate the README artwork for The-Mailroom (constellation design v2).

    python3 docs/assets/readme/generate.py          # rewrite the SVGs beside this file
    python3 docs/assets/readme/generate.py --check  # read-only drift gate (exit 1 on drift)

`_art.py` is the shared kit (identical in every constellation repo); this file
owns only this repository's labels, scene and facts. Facts come from the README
and `docs/architecture.md`: four surfaces on one display API (`/api/*` + `/ws`),
the seven floor stations (SORTER, EXTRACT, JUDGE, BOSS, REPORT, ARCHIVE and the
human-review siding), the six pixel-console desks, Langfuse as the sole display
source (Phoenix reads mailroom-reloaded), Python 3.11+ and version 0.5.1.
Standard library only, deterministic output.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _art as art  # noqa: E402  (shared kit lives beside this file)

HERO = {
    'title': 'The-Mailroom',
    'kicker': 'THE MAILROOM CONSTELLATION · THE VISUALIZER',
    'tagline': 'Every pipeline run as an animated conveyor of envelopes — driven by real traces.',
    'eyebrow': 'PIXEL CONSOLE · OBSERVATORY · TERMINAL UI · LANGFUSE-ONLY · REPLAY',
    'caption': 'one display API for four surfaces · values on screen are interpreted traces, never canned data',
    'alt': 'Animated banner: a retro CRT showing the pixel-art mailroom floor. Envelopes ride a conveyor past the '
           'SORTER, EXTRACT, JUDGE, BOSS, REPORT and ARCHIVE stations; a flagged one is parked on the REVIEW siding. '
           'The source lamp reads LANGFUSE.',
    'tagline_lines': ['Every pipeline run as an animated', 'conveyor — driven by real traces.'],
    'mobile_cards': [('Floor', 'a conveyor of envelopes'), ('Review', 'the siding as a queue'),
                     ('Replay', 'stored traces, re-run'), ('Surfaces', 'console · Observatory · TUI')],
    'mobile_note': 'Langfuse stays the only display source',
}
STATIONS = [('SORTER', '#f472b6'), ('EXTRACT', '#f59e0b'), ('JUDGE', '#a78bfa'), ('BOSS', '#f87171'),
            ('REPORT', '#7dd3fc'), ('ARCHIVE', '#4ade80'), ('REVIEW', '#facc15')]
DESKS = ['FLOOR', 'REVIEW', 'SESSIONS', 'HISTORY', 'METRICS', 'CONSOLE']
STATS = [('4', 'surfaces · one display API', art.SKY), ('7', 'floor stations · incl. review', art.VIOLET),
         ('6', 'pixel-console desks', art.LIME), ('Langfuse', 'the only display source', art.PINK),
         ('0.5.1', 'current release', art.AMBER), ('3.11+', 'Python', art.GREEN)]
STAGES = [('Trace', 'Langfuse or Phoenix', 'the sole display source'), ('Interpret', 'interpret_trace', 'spans → stations'),
          ('Serve', '/api/* + /ws', 'one display API'), ('Render', 'four surfaces', 'console · Observatory · TUI'),
          ('Act', 'review resolve', 'to the producer API')]
SIDE = [('llm-mailroom', 'Langfuse traces', 'the default producer'), ('mailroom-reloaded', 'Phoenix spans', 'mailroom.node.*'),
        ('Dojo', 'optional [eval]', 'offline evaluation'), ('HF Space', 'live Observatory', 'public Docker Space'),
        ('GH Pages', 'terminal site', 'static snapshot')]
TERMINAL = [('cmd', 'git clone https://github.com/Exios66/The-Mailroom.git'),
            ('cmd', 'cd The-Mailroom && pip install -e ".[dev]"'),
            ('cmd', 'cp .env.example .env'),
            ('note', '# add LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY'),
            ('cmd', 'mailroom-web'),
            ('note', '# → http://127.0.0.1:8001 · the Observatory is also at /live'),
            ('cmd', 'mailroom-tui --once --view floor'),
            ('note', '# one terminal frame, for scripting'),
            ('cmd', 'python scripts/seed_demo.py'),
            ('note', '# seeds demo runs into Langfuse, so nothing on screen is canned')]
TUI_GAUGES = [('pixel console', 'mailroom-web', None, art.SKY), ('Observatory', '/live · hosted', None, art.VIOLET),
              ('terminal UI', 'mailroom-tui', None, art.LIME), ('terminal site', 'GitHub Pages', None, art.PINK),
              ('data source', 'Langfuse only', None, art.GREEN)]
TUI_LOG = [('info', '*** Beginning station: SORTER ***'), ('ok', 'judge verdict banners as runs advance'),
           ('warn', 'review siding: waiting on a human'), ('info', 'REPLAY re-runs a stored trace'),
           ('ok', 'floor snapshots stream over /ws')]
TUI_STATUS = '[f]loor [r]eview [s]essions [m]etrics [i]nspect [ ] [d]ebug [q]uit'

PENV = ('<g id="penv"><rect width="22" height="15" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.5"/>'
        '<rect x="3" y="3" width="6" height="4" fill="#6366f1"/><rect x="3" y="10" width="14" height="1.6" fill="#94a3b8"/></g>')


def scene() -> str:
    """A retro CRT showing the floor: desks along the top, stations on a belt, envelopes in motion."""
    x0, y0, w, h = 100, 226, 1000, 172
    out = [f'<defs>{PENV}<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
           '<rect width="4" height="1" fill="#ffffff" opacity=".05"/></pattern></defs>',
           f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" rx="14" fill="#05080f" stroke="#3b4660" stroke-width="2.5"/>',
           f'<rect x="{x0 + 3}" y="{y0 + 3}" width="{w - 6}" height="{h - 6}" rx="12" fill="url(#scan)"/>',
           art.text(x0 + 22, y0 + 26, 'THE MAILROOM', 14, '#e2e8f0', 800, spacing=5, family=art.MONO),
           art.text(x0 + 215, y0 + 26, 'LLM-MAILROOM VISUAL ENGINE', 10, '#475569', 600, spacing=2, family=art.MONO),
           f'<circle cx="{x0 + w - 190}" cy="{y0 + 21}" r="5" fill="#4ade80"/>',
           art.text(x0 + w - 176, y0 + 26, 'SOURCE: LANGFUSE', 12, '#cbd5e1', 600, family=art.MONO)]
    dx = x0 + 22
    for name in DESKS:
        out.append(art.text(dx, y0 + 52, name, 10.5, '#8b9bb4' if name != 'FLOOR' else '#fef3c7', 700, spacing=2, family=art.MONO))
        if name == 'FLOOR':
            out.append(f'<rect x="{dx}" y="{y0 + 57}" width="{len(name) * 9 + 4}" height="2" fill="#f59e0b"/>')
        dx += len(name) * 9 + 36
    by = y0 + 126
    out.append(f'<rect x="{x0 + 14}" y="{by}" width="{w - 28}" height="14" rx="3" fill="#1b2231" stroke="#2f3a52"/>')
    out.append(f'<path d="M{x0 + 14} {by + 7} H{x0 + w - 14}" stroke="#334155" stroke-width="1.5" stroke-dasharray="8 8"/>')
    step = (w - 100) / (len(STATIONS) - 1)
    for i, (name, color) in enumerate(STATIONS):
        cx = x0 + 50 + i * step
        out.append(art.text(cx, y0 + 96, name, 11, color, 800, 'middle', spacing=1.5, family=art.MONO))
        out.append(f'<rect x="{art.num(cx - 38)}" y="{y0 + 102}" width="76" height="3" fill="{color}"/>')
        out.append(f'<rect x="{art.num(cx - 38)}" y="{by - 3}" width="76" height="3" fill="#78350f"/>')
    for i in (1, 6):  # static envelopes parked at EXTRACT and on the review siding
        cx = x0 + 50 + i * step
        out.append(f'<use href="#penv" x="{art.num(cx - 30)}" y="{by - 20}"/>')
    out.append(f'<use href="#penv" x="{art.num(x0 + 50 + 6 * step - 4)}" y="{by - 20}"/>')
    out.append(f'<path id="crt" d="M{x0 + 20} {by - 12} H{x0 + w - 20}" fill="none"/>')
    out.append('<g class="motion">' + ''.join(
        f'<use href="#penv" opacity="0"><animateMotion dur="7s" begin="{k * 1.75}s" repeatCount="indefinite"><mpath href="#crt"/></animateMotion>'
        f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.05;.93;1" dur="7s" begin="{k * 1.75}s" repeatCount="indefinite"/></use>'
        for k in range(4)) + '</g>')
    out.append(art.text(x0 + w / 2, y0 + h - 8, 'click an envelope to inspect its run', 10.5, '#475569', anchor='middle', family=art.MONO))
    return '\n'.join(out)


def build() -> dict[str, str]:
    """Return every generated asset keyed by file name."""
    flow_desc = ('Traces from Langfuse (or Phoenix) are interpreted into stations, served over one display API and '
                 'rendered by four surfaces; review decisions go back to the producer.')
    return {
        'hero.svg': art.hero(HERO, scene),
        'hero-mobile.svg': art.hero(HERO, mobile=True),
        'stats.svg': art.stats(STATS, 'The-Mailroom by the numbers'),
        'stats-mobile.svg': art.stats(STATS, 'The-Mailroom by the numbers', mobile=True),
        'flow.svg': art.flow('From a trace to a screen', STAGES, SIDE, 'What it reads and where it runs', desc=flow_desc,
                             side_color=art.PINK),
        'flow-mobile.svg': art.flow('From a trace to a screen', STAGES, SIDE, 'What it reads and where it runs',
                                    mobile=True, desc=flow_desc, side_color=art.PINK),
        'constellation.svg': art.constellation('The-Mailroom'),
        'constellation-mobile.svg': art.constellation('The-Mailroom', mobile=True),
        'tui.svg': art.tui('~/The-Mailroom — mailroom-tui', TUI_GAUGES, TUI_LOG, TUI_STATUS,
                           'Dashboard: the four surfaces and the Langfuse-only source, and a sample of what the terminal '
                           'UI prints as runs advance.', left='SURFACES', right='FLOOR LOG'),
        'terminal.svg': art.terminal('~/The-Mailroom — zsh', TERMINAL,
                                     'Animated terminal: clone, install, add Langfuse keys, start the pixel console, print '
                                     'one terminal frame and seed demo runs.'),
    }


def main() -> None:
    """Write the assets, or compare them byte-for-byte with --check."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='fail on drift without writing')
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    drift = []
    for name, content in build().items():
        path = base / name
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8') != content:
                drift.append(name)
        else:
            path.write_text(content, encoding='utf-8')
    if drift:
        parser.exit(1, 'README asset drift: ' + ', '.join(drift) + '\n')
    print('README assets match' if args.check else 'README assets written')


if __name__ == '__main__':
    main()
