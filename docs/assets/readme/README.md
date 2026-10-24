# Hub README artwork

The hub keeps its established data-flow map, including both sandbox and
pipeline traces into Langfuse. `make_constellation_svg.py` owns that map;
the standalone repositories own their separate shared artwork kit.

```bash
python3 docs/assets/readme/make_constellation_svg.py
python3 docs/assets/readme/make_constellation_svg.py --check
python3 -m http.server 8008 --bind 127.0.0.1
```

Open `http://127.0.0.1:8008/docs/assets/readme/layout-check.html` and require
**PASS**. It measures actual glyph bounds and padded callouts, node/canvas
clearances and paint order at 0, 0.7, 1.5 and 3 seconds. Text stays above
particles; reduced-motion hides only `.motion` elements. Generated SVGs are
self-contained and contain no scripts or remote fonts.
