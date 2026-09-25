"""Export the isolated mobile OpenAPI document (separate from legacy /v1).

    uv run python -m scripts.tracker_export_openapi

The checked-in copy is the Swift client's source; tests fail when it drifts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))

from app.core.config import Settings  # noqa: E402
from app.tracker.mobile_api import create_mobile_app  # noqa: E402

TARGET = ROOT / "docs/tracker/api/mobile-openapi-v1.json"


def main() -> None:
    schema = create_mobile_app(Settings()).openapi()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(TARGET.relative_to(ROOT))


if __name__ == "__main__":
    main()
