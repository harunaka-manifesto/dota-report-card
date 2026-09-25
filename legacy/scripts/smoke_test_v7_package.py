"""Build and install both distributions, then load V7's runtime assets."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def main() -> None:
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("uv is required for the isolated package smoke test")

    with tempfile.TemporaryDirectory(prefix="dota-v7-package-smoke-") as raw_tmp:
        tmp = Path(raw_tmp)
        dist = tmp / "dist"
        _run([uv, "build", "--wheel", "--sdist", "--out-dir", str(dist)])
        artifacts = (
            dist / "dota_report_card-0.1.0-py3-none-any.whl",
            dist / "dota_report_card-0.1.0.tar.gz",
        )
        smoke = """
from report_card.heroes.taxonomy import load_default_taxonomy
from report_card.player_analysis_v7.service import V7RuntimeService
from report_card.stratz.item_vocabulary import load_item_vocabulary

items = load_item_vocabulary()
taxonomy = load_default_taxonomy()
assert items
assert len(taxonomy.heroes) == 127

class Provider: ...
class Repository: ...

service = V7RuntimeService(Provider(), Repository())
assert len(service.hero_metadata) == len(taxonomy.heroes)
print(f"items={len(items)} heroes={len(taxonomy.heroes)} service=ok")
"""
        for artifact in artifacts:
            env_dir = tmp / artifact.stem
            venv = env_dir / "venv"
            _run([uv, "venv", "--python", "3.11", str(venv)], cwd=tmp)
            _run([uv, "pip", "install", "--python", str(venv / "bin/python"), str(artifact)])
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env["PYTHONNOUSERSITE"] = "1"
            _run([str(venv / "bin/python"), "-c", smoke], cwd=tmp, env=env)
            print(f"PASS {artifact.name}")


if __name__ == "__main__":
    main()
