"""Group serving records into comparable legs (dojo v0.22 ``identity_mixed``).

``compare_serving`` / ``emit_serving_scorecard`` treat each side of a
comparison as ONE leg and mark a leg whose runs differ on
``serving_kind`` / ``model`` / ``prompt_version`` / ``task`` /
``dataset_fingerprint`` / ``dataset_revision`` / ``split`` / ``draw_seed`` as
``identity_mixed`` (and ``emit_serving_scorecard`` refuses it). An experiment
log or a matrix holds many models, prompts and datasets, so pooling "every
local row" against "every API row" produces exactly that.

This module partitions rows the way dojo ``pair_comparable_runs`` does — by
full identity first — and pairs a local-side leg with an API-side leg only
when they measured the same thing (task, prompt, dataset fingerprint, revision,
split, draw seed, quality ``metric_id``). Model and serving kind are what the
two sides are *supposed* to differ on, so they are part of a leg's identity but
not of the pairing key.

It depends only on the dojo; ``job.metrics``, ``eval.scoring`` and the matrix
all share it so ``sandbox eval local_vs_api --from-log``, ``sandbox matrix``
and ``sandbox metrics compare`` group identically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

from llm_dojo_scoring.serving import normalize_serving_record

#: Identity fields every run in one comparison leg must share. Mirrors the
#: dojo's ``serving._LEG_IDENTITY_KEYS`` (tests/test_serving_groups.py pins the
#: two together so a dojo change cannot silently desynchronise the grouping).
LEG_IDENTITY_FIELDS: tuple[str, ...] = (
    "serving_kind",
    "model",
    "prompt_version",
    "task",
    "dataset_fingerprint",
    "dataset_revision",
    "split",
    "draw_seed",
)

#: What a local-side and an API-side leg must share to be compared. ``model``
#: and ``serving_kind`` are deliberately absent: they are the thing compared.
#: Sandbox-only identity on top of the dojo's eight: the sha256 of the prompt text.
#: The dojo identifies a prompt by its label alone, but eval-environment keys can
#: collide with other namespaces (a ``config/prompts`` stem named ``sorter_v1`` is
#: the mailroom text, eval-environment ``sorter_v1`` is not), so runs of different
#: prompt bytes never share a leg or pair, whatever they are called.
EXTRA_IDENTITY_FIELDS: tuple[str, ...] = ("prompt_sha256",)

PAIRING_FIELDS: tuple[str, ...] = (
    "task",
    "prompt_version",
    "dataset_fingerprint",
    "dataset_revision",
    "split",
    "draw_seed",
    "metric_id",
)


def _extra_of(record: Mapping[str, Any] | None) -> dict[str, Any]:
    return {name: ((record or {}).get(name) or None) for name in EXTRA_IDENTITY_FIELDS}


def _identity_of(run: Any, record: Mapping[str, Any] | None = None) -> dict[str, Any]:
    out = {name: getattr(run.identity, name, None) for name in LEG_IDENTITY_FIELDS}
    out.update(_extra_of(record))
    return out


def _pairing_of(run: Any, record: Mapping[str, Any] | None = None) -> dict[str, Any]:
    key = {name: getattr(run.identity, name, None) for name in PAIRING_FIELDS if name != "metric_id"}
    key["metric_id"] = run.metric_id
    key.update(_extra_of(record))
    return key


def leg_identity(record: Mapping[str, Any]) -> dict[str, Any]:
    """The eight leg-identity fields of one serving record (dojo's reading) + the prompt sha256."""
    return _identity_of(normalize_serving_record(record), record)


def pairing_key(record: Mapping[str, Any]) -> dict[str, Any]:
    """What a record measured, independent of who served it."""
    return _pairing_of(normalize_serving_record(record), record)


def _freeze(mapping: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted(mapping.items()))


@dataclass
class Leg:
    """Runs sharing one full identity: safe to pool into one comparison leg."""

    side: str  # sandbox bucket: local | modal | api | unknown
    identity: dict[str, Any]
    key: dict[str, Any]
    rows: list[dict[str, Any]] = field(default_factory=list)

    @property
    def label(self) -> str:
        return leg_label(self.identity)


def leg_label(identity: Mapping[str, Any]) -> str:
    """Short human label: ``model | prompt | task | dataset``."""
    dataset = identity.get("dataset_fingerprint") or identity.get("dataset_revision")
    parts = [
        identity.get("model") or "model?",
        identity.get("prompt_version") or "prompt?",
        identity.get("task") or "task?",
    ]
    if dataset:
        parts.append(str(dataset)[:12])
    return " | ".join(str(p) for p in parts)


def group_legs(
    rows: Iterable[Mapping[str, Any]],
    bucket_of: Callable[[Mapping[str, Any]], str],
) -> list[Leg]:
    """Partition rows into legs by (sandbox bucket, full identity), first-seen order."""
    legs: dict[tuple[Any, ...], Leg] = {}
    for row in rows:
        side = bucket_of(row)
        run = normalize_serving_record(row)
        identity, pairing = _identity_of(run, row), _pairing_of(run, row)
        key = (side, _freeze(identity), _freeze(pairing))
        leg = legs.get(key)
        if leg is None:
            leg = legs[key] = Leg(side=side, identity=identity, key=pairing)
        leg.rows.append(dict(row))
    return list(legs.values())


@dataclass
class LegPair:
    left: Leg
    right: Leg

    @property
    def key(self) -> dict[str, Any]:
        return self.left.key

    @property
    def label(self) -> str:
        return f"{self.left.label}  vs  {self.right.label}"


def pair_legs(lefts: Sequence[Leg], rights: Sequence[Leg]) -> tuple[list[LegPair], list[Leg], list[Leg]]:
    """Pair every left leg with every right leg that measured the same thing.

    Returns ``(pairs, unpaired_lefts, unpaired_rights)``. Two local models run
    against one API model on the same draw give two pairs (each model against
    the API leg), not one pooled leg.
    """
    pairs: list[LegPair] = []
    used_left: set[int] = set()
    used_right: set[int] = set()
    for i, left in enumerate(lefts):
        for j, right in enumerate(rights):
            if _freeze(left.key) == _freeze(right.key):
                pairs.append(LegPair(left, right))
                used_left.add(i)
                used_right.add(j)
    return (
        pairs,
        [leg for i, leg in enumerate(lefts) if i not in used_left],
        [leg for j, leg in enumerate(rights) if j not in used_right],
    )


def pooled_identity_conflict(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """Identity fields that differ across ``rows`` (what dojo calls ``identity_mixed``)."""
    idents = [leg_identity(r) for r in rows]
    return [
        name
        for name in (*LEG_IDENTITY_FIELDS, *EXTRA_IDENTITY_FIELDS)
        if len({i.get(name) for i in idents}) > 1
    ]


def select_pair(pairs: Sequence[LegPair], selector: str | int | None) -> LegPair:
    """Pick one pair by 1-based index or by a unique label substring.

    Raises ``ValueError`` (naming the choices) when nothing or more than one
    pair matches, so a CLI ``--group`` mistake is loud.
    """
    if selector is None:
        raise ValueError("no group selector")
    text = str(selector).strip()
    if text.isdigit():
        idx = int(text)
        if 1 <= idx <= len(pairs):
            return pairs[idx - 1]
        raise ValueError(f"group {idx} out of range (1..{len(pairs)})")
    hits = [p for p in pairs if text.lower() in p.label.lower()]
    if len(hits) == 1:
        return hits[0]
    choices = "; ".join(f"{i}: {p.label}" for i, p in enumerate(pairs, start=1))
    why = "ambiguous" if hits else "matches no group"
    raise ValueError(f"group selector {selector!r} {why}; choices: {choices}")
