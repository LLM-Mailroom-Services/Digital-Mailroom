# Package marker.
#
# Monorepo: sibling llm-mailroom's editable install exposes src/scripts as a
# regular top-level `scripts` package, which would otherwise shadow this
# namespace (regular packages always beat PEP-420 portions regardless of
# sys.path order). With this marker, ROOT at sys.path[0] (tests/conftest.py)
# wins for `from scripts.demo_pilot_run import ...` etc.
