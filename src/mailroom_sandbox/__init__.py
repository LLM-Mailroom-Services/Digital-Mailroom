"""Local LLM mailroom sandbox.

Self-contained posture (DMR-057): the family code the sandbox imports at
runtime (``pipeline.*``/``graph.*``/``agents.*``/``llm.*``/``legalbench.*``
from llm-mailroom, ``llm_dojo_scoring.*`` from llm-dojo-scoring) ships as
tracked snapshots under ``vendor/``. This package's ``__init__`` puts those
trees on ``sys.path`` BEFORE anything else imports them, so a fresh checkout
works offline with no pip git pins and no ``sandbox fetch-deps`` step.

The Dojo is resolved installed-release-first: a ``llm-dojo-scoring`` release
installed in the environment (``requirements/dojo-release.txt``) that matches the
vendored pin is used, and the vendored snapshot is the fallback when it is
missing, off-pin or fails to import (``mailroom_sandbox.dojo_source``).
"""

from __future__ import annotations

import os
import sys

from mailroom_sandbox.paths import vendored_mailroom_src

_vendored = vendored_mailroom_src()
if _vendored is not None:
    _resolved = str(_vendored.resolve())
    if _resolved not in sys.path:
        sys.path.insert(0, _resolved)

from mailroom_sandbox import dojo_source as _dojo_source  # noqa: E402

_dojo_source.choose()


def prefer_own_venv_tools() -> None:
    """Run this venv's pinned CLIs even when the venv is not activated.

    ``.venv/bin/sandbox`` would otherwise shell out to whichever ``modal`` comes
    first on ``PATH``, which can be a global install on another SDK version.
    """
    if sys.prefix == sys.base_prefix:
        return
    own_bin = os.path.dirname(sys.executable)
    entries = (os.environ.get("PATH") or os.defpath).split(os.pathsep)
    if entries[0] != own_bin:
        os.environ["PATH"] = os.pathsep.join([own_bin, *(e for e in entries if e != own_bin)])


from mailroom_sandbox.runtime import activate

__version__ = "0.3.0"
__all__ = ["activate", "__version__"]
