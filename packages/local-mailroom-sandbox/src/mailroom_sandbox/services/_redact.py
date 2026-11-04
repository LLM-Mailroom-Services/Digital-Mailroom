"""Keep credentials in endpoint URLs out of diagnostics and published snapshots."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

_URL = re.compile(r"https?://[^\s<>\"']+")


def redact_urls(text: str) -> str:
    """Remove userinfo, query values and fragments from URLs in diagnostic text."""
    def replace(match: re.Match[str]) -> str:
        try:
            value = match.group()
            parts = urlsplit(value)
            # A delimiter (``#``/``?``) can split a URL-shaped password before
            # its ``@host`` suffix, so ``netloc`` still holds a credential
            # fragment. Never format an ambiguous token: reject it outright.
            if "@" in value and "@" not in parts.netloc:
                return "[invalid endpoint]"
            return urlunsplit((parts.scheme, parts.netloc.rsplit("@", 1)[-1], parts.path,
                               "REDACTED" if parts.query else "", ""))
        except ValueError:
            return "[invalid endpoint]"

    return _URL.sub(replace, text)
