"""DMR-087: paired scorers must refuse mismatched expected/predicted lengths.

``zip`` silently truncates, so ``accuracy(['a', 'b'], ['a'])`` used to return
1.0. Each scorer now raises ``ValueError`` naming both lengths; equal-length
behavior is pinned with hand-computed values.
"""

import pytest

from llm_dojo_scoring.asr import score_transcription
from llm_dojo_scoring.classification import (
    accuracy,
    binary_metrics,
    confusion_matrix,
    macro_accuracy,
    macro_prf,
    per_class_stats,
)
from llm_dojo_scoring.mailroom import score_aligned_classification
from llm_dojo_scoring.tasks import score_task

MSG = r"length mismatch.*expected has 2.*predicted has 1"

EXP2 = ["contract", "correspondence"]
PRED1 = ["contract"]


@pytest.mark.parametrize(
    "call",
    [
        lambda e, p: accuracy(e, p),
        lambda e, p: per_class_stats(e, p),
        lambda e, p: macro_accuracy(e, p),
        lambda e, p: confusion_matrix(e, p),
        lambda e, p: binary_metrics(e, p, "contract"),
        lambda e, p: macro_prf(e, p),
        lambda e, p: macro_prf(e, p, normalize=False),
        lambda e, p: score_transcription(e, p),
        lambda e, p: score_aligned_classification(e, p),
        lambda e, p: score_task("doc_class", e, p),
    ],
    ids=[
        "accuracy", "per_class_stats", "macro_accuracy", "confusion_matrix",
        "binary_metrics", "macro_prf", "macro_prf_raw", "score_transcription",
        "score_aligned_classification", "score_task",
    ],
)
def test_mismatched_lengths_raise(call):
    with pytest.raises(ValueError, match=MSG):
        call(list(EXP2), list(PRED1))
    # predicted longer than expected is equally refused
    with pytest.raises(ValueError, match=r"expected has 1.*predicted has 2"):
        call(list(PRED1), list(EXP2))


def test_accuracy_equal_length():
    assert accuracy(["contract", "correspondence"], ["contract", "contract"]) == 0.5


def test_per_class_stats_equal_length():
    s = per_class_stats(["contract", "correspondence"], ["contract", "contract"])
    assert s["contract"]["accuracy"] == 1.0
    assert s["contract"]["precision"] == 0.5
    assert s["correspondence"]["accuracy"] == 0.0


def test_macro_accuracy_equal_length():
    assert macro_accuracy(
        ["contract", "correspondence"], ["contract", "contract"]
    ) == 0.5


def test_confusion_matrix_equal_length():
    m, labels = confusion_matrix(
        ["contract", "correspondence"], ["contract", "contract"]
    )
    assert labels == ["contract", "correspondence"]
    assert m == [[1, 0], [1, 0]]


def test_binary_metrics_equal_length():
    r = binary_metrics(
        ["contract", "correspondence"], ["contract", "contract"], "contract"
    )
    assert (r["tp"], r["fp"], r["fn"], r["tn"]) == (1, 1, 0, 0)
    assert r["precision"] == 0.5 and r["recall"] == 1.0


def test_macro_prf_equal_length():
    r = macro_prf(["contract", "correspondence"], ["contract", "contract"])
    # contract P=0.5 R=1; correspondence P=0 R=0 -> macro P=0.25 R=0.5
    assert r["precision_macro"] == 0.25
    assert r["recall_macro"] == 0.5
    assert r["n"] == 2


def test_score_transcription_equal_length():
    r = score_transcription(["a b", "c d"], ["a b", "c x"])
    assert r["n"] == 2
    assert r["wer"] == 0.25  # (0/2 + 1/2) / 2


def test_score_transcription_single_pair_unchanged():
    assert score_transcription("a b", "a b")["n"] == 1


def test_score_aligned_classification_equal_length():
    r = score_aligned_classification(EXP2, ["contract", "contract"])
    assert r["n"] == 2
    assert r["exact_accuracy"] == 0.5


def test_score_task_equal_length():
    r = score_task("doc_class", EXP2, ["contract", "contract"])
    assert r["n"] == 2
    assert r["accuracy"] == 0.5
