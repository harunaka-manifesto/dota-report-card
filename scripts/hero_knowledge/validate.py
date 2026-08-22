"""Validation gates for source and product-facing snapshots."""

from __future__ import annotations

from typing import Any

from .errors import ValidationError

SEMANTIC_FUNCTIONS = frozenset(
    {
        "initiation",
        "counter_initiation",
        "catch",
        "frontline",
        "fight_control",
        "save",
        "sustain",
        "forced_movement",
        "repositioning",
        "mobility",
        "burst",
        "sustained_damage",
        "wave_clear",
        "push",
        "global_presence",
        "scaling",
        "vision",
    }
)
SEMANTIC_DEMANDS = frozenset(
    {"commitment", "access", "repositioning", "economy", "timing", "execution", "exposure", "micro"}
)
SEMANTIC_BANDS = frozenset({"low", "medium", "high", "unknown"})
SEMANTIC_POSITIONS = frozenset({"1", "2", "3", "4", "5"})


def validate_semantic_layer(snapshot: dict[str, Any]) -> tuple[str, ...]:
    """Validate the reviewed semantic facts before snapshot generation."""

    errors: list[str] = []
    for field in ("schema_version", "version", "review_status", "heroes"):
        if field not in snapshot:
            errors.append(f"semantic.missing:{field}")
    if snapshot.get("review_status") not in {"reviewed", "approved"}:
        errors.append("semantic.review_not_approved")
    vocabulary = snapshot.get("vocabulary")
    if not isinstance(vocabulary, dict):
        errors.append("semantic.vocabulary_missing")
    else:
        if _as_set(vocabulary.get("functional_jobs")) != SEMANTIC_FUNCTIONS:
            errors.append("semantic.vocabulary_functions_drift")
        if _as_set(vocabulary.get("demands")) != SEMANTIC_DEMANDS:
            errors.append("semantic.vocabulary_demands_drift")
        if _as_set(vocabulary.get("bands")) != SEMANTIC_BANDS:
            errors.append("semantic.vocabulary_bands_drift")
    heroes = snapshot.get("heroes", [])
    if not isinstance(heroes, list) or not heroes:
        return tuple((*errors, "semantic.heroes_missing"))
    ids: list[int] = []
    for row in heroes:
        if not isinstance(row, dict):
            errors.append("semantic.hero_not_object")
            continue
        hero_id = row.get("hero_id")
        if not isinstance(hero_id, int) or hero_id <= 0:
            errors.append(f"semantic.invalid_hero_id:{hero_id}")
            continue
        ids.append(hero_id)
        if row.get("review_status") != "approved":
            errors.append(f"semantic.hero_not_approved:{hero_id}")
        functions = row.get("functions", {})
        if not isinstance(functions, dict):
            errors.append(f"semantic.functions_missing:{hero_id}")
        else:
            for field in ("primary", "secondary"):
                values = functions.get(field, [])
                if not isinstance(values, list):
                    errors.append(f"semantic.{hero_id}.{field}_not_list")
                else:
                    errors.extend(
                        f"semantic.{hero_id}.unknown_function:{value}"
                        for value in values
                        if value not in SEMANTIC_FUNCTIONS
                    )
        capabilities = row.get("capabilities")
        function_keys = {
            value
            for field in ("primary", "secondary")
            for value in (functions.get(field, []) if isinstance(functions, dict) and isinstance(functions.get(field, []), list) else [])
        }
        if not isinstance(capabilities, dict) or set(capabilities) != function_keys:
            errors.append(f"semantic.{hero_id}.capabilities_drift")
        elif any(value not in {"low", "medium", "high", "unknown"} for value in capabilities.values()):
            errors.append(f"semantic.{hero_id}.invalid_capability_band")
        demands = row.get("demands", {})
        if not isinstance(demands, dict) or set(demands) != SEMANTIC_DEMANDS:
            errors.append(f"semantic.{hero_id}.incomplete_demands")
        elif any(value not in SEMANTIC_BANDS for value in demands.values()):
            errors.append(f"semantic.{hero_id}.invalid_demand_band")
        positions = row.get("position_credibility")
        if not isinstance(positions, dict) or set(positions) != SEMANTIC_POSITIONS:
            errors.append(f"semantic.{hero_id}.incomplete_position_credibility")
        elif any(value not in {"primary", "secondary", "unsupported", "unknown"} for value in positions.values()):
            errors.append(f"semantic.{hero_id}.invalid_position_credibility")
        for field in ("strengths", "weaknesses", "teamfight_profile"):
            values = row.get(field)
            if not isinstance(values, list) or not values:
                errors.append(f"semantic.{hero_id}.{field}_missing")
                continue
            for item in values:
                if not isinstance(item, dict) or not item.get("semantic_key"):
                    errors.append(f"semantic.{hero_id}.{field}_evidence_invalid")
                elif field != "teamfight_profile" and not isinstance(item.get("evidence_refs"), list):
                    errors.append(f"semantic.{hero_id}.{field}_refs_missing")
        review = row.get("review")
        if (
            not isinstance(review, dict)
            or not isinstance(review.get("sources"), list)
            or not review.get("sources")
            or not review.get("reviewer")
            or not review.get("reviewed_at")
            or not review.get("patch")
        ):
            errors.append(f"semantic.{hero_id}.provenance_incomplete")
        if row.get("confidence") not in {"high", "medium", "low"}:
            errors.append(f"semantic.{hero_id}.invalid_confidence")
        if row.get("empirical_support") not in SEMANTIC_BANDS:
            errors.append(f"semantic.{hero_id}.invalid_empirical_support")
    if len(ids) != len(set(ids)):
        errors.append("semantic.duplicate_hero_ids")
    return tuple(errors)


def _as_set(value: Any) -> set[Any]:
    return set(value) if isinstance(value, (list, tuple, set, frozenset)) else set()


def _rate(value: Any, field: str, errors: list[str]) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        errors.append(f"{field}: expected a number in [0, 1]")


def validate_valve_snapshot(
    snapshot: dict[str, Any], *, require_complete: bool = False
) -> tuple[str, ...]:
    errors: list[str] = []
    roster = snapshot.get("roster", [])
    heroes = snapshot.get("heroes", [])
    if not isinstance(roster, list) or not roster:
        errors.append("valve.roster_missing")
    if not isinstance(heroes, list) or not heroes:
        errors.append("valve.heroes_missing")
    roster_ids = [row.get("hero_id") for row in roster if isinstance(row, dict)]
    hero_ids = [row.get("hero_id") for row in heroes if isinstance(row, dict)]
    if len(roster_ids) != len(set(roster_ids)):
        errors.append("valve.duplicate_roster_ids")
    if len(hero_ids) != len(set(hero_ids)):
        errors.append("valve.duplicate_hero_ids")
    if require_complete and set(roster_ids) != set(hero_ids):
        errors.append("valve.incomplete_roster_details")
    for row in heroes:
        if not isinstance(row, dict):
            errors.append("valve.hero_not_object")
            continue
        hero_id = row.get("hero_id")
        if hero_id not in set(roster_ids):
            errors.append(f"valve.hero_not_in_roster:{hero_id}")
        if not row.get("identity"):
            errors.append(f"valve.identity_missing:{hero_id}")
        abilities = row.get("abilities", [])
        if not isinstance(abilities, list):
            errors.append(f"valve.abilities_not_list:{hero_id}")
        else:
            ids = [item.get("ability_id") for item in abilities if isinstance(item, dict)]
            if len(ids) != len(set(ids)):
                errors.append(f"valve.duplicate_abilities:{hero_id}")
    return tuple(errors)


def _count_pair(
    row: dict[str, Any],
    *,
    prefix: str,
    count_key: str,
    win_key: str,
    errors: list[str],
) -> None:
    count = row.get(count_key)
    wins = row.get(win_key)
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        errors.append(f"{prefix}.invalid_{count_key}")
    if isinstance(wins, bool) or not isinstance(wins, int) or wins < 0:
        errors.append(f"{prefix}.invalid_{win_key}")
    if isinstance(count, int) and isinstance(wins, int) and 0 <= wins <= count:
        return
    if isinstance(count, int) and isinstance(wins, int) and wins > count:
        errors.append(f"{prefix}.wins_exceed_count")


def validate_opendota_snapshot(
    snapshot: dict[str, Any],
    canonical_ids: set[int] | None = None,
    *,
    require_complete: bool = False,
) -> tuple[str, ...]:
    errors: list[str] = []
    heroes = snapshot.get("heroes", [])
    if not isinstance(heroes, list) or not heroes:
        return ("opendota.heroes_missing",)
    seen_ids: set[int] = set()
    for hero in heroes:
        if not isinstance(hero, dict):
            errors.append("opendota.hero_not_object")
            continue
        hero_id = hero.get("hero_id")
        if not isinstance(hero_id, int):
            errors.append(f"opendota.invalid_hero:{hero_id}")
            continue
        if hero_id in seen_ids:
            errors.append(f"opendota.duplicate_hero:{hero_id}")
        seen_ids.add(hero_id)
        if canonical_ids is not None and hero_id not in canonical_ids:
            errors.append(f"opendota.unknown_hero:{hero_id}")
        for field in (
            "bracket_performance",
            "duration_profile",
            "item_profile",
            "matchup_profile",
        ):
            if not isinstance(hero.get(field), list):
                errors.append(f"opendota.{hero_id}.{field}_not_list")

        for index, row in enumerate(hero.get("bracket_performance", [])):
            prefix = f"opendota.{hero_id}.bracket_performance.{index}"
            if not isinstance(row, dict):
                errors.append(f"{prefix}.not_object")
                continue
            _count_pair(
                row,
                prefix=prefix,
                count_key="picks",
                win_key="wins",
                errors=errors,
            )
            _rate(row.get("win_rate"), f"{prefix}.win_rate", errors)

        for index, row in enumerate(hero.get("duration_profile", [])):
            prefix = f"opendota.{hero_id}.duration_profile.{index}"
            if not isinstance(row, dict):
                errors.append(f"{prefix}.not_object")
                continue
            duration = row.get("duration_bin_seconds")
            if isinstance(duration, bool) or not isinstance(duration, int) or duration < 0:
                errors.append(f"{prefix}.invalid_duration")
            _count_pair(
                row,
                prefix=prefix,
                count_key="games",
                win_key="wins",
                errors=errors,
            )
            _rate(row.get("win_rate"), f"{prefix}.win_rate", errors)

        for index, row in enumerate(hero.get("item_profile", [])):
            prefix = f"opendota.{hero_id}.item_profile.{index}"
            if not isinstance(row, dict):
                errors.append(f"{prefix}.not_object")
                continue
            item_id = row.get("item_id")
            count = row.get("count")
            if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id <= 0:
                errors.append(f"{prefix}.invalid_item_id")
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                errors.append(f"{prefix}.invalid_count")
            _rate(row.get("share"), f"{prefix}.share", errors)

        matchup_keys: set[int] = set()
        for index, row in enumerate(hero.get("matchup_profile", [])):
            prefix = f"opendota.{hero_id}.matchup_profile.{index}"
            if not isinstance(row, dict):
                errors.append(f"{prefix}.not_object")
                continue
            opponent = row.get("opponent_hero_id")
            if not isinstance(opponent, int) or opponent <= 0:
                errors.append(f"{prefix}.invalid_opponent")
            elif canonical_ids is not None and opponent not in canonical_ids:
                errors.append(f"{prefix}.unknown_opponent:{opponent}")
            elif opponent in matchup_keys:
                errors.append(f"{prefix}.duplicate_opponent:{opponent}")
            if isinstance(opponent, int):
                matchup_keys.add(opponent)
            _count_pair(
                row,
                prefix=prefix,
                count_key="games",
                win_key="wins",
                errors=errors,
            )
            _rate(row.get("win_rate"), f"{prefix}.win_rate", errors)
            if row.get("evidence_population") != "opendota_aggregate":
                errors.append(f"{prefix}.population_not_explicit")
    if require_complete and canonical_ids is not None and seen_ids != canonical_ids:
        errors.append("opendota.incomplete_canonical_roster")
    return tuple(errors)


def validate_knowledge_snapshot(
    snapshot: dict[str, Any], *, require_opendota: bool = True
) -> tuple[str, ...]:
    errors: list[str] = []
    for field in ("schema_version", "knowledge_version", "generated_at", "sources", "heroes"):
        if field not in snapshot:
            errors.append(f"knowledge.missing:{field}")
    heroes = snapshot.get("heroes", [])
    if not isinstance(heroes, list) or not heroes:
        errors.append("knowledge.heroes_missing")
        return tuple(errors)
    sources = snapshot.get("sources", {})
    opendota_source = sources.get("opendota") if isinstance(sources, dict) else None
    if require_opendota and (
        not isinstance(opendota_source, dict)
        or opendota_source.get("required") is not True
        or opendota_source.get("status") not in {"available", "partial"}
    ):
        errors.append("knowledge.opendota_required")
    ids: list[int] = []
    for row in heroes:
        if not isinstance(row, dict):
            errors.append("knowledge.hero_not_object")
            continue
        identity = row.get("identity", {})
        hero_id = identity.get("hero_id") if isinstance(identity, dict) else None
        if not isinstance(hero_id, int):
            errors.append("knowledge.invalid_hero_id")
        else:
            ids.append(hero_id)
        if not row.get("provenance", {}).get("field_sources"):
            errors.append(f"knowledge.field_sources_missing:{hero_id}")
        empirical = row.get("empirical", {})
        if isinstance(empirical, dict):
            for field in (
                "bracket_performance",
                "duration_profile",
                "item_profile",
                "matchup_profile",
            ):
                if not isinstance(empirical.get(field), list):
                    errors.append(f"knowledge.{hero_id}.empirical.{field}_missing")
            if not isinstance(empirical.get("optional_valve_plus"), dict):
                errors.append(f"knowledge.{hero_id}.empirical.optional_valve_plus_invalid")
        editorial_status = row.get("editorial", {}).get("review_status")
        if editorial_status not in {"unreviewed", "draft", "reviewed", "approved", "stale"}:
            errors.append(f"knowledge.invalid_editorial_status:{hero_id}")
    if len(ids) != len(set(ids)):
        errors.append("knowledge.duplicate_hero_ids")
    return tuple(errors)


def assert_valid(errors: tuple[str, ...], label: str) -> None:
    if errors:
        raise ValidationError(f"Invalid {label} snapshot: {', '.join(errors)}", errors)
