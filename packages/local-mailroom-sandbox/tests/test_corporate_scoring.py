"""Sandbox #145 vendor bump: ``score_extraction_row`` drives the per-subclass dojo machinery.

The sandbox scores a corporate-record row through the SAME vendored alignment
the dojo's ``suites._score_extraction`` runs (``align_unlabeled`` +
``corporate_record_schema``) — wired via ``doc_subclass``/``expected_subclass``.
The original cache cases check WIRING: their expectations are computed IN TEST from
the vendored module (no hardcoded numbers), so a scoring bump that changes the
alignment semantics still passes as long as the sandbox faithfully forwards
the subclass to the vendored engine. Unconditional annotated-field cases below
also pin independent hand-computed scores and require no local corpus cache.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from mailroom_sandbox.eval.scoring import score_extraction_row

REPO = Path(__file__).resolve().parents[1]


def _real_row(doc_class: str, subclass: str | None = None) -> dict[str, Any]:
    """One REAL published-v9.2 row from the installed corpus cache.

    Skipped (not stubbed) when the cache is absent, so a fixture never drifts
    from the published GT shape this wiring must serve. With *subclass* the row
    must carry that ``expected_subclass`` (corporate-record machinery); without
    it the first row of *doc_class* is used — the published rows all carry an
    ``expected_subclass`` key, so the subclass-forwarding pin (below) runs on
    the value the dataset actually stores.
    """
    for cache in sorted((REPO / "data" / "cache").glob("*mailroom-dataset*")):
        gt = cache / "ground_truth_all.jsonl"
        if not gt.is_file():
            continue
        for line in gt.open(encoding="utf-8"):
            row = json.loads(line)
            if row.get("expected_doc_class") != doc_class:
                continue
            if (
                subclass is not None
                and str(row.get("expected_subclass") or "").lower() != subclass
            ):
                continue
            return row
    pytest.skip(f"no {doc_class}/{subclass} GT row in the installed corpus cache")


def _real_corporate_row(subclass: str = "bylaws") -> dict[str, Any]:
    """One REAL published-v9.2 corporate row of *subclass* (see :func:`_real_row`)."""
    return _real_row("corporate_record", subclass)


def test_corporate_row_scores_with_dojo_alignment():
    from llm_dojo_scoring import suite_for_doc_type
    from llm_dojo_scoring.corporate_record_schema import align_unlabeled

    row = _real_corporate_row("bylaws")
    expected = row["expected_fields"]
    # A realistic prediction: the labeled semantic trio plus subclass entity
    # keys the published GT leaves blank WITHOUT documenting absence.
    predicted = dict(expected)
    predicted["intent"] = expected.get("intent")
    predicted["subject_matter"] = "bylaws of the registrant"
    predicted["keywords"] = ["bylaws", "EX-3.2"]
    predicted["entity_name"] = "NCM Financial, Inc."
    predicted["certifying_officer"] = "Michael Noel"
    predicted["principal"] = "Someone Else"  # another subclass's extension key

    scored = score_extraction_row(
        "corporate_record",
        predicted,
        expected,
        doc_text=row.get("doc_text"),
        expected_subclass=row.get("expected_subclass"),
    )

    # Dojo-side expectation, computed IN TEST from the vendored module.
    dojo_expected, dojo_predicted, dojo_dropped = align_unlabeled(
        row.get("expected_subclass"), expected, expected, predicted
    )
    assert dojo_dropped, "the fixture must exercise unlabeled fields"
    # 1. per-row unlabeled_fields match the dojo payload exactly
    assert scored["unlabeled_fields"] == list(dojo_dropped)
    # 2. the headline equals the vendored engine on the aligned pair
    reference = suite_for_doc_type("corporate_record").score(
        dojo_expected, dojo_predicted, doc_text=row.get("doc_text")
    )
    assert scored["overall_extraction_score"] == pytest.approx(
        reference.overall_score, abs=1e-9
    )
    # 3. a subclass entity the GT never labeled was aligned out, not charged
    #    as a spurious fill: score the unaligned pair the OLD (pre-#145) way
    #    and confirm the wired path scores STRICTLY not-worse.
    raw_reference = suite_for_doc_type("corporate_record").score(
        expected, predicted, doc_text=row.get("doc_text")
    )
    assert scored["overall_extraction_score"] >= raw_reference.overall_score - 1e-9


_PIN_DOC_TYPES = (
    "contract",
    "correspondence",
    "insurance_claim",
    "merger_agreement",
    "corporate_record",
)


@pytest.mark.parametrize("doc_type", _PIN_DOC_TYPES)
def test_expected_subclass_is_score_comparable(doc_type: str):
    """Equality pin: ``expected_subclass=`` must NEVER move a number.

    Pins the 3,302-row comparability invariant the native adversarial review
    PROVED NUMERICALLY for PR #145: forwarding the row's stored
    ``expected_subclass`` into :func:`score_extraction_row` left the scores
    identical old-vs-new across ALL 3,302 published corpus rows. On one REAL
    row per doc type (the same installed corpus cache every other test here
    reads), this asserts against the same call WITHOUT the kwarg:

    * every numeric payload field — all five ``_EXTRACT_PRF_KEYS`` plus
      ``overall_extraction_score`` — is byte-identical (a wiring bug that
      changed any score on any doc type fails here), and
    * the key-set delta is exactly within the two keys the subclass path may
      add — the dojo's per-row ``unlabeled_fields`` provenance and the
      detailed ``fields`` provenance block. No number may disappear.

    The subclass is allowed to change provenance (that is the entire point of
    the machinery); it is NOT allowed to change what the row scored.
    """
    from mailroom_sandbox.eval.scoring import _EXTRACT_PRF_KEYS

    row = _real_row(doc_type)
    sub = str(row.get("expected_subclass") or "").strip() or None
    expected = row["expected_fields"]
    # a realistic prediction from the GT itself; the semantic trio is filled
    # when the published GT leaves it blank so the payload has numbers to pin.
    predicted = dict(expected)
    if not predicted.get("subject_matter"):
        predicted["subject_matter"] = "comparability pin: subject matter"
    if not predicted.get("keywords"):
        predicted["keywords"] = ["comparability", "pin"]

    with_sub = score_extraction_row(
        doc_type,
        dict(predicted),
        expected,
        doc_text=row.get("doc_text"),
        expected_subclass=sub,
    )
    without = score_extraction_row(
        doc_type, dict(predicted), dict(expected), doc_text=row.get("doc_text")
    )

    for key in ("overall_extraction_score", *_EXTRACT_PRF_KEYS):
        assert with_sub.get(key) == without.get(key), (
            f"{doc_type}/{row['id']}: forwarding expected_subclass={sub!r} "
            f"changed payload[{key!r}]: {with_sub.get(key)!r} != {without.get(key)!r}"
        )
    vanished = set(without) - set(with_sub)
    extra = set(with_sub) - set(without)
    assert not vanished, f"{doc_type}/{row['id']}: keys vanished under the kwarg: {sorted(vanished)}"
    assert extra <= {"unlabeled_fields", "fields"}, (
        f"{doc_type}/{row['id']}: subclass kwarg added keys outside the two "
        f"provenance keys: {sorted(extra)}"
    )
    if doc_type == "corporate_record" and sub:
        assert "unlabeled_fields" in with_sub, (
            "corporate_record forward must surface the dojo's per-row "
            "unlabeled_fields (PR #145 wiring contract)"
        )


@pytest.mark.parametrize("subclass", ("powers_of_attorney", "rights_instrument"))
def test_corporate_alignment_is_subclass_sensitive(subclass: str):
    """Without the subclass the alignment normalizes to ``other`` — detectable.

    Extension fields named only by the row's own subclass (e.g. a
    ``powers_of_attorney`` row's ``principal``, filled as a real prediction on
    the published v9.2 shape where entity GT is blank/unlabeled) must remain
    scorable candidates under the forwarded subclass; the miss does not change
    the unlabeled set the same way it would under "" → ``other``. The second
    parameter, ``rights_instrument``, is the same fill on a row whose OWN
    extension keys (``instrument_kind``/``holder``/…) differ from
    ``principal`` — the reviewer-sourced case of a real sub-vs-other alignment
    divergence found in the same row cache.
    """
    from llm_dojo_scoring.corporate_record_schema import align_unlabeled

    row = _real_corporate_row(subclass)
    assert row.get("expected_subclass"), row["id"]
    expected = row["expected_fields"]
    predicted = dict(expected)
    predicted["principal"] = "Grantor L."

    scored = score_extraction_row(
        "corporate_record", predicted, expected, expected_subclass=row["expected_subclass"]
    )
    _, _, dojo_dropped = align_unlabeled(
        row["expected_subclass"], expected, expected, predicted
    )
    _, _, other_dropped = align_unlabeled(None, expected, expected, predicted)
    # the fwd subclass vs the default normalized one must be asserted to be
    # what the sandbox actually produced
    assert scored["unlabeled_fields"] == list(dojo_dropped)
    # and the scored payload used the subclass, whatever the dojo itself
    # computed from it: doc_subclass ≡ expected_subclass kwarg equivalence.
    scored_other = score_extraction_row(
        "corporate_record", predicted, expected,
        doc_subclass=row["expected_subclass"],
    )
    assert scored_other["unlabeled_fields"] == list(dojo_dropped)
    assert scored["overall_extraction_score"] == scored_other["overall_extraction_score"]
    # guard against a silent default-"other" fallback producing a different
    # alignment than the dojo's own subclass-aware computation — asserted
    # UNCONDITIONALLY now: on the published v9.2 entity-GT-blank shape the two
    # alignments genuinely diverge for every subclass with its own extension
    # keys, so the fixture is first required to diverge, then the scored
    # payload is required to differ from the "other" alignment directly.
    assert dojo_dropped != other_dropped, (
        "fixture lost its sub-vs-other fill divergence; pick a row whose "
        "subclass extension keys are actually unlabeled"
    )
    assert scored["unlabeled_fields"] != list(other_dropped)


def test_non_subclass_paths_are_unchanged():
    """``doc_subclass=None`` (or an unknown class) keeps the legacy payload."""
    predicted = {
        "intent": "payment_demand",
        "subject_matter": "unpaid invoices",
        "keywords": ["breach", "demand", "invoice"],
    }
    clean = score_extraction_row("correspondence", predicted, dict(predicted))
    scored = score_extraction_row("correspondence", dict(predicted), dict(predicted))
    assert "unlabeled_fields" not in clean and "unlabeled_fields" not in scored
    assert scored["overall_extraction_score"] == clean["overall_extraction_score"]
    corporate = score_extraction_row(
        "corporate_record", dict(predicted), dict(predicted)
    )
    # no subclass given → legacy single-path result; no alignment surfaced
    assert "unlabeled_fields" not in corporate
    assert corporate["overall_extraction_score"] is not None


@pytest.mark.parametrize(
    "field,expected_value,presence,expected_precision",
    [
        ("certifying_officer", "Bob", "populated", 1.0),
        ("certifying_officer", "", "schema_documented_absence", 2 / 3),
        ("entity_name", None, "schema_documented_absence", 2 / 3),
    ],
)
def test_labeled_corporate_fields_are_not_filtered_before_scoring(
    field, expected_value, presence, expected_precision
):
    """Keep annotated mismatches and explicit absences as real scoring events."""
    expected = {
        "intent": "governance_rules",
        "subject_matter": "Bylaws",
        field: expected_value,
        "gt_presence": json.dumps({field: presence}),
    }
    predicted = {
        "intent": "governance_rules",
        "subject_matter": "Bylaws",
        field: "Alice",
    }
    result = score_extraction_row(
        "corporate_record", predicted, expected, expected_subclass="bylaws"
    )
    # Two correct semantic fields; a wrong label is one FN, while a
    # hallucinated documented absence is one FP. Both yield F1 = 4/5.
    assert result["extraction_f1"] == pytest.approx(0.8)
    assert result["extraction_precision"] == pytest.approx(expected_precision, abs=5e-5)
    assert field not in result["unlabeled_fields"]
    if presence == "populated":
        assert result["overall_extraction_score"] < 1.0
    else:
        # Dojo excludes empty GT from its quality average; the precision/F1
        # metrics above are the independent penalty for spurious fills.
        assert result["overall_extraction_score"] == 1.0


def test_registered_corporate_extension_is_not_an_extra_schema_key():
    """A bylaws extension belongs to the subclass schema, unlike a POA field."""
    predicted = {
        "entity_name": "Example LLC", "record_type": "bylaws",
        "intent": "governance_rules", "subject_matter": "Bylaws",
        "keywords": ["bylaws"], "certifying_officer": "Alice",
        "principal": "Wrong subclass",
    }
    result = score_extraction_row(
        "corporate_record", predicted,
        {"intent": "governance_rules", "certifying_officer": "Alice"},
        expected_subclass="bylaws",
    )
    assert "certifying_officer" not in result["extra_schema_keys"]
    assert "principal" in result["extra_schema_keys"]
