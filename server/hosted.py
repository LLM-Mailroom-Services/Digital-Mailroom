"""Public hosted edition entry point (Mailroom Observatory).

Binds on 0.0.0.0 so a container, Hugging Face Space, or any ASGI host can
serve the modern /live UI. The pixel-art console stays on `mailroom-web`.
"""

from __future__ import annotations

import os


def run() -> None:
    os.environ.setdefault("MAILROOM_EDITION", "hosted")
    os.environ.setdefault("MAILROOM_HOST", "0.0.0.0")
    from server.main import run as run_server

    run_server()


if __name__ == "__main__":
    run()
