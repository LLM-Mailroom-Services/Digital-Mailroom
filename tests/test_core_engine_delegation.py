"""Offline eval uses real Dojo; ordinary display import stays dependency-free."""
import math
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def engine_calls():
    """Record real engine calls; never stub the scorer being verified."""
    seen = set()
    old = sys.getprofile()
    def profile(frame, event, arg):
        """Observe executed Dojo functions."""
        if event == "call" and frame.f_globals.get("__name__", "") == "llm_dojo_scoring.pipeline_scoring":
            seen.add(frame.f_code.co_name)
    sys.setprofile(profile)
    try:
        yield seen
    finally:
        sys.setprofile(old)


def test_visualizer_rows_and_predicates_delegate_to_real_dojo():
    """Explicit False, missing GT, asymmetric subclass and display values survive."""
    from mailroom_ui import pipeline_eval as c
    rows = [
        {"expected": "contract", "predicted": "contract", "stage": "archived", "exact_ok": True, "aligned_ok": True, "expected_subclass": "license", "contract_subtype": "license", "cost_usd": 0.1, "total_tokens": 10, "seconds": 2, "intake_changed": True},
        {"expected": "contract", "predicted": "contract", "stage": "review", "exact_ok": True, "aligned_ok": True, "expected_subclass": "license", "doc_subclass": "license", "subclass_ok": False, "cost_usd": 0.2, "total_tokens": 20, "seconds": 4},
        {"expected": None, "predicted": None, "stage": "archived", "predicted_subclass": "license"},
        {"expected": "contract", "stage": "failed", "expected_subclass": "license"},
    ]
    with engine_calls() as calls:
        out = c.score_rows(rows)
        assert c.aligned("contract", "contract")
        assert not c.subclass_ok("maintenance", "license")
        assert c.classify_failure({"stage": "failed"}) == "failed"
    assert out["exact_accuracy"] == 0.5 and out["n"] == 4
    assert out["n_subclass"] == 3 and out["subclass_accuracy"] == 1 / 3
    assert out["confusion"] == {"contract": {"contract": 2, "none": 1}, "unknown": {"none": 1}}
    assert out["by_class"]["contract"] == {"n": 3, "exact": 2, "aligned": 2}
    assert out["cost_usd_sum"] == 0.3 and out["tokens_sum"] == 30
    assert out["latency_s_mean"] == 3.0 and out["intake_changed"] == 1
    assert "predicted_subclass" not in rows[0]
    assert {"score_pipeline_rows", "pipeline_classes_aligned", "pipeline_subclass_match", "classify_pipeline_failure"} <= calls
    assert math.isnan(c.score_rows([{"cost_usd": float("nan")}])["cost_usd_sum"])


def test_import_without_dojo_is_lazy_and_eval_failure_is_actionable():
    """-I -S proves importing the facade needs no environment/site packages."""
    root = str(Path(__file__).resolve().parents[1])
    script = """import sys
sys.path.insert(0, sys.argv[1])
from mailroom_ui import pipeline_eval as c
assert not any(x.startswith('llm_dojo_scoring') for x in sys.modules)
try:
    c.score_rows([])
except ImportError as exc:
    assert 'The-Mailroom[eval]' in str(exc), str(exc)
else:
    raise AssertionError('missing optional scorer must fail explicitly')
print(c.__file__)
"""
    out = subprocess.run([sys.executable, "-I", "-S", "-c", script, root], text=True, capture_output=True)
    assert out.returncode == 0, out.stdout + out.stderr


def test_trace_adapter_delegates_literal_equality_and_keeps_missing_gt_guard():
    """Real trace lifting delegates equality but never credits two absent labels."""
    from scripts.eval_pipeline import traces_to_rows
    with engine_calls() as calls:
        rows = traces_to_rows([
            {"id": "known", "input": {"ground_truth": {"expected_hf_class": "contract"}}, "output": {"doc_type": "contract", "stage": "archived"}},
            {"id": "missing", "input": {}, "output": {"stage": "archived"}},
        ])
    assert rows[0]["exact_ok"] is True
    assert rows[1]["exact_ok"] is False
    assert "pipeline_labels_equal" in calls
