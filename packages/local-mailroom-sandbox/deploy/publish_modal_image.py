"""Build the vLLM serving image and publish it by name (`sandbox modal publish-image`).

Named images belong to one Modal workspace, so run this once per account. The
name carries the vLLM tag, which is what a run's lock records. The job image is
not published: it bundles this checkout, so a stale copy would run old code.
"""

from __future__ import annotations

import sys
from pathlib import Path

import modal

sys.path.insert(0, str(Path(__file__).resolve().parent))

from modal_vllm import NAMED_IMAGE, serving_image  # noqa: E402


def main() -> None:
    app = modal.App.lookup("sandbox-image-builds", create_if_missing=True)
    with modal.enable_output():
        serving_image.build(app).publish(NAMED_IMAGE)
    print(f"published {NAMED_IMAGE}")


if __name__ == "__main__":
    main()
