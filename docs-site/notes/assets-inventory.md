<div align="center">

# 📁 Documentation Assets

**Deployment assets for [The Digital Mailroom](https://mailroom-inc.gitbook.io/the-digital-mailroom/) GitBook.**

</div>

---

## Contents

Images, diagrams, and mascot art used by this documentation site. This folder is the **single source of truth** for the site's assets — the GitBook is built from `docs/`.

- `banner.png` — masthead banner (the night-shift owl at the sorting desk)
- `mailroom-pipeline.svg` — pipeline diagram
- `fumi/fumi.gif` — GitBook home copy of Fumi (on-duty + Meet Fumi; not the page header)
- `mascot/` — the full **Fumi + Hermes** set (see `mascot/README.md`): `fumi.svg`, `fumi.gif`, `fumi.png`, `fumi-icon.png`, `fumi-sheet.png`, `hoot-icon.png` (Hermes, the page favicon), and the source sprite `source/fumi-base.png`

The GitBook-referenced copies live in [`../.gitbook/assets/`](/assets/) (`banner.png`, `fumi.gif`, `hoot-icon.png`). That folder also holds the generated `chart-*.svg` files, which `scripts/build_charts.py` writes. They have no source copy here.

## Usage

Assets are referenced by documentation files in `docs/`. GitBook strips scripts and may not animate SVG, so use `fumi.gif` where a still SVG will not animate.

## Related Files

- `../.gitbook/assets/` — the GitBook-referenced asset copies
- `../` — documentation root (`README.md`, `SUMMARY.md`)
