"""Offline readiness of an experiment campaign: oracle mock scoring, reports and watchers (SAND-081)."""
import json
import time

import pytest

from mailroom_sandbox import cli, experiments as ex
from mailroom_sandbox.eval import scoring
from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.job.spec import run_dir
from mailroom_sandbox.mock_llm import fake_structured_payload, oracle_extraction

CUAD_LABELS = {
    "Document Name": [{"text": "SERVICES AGREEMENT"}],
    "Parties": [{"text": "Acme Corp"}, {"text": "Beta LLC"}],
    "Governing Law": [{"text": "laws of Delaware"}],
    "Exclusivity": [{"text": "Provider shall not serve competitors."}],
    "Non-Compete": [],
}
MAUD_LABELS = {
    "Absence of Litigation Closing Condition": {"answer": "Pending"},
    "Accuracy of Target R&W Closing Condition": {"answer": "General R&Ws"},
}


@pytest.fixture(autouse=True)
def environment(monkeypatch, job_data_dir):
    monkeypatch.setattr('mailroom_sandbox.runtime.dotenv_files', lambda: [])
    monkeypatch.setattr('mailroom_sandbox.paths.dotenv_files', lambda: [])
    monkeypatch.delenv('MODAL_WORKSPACE', raising=False)


@pytest.mark.parametrize(("doc_type", "fields", "metric"), [
    ("contract", {"cuad_clause_labels": json.dumps(CUAD_LABELS), "intent": "x", "gt_presence": "{}"},
     "cuad_presence_f1"),
    ("merger_agreement", {"maud_clause_labels": json.dumps(MAUD_LABELS), "keywords": ""}, "maud_accuracy"),
    ("correspondence", {"sender": "Jane", "recipient": "John", "keywords": '["meeting", "tomorrow"]',
                        "sentiment_label": "neutral"}, "extraction_f1"),
])
def test_oracle_answer_scores_perfectly_in_the_specialist_schema(doc_type, fields, metric):
    pred = oracle_extraction(fields, doc_type)
    assert "cuad_clause_labels" not in pred and "maud_clause_labels" not in pred
    scored = scoring.score_extraction_row(doc_type, pred, dict(fields), doc_text="SERVICES AGREEMENT Acme Corp")
    assert scored[metric] == pytest.approx(1.0)
    assert scored["overall_extraction_score"] == pytest.approx(1.0)
    assert scored["schema_adherence"] == 1.0  # JSON-string lists decoded; GT-only keys dropped
    if doc_type == "contract":
        assert scored["cuad_value_correct"] == scored["cuad_value_checked"] == 3


def test_mock_sorter_and_reviewer_answer_with_a_subclass_above_the_review_threshold():
    expect = {"doc_type": "contract", "expected_subclass": "license", "expected_fields": {}}
    for prompt in ("Classify this legal document", "CONFIGURED TAXONOMY\n\nCLASSIFY THIS DOCUMENT\n\nx"):
        payload = fake_structured_payload(prompt, expect)
        assert payload["doc_type"] == "contract" and payload["doc_subclass"] == "license"
        assert payload["confidence"] >= 0.98  # contracts' "high" threshold; 0.97 routed every one to review


def test_in_graph_specialist_prompt_gets_the_oracle_answer():
    expect = {"doc_type": "contract", "expected_fields": {"cuad_clause_labels": json.dumps(CUAD_LABELS)}}
    payload = fake_structured_payload("Sorter classification: doc_type=contract. Extract this document's fields", expect)
    assert "cuad_clauses" in payload and "mock_extraction" not in payload


def _write(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return path


def _row(i, doc_class="correspondence", subclass="email"):
    return {"id": f"{doc_class}-{i}", "doc_text": "Email from Jane to John: meeting tomorrow.",
            "expected_doc_class": doc_class, "expected_subclass": subclass, "expected_stage": "archived",
            "expected_fields": {"sender": "Jane", "recipient": "John"}}


def test_local_dataset_too_small_is_refused_at_create(tmp_path, capsys):
    source = _write(tmp_path / "docs.jsonl", [_row(0)])
    args = ["experiment", "create", "tiny", "--doc-class", "correspondence", "--samples", "3", "--mock",
            "--local-dataset", str(source), "--output", str(tmp_path / "tiny")]
    assert cli.main(args) != 0
    assert "has 1 scoreable correspondence row(s); lower --samples to 1" in capsys.readouterr().err
    assert not (tmp_path / "tiny").exists()


def test_local_dataset_drops_hub_subclass_quotas_it_cannot_fill(tmp_path):
    # The contracts template carries Hub subclass quotas; a local file with other subclasses
    # used to pass create and then fail preflight.
    rows = [{**_row(i, "contract", "Local Subclass"),
             "expected_fields": {"cuad_clause_labels": json.dumps(CUAD_LABELS)}} for i in range(3)]
    source = _write(tmp_path / "docs.jsonl", rows)
    config = tmp_path / "local" / "experiment.yaml"
    assert cli.main(["experiment", "create", "local", "--doc-class", "contract", "--samples", "2", "--mock",
                     "--trace-sink", "none", "--local-dataset", str(source), "--output", str(config.parent)]) == 0
    spec = ex._load(config)[2][0][1]
    assert "sub_buckets" not in spec.dataset.strata["buckets"][0]
    assert cli.main(["experiment", "preflight", "--config", str(config)]) == 0


def test_mock_pipeline_campaign_prepares_without_modal_workspace_and_reports_quality(tmp_path):
    # SAND-078 gives a Modal pipeline's judge its own route; its endpoint is unknown without
    # MODAL_WORKSPACE, which must not refuse a mock campaign's review.
    source = _write(tmp_path / "docs.jsonl", [_row(i) for i in range(2)])
    config = tmp_path / "pipe" / "experiment.yaml"
    assert cli.main(["experiment", "create", "pipe", "--task", "pipeline", "--doc-class", "correspondence",
                     "--samples", "2", "--mock", "--trace-sink", "none", "--local-dataset", str(source),
                     "--output", str(config.parent)]) == 0
    assert "judge" in ex._load(config)[2][0][1].agent_routes
    assert cli.main(["experiment", "launch", "--config", str(config)]) == 0
    store = RunStore(run_dir(ex._load(config)[2][0][1].run_id))
    scores = [item["score"] for item in store.load_items()]
    assert all({"class_correct", "stage_correct", "overall_extraction_score"} <= set(score) for score in scores)
    report = (config.parent / "report.md").read_text()
    assert "## Quality" in report and "| Headline |" in report
    assert "## Sand42 metrics" in report and "## Pipeline routing" in report
    data = json.loads((config.parent / "report.json").read_text())["runs"][0]["sand42"]
    assert data["pipeline"]["documents"] == 2 and data["reliability"]["ok"] == 2
    card = json.loads((config.parent / "cards" / f"{store.run_id}.card.json").read_text())
    assert card["cost"] == {}  # a mock run billed no GPU
    assert any(e["event"] == "start" for e in store.events())


def test_report_shows_paired_quality_deltas(tmp_path):
    source = _write(tmp_path / "docs.jsonl", [_row(i) for i in range(2)])
    config = tmp_path / "grid" / "experiment.yaml"
    assert cli.main(["experiment", "create", "grid", "--design", "sand42", "--doc-class", "correspondence",
                     "--samples", "2", "--mock", "--trace-sink", "none", "--local-dataset", str(source),
                     "--output", str(config.parent)]) == 0
    assert cli.main(["experiment", "launch", "--config", str(config)]) == 0
    report = (config.parent / "report.md").read_text()
    assert "## Paired comparisons" in report and report.count("+0.000") >= 3
    data = json.loads((config.parent / "report.json").read_text())
    assert all(item["paired_quality"]["paired_documents"] == 2 for item in data["comparisons"])
    assert all(run["stored_score_means"]["overall_extraction_score"] == 1.0 for run in data["runs"])


def test_sorting_clock_counts_from_the_latest_start(job_data_dir):
    from mailroom_sandbox.tui.tray_context import lifecycle_from_store

    store = RunStore(run_dir("clock-run"))
    store.write_lock({"run_id": "clock-run", "task": "pipeline", "job": {"concurrency": 8}})
    store.append_event("start", task="pipeline")
    store.write_checkpoint(state="running", cursor=1, total=10, remote=None)
    life = lifecycle_from_store(store, [], now=time.time() + 42)
    assert life["phase"] == "SORTING" and life["elapsed_s"] >= 41


def test_mock_run_starts_no_modal_log_streams(job_data_dir, monkeypatch):
    from mailroom_sandbox import watch
    from mailroom_sandbox.watch import LogBuffer

    store = RunStore(run_dir("mock-logs"))
    store.write_lock({"run_id": "mock-logs", "task": "pipeline", "job": {"mock": True}})
    monkeypatch.setattr(watch, "_stream_logs", lambda *a, **k: pytest.fail("mock runs have no Modal app"))
    sink = LogBuffer(None)
    import threading

    assert watch.start_log_streams(store, "sandbox-vllm", sink, threading.Event()) == []
    assert sink.tail(1) == ["mock run · no Modal app to stream"]


def test_local_strata_counts_scoreable_rows_and_keeps_unicode_separators(tmp_path):
    rows = [{**_row(0), "doc_text": "line\u2028separator"},
            {**_row(1, "contract", "license"), "expected_fields": {"cuad_clause_labels": json.dumps(CUAD_LABELS)}},
            {**_row(2, "contract", "license"), "expected_fields": {}}]  # no CUAD labels: never scoreable
    source = tmp_path / "docs.jsonl"
    source.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    assert ex._local_strata(source) == {"correspondence": ["email"], "contract": ["license"]}


def test_subclass_quota_matches_aliases_as_the_sampler_does():
    local = {"contract": ["License_Agreements", "License_Agreements"]}
    assert ex._fills(local, "contract", {"subclass": "license", "count": 2})
    assert not ex._fills(local, "contract", {"subclass": "license", "count": 3})


def test_usage_reports_a_true_median_and_tolerates_missing_completion_tokens():
    items = [{"ok": True, "latency_ms": ms, "prompt_tokens": 10} for ms in (1, 2, 3, 10)]
    usage = ex._usage(items)
    assert usage == {"prompt_tokens": 40, "completion_tokens": None, "p50_latency_ms": 2.5}


def test_local_dataset_counts_only_requested_subclasses(tmp_path, capsys):
    rows = [{**_row(i, "contract", sub), "expected_fields": {"cuad_clause_labels": json.dumps(CUAD_LABELS)}}
            for i, sub in enumerate(["License_Agreements", "service", "service"])]
    source = _write(tmp_path / "subclasses.jsonl", rows)
    base = ["experiment", "create", "subclass", "--doc-class", "contract", "--samples", "2", "--mock",
            "--trace-sink", "none", "--local-dataset", str(source), "--output", str(tmp_path / "campaign")]
    assert cli.main(base + ["--subclass", "license"]) != 0
    assert "has 1 scoreable contract row(s)" in capsys.readouterr().err
    assert not (tmp_path / "campaign").exists()
    assert cli.main(base + ["--subclass", "license", "--subclass", "service"]) == 0
    assert cli.main(["experiment", "preflight", "--config", str(tmp_path / "campaign" / "experiment.yaml")]) == 0


def test_local_dataset_count_applies_the_requested_subclass(tmp_path, capsys):
    rows = [_row(0, "correspondence", "email"), _row(1, "correspondence", "letter"),
            _row(2, "correspondence", "letter")]
    source = _write(tmp_path / "docs.jsonl", rows)
    args = ["experiment", "create", "sub", "--doc-class", "correspondence", "--samples", "2", "--mock",
            "--subclass", "email", "--local-dataset", str(source), "--output", str(tmp_path / "sub")]
    assert cli.main(args) != 0
    assert "has 1 scoreable correspondence row(s)" in capsys.readouterr().err


def test_local_dataset_count_accepts_several_requested_subclasses(tmp_path):
    rows = [_row(0, "correspondence", "email"), _row(1, "correspondence", "letter"),
            _row(2, "correspondence", "memo")]
    source = _write(tmp_path / "docs.jsonl", rows)
    args = ["experiment", "create", "subs", "--doc-class", "correspondence", "--samples", "2", "--mock",
            "--subclass", "email", "--subclass", "letter", "--trace-sink", "none",
            "--local-dataset", str(source), "--output", str(tmp_path / "subs")]
    assert cli.main(args) == 0
