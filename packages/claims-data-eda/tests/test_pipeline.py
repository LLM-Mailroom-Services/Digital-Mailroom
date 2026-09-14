"""Unit tests for the DE-SynPUF pipeline toolchain (no corpus data required)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from build_corpus_index import compact, iso_date, to_float, to_int  # noqa: E402
from render_eob import gt_fields, insured_pseudonym, money, pipeline_row, render  # noqa: E402


# ---------------------------------------------------------------- fixtures

def inpatient_row() -> dict:
    return {
        "record_id": "inpatient:900000000000001:1",
        "record_type": "claim",
        "claim_type": "inpatient",
        "bene_id": "BENE0001",
        "clm_id": "900000000000001",
        "segment": 1,
        "year": 2009,
        "from_dt": "2009-04-02",
        "thru_dt": "2009-04-08",
        "admit_dt": "2009-04-02",
        "discharge_dt": "2009-04-08",
        "payment_amt": 5400.0,
        "primary_payer_amt": 0.0,
        "prvdr_num": "24XYZ",
        "provider_npis": ["1234567893"],
        "diagnosis_codes": ["4280", "42820"],
        "admitting_dx": "4280",
        "procedure_codes": ["3971"],
        "hcpcs_codes": [],
        "drg_cd": "292",
        "utilization_days": 6,
        "deductible_amt": 1100.0,
        "coinsurance_amt": 0.0,
        "blood_deductible_amt": None,
        "pass_thru_per_diem_amt": None,
        "bene_age": 74,
        "bene_sex": "F",
        "bene_state": 33,
        "chronic_conditions": {"CHF": 1},
    }


def carrier_row() -> dict:
    return {
        "record_id": "carrier:800000000000002",
        "record_type": "claim",
        "claim_type": "carrier",
        "bene_id": "BENE0002",
        "clm_id": "800000000000002",
        "year": 2008,
        "from_dt": "2008-07-11",
        "thru_dt": "2008-07-11",
        "payment_amt": 195.4,
        "provider_npis": ["1999999999", "1888888888"],
        "diagnosis_codes": ["25000"],
        "procedure_codes": [],
        "hcpcs_codes": ["99213", "36415"],
        "lines": [
            {"line_num": 1, "hcpcs": "99213", "payment_amt": 75.4,
             "allowed_charge_amt": 92.5, "coinsurance_amt": 12.1, "deductible_amt": 0.0},
            {"line_num": 2, "hcpcs": "36415", "payment_amt": 120.0,
             "allowed_charge_amt": 120.0, "coinsurance_amt": 0.0, "deductible_amt": 0.0},
        ],
        "bene_age": 71,
        "bene_sex": "M",
        "bene_state": 5,
        "chronic_conditions": {},
    }


def pde_row() -> dict:
    return {
        "record_id": "pde:700000000000003",
        "record_type": "pde",
        "claim_type": "pde",
        "bene_id": "BENE0003",
        "pde_id": "700000000000003",
        "year": 2010,
        "service_dt": "2010-01-19",
        "ndc": "00093000801",
        "qty_dispensed": 30.0,
        "days_supply": 30,
        "drug_cost_amt": 42.1,
        "patient_pay_amt": 6.35,
        "bene_age": 68,
        "bene_sex": "M",
        "bene_state": 44,
        "chronic_conditions": {},
    }


SAMPLE_ROWS = pytest.mark.parametrize(
    "row_fn", [inpatient_row, carrier_row, pde_row],
)


# ---------------------------------------------------------------- normalizers

class TestNormalizers:
    def test_iso_date(self):
        assert iso_date("20090402") == "2009-04-02"
        assert iso_date("") is None
        assert iso_date(None) is None
        # hub#58: month/day ranges validated; garbage and non-ISO pass-through
        # return None instead of reaching downstream int() and raising.
        assert iso_date("20101332") is None   # month 13
        assert iso_date("20100431") is None   # day 31 invalid for April (range check)
        assert iso_date("N/A") is None
        assert iso_date("1/1/2010") is None
        assert iso_date("2010-04-02") == "2010-04-02"  # already-ISO tolerated
        assert iso_date("2010040") is None   # malformed

    def test_to_float(self):
        assert to_float("42.10") == 42.1
        assert to_float(" ") is None
        assert to_float("N/A") is None

    def test_to_int(self):
        assert to_int("007") == 7
        assert to_int("x") is None

    def test_compact_drops_nulls_and_empties(self):
        out = compact({"a": None, "b": "", "c": [], "d": {}, "e": 0, "f": [None, 1], "g": {"h": None, "i": 2}})
        assert out == {"e": 0, "f": [None, 1], "g": {"i": 2}}

    def test_compact_keeps_zero_money(self):
        assert compact({"payment_amt": 0.0}) == {"payment_amt": 0.0}


# ---------------------------------------------------------------- renderer

class TestRenderDeterminism:
    @SAMPLE_ROWS
    def test_byte_identical_on_rebuild(self, row_fn):
        a = render(row_fn())
        b = render(row_fn())
        assert a[0] == b[0]
        assert a[1] == b[1]

    @SAMPLE_ROWS
    def test_verbatim_contract_all_types(self, row_fn):
        doc, gt = render(row_fn())
        for key in ("claim_number", "policy_number", "insurer", "insured_party"):
            assert gt[key] and str(gt[key]) in doc
        assert money(gt["claimed_amount"]) in doc
        for d in (gt["date_of_loss"], gt["date_filed"]):
            if d:
                assert d in doc

    @SAMPLE_ROWS
    def test_policy_number_labeled_exactly_once(self, row_fn):
        """The synthetic DESYNPUF_ID is deliberately rendered as the policy
        number (the corpus has no separate policy identifier) -- it must appear
        exactly once, in its labeled field."""
        row = row_fn()
        doc, gt = render(row)
        assert doc.count(f"Policy number:            {gt['policy_number']}") == 1
        assert gt["insured_party"] != gt["policy_number"]  # pseudonym, not the raw id

    def test_unknown_type_raises(self):
        bad = inpatient_row()
        bad["claim_type"] = "dental"
        with pytest.raises(ValueError):
            render(bad)

    def test_pseudonym_deterministic(self):
        assert insured_pseudonym("A") == insured_pseudonym("A")
        assert insured_pseudonym("A") != insured_pseudonym("B")


# ---------------------------------------------------------------- GT schema

MAILROOM_SCHEMA_KEYS = {
    "claim_number", "policy_number", "insurer", "insured_party", "claim_type",
    "date_of_loss", "date_filed", "claimed_amount", "adjuster",
    "damages_description", "coverage_determination", "denial_reasons",
    "supporting_documents",
}


class TestGroundTruth:
    @SAMPLE_ROWS
    def test_schema_key_alignment(self, row_fn):
        _, gt = render(row_fn())
        assert set(gt) == MAILROOM_SCHEMA_KEYS

    @SAMPLE_ROWS
    def test_synthetic_corpus_invariants(self, row_fn):
        _, gt = render(row_fn())
        assert gt["claim_type"] == "health"           # line of business constant
        assert gt["coverage_determination"] == "approved"  # no denials exist in SynPUF
        assert gt["denial_reasons"] == []
        assert gt["adjuster"] is None                 # adjusters do not exist in SynPUF

    @SAMPLE_ROWS
    def test_claim_type_field_type(self, row_fn):
        _, gt = render(row_fn())
        assert isinstance(gt["claimed_amount"], float)
        assert isinstance(gt["supporting_documents"], list)


# ---------------------------------------------------------------- pipeline row

class TestPipelineRow:
    @SAMPLE_ROWS
    def test_flat_dump_shape(self, row_fn):
        r = pipeline_row(row_fn())
        assert set(r) >= {"filename", "doc_text", "prompt", "expected",
                          "expected_subclass", "metadata"}
        assert r["expected"] == "insurance_claim"
        assert r["expected_subclass"] in {"inpatient", "outpatient", "carrier", "pde"}
        assert r["prompt"] == ""
        assert r["filename"].endswith(".txt")
        assert r["metadata"]["ground_truth"]["claim_number"]

    def test_metadata_codes_carried(self):
        r = pipeline_row(carrier_row())
        m = r["metadata"]
        assert m["diagnosis_codes"] == ["25000"]
        assert sorted(m["hcpcs_codes"]) == ["36415", "99213"]
        assert len(m["provider_npis"]) == 2

    def test_json_roundtrip(self):
        r = pipeline_row(pde_row())
        assert json.loads(json.dumps(r))["metadata"]["ground_truth"] == r["metadata"]["ground_truth"]


def test_reservoir_seed_is_process_stable():
    """hub#58: the pipeline-dump stratum seed must be deterministic across
    processes — the old `hash(key) % 10000` used Python's salted built-in
    hash, so reservoir RNG streams differed between runs (PYTHONHASHSEED).
    zlib.crc32 is stable; two fresh reservoirs over the same stream agree
    and the seed function is a pure function of the key."""
    import zlib

    def seed_for(key, base=42):
        return base + zlib.crc32(str(key).encode()) % 10000

    # same key -> same seed every call (pure function, no process salt)
    assert seed_for(("inpatient", 2009, "LOW")) == seed_for(("inpatient", 2009, "LOW"))
    # different keys -> (overwhelmingly) different seeds
    assert seed_for(("inpatient", 2009, "LOW")) != seed_for(("pde", 2011, "MED"))

    # two independent reservoirs over the same keyed stream must agree
    def run_reservoir(seed):
        from build_pipeline_dump import Reservoir

        r = Reservoir(k=3, seed=seed)
        for i in range(50):
            r.add({"record_id": f"row-{i}", "claim_type": "inpatient"})
        return sorted(x["record_id"] for x in r.items)

    a = run_reservoir(seed_for(("inpatient", 2009, "LOW")))
    b = run_reservoir(seed_for(("inpatient", 2009, "LOW")))
    assert a == b
