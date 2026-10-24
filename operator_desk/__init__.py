"""Operator desk — auth, archive, ops, and bin observer.

Not a document-display source. Display values stay Langfuse-only via
``mailroom_ui``. This package owns the operator-facing FastAPI routers
mounted at ``/v1/auth``, ``/v1/archive``, ``/v1/ops``, and ``/ws/pipeline``.
"""

from .mount import OPERATOR_ENDPOINTS, mount_operator, operator_status

__all__ = ["OPERATOR_ENDPOINTS", "mount_operator", "operator_status"]
