#!/usr/bin/env python3
"""Verified targets for a saved sorter pass: correct labels, flag disputes, score the sorter.

The saved sorter answers (data/handoff/<name>/<split>.jsonl) are the reviewer's INPUT and are
never changed. This writes data/handoff/<name>/<split>.targets.jsonl: per document the target
class and subclass a reviewer (or any model trained on this data) should be scored against,
why, and whether the sorter got it right. Rules, each recorded in ``target_evidence``:

1. Contract subclass labels are CUAD folder names ("License_Agreements"); the target is the
   taxonomy key ("license"). Status ``label_normalized``.
2. Merger ``other`` is not a consideration type: every such row has no MAUD "Type of
   Consideration" annotation, and every annotated row's label equals its MAUD answer. The
   target subclass is None (status ``unannotated``): class is usable, subclass is not scored.
3. A label is CORRECTED only when two independent sources agree against it: the document's
   own title line (first heading lines, exhibit stamps removed) and the Decisions-model
   reviewer's answer (openai/gpt-6-luna-decisions runs). Status ``corrected``.
4. Exactly one source against the label: status ``disputed``; excluded from training and
   scoring until a person checks it (listed in the report).
6. A sorter class error whose label no rule confirms and the reviewer also disputes is
   ``ambiguous``: kept with all three answers as an ambiguity example, not used as a target.
5. Sorter class errors whose label a deterministic corpus rule confirms are kept as
   ``label`` with that evidence: Enron maildir files are correspondence (all mailbox text is
   correspondence), indenture and registration/investor-rights titles are corporate_record.

    python scripts/patch_sorter_handoff.py --name sorter-qwen3.7-flash --split train \
        --dataset-run sorter-handoff-qwen-train --dataset-run sorter-handoff-qwen-train-rest
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

from mailroom_sandbox.paths import repo_root

# Decisions-model reviewer runs (all openai/gpt-6-luna-decisions); later entries win.
REVIEWER_RUNS = (
    "reviewer-calibration-luna-decisions",
    "reviewer-calibration-luna-decisions-v2",
    "reviewer-validation-luna-decisions-v2-test",
    "reviewer-validation-luna-decisions-v3.0.0-test",
    "reviewer-verify-sorter-handoff-train",  # 3.1.0 on the disputed and unconfirmed train rows
)
REVIEWER_MIN_P = 0.9  # the reviewer counts as a source only at this class probability or above

CONTRACT_KEYS = {
    "affiliate_agreements": "affiliate", "agency_agreements": "agency", "co_branding": "co_branding",
    "collaboration": "collaboration", "consulting_agreements": "consulting", "development": "development",
    "distributor": "distributor", "endorsement": "endorsement", "franchise": "franchise", "hosting": "hosting",
    "ip": "ip", "joint_venture": "joint_venture", "joint_venture_filing": "joint_venture",
    "license_agreements": "license", "maintenance": "maintenance", "manufacturing": "manufacturing",
    "marketing": "marketing", "non_compete_non_solicit": "non_compete_no_solicit", "outsourcing": "outsourcing",
    "promotion": "promotion", "reseller": "reseller", "service": "service", "sponsorship": "sponsorship",
    "strategic_alliance": "strategic_alliance", "supply": "supply", "transportation": "transportation",
}

# Title rules on the heading lines only, most specific first.
TITLE_RULES = (
    ("corporate_record", "charter_amendment", r"^(CERTIFICATE|ARTICLES) OF (AMENDMENT|CORRECTION)"),
    ("corporate_record", "officer_certificate", r"CERTIFICATE OF DESIGNATIONS?\b|OFFICER.?S.? CERTIFICATE"),
    ("corporate_record", "subsidiary_list", r"SUBSIDIARIES OF|LIST OF SUBSIDIARIES"),
    ("corporate_record", "powers_of_attorney", r"^(LIMITED |SPECIAL |DURABLE )?POWERS? OF ATTORNEY"),
    ("corporate_record", "indenture", r"^(FIRST |SECOND |THIRD |[A-Z]+ )?(SUPPLEMENTAL )?INDENTURE\b"),
    ("corporate_record", "rights_instrument", r"REGISTRATION RIGHTS AGREEMENT|INVESTOR RIGHTS AGREEMENT"),
    ("corporate_record", "bylaws", r"^(AMENDED AND RESTATED |RESTATED |SECOND AMENDED AND RESTATED )?BY-?LAWS\b"),
    ("corporate_record", "articles_of_incorporation",
     r"^(AMENDED AND RESTATED |RESTATED |SECOND AMENDED AND RESTATED )?(CERTIFICATE|ARTICLES) OF "
     r"(INCORPORATION|FORMATION|ORGANIZATION)"),
)
MAILDIR = re.compile(r"^[a-z]+-[a-z]+/[^/]+(/[^/]+)*/\d+\.?$")



def label_confirmed(evidence: list[str]) -> bool:
    """Whether a corpus rule confirmed the label: the maildir rule, a title rule or the reviewer.

    The one definition for rule 6 and the ``sorter_class_errors_label_confirmed`` count; an
    evidence note that confirms nothing (a folder-name mapping, the MAUD unannotated note) does not.
    """
    return any("confirm" in e or "maildir" in e or "reviewer agrees" in e for e in evidence)

def _lines(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="\n") as handle:
        return [json.loads(line) for line in handle.read().split("\n") if line.strip()]


def _norm_contract(label: str | None) -> str | None:
    if label is None:
        return None
    key = re.sub(r"[^a-z]+", "_", label.lower()).strip("_")
    return CONTRACT_KEYS.get(key, key)


def _heading(text: str) -> str:
    """The first heading lines: exhibit stamps, links and filing wrappers removed."""
    text = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", text[:3000])
    out = []
    for raw in text.split("\n"):
        line = re.sub(r"\s+", " ", raw).strip().upper()
        if not line or re.match(r"^(EX-|EXHIBIT|EXH\b|<|\d+$|[\d.]+ +[\w.-]+\.HTM)", line) or len(line) < 4:
            continue
        out.append(line)
        if len(out) == 4:
            break
    return "\n".join(out)


def _title_class(text: str) -> tuple[str, str] | None:
    head = _heading(text)
    for cls, sub, rule in TITLE_RULES:
        for line in head.split("\n"):
            if re.search(rule, line):
                return cls, sub
    return None


def _reviewer_answers(root: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for rid in REVIEWER_RUNS:
        path = root / "data" / "runtime" / "runs" / rid / "items.jsonl"
        if not path.is_file():
            continue
        for item in _lines(path):
            pred = item.get("pred") or {}
            if item.get("ok") and pred.get("doc_type"):
                p = pred.get("doc_type_probability", pred.get("confidence"))
                sub = pred.get("doc_subclass") or pred.get("contract_subtype")
                out[str(item["item_id"])] = {"run": rid, "doc_type": pred["doc_type"],
                                             "doc_subclass": _norm_contract(sub) if pred["doc_type"] == "contract" else sub,
                                             "p": p}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--dataset-run", action="append", required=True,
                        help="sorter run whose locked dataset.jsonl holds the document text")
    args = parser.parse_args()
    root = repo_root()
    folder = root / "data" / "handoff" / args.name
    saved = _lines(folder / f"{args.split}.jsonl")
    texts: dict[str, dict] = {}
    for rid in args.dataset_run:
        for row in _lines(root / "data" / "runtime" / "runs" / rid / "dataset.jsonl"):
            texts[row["id"]] = row
    reviewer = _reviewer_answers(root)

    out_rows, status = [], collections.Counter()
    disputes, corrections = [], []
    for row in saved:
        doc = texts[row["id"]]
        label_cls, label_sub = row["expected_doc_class"], row["expected_subclass"]
        target_cls, target_sub, state, evidence = label_cls, label_sub, "label", []
        if label_cls == "contract":
            target_sub = _norm_contract(label_sub)
            state, evidence = "label_normalized", [f"CUAD folder {label_sub!r} -> taxonomy key {target_sub!r}"]
        if label_cls == "merger_agreement" and label_sub == "other":
            fields = doc.get("expected_fields")
            fields = fields if isinstance(fields, dict) else json.loads(fields or "{}")
            maud = json.loads(fields.get("maud_clause_labels") or "{}")
            if "Type of Consideration" not in maud:
                target_sub, state = None, "unannotated"
                evidence = ["merger 'other' has no MAUD Type of Consideration annotation"]

        title = _title_class(doc.get("doc_text") or "")
        rev = reviewer.get(row["id"])
        rev_sure = rev if rev and isinstance(rev.get("p"), (int, float)) and rev["p"] >= REVIEWER_MIN_P else None
        # Rule 3 / 4: label vs title vs reviewer (class and subclass).
        if state in ("label", "label_normalized") and title is not None:
            title_against = title != (target_cls, target_sub)
            rev_pair = (rev_sure["doc_type"], rev_sure["doc_subclass"]) if rev_sure else None
            if title_against and rev_pair == title:
                corrections.append({"id": row["id"], "filename": row["filename"], "label": [label_cls, label_sub],
                                    "target": list(title), "reviewer": rev_sure})
                target_cls, target_sub, state = title[0], title[1], "corrected"
                evidence.append(f"title line says {title[0]}/{title[1]}; Decisions reviewer agrees "
                                f"({rev_sure['run']}, p={rev_sure['p']:.2f})")
            elif title_against and title[0] == target_cls and rev_pair is not None and rev_pair == (target_cls, target_sub):
                evidence.append(f"title rule says {title[1]} but the reviewer agrees with the label; label kept")
            elif title_against and (rev_pair is None or rev_pair != (target_cls, target_sub)):
                state = "disputed"
                evidence.append(f"title line says {title[0]}/{title[1]}; reviewer: "
                                f"{(rev_pair if rev_pair else 'no confident answer')}")
                disputes.append({"id": row["id"], "filename": row["filename"], "label": [label_cls, label_sub],
                                 "title": list(title), "reviewer": rev})
        # Rule 5: confirm the label on sorter class errors with a corpus rule.
        sorter_cls = row.get("sorter_doc_type")
        if sorter_cls != target_cls and state in ("label", "label_normalized"):
            if target_cls == "correspondence" and MAILDIR.match(str(row.get("filename") or "")):
                evidence.append("Enron maildir file: all mailbox text is correspondence")
            elif title is not None and title[0] == target_cls:
                evidence.append(f"title line confirms {title[0]}")
            if rev_sure and rev_sure["doc_type"] == target_cls:
                evidence.append(f"Decisions reviewer confirms the class ({rev_sure['run']}, p={rev_sure['p']:.2f})")
            confirmed = label_confirmed(evidence)
            if not confirmed and rev is not None and rev.get("doc_type") != target_cls:
                # Rule 6: sorter and reviewer both disagree with an unconfirmed label: a real
                # ambiguity case. Kept as an example, not used as a class target.
                state = "ambiguous"
                evidence.append(f"no rule confirms the label; sorter says {sorter_cls}, reviewer says "
                                f"{rev.get('doc_type')} (p={rev.get('p') or 0:.2f})")
        sorter_sub = row.get("sorter_doc_subclass")
        sorter_sub = _norm_contract(sorter_sub) if sorter_cls == "contract" else sorter_sub
        usable = state in ("label", "label_normalized", "corrected", "unannotated")
        record = {
            "id": row["id"], "filename": row["filename"],
            "label_doc_class": label_cls, "label_subclass": label_sub,
            "target_doc_class": target_cls if state not in ("disputed", "ambiguous") else None,
            "target_subclass": target_sub if state not in ("disputed", "ambiguous") else None,
            "target_status": state, "target_evidence": evidence,
            "use_for_class": usable, "use_for_subclass": usable and state != "unannotated",
            "sorter_doc_type": sorter_cls, "sorter_doc_subclass": sorter_sub,
            "sorter_confidence": row.get("sorter_confidence"),
            "sorter_class_correct": (sorter_cls == target_cls) if usable else None,
            "sorter_subclass_correct": (sorter_cls == target_cls and sorter_sub == target_sub)
            if usable and state != "unannotated" else None,
            "reviewer_evidence": rev,
        }
        status[state] += 1
        out_rows.append(json.dumps(record, ensure_ascii=False, sort_keys=True))

    text = "\n".join(out_rows) + "\n"
    path = folder / f"{args.split}.targets.jsonl"
    path.write_text(text, encoding="utf-8")
    rows = [json.loads(line) for line in out_rows]
    cls_rows = [r for r in rows if r["use_for_class"]]
    sub_rows = [r for r in rows if r["use_for_subclass"]]
    summary = {
        "file": path.name, "sha256": hashlib.sha256(text.encode()).hexdigest(), "documents": len(rows),
        "target_status": dict(status),
        "sorter_class_correct": sum(r["sorter_class_correct"] for r in cls_rows),
        "sorter_class_scored": len(cls_rows),
        "sorter_subclass_correct": sum(r["sorter_subclass_correct"] for r in sub_rows),
        "sorter_subclass_scored": len(sub_rows),
        "sorter_class_errors_by_pattern": dict(collections.Counter(
            f"{r['target_doc_class']} -> {r['sorter_doc_type']}" for r in cls_rows if not r["sorter_class_correct"])),
        "sorter_class_errors_label_confirmed": sum(
            1 for r in cls_rows if not r["sorter_class_correct"] and label_confirmed(r["target_evidence"])),
        "corrections": corrections, "disputes": disputes,
        "rules": "scripts/patch_sorter_handoff.py docstring",
    }
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["splits"][args.split]["targets"] = {k: v for k, v in summary.items() if k not in ("corrections", "disputes")}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (folder / f"{args.split}.corrections.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                                                           encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("corrections", "disputes")}, indent=2, sort_keys=True))
    print("corrections", len(corrections), "disputes", len(disputes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
