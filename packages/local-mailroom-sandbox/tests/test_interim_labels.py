"""Interim GT label overlay: the committed files stay consistent and the admission rules hold."""
from __future__ import annotations

import json

from mailroom_sandbox import interim_labels as il
from mailroom_sandbox.job.spec import DatasetSpec


def _row(cls="corporate_record", sub="bylaws", text="ACME HOLDINGS, INC. Bylaws adopted March 3, 2020 by Jane Roe.", **exp):
    return {"id": "D1", "expected_doc_class": cls, "expected_subclass": sub, "doc_text": text,
            "expected_fields": json.dumps({"intent": "governance_rules", "gt_presence": json.dumps({"intent": "populated"}), **exp})}


def test_committed_overlay_is_consistent():
    assert il.verify() == []
    man = il.load_manifest()
    assert man["schema"] == il.SCHEMA and man["sources"] and man["files"]
    for rec in il.load_overlay().values():
        cls = rec["doc_class"]
        assert rec["doc_sha256"] and rec["source"]["gate_run"] and rec["source"]["question_set"]
        for field, lab in rec["labels"].items():
            assert lab["use_as_truth"] == (lab["status"] in il.TRUTH_STATUSES)
            if lab["status"] == "gap_fill":
                assert field in il.GAP_FIELDS[cls], (rec["doc_id"], field)
                assert lab["support"] >= (il.NULL_SUPPORT_MIN if lab["value"] is None else il.SUPPORT_MIN)
            if lab["status"] == "derived":
                assert lab["value"] == rec["doc_subclass"]
            if lab["status"] == "correction":
                assert cls == "contract" and lab["basis"] in ("cuad_party_spans", "cuad_agreement_date")


def test_gap_fill_needs_support_grounding_and_no_hub_label():
    row = _row()
    gate = {"verdict": "retry_extraction",
            "field_support": {"entity_name": 0.97, "signatories": 0.95, "jurisdiction": 0.6, "intent": 0.99,
                              "effective_date": 0.93, "filing_number": 0.92}}
    fields = {"entity_name": "Acme Holdings, Inc.", "signatories": ["Roe, Jane"], "jurisdiction": "Delaware",
              "intent": "governance_rules", "effective_date": "2020-03-03", "filing_number": "F-123"}
    out = il.labels_for(row, fields, gate, {"intent": True})
    assert out["entity_name"]["status"] == "gap_fill"
    assert out["signatories"]["value"] == ["Roe, Jane"]  # name order does not matter
    assert out["effective_date"]["status"] == "gap_fill"  # "March 3, 2020" grounds the ISO date
    assert "jurisdiction" not in out  # support below SUPPORT_MIN
    assert "filing_number" not in out  # not in the document: ungrounded
    assert "intent" not in out  # the Hub labels it and the extraction agrees
    assert out["record_type"] == {"value": "bylaws", "status": "derived", "basis": "hub_subclass",
                                  "hub_value": None, "use_as_truth": True}
    assert il.labels_for(row, fields, {**gate, "verdict": "human_review"}, {"intent": True}).keys() == {"record_type"}


def test_disputed_is_never_truth_and_cms_table_is_derived():
    row = _row("correspondence", "email", "Please send the report.", intent="notice", intent_source="heuristic")
    out = il.labels_for(row, {"intent": "request"}, {"verdict": "accept", "field_support": {"intent": 0.98}},
                        {"intent": False})
    assert out["intent"]["status"] == "disputed" and out["intent"]["use_as_truth"] is False
    assert out["intent"]["hub_value"] == "notice" and out["intent"]["hub_source"] == "heuristic"
    cms = il.labels_for(_row("insurance_claim", "carrier", "x"), {}, {"verdict": "accept", "field_support": {}}, {})
    assert cms["cms_source_table"]["value"] == "carrier" and cms["cms_source_table"]["use_as_truth"]


def test_contract_corrections_rest_on_the_hubs_own_cuad_evidence(monkeypatch):
    spans = {"Parties": ["Seller", "NMS COMMUNICATIONS CORP.", "Backhaul", "VERSO BACKHAUL SOLUTIONS, INC."],
             "Effective Date": [], "Agreement Date": ["December 20, 2007"]}
    import llm_dojo_scoring.sandbox_scoring as ss

    monkeypatch.setattr(ss, "gt_categories", lambda labels: spans)
    exp = {"cuad_clause_labels": "{}"}
    assert il.contract_correction("parties", ['NMS COMMUNICATIONS CORP. ("Seller")', "Verso Backhaul Solutions, Inc."], exp) == "cuad_party_spans"
    assert il.contract_correction("parties", ["NMS COMMUNICATIONS CORP.", "Someone Else LLC"], exp) is None
    # A subset of the parties is incomplete, not a correction: Verso's legal name is unaccounted for.
    assert il.contract_correction("parties", ['NMS COMMUNICATIONS CORP. ("Seller")'], exp) is None
    # Without annotations: "Seller" and "Backhaul" name no further legal entity; still complete.
    assert il.contract_correction("parties", ["NMS COMMUNICATIONS CORP.", "Verso Backhaul Solutions, Inc."], exp) == "cuad_party_spans"
    spans["Parties"] = ["we", "NMS COMMUNICATIONS CORP.", "Verso Backhaul Solutions, Inc.",
                        "NMS and Verso may each be referred to herein as a Party"]
    assert il.contract_correction("parties", ["NMS Communications Corp.", "Verso Backhaul Solutions, Inc."], exp) == "cuad_party_spans"
    spans["Parties"] = ["Seller", "NMS COMMUNICATIONS CORP.", "Backhaul", "VERSO BACKHAUL SOLUTIONS, INC."]
    assert il.contract_correction("effective_date", "2007-12-20", exp) == "cuad_agreement_date"
    assert il.contract_correction("effective_date", "2008-01-01", exp) is None
    spans["Effective Date"] = ["January 1, 2008"]
    assert il.contract_correction("effective_date", "2007-12-20", exp) is None  # CUAD states one: no correction


def test_apply_overlay_merges_truth_only_and_hub_wins():
    row = _row(entity_name="Hub Name Inc.", gt_presence=json.dumps({"intent": "populated", "entity_name": "populated"}))
    rec = {"doc_id": "D1", "doc_sha256": il.doc_sha(row["doc_text"]), "labels": {
        "entity_name": {"value": "Overlay Inc.", "status": "gap_fill", "use_as_truth": True},
        "jurisdiction": {"value": None, "status": "gap_fill", "use_as_truth": True},
        "intent": {"value": "other", "status": "disputed", "use_as_truth": False},
        "record_type": {"value": "bylaws", "status": "derived", "use_as_truth": True}}}
    out = il.apply_overlay(row, {"D1": rec}, overlay_sha="abc")
    exp = json.loads(out["expected_fields"])
    assert exp["entity_name"] == "Hub Name Inc." and exp["intent"] == "governance_rules"
    assert exp["record_type"] == "bylaws" and exp["jurisdiction"] is None
    pres = json.loads(exp["gt_presence"])
    assert pres["record_type"] == "populated" and pres["jurisdiction"] == "schema_documented_absence"
    assert out["interim_labels"] == {"fields": ["jurisdiction", "record_type"], "overlay_sha256": "abc"}
    changed = {**row, "doc_text": row["doc_text"] + " amended"}
    assert il.apply_overlay(changed, {"D1": rec}, overlay_sha="abc") == changed  # stale text: untouched
    assert row["expected_fields"] == _row(entity_name="Hub Name Inc.", gt_presence=json.dumps(
        {"intent": "populated", "entity_name": "populated"}))["expected_fields"]  # input not mutated


def test_superseded_reports_hub_labels_and_changed_text():
    row = _row()
    rec = {"doc_id": "D1", "doc_sha256": il.doc_sha(row["doc_text"]),
           "labels": {"entity_name": {"value": "Acme", "status": "gap_fill", "use_as_truth": True}}}
    assert il.superseded([row], {"D1": rec}) == []
    hub = _row(entity_name="Acme", gt_presence=json.dumps({"entity_name": "populated"}))
    assert il.superseded([hub], {"D1": rec}) == [("D1", "entity_name")]
    assert il.superseded([{**row, "doc_text": "new"}], {"D1": rec}) == [("D1", "*")]


def test_interim_labels_is_hashed_only_when_set():
    base = DatasetSpec(repo="r", split="train")
    assert "interim_labels" not in base.request_core()
    on = DatasetSpec(repo="r", split="train", interim_labels=True).request_core()
    assert on["interim_labels"] == il.overlay_fingerprint() and len(on["interim_labels"]) == 64


def test_prepare_subset_applies_the_overlay_only_when_asked(tmp_path, monkeypatch):
    from mailroom_sandbox.corpus import prepare_subset

    row = _row()
    row["id"] = "D1"
    src = tmp_path / "rows.jsonl"
    src.write_text(json.dumps(row) + "\n", encoding="utf-8")
    rec = {"doc_id": "D1", "doc_sha256": il.doc_sha(row["doc_text"]),
           "labels": {"record_type": {"value": "bylaws", "status": "derived", "use_as_truth": True}}}
    monkeypatch.setattr(il, "verify", lambda root=None: [])
    monkeypatch.setattr(il, "load_overlay", lambda root=None: {"D1": rec})
    monkeypatch.setattr(il, "overlay_fingerprint", lambda root=None: "f" * 64)
    off = prepare_subset(DatasetSpec(local_path=str(src)), tmp_path / "off.jsonl")
    assert "interim_labels" not in off["metadata"]
    assert "interim_labels" not in json.loads((tmp_path / "off.jsonl").read_text())
    on = prepare_subset(DatasetSpec(local_path=str(src), interim_labels=True), tmp_path / "on.jsonl")
    assert on["metadata"]["interim_labels"] == {"overlay_sha256": "f" * 64, "rows_with_labels": 1, "fields_applied": 1}
    locked = json.loads((tmp_path / "on.jsonl").read_text())
    exp = locked["expected_fields"]
    assert (json.loads(exp) if isinstance(exp, str) else exp)["record_type"] == "bylaws"
    monkeypatch.setattr(il, "verify", lambda root=None: ["corporate_record.jsonl: sha256 differs"])
    import pytest

    with pytest.raises(ValueError, match="inconsistent"):
        prepare_subset(DatasetSpec(local_path=str(src), interim_labels=True), tmp_path / "bad.jsonl")


def test_null_truth_label_is_a_documented_absence_the_dojo_scores():
    """A null gap fill must read as "expected empty", not unlabeled, so corporate scoring keeps it."""
    from llm_dojo_scoring.corporate_record_schema import unlabeled_fields

    row = _row()
    rec = {"doc_id": "D1", "doc_sha256": il.doc_sha(row["doc_text"]), "labels": {
        "jurisdiction": {"value": None, "status": "gap_fill", "use_as_truth": True}}}
    exp = json.loads(il.apply_overlay(row, {"D1": rec}, overlay_sha="abc")["expected_fields"])
    assert "jurisdiction" not in unlabeled_fields("bylaws", exp)
    assert "jurisdiction" in unlabeled_fields("bylaws", json.loads(row["expected_fields"]))


def _overlay_two_labels(root):
    """An overlay of one document with two gap fills, written as the builder would."""
    import importlib.util
    import pathlib

    spec = importlib.util.spec_from_file_location(
        "interim_labels_script", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "interim_labels.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    row = _row()
    rec = {"doc_id": "D1", "doc_class": "corporate_record", "doc_sha256": il.doc_sha(row["doc_text"]), "labels": {
        "entity_name": {"value": "Acme", "status": "gap_fill", "use_as_truth": True},
        "jurisdiction": {"value": "Delaware", "status": "gap_fill", "use_as_truth": True}}}
    root.mkdir()
    text = json.dumps(rec, sort_keys=True) + "\n"
    (root / "corporate_record.jsonl").write_text(text, encoding="utf-8")
    man = {"schema": il.SCHEMA, "sources": [], "files": {"corporate_record.jsonl": il._sha(text)},
           "counts": {"corporate_record": {"entity_name": {"gap_fill": 1}, "jurisdiction": {"gap_fill": 1}}}}
    (root / "MANIFEST.json").write_text(json.dumps(man), encoding="utf-8")
    hub = _row(entity_name="Acme", gt_presence=json.dumps({"entity_name": "populated"}))
    return mod, hub


def test_prune_rewrites_counts_and_still_fails_on_other_problems(tmp_path, monkeypatch):
    root = tmp_path / "interim"
    mod, hub = _overlay_two_labels(root)
    monkeypatch.setattr(mod, "_local_gate_runs", lambda: {})
    rows = tmp_path / "rows.jsonl"
    rows.write_text(json.dumps(hub) + "\n", encoding="utf-8")
    assert mod.check(root, rows, prune=True) == 0
    man = json.loads((root / "MANIFEST.json").read_text())
    assert man["counts"] == {"corporate_record": {"jurisdiction": {"gap_fill": 1}}}
    assert il.verify(root) == []
    # An integrity problem left beside the pruned labels must still fail the check.
    (root / "stray.jsonl").write_text("", encoding="utf-8")
    hub2 = _row(jurisdiction="Delaware", gt_presence=json.dumps({"jurisdiction": "populated"}))
    rows.write_text(json.dumps(hub2) + "\n", encoding="utf-8")
    assert mod.check(root, rows, prune=True) == 1
    # ...and the prune is refused, so the still-superseded label stays in place.
    assert "jurisdiction" in json.loads((root / "corporate_record.jsonl").read_text())["labels"]


def test_prune_never_rehashes_a_file_that_fails_integrity(tmp_path, monkeypatch):
    root = tmp_path / "interim"
    mod, hub = _overlay_two_labels(root)
    monkeypatch.setattr(mod, "_local_gate_runs", lambda: {})
    path = root / "corporate_record.jsonl"
    rec = json.loads(path.read_text())
    rec["labels"]["jurisdiction"]["value"] = "Nevada"  # a hand edit the manifest hash does not cover
    path.write_text(json.dumps(rec, sort_keys=True) + "\n", encoding="utf-8")
    sha_before = json.loads((root / "MANIFEST.json").read_text())["files"]["corporate_record.jsonl"]
    rows = tmp_path / "rows.jsonl"
    rows.write_text(json.dumps(hub) + "\n", encoding="utf-8")
    assert mod.check(root, rows, prune=True) == 1
    assert json.loads((root / "MANIFEST.json").read_text())["files"]["corporate_record.jsonl"] == sha_before
    assert any("sha256 differs" in p for p in il.verify(root))


def test_counts_tolerate_a_label_without_status(tmp_path):
    mod, _ = _overlay_two_labels(tmp_path / "interim")
    root = tmp_path / "interim"
    rec = json.loads((root / "corporate_record.jsonl").read_text())
    del rec["labels"]["jurisdiction"]["status"]
    rec2 = {**rec, "doc_id": "D2"}
    rec2["labels"] = {"jurisdiction": {"value": "Delaware", "status": "gap_fill", "use_as_truth": True}}
    (root / "corporate_record.jsonl").write_text(json.dumps(rec) + "\n" + json.dumps(rec2) + "\n", encoding="utf-8")
    counts = mod._counts(root, ["corporate_record.jsonl"])
    assert counts["corporate_record"]["jurisdiction"] == {"gap_fill": 1, None: 1}


def test_replace_leaves_no_staged_file(tmp_path):
    mod, _ = _overlay_two_labels(tmp_path / "interim")
    target = tmp_path / "out.json"
    mod._replace(target, "one")
    mod._replace(target, "two")
    assert target.read_text() == "two"
    assert [p.name for p in tmp_path.iterdir() if p.name != "interim"] == ["out.json"]
