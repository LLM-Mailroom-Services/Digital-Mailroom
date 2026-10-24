"""Observatory BERT lane panels (#111): manifest contract + rendering.

The panels are a vanilla, DOM-free JS module (``hosted/js/bert_panels.js``)
mirroring the Observatory's own conventions, so this suite executes the REAL
shipped module in ``node`` against fixture manifests — one test per panel for
render-with-fixture and one for degrade-when-absent — plus static wiring
checks (the same convention test_hosted.py uses for app.js/index.html) and
server-side lift tests proving ``intake_bert`` reaches the run payload.

Node-only tests SKIP (never fake-pass) when ``node`` is not on PATH; the
Python lift + wiring tests always run.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mailroom_ui.langfuse_source import LangfuseSource
from mailroom_ui.trace_interpreter import interpret_trace
from server.main import create_app
from tests.fake_langfuse import FakeClient, make_trace

ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / "hosted" / "js" / "bert_panels.js"
APP_JS = ROOT / "hosted" / "js" / "app.js"
INDEX = ROOT / "hosted" / "index.html"

NODE = shutil.which("node")

# ---- fixture manifests ---------------------------------------------------
# Shadow-mode docs across TWO artifact revisions: 4 real BERT triages (2 per
# revision), 1 clerk fail-soft handoff, 1 pre-BERT manifest with no block.
REV1 = "abcdef1234567890"
REV2 = "fedcba0987654321"

FIXTURE = [
    # rev1: BERT PASS, sorter agrees, gate skip-eligible, judge CORRECT
    {
        "intake_bert": {
            "available": True, "method": "bert", "doc_type": "contract",
            "doc_type_pass": True, "agreement": True, "artifact_sha": REV1,
            "gate_outcome": {"verdict": "PASS", "mode": "shadow",
                             "eligible_for_sorter_skip": True, "failed_checks": []},
        },
        "doc_type": "contract", "verdict": "CORRECT",
    },
    # rev1: BERT FAIL + label flip vs sorter, gate not skip-eligible
    {
        "intake_bert": {
            "available": True, "method": "bert", "doc_type": "correspondence",
            "doc_type_pass": False, "agreement": False, "artifact_sha": REV1,
            "gate_outcome": {"verdict": "FAIL", "mode": "shadow",
                             "eligible_for_sorter_skip": False,
                             "failed_checks": ["sorter_agreement"]},
        },
        "doc_type": "contract", "verdict": "MISS",
    },
    # rev2: BERT PASS, no gate_outcome yet (gate absent), judge CORRECT
    {
        "intake_bert": {
            "available": True, "method": "bert", "doc_type": "insurance_claim",
            "doc_type_pass": True, "artifact_sha": REV2,
        },
        "doc_type": "insurance_claim", "verdict": "CORRECT",
    },
    # rev2: BERT PASS, no gate_outcome yet, judge PARTIAL
    {
        "intake_bert": {
            "available": True, "method": "bert", "doc_type": "insurance_claim",
            "doc_type_pass": True, "artifact_sha": REV2,
        },
        "doc_type": "insurance_claim", "verdict": "PARTIAL",
    },
    # fail-soft clerk handoff (no doc_type_pass, no gate)
    {
        "intake_bert": {"available": False, "reason": "no_model",
                        "method": "deterministic", "route": "clerk_only"},
        "doc_type": "contract", "verdict": "CORRECT",
    },
    # pre-BERT manifest: no intake.bert at all
    {"doc_type": "contract", "verdict": "CORRECT"},
]

# Expected reductions over FIXTURE (computed by hand from the panel rules):
#   bert-pass      3/4 (75%)   rev1 1/2 · rev2 2/2
#   sorter-skip    1/2 (50%)
#   disagreement   1/4 (25%)   (rev2 docs carry both labels -> comparable, agree)
#   fail-soft      1/5 (20%)   reasons {no_model: 1}
#   extract-acc    2/4 (50%)   rev1 1/2 · rev2 1/2  (waits on judge verdicts)


def _node(expr: str) -> object:
    """Evaluate a JS expression with bert_panels.js loaded; return JSON."""
    code = (
        f'const P = require({json.dumps(str(MODULE))});\n'
        f"const out = {expr};\n"
        "process.stdout.write(JSON.stringify(out));"
    )
    res = subprocess.run([NODE, "-e", code], capture_output=True, text=True, timeout=30)
    if res.returncode != 0:
        raise AssertionError(f"node failed:\nstdout={res.stdout}\nstderr={res.stderr}")
    return json.loads(res.stdout)


def _render(manifests: list[dict]) -> str:
    return _node(f"P.render({json.dumps(manifests)})")


def _compute(manifests: list[dict]) -> dict:
    return _node(f"P.compute({json.dumps(manifests)})")


needs_node = pytest.mark.skipif(NODE is None, reason="node not on PATH")


# ---- module + wiring (always run, static convention) ---------------------

def test_module_is_wired_into_the_observatory():
    assert 'bert_panels.js' in INDEX.read_text(encoding="utf-8")
    assert 'id="bert-panels"' in INDEX.read_text(encoding="utf-8")
    assert 'id="bert-panels-body"' in INDEX.read_text(encoding="utf-8")
    js = APP_JS.read_text(encoding="utf-8")
    assert "renderBertPanels(runs)" in js
    assert "window.BERTPanels" in js
    assert 'bert_panels.js did not load' in js


def test_module_is_vanilla_and_pure():
    src = MODULE.read_text(encoding="utf-8")
    assert '"use strict"' in src
    assert "document.getElementById" not in src
    assert "fetch(" not in src
    assert "window.BERTPanels" in src  # browser binding
    assert "module.exports" in src     # node binding (tests)


def test_five_panels_declared():
    keys = _node("P.PANELS.map(p => p.key)")
    assert keys == ["bert-pass", "sorter-skip", "disagreement", "fail-soft", "extract-accuracy"]


@needs_node
def test_compute_reductions_match_the_fixture():
    c = _compute(FIXTURE)
    assert c["runs"] == 6 and c["bertDocs"] == 5
    assert c["modes"] == ["shadow"]
    assert c["panels"]["bert-pass"]["n"] == 3 and c["panels"]["bert-pass"]["d"] == 4
    assert c["panels"]["sorter-skip"]["n"] == 1 and c["panels"]["sorter-skip"]["d"] == 2
    assert c["panels"]["disagreement"]["n"] == 1 and c["panels"]["disagreement"]["d"] == 4
    assert c["panels"]["fail-soft"]["n"] == 1 and c["panels"]["fail-soft"]["d"] == 5
    assert c["panels"]["fail-soft"]["reasons"] == {"no_model": 1}
    assert c["panels"]["extract-accuracy"]["n"] == 2 and c["panels"]["extract-accuracy"]["d"] == 4
    # two artifact revisions drive per-revision columns
    revs = c["panels"]["bert-pass"]["byRevision"]
    assert set(revs) == {REV1, REV2}
    assert revs[REV1] == {"n": 1, "d": 2} and revs[REV2] == {"n": 2, "d": 2}


# ---- one test per panel: renders with a fixture manifest -----------------

@needs_node
def test_panel_bert_pass_renders_with_fixture():
    html = _render(FIXTURE)
    assert "BERT pass rate" in html
    assert "75% (3/4)" in html
    assert "doc_type_pass" in html and "intake.bert.doc_type_pass" in html
    assert "revision abcdef12" in html and "revision fedcba09" in html  # per-revision columns


@needs_node
def test_panel_sorter_skip_renders_with_fixture():
    html = _render(FIXTURE)
    assert "Sorter-skip rate" in html
    assert "50% (1/2)" in html
    assert "eligible_for_sorter_skip" in html
    assert "gate mode shadow" in html  # provenance chip, not promotion authority


@needs_node
def test_panel_disagreement_renders_with_fixture():
    html = _render(FIXTURE)
    assert "Disagreement rate" in html
    assert "25% (1/4)" in html
    assert "intake.bert.agreement" in html and "failed_checks" in html


@needs_node
def test_panel_fail_soft_renders_with_fixture():
    html = _render(FIXTURE)
    assert "Fail-soft rate" in html
    assert "20% (1/5)" in html
    assert "no_model" in html and "intake.bert.reason" in html


@needs_node
def test_panel_extract_accuracy_renders_with_fixture():
    html = _render(FIXTURE)
    assert "Downstream extract accuracy" in html
    assert "50% (2/4)" in html
    assert "verdict" in html and "revision abcdef12" in html


# ---- one test per panel: degrades when the field is absent ---------------

NO_BERT = [
    {"doc_type": "contract", "verdict": "CORRECT"},
    {"doc_type": "correspondence"},
]


@needs_node
def test_panel_bert_pass_degrades_when_field_absent():
    html = _render(NO_BERT)
    assert "BERT pass rate" in html
    assert "No BERT manifests in the live window" in html
    assert "No data in the live window" in html
    assert "0/0" in html  # n/d columns read zero, never a fabricated rate


@needs_node
def test_panel_sorter_skip_degrades_when_field_absent():
    html = _render(NO_BERT)
    assert "Sorter-skip rate" in html
    assert "No data in the live window" in html


@needs_node
def test_panel_disagreement_degrades_when_field_absent():
    html = _render(NO_BERT)
    assert "Disagreement rate" in html
    assert "No data in the live window" in html


@needs_node
def test_panel_fail_soft_degrades_when_field_absent():
    html = _render(NO_BERT)
    assert "Fail-soft rate" in html
    assert "No data in the live window" in html


@needs_node
def test_panel_extract_accuracy_degrades_when_field_absent():
    # bert-triaged docs WITH NO judge verdicts: awaiting state, not a zero.
    awaiting = [
        {"intake_bert": {"available": True, "method": "bert",
                         "doc_type": "contract", "doc_type_pass": True,
                         "artifact_sha": REV1}, "doc_type": "contract"},
    ]
    html = _render(awaiting)
    assert "Downstream extract accuracy" in html
    assert "Awaiting data" in html
    assert "no judge verdicts" in html
    assert "0/0" in html


# ---- server-side lift (always run) ---------------------------------------

def test_interpreter_lifts_intake_bert_from_manifest_output():
    bert = {"available": True, "method": "bert", "doc_type": "contract",
            "doc_type_pass": True, "artifact_sha": REV1,
            "gate_outcome": {"verdict": "PASS", "mode": "shadow",
                             "eligible_for_sorter_skip": True, "failed_checks": []}}
    trace = make_trace("t-lift", output_extra={"intake": {"bert": bert}})
    run = interpret_trace(trace, trace.get("observations", []), trace.get("scores", []))
    assert run.intake_bert == bert
    assert run.verdict == "CORRECT"  # judge verdict still rides the run


def test_interpreter_leaves_intake_bert_none_without_the_block():
    trace = make_trace("t-plain")
    run = interpret_trace(trace, trace.get("observations", []), trace.get("scores", []))
    assert run.intake_bert is None  # pre-BERT manifests stay clean


def test_traces_payload_carries_intake_bert():
    bert = {"available": True, "method": "bert", "doc_type": "contract",
            "doc_type_pass": True, "artifact_sha": REV1,
            "gate_outcome": {"verdict": "PASS", "mode": "shadow", "failed_checks": []}}
    src = LangfuseSource(client=FakeClient([
        make_trace("t-1"),
        make_trace("t-2", output_extra={"intake": {"bert": bert}}),
    ]))
    with TestClient(create_app(src)) as client:
        runs = client.get("/api/traces").json()["runs"]
    by_trace = {r["trace_id"]: r for r in runs}
    assert by_trace["t-1"]["intake_bert"] is None
    assert by_trace["t-2"]["intake_bert"] == bert


def test_live_assets_mount_bert_panels_module():
    src = LangfuseSource(client=FakeClient([make_trace("t-mount")]))
    with TestClient(create_app(src)) as client:
        r = client.get("/live/static/js/bert_panels.js")
    assert r.status_code == 200
    assert "BERTPanels" in r.text and "module.exports" in r.text