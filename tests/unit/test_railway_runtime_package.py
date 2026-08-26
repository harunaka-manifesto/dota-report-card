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
    assert EXPECTED_PACKAGE_SHA256 == "8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0"
    assert EXPECTED_AUTHORIZATION_SHA256 == "9ddde890c25a47fcabf7a5e51f22ba3a3007f79dd5e5f9c52845a2bfe4e69b2a"
