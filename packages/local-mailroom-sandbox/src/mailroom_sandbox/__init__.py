"""Local LLM mailroom sandbox.

Self-contained posture (DMR-057): the family code the sandbox imports at
runtime (``pipeline.*``/``graph.*``/``agents.*``/``llm.*``/``legalbench.*``
from llm-mailroom, ``llm_dojo_scoring.*`` from llm-dojo-scoring) ships as
tracked snapshots under ``vendor/``. This package's ``__init__`` puts those
trees on ``sys.path`` BEFORE anything else imports them, so a fresh checkout
works offline with no pip git pins and no ``sandbox fetch-deps`` step.
"""

from __future__ import annotations

import sys

from mailroom_sandbox.paths import vendored_dojo_src, vendored_mailroom_src

for _vendored in (vendored_mailroom_src(), vendored_dojo_src()):
    if _vendored is not None:
        _resolved = str(_vendored.resolve())
        if _resolved not in sys.path:
            sys.path.insert(0, _resolved)

from mailroom_sandbox.runtime import activate

__version__ = "0.1.0"
__all__ = ["activate", "__version__"]
