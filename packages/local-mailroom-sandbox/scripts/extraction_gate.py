#!/usr/bin/env python3
"""Extraction quality gate: build the baseline sample, then calibrate the gate against the dojo.

The gate (``task: extraction_gate``, question set ``config/decisions/extraction_gate_v*.yaml``) is
the Decisions model ``openai/gpt-6-luna-decisions`` reading a document with the specialist's real
extraction of it. Its truth is the dojo score of that extraction against the row's
``expected_fields`` (the same scorer every specialist run uses).

``inputs`` writes the baseline documents, mailroom-dataset ground_truth rows taken from a locked
run's ``dataset.jsonl``, stratified by subclass within each of the five classes (seed 42):
one file per class for the specialist runs (``data/runtime/handoff/gate-<split>-<class>.jsonl``)
and their union for the gate run (``gate-<split>.jsonl``). A class's rows must carry its ground
truth (CUAD / MAUD labels for contract / merger, populated fields otherwise).

``expand`` writes a further round (``--tag r2``: ``gate-<split>-r2-<class>.jsonl`` and their union)
of documents no live specialist run has extracted yet, by id and by folded text, so no example is
collected twice. Each subclass draws from its shorter half first (cheap documents), contracts cover
every CUAD subtype, and merger agreements are limited to labelled consideration subclasses. Contracts
and merger agreements are the exception to short-first: drawn representatively, full length.

``calibrate`` reads a finished gate run: per class and overall, how well ``accept_probability``
separates good extractions (dojo score >= --good) from bad ones (AUROC), the accept cutoff that
keeps precision >= --precision, and per-field support against per-field truth.

    python scripts/extraction_gate.py --split train inputs --dataset-run reviewer-calibration-luna-decisions-v3.1.0-train
    sandbox run start --config config/runs/extraction-gate-specialist-<class>-qwen.yaml --initials XX   # x5
    sandbox run start --config config/runs/extraction-gate-luna-v1.0.0-baseline.yaml --initials XX
    python scripts/extraction_gate.py calibrate --run extraction-gate-luna-v1.0.0-baseline
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import random
from pathlib import Path
from typing import Any

from mailroom_sandbox.job.spec import run_dir, runs_root
from mailroom_sandbox.paths import repo_root

CLASSES = ("insurance_claim", "corporate_record", "correspondence", "contract", "merger_agreement")
# Baseline size per class: small enough to afford, large enough for a per-class AUROC.
BASELINE = {"insurance_claim": 60, "corporate_record": 40, "correspondence": 60, "contract": 40, "merger_agreement": 20}
# Contract and merger documents run to hundreds of thousands of characters; the baseline caps the
# length so a handful of outliers cannot take the budget (the cap is reported with the sample).
MAX_CHARS = {"contract": 120_000, "merger_agreement": 400_000}


def _lines(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="\n") as handle:
        return [json.loads(line) for line in handle.read().split("\n") if line.strip()]


def _expected(row: dict) -> dict:
    raw = row.get("expected_fields") or {}
    return json.loads(raw) if isinstance(raw, str) else dict(raw)


def has_truth(row: dict) -> bool:
    """Whether the row carries ground truth the dojo scores an extraction of its class against."""
    exp = _expected(row)
    cls = row.get("expected_doc_class")
    if cls == "contract":
        return exp.get("cuad_clause_labels") not in (None, "", "{}", {})
    if cls == "merger_agreement":
        return exp.get("maud_clause_labels") not in (None, "", "{}", {})
    try:
        presence = json.loads(exp.get("gt_presence") or "{}")
    except (TypeError, ValueError):
        presence = {}
    return any(v == "populated" for v in presence.values())


def stratified(rows: list[dict], count: int, seed: int) -> list[dict]:
    """``count`` rows spread evenly over subclasses (round-robin over seeded shuffles)."""
    rng = random.Random(seed)
    by_sub: dict[str, list[dict]] = collections.defaultdict(list)
    for row in sorted(rows, key=lambda r: r["id"]):
        by_sub[str(row.get("expected_subclass") or "")].append(row)
    for bucket in by_sub.values():
        rng.shuffle(bucket)
    picked: list[dict] = []
    order = sorted(by_sub)
    while len(picked) < count and any(by_sub.values()):
        for sub in order:
            if by_sub[sub] and len(picked) < count:
                picked.append(by_sub[sub].pop())
    return sorted(picked, key=lambda r: r["id"])


def cmd_inputs(args: argparse.Namespace) -> int:
    root = repo_root()
    rows: dict[str, dict] = {}
    for rid in args.dataset_run:
        for row in _lines(run_dir(rid) / "dataset.jsonl"):
            if row.get("split", args.split) == args.split:
                rows.setdefault(row["id"], row)
    out_dir = root / "data" / "runtime" / "handoff"
    out_dir.mkdir(parents=True, exist_ok=True)
    union: list[dict] = []
    summary: dict[str, Any] = {}
    for cls in CLASSES:
        pool = [r for r in rows.values() if r.get("expected_doc_class") == cls and has_truth(r)
                and len(r.get("doc_text") or "") <= MAX_CHARS.get(cls, 10**9)]
        picked = stratified(pool, BASELINE[cls], args.seed)
        text = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in picked)
        path = out_dir / f"gate-{args.split}-{cls}.jsonl"
        path.write_text(text, encoding="utf-8")
        union.extend(picked)
        summary[cls] = {"file": str(path.relative_to(root)), "documents": len(picked), "pool": len(pool),
                        "max_chars": MAX_CHARS.get(cls), "doc_chars": sum(len(r["doc_text"]) for r in picked),
                        "by_subclass": dict(collections.Counter(r.get("expected_subclass") for r in picked)),
                        "sha256": hashlib.sha256(text.encode()).hexdigest()}
    text = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in sorted(union, key=lambda r: r["id"]))
    path = out_dir / f"gate-{args.split}.jsonl"
    path.write_text(text, encoding="utf-8")
    summary["all"] = {"file": str(path.relative_to(root)), "documents": len(union),
                      "doc_chars": sum(len(r["doc_text"]) for r in union), "sha256": hashlib.sha256(text.encode()).hexdigest()}
    print(json.dumps(summary, indent=2))
    return 0


# ---------------------------------------------------------------------------- expansion rounds

# Round-2 additions per class (on top of the baseline): many more of the small, cheap classes,
# a slight increase in contracts spread over every CUAD subtype, and a minimal merger top-up
# restricted to labelled consideration subclasses.
ROUND2 = {"insurance_claim": 240, "correspondence": 240, "corporate_record": 160, "contract": 40,
          "merger_agreement": 10}
EXCLUDE_SUBCLASSES = {"merger_agreement": {"other", "", "None"}}
# Exceptions to short-first: contracts and merger agreements are drawn representatively by length
# (seeded random within each subtype) with no length cap, so full-length documents stay in.
REPRESENTATIVE = {"contract", "merger_agreement"}


def text_key(text: str | None) -> str:
    """Whitespace- and case-folded text hash: the same document under two ids is one example."""
    return hashlib.sha256(" ".join((text or "").split()).lower().encode()).hexdigest()


def round_files(root: Path, split: str, tag: str) -> list[Path]:
    """This round's input files: ``gate-<split>-<tag>.jsonl`` and ``gate-<split>-<tag>-<class>.jsonl``.

    Matched exactly, so round ``r2`` never picks up ``r20``'s files.
    """
    handoff = root / "data" / "runtime" / "handoff"
    return sorted({*handoff.glob(f"gate-{split}-{tag}.jsonl"), *handoff.glob(f"gate-{split}-{tag}-*.jsonl")})


def collected(root: Path, *, skip: set[Path] = frozenset()) -> tuple[set[str], set[str], list[str]]:
    """Ids and text keys of every document a live specialist run already extracted.

    Runs are read from the configured run root (``MAILROOM_BASE_DIR``). Earlier rounds' input
    files count too, except those in ``skip`` (the round being rebuilt).
    """
    from mailroom_sandbox.job.checkpoint import RunStore

    ids: set[str] = set()
    keys: set[str] = set()
    runs: list[str] = []
    for lock_path in sorted(runs_root().glob("*/spec.lock.json")):
        try:
            store = RunStore(lock_path.parent)
            lock = store.read_lock()
        except Exception:  # noqa: BLE001 - unreadable runs cannot have collected anything
            continue
        if not str(lock.get("task") or "").endswith("_specialist") or (lock.get("job") or {}).get("mock"):
            continue
        rows = {str(r["id"]): r for r in store.dataset_rows()}
        done = {str(i["item_id"]) for i in store.load_items() if i.get("ok") and not i.get("error")}
        if not done:
            continue
        runs.append(lock_path.parent.name)
        for doc_id in done:
            ids.add(doc_id)
            if doc_id in rows:
                keys.add(text_key(rows[doc_id].get("doc_text")))
    # Earlier rounds' input files count too (a round prepared but not yet run is still taken).
    for path in sorted((root / "data" / "runtime" / "handoff").glob("gate-*.jsonl")):
        if path in skip:
            continue
        for row in _lines(path):
            ids.add(str(row["id"]))
            keys.add(text_key(row.get("doc_text")))
    return ids, keys, runs


def short_first(rows: list[dict], count: int, seed: int, *, short_share: float = 0.5) -> list[dict]:
    """Like :func:`stratified`, but each subclass draws from its shorter half first.

    Within a subclass the rows are split at the ``short_share`` length quantile; the short part is
    shuffled (seeded) and drawn first, then the long part, so every subclass is represented and
    the sample leans to cheap documents without being only the very shortest.
    """
    rng = random.Random(seed)
    by_sub: dict[str, list[dict]] = collections.defaultdict(list)
    for row in sorted(rows, key=lambda r: r["id"]):
        by_sub[str(row.get("expected_subclass") or "")].append(row)
    queues: dict[str, list[dict]] = {}
    for sub, bucket in by_sub.items():
        bucket.sort(key=lambda r: (len(r.get("doc_text") or ""), r["id"]))
        cut = max(1, round(len(bucket) * short_share))
        short, long_ = bucket[:cut], bucket[cut:]
        rng.shuffle(short)
        rng.shuffle(long_)
        queues[sub] = long_[::-1] + short[::-1]  # pop() from the end: short part first
    picked: list[dict] = []
    order = sorted(queues)
    while len(picked) < count and any(queues.values()):
        for sub in order:
            if queues[sub] and len(picked) < count:
                picked.append(queues[sub].pop())
    return sorted(picked, key=lambda r: r["id"])


def cmd_expand(args: argparse.Namespace) -> int:
    root = repo_root()
    rows: dict[str, dict] = {}
    for rid in args.dataset_run:
        for row in _lines(run_dir(rid) / "dataset.jsonl"):
            if row.get("split", args.split) == args.split:
                rows.setdefault(row["id"], row)
    existing = round_files(root, args.split, args.tag)
    if existing and not args.overwrite:
        # Once the round's specialist runs finish, its documents count as history, so a rebuild
        # would pick different documents than the runs (and the gate config) used.
        print(f"extraction_gate expand: round {args.tag!r} already has {len(existing)} input file(s); refusing "
              "to rebuild it (pass --overwrite only if none of its runs has started)")
        return 1
    counts = dict(ROUND2)
    for spec in args.count:
        cls, _, n = spec.partition("=")
        if cls not in CLASSES or not n.isdigit():
            print(f"extraction_gate expand: --count {spec!r} must be CLASS=N with CLASS one of {', '.join(CLASSES)}")
            return 1
        counts[cls] = int(n)
    # Rebuilding this round: its own earlier files are not "collected".
    seen_ids, seen_keys, runs = collected(root, skip=set(existing))
    if not runs and not args.allow_no_history:
        print("extraction_gate expand: found no finished specialist run to exclude; refusing "
              "(pass --allow-no-history for a first round)")
        return 1
    for stale in existing:
        stale.unlink()  # only after every check passed
    out_dir = root / "data" / "runtime" / "handoff"
    tag = args.tag
    union: list[dict] = []
    summary: dict[str, Any] = {"excluded_runs": runs, "excluded_ids": len(seen_ids)}
    for cls in CLASSES:
        if not counts.get(cls):
            continue
        skip_sub = EXCLUDE_SUBCLASSES.get(cls, set())
        pool, keys = [], set(seen_keys)
        for r in sorted(rows.values(), key=lambda r: r["id"]):
            key = text_key(r.get("doc_text"))
            if (r.get("expected_doc_class") != cls or not has_truth(r) or r["id"] in seen_ids or key in keys
                    or str(r.get("expected_subclass")) in skip_sub
                    or (cls not in REPRESENTATIVE and len(r.get("doc_text") or "") > MAX_CHARS.get(cls, 10**9))):
                continue
            keys.add(key)  # one example per distinct text inside the pool as well
            pool.append(r)
        picked = (stratified(pool, counts[cls], args.seed) if cls in REPRESENTATIVE
                  else short_first(pool, counts[cls], args.seed, short_share=args.short_share))
        text = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in picked)
        path = out_dir / f"gate-{args.split}-{tag}-{cls}.jsonl"
        path.write_text(text, encoding="utf-8")
        union.extend(picked)
        chars = sorted(len(r["doc_text"]) for r in picked)
        summary[cls] = {"file": str(path.relative_to(root)), "documents": len(picked), "pool": len(pool),
                        "sampling": "representative" if cls in REPRESENTATIVE else f"short-first ({args.short_share})",
                        "pool_median_chars": sorted(len(r["doc_text"]) for r in pool)[len(pool) // 2] if pool else 0,
                        "max_chars": chars[-1] if chars else 0,
                        "doc_chars": sum(chars), "median_chars": chars[len(chars) // 2] if chars else 0,
                        "by_subclass": dict(sorted(collections.Counter(str(r.get("expected_subclass")) for r in picked).items())),
                        "sha256": hashlib.sha256(text.encode()).hexdigest()}
    overlap = {r["id"] for r in union} & seen_ids
    assert not overlap, f"round {tag} repeats collected documents: {sorted(overlap)[:5]}"
    text = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in sorted(union, key=lambda r: r["id"]))
    path = out_dir / f"gate-{args.split}-{tag}.jsonl"
    path.write_text(text, encoding="utf-8")
    summary["all"] = {"file": str(path.relative_to(root)), "documents": len(union),
                      "doc_chars": sum(len(r["doc_text"]) for r in union), "sha256": hashlib.sha256(text.encode()).hexdigest()}
    print(json.dumps(summary, indent=2))
    return 0


# ---------------------------------------------------------------------------- calibration

def auroc(scores: list[float], labels: list[bool]) -> float | None:
    """Probability a random good extraction outranks a random bad one (ties count half)."""
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return round(wins / (len(pos) * len(neg)), 4)


def spearman(xs: list[float], ys: list[float]) -> float | None:
    """Rank correlation of the gate's accept probability with the dojo score."""
    if len(xs) < 3:
        return None

    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        out = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                out[order[k]] = (i + j) / 2
            i = j + 1
        return out

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    var = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(cov / var, 4) if var else None


def cutoff_for_precision(scores: list[float], labels: list[bool], precision: float) -> dict[str, Any]:
    """Lowest accept cutoff whose accepted set keeps the target precision (most coverage)."""
    best: dict[str, Any] = {"cutoff": None, "precision": None, "accept_rate": 0.0, "recall": 0.0}
    n_good = sum(labels)
    for cut in sorted(set(scores)):
        acc = [y for s, y in zip(scores, labels) if s >= cut]
        if acc and sum(acc) / len(acc) >= precision:
            return {"cutoff": round(cut, 4), "precision": round(sum(acc) / len(acc), 4),
                    "accept_rate": round(len(acc) / len(labels), 4),
                    "recall": round(sum(acc) / n_good, 4) if n_good else None}
    return best


def _field_truth(doc_type: str, row: dict, fields: dict, good: float) -> tuple[dict[str, bool], str | None]:
    """Per-field correctness of the extraction, from the dojo scorers, and the scorer error if any.

    On an error the row's fields are unscored; ``calibrate`` counts it in ``skipped``.
    """
    exp = _expected(row)
    out: dict[str, bool] = {}
    try:
        if doc_type == "contract":
            from llm_dojo_scoring.sandbox_scoring import FIELD_CATEGORY, _empty, _value_ok, gt_categories

            spans = gt_categories(exp.get("cuad_clause_labels"))
            for field, cat in FIELD_CATEGORY.items():
                if cat in spans:
                    value = fields.get(field)
                    out[field] = (_value_ok(field, value, spans[cat]) if field in ("document_name", "parties", "governing_law")
                                  else not _empty(value)) if spans[cat] else _empty(value)
            from mailroom_sandbox.eval.cuad_scoring import score_cuad

            out["cuad_clauses"] = float(score_cuad(fields, exp["cuad_clause_labels"]).get("cuad_presence_f1") or 0) >= good
            return out, None
        if doc_type == "merger_agreement":
            from mailroom_sandbox.eval.maud_scoring import score_maud

            out["maud_clauses"] = float(score_maud(fields, exp["maud_clause_labels"]).get("maud_accuracy") or 0) >= good
            sub = row.get("expected_subclass")
            if sub and sub != "other":
                out["merger_consideration"] = fields.get("merger_consideration") == sub
            return out, None
        from mailroom_sandbox.datasets import parse_expected_fields
        from mailroom_sandbox.eval.scoring import suite_for_doc_type

        suite = suite_for_doc_type(doc_type)
        kwargs = {"doc_subclass": row.get("expected_subclass")} if doc_type == "corporate_record" and row.get("expected_subclass") else {}
        result = suite.score(parse_expected_fields(row) or exp, fields, doc_text=row.get("doc_text"), detailed=True, **kwargs)
        extraction = result["extraction"] if isinstance(result, dict) else result
        unlabeled = set((result.get("unlabeled_fields") or []) if isinstance(result, dict) else [])
        for field, score in (getattr(extraction, "field_scores", None) or {}).items():
            if field not in unlabeled:
                out[field] = float(getattr(score, "score", score)) >= good
    except Exception as exc:  # noqa: BLE001 - a scorer gap leaves that row's fields unscored, reported
        print(f"field truth {doc_type} {row.get('id')}: {type(exc).__name__}: {exc}")
        return {}, f"{type(exc).__name__}: {exc}"
    return out, None


# Fields whose labels come from mailbox/template metadata the text does not carry (dojo truth
# rate 0-6% on every class in the 1.1.0 pooled calibration): never part of the key-field target.
UNGROUNDED = {"subject_matter", "keywords", "damages_description", "supporting_documents", "maud_clauses"}


def key_fields(qset: dict | None, doc_type: str) -> set[str]:
    """The key fields of a class: the ones the gate asks about, minus the ungrounded ones."""
    return set(((qset or {}).get("fields") or {}).get(doc_type) or {}) - UNGROUNDED


def _at(scores: list[float], labels: list[bool], cut: float) -> dict[str, float | None]:
    """Accept rate, precision and recall of ``score >= cut``."""
    sel = [y for s, y in zip(scores, labels) if s >= cut]
    return {"cutoff": cut, "accept_rate": round(len(sel) / len(labels), 4) if labels else None,
            "precision": round(sum(sel) / len(sel), 4) if sel else None,
            "recall": round(sum(sel) / max(1, sum(labels)), 4)}


def corrected_truth(doc_type: str, row: dict, fields: dict, truth: dict[str, bool]) -> dict[str, bool]:
    """Field truth with the documented GT/scorer defects corrected (interim_labels.contract_correction).

    Only the Hub's own evidence decides (every extracted party is a CUAD Parties span; the date
    equals the CUAD Agreement Date when CUAD has no Effective Date): the gate is never consulted.
    """
    if doc_type != "contract":
        return truth
    from mailroom_sandbox.interim_labels import contract_correction

    exp = _expected(row)
    return {f: ok or bool(contract_correction(f, fields.get(f), exp)) for f, ok in truth.items()}


def calibrate(items: list[dict], rows: dict[str, dict], handoff: dict[str, dict], *, good: float, precision: float,
              qset: dict | None = None, corrected: bool = False, include_truncated: bool = False) -> dict:
    """Score the gate against two targets.

    A row whose document was cut at the question set's input cap (``pred.truncated``) is
    skipped unless ``include_truncated``: the gate judged an extraction of text it never saw, so
    clauses past the cap look unsupported (1.0.0 cut most merger agreements at 240k).

    ``classes``: the dojo extraction score >= ``good`` (every scored field, free text included).
    ``keyfields``: every labelled key field right (:func:`key_fields`), and the fraction right,
    so a gate that judges key fields is measured on what it can see.
    """
    per: dict[str, dict[str, list]] = collections.defaultdict(lambda: {"p": [], "y": [], "score": [], "verdict": []})
    keyed: dict[str, dict[str, list]] = collections.defaultdict(lambda: {"p": [], "y": [], "frac": [], "verdict": [], "fs": []})
    fields: dict[tuple[str, str], dict[str, list]] = collections.defaultdict(lambda: {"p": [], "y": []})
    skipped = collections.Counter()
    for item in items:
        pred, score = item.get("pred") or {}, item.get("score") or {}
        p, s = pred.get("accept_probability"), score.get("extraction_score")
        doc_id = str(item.get("item_id"))
        if not item.get("ok") or not isinstance(p, (int, float)) or not isinstance(s, (int, float)):
            skipped["no_answer_or_score"] += 1
            continue
        cls = score.get("doc_type") or pred.get("doc_type")
        if pred.get("truncated") and not include_truncated:
            skipped[f"truncated_input:{cls}"] += 1
            continue
        for key in (cls, "all"):
            per[key]["p"].append(float(p))
            per[key]["y"].append(float(s) >= good)
            per[key]["score"].append(float(s))
            per[key]["verdict"].append(pred.get("verdict"))
        ext = (handoff.get(doc_id) or {}).get("fields") or {}
        truth, error = _field_truth(cls, rows[doc_id], ext, good) if doc_id in rows else ({}, None)
        if error:
            # Reported per class: a Dojo source without the scorer's names loses a whole class silently otherwise.
            skipped[f"field_truth_error:{cls}"] += 1
        if corrected and doc_id in rows:
            truth = corrected_truth(cls, rows[doc_id], ext, truth)
        wanted = key_fields(qset, cls)
        key_truth = [ok for f, ok in truth.items() if f in wanted]
        if key_truth:
            support = pred.get("field_support") or {}
            asked = [float(support[f]) for f in sorted(wanted) if isinstance(support.get(f), (int, float))]
            # A run whose set asks no field at all (1.0.0) is scored on its verdict. A run with field
            # answers but not for every key field (e.g. --key-set names fields an older run never
            # asked, or answers went missing) is not scored: any product over the rest is inflated.
            partial = bool(support) and len(asked) < len(wanted)
            if partial:
                skipped[f"key_support_missing:{cls}"] += 1
            fscore = math.prod(asked) if asked else float(p)
            for key in (cls, "all") if not partial else ():
                keyed[key]["fs"].append(fscore)
                keyed[key]["p"].append(float(p))
                keyed[key]["y"].append(all(key_truth))
                keyed[key]["frac"].append(sum(key_truth) / len(key_truth))
                keyed[key]["verdict"].append(pred.get("verdict"))
        for field, ok in truth.items():
            prob = (pred.get("field_support") or {}).get(field)
            if isinstance(prob, (int, float)):
                fields[(cls, field)]["p"].append(float(prob))
                fields[(cls, field)]["y"].append(ok)
    report: dict[str, Any] = {"good_threshold": good, "target_precision": precision, "skipped": dict(skipped),
                              "field_truth": "dojo+gt-corrections" if corrected else "dojo", "classes": {}}
    for cls, d in sorted(per.items()):
        n = len(d["y"])
        median = sorted(d["score"])[n // 2]
        report["classes"][cls] = {
            "n": n, "good_rate": round(sum(d["y"]) / n, 4), "mean_extraction_score": round(sum(d["score"]) / n, 4),
            "accept_auroc": auroc(d["p"], d["y"]),
            # Within-class view: a class whose scores sit far below --good (correspondence free text)
            # still shows whether the gate ranks its better extractions above its worse ones.
            "median_score": round(median, 4),
            "accept_auroc_above_median": auroc(d["p"], [s > median for s in d["score"]]),
            "spearman_accept_vs_score": spearman(d["p"], d["score"]),
            "verdicts": dict(collections.Counter(d["verdict"])),
            "accept_verdict_precision": (round(sum(y for y, v in zip(d["y"], d["verdict"]) if v == "accept")
                                               / max(1, sum(v == "accept" for v in d["verdict"])), 4)),
            "cutoff": cutoff_for_precision(d["p"], d["y"], precision),
        }
    report["keyfields"] = {}
    for cls, d in sorted(keyed.items()):
        n = len(d["y"])
        accepted = [y for y, v in zip(d["y"], d["verdict"]) if v == "accept"]
        report["keyfields"][cls] = {
            "n": n, "fields": sorted(key_fields(qset, cls)) if cls != "all" else None,
            "all_right_rate": round(sum(d["y"]) / n, 4), "mean_fraction_right": round(sum(d["frac"]) / n, 4),
            "accept_auroc": auroc(d["p"], d["y"]), "spearman_accept_vs_fraction": spearman(d["p"], d["frac"]),
            "verdicts": dict(collections.Counter(d["verdict"])),
            "accept_verdict_precision": round(sum(accepted) / len(accepted), 4) if accepted else None,
            "accept_verdict_recall": round(sum(accepted) / max(1, sum(d["y"])), 4),
            "cutoff": cutoff_for_precision(d["p"], d["y"], precision),
            # The gating score (decision_backends.key_field_score): product of key-field supports.
            "field_score_auroc": auroc(d["fs"], d["y"]),
            "field_score_at_half": _at(d["fs"], d["y"], 0.5),
            "field_score_cutoff": cutoff_for_precision(d["fs"], d["y"], precision),
        }
    report["fields"] = {f"{cls}.{field}": {"n": len(d["y"]), "truth_rate": round(sum(d["y"]) / len(d["y"]), 4),
                                           "support_auroc": auroc(d["p"], d["y"])}
                        for (cls, field), d in sorted(fields.items())}
    return report


def cmd_calibrate(args: argparse.Namespace) -> int:
    """Calibrate one gate run, or several pooled (``--run`` repeated; rounds never share a document)."""
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    items: list[dict] = []
    rows: dict[str, dict] = {}
    handoff: dict[str, Any] = {}
    reviewers = []
    for run_id in args.run:
        store = RunStore(run_dir(run_id))
        lock = store.read_lock() or {}
        if lock.get("task") != "extraction_gate":
            print(f"extraction_gate: {run_id} is not an extraction_gate run")
            return 1
        if (lock.get("job") or {}).get("mock", True):
            print(f"extraction_gate: {run_id} is a mock run; nothing to calibrate")
            return 1
        run_rows = {r["id"]: r for r in store.dataset_rows()}
        repeated = set(run_rows) & set(rows)
        if repeated:
            print(f"extraction_gate: {run_id} repeats {len(repeated)} documents of an earlier --run")
            return 1
        rows.update(run_rows)
        handoff.update((lock.get("reviewer") or {}).get("handoff") or {})
        items.extend(store.load_items())
        reviewers.append(lock.get("reviewer") or {})
    if len({r.get("questions_sha256") for r in reviewers}) > 1:
        print("extraction_gate: the runs used different question sets; calibrate them separately")
        return 1
    from mailroom_sandbox.decision_backends import load_question_set

    # --key-set scores an older run's gate on a newer set's key fields, so two sets compare on one target.
    key_stem = args.key_set or reviewers[0].get("questions")
    qset = load_question_set(key_stem) if key_stem else None
    name = args.name or "+".join(args.run)
    report = {"run_id": name, "runs": list(args.run), "question_set": reviewers[0].get("questions"),
              "questions_sha256": reviewers[0].get("questions_sha256"), "key_field_set": key_stem,
              **calibrate(items, rows, handoff, good=args.good, precision=args.precision, qset=qset,
                          corrected=args.corrected_truth, include_truncated=args.include_truncated)}
    out = repo_root() / "reports" / "extraction-gate" / f"{name}.calibration.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"classes": report["classes"], "keyfields": report["keyfields"]}, indent=2, sort_keys=True))
    print(f"wrote {out.relative_to(repo_root())}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", default="train")
    parser.add_argument("--seed", type=int, default=42)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_in = sub.add_parser("inputs", help="write the baseline documents")
    p_in.add_argument("--dataset-run", action="append", required=True)
    p_ex = sub.add_parser("expand", help="write a new round of documents no specialist run has extracted")
    p_ex.add_argument("--dataset-run", action="append", required=True)
    p_ex.add_argument("--tag", default="r2", help="round name used in the output file names")
    p_ex.add_argument("--count", action="append", default=[], metavar="CLASS=N", help="override a ROUND2 count")
    p_ex.add_argument("--allow-no-history", action="store_true")
    p_ex.add_argument("--overwrite", action="store_true", help="rebuild a round whose input files exist")
    p_ex.add_argument("--short-share", type=float, default=0.5,
                      help="draw each subclass from its shortest share of documents first")
    p_ca = sub.add_parser("calibrate", help="score a finished gate run against the dojo")
    p_ca.add_argument("--run", action="append", required=True, help="gate run (repeat to pool rounds)")
    p_ca.add_argument("--name", help="report name when pooling (default: the run ids joined by +)")
    p_ca.add_argument("--corrected-truth", action="store_true",
                      help="correct documented GT/scorer defects in the field truth (CUAD parties/effective date)")
    p_ca.add_argument("--key-set", help="question set whose key fields define the key-field target (default: the run's own)")
    p_ca.add_argument("--good", type=float, default=0.8, help="dojo score at or above which an extraction is good")
    p_ca.add_argument("--precision", type=float, default=0.9, help="target precision of the accepted set")
    p_ca.add_argument("--include-truncated", action="store_true",
                      help="also calibrate rows whose document was cut at the input cap (skipped by default)")
    args = parser.parse_args()
    return {"inputs": cmd_inputs, "expand": cmd_expand, "calibrate": cmd_calibrate}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
