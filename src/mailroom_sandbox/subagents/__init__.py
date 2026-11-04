"""Central subagent roster + harness adapters (Cursor, OpenCode)."""

from mailroom_sandbox.subagents.family import list_packages, resolve_package
from mailroom_sandbox.subagents.materialize import materialize_package
from mailroom_sandbox.subagents.propagate import propagate_family_checkouts
from mailroom_sandbox.subagents.roster import SubagentEntry, load_roster
from mailroom_sandbox.subagents.sync import sync_harness

__all__ = [
    "SubagentEntry",
    "list_packages",
    "load_roster",
    "materialize_package",
    "propagate_family_checkouts",
    "resolve_package",
    "sync_harness",
]
