"""Translate STRATZ-native models into the provider-neutral V7 input model."""

from __future__ import annotations

from typing import Literal

from app.providers.base import (
    CanonicalProfile,
    ProviderProvenance,
    V7CanonicalHistory,
    V7CanonicalMatch,
    canonical_json_sha256,
)

from .models import (
    STRATZ_PROVIDER,
    STRATZ_PROVIDER_SCHEMA_VERSION,
    StratzHistory,
    StratzHistoryPage,
    StratzMatch,
    StratzMatchPlayer,
    StratzPlayerProfile,
)

STRATZ_NORMALIZER_VERSION = "stratz-v7-normalization-1.0.0"


def normalize_stratz_profile(profile: StratzPlayerProfile) -> CanonicalProfile:
    return CanonicalProfile(
        provider=STRATZ_PROVIDER,
        provider_schema_version=STRATZ_PROVIDER_SCHEMA_VERSION,
        account_id=profile.steam_account_id,
        display_name=profile.name,
        avatar_url=profile.avatar,
        is_anonymous=profile.is_anonymous,
        is_public=profile.is_stratz_public,
    )


def normalize_stratz_match(
    match: StratzMatch,
    *,
    account_id: int | None = None,
) -> V7CanonicalMatch:
    if match.match_id <= 0:
        raise ValueError("STRATZ match ID must be positive")
    player = match.player_for(account_id)
    if player is None:
        raise ValueError("STRATZ match does not contain the requested player")
    return _canonical_match(match, player)


def normalize_stratz_page(
    page: StratzHistoryPage,
    *,
    account_id: int | None = None,
) -> tuple[V7CanonicalMatch, ...]:
    return tuple(normalize_stratz_match(match, account_id=account_id) for match in page.matches)


def normalize_stratz_history(
    history: StratzHistory,
    *,
    account_id: int | None = None,
) -> V7CanonicalHistory:
    selected = _deduplicate(history.matches)
    canonical = tuple(
        normalize_stratz_match(match, account_id=account_id) for match in selected.matches
    )
    parsed_coverage = (
        sum(match.is_parsed for match in history.matches) / len(history.matches)
        if history.matches
        else None
    )
    provenance = ProviderProvenance(
        provider=STRATZ_PROVIDER,
        provider_schema_version=STRATZ_PROVIDER_SCHEMA_VERSION,
        operation_name=history.operation_name,
        operation_version=history.operation_version,
        document_sha256=history.operation_document_sha256,
        normalizer_version=STRATZ_NORMALIZER_VERSION,
        request_count=history.ledger.request_count,
        page_count=history.ledger.page_count or len(history.pages),
        fetched_at=history.fetched_at,
        raw_payload_sha256=history.raw_payload_sha256,
        completeness="truncated" if history.truncated else "complete",
        parsed_coverage=parsed_coverage,
    )
    return V7CanonicalHistory(
        profile=normalize_stratz_profile(history.profile),
        window=history.window,
        matches=canonical,
        provenance=provenance,
        duplicate_match_count=selected.duplicate_count,
    )


class _DeduplicatedMatches:
    def __init__(self, matches: tuple[StratzMatch, ...], duplicate_count: int) -> None:
        self.matches = matches
        self.duplicate_count = duplicate_count


def _deduplicate(matches: tuple[StratzMatch, ...]) -> _DeduplicatedMatches:
    chosen: dict[int, StratzMatch] = {}
    duplicate_count = 0
    for match in matches:
        previous = chosen.get(match.match_id)
        if previous is None:
            chosen[match.match_id] = match
            continue
        duplicate_count += 1
        if _match_preference(match) > _match_preference(previous):
            chosen[match.match_id] = match
    ordered = tuple(
        sorted(
            chosen.values(),
            key=lambda item: (item.started_at is None, -(item.started_at or 0), item.match_id),
        )
    )
    return _DeduplicatedMatches(ordered, duplicate_count)


def _match_preference(match: StratzMatch) -> tuple[int, str]:
    values = [
        match.did_radiant_win,
        match.duration_seconds,
        match.started_at,
        match.ended_at,
        match.lobby_type,
        match.game_mode,
        match.game_version_id,
        match.parsed_at,
    ]
    for player in match.players:
        values.extend(player.as_dict().values())
    populated = sum(value is not None for value in values)
    # A stable digest breaks ties without depending on page arrival order.
    return populated, canonical_json_sha256(match.as_dict())


def _canonical_match(match: StratzMatch, player: StratzMatchPlayer) -> V7CanonicalMatch:
    side: Literal["radiant", "dire"] | None = (
        "radiant"
        if player.is_radiant is True
        else "dire"
        if player.is_radiant is False
        else None
    )
    won = player.is_victory
    if won is None and match.did_radiant_win is not None and side is not None:
        won = match.did_radiant_win == (side == "radiant")
    return V7CanonicalMatch(
        provider=STRATZ_PROVIDER,
        provider_schema_version=STRATZ_PROVIDER_SCHEMA_VERSION,
        match_id=match.match_id,
        hero_id=player.hero_id,
        started_at=match.started_at,
        duration_seconds=match.duration_seconds,
        side=side,
        won=won,
        kills=player.kills,
        deaths=player.deaths,
        assists=player.assists,
        game_version_id=match.game_version_id,
        position=player.position,
        role=player.role,
        lane=player.lane,
        game_mode_native=match.game_mode,
        lobby_native=match.lobby_type,
        leaver_status_native=player.leaver_status,
        is_parsed=match.is_parsed,
    )


__all__ = [
    "STRATZ_NORMALIZER_VERSION",
    "normalize_stratz_history",
    "normalize_stratz_match",
    "normalize_stratz_page",
    "normalize_stratz_profile",
]
