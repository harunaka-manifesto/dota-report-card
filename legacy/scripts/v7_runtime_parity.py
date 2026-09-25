#!/usr/bin/env python3
"""Verify frozen research-to-runtime parity on one safe DISCOVERY sample."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "legacy" / "services" / "api"))
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))

from app.providers.base import (  # noqa: E402
    CanonicalProfile,
    HistoryWindow,
    ProviderProvenance,
    V7CanonicalHistory,
    V7CanonicalMatch,
)
from report_card.player_analysis_v7.context_projection import load_context_projection  # noqa: E402
from report_card.player_analysis_v7.population import load_population_parameters  # noqa: E402
from report_card.player_analysis_v7.research import inference  # noqa: E402
from report_card.player_analysis_v7.research.features import PlayerFrame, extract  # noqa: E402
from report_card.player_analysis_v7.research.pass2_observations import (  # noqa: E402
    OBSERVATION_REGISTRY,
    chronological,
)
from report_card.player_analysis_v7.research.pass2_tables import (  # noqa: E402
    is_pass2_product_context,
)
from report_card.player_analysis_v7.research.registry import FAMILY_BY_NAME  # noqa: E402
from report_card.player_analysis_v7.runtime import (  # noqa: E402
    _archetype,
    _estimate,
    _finding_rows,
    _recommendation,
    analyze_v7,
    parsed_rows,
)


def read(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("split") != "DISCOVERY":
        raise SystemExit(f"{path}: parity may read DISCOVERY only")
    return document


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_history(document: dict[str, Any], deep_match_ids: set[int]) -> V7CanonicalHistory:
    matches = tuple(
        V7CanonicalMatch(
            provider="stratz",
            provider_schema_version="stored-discovery-parity",
            match_id=row["match_id"],
            hero_id=row.get("hero_id"),
            started_at=row.get("started_at"),
            duration_seconds=row.get("duration_seconds"),
            side=(
                "radiant"
                if row.get("is_radiant") is True
                else "dire"
                if row.get("is_radiant") is False
                else None
            ),
            won=row.get("is_victory"),
            kills=row.get("kills"),
            deaths=row.get("deaths"),
            assists=row.get("assists"),
            game_version_id=row.get("game_version_id"),
            position=row.get("position_native"),
            role=row.get("role_native"),
            lane=row.get("lane_native"),
            game_mode_native=row.get("game_mode_native"),
            lobby_native=row.get("lobby_type_native"),
            leaver_status_native=row.get("leaver_status_native"),
            is_parsed=row["match_id"] in deep_match_ids,
        )
        for row in document["rows"]
    )
    window = document["window"]
    return V7CanonicalHistory(
        profile=CanonicalProfile("stratz", "stored-discovery-parity", 1, "Player", None, False, True),
        window=HistoryWindow(**window),
        matches=matches,
        provenance=ProviderProvenance(
            "stratz", "stored-discovery-parity", "stored", "1", "0" * 64,
            "stored", 0, 0, "2026-09-08T00:00:00Z", "0" * 64, "complete",
            len(deep_match_ids) / len(matches),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history-document", type=Path, required=True)
    parser.add_argument("--pass2-document", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    forbidden = ("CANDIDATE_TEST", "CALIBRATION_RESERVED", "SEALED_VALIDATION")
    if any(token.lower() in str(path).lower() for token in forbidden for path in (args.history_document, args.pass2_document)):
        raise SystemExit("protected split path refused")

    history_document = read(args.history_document)
    pass2_document = read(args.pass2_document)
    if history_document.get("account_pseudonym") != pass2_document.get("account_pseudonym"):
        raise SystemExit("sample documents do not belong to the same pseudonymous account")
    history = history_document["rows"]
    deep = chronological(
        [row for row in pass2_document["rows"] if is_pass2_product_context(row)]
    )
    frame = PlayerFrame("runtime_player", "DISCOVERY", "complete", history, parsed_rows(deep))
    artifact = load_context_projection()
    rows: dict[str, Any] = {}
    for key in sorted(artifact.dimensions):
        source = OBSERVATION_REGISTRY.get(key) or FAMILY_BY_NAME[key]
        opportunities = source.fn(deep) if key in OBSERVATION_REGISTRY else extract(key, frame)
        projection = artifact.finding(key)
        residuals = []
        for opportunity in opportunities:
            context = dict(opportunity.ctx)
            effect = projection.intercept
            for factor in projection.factors:
                level = opportunity.arm if factor.name == "__arm__" else context[factor.name]
                effect += factor.coefficient_for(level)
            residuals.append(opportunity.value - effect)
        armed = source.treated is not None and source.control is not None
        arm_codes = [
            1 if opportunity.arm == source.treated else 0
            for opportunity in opportunities
        ]
        expected = inference.player_inference(
            "runtime_player",
            residuals,
            arm_codes if armed else None,
            1 if armed else None,
            0 if armed else None,
        )
        actual = _estimate(
            key,
            opportunities,
            treated=source.treated,
            control=source.control,
        )
        if expected is None or actual is None:
            raise SystemExit(f"{key}: safe sample does not support parity")
        delta_error = abs(expected.delta - actual.delta)
        se_error = abs(expected.standard_error - actual.standard_error)
        if delta_error > 1e-12 or se_error > 1e-12:
            raise SystemExit(f"{key}: runtime parity failed")
        rows[key] = {
            "opportunities": len(opportunities),
            "delta_absolute_error": delta_error,
            "se_absolute_error": se_error,
        }

    population = load_population_parameters()
    findings, estimates = _finding_rows(frame, deep, population)
    private_recommendation = _recommendation(deep, population)
    assigned, mode = _archetype(deep, sorted(history, key=lambda row: row["started_at"]), population)
    payload = analyze_v7(
        history=canonical_history(history_document, {row["match_id"] for row in deep}),
        deep_rows=deep,
        hero_metadata={},
        generated_at="2026-09-08T00:00:00Z",
    )
    public_json = payload.public_projection.model_dump_json()
    if payload.recommendation and payload.recommendation.recommendation_text in public_json:
        raise SystemExit("private Recommendation leaked into public projection")
    document = {
        "schema_version": "v7-new-lineage-runtime-parity-1.0.0",
        "split": "DISCOVERY",
        "identities_included": False,
        "sample": {
            "history_document_sha256": digest(args.history_document),
            "pass2_document_sha256": digest(args.pass2_document),
            "history_rows": len(history),
            "pass2_product_rows": len(deep),
        },
        "projection": {
            "artifact_version": artifact.artifact_version,
            "artifact_sha256": artifact.artifact_sha256,
            "dimensions_verified": len(rows),
            "tolerance": 1e-12,
            "all_pass": all(
                math.isclose(row["delta_absolute_error"], 0.0, abs_tol=1e-12)
                and math.isclose(row["se_absolute_error"], 0.0, abs_tol=1e-12)
                for row in rows.values()
            ),
            "dimensions": rows,
        },
        "runtime": {
            "estimable_findings": len(estimates),
            "selected_findings": len(findings),
            "recommendation": "AVAILABLE" if private_recommendation else "REFUSED",
            "archetype": "AVAILABLE" if assigned else "REFUSED",
            "dominant_mode": mode,
            "capability_payload_valid": True,
            "private_recommendation_absent_from_public_projection": True,
        },
        "provider_calls": {"stratz": 0, "opendota": 0},
        "protected_splits": {token: "NOT_READ" for token in forbidden},
    }
    serialized = json.dumps(document, indent=2, sort_keys=True)
    if history_document["account_pseudonym"] in serialized:
        raise SystemExit("sample pseudonym leaked into parity evidence")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(serialized + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
