"""The-Mailroom — pixel-art visualization console for the llm-mailroom pipeline.

Langfuse is the sole source of truth: every display value is derived from
Langfuse traces, observations, scores, and sessions.
"""



def _read_version() -> str:
    """Installed dist version, else the checkout's pyproject.toml.

    This was a hard-coded "0.1.0" through three releases.
    """
    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            return version("the-mailroom")
        except PackageNotFoundError:
            pass
    except ImportError:  # pragma: no cover - py<3.8
        pass
    import re
    from pathlib import Path

    try:
        text = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text()
    except OSError:
        return "0+unknown"
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else "0+unknown"


__version__ = _read_version()
