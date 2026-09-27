#!/usr/bin/env python3
"""Document-class taxonomy parity gate (HUB-019, plan §65/§65A).

Fails (exit 1) when the surfaces that state which document classes are LIVE
ever disagree about the canonical five-class set. The literal source of truth
is ``HUB_CLASSES`` in ``packages/llm-mailroom/src/pipeline/hf_corpora.py`` —
every check diffs against that constant parsed straight out of the file, never
against a hand-maintained copy. ``docs/v7-taxonomy.md`` is the canonical prose
contract.

Strict surfaces (must equal the canonical five):

- ``hf_corpora.py`` ``HUB_CLASSES`` (the anchor itself)
- ``taxonomy.yaml`` ``doc_classes`` live entries (``status: retired`` entries
  are retained machinery, not live classes — docs/v7-taxonomy.md §4)
- llm-mailroom sorter output vocabulary (``sorter_agent.py`` ``DOC_CLASSES``)
- specialist registry coverage (``build_graph.py``
  ``_specialist_extractor_map`` must resolve every live class's specialist)
- ``docs/v7-taxonomy.md`` stated live + v7-represented class blocks
- dojo HF-corpus class universe (``corpus.py`` ``CORPUS_DOC_TYPES`` — pinned
  to ``Lucius-Morningstar/mailroom-dataset``)
- entity-repo pilot class universe (``PILOT_CLASS_KEYS`` — the docclass GT
  surface)
- sandbox docclass fixture (``docclass_mini.jsonl`` ``doc_type`` values)

Structural surfaces (documented compat/retirement remnants — must CONTAIN the
canonical five up to the documented extract alias ``merger_agreement →
contract``, and may only add classes from the retired roster):

- dojo ``config.py`` ``DOC_CLASS_KEYS`` / ``LIVE_DOC_CLASS_KEYS`` /
  ``RETIRED_DOC_CLASS_KEYS``
- dojo ``mailroom.py`` ``LIVE_DOC_TYPES`` / ``RETIRED_DOC_TYPES`` /
  ``EXTRACT_CLASS_ALIASES``
- entity-repo ``sorter_agent.py`` ``DOC_CLASSES`` / ``DOCCLASS_CLASS_KEYS``

Subclass parity layer (HUB-041): per live class, the canonical Hub
``expected_subclass`` vocabulary (pinned from the mailroom-corpus v8 GT,
revision ``eafe1ab4``) must be COVERED by every subclass catalog surface,
whose extras are tolerated only from documented rosters:

- dojo ``corpus.py`` ``DOC_TYPE_SUBCLASSES`` (the scoring catalog — strict:
  extras only from the corporate full-enum roster)
- dojo ``corpus.py`` ``CORPUS_SUBCLASS_SURFACES`` (the observed-GT table —
  must EQUAL the canonical set for the four non-contract classes; contract
  stays folder-style spellings and is only required non-empty)
- dojo ``mailroom.py`` ``HUB_SUBCLASS_INVENTORIES``
- entity-repo ``config/taxonomy.yaml`` ``subclasses:`` blocks
- entity-repo ``sorter_agent.py`` per-class subclass lists
  (``SUBCLASS_DIMENSIONS`` members)
- The-Mailroom ``pipeline_schema.py`` ``DOC_SUBCLASS_BY_CLASS``
- llm-mailroom ``doc_inventories.py`` ``_DOJO_SORTER_SUBCLASSES`` (fallback
  catalog) + ``INSURANCE_CLAIM_TYPES`` (extract claim_type inventory — the
  legacy FNOL lines are a documented roster)

The explicit fallback ``other`` is the sanctioned catch-all on every surface
(docs/v7-taxonomy.md; `other` subclass spans types).

Retired classes (plan §60): ``compliance_filing``, ``court_opinion``,
``due_diligence``. They are former classes, not "extended taxonomy awaiting
coverage"; a surface listing them is tolerated only under the structural
rule above. Reintroducing one as live is a fresh taxonomy decision requiring
its own ``taxonomy_version`` bump — this gate must never learn them as live.

Usage:
    python scripts/taxonomy_parity.py [--json] [--root PATH]

Exit 0 = parity holds; exit 1 = drift (readable diagnostics listed). Stdlib
only, network-free; modeled on the ``github_labels.py audit`` CI-gate pattern.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Plan §60 retired roster — former classes, tolerated only as remnants.
RETIRED_ROSTER = frozenset({"compliance_filing", "court_opinion", "due_diligence"})

#: Documented extract alias (dojo mailroom.py): merger extracts via the
#: contracts specialist / ContractExtraction while staying a distinct class.
#: docs/v7-taxonomy.md; plan §6/§59/§81.
KNOWN_EXTRACT_ALIASES = frozenset({"merger_agreement"})

HF_CORPORA = "packages/llm-mailroom/src/pipeline/hf_corpora.py"
TAXONOMY_YAML = "packages/llm-mailroom/src/config/taxonomy.yaml"
MAILROOM_SORTER = "packages/llm-mailroom/src/langchain_agents/sorter_agent.py"
MAILROOM_GRAPH = "packages/llm-mailroom/src/graph/build_graph.py"
MAILROOM_DOC_INVENTORIES = "packages/llm-mailroom/src/langchain_agents/doc_inventories.py"
V7_TAXONOMY_DOC = "docs/v7-taxonomy.md"
DOJO_CORPUS = "packages/llm-dojo-scoring/llm_dojo_scoring/corpus.py"
DOJO_CONFIG = "packages/llm-dojo-scoring/llm_dojo_scoring/config.py"
DOJO_MAILROOM = "packages/llm-dojo-scoring/llm_dojo_scoring/mailroom.py"
ENTITY_SORTER = "packages/llm-entity-extraction/agents/sorter_agent.py"
ENTITY_TAXONOMY = "packages/llm-entity-extraction/config/taxonomy.yaml"
THE_MAILROOM_SCHEMA = "packages/The-Mailroom/mailroom_ui/pipeline_schema.py"
SANDBOX_FIXTURE = "packages/local-mailroom-sandbox/data/fixtures/hf/docclass_mini.jsonl"

# --- HUB-041 subclass layer ---------------------------------------------------
#
# Canonical Hub expected_subclass vocabulary per live class, re-pinned from
# the CURRENT dataset: mailroom-dataset v9 (Lucius-Morningstar/mailroom-dataset,
# pinned tip 46a4d3c2, 3,302 rows, GT-closure revision 2026-09-13) — the
# canonical successor of the frozen mailroom-corpus v8 baseline (eafe1ab4,
# 2,000 rows; DMR-071 adjudication 2026-09-16: the dataset pin is the source
# of truth). Contract GT carries 26 folder-style subclass spellings
# ("License_Agreements", "Joint Venture _ Filing", ...) that normalize onto
# these 25 CUAD family keys (dojo normalize_subtype). Correspondence GT
# carries exactly the 8 communication-form tokens — the `voicemail` key from
# the v8-era Enron labeler enum is NOT in the v9 GT vocabulary and was
# removed from every catalog surface (DMR-071).
HUB_SUBCLASSES: dict[str, frozenset[str]] = {
    "contract": frozenset({
        "affiliate", "agency", "collaboration", "co_branding", "consulting",
        "development", "distributor", "endorsement", "franchise", "hosting",
        "ip", "joint_venture", "license", "maintenance", "manufacturing",
        "marketing", "non_compete_no_solicit", "outsourcing", "promotion",
        "reseller", "service", "sponsorship", "strategic_alliance", "supply",
        "transportation",
    }),
    "merger_agreement": frozenset({
        "all_cash", "all_stock", "mixed_cash_stock", "mixed_cash_stock_election",
        "other",
    }),
    "corporate_record": frozenset({
        "articles_of_incorporation", "board_resolution", "bylaws",
        "charter_amendment", "indenture", "officer_certificate", "other",
        "powers_of_attorney", "rights_instrument", "subsidiary_list",
    }),
    "correspondence": frozenset({
        "email", "letter", "memo", "notice", "demand", "attorney_demand",
        "press_release", "meeting_request",
    }),
    "insurance_claim": frozenset({
        "carrier", "inpatient", "outpatient", "pde", "property", "auto",
    }),
}

#: Documented extras: corporate_record's full scoring enum extends the 10-token
#: v9 GT vocabulary with exactly one record type (`certificate_of_formation`,
#: LLC formation certificates — EDGAR EX-3.1 convention, dojo corpus.py "full
#: enum is the scoring surface"); the insurance EXTRACT claim_type inventory
#: keeps the legacy FNOL product lines (doc_inventories.py). `other` is the
#: sanctioned fallback everywhere and never needs a roster entry.
CORPORATE_FULL_ENUM_EXTRAS = frozenset({
    "certificate_of_formation",
})
INSURANCE_EXTRACT_EXTRAS = frozenset({
    "liability", "health", "life", "workers_comp",
})

#: entity sorter per-class subclass list variable names (agents/sorter_agent.py).
ENTITY_SORTER_SUBCLASS_VARS = {
    "merger_agreement": "MERGER_SUBCLASSES",
    "corporate_record": "CORPORATE_RECORD_SUBCLASSES",
    "correspondence": "CORRESPONDENCE_SUBCLASSES",
    "insurance_claim": "INSURANCE_CLAIM_SUBCLASSES",
}


class Drift(Exception):
    """One parity violation, with the surface it was found on."""


def read(root: Path, rel: str) -> str:
    path = root / rel
    if not path.is_file():
        raise Drift(f"{rel}: file missing (expected by the parity gate)")
    return path.read_text(encoding="utf-8")


def module_assigns(source: str, seed: dict | None = None):
    """Parse a module and return {target_name: literal_value_or_None}.

    List ``+`` concatenations evaluate when every operand is a known literal;
    anything non-literal records None (the caller decides if that is fatal).
    ``seed`` pre-populates known names (e.g. constants resolved from a sibling
    module the target imports them from).
    """
    tree = ast.parse(source)
    values: dict[str, object] = dict(seed or {})

    def literal(node):
        try:
            return ast.literal_eval(node)
        except (ValueError, SyntaxError):
            return None

    def resolve(node):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = resolve(node.left), resolve(node.right)
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            if isinstance(left, tuple) and isinstance(right, tuple):
                return left + right
            return None
        if isinstance(node, ast.List):
            items = [resolve(item) for item in node.elts]
            return items if all(i is not None for i in items) else None
        if isinstance(node, ast.Tuple):
            items = [resolve(item) for item in node.elts]
            return tuple(items) if all(i is not None for i in items) else None
        if isinstance(node, ast.Dict):
            keys = [None if k is None else resolve(k) for k in node.keys]
            vals = [resolve(v) for v in node.values]
            if any(k is None for k in keys) or any(v is None for v in vals):
                return None
            return dict(zip(keys, vals))
        if isinstance(node, ast.Name):
            return values.get(node.id)  # previously assigned literal (list concat)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "tuple"
            and len(node.args) == 1
            and not node.keywords
        ):
            item = resolve(node.args[0])
            return tuple(item) if isinstance(item, (list, tuple)) else None
        return literal(node)

    for node in tree.body:
        if isinstance(node, ast.Assign):
            value = resolve(node.value)
            for target in node.targets:
                if isinstance(target, ast.Name):
                    values[target.id] = value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            values[node.target.id] = resolve(node.value)
    return values


def function_return_literal(source: str, function: str):
    """Literal returned by a top-level function (e.g. a dict-literal mapping).

    For dict returns whose values are names (``_extract_contracts`` ...),
    only the keys are needed and parsed; values resolve to None.
    """
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function:
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Dict):
                    keys = []
                    for key_node in stmt.value.keys:
                        try:
                            keys.append(ast.literal_eval(key_node))
                        except (ValueError, SyntaxError, TypeError):
                            return None
                    return dict.fromkeys(keys)
                if isinstance(stmt, ast.Return):
                    try:
                        return ast.literal_eval(stmt.value)
                    except (ValueError, SyntaxError, TypeError):
                        return None
    return None


def parse_doc_classes(source: str) -> list[dict]:
    """Minimal strict reader for taxonomy.yaml ``doc_classes`` entries.

    Only the scalar fields the gate needs (``key``, ``status``,
    ``specialist``, ``schema``) are read; anything the reader cannot follow
    is a hard error — a parity gate must never silently misparse.
    """
    lines = source.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.rstrip() == "doc_classes:":
            start = i + 1
            break
    if start is None:
        raise Drift("taxonomy.yaml: no top-level 'doc_classes:' block found")

    entries: list[dict] = []
    current: dict | None = None
    field_indent = None  # indent of an entry-level field (nested maps go deeper)
    for line in lines[start:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            break  # next top-level key: block over
        stripped = line.strip()
        is_item = stripped.startswith("- ")
        if is_item:
            if "key:" not in stripped:
                raise Drift(f"taxonomy.yaml: doc_classes list item without 'key:': {stripped!r}")
            current = {}
            entries.append(current)
            field_indent = indent + 2  # continuation fields align after "- "
            stripped = stripped[2:].strip()
            capture = True  # marker-line fields are entry-level by definition
        else:
            if current is None:
                raise Drift(f"taxonomy.yaml: unexpected line under doc_classes: {line.strip()!r}")
            if field_indent is not None and indent < field_indent:
                raise Drift(f"taxonomy.yaml: unexpected dedent inside doc_classes entry: {line.strip()!r}")
            capture = indent == field_indent
        if not capture or ":" not in stripped:
            continue
        field, _, value = stripped.partition(":")
        field = field.strip()
        if field in {"key", "status", "specialist", "schema"}:
            if field in current:
                raise Drift(f"taxonomy.yaml: duplicate field {field!r} in one doc_classes entry")
            current[field] = value.strip().strip("'\"")
    if not entries:
        raise Drift("taxonomy.yaml: doc_classes block parsed to zero entries")
    for entry in entries:
        if "key" not in entry:
            raise Drift("taxonomy.yaml: doc_classes entry missing 'key'")
    return entries


def parse_md_code_block(source: str, heading: str) -> list[str]:
    """Class list from the fenced block directly under a ```heading```.```"""
    lines = source.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == heading:
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip().startswith("```"):
                    block = []
                    for k in range(j + 1, len(lines)):
                        if lines[k].strip().startswith("```"):
                            if not block:
                                raise Drift(f"docs/v7-taxonomy.md: empty class block under {heading!r}")
                            return [v.strip() for v in block]
                        block.append(lines[k].strip())
                    raise Drift(f"docs/v7-taxonomy.md: unterminated code block under {heading!r}")
            raise Drift(f"docs/v7-taxonomy.md: no code block under {heading!r}")
    raise Drift(f"docs/v7-taxonomy.md: heading {heading!r} not found")


def check_equal(surface: str, got, canon: set[str]) -> list[str]:
    got_set = set(got)
    problems = []
    if len(got_set) != len(got):
        problems.append(f"{surface}: duplicate entries: {sorted(got_set ^ set(got)) or got}")
    if got_set != canon:
        problems.append(
            f"{surface}: expected exactly the canonical five {sorted(canon)}; "
            f"missing={sorted(canon - got_set)} unexpected={sorted(got_set - canon)}"
        )
    return problems


def check_structural(surface: str, got, canon: set[str], aliases: frozenset) -> list[str]:
    """Compat-surface rule: canon ⊆ got ∪ aliases; extras ⊆ retired roster."""
    got_set = set(got)
    covered = got_set | set(aliases)
    problems = []
    if not canon <= covered:
        problems.append(
            f"{surface}: missing live classes (beyond documented aliases "
            f"{sorted(aliases)}): {sorted(canon - covered)}"
        )
    illegal = got_set - canon - RETIRED_ROSTER
    if illegal:
        problems.append(
            f"{surface}: classes outside the canonical five and the retired "
            f"roster {sorted(RETIRED_ROSTER)}: {sorted(illegal)} — a new live "
            "class requires a taxonomy decision (plan §61/§62), not a silent add"
        )
    return problems


# --- surface checks (each appends readable problems) -----------------------


def check_hub_classes(source: str, canon: set[str]) -> list[str]:
    values = module_assigns(source)
    if values.get("HUB_CLASSES") is None:
        raise Drift(f"{HF_CORPORA}: HUB_CLASSES not found / not a literal tuple")
    return check_equal(HF_CORPORA, values["HUB_CLASSES"], canon)


def check_taxonomy_yaml(source: str, canon: set[str]) -> list[str]:
    entries = parse_doc_classes(source)
    live = [e["key"] for e in entries if e.get("status") != "retired"]
    retired = [e["key"] for e in entries if e.get("status") == "retired"]
    problems = check_equal(f"{TAXONOMY_YAML} (live entries)", live, canon)
    outside = sorted(set(retired) - RETIRED_ROSTER)
    if outside:
        problems.append(
            f"{TAXONOMY_YAML}: entries marked 'status: retired' outside the "
            f"§60 retired roster: {outside}"
        )
    for entry in entries:
        if entry["key"] in canon:
            for field in ("specialist", "schema"):
                if not entry.get(field):
                    problems.append(f"{TAXONOMY_YAML}: live class {entry['key']!r} missing {field!r}")
    merger = next((e for e in entries if e["key"] == "merger_agreement"), None)
    if merger and merger.get("status") != "retired":
        if (
            merger.get("specialist") != "merger_agreement_specialist"
            or merger.get("schema") != "MergerAgreementExtraction"
        ):
            problems.append(
                f"{TAXONOMY_YAML}: merger_agreement must route to "
                "merger_agreement_specialist / MergerAgreementExtraction "
                "(DMR-078 dedicated MAUD specialist); got "
                f"specialist={merger.get('specialist')!r} schema={merger.get('schema')!r}"
            )
    return problems


def check_mailroom_sorter(source: str, canon: set[str]) -> list[str]:
    values = module_assigns(source)
    doc_classes = values.get("DOC_CLASSES")
    if not isinstance(doc_classes, list):
        raise Drift(f"{MAILROOM_SORTER}: DOC_CLASSES not found / not a literal list")
    keys = [d.get("key") for d in doc_classes if isinstance(d, dict)]
    return check_equal(MAILROOM_SORTER, keys, canon)


def check_specialist_registry(source: str, yaml_source: str, canon: set[str]) -> list[str]:
    mapping = function_return_literal(source, "_specialist_extractor_map") or {}
    entries = parse_doc_classes(yaml_source)
    live_specialists = {
        e.get("specialist") for e in entries if e["key"] in canon and e.get("status") != "retired"
    }
    missing = sorted(s for s in live_specialists if s not in mapping)
    if missing:
        return [
            f"{MAILROOM_GRAPH}: _specialist_extractor_map does not resolve live "
            f"specialists {missing} — dispatch would fail at runtime"
        ]
    return []


def check_v7_doc(source: str, canon: set[str]) -> list[str]:
    problems = []
    problems += check_equal(
        f"{V7_TAXONOMY_DOC} (Live Mailroom document classes)",
        parse_md_code_block(source, "### Live Mailroom document classes"),
        canon,
    )
    problems += check_equal(
        f"{V7_TAXONOMY_DOC} (v7 represented document classes)",
        parse_md_code_block(source, "### v7 represented document classes"),
        canon,
    )
    return problems


def check_dojo_corpus(source: str, canon: set[str]) -> list[str]:
    values = module_assigns(source)
    doc_types = values.get("CORPUS_DOC_TYPES")
    if doc_types is None:
        raise Drift(f"{DOJO_CORPUS}: CORPUS_DOC_TYPES not found / not a literal tuple")
    problems = check_equal(f"{DOJO_CORPUS} (HF corpus represented classes)", doc_types, canon)
    absent = values.get("CORPUS_ABSENT_DOC_TYPES")
    if absent is not None:
        outside = sorted(set(absent) - RETIRED_ROSTER)
        if outside:
            problems.append(
                f"{DOJO_CORPUS}: CORPUS_ABSENT_DOC_TYPES outside the §60 retired "
                f"roster: {outside}"
            )
    return problems


def check_dojo_config(source: str, canon: set[str]) -> list[str]:
    values = module_assigns(source)
    problems = []
    for name in ("DOC_CLASS_KEYS", "LIVE_DOC_CLASS_KEYS"):
        got = values.get(name)
        if got is None:
            raise Drift(f"{DOJO_CONFIG}: {name} not found / not a literal list")
        problems += check_structural(f"{DOJO_CONFIG} {name}", got, canon, KNOWN_EXTRACT_ALIASES)
    retired = values.get("RETIRED_DOC_CLASS_KEYS")
    if retired is None:
        raise Drift(f"{DOJO_CONFIG}: RETIRED_DOC_CLASS_KEYS not found / not a literal list")
    outside = sorted(set(retired) - RETIRED_ROSTER)
    if outside:
        problems.append(f"{DOJO_CONFIG} RETIRED_DOC_CLASS_KEYS outside the §60 roster: {outside}")
    return problems


def check_dojo_mailroom(source: str, canon: set[str]) -> list[str]:
    values = module_assigns(source)
    problems = []
    live = values.get("LIVE_DOC_TYPES")
    if live is None:
        raise Drift(f"{DOJO_MAILROOM}: LIVE_DOC_TYPES not found / not a literal tuple")
    aliases = values.get("EXTRACT_CLASS_ALIASES")
    if not isinstance(aliases, dict):
        raise Drift(f"{DOJO_MAILROOM}: EXTRACT_CLASS_ALIASES not found / not a literal dict")
    problems += check_structural(
        f"{DOJO_MAILROOM} LIVE_DOC_TYPES", live, canon, frozenset(aliases)
    )
    unknown_alias_targets = sorted(v for v in aliases.values() if v not in live and v not in canon)
    if unknown_alias_targets:
        problems.append(
            f"{DOJO_MAILROOM}: EXTRACT_CLASS_ALIASES targets outside LIVE_DOC_TYPES "
            f"and the canonical five: {unknown_alias_targets}"
        )
    retired = values.get("RETIRED_DOC_TYPES")
    if retired is None:
        raise Drift(f"{DOJO_MAILROOM}: RETIRED_DOC_TYPES not found / not a literal tuple")
    outside = sorted(set(retired) - RETIRED_ROSTER)
    if outside:
        problems.append(f"{DOJO_MAILROOM} RETIRED_DOC_TYPES outside the §60 roster: {outside}")
    return problems


def check_entity_sorter(source: str, canon: set[str]) -> list[str]:
    values = module_assigns(source)
    pilot = values.get("PILOT_CLASS_KEYS")
    if pilot is None:
        raise Drift(f"{ENTITY_SORTER}: PILOT_CLASS_KEYS not found / not a literal list")
    problems = check_equal(f"{ENTITY_SORTER} (pilot class universe)", pilot, canon)
    base = values.get("DOC_CLASSES") or []
    if not base:
        raise Drift(f"{ENTITY_SORTER}: DOC_CLASSES not found / not a literal list")
    extended = values.get("DOCCLASS_CLASSES")
    if not isinstance(extended, list):
        raise Drift(
            f"{ENTITY_SORTER}: DOCCLASS_CLASSES not resolvable as a literal "
            "concatenation — sorter surface changed shape?"
        )
    keys = [d.get("key") for d in extended if isinstance(d, dict)]
    problems += check_structural(
        f"{ENTITY_SORTER} DOCCLASS_CLASS_KEYS", keys, canon, KNOWN_EXTRACT_ALIASES
    )
    return problems


def check_sandbox_fixture(source: str, canon: set[str]) -> list[str]:
    allowed = canon | {"unknown"}
    problems = []
    for n, line in enumerate(source.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise Drift(f"{SANDBOX_FIXTURE}:{n}: not valid JSONL: {exc}")
        doc_type = row.get("doc_type")
        if doc_type not in allowed:
            problems.append(
                f"{SANDBOX_FIXTURE}:{n}: doc_type {doc_type!r} outside the "
                "canonical five (plan §66/§67)"
            )
    return problems


# --- HUB-041 subclass layer ---------------------------------------------------


def parse_entity_taxonomy_subclasses(source: str) -> dict[str, list[str]]:
    """Subclass keys per doc class from entity ``config/taxonomy.yaml``.

    Reads each doc-class entry's optional ``subclasses:`` block (items shaped
    ``- {key: x, label: ...}`` or ``- key: x``). A class without a block is
    simply absent from the result (contract declares its CUAD dimension in a
    comment; the sorter CONTRACT_SUBTYPE_KEYS carry it).
    """
    import re

    result: dict[str, list[str]] = {}
    current: str | None = None
    in_doc_classes = False
    in_subclasses = False
    subclasses_indent = 0
    for raw in source.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        stripped = raw.strip()
        if indent == 0:
            in_doc_classes = stripped == "doc_classes:"
            current = None
            in_subclasses = False
            continue
        if not in_doc_classes:
            continue
        if stripped.startswith("- "):
            body = stripped[2:].strip()
            if in_subclasses and indent > subclasses_indent:
                match = re.match(r"\{?\s*key:\s*([A-Za-z0-9_]+)", body)
                if match and current:
                    result[current].append(match.group(1))
                    continue
            match = re.match(r"key:\s*([A-Za-z0-9_]+)", body)
            if match:
                current = match.group(1)
                result.setdefault(current, [])
                in_subclasses = False
            continue
        if current and stripped == "subclasses:":
            in_subclasses = True
            subclasses_indent = indent
            continue
        if in_subclasses and indent <= subclasses_indent:
            in_subclasses = False
    return result


def _subclass_keys(got) -> list[str]:
    """Key column of a parsed subclass catalog (list of dicts / tuple / dict)."""
    if isinstance(got, dict):
        return [str(k) for k in got.keys()]
    if isinstance(got, (list, tuple)):
        keys = []
        for item in got:
            if isinstance(item, dict) and "key" in item:
                keys.append(str(item["key"]))
            elif isinstance(item, str):
                keys.append(item)
            else:
                return []
        return keys
    return []


def check_subclass_coverage(
    surface: str, doc_class: str, got, extras: frozenset
) -> list[str]:
    """Hub vocabulary ⊆ surface catalog; extras only from rosters.

    The sanctioned catch-all ``other`` is excluded from the strict-coverage
    requirement: per-class sorter lists get it appended once at the
    DOC_SUBCLASSES level (``DOC_SUBCLASS_UNKNOWN``), and the observed-GT
    tables that DO carry it are exact-checked separately.
    """
    keys = _subclass_keys(got)
    if not keys:
        raise Drift(f"{surface}: {doc_class} subclass catalog missing or unparseable")
    problems: list[str] = []
    if len(keys) != len(set(keys)):
        problems.append(f"{surface}: {doc_class} duplicate subclass entries")
    got_set = set(keys)
    canon = HUB_SUBCLASSES[doc_class] - {"other"}
    if not canon <= got_set:
        problems.append(
            f"{surface}: {doc_class} subclass catalog is missing Hub GT "
            f"tokens {sorted(canon - got_set)} (HUB-041 canonical set)"
        )
    illegal = got_set - HUB_SUBCLASSES[doc_class] - extras - {"other"}
    if illegal:
        problems.append(
            f"{surface}: {doc_class} subclass catalog lists tokens outside the "
            f"Hub canonical set and the documented extras {sorted(extras)}: "
            f"{sorted(illegal)} — a new subclass token needs a taxonomy "
            "decision (HUB-041 law), not a silent add"
        )
    return problems


def check_dojo_subclass_catalogs(
    corp_source: str, mail_source: str, config_values: dict | None = None
) -> list[str]:
    problems: list[str] = []
    corpus_values = module_assigns(corp_source, seed=config_values)
    catalogs = corpus_values.get("DOC_TYPE_SUBCLASSES")
    if not isinstance(catalogs, dict):
        raise Drift(f"{DOJO_CORPUS}: DOC_TYPE_SUBCLASSES not found / not a literal dict")
    surfaces = corpus_values.get("CORPUS_SUBCLASS_SURFACES")
    if not isinstance(surfaces, dict):
        raise Drift(f"{DOJO_CORPUS}: CORPUS_SUBCLASS_SURFACES not found / not a literal dict")
    for doc_class in sorted(HUB_SUBCLASSES):
        extras = CORPORATE_FULL_ENUM_EXTRAS if doc_class == "corporate_record" else frozenset()
        problems += check_subclass_coverage(
            f"{DOJO_CORPUS} DOC_TYPE_SUBCLASSES", doc_class,
            catalogs.get(doc_class), extras,
        )
        observed = surfaces.get(doc_class)
        if doc_class == "contract":
            # GT carries folder-style spellings ("License_Agreements", …) that
            # normalize onto the 25 keys — only require the table be populated.
            if not _subclass_keys(observed):
                problems.append(
                    f"{DOJO_CORPUS} CORPUS_SUBCLASS_SURFACES: contract surfaces "
                    "table empty / unparseable"
                )
            continue
        got_set = set(_subclass_keys(observed))
        if got_set != set(HUB_SUBCLASSES[doc_class]):
            problems.append(
                f"{DOJO_CORPUS} CORPUS_SUBCLASS_SURFACES: {doc_class} observed-GT "
                f"surfaces {sorted(got_set)} != the canonical Hub set "
                f"{sorted(HUB_SUBCLASSES[doc_class])} — re-pin against the "
                "mailroom-corpus revision the GT actually carries"
            )
    hub_inventories = module_assigns(mail_source).get("HUB_SUBCLASS_INVENTORIES")
    if not isinstance(hub_inventories, dict):
        raise Drift(
            f"{DOJO_MAILROOM}: HUB_SUBCLASS_INVENTORIES not found / not a literal dict"
        )
    for doc_class in sorted(HUB_SUBCLASSES):
        if doc_class not in hub_inventories:
            continue
        extras = CORPORATE_FULL_ENUM_EXTRAS if doc_class == "corporate_record" else frozenset()
        problems += check_subclass_coverage(
            f"{DOJO_MAILROOM} HUB_SUBCLASS_INVENTORIES", doc_class,
            hub_inventories[doc_class], extras,
        )
    return problems


def check_entity_subclass_surfaces(sorter_source: str, taxonomy_source: str) -> list[str]:
    problems: list[str] = []
    values = module_assigns(sorter_source)
    for doc_class, var in sorted(ENTITY_SORTER_SUBCLASS_VARS.items()):
        extras = CORPORATE_FULL_ENUM_EXTRAS if doc_class == "corporate_record" else frozenset()
        problems += check_subclass_coverage(
            f"{ENTITY_SORTER} {var}", doc_class, values.get(var), extras
        )
    blocks = parse_entity_taxonomy_subclasses(taxonomy_source)
    for doc_class in sorted(HUB_SUBCLASSES):
        if not blocks.get(doc_class):
            # No subclasses block (contract declares its CUAD dimension in a
            # comment; the sorter CONTRACT_SUBTYPE_KEYS carry it) — skip.
            continue
        extras = CORPORATE_FULL_ENUM_EXTRAS if doc_class == "corporate_record" else frozenset()
        problems += check_subclass_coverage(
            f"{ENTITY_TAXONOMY} subclasses[{doc_class}]", doc_class,
            blocks[doc_class], extras,
        )
    return problems


def check_mailroom_subclass_surfaces(inventories_source: str, schema_source: str) -> list[str]:
    problems: list[str] = []
    inv = module_assigns(inventories_source)
    fallback = inv.get("_DOJO_SORTER_SUBCLASSES")
    if not isinstance(fallback, dict):
        raise Drift(
            f"{MAILROOM_DOC_INVENTORIES}: _DOJO_SORTER_SUBCLASSES not found / "
            "not a literal dict"
        )
    for doc_class in sorted(HUB_SUBCLASSES):
        if doc_class not in fallback:
            continue
        extras = CORPORATE_FULL_ENUM_EXTRAS if doc_class == "corporate_record" else frozenset()
        problems += check_subclass_coverage(
            f"{MAILROOM_DOC_INVENTORIES} _DOJO_SORTER_SUBCLASSES", doc_class,
            fallback[doc_class], extras,
        )
    claim_types = inv.get("INSURANCE_CLAIM_TYPES")
    problems += check_subclass_coverage(
        f"{MAILROOM_DOC_INVENTORIES} INSURANCE_CLAIM_TYPES", "insurance_claim",
        claim_types, INSURANCE_EXTRACT_EXTRAS,
    )
    schema_values = module_assigns(schema_source)
    by_class = schema_values.get("DOC_SUBCLASS_BY_CLASS")
    if not isinstance(by_class, dict):
        raise Drift(
            f"{THE_MAILROOM_SCHEMA}: DOC_SUBCLASS_BY_CLASS not found / not a literal dict"
        )
    for doc_class in sorted(HUB_SUBCLASSES):
        if doc_class not in by_class:
            continue
        extras = CORPORATE_FULL_ENUM_EXTRAS if doc_class == "corporate_record" else frozenset()
        problems += check_subclass_coverage(
            f"{THE_MAILROOM_SCHEMA} DOC_SUBCLASS_BY_CLASS", doc_class,
            by_class[doc_class], extras,
        )
    return problems


# --- driver -----------------------------------------------------------------


def run_checks(root: Path) -> list[str]:
    hf = read(root, HF_CORPORA)
    values = module_assigns(hf)
    hub = values.get("HUB_CLASSES")
    if hub is None:
        raise Drift(f"{HF_CORPORA}: HUB_CLASSES not found / not a literal tuple")
    canon = set(hub)
    if len(canon) != len(hub):
        raise Drift(f"{HF_CORPORA}: HUB_CLASSES contains duplicates: {sorted(hub)}")
    if not canon:
        raise Drift(f"{HF_CORPORA}: HUB_CLASSES is empty")

    problems: list[str] = []
    problems += check_hub_classes(hf, canon)
    problems += check_taxonomy_yaml(read(root, TAXONOMY_YAML), canon)
    problems += check_mailroom_sorter(read(root, MAILROOM_SORTER), canon)
    problems += check_specialist_registry(read(root, MAILROOM_GRAPH), read(root, TAXONOMY_YAML), canon)
    problems += check_v7_doc(read(root, V7_TAXONOMY_DOC), canon)
    problems += check_dojo_corpus(read(root, DOJO_CORPUS), canon)
    problems += check_dojo_config(read(root, DOJO_CONFIG), canon)
    problems += check_dojo_mailroom(read(root, DOJO_MAILROOM), canon)
    problems += check_entity_sorter(read(root, ENTITY_SORTER), canon)
    problems += check_sandbox_fixture(read(root, SANDBOX_FIXTURE), canon)
    # HUB-041 subclass layer: per-class Hub GT vocabulary vs every catalog.
    dojo_config_values = module_assigns(read(root, DOJO_CONFIG))
    # config.py derives CONTRACT_SUBTYPE_KEYS via a comprehension over the
    # CONTRACT_SUBTYPES literal — resolve it the same way for the seed.
    subtypes = dojo_config_values.get("CONTRACT_SUBTYPES")
    if isinstance(subtypes, list):
        dojo_config_values["CONTRACT_SUBTYPE_KEYS"] = [
            d["key"] for d in subtypes if isinstance(d, dict) and "key" in d
        ]
    problems += check_dojo_subclass_catalogs(
        read(root, DOJO_CORPUS), read(root, DOJO_MAILROOM), dojo_config_values
    )
    problems += check_entity_subclass_surfaces(
        read(root, ENTITY_SORTER), read(root, ENTITY_TAXONOMY)
    )
    problems += check_mailroom_subclass_surfaces(
        read(root, MAILROOM_DOC_INVENTORIES), read(root, THE_MAILROOM_SCHEMA)
    )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repo root override (tests)")
    args = parser.parse_args(argv)

    try:
        problems = run_checks(args.root)
    except Drift as exc:
        if args.json:
            print(json.dumps({"ok": False, "errors": [str(exc)], "drift": []}, indent=2))
        else:
            print(f"TAXONOMY PARITY: STRUCTURAL ERROR\n  {exc}")
        return 1

    if args.json:
        print(json.dumps({"ok": not problems, "drift": problems}, indent=2))
    elif problems:
        print("TAXONOMY PARITY: DRIFT DETECTED (plan §65A)")
        for problem in problems:
            print(f"  - {problem}")
        print(
            "\nCanonical source: HUB_CLASSES in packages/llm-mailroom/src/"
            "pipeline/hf_corpora.py; prose contract: docs/v7-taxonomy.md."
        )
    else:
        print(
            "TAXONOMY PARITY: OK — all surfaces agree on the canonical "
            "five-class set and the Hub subclass vocabularies (HUB-041 layer)"
        )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
