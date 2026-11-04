"""Run sandbox experiments with ANY eval-environment prompt version.

eval-environment owns every prompt text: archived ``*_v0``, frozen ``*_v1`` and
every GEPA / manual mutation (``correspondence_specialist_v7``, ``sorter_v3`` ...).
The dojo exposes them through ``llm_dojo_scoring.prompts`` (``get_prompt_version``).
This module is the sandbox's one seam onto that API:

* :func:`lookup_prompt_version` is the ONLY function that touches the dojo. Keys
  resolve from the dojo lineage and from nowhere else: never from the vendored
  mailroom registry (``langchain_agents.prompts.PROMPT_VERSIONS`` also has
  ``sorter_v0 ... sorter_v14`` -- same names, different texts) and never from
  ``config/prompts/*.txt`` (the stem ``sorter_v1`` there is the MAILROOM text).
* :func:`resolve_prompt` returns ``(key, text, sha256)`` for a role; the sha256
  is re-computed from the text and must equal the dojo's.
* A selection (``{role: key}``) is parsed from ``--prompt-version`` /
  ``prompt.versions`` of a run spec, validated (unknown key, key/role mismatch,
  role the pipeline lacks -> :class:`PromptSelectionError`), written into the
  run lock as ``source: eval-environment`` agents, applied through
  ``prompt_registry.apply_runtime_overrides`` and stamped on every record
  (``prompt_version`` = the key, ``prompt_sha256``, ``eval_environment_prompt_key``,
  ``prompt_versions``). ``prompt_version`` and ``prompt_sha256`` are grouping
  identity (``serving_groups``), so different mutations never pool.

With no selection nothing here runs and behaviour is exactly the existing
``*_simplified`` stem default.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

SOURCE = "eval-environment"

_KEY_RE = re.compile(r"^(?P<role>[A-Za-z][A-Za-z0-9_-]*?)_v(?P<n>\d+)$")


class PromptSelectionError(ValueError):
    """A prompt-version selection that cannot be honoured. Always fatal."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── the dojo-facing functions ─────────────────────────────────────────────────
_LINEAGE_API = (
    "PromptVersion",
    "LINEAGE_SOURCE",
    "list_prompt_versions",
    "get_prompt_version",
    "prompt_roles",
    "prompt_chain",
    "latest_prompt_version",
    "default_prompt_version",
    "diff_prompt_versions",
)


def lineage_api() -> Any:
    """The dojo's prompt-lineage module (``llm_dojo_scoring.prompts``), checked for the full API.

    The catalog renderer and the ``sandbox prompts`` commands read the lineage
    through this (the one place that names the dojo module); a dojo without the
    API raises :class:`PromptSelectionError`.
    """
    try:
        import llm_dojo_scoring.prompts as api
    except ImportError as exc:
        raise PromptSelectionError(f"llm_dojo_scoring.prompts is not importable: {exc}") from exc
    missing = [name for name in _LINEAGE_API if not hasattr(api, name)]
    if missing:
        raise PromptSelectionError(
            f"the vendored llm-dojo-scoring lacks the prompt lineage API ({', '.join(missing)}); "
            "re-vendor a dojo that ships llm_dojo_scoring.prompts.lineage"
        )
    return api


def lookup_prompt_version(key: str) -> Any:
    """Return the dojo ``PromptVersion`` for ``key`` (``.role .text .sha256 .lineage ...``).

    The single place the sandbox reads prompt texts from eval-environment.
    Raises :class:`PromptSelectionError` for an unknown key (with the dojo's
    suggestions) and when the vendored dojo has no lineage API yet.
    """
    try:
        from llm_dojo_scoring.prompts import get_prompt_version
    except ImportError as exc:
        raise PromptSelectionError(
            "the vendored llm-dojo-scoring has no prompt-version lineage API "
            "(llm_dojo_scoring.prompts.get_prompt_version); re-vendor the dojo "
            f"release that ships it before selecting eval-environment prompt versions ({exc})"
        ) from exc
    try:
        return get_prompt_version(key)
    except KeyError as exc:
        detail = exc.args[0] if exc.args else key
        raise PromptSelectionError(f"unknown eval-environment prompt version {key!r}: {detail}") from exc


# ── parsing ──────────────────────────────────────────────────────────────────
def role_from_key(key: str) -> str:
    """Role a bare key names (``correspondence_specialist_v3`` -> ``correspondence_specialist``).

    Lexical only (so spec hashing needs no dojo); :func:`resolve_prompt` checks it
    against the dojo's own ``role``.
    """
    match = _KEY_RE.match(str(key).strip())
    if not match:
        raise PromptSelectionError(
            f"cannot infer a role from prompt version {key!r} (expected <role>_v<N>); "
            "write it as role=key"
        )
    return match.group("role")


def parse_selection(items: Iterable[str] | Mapping[str, str] | None) -> dict[str, str]:
    """``["role=key", "bare_key_v3", ...]`` (or a mapping) -> ``{role: key}``.

    Two different keys for one role are an error; an identical repeat is idempotent.
    """
    if not items:
        return {}
    pairs: list[tuple[str, str]] = []
    if isinstance(items, Mapping):
        pairs = [(str(r).strip(), str(k).strip()) for r, k in items.items()]
    else:
        for raw in items:
            text = str(raw).strip()
            if not text:
                raise PromptSelectionError("empty --prompt-version value")
            if "=" in text:
                role, _, key = text.partition("=")
                pairs.append((role.strip(), key.strip()))
            else:
                pairs.append((role_from_key(text), text))
    out: dict[str, str] = {}
    for role, key in pairs:
        if not role or not key:
            raise PromptSelectionError(f"malformed prompt version {role}={key!r} (want role=key)")
        if role in out and out[role] != key:
            raise PromptSelectionError(
                f"role {role!r} selected twice with different versions ({out[role]!r} and {key!r})"
            )
        out[role] = key
    return dict(sorted(out.items()))


def pipeline_roles() -> set[str]:
    """Roles the sandbox pipeline actually has (static roster + vendored templates)."""
    from mailroom_sandbox.prompt_registry import agent_prompt_names

    return set(agent_prompt_names())


def validate_roles(selection: Mapping[str, str]) -> None:
    roles = pipeline_roles()
    for role in selection:
        if role not in roles:
            raise PromptSelectionError(
                f"role {role!r} is not a pipeline agent; have {sorted(roles)}"
            )


# ── resolution ───────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ResolvedPrompt:
    role: str
    key: str
    text: str
    sha256: str
    lineage: str | None = None
    chars: int | None = None

    def lock_entry(self) -> dict[str, Any]:
        """Per-agent run-lock block (shape of ``prompt_registry.resolve_prompt``)."""
        from mailroom_sandbox.prompt_registry import managed_name_for

        return {
            "agent": self.role,
            "source": SOURCE,
            "name": managed_name_for(self.role),
            "version": None,
            "label": None,
            "file": None,
            "key": self.key,
            "lineage": self.lineage,
            "chars": self.chars if self.chars is not None else len(self.text),
            "sha256": self.sha256,
            "text": self.text,
        }


def resolve_prompt(role: str, key: str | None = None) -> tuple[str, str, str]:
    """``(key, text, sha256)`` of ``role``'s prompt.

    ``key=None`` is the sandbox default (the catalog ``*_simplified`` stem, i.e.
    exactly what a run gets today); roles without a default stem raise. An
    explicit key is read from the dojo only and must belong to ``role``.
    """
    resolved = _resolve(role, key)
    return resolved.key, resolved.text, resolved.sha256


def _resolve(role: str, key: str | None) -> ResolvedPrompt:
    if key is None:
        from mailroom_sandbox import eval_environment_lineage as lineage
        from mailroom_sandbox.prompts import load_variant

        stem = lineage.default_prompt_variant(role)
        if not stem:
            raise PromptSelectionError(f"role {role!r} has no sandbox default prompt stem; name a version")
        text = load_variant(stem)
        row = lineage.lookup(agent=role) or {}
        return ResolvedPrompt(
            role=role,
            key=str(row.get("eval_environment_key") or stem),
            text=text,
            sha256=_sha(text),
            lineage="default-stem",
            chars=len(text),
        )
    pv = lookup_prompt_version(key)
    got_key = str(getattr(pv, "key", key))
    if got_key != key:
        raise PromptSelectionError(f"dojo returned prompt version {got_key!r} for {key!r}")
    pv_role = str(getattr(pv, "role", ""))
    if pv_role != role:
        raise PromptSelectionError(
            f"prompt version {key!r} belongs to role {pv_role!r}, not {role!r}"
        )
    text = getattr(pv, "text", None)
    if not isinstance(text, str) or not text:
        raise PromptSelectionError(f"prompt version {key!r} has no text")
    sha = _sha(text)
    claimed = str(getattr(pv, "sha256", "") or "")
    if claimed and claimed != sha:
        raise PromptSelectionError(
            f"prompt version {key!r}: text sha256 {sha[:12]} != dojo sha256 {claimed[:12]} "
            "(refusing to run text that is not the frozen version)"
        )
    return ResolvedPrompt(
        role=role,
        key=key,
        text=text,
        sha256=sha,
        lineage=getattr(pv, "lineage", None),
        chars=getattr(pv, "chars", None),
    )


@dataclass(frozen=True)
class Selection:
    """Resolved per-role prompt versions for one run."""

    prompts: Mapping[str, ResolvedPrompt] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return bool(self.prompts)

    @property
    def keys(self) -> dict[str, str]:
        return {role: p.key for role, p in sorted(self.prompts.items())}

    def versions_stamp(self) -> dict[str, dict[str, str]]:
        return {role: {"key": p.key, "sha256": p.sha256} for role, p in sorted(self.prompts.items())}

    def label_for(self, task: str | None) -> tuple[str, str] | None:
        """``(prompt_version, prompt_sha256)`` a record of ``task`` is logged under.

        A task naming a selected role logs that role's key + sha. Any other task
        (pipeline / chained / extract ...) logs the selection as a whole: the lone
        key, or ``key+key`` with a digest over every role/key/sha. A task naming a
        role that was NOT selected is untouched (``None``).
        """
        if not self.prompts:
            return None
        if task in self.prompts:
            p = self.prompts[str(task)]
            return p.key, p.sha256
        from mailroom_sandbox.eval_environment_lineage import catalog_agents

        single_role_task = bool(task) and (task in pipeline_roles_static() or task in catalog_agents())
        if single_role_task:
            return None
        if len(self.prompts) == 1:
            p = next(iter(self.prompts.values()))
            return p.key, p.sha256
        label = "+".join(p.key for _, p in sorted(self.prompts.items()))
        digest = _sha("\n".join(f"{r}:{p.key}:{p.sha256}" for r, p in sorted(self.prompts.items())))
        return label, digest

    def stamp(self, record: dict[str, Any]) -> dict[str, Any]:
        """Stamp the selected identity on a record / scorecard row (in place)."""
        task = str(record.get("task") or "")
        got = self.label_for(task)
        if got is None:
            return record
        label, sha = got
        record["prompt_version"] = label
        record["prompt_sha256"] = sha
        record["prompt_source"] = SOURCE
        record["prompt_versions"] = self.versions_stamp()
        if task in self.prompts:
            record["eval_environment_prompt_key"] = label
        return record

    def lock_agents(self) -> dict[str, dict[str, Any]]:
        return {role: p.lock_entry() for role, p in sorted(self.prompts.items())}


def pipeline_roles_static() -> set[str]:
    from mailroom_sandbox.prompt_registry import STATIC_AGENTS

    return set(STATIC_AGENTS)


EMPTY = Selection()


def resolve_selection(spec: Iterable[str] | Mapping[str, str] | None) -> Selection:
    """Parse + validate + resolve a selection; every failure is a :class:`PromptSelectionError`."""
    mapping = parse_selection(spec)
    if not mapping:
        return EMPTY
    validate_roles(mapping)
    return Selection({role: _resolve(role, key) for role, key in mapping.items()})


def selection_from_lock(prompt_lock: Mapping[str, Any] | None) -> Selection:
    """Rebuild the selection a run lock recorded (no dojo access needed)."""
    prompts: dict[str, ResolvedPrompt] = {}
    for role, ref in ((prompt_lock or {}).get("agents") or {}).items():
        if isinstance(ref, Mapping) and ref.get("source") == SOURCE:
            prompts[str(role)] = ResolvedPrompt(
                role=str(role),
                key=str(ref["key"]),
                text=str(ref.get("text") or ""),
                sha256=str(ref.get("sha256") or ""),
                lineage=ref.get("lineage"),
                chars=ref.get("chars"),
            )
    return Selection(prompts)


def check_no_stem_conflict(selection: Mapping[str, str], stem: str | None) -> None:
    """``--prompt <stem>`` and ``--prompt-version`` must not both set one role."""
    if not stem or not selection:
        return
    from mailroom_sandbox.eval_environment_lineage import agents_for_variant

    clash = sorted(set(agents_for_variant(stem)) & set(selection))
    if clash:
        raise PromptSelectionError(
            f"--prompt {stem!r} and --prompt-version both set the prompt for {clash}; use one"
        )


def merge_into_spec_prompt(prompt: dict[str, Any], cli_items: Sequence[str] | None) -> dict[str, Any]:
    """Return a copy of a run spec's ``prompt`` section with CLI selections merged (CLI wins per role)."""
    merged = dict(prompt or {})
    base = parse_selection(merged.get("versions"))
    base.update(parse_selection(cli_items))
    if base:
        merged["versions"] = dict(sorted(base.items()))
    check_spec_prompt(merged)
    return merged


def check_spec_prompt(prompt: Mapping[str, Any]) -> dict[str, str]:
    """Format-level validation of ``prompt.versions`` (no dojo); returns the normalized map."""
    versions = parse_selection(prompt.get("versions"))
    agents = prompt.get("agents") if isinstance(prompt.get("agents"), Mapping) else {}
    clash = sorted(set(versions) & set(agents))
    if clash:
        raise PromptSelectionError(
            f"prompt.versions and prompt.agents both set the prompt for {clash}; use one"
        )
    return versions


# ── process-wide active selection (CLI eval path and the job runner) ─────────
_ACTIVE: Selection = EMPTY


def set_active_selection(selection: Selection | None) -> None:
    global _ACTIVE
    _ACTIVE = selection or EMPTY


def active_selection() -> Selection:
    return _ACTIVE


def clear_active_selection() -> None:
    set_active_selection(None)


def apply_selection(selection: Selection | None = None) -> list[str]:
    """Patch the live pipeline with the selected texts. Loud when a role cannot be patched."""
    sel = selection if selection is not None else _ACTIVE
    if not sel:
        return []
    from mailroom_sandbox.prompt_registry import apply_runtime_overrides

    texts = {role: p.text for role, p in sel.prompts.items()}
    patched = apply_runtime_overrides(texts)
    missing = sorted(set(texts) - set(patched))
    if missing:
        raise PromptSelectionError(
            f"prompt versions {', '.join(sel.prompts[r].key for r in missing)} could not be applied "
            f"to {missing} (pipeline not importable) -- the run would execute default prompts"
        )
    return patched
