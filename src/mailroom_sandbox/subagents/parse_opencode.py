"""Parse OpenCode agent markdown (YAML frontmatter + body)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml


_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class OpencodeAgentDoc:
    frontmatter: dict[str, Any]
    body: str

    @property
    def description(self) -> str:
        desc = self.frontmatter.get("description")
        if desc is None:
            return ""
        return str(desc).strip()


def parse_opencode_markdown(text: str) -> OpencodeAgentDoc:
    match = _FRONTMATTER.match(text)
    if not match:
        return OpencodeAgentDoc(frontmatter={}, body=text.lstrip())
    meta = yaml.safe_load(match.group(1)) or {}
    body = text[match.end() :]
    return OpencodeAgentDoc(frontmatter=meta, body=body.lstrip("\n"))
