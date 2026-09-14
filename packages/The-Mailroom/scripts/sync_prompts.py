#!/usr/bin/env python3
"""Push the vendored agent prompts into Langfuse Prompt Management.

Port of llm-mailroom's ``scripts/sync_prompts.py`` with the same contract:
one text prompt per agent named ``mailroom-<agent_name>``, labeled
``production``. Creating a prompt with an existing name adds a new version and
moves the ``production`` label to it, so repeated syncs are only performed when
the local template actually changed — the prompt list stays clean and version
history stays meaningful.

Templates come from ``mailroom_ui/prompt_registry.PROMPT_TEMPLATES`` (the
vendored mirror) unless MAILROOM_PROMPTS points at a JSON override.

Usage:
    python scripts/sync_prompts.py              # sync all prompts
    python scripts/sync_prompts.py --dry-run    # show what would change
    python scripts/sync_prompts.py --force      # always create a new version
    python scripts/sync_prompts.py --agent sorter
    python scripts/sync_prompts.py --docclass   # sync the entity-repo docclass
                                                # family instead (name = the
                                                # version key verbatim, from
                                                # llm-entity-extraction
                                                # src/prompts_docclass.py)
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

# V-27: explicit path — find_dotenv() silently missed .env in some invocation
# contexts (frame-walking quirk), leaving creds unset.
load_dotenv(__import__("pathlib").Path(__file__).resolve().parent.parent / ".env")


def _client():
    from langfuse import Langfuse

    missing = [k for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY") if not os.environ.get(k)]
    if missing:
        sys.exit(f"missing env vars: {', '.join(missing)} (copy .env.example -> .env and fill in)")
    client = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com"),
    )
    try:
        client.auth_check()
    except Exception as exc:
        sys.exit(f"Langfuse rejected the configured credentials ({str(exc)[:120]}).")
    return client


def _current_production(client, name: str) -> str | None:
    try:
        prompt = client.get_prompt(name, label="production")
        return prompt.prompt
    except Exception:
        return None


def sync_one(client, agent_name: str, template: str, *, force: bool, dry_run: bool, docclass: bool = False) -> str:
    if docclass:
        # Entity-repo contract: prompt name = the version key verbatim.
        name = agent_name
    else:
        from mailroom_ui.prompt_registry import prompt_name

        name = prompt_name(agent_name)
    current = None if force else _current_production(client, name)
    if current == template:
        return f"unchanged  {name}"
    action = "force" if force else ("create" if current is None else "update")
    if dry_run:
        return f"{action:9s} {name}"
    client.create_prompt(name=name, type="text", prompt=template, labels=["production"])
    return f"{action:9s} {name}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync agent prompts to Langfuse prompt management.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without creating anything.")
    parser.add_argument("--force", action="store_true", help="Always create a new prompt version.")
    parser.add_argument("--agent", help="Only sync one agent (e.g. sorter).")
    parser.add_argument("--docclass", action="store_true",
                        help="Sync the llm-entity-extraction docclass family "
                             "(mailroom_ui/docclass_prompts.py) instead of the "
                             "agent roster; prompt name = version key verbatim.")
    args = parser.parse_args()

    if args.docclass:
        from mailroom_ui.docclass_prompts import load_docclass_templates

        templates = load_docclass_templates()
    else:
        from mailroom_ui.prompt_registry import load_prompt_templates

        templates = load_prompt_templates()
    if args.agent:
        if args.agent not in templates:
            print(f"Unknown agent '{args.agent}'. Available: {', '.join(sorted(templates))}")
            return 1
        templates = {args.agent: templates[args.agent]}

    client = _client()

    print(f"{'status':<10} prompt")
    print("-" * 60)
    statuses = []
    for agent_name, template in sorted(templates.items()):
        status = sync_one(client, agent_name, template, force=args.force, dry_run=args.dry_run,
                          docclass=args.docclass)
        statuses.append(status)
        print(status)

    changed = sum(1 for s in statuses if not s.startswith("unchanged"))
    if not args.dry_run:
        client.flush()
    print(f"\n{len(templates)} prompts checked, {changed} {'would change' if args.dry_run else 'synced'}.")
    host = os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com").rstrip("/")
    prefix = "version keys" if args.docclass else "name prefix: mailroom-"
    print(f"Prompts live at {host} ({prefix}, label: production).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
