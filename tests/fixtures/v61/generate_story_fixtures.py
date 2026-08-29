"""Generate the checked-in V6.1 frontend fixtures from the canonical builder.

The browser fixture server consumes the serialized payloads under
``apps/web/tests/fixtures/persisted-reports``.  This generator intentionally
uses the same normalized-row boundary and ``build_story_payload`` used by the
API so fixture state, manifests, and finding-slot combinations cannot drift
from the public contract.

Run from the repository root with::

    PYTHONPATH=services/api uv run python tests/fixtures/v61/generate_story_fixtures.py
"""

from __future__ import annotations

import copy
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services" / "api"))
sys.path.insert(0, str(ROOT / "tests" / "unit"))

from app.api.report_schemas import validate_free_dna_report  # noqa: E402
from app.api.story_payload_schemas_v61 import StoryPayloadV61Schema  # noqa: E402
from app.ingestion.summary_normalize import normalize_summary_rows  # noqa: E402
from app.player_analysis_v61.story_projection import build_story_payload  # noqa: E402
from app.player_analysis_v61.story_selector import select_story_matches  # noqa: E402
from test_free_dna_v61_contract import _generate  # noqa: E402

OUTPUT_DIR = ROOT / "apps" / "web" / "tests" / "fixtures" / "persisted-reports"
TAXONOMY_CHECKSUMS = {
    "factual_checksum": "56b0c0fb2f9f1e75d3649b655780197d12a845edb26ccb0d2645370b42e2cb89",
    "editorial_checksum": "394190d3a4c8b067b9eda04975d8d7c1b19092a9f1c9a39d46266bfec5533e0d",
}


def timestamp(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=UTC).timestamp())


def story_rows(
    outcomes: tuple[bool, ...] = (True, True, True, False, False, True),
) -> list[dict[str, object]]:
    """Return a deterministic synthetic summary corpus for public fixtures.

    April is intentionally empty while the other eleven months have six
    dated matches.  This exercises an empty Hero Era without weakening the
    builder's selection or evidence gates.

    ``outcomes`` is the repeating win/loss pattern.  The default gives a
    two-match losing streak; a loss-heavy pattern produces a long streak and a
    negative Rank Points direction, neither of which the default reaches.
    """

    rows: list[dict[str, object]] = []
    heroes = (1, 2, 3, 4, 5, 6)
    for month in range(1, 13):
        if month == 4:
            continue
        for slot in range(6):
            index = len(rows) + 1
            day = 2 if month == 1 else slot + 1
            mode, lobby = (22, 7) if index % 3 == 0 else (1, 0)
            rows.append(
                {
                    "match_id": 980_000_000 + index,
                    "start_time": timestamp(
                        f"2025-{month:02d}-{day:02d}T12:00:00+00:00"
                    ),
                    "duration": 3_900 if index == 7 else 1_800 + index % 7 * 120,
                    "hero_id": heroes[slot],
                    "player_slot": 0,
                    "won": outcomes[(index - 1) % len(outcomes)],
                    "game_mode": mode,
                    "lobby_type": lobby,
                    "leaver_status": 0,
                    "kills": 2 + index % 13,
                    "deaths": 1 + index % 7,
                    "assists": 4 + index % 15,
                    "lane_role": 1,
                    "version": 1,
                }
            )
    return rows


def finding(family: str, published: bool) -> dict[str, object]:
    if not published:
        return {"family": family, "published": False}
    claim = f"Observed {family.replace('_', ' ')} evidence in this fixture."
    return {
        "family": family,
        "published": True,
        "claim": claim,
        "interpretation": "This bounded fixture relationship remains descriptive.",
        "evidence_refs": [f"fixture:{family}"],
        "confidence": "high",
        "semantic_outcome_key": (
            "clean_transfer" if family == "transfer" else "one_loss_runback"
        ),
        "claim_contract": {
            "claim": claim,
            "evidence": "Two public summary signals support the bounded observation.",
            "interpretation": "This describes an association without assigning a cause.",
            "recommendation": None,
            "alternatives": ["Unobserved match context"],
            "verification": {
                "eligibility_games": 5,
                "primary_metric": "win_rate",
                "guardrail_metric": "sample_size",
                "causal": False,
                "abstention": "too early to tell",
            },
            "interaction": "open_deep",
            "copy_version": "free-dna-semantic-copy-6.1.0",
            "deep_handoff": {
                "cohort_reference": f"cohort:v61:fixture-{family}",
                "unanswered_alternatives": ["Unobserved match context"],
            },
        },
    }


def build_payload(
    rows: list[dict[str, object]],
    *,
    post_loss: bool,
    transfer: bool,
    hero_metadata: dict[int, dict[str, str]] | None,
    completeness: str,
    display_name: str | None,
) -> dict[str, Any]:
    normalized = normalize_summary_rows(rows, 999_999)
    selection = select_story_matches(normalized.matches)
    payload = build_story_payload(
        selection=selection,
        legacy_report={
            "findings": [
                finding("post_loss_response", post_loss),
                finding("transfer", transfer),
            ]
        },
        profile={"personaname": display_name, "account_id": 999_999}
        if display_name
        else None,
        canonical_audit={"completeness": completeness},
        window_start=timestamp("2025-01-01T00:00:00+00:00"),
        window_end=timestamp("2025-12-31T23:59:59+00:00"),
        hero_metadata=hero_metadata,
        hero_taxonomy_checksums=TAXONOMY_CHECKSUMS,
        internal_evidence={"post_loss": {"comparable_pair_count": 7}},
    )
    if payload is None:
        raise RuntimeError("fixture rows did not clear the story activation gate")
    validated = StoryPayloadV61Schema.model_validate(payload)
    return validated.model_dump(mode="json", by_alias=True)


def hero_metadata() -> dict[int, dict[str, str]]:
    return {
        1: {"display_name": "Hero Alpha"},
        2: {"display_name": "Hero Beta"},
        3: {"display_name": "Hero Gamma"},
        4: {"display_name": "Hero Delta"},
        5: {"display_name": "Hero Epsilon"},
        6: {"display_name": "Hero Zeta"},
    }


def scrub_historical(value: Any) -> Any:
    """Remove private identifiers while preserving public nesting and nulls."""

    forbidden = {
        "account_id",
        "player_id",
        "steam_id",
        "steamid",
        "steam_id64",
        "match_id",
        "match_ids",
        "session_id",
        "session_ids",
        "protected_cohort_reference",
        "raw_cohort_reference",
    }
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key in forbidden:
                continue
            if key == "cohort_reference":
                result[key] = "fixture-historical-cohort"
            else:
                result[key] = scrub_historical(item)
        return result
    if isinstance(value, list):
        return [scrub_historical(item) for item in value]
    return value


def historical_report() -> dict[str, Any]:
    """Derive the historical shape from the production report generator.

    NOTE: the upstream generator bootstraps without a fixed seed, so interval
    bounds and stability values differ between runs.  The checked-in
    ``v61-historical-production.json`` is therefore a pinned sample, not a
    reproducible artifact: regenerate it deliberately, not as a side effect.

    The story extension and its version keys are removed to model an older
    persisted report.  Missing ``story_band`` values are preserved as missing,
    while the remaining legacy nesting and explicit nulls stay intact.
    """

    report, _source = _generate()
    # Validate the unsanitized source against the production contract before
    # redaction.  The historical fixture intentionally replaces opaque
    # references with a non-production marker, so it is not revalidated as a
    # current report after that privacy-preserving transformation.
    validate_free_dna_report(report)
    historical = scrub_historical(copy.deepcopy(report))
    historical.pop("story_payload", None)
    historical["report_id"] = "v61-historical-production-fixture"
    historical["identity"]["display_name"] = "Historical fixture player"
    for key in (
        "story_payload",
        "story_rules",
        "story_copy",
        "game_mode_map",
        "hero_taxonomy",
        "hero_metadata",
        "archetype_contract",
    ):
        historical["versions"].pop(key, None)
    for hero in historical.get("hero_portfolio", {}).get("heroes", []):
        if isinstance(hero, dict):
            hero.pop("story_band", None)
    historical["metadata"].update(
        {
            "created_at": "2026-01-15T00:00:00+00:00",
            "expires_at": None,
            "data_from": "2025-01-15T00:00:00+00:00",
            "data_to": "2026-01-14T00:00:00+00:00",
            "raw_history_hash": "fixture-historical-history",
        }
    )
    historical["reproducibility"].update(
        {
            "generated_at": "2026-01-15T00:00:00+00:00",
            "input_snapshot_hash": "fixture-historical-history",
            "window_start": "2025-01-15T00:00:00+00:00",
            "window_end": "2026-01-14T00:00:00+00:00",
        }
    )
    return historical


def write_json(filename: str, value: Any) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / filename).write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    rows = story_rows()
    metadata = hero_metadata()
    combinations = {
        "v61-story-payload-none.json": (False, False),
        "v61-story-payload-post-loss.json": (True, False),
        "v61-story-payload-transfer.json": (False, True),
        "v61-story-payload-both.json": (True, True),
    }
    for filename, (post_loss, transfer) in combinations.items():
        write_json(
            filename,
            build_payload(
                rows,
                post_loss=post_loss,
                transfer=transfer,
                hero_metadata=metadata,
                completeness="complete",
                display_name="Story fixture player",
            ),
        )
    write_json(
        "v61-story-payload-long-streak.json",
        build_payload(
            # Four consecutive losses inside each month, so the losing streak
            # clears the frozen three-match microcopy minimum, and ranked
            # losses outnumber ranked wins.
            story_rows(outcomes=(True, False, False, False, False, True)),
            post_loss=True,
            transfer=False,
            hero_metadata=metadata,
            completeness="complete",
            display_name="Long streak fixture player",
        ),
    )
    write_json(
        "v61-story-payload-degraded.json",
        build_payload(
            rows[:30],
            post_loss=False,
            transfer=False,
            hero_metadata={},
            completeness="possibly_truncated",
            display_name=None,
        ),
    )
    write_json("v61-historical-production.json", historical_report())
    print(f"wrote {len(combinations) + 3} fixtures to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
