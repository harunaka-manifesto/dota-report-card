from __future__ import annotations

from pathlib import Path

from scripts.verify_v61_runtime_package import (
    EXPECTED_ANALYTICAL_SOURCE_SHA,
    EXPECTED_AUTHORIZATION_SHA256,
    EXPECTED_PACKAGE_SHA256,
    verify_package,
)

PACKAGE_DIR = Path(__file__).resolve().parents[2] / "infra/runtime-artifacts/free_dna_v61/6.1.0"


def test_railway_image_package_is_the_approved_v61_bundle() -> None:
    verify_package(PACKAGE_DIR)


def test_api_image_bakes_the_same_package_for_api_and_worker() -> None:
    dockerfile = (PACKAGE_DIR.parents[2] / "docker" / "api.Dockerfile").read_text(encoding="utf-8")
    assert "COPY infra/runtime-artifacts/free_dna_v61/6.1.0/ ./runtime-artifacts/free_dna_v61/6.1.0/" in dockerfile
    assert "RUN python scripts/verify_v61_runtime_package.py /app/runtime-artifacts/free_dna_v61/6.1.0" in dockerfile
    assert f"FREE_DNA_V61_ANALYTICAL_SOURCE_SHA={EXPECTED_ANALYTICAL_SOURCE_SHA}" in dockerfile
    assert EXPECTED_PACKAGE_SHA256 == "22206d20b84bf9ee73b93c64177443e1bb585ccdb818c188ac40d9acfcb358f9"
    assert EXPECTED_AUTHORIZATION_SHA256 == "3adb977f85c6896ef3228004bb4a60641ce51668688a9b57fa652136fd8ecfb9"


def test_api_image_is_non_root_and_keeps_artifacts_read_only() -> None:
    dockerfile = (PACKAGE_DIR.parents[2] / "docker" / "api.Dockerfile").read_text(encoding="utf-8")
    assert "RUN chmod -R a-w /app/runtime-artifacts/free_dna_v61/6.1.0" in dockerfile
    assert "RUN addgroup --system app && adduser --system --ingroup app --no-create-home app" in dockerfile
    assert "USER app" in dockerfile
