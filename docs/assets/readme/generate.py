#!/usr/bin/env python3
"""Generate the README artwork for local-mailroom-sandbox (constellation design v2).

    python3 docs/assets/readme/generate.py          # rewrite the SVGs beside this file
    python3 docs/assets/readme/generate.py --check  # read-only drift gate (exit 1 on drift)

`_art.py` is the shared kit (identical in every constellation repo); this file
owns only this repository's labels, scene and facts. Facts come from the README,
`config/profiles/` (seven provider profiles; Ollama `qwen3:8b` default with a
`qwen3:7b` fallback), `vendor/` (two tracked snapshots: llm-mailroom and
llm-dojo-scoring) and the `sandbox` CLI in `src/mailroom_sandbox/cli.py`.
Standard library only, deterministic output.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _art as art  # noqa: E402  (shared kit lives beside this file)

HERO = {
    'title': 'local-mailroom-sandbox',
    'kicker': 'THE MAILROOM CONSTELLATION · THE SANDBOX',
    'tagline': 'Run the whole mailroom on your own machine — or on a rented GPU — and score every run.',
    'eyebrow': 'SEVEN PROVIDER PROFILES · VENDORED PIPELINE + DOJO · MOCK FIRST · LIVE OR LOUD',
    'caption': 'Ollama qwen3:8b by default · vLLM, Modal, llama.cpp, LM Studio or OpenRouter by profile · Langfuse traces',
    'alt': 'Animated banner: seven provider profiles (Ollama, vLLM local, vLLM remote, Modal vLLM, llama.cpp, '
           'LM Studio, OpenRouter) feed the vendored 13-node llm-mailroom graph, whose runs are scored by the '
           'vendored llm-dojo-scoring and traced to Langfuse.',
    'tagline_lines': ['Run the whole mailroom on your', 'own machine, and score every run.'],
    'mobile_cards': [('Serve', 'seven provider profiles'), ('Run', 'vendored 13-node graph'),
                     ('Score', 'vendored llm-dojo-scoring'), ('Trace', 'Langfuse · The-Mailroom')],
    'mobile_note': 'Ollama qwen3:8b default · mock first, then local',
    'mobile_title_size': 38,
}
PROFILES = [('ollama', art.GREEN), ('vllm-local', art.SKY), ('vllm-remote', art.SKY), ('modal-vllm', art.VIOLET),
            ('llamacpp', art.YELLOW), ('lmstudio', art.ORANGE), ('openrouter', art.PINK)]
STATS = [('7', 'provider profiles', art.SKY), ('2', 'vendored snapshots', art.VIOLET), ('13', 'graph nodes', art.LIME),
         ('5', 'document classes', art.YELLOW), ('3,302', 'rows · pinned pull', art.PINK),
         ('--mock', 'no LLM needed', art.GREEN)]
STAGES = [('Install', 'pip install -e', '".[dev]"'), ('Up', 'sandbox up', 'Langfuse + Ollama'),
          ('Models', 'pull-models', 'qwen3:8b'), ('Health', 'sandbox health', 'provider + sinks'),
          ('Mock', 'pilot --mock', 'machinery only'), ('Local', 'pilot --local', 'real local model'),
          ('Score', 'sandbox eval', 'vendored dojo')]
SIDE = [('Matrix', 'sandbox matrix', 'providers × models'), ('Runs', 'sandbox run start', 'config/runs/*.yaml'),
        ('Modal', '--job-mode modal', 'GPU worker'), ('Compare', 'metrics compare', 'local · modal · api'),
        ('Watch', 'sandbox watch', 'mailroom TUI')]
TERMINAL = [('cmd', 'pip install -e ".[dev]"'),
            ('cmd', 'cp config/.env.example .env'),
            ('cmd', 'sandbox up'),
            ('note', '# compose profiles: langfuse + ollama'),
            ('cmd', 'sandbox pull-models'),
            ('note', '# ollama pull qwen3:8b'),
            ('cmd', 'sandbox health'),
            ('cmd', 'sandbox pilot --mock'),
            ('note', '# machinery only, no LLM'),
            ('cmd', 'sandbox pilot --local'),
            ('note', '# the same pipeline on your local model')]
TUI_GAUGES = [('ollama', 'qwen3:8b', 1.0, art.GREEN), ('vllm-local', 'local GPU', 0.8, art.SKY),
              ('vllm-remote', 'tunnel', 0.8, art.SKY), ('modal-vllm', 'Modal', 0.8, art.VIOLET),
              ('llamacpp', 'port 8080', 0.6, art.YELLOW), ('lmstudio', 'desktop', 0.6, art.ORANGE),
              ('openrouter', 'API', 0.5, art.PINK)]
TUI_LOG = [('ok', 'vendor/llm-mailroom snapshot loaded'), ('ok', 'vendor/llm-dojo-scoring snapshot loaded'),
           ('info', 'profile ollama · qwen3:8b'), ('ok', 'pilot --mock: machinery green'),
           ('info', 'traces → Langfuse document-pipeline'),
           ('warn', 'vllm-local without --local: warns, no mock')]
TUI_STATUS = 'sandbox profiles · seven profiles · bar length is illustrative, not a benchmark'


def scene() -> str:
    """Seven provider chips feed the vendored graph, which hands runs to the dojo and Langfuse."""
    out = [art.text(150, 232, 'PROVIDER PROFILES', 11, '#8b9bb4', 700, spacing=2)]
    paths = []
    for i, (name, color) in enumerate(PROFILES):
        y = 240 + i * 22
        out.append(art.chip(150, y, 160, 19, name, color, size=11))
        paths.append(f'<path id="pp{i}" d="M310 {y + 9.5} C400 {y + 9.5} 400 318 480 318"/>')
    out.append('<defs>' + ''.join(paths) + '</defs>')
    out.append('<g fill="none" stroke="#334155" stroke-width="1.5">'
               + ''.join(f'<use href="#pp{i}"/>' for i in range(len(PROFILES))) + '</g>')
    out.append('<g class="motion">' + ''.join(art.particle(f'pp{i}', 2.2, i * 0.45, color, 4)
                                              for i, (_, color) in enumerate(PROFILES)) + '</g>')
    out.append(f'<rect x="480" y="262" width="270" height="112" rx="16" fill="{art.PANEL}" stroke="{art.LIME}" stroke-width="2"/>')
    out.append(art.text(615, 296, 'vendor/llm-mailroom', 17, art.INK, 700, 'middle', family=art.MONO))
    out.append(art.text(615, 322, '13-node LangGraph pipeline', 14, art.MUTED, anchor='middle'))
    out.append(art.text(615, 346, 'classify → extract → compile → archive', 12, art.DIM, anchor='middle'))
    out.append(art.pulse_ring(480, 262, 270, 112, art.LIME))
    for k, (label, sub, color, y) in enumerate([('vendor/llm-dojo-scoring', 'score every run', art.VIOLET, 262),
                                                 ('Langfuse', 'trace → The-Mailroom', art.SKY, 322)]):
        out.append(f'<rect x="850" y="{y}" width="260" height="52" rx="12" fill="{art.PANEL}" stroke="{color}" stroke-width="1.8"/>')
        out.append(art.text(980, y + 22, label, 14, art.INK, 700, 'middle', family=art.MONO))
        out.append(art.text(980, y + 41, sub, 12, art.MUTED, anchor='middle'))
        out.append(art.arrow(750, 318, 846, y + 26, color))
        out.append(f'<path id="po{k}" d="M750 318 L846 {y + 26}" fill="none"/>')
        out.append('<g class="motion">' + art.particle(f'po{k}', 1.4, k * 0.7, color, 4) + '</g>')
    return '\n'.join(out)


def build() -> dict[str, str]:
    """Return every generated asset keyed by file name."""
    flow_desc = ('The local path from install to a scored run: install, bring up Langfuse and Ollama, pull the model, '
                 'probe the provider and trace sinks, run the pilot with the mock and then a local model, and score with the vendored dojo; '
                 'matrix, run specs, Modal workers, comparisons and the watch TUI branch off it.')
    return {
        'hero.svg': art.hero(HERO, scene),
        'hero-mobile.svg': art.hero(HERO, mobile=True),
        'stats.svg': art.stats(STATS, 'local-mailroom-sandbox by the numbers'),
        'stats-mobile.svg': art.stats(STATS, 'local-mailroom-sandbox by the numbers', mobile=True),
        'flow.svg': art.flow('Mock first, then local, then scored', STAGES, SIDE, 'When you scale out',
                             desc=flow_desc, side_color=art.VIOLET),
        'flow-mobile.svg': art.flow('Mock first, then local, then scored', STAGES, SIDE, 'When you scale out',
                                    mobile=True, desc=flow_desc, side_color=art.VIOLET),
        'constellation.svg': art.constellation('local-mailroom-sandbox'),
        'constellation-mobile.svg': art.constellation('local-mailroom-sandbox', mobile=True),
        'tui.svg': art.tui('~/local-mailroom-sandbox — sandbox profiles', TUI_GAUGES, TUI_LOG, TUI_STATUS,
                           'Dashboard: the seven provider profiles with what each targets, and a log of a mock '
                           'pilot run on the default Ollama profile.', left='PROVIDER PROFILES', right='RUN LOG'),
        'terminal.svg': art.terminal('~/local-mailroom-sandbox — zsh', TERMINAL,
                                     'Animated terminal: install, copy the env file, bring up Langfuse and Ollama, '
                                     'pull the model, check health, then run the pilot with the mock and with a local model.'),
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
