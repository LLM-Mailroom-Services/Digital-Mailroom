"""``python -m operator_desk`` — migrate the operator store and print status."""

from __future__ import annotations

import logging

from .db import ensure_bins, migrate
from .mount import operator_status

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    ensure_bins()
    path = migrate()
    print(f"Migrations applied to {path}")
    print(operator_status())
