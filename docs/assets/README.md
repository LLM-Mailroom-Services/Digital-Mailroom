<div align="center">

# 📁 Documentation Assets

**Shared documentation assets for the Digital-Mailroom monorepo.**

</div>

---

## Contents

Images, diagrams, and other assets used in documentation.

| Asset | Used by | Notes |
| --- | --- | --- |
| `mailroom-pipeline.svg` | README, wiki | Canonical 13-node pipeline diagram (source of truth) |
| `mailroom-processing-banner.svg` / `-dark.svg` | README | Six-stage processing banner, light and dark |
| `readme/hero.svg` | README | Animated conveyor hero (SMIL, no scripts) |
| `readme/constellation.svg` | README | Animated package data-flow map |
| `readme/stats.svg` | README | "By the numbers" strip, regenerate with `make_stats_svg.py` |
| `readme/terminal.svg` | README | Typing quickstart terminal, regenerate with `make_terminal_svg.py` |
| `readme/sorting-floor.gif` | README | Pixel-art sorting loop, regenerate with `uv run --frozen python docs/assets/readme/make_sorting_gif.py` |

Keep the README numbers in `make_stats_svg.py` in step with `AGENTS.md`
(package count, dataset rows, roster size) when they change.

## Usage

Assets are referenced by documentation files in `docs/`.

## Related Files

- `../` — Documentation root
- `../reports/` — Evaluation reports
- `../wiki/` — GitHub wiki pages
