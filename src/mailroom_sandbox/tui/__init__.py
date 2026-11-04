"""Mailroom TUI design system, vendored from LLM-Mailroom-Services/mailroom-ml.

`pretty_log.py` is a VERBATIM copy of mailroom-ml `training/pretty_log.py` at
commit f85f79ed9f2c0a7f1e17e755ee1a8094cf5a7197 (sha256 ac1b7aa34ae5e67723024f148fe2f0df76e34eb8ea959d3cd7ecbeeb757ce41c).
Do not edit it here — refresh it from mailroom-ml and update the pin
(guarded by tests/test_watch.py::test_vendored_pretty_log_is_pinned).
`mailroom_sandbox.watch` builds the eval-run panels on its primitives.
``mailroom_sandbox.tui.session`` is the tail-friendly CLI integration layer
(SAND-033) for ``sandbox run|eval|matrix`` and deploy entrypoints.
``mailroom_sandbox.tui.web`` serves the same SAND-032 watch panels in a
localhost browser via ``sandbox watch --web``.
"""

PRETTY_LOG_UPSTREAM = "LLM-Mailroom-Services/mailroom-ml@088530b58a5f17e198e05dc17785bbaea63af50b:training/pretty_log.py"
PRETTY_LOG_SHA256 = "ac1b7aa34ae5e67723024f148fe2f0df76e34eb8ea959d3cd7ecbeeb757ce41c"
