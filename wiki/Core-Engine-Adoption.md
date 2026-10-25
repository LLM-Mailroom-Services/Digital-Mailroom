# Optional offline evaluation engine (DMR-091 proposal)

Offline evaluation depends on the canonical Dojo 0.23.1 engine through the
immutable release requirement in `[eval]`. The development extra includes eval
for the complete test suite. Workspace redirects resolve the same engine in
Digital-Mailroom; standalone installs retain the release requirement.

Install `pip install -e '.[eval]'` to use the offline
`scripts/eval_pipeline.py` and production-pilot scoring. Default display and
server imports stay light: importing `mailroom_ui.pipeline_eval` does not load
Dojo. Calling a scorer without the required API raises an actionable ImportError;
there is no local scoring fallback. This eval-only use follows the user's
explicit Dojo-owns-scoring direction and supersedes the older blanket no-Dojo
rule in source AGENTS/skills for offline eval only.

The facade retains existing function names and report keys. The eval script
now calls its additive `exact` adapter instead of recomputing equality; every
existing GT guard is retained. Producer subclass
field lifting and telemetry/intake display aggregation remain here. Quality
predicates, lifecycle failure priority, all-row accuracy, sparse confusion and
by-class counts delegate to Dojo. Explicit subclass False wins; absent subclass
GT is excluded, absent prediction is a miss, failed rows with GT remain in
support. Unlabeled rows remain in the old class denominator. Supplied exact/
aligned flags are trusted, not inferred. Literal class policy differs from
pipeline trim/lowercase policy; unknown tokens do not collapse to other.

The canonical predicates reject absent GT/predictions, missing alias entries
and whitespace-only subclass tokens. This closes missing-label false positives
while preserving valid-label semantics. Lifecycle `archived` bypasses empty
extraction but `archive` does not. Missing display telemetry
retains its legacy zero defaults. Nonfinite telemetry is not silently cleaned:
NaN cost/latency propagates and invalid token conversion raises.

`tests/test_core_engine_delegation.py` observes real Dojo calls on row dictionaries
and runs a subprocess with `-I -S` to prove the facade imports without Dojo and
fails clearly when optional evaluation is requested. Run it with the existing
`tests/test_eval_pipeline.py` and the full source suite after release adoption.
Display still uses Langfuse as its source of truth; no serving path changes.
