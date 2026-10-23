"""Unit pins for the Gmail corpus pilot (HUB-053) — lab + corpus loader.

Network-free by construction: the corpus loader's HTTP layer is faked, the
offline snapshot is the document source, and the SMTP/mock fire paths are
exercised against the hermetic temp base dir.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from notebooks import gmail_pilot_lab as lab


# ---------------------------------------------------------------------------
# Corpus selection — offline snapshot (the committed, integrity-verified one)


def test_snapshot_rows_are_integrity_verified():
    from pipeline.hf_corpora import FULL_CORPUS_REVISION

    data = json.loads(lab.SNAPSHOT_PATH.read_text())
    # hub#47: the snapshot derives from the v9 dataset at the same pin the
    # loader defaults to — never the frozen v8 corpus.
    assert data["dataset"] == "Lucius-Morningstar/mailroom-dataset"
    assert data["hub_sha"] == FULL_CORPUS_REVISION
    roles = [r["role"] for r in data["rows"]]
    assert "insurance_claim" in roles and "correspondence" in roles and "contract" in roles
    for row in data["rows"]:
        text = row["doc_text"]
        assert text, f"{row['role']}: empty doc_text"
        assert row["labels"].get("content_sha256"), f"{row['role']}: no content_sha256"
        import hashlib

        assert hashlib.sha256(text.encode("utf-8")).hexdigest() == row["labels"]["content_sha256"], (
            f"{row['role']}: snapshot text does not match its corpus content_sha256"
        )


@pytest.mark.parametrize("field", ["hub_sha", "plan_revision_pin", "hub_sha_tip"])
def test_snapshot_provenance_uses_v9_2_pin(field):
    from pipeline.hf_corpus_loader import load_snapshot

    rows, provenance = load_snapshot()

    assert rows
    assert provenance["dataset"] == "Lucius-Morningstar/mailroom-dataset"
    assert provenance[field] == "v9.2"


@pytest.mark.parametrize(
    "role", ["insurance_claim", "correspondence", "contract", "handoff_case_contract"],
)
def test_offline_document_preserves_v9_2_provenance(role):
    doc = lab.select_document(role=role, live=False)

    assert doc["role"] == role
    assert doc["provenance"]["source"] == "committed-snapshot"
    assert doc["provenance"]["dataset"] == "Lucius-Morningstar/mailroom-dataset"
    assert doc["provenance"]["hub_sha"] == "v9.2"


def test_select_document_filters_by_class_and_budget(temp_base_dir):
    doc = lab.select_document(doc_class="insurance_claim", max_chars=12000)
    assert doc["labels"]["expected"] == "insurance_claim"
    assert len(doc["doc_text"]) <= 12000
    assert doc["provenance"]["source"] == "committed-snapshot"
    # the deliberate handoff case is excluded by the budget
    with pytest.raises(RuntimeError):
        lab.select_document(role="handoff_case_contract", max_chars=12000)
    # and served explicitly when asked
    handoff = lab.select_document(role="handoff_case_contract", max_chars=None)
    assert len(handoff["doc_text"]) > 12000


# ---------------------------------------------------------------------------
# Loader ladder (offline: faked HTTP; the /parquet + join + integrity path)


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def raise_for_status(self):
        pass

    @property
    def content(self):
        return self._payload


@pytest.mark.parametrize(
    "load_kwargs,expected_revision",
    [({}, "v9.2"), ({"revision": "v9.1"}, "v9.1"), ({"revision": None}, None)],
    ids=["default-v9.2", "historical-override", "explicit-unpinned"],
)
@pytest.mark.parametrize("strategy", ["parquet", "rows_pagination"])
def test_load_corpus_join_and_integrity(
    temp_base_dir, monkeypatch, mocker, load_kwargs, expected_revision, strategy,
):
    from pipeline import hf_corpus_loader as loader

    text_a, text_b = "alpha corpus text", "beta corpus text"
    import hashlib

    gt = pd.DataFrame(
        [
            {"filename": "a.txt", "expected": "contract", "content_sha256": hashlib.sha256(text_a.encode()).hexdigest()},
            {"filename": "b.txt", "expected": "correspondence", "content_sha256": hashlib.sha256(text_b.encode()).hexdigest()},
        ]
    )
    blind = pd.DataFrame([{"filename": "a.txt", "doc_text": text_a}, {"filename": "b.txt", "doc_text": text_b}])
    frames = {"ground_truth": gt, "default": blind}

    def fake_parquet_urls(repo_id, *, split="train", revision=None):
        if strategy == "rows_pagination":
            raise RuntimeError("parquet unavailable")
        return {name: f"https://viewer.test/{name}.parquet" for name in frames}

    parquet_urls = mocker.patch.object(loader, "parquet_urls", side_effect=fake_parquet_urls)
    rows_ladder = mocker.patch.object(
        loader, "_rows_ladder",
        side_effect=lambda repo_id, config, **kwargs: frames[config].copy(),
    )
    monkeypatch.setattr(loader, "dataset_sha", lambda repo_id=None: "fakesha")
    def fake_cache(url, label):
        config = "ground_truth" if label.endswith("ground_truth_train") else "default"
        return frames[config].to_parquet()

    monkeypatch.setattr(loader, "_cached_get_bytes", fake_cache)

    merged, prov = loader.load_corpus(**load_kwargs)
    assert parquet_urls.call_args_list == [
        mocker.call(loader.FULL_CORPUS_ID, split="train", revision=expected_revision),
        mocker.call(loader.FULL_CORPUS_ID, split="train", revision=expected_revision),
    ]
    if strategy == "rows_pagination":
        assert rows_ladder.call_args_list == [
            mocker.call(loader.FULL_CORPUS_ID, config, split="train", revision=expected_revision)
            for config in ("ground_truth", "default")
        ]
    else:
        rows_ladder.assert_not_called()
    assert prov["revision_requested"] == expected_revision
    assert prov["hub_sha_tip"] == "fakesha"
    if expected_revision is not None:
        assert prov["hub_tip_drift"] == {"tip": "fakesha", "pinned": expected_revision}
    else:
        assert "hub_tip_drift" not in prov
    for config in ("ground_truth", "default"):
        assert prov[config]["strategy"] == strategy
        assert prov[config]["revision"] == expected_revision
    assert prov["integrity"] == {"checked": 2, "verified": 2, "mismatched": 0}
    assert list(merged["expected"]) == ["contract", "correspondence"]
    assert list(merged["doc_text"]) == [text_a, text_b]

    row = loader.pick_document(merged, doc_class="contract")
    assert row["filename"] == "a.txt" and row["_selection"]["position"] == 0
    with pytest.raises(RuntimeError):
        loader.pick_document(merged, doc_class="merger_agreement")


def test_loader_never_silently_returns_empty(temp_base_dir, monkeypatch):
    from pipeline import hf_corpus_loader as loader

    monkeypatch.setattr(loader, "parquet_urls", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(loader, "_rows_ladder", lambda *a, **k: pd.DataFrame())
    with pytest.raises(RuntimeError, match="cannot load"):
        loader.load_config_frame("x/y", "ground_truth")


# ---------------------------------------------------------------------------
# Email build + fire paths (smoke-test mirrors)


def test_build_pilot_email_single_attachment_shape(temp_base_dir):
    doc = lab.select_document(doc_class="insurance_claim")
    path, name = lab.build_attachment(doc, Path(temp_base_dir) / "work", stamp="20260904T000000Z")
    assert path.exists() and name.startswith("pilot_20260904T000000Z_")
    raw, message_id, att_name = lab.build_pilot_email(path, "PILOT-NB", stamp="20260904T000000Z")
    assert message_id.startswith("<gmail-pilot-") and message_id.endswith("@mailroom.local>")
    assert b"[M:PILOT-NB]" in raw
    assert att_name.encode() in raw
    # exactly ONE attachment (single-document upload => route: triage)
    assert raw.count(b"Content-Disposition: attachment") == 1


def test_deliver_mock_writes_poller_exact_sidecar(temp_base_dir):
    doc = lab.select_document(doc_class="insurance_claim")
    path, _ = lab.build_attachment(doc, Path(temp_base_dir) / "work", stamp="20260904T000000Z")
    from pipeline import bins

    result = lab.deliver_mock(path, "PILOT-NB", "<gmail-pilot-x@mailroom.local>", stamp="20260904T000000Z")
    assert result["delivered"] and result["reject_reason"] is None
    meta = json.loads((bins.inbox_dir() / f"{result['delivered']}.meta").read_text())
    assert meta["route"] == "triage" and meta["source"] == "gmail"
    assert meta["message_id"] == "<gmail-pilot-x@mailroom.local>"
    assert meta["matter_id"] == "PILOT-NB"


# ---------------------------------------------------------------------------
# Watch + ground-truth checks + report (deterministic, fail-soft)


def test_watchlog_drains_matching_events_only(temp_base_dir):
    from pipeline import bins

    log_path = bins.get_base_dir() / "watcher.out"
    log_path.write_text("2026-09-04T00:00:01.000Z [info] gmail_attachment_queued file=pilot_X.txt\nnoise line\n")
    watch = lab.WatchLog(path=log_path)
    (log_path.parent / "watcher.out").write_text(
        log_path.read_text() + "2026-09-04T00:00:02.000Z [info] triage_archived file=pilot_X.txt\nother file=y\n"
    )
    added = watch.drain("pilot_X")
    assert [e["line"] for e in added] == ["2026-09-04T00:00:02.000Z [info] triage_archived file=pilot_X.txt"]
    assert added[0]["ts"] == "2026-09-04T00:00:02.000Z"
    assert watch.drain("pilot_X") == []  # idempotent — offset advanced


def test_ground_truth_checks_compare_corpus_labels(temp_base_dir):
    doc = lab.select_document(doc_class="insurance_claim")
    manifest = {
        "stage": "archived",
        "doc_type": doc["labels"]["expected"],
        "doc_subclass": doc["labels"].get("expected_subclass"),
        "intake": {"triage": {"primary_doc_class": doc["labels"]["expected"], "extraction": {
            "claim_number": doc["labels"].get("claim_number"),
        }}},
    }
    checks = lab.ground_truth_checks(manifest, doc)
    by_name = {c["check"]: c for c in checks}
    assert by_name["doc_class"]["ok"] is True
    assert by_name["stage"]["ok"] is True
    if by_name.get("extraction.claim_number"):
        assert by_name["extraction.claim_number"]["ok"] is True
    # a wrong class must fail the check honestly
    manifest["doc_type"] = "contract"
    checks_bad = lab.ground_truth_checks(manifest, doc)
    assert next(c for c in checks_bad if c["check"] == "doc_class")["ok"] is False


def test_report_writer_produces_json_and_markdown(temp_base_dir):
    run = {
        "token": "pilotX", "stamp": "20260904T000000Z", "mode": "mock",
        "fired": {"fired": True}, "matter_id": "PILOT-NB", "attachment_name": "a.txt",
        "doc": {"labels": {}, "provenance": {"source": "committed-snapshot"}, "chars": 10},
        "manifest": {"stage": "archived", "intake": {"triage": {"primary_doc_class": "insurance_claim", "confidence": 0.9}}},
        "elapsed_s": 12.0,
        "checks": [{"check": "doc_class", "expected": "insurance_claim", "actual": "insurance_claim", "ok": True}],
        "evidence": {"audit_chain_ok": True, "audit_events": ["triage_archived"], "relations_edges": []},
        "log_events": [], "verdict": "PASS (1/1 checks ok)",
    }
    paths = lab.write_report(run)
    assert paths["json"].exists() and paths["md"].exists()
    md = paths["md"].read_text()
    assert "Gmail corpus pilot" in md and "PASS (1/1 checks ok)" in md
    assert "| doc_class | insurance_claim | insurance_claim | yes |" in md
