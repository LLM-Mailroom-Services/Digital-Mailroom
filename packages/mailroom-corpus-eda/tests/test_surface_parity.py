"""mailroom-issues#75 — subclass-surface parity guard: re-derive the observed
``expected_subclass`` surfaces from the pinned v9 ground_truth parquet and
fail if the scoring vocab (llm-dojo-scoring ``CORPUS_SUBCLASS_SURFACES``) or
the build vocab (``mailroom_eda.v9_build.EXPECTED_SUBCLASS_BY_CLASS``) drifts
from the data, so surface drift fails CI instead of the reviewer.

Data surface = the canonical source of truth (mailroom-dataset v9, tip
46a4d3c2 — the snapshot under ``data/parquet`` is fetched at that pin by
``run_all.py`` P0 / ``download.download_corpus``). The scoring and build
catalogs below MUST agree with it.

Modelled on test_hub57_truth.py (cross-package catalogs pinned to the live
Hub revision) and the conftest snapshot convention (skips when the local HF
snapshot is absent — gitignored; fetch via ``run_all.py --phases P0``).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "llm-dojo-scoring"))

from mailroom_eda.v9_build import EXPECTED_SUBCLASS_BY_CLASS  # noqa: E402

# Five corpus classes are the only ground-truth doc_types in the v9 merge.
CLASSES = (
    "contract",
    "merger_agreement",
    "corporate_record",
    "correspondence",
    "insurance_claim",
)


def _observed_surfaces(snapshot_rows: list[dict]) -> dict[str, set[str]]:
    surfaces: dict[str, set[str]] = {c: set() for c in CLASSES}
    for row in snapshot_rows:
        doc_type = row.get("expected")
        subcls = row.get("expected_subclass")
        if doc_type in surfaces and isinstance(subcls, str) and subcls:
            surfaces[doc_type].add(subcls)
    return surfaces


def test_scoring_surfaces_match_pinned_v9_data(snapshot_rows):
    """llm-dojo CORPUS_SUBCLASS_SURFACES == observed ground_truth surfaces."""
    from llm_dojo_scoring.corpus import CORPUS_SUBCLASS_SURFACES

    observed = _observed_surfaces(snapshot_rows)
    # ordered-tuple comparison on top of set equality: a rename or a reorder
    # of the catalog is drift too
    for doc_type in CLASSES:
        assert set(CORPUS_SUBCLASS_SURFACES[doc_type]) == observed[doc_type], (
            f"{doc_type} scoring surface drifted: "
            f"{sorted(CORPUS_SUBCLASS_SURFACES[doc_type])} != {sorted(observed[doc_type])}"
        )
        assert tuple(CORPUS_SUBCLASS_SURFACES[doc_type]) == tuple(sorted(observed[doc_type])), (
            f"{doc_type} scoring surface order drifted: "
            f"{CORPUS_SUBCLASS_SURFACES[doc_type]}"
        )


def test_build_vocab_matches_pinned_v9_data(snapshot_rows):
    """v9_build.EXPECTED_SUBCLASS_BY_CLASS == observed ground_truth surfaces."""
    observed = _observed_surfaces(snapshot_rows)
    for doc_type in CLASSES:
        assert set(EXPECTED_SUBCLASS_BY_CLASS[doc_type]) == observed[doc_type], (
            f"{doc_type} build vocab drifted: "
            f"{sorted(EXPECTED_SUBCLASS_BY_CLASS[doc_type])} != {sorted(observed[doc_type])}"
        )


def test_scoring_and_build_vocabularies_agree(snapshot_rows):
    """The two in-repo constants must agree with each other (three-way pin)."""
    from llm_dojo_scoring.corpus import CORPUS_SUBCLASS_SURFACES

    for doc_type in CLASSES:
        assert set(CORPUS_SUBCLASS_SURFACES[doc_type]) == set(
            EXPECTED_SUBCLASS_BY_CLASS[doc_type]
        ), (
            f"{doc_type}: scoring {sorted(CORPUS_SUBCLASS_SURFACES[doc_type])} != "
            f"build {sorted(EXPECTED_SUBCLASS_BY_CLASS[doc_type])}"
        )