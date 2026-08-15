from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "packages/api-client/src/openapi-meta.ts"


def main() -> None:
    sys.path.insert(0, str(ROOT / "services/api"))
    from app.main import create_app

    schema = create_app().openapi()
    paths = sorted(schema.get("paths", {}))
    content = (
        "// Generated from FastAPI /openapi.json. Do not edit manually.\n"
        f"export const apiPaths = {json.dumps(paths, indent=2)} as const;\n"
    )
    OUTPUT.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
