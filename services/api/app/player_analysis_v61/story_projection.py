"""Assembly boundary for the additive Free DNA V6.1 story payload.

The descriptive aggregators live in :mod:`story_payload`; this module owns
only the boundary between those facts and the report contract.  In
particular, it projects the already-published legacy findings and never
recomputes inferential evidence.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import UTC, date, datetime
from typing import Any, Literal

from app.api.story_payload_schemas_v61 import (
    STORY_CARD_VERSION,
    STORY_HERO_METADATA_VERSION,
    STORY_HERO_TAXONOMY_VERSION,
    STORY_MODULE_KEYS,
    STORY_MODULE_PAGES,
    STORY_PAYLOAD_VERSION,
    StoryPayloadV61Schema,
)
from app.player_analysis_v61.story_payload import build_story_modules
from app.player_analysis_v61.story_selector import StorySelection

STORY_VERSION_KEYS = (
    "story_payload",
    "story_rules",
    "story_copy",
    "game_mode_map",
    "hero_taxonomy",
    "hero_metadata",
    "archetype_contract",
)


def _field(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, Mapping):
        value = row.get(key, default)
    else:
        value = getattr(row, key, default)
    if value is not None:
        return value
    aliases = {
        "started_at": "start_time",
        "start_time": "started_at",
        "duration_seconds": "duration",
    }
    alias = aliases.get(key)
    if alias is None:
        return default
    if isinstance(row, Mapping):
        return row.get(alias, default)
    return getattr(row, alias, default)


def _int(value: Any, *, minimum: int | None = None) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if isinstance(value, float) and value != parsed:
        return None
    if minimum is not None and parsed < minimum:
        return None
    return parsed


def _bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    return None


def _story_row_hash_projection(row: Any) -> dict[str, Any]:
    """Return exactly the identifier-free fields consumed by story facts."""

    return {
        "game_mode": _int(_field(row, "game_mode")),
        "lobby_type": _int(_field(row, "lobby_type")),
        "started_at": _int(_field(row, "started_at")),
        "duration_seconds": _int(_field(row, "duration_seconds"), minimum=0),
        "hero_id": _int(_field(row, "hero_id"), minimum=1),
        "won": _bool(_field(row, "won")),
        "kills": _int(_field(row, "kills"), minimum=0),
        "deaths": _int(_field(row, "deaths"), minimum=0),
        "assists": _int(_field(row, "assists"), minimum=0),
    }


def story_input_sha256(rows: Sequence[Any]) -> str:
    """Hash the sorted, identifier-free story inputs used by aggregation."""

    projections = [_story_row_hash_projection(row) for row in rows]
    projections.sort(
        key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"))
    )
    payload = json.dumps(
        {"version": STORY_PAYLOAD_VERSION, "rows": projections},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _utc_date(timestamp: Any) -> date | None:
    value = _int(timestamp)
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value, tz=UTC).date()
    except (OverflowError, OSError, ValueError):
        return None


def _date_string(timestamp: Any) -> str | None:
    value = _utc_date(timestamp)
    return value.isoformat() if value is not None else None


def _profile_display_name(profile: Mapping[str, Any] | None) -> str | None:
    if not profile:
        return None
    nested = profile.get("profile")
    source = nested if isinstance(nested, Mapping) else profile
    value = source.get("personaname", source.get("display_name"))
    if not isinstance(value, str):
        return None
    value = value.strip()
    if (
        not value
        or value.casefold() == "anonymous player"
        or value.isdigit()
        or value.startswith(("http://", "https://"))
    ):
        return None
    return value


def _completeness(value: str | bool | None) -> Literal[
    "complete", "possibly_truncated", "unknown"
]:
    if value is True or value == "complete":
        return "complete"
    if value == "possibly_truncated":
        return "possibly_truncated"
    return "unknown"


def _audit_value(audit: Any, key: str, default: Any = None) -> Any:
    if isinstance(audit, Mapping):
        return audit.get(key, default)
    return getattr(audit, key, default)


def _report_findings(report: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    raw = report.get("findings")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        return ()
    return tuple(item for item in raw if isinstance(item, Mapping))


def _finding_slot(
    family: str,
    findings: Sequence[Mapping[str, Any]],
    *,
    comparable_pair_count: int | None,
) -> dict[str, Any]:
    finding = next((item for item in findings if item.get("family") == family), None)
    contract = finding.get("claim_contract") if finding is not None else None
    eligible = bool(
        finding
        and finding.get("published")
        and finding.get("claim")
        and finding.get("interpretation")
        and isinstance(contract, Mapping)
    )
    slot_family = "post_loss_response" if family == "post_loss_response" else "transfer"
    if not eligible or (family == "post_loss_response" and comparable_pair_count is None):
        return {"available": False, "family": slot_family, "content": None}
    if finding is None or not isinstance(contract, Mapping):
        return {"available": False, "family": slot_family, "content": None}

    projected_contract = deepcopy(dict(contract))
    projected_contract.pop("deep_handoff", None)
    content = {
        "family": slot_family,
        "claim": finding.get("claim"),
        "interpretation": finding.get("interpretation"),
        "claim_contract": projected_contract,
        "evidence_refs": [str(value) for value in finding.get("evidence_refs", ())],
        "confidence": finding.get("confidence", "unavailable"),
        "semantic_outcome_key": finding.get("semantic_outcome_key"),
        "comparable_opportunities": comparable_pair_count
        if family == "post_loss_response"
        else None,
        "cross_session_transitions": False,
    }
    return {"available": True, "family": slot_family, "content": content}


def _module_is_shippable(key: str, module: Mapping[str, Any]) -> bool:
    if module.get("state") not in {"available", "degraded"}:
        return False
    if key != "deep":
        return True
    data = module.get("data")
    return isinstance(data, Mapping) and data.get("available") is True


def _manifests(
    modules: Mapping[str, Mapping[str, Any]],
    finding_slots: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    page_items: list[dict[str, Any]] = []
    for key in STORY_MODULE_KEYS:
        module = modules[key]
        if not _module_is_shippable(key, module):
            continue
        page_items.append({"id": key, "page": STORY_MODULE_PAGES[key], "module": key})
    if finding_slots["transfer"].get("available"):
        page_items.append({"id": "transfer", "page": STORY_MODULE_PAGES["transfer"], "module": "transfer"})
    if finding_slots["post_loss"].get("available"):
        page_items.append({"id": "post_loss", "page": STORY_MODULE_PAGES["post_loss"], "module": "post_loss"})

    # Page 24 is the last public combat fact.  Page 26 is a reviewed frontend
    # bridge, not a story module, and must be adjacent without naming Page 25.
    if any(item.get("page") == STORY_MODULE_PAGES["deaths"] for item in page_items):
        page_items.append({"id": "page-26", "page": 26})
    page_items.sort(key=lambda item: int(item["page"]))

    card_modules = [
        key
        for key in STORY_MODULE_KEYS
        if key != "card_collage" and _module_is_shippable(key, modules[key])
    ]
    if finding_slots["transfer"].get("available"):
        card_modules.append("transfer")
    if finding_slots["post_loss"].get("available"):
        card_modules.append("post_loss")
    card_modules.sort(key=lambda key: STORY_MODULE_PAGES[key])
    cards = [
        {
            "id": f"story-card-{key}",
            "module": key,
            "page": STORY_MODULE_PAGES[key],
        }
        for key in card_modules
    ]
    return page_items, cards


def build_story_payload(
    *,
    selection: StorySelection,
    legacy_report: Mapping[str, Any],
    profile: Mapping[str, Any] | None,
    canonical_audit: Mapping[str, Any] | Any,
    window_start: int,
    window_end: int,
    hero_metadata: Mapping[Any, Any] | None,
    hero_taxonomy_checksums: Mapping[str, str],
    internal_evidence: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Build and validate the complete story extension when it is active."""

    if len(selection.matches) < 30:
        return None
    rows = tuple(selection.matches)
    audit_completeness = _audit_value(canonical_audit, "completeness")
    completeness = _completeness(audit_completeness)
    modules = build_story_modules(
        rows,
        hero_metadata=hero_metadata,
        window_start=window_start,
        window_end=window_end,
        history_completeness=completeness,
        mode_map_valid=True,
        display_name=_profile_display_name(profile),
        deep_available=False,
    )
    modules["card_collage"] = {
        "state": "available",
        "reason": None,
        "copy_variant": STORY_CARD_VERSION,
        "data": {"version": STORY_CARD_VERSION, "cards": []},
    }

    dates = [
        day
        for row in rows
        if (day := _utc_date(_field(row, "started_at"))) is not None
    ]
    if not dates:
        raise ValueError("active story payload requires dated matches")
    observed_from = min(dates)
    observed_to = max(dates)
    window_start_date = _utc_date(window_start)
    window_end_date = _utc_date(window_end)
    if window_start_date is None or window_end_date is None:
        raise ValueError("story payload requires valid window dates")
    duration_candidates = len(rows)
    duration_known = sum(
        _int(_field(row, "duration_seconds"), minimum=0) is not None for row in rows
    )
    duration_coverage = duration_known / duration_candidates if duration_candidates else 0.0
    pair_count: int | None = None
    if isinstance(internal_evidence, Mapping):
        post_loss = internal_evidence.get("post_loss")
        if isinstance(post_loss, Mapping):
            raw_pair_count = post_loss.get("comparable_pair_count")
            pair_count = _int(raw_pair_count, minimum=0)
    finding_slots = {
        "post_loss": _finding_slot(
            "post_loss_response",
            _report_findings(legacy_report),
            comparable_pair_count=pair_count,
        ),
        "transfer": _finding_slot(
            "transfer",
            _report_findings(legacy_report),
            comparable_pair_count=None,
        ),
    }
    page_manifest, cards = _manifests(modules, finding_slots)
    card_data = modules["card_collage"]["data"]
    if not isinstance(card_data, dict):
        raise ValueError("story card collage requires card data")
    card_data["cards"] = cards

    hello_data = modules["hello"]["data"]
    short_history = bool(
        isinstance(hello_data, Mapping) and hello_data.get("history_materially_short")
    )
    selection_counts = {
        key: int(selection.mode_counts.get(key, 0))
        for key in (
            "unranked_all_pick",
            "ranked_all_pick",
            "unranked_captains_mode",
            "ranked_captains_mode",
        )
    }
    payload = {
        "version": STORY_PAYLOAD_VERSION,
        "availability": {"state": "available", "reason": None},
        "provenance": {
            "provider": "opendota_summary",
            "physical_history_requests": 1,
            "detail_requests": 0,
            "parse_requests": 0,
            "mode_map_version": selection.mode_map_version,
            "mode_map_checksum": selection.mode_map_checksum,
            "hero_taxonomy_version": STORY_HERO_TAXONOMY_VERSION,
            "hero_taxonomy_factual_checksum": hero_taxonomy_checksums.get(
                "factual_checksum"
            ),
            "hero_taxonomy_editorial_checksum": hero_taxonomy_checksums.get(
                "editorial_checksum"
            ),
            "hero_metadata_version": STORY_HERO_METADATA_VERSION,
            "story_input_sha256": story_input_sha256(rows),
        },
        "universe": {
            "key": "public_ap_cm_story_v1",
            "requested_window_days": 365,
            "window_start": window_start_date.isoformat(),
            "window_end": window_end_date.isoformat(),
            "observed_from": observed_from.isoformat(),
            "observed_to": observed_to.isoformat(),
            "observed_days": (observed_to - observed_from).days + 1,
            "history_materially_short": short_history,
            "match_count": len(rows),
            "volume_tier": "limited" if len(rows) < 60 else "normal",
            "mode_counts": selection_counts,
            "excluded_or_unknown_count": selection.excluded_or_unknown_count,
            "duration_candidate_count": duration_candidates,
            "duration_known_count": duration_known,
            "duration_coverage": duration_coverage,
            "history_completeness": completeness,
        },
        "identity": {"display_name": _profile_display_name(profile)},
        "modules": modules,
        "finding_slots": finding_slots,
        "page_manifest": page_manifest,
        "card_manifest": cards,
    }
    return StoryPayloadV61Schema.model_validate(payload).model_dump(mode="json", by_alias=True)


__all__ = [
    "STORY_VERSION_KEYS",
    "build_story_payload",
    "story_input_sha256",
]
