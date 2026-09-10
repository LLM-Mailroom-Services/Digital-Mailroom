"""DMR-049 LegalBench subset loading & processing regression tests.

Covers the lucius audit findings: the job runner's task-aware expected field
(F1 — legalbench labels live in ``answer``, not ``expected_doc_class``), loud
missing/empty fixtures (F2), task selection + the honest family refusal
(F3/F4), seeded sampling (F5), the job-spec question/answer guard (F6), and
honest mock labelling (F8).
"""

from __future__ import annotations

import json

import pytest

from mailroom_sandbox.eval import experiment_log, runners
from mailroom_sandbox.job import preflight, runner
from mailroom_sandbox.job.spec import DatasetSpec, RunSpec


# ── F1: task-aware expected field ────────────────────────────────────────────


def test_expected_for_reads_answer_for_legalbench():
    row = {"id": "lb_01", "answer": "Yes", "expected_doc_class": None}
    assert runner._expected_for("legalbench", row) == "Yes"


def test_expected_for_reads_class_for_sorter():
    row = {"expected_doc_class": "contract"}
    assert runner._expected_for("sorter", row) == "contract"


# ── F2: loud missing fixture ─────────────────────────────────────────────────


def test_load_legalbench_fixtures_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("mailroom_sandbox.datasets.fixtures_dir", lambda: tmp_path)
    from mailroom_sandbox.datasets import load_legalbench_fixtures

    with pytest.raises(FileNotFoundError, match="legalbench fixture missing"):
        load_legalbench_fixtures()


# ── F3/F4: task selection + suite bridge ─────────────────────────────────────


def test_legalbench_family_classification_refused():
    with pytest.raises(ValueError, match="family_classification"):
        runners.run_legalbench_eval(mock=True, task="family_classification")


def test_legalbench_suite_requires_explicit_n():
    with pytest.raises(ValueError, match="explicit --n"):
        runners.run_legalbench_eval(mock=True, suite=True)


def test_legalbench_suite_bridge_fails_loud_without_corpus():
    # In this checkout data/cuad is deliberately pruned; the bridge must fail
    # loudly with the fetch command — never silently fall back to the fixture.
    from mailroom_sandbox.datasets import load_legalbench_suite_rows

    with pytest.raises(Exception) as excinfo:
        load_legalbench_suite_rows("contract_qa", sample=2, seed=1)
    assert "fetch_full_cuad" in str(excinfo.value)


# ── F5: seeded sampling ──────────────────────────────────────────────────────


def test_seeded_sample_is_deterministic_and_seed_sensitive():
    rows = [{"id": f"r{i}"} for i in range(10)]
    a = runners._seeded_sample(rows, 4, 7)
    b = runners._seeded_sample(rows, 4, 7)
    c = runners._seeded_sample(rows, 4, 8)
    assert [r["id"] for r in a] == [r["id"] for r in b]
    assert [r["id"] for r in a] != [r["id"] for r in c]
    assert len(a) == 4


# ── F6 + F1 end-to-end: legalbench job run ───────────────────────────────────


def _legalbench_store(tmp_path, rows: int = 5, run_id: str = "run-lb"):
    """A prepared legalbench job whose answers match half the mock parity."""
    path = tmp_path / "lb.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for i in range(rows):
            row = {
                "id": f"lb_{i}",
                "filename": f"lb_{i}.txt",
                "doc_text": f"passage {i}",
                "question": f"Question {i}?",
            }
            mock = runners._mock_legalbench_answer(row)
            row["answer"] = mock if i % 2 == 0 else ("No" if mock == "Yes" else "Yes")
            fh.write(json.dumps(row) + "\n")
    spec = RunSpec(
        run_id=run_id,
        task="legalbench",
        dataset=DatasetSpec(local_path=f"file://{path}", limit=rows),
        engine={"kind": "vllm-local", "modal": None},
        trace={"sink": "none"},
        job={"mock": True},
    )
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "prepared", report
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    return RunStore(run_dir(report["run_id"]))


def test_legalbench_job_expected_uses_answer_field(tmp_path, job_data_dir):
    store = _legalbench_store(tmp_path)
    summary = runner.run_job(store, mock=None)
    assert summary["state"] == "done"
    items = store.load_items()
    assert {i["expected"] for i in items} <= {"Yes", "No"}
    # F1 regression: the old code read expected_doc_class → every legalbench
    # prediction scored 0.0; the answer field must produce a real score.
    assert summary["scores"]["exact_match"] > 0.0


def test_legalbench_job_guard_rejects_non_legalbench_rows(tmp_path, job_data_dir):
    path = tmp_path / "corpus.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for i in range(3):
            fh.write(
                json.dumps(
                    {
                        "id": f"c{i}",
                        "filename": f"c{i}.txt",
                        "doc_text": f"corpus text {i}",
                        "expected": "contract",
                    }
                )
                + "\n"
            )
    spec = RunSpec(
        run_id="run-lb-bad",
        task="legalbench",
        dataset=DatasetSpec(local_path=f"file://{path}", limit=3),
        engine={"kind": "vllm-local", "modal": None},
        trace={"sink": "none"},
        job={"mock": True},
    )
    report = preflight.preflight(spec, offline=True)
    assert report["status"] == "prepared", report
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    store = RunStore(run_dir(report["run_id"]))
    with pytest.raises(ValueError, match="not a legalbench subset"):
        runner.run_job(store, mock=None)


# ── F8: honest mock labelling ────────────────────────────────────────────────


def test_legalbench_mock_record_labelled(tmp_path, monkeypatch):
    log = tmp_path / "experiment_log.jsonl"
    monkeypatch.setattr(experiment_log, "jsonl_path", lambda: log)
    monkeypatch.setattr(experiment_log, "md_path", lambda: tmp_path / "experiment_log.md")
    result = runners.run_legalbench_eval(mock=True)
    assert 0.0 <= result["scores"]["exact_match"] < 1.0
    records = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]
    record = records[-1]
    assert record["model"] == "mock/mock-legalbench"
    assert record["mock"] is True
    assert record["seed"] == 42
