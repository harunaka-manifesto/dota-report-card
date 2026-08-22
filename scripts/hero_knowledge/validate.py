"""Validation gates for source and product-facing snapshots."""

from __future__ import annotations

import re
from pathlib import Path
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


_EVIDENCE_REF_RE = re.compile(
    r"^(?P<namespace>valve|editorial|derived|opendota):[^\s#]+(?:#[^\s#]+)*$"
)


def validate_semantic_layer(
    snapshot: dict[str, Any],
    canonical_ids: set[int] | None = None,
    *,
    require_complete: bool = False,
    repo_root: str | Path | None = None,
    strict_evidence: bool | None = None,
) -> tuple[str, ...]:
    """Validate reviewed semantic facts before snapshot generation.

    The original pilot layer intentionally accepted scalar values and broad
    source labels.  Full-roster freezes opt into the stricter contract by
    carrying an evidence catalog (or by passing ``strict_evidence=True``):
    every field-level value is structured, references resolve to a known local
    source or derivation rule, and the canonical roster can be checked exactly.
    Keeping the compatibility mode here is important because the pilot file is
    retained as immutable history and is still used by migration tooling.
    """

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
    strict = bool(
        strict_evidence
        if strict_evidence is not None
        else isinstance(snapshot.get("evidence_catalog"), dict)
    )
    evidence_catalog = snapshot.get("evidence_catalog", {})
    if strict and not isinstance(evidence_catalog, dict):
        errors.append("semantic.evidence_catalog_missing")
        evidence_catalog = {}
    if strict:
        for catalog_ref, catalog_entry in evidence_catalog.items():
            if _EVIDENCE_REF_RE.fullmatch(str(catalog_ref)) is None:
                errors.append(f"semantic.evidence_catalog.malformed_ref:{catalog_ref}")
            elif not isinstance(catalog_entry, dict):
                errors.append(f"semantic.evidence_catalog.entry_invalid:{catalog_ref}")
            elif catalog_entry.get("namespace") != str(catalog_ref).split(":", 1)[0]:
                errors.append(f"semantic.evidence_catalog.namespace_mismatch:{catalog_ref}")
    evidence_root = (
        Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    )
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
            for value in (
                functions.get(field, [])
                if isinstance(functions, dict) and isinstance(functions.get(field, []), list)
                else []
            )
        }
        if not isinstance(capabilities, dict) or set(capabilities) != function_keys:
            errors.append(f"semantic.{hero_id}.capabilities_drift")
        elif strict:
            for key, value in capabilities.items():
                errors.extend(
                    _validate_semantic_value(
                        value,
                        field=f"semantic.{hero_id}.capabilities.{key}",
                        strict=True,
                        snapshot=snapshot,
                        evidence_catalog=evidence_catalog,
                        evidence_root=evidence_root,
                    )
                )
        elif any(
            value not in {"low", "medium", "high", "unknown"} for value in capabilities.values()
        ):
            errors.append(f"semantic.{hero_id}.invalid_capability_band")
        demands = row.get("demands", {})
        if not isinstance(demands, dict) or set(demands) != SEMANTIC_DEMANDS:
            errors.append(f"semantic.{hero_id}.incomplete_demands")
        elif strict:
            for key, value in demands.items():
                errors.extend(
                    _validate_semantic_value(
                        value,
                        field=f"semantic.{hero_id}.demands.{key}",
                        strict=True,
                        snapshot=snapshot,
                        evidence_catalog=evidence_catalog,
                        evidence_root=evidence_root,
                    )
                )
        elif any(value not in SEMANTIC_BANDS for value in demands.values()):
            errors.append(f"semantic.{hero_id}.invalid_demand_band")
        positions = row.get("position_credibility")
        if not isinstance(positions, dict) or set(positions) != SEMANTIC_POSITIONS:
            errors.append(f"semantic.{hero_id}.incomplete_position_credibility")
        elif any(
            value not in {"primary", "secondary", "unsupported", "unknown"}
            for value in positions.values()
        ):
            errors.append(f"semantic.{hero_id}.invalid_position_credibility")
        if strict:
            position_refs = row.get("position_evidence_refs")
            if not isinstance(position_refs, list) or not position_refs:
                errors.append(f"semantic.{hero_id}.position_refs_missing")
            else:
                for ref in position_refs:
                    errors.extend(
                        _validate_evidence_ref(
                            ref,
                            field=f"semantic.{hero_id}.position_evidence_refs",
                            snapshot=snapshot,
                            evidence_catalog=evidence_catalog,
                            evidence_root=evidence_root,
                        )
                    )
        specialist_markers = row.get("specialist_markers", [])
        if not isinstance(specialist_markers, list) or any(
            not isinstance(marker, str) or not marker for marker in specialist_markers
        ):
            errors.append(f"semantic.{hero_id}.specialist_markers_invalid")
        for field in ("strengths", "weaknesses", "teamfight_profile"):
            values = row.get(field)
            if not isinstance(values, list) or not values:
                errors.append(f"semantic.{hero_id}.{field}_missing")
                continue
            for item in values:
                if not isinstance(item, dict) or not item.get("semantic_key"):
                    errors.append(f"semantic.{hero_id}.{field}_evidence_invalid")
                elif strict:
                    refs = item.get("evidence_refs")
                    if not isinstance(refs, list) or not refs:
                        errors.append(f"semantic.{hero_id}.{field}_refs_missing")
                    else:
                        for ref in refs:
                            errors.extend(
                                _validate_evidence_ref(
                                    ref,
                                    field=f"semantic.{hero_id}.{field}.evidence_refs",
                                    snapshot=snapshot,
                                    evidence_catalog=evidence_catalog,
                                    evidence_root=evidence_root,
                                )
                            )
                elif field != "teamfight_profile" and not isinstance(
                    item.get("evidence_refs"), list
                ):
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
        if strict:
            review_sources = row.get("review", {}).get("sources", [])
            if isinstance(review_sources, list):
                for ref in review_sources:
                    errors.extend(
                        _validate_evidence_ref(
                            ref,
                            field=f"semantic.{hero_id}.review.sources",
                            snapshot=snapshot,
                            evidence_catalog=evidence_catalog,
                            evidence_root=evidence_root,
                        )
                    )
    if len(ids) != len(set(ids)):
        errors.append("semantic.duplicate_hero_ids")
    if strict:
        root_review = snapshot.get("review", {})
        root_sources = root_review.get("sources", []) if isinstance(root_review, dict) else []
        if not isinstance(root_sources, list) or not root_sources:
            errors.append("semantic.review.sources_missing")
        else:
            for ref in root_sources:
                errors.extend(
                    _validate_evidence_ref(
                        ref,
                        field="semantic.review.sources",
                        snapshot=snapshot,
                        evidence_catalog=evidence_catalog,
                        evidence_root=evidence_root,
                    )
                )
    if canonical_ids is not None:
        observed = set(ids)
        unknown = sorted(observed - canonical_ids)
        missing = sorted(canonical_ids - observed)
        errors.extend(f"semantic.unknown_hero:{hero_id}" for hero_id in unknown)
        if require_complete and missing:
            errors.append("semantic.incomplete_canonical_roster")
    elif require_complete:
        errors.append("semantic.canonical_roster_missing")
    if (
        require_complete
        and isinstance(snapshot.get("hero_count"), int)
        and snapshot["hero_count"] != len(ids)
    ):
        errors.append("semantic.hero_count_mismatch")
    return tuple(errors)


def _validate_semantic_value(
    value: Any,
    *,
    field: str,
    strict: bool,
    snapshot: dict[str, Any],
    evidence_catalog: dict[str, Any],
    evidence_root: Path,
) -> tuple[str, ...]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return (f"{field}.structured_value_missing",)
    band = value.get("band")
    if band not in SEMANTIC_BANDS:
        errors.append(f"{field}.invalid_band")
    refs = value.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        errors.append(f"{field}.evidence_refs_missing")
    else:
        for ref in refs:
            errors.extend(
                _validate_evidence_ref(
                    ref,
                    field=f"{field}.evidence_refs",
                    snapshot=snapshot,
                    evidence_catalog=evidence_catalog,
                    evidence_root=evidence_root,
                )
            )
    return tuple(errors)


def _validate_evidence_ref(
    ref: Any,
    *,
    field: str,
    snapshot: dict[str, Any],
    evidence_catalog: dict[str, Any],
    evidence_root: Path,
) -> tuple[str, ...]:
    if not isinstance(ref, str) or _EVIDENCE_REF_RE.fullmatch(ref) is None:
        return (f"{field}.malformed_ref:{ref}",)
    entry = evidence_catalog.get(ref)
    if not isinstance(entry, dict):
        return (f"{field}.unresolved_ref:{ref}",)
    namespace = ref.split(":", 1)[0]
    if entry.get("namespace") != namespace:
        return (f"{field}.namespace_mismatch:{ref}",)
    errors: list[str] = []
    source_file = entry.get("source_file")
    if namespace == "editorial":
        if not isinstance(source_file, str) or not source_file:
            errors.append(f"{field}.editorial_source_missing:{ref}")
        else:
            root_resolved = evidence_root.resolve()
            source_resolved = (evidence_root / source_file).resolve()
            if root_resolved not in source_resolved.parents:
                errors.append(f"{field}.editorial_source_outside_root:{ref}")
            elif not source_resolved.is_file():
                errors.append(f"{field}.editorial_source_unresolved:{ref}")
    if namespace == "derived":
        version = str(snapshot.get("version", ""))
        rule_version = str(entry.get("rule_version", ""))
        if not rule_version or rule_version != version:
            errors.append(f"{field}.derived_rule_unresolved:{ref}")
    if namespace in {"valve", "opendota"}:
        status = entry.get("status")
        if status not in {"available", "partial"}:
            # A strict field-level citation must resolve to usable evidence;
            # an unavailable/unknown source belongs in the snapshot's
            # limitations metadata, never in a factual claim's refs.
            errors.append(f"{field}.source_unavailable:{ref}")
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
    semantic_source = sources.get("semantic_review") if isinstance(sources, dict) else None
    strict_semantic = isinstance(semantic_source, dict) and semantic_source.get("status") in {
        "reviewed",
        "approved",
    }
    if require_opendota and (
        not isinstance(opendota_source, dict)
        or (
            opendota_source.get("required") is not False
            and opendota_source.get("status") not in {"available", "partial"}
        )
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
        specialist_markers = row.get("specialist_markers", [])
        if not isinstance(specialist_markers, list) or any(
            not isinstance(marker, str) or not marker for marker in specialist_markers
        ):
            errors.append(f"knowledge.{hero_id}.specialist_markers_invalid")
        if strict_semantic:
            functions = row.get("functions")
            if (
                not isinstance(functions, dict)
                or not isinstance(functions.get("primary"), list)
                or not isinstance(functions.get("secondary"), list)
            ):
                errors.append(f"knowledge.{hero_id}.functions_missing")
                function_keys: set[str] = set()
            else:
                function_keys = set(functions["primary"]) | set(functions["secondary"])
            capabilities = row.get("capabilities")
            if not isinstance(capabilities, dict) or set(capabilities) != function_keys:
                errors.append(f"knowledge.{hero_id}.capabilities_drift")
            demands = row.get("demands")
            if not isinstance(demands, dict) or set(demands) != SEMANTIC_DEMANDS:
                errors.append(f"knowledge.{hero_id}.demands_incomplete")
            position = row.get("position_credibility")
            if not isinstance(position, dict) or set(position) != SEMANTIC_POSITIONS:
                errors.append(f"knowledge.{hero_id}.position_credibility_incomplete")
    if len(ids) != len(set(ids)):
        errors.append("knowledge.duplicate_hero_ids")
    return tuple(errors)


def assert_valid(errors: tuple[str, ...], label: str) -> None:
    if errors:
        raise ValidationError(f"Invalid {label} snapshot: {', '.join(errors)}", errors)
