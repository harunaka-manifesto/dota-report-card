"""Validated STRATZ-native response models for the V7 foundation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.providers.base import HistoryWindow, RequestLedger, canonical_json_sha256

STRATZ_PROVIDER = "stratz"
STRATZ_PROVIDER_SCHEMA_VERSION = "stratz-history-schema-1.0.0"

# These are an audited schema snapshot, not a conversion table. Unknown future
# enum values remain valid native strings so a schema extension cannot silently
# become an old provider's integer or role vocabulary.
STRATZ_ENUM_VOCABULARY: dict[str, tuple[str, ...]] = {
    "leaver_status": (
        "NONE",
        "DISCONNECTED",
        "DISCONNECTED_TOO_LONG",
        "ABANDONED",
        "AFK",
        "NEVER_CONNECTED",
        "NEVER_CONNECTED_TOO_LONG",
        "FAILED_TO_READY_UP",
        "DECLINED_READY_UP",
    ),
    "lane": ("ROAMING", "SAFE_LANE", "MID_LANE", "OFF_LANE", "JUNGLE", "UNKNOWN"),
    "position": ("POSITION_1", "POSITION_2", "POSITION_3", "POSITION_4", "POSITION_5", "UNKNOWN", "FILTERED", "ALL"),
    "role": ("CORE", "LIGHT_SUPPORT", "HARD_SUPPORT", "UNKNOWN"),
    "lane_outcome": ("TIE", "RADIANT_VICTORY", "RADIANT_STOMP", "DIRE_VICTORY", "DIRE_STOMP"),
}


class StratzModelError(ValueError):
    """The response no longer matches the selected operation's shape."""


_MISSING = object()


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise StratzModelError(f"{path} must be an object")
    return value


def _value(raw: Mapping[str, Any], key: str, path: str, *, required: bool = True) -> Any:
    value = raw.get(key, _MISSING)
    if required and value is _MISSING:
        raise StratzModelError(f"missing STRATZ field: {path}.{key}")
    return None if value is _MISSING else value


def _int_value(value: Any, path: str, *, required: bool = False) -> int | None:
    if value is None:
        if required:
            raise StratzModelError(f"{path} cannot be null")
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise StratzModelError(f"{path} must be an integer")
    return value


def _bool_value(value: Any, path: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise StratzModelError(f"{path} must be a boolean")
    return value


def _str_value(value: Any, path: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise StratzModelError(f"{path} must be a string")
    return value


def _int_tuple(value: Any, path: str) -> tuple[int, ...] | None:
    if value is None:
        return None
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise StratzModelError(f"{path} must be an array")
    result: list[int] = []
    for index, item in enumerate(value):
        parsed = _int_value(item, f"{path}[{index}]", required=True)
        assert parsed is not None
        result.append(parsed)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class StratzPlayerProfile:
    steam_account_id: int
    name: str | None
    avatar: str | None
    is_anonymous: bool | None
    is_stratz_public: bool | None

    @classmethod
    def from_graphql(cls, player: Any) -> StratzPlayerProfile:
        raw_player = _object(player, "player")
        account_id = _int_value(
            _value(raw_player, "steamAccountId", "player"),
            "player.steamAccountId",
            required=True,
        )
        assert account_id is not None
        account_value = _value(raw_player, "steamAccount", "player")
        if account_value is None:
            raise StratzModelError("player.steamAccount is unavailable")
        account = _object(account_value, "player.steamAccount")
        return cls(
            steam_account_id=account_id,
            name=_str_value(_value(account, "name", "player.steamAccount"), "player.steamAccount.name"),
            avatar=_str_value(_value(account, "avatar", "player.steamAccount"), "player.steamAccount.avatar"),
            is_anonymous=_bool_value(
                _value(account, "isAnonymous", "player.steamAccount"),
                "player.steamAccount.isAnonymous",
            ),
            is_stratz_public=_bool_value(
                _value(account, "isStratzPublic", "player.steamAccount"),
                "player.steamAccount.isStratzPublic",
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "steam_account_id": self.steam_account_id,
            "name": self.name,
            "avatar": self.avatar,
            "is_anonymous": self.is_anonymous,
            "is_stratz_public": self.is_stratz_public,
        }


@dataclass(frozen=True, slots=True)
class StratzMatchPlayer:
    steam_account_id: int | None
    player_slot: int | None
    is_radiant: bool | None
    is_victory: bool | None
    hero_id: int | None
    variant: int | None
    kills: int | None
    deaths: int | None
    assists: int | None
    leaver_status: str | None
    party_id: int | None
    lane: str | None
    position: str | None
    role: str | None

    @classmethod
    def from_graphql(cls, player: Any, *, path: str = "players[]") -> StratzMatchPlayer:
        raw = _object(player, path)
        return cls(
            steam_account_id=_int_value(_value(raw, "steamAccountId", path), f"{path}.steamAccountId"),
            player_slot=_int_value(_value(raw, "playerSlot", path), f"{path}.playerSlot"),
            is_radiant=_bool_value(_value(raw, "isRadiant", path), f"{path}.isRadiant"),
            is_victory=_bool_value(_value(raw, "isVictory", path), f"{path}.isVictory"),
            hero_id=_int_value(_value(raw, "heroId", path), f"{path}.heroId"),
            variant=_int_value(_value(raw, "variant", path), f"{path}.variant"),
            kills=_int_value(_value(raw, "kills", path), f"{path}.kills"),
            deaths=_int_value(_value(raw, "deaths", path), f"{path}.deaths"),
            assists=_int_value(_value(raw, "assists", path), f"{path}.assists"),
            leaver_status=_str_value(_value(raw, "leaverStatus", path), f"{path}.leaverStatus"),
            party_id=_int_value(_value(raw, "partyId", path), f"{path}.partyId"),
            lane=_str_value(_value(raw, "lane", path), f"{path}.lane"),
            position=_str_value(_value(raw, "position", path), f"{path}.position"),
            role=_str_value(_value(raw, "role", path), f"{path}.role"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "steam_account_id": self.steam_account_id,
            "player_slot": self.player_slot,
            "is_radiant": self.is_radiant,
            "is_victory": self.is_victory,
            "hero_id": self.hero_id,
            "variant": self.variant,
            "kills": self.kills,
            "deaths": self.deaths,
            "assists": self.assists,
            "leaver_status": self.leaver_status,
            "party_id": self.party_id,
            "lane": self.lane,
            "position": self.position,
            "role": self.role,
        }


@dataclass(frozen=True, slots=True)
class StratzMatch:
    match_id: int
    did_radiant_win: bool | None
    duration_seconds: int | None
    started_at: int | None
    ended_at: int | None
    lobby_type: str | None
    game_mode: str | None
    game_version_id: int | None
    parsed_at: int | None
    players: tuple[StratzMatchPlayer, ...]
    radiant_kills: tuple[int, ...] | None = None
    dire_kills: tuple[int, ...] | None = None
    radiant_networth_leads: tuple[int, ...] | None = None
    radiant_experience_leads: tuple[int, ...] | None = None
    bottom_lane_outcome: str | None = None
    mid_lane_outcome: str | None = None
    top_lane_outcome: str | None = None

    @classmethod
    def from_graphql(cls, match: Any, *, path: str = "matches[]") -> StratzMatch:
        raw = _object(match, path)
        raw_players = _value(raw, "players", path)
        if isinstance(raw_players, Mapping):
            player_values: Sequence[Any] = (raw_players,)
        elif isinstance(raw_players, Sequence) and not isinstance(
            raw_players, (str, bytes, bytearray)
        ):
            player_values = raw_players
        else:
            raise StratzModelError(f"{path}.players must be an array")
        match_id = _int_value(_value(raw, "id", path), f"{path}.id", required=True)
        assert match_id is not None
        return cls(
            match_id=match_id,
            did_radiant_win=_bool_value(_value(raw, "didRadiantWin", path), f"{path}.didRadiantWin"),
            duration_seconds=_int_value(_value(raw, "durationSeconds", path), f"{path}.durationSeconds"),
            started_at=_int_value(_value(raw, "startDateTime", path), f"{path}.startDateTime"),
            ended_at=_int_value(_value(raw, "endDateTime", path), f"{path}.endDateTime"),
            lobby_type=_str_value(_value(raw, "lobbyType", path), f"{path}.lobbyType"),
            game_mode=_str_value(_value(raw, "gameMode", path), f"{path}.gameMode"),
            game_version_id=_int_value(_value(raw, "gameVersionId", path), f"{path}.gameVersionId"),
            parsed_at=_int_value(_value(raw, "parsedDateTime", path), f"{path}.parsedDateTime"),
            players=tuple(
                StratzMatchPlayer.from_graphql(item, path=f"{path}.players[{index}]")
                for index, item in enumerate(player_values)
            ),
            radiant_kills=_int_tuple(_value(raw, "radiantKills", path, required=False), f"{path}.radiantKills"),
            dire_kills=_int_tuple(_value(raw, "direKills", path, required=False), f"{path}.direKills"),
            radiant_networth_leads=_int_tuple(
                _value(raw, "radiantNetworthLeads", path, required=False),
                f"{path}.radiantNetworthLeads",
            ),
            radiant_experience_leads=_int_tuple(
                _value(raw, "radiantExperienceLeads", path, required=False),
                f"{path}.radiantExperienceLeads",
            ),
            bottom_lane_outcome=_str_value(
                _value(raw, "bottomLaneOutcome", path, required=False),
                f"{path}.bottomLaneOutcome",
            ),
            mid_lane_outcome=_str_value(
                _value(raw, "midLaneOutcome", path, required=False),
                f"{path}.midLaneOutcome",
            ),
            top_lane_outcome=_str_value(
                _value(raw, "topLaneOutcome", path, required=False),
                f"{path}.topLaneOutcome",
            ),
        )

    @property
    def is_parsed(self) -> bool:
        return self.parsed_at is not None

    def player_for(self, account_id: int | None) -> StratzMatchPlayer | None:
        if account_id is not None:
            return next(
                (player for player in self.players if player.steam_account_id == account_id),
                None,
            )
        return self.players[0] if len(self.players) == 1 else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "did_radiant_win": self.did_radiant_win,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "lobby_type": self.lobby_type,
            "game_mode": self.game_mode,
            "game_version_id": self.game_version_id,
            "parsed_at": self.parsed_at,
            "players": [player.as_dict() for player in self.players],
            "radiant_kills": self.radiant_kills,
            "dire_kills": self.dire_kills,
            "radiant_networth_leads": self.radiant_networth_leads,
            "radiant_experience_leads": self.radiant_experience_leads,
            "bottom_lane_outcome": self.bottom_lane_outcome,
            "mid_lane_outcome": self.mid_lane_outcome,
            "top_lane_outcome": self.top_lane_outcome,
        }


@dataclass(frozen=True, slots=True)
class StratzHistoryPage:
    profile: StratzPlayerProfile
    matches: tuple[StratzMatch, ...]
    skip: int
    take: int
    raw_data: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_graphql(
        cls,
        data: Any,
        *,
        account_id: int,
        skip: int,
        take: int,
    ) -> StratzHistoryPage:
        root = _object(data, "data")
        player = _value(root, "player", "data")
        if player is None:
            raise StratzModelError("data.player is unavailable")
        raw_player = _object(player, "data.player")
        profile = StratzPlayerProfile.from_graphql(raw_player)
        raw_matches = _value(raw_player, "matches", "data.player")
        if not isinstance(raw_matches, Sequence) or isinstance(
            raw_matches, (str, bytes, bytearray)
        ):
            raise StratzModelError("data.player.matches must be an array")
        return cls(
            profile=profile,
            matches=tuple(
                StratzMatch.from_graphql(match, path=f"data.player.matches[{index}]")
                for index, match in enumerate(raw_matches)
            ),
            skip=skip,
            take=take,
            raw_data=root,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile.as_dict(),
            "matches": [match.as_dict() for match in self.matches],
            "skip": self.skip,
            "take": self.take,
        }


@dataclass(frozen=True, slots=True)
class StratzHistory:
    profile: StratzPlayerProfile
    matches: tuple[StratzMatch, ...]
    pages: tuple[StratzHistoryPage, ...]
    raw_pages: tuple[Mapping[str, Any], ...]
    ledger: RequestLedger
    window: HistoryWindow
    fetched_at: str
    operation_name: str
    operation_version: str
    operation_document_sha256: str
    truncated: bool = False
    duplicate_match_count: int = 0

    @property
    def raw_payload_sha256(self) -> str:
        return canonical_json_sha256(list(self.raw_pages))

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile.as_dict(),
            "matches": [match.as_dict() for match in self.matches],
            "pages": [page.as_dict() for page in self.pages],
            "ledger": self.ledger.as_dict(),
            "window": self.window.as_dict(),
            "fetched_at": self.fetched_at,
            "operation_name": self.operation_name,
            "operation_version": self.operation_version,
            "operation_document_sha256": self.operation_document_sha256,
            "truncated": self.truncated,
            "duplicate_match_count": self.duplicate_match_count,
            "raw_payload_sha256": self.raw_payload_sha256,
        }


# Explicit names for callers that prefer the operation's vocabulary.
StratzMatchCore = StratzMatch
StratzHistoryRow = StratzMatch
StratzProfile = StratzPlayerProfile


__all__ = [
    "STRATZ_ENUM_VOCABULARY",
    "STRATZ_PROVIDER",
    "STRATZ_PROVIDER_SCHEMA_VERSION",
    "StratzHistory",
    "StratzHistoryPage",
    "StratzHistoryRow",
    "StratzMatch",
    "StratzMatchCore",
    "StratzMatchPlayer",
    "StratzModelError",
    "StratzPlayerProfile",
    "StratzProfile",
]
