"""Spec-driven job orchestrator for the sandbox (DMR-027).

A run is a locked, resumable, pollable job: prompt version(s) + HF dataset
subset + vLLM/Modal engine spec + OTEL trace sink, prepared and pinned at
preflight, executed against a local endpoint or a remote Modal function,
checkpointed per item, and compared across local / Modal / API runs.
"""

from __future__ import annotations
