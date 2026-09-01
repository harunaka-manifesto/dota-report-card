"""Versioned STRATZ GraphQL operations used by the V7 provider."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GraphQLOperation:
    name: str
    version: str
    purpose: str
    document: str
    response_model: str

    @property
    def document_sha256(self) -> str:
        return hashlib.sha256(self.document.encode("utf-8")).hexdigest()

    @property
    def digest(self) -> str:
        return self.document_sha256

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "version": self.version,
            "purpose": self.purpose,
            "document_sha256": self.document_sha256,
            "response_model": self.response_model,
        }


GET_PLAYER_PROFILE = GraphQLOperation(
    name="GetPlayerProfile",
    version="1.0.0",
    purpose="Read the public STRATZ profile and privacy state.",
    response_model="StratzPlayerProfile",
    document="""
query GetPlayerProfile($steamAccountId: Long!) {
  player(steamAccountId: $steamAccountId) {
    steamAccountId
    steamAccount {
      id
      name
      avatar
      isAnonymous
      isStratzPublic
    }
  }
}
""".strip(),
)


GET_PLAYER_HISTORY_PAGE = GraphQLOperation(
    name="GetPlayerHistoryPage",
    version="1.0.0",
    purpose="Read one bounded, provider-native player history page.",
    response_model="StratzHistoryPage",
    document="""
query GetPlayerHistoryPage(
  $steamAccountId: Long!
  $startDateTime: Long!
  $endDateTime: Long!
  $take: Int!
  $skip: Int!
) {
  player(steamAccountId: $steamAccountId) {
    steamAccountId
    steamAccount {
      id
      name
      avatar
      isAnonymous
      isStratzPublic
    }
    matches(request: {
      startDateTime: $startDateTime
      endDateTime: $endDateTime
      take: $take
      skip: $skip
    }) {
      id
      didRadiantWin
      durationSeconds
      startDateTime
      endDateTime
      lobbyType
      gameMode
      gameVersionId
      parsedDateTime
      players(steamAccountId: $steamAccountId) {
        steamAccountId
        playerSlot
        isRadiant
        isVictory
        heroId
        variant
        kills
        deaths
        assists
        leaverStatus
        partyId
        lane
        position
        role
      }
    }
  }
}
""".strip(),
)


GET_MATCH_CORE = GraphQLOperation(
    name="GetMatchCore",
    version="1.0.0",
    purpose="Read provider-native match context and player scoreboard rows.",
    response_model="StratzMatchCore",
    document="""
query GetMatchCore($matchId: Long!) {
  match(id: $matchId) {
    id
    didRadiantWin
    durationSeconds
    startDateTime
    endDateTime
    lobbyType
    gameMode
    gameVersionId
    parsedDateTime
    radiantKills
    direKills
    radiantNetworthLeads
    radiantExperienceLeads
    bottomLaneOutcome
    midLaneOutcome
    topLaneOutcome
    players {
      steamAccountId
      playerSlot
      isRadiant
      isVictory
      heroId
      variant
      kills
      deaths
      assists
      leaverStatus
      partyId
      lane
      position
      role
    }
  }
}
""".strip(),
)


GET_PARSED_MATCH_CORE = GraphQLOperation(
    name="GetParsedMatchCore",
    version="1.0.0",
    purpose="Prepared parsed-match hook; not acquired by this foundation phase.",
    response_model="StratzParsedMatchCore",
    document="""
query GetParsedMatchCore($matchId: Long!, $steamAccountId: Long!) {
  match(id: $matchId) {
    id
    durationSeconds
    startDateTime
    gameVersionId
    parsedDateTime
    players(steamAccountId: $steamAccountId) {
      steamAccountId
      heroId
      position
      role
      lane
      stats {
        networthPerMinute
        lastHitsPerMinute
        deniesPerMinute
        heroDamagePerMinute
        killEvents { time }
        deathEvents { time }
        assistEvents { time }
        itemPurchases { time itemId }
      }
    }
  }
}
""".strip(),
)


GET_PARSED_MATCHES_BATCH = GraphQLOperation(
    name="GetParsedMatchesBatch",
    version="1.0.0",
    purpose="Prepared match-id batch hook; not acquired by this foundation phase.",
    response_model="StratzParsedMatchBatch",
    document="""
query GetParsedMatchesBatch($steamAccountId: Long!, $matchIds: [Long!]!) {
  player(steamAccountId: $steamAccountId) {
    matches(request: { matchIds: $matchIds }) {
      id
      durationSeconds
      startDateTime
      gameVersionId
      parsedDateTime
      players(steamAccountId: $steamAccountId) {
        steamAccountId
        heroId
        position
        role
        lane
        stats {
          networthPerMinute
          lastHitsPerMinute
          deniesPerMinute
          heroDamagePerMinute
          killEvents { time }
          deathEvents { time }
          assistEvents { time }
          itemPurchases { time itemId }
        }
      }
    }
  }
}
""".strip(),
)


V7_SCHEMA_SENTINEL = GraphQLOperation(
    name="V7SchemaSentinel",
    version="1.0.0",
    purpose="Confirm the current core STRATZ schema before a live microprobe.",
    response_model="StratzSchemaSentinel",
    document="""
query V7SchemaSentinel {
  match: __type(name: "MatchType") { ...TypeShape }
  matchPlayer: __type(name: "MatchPlayerType") { ...TypeShape }
  playerStats: __type(name: "MatchPlayerStatsType") { ...TypeShape }
  playerPlayback: __type(name: "MatchPlayerPlaybackDataType") { ...TypeShape }
  matchPlayback: __type(name: "MatchPlaybackDataType") { ...TypeShape }
  player: __type(name: "PlayerType") { ...TypeShape }
  matchesRequest: __type(name: "PlayerMatchesRequestType") { ...TypeShape }
}

fragment TypeShape on __Type {
  kind
  name
  enumValues(includeDeprecated: true) { name }
  inputFields { name type { ...TypeRef } }
  fields(includeDeprecated: true) {
    name
    isDeprecated
    args { name type { ...TypeRef } }
    type { ...TypeRef }
  }
}

fragment TypeRef on __Type {
  kind
  name
  ofType {
    kind
    name
    ofType {
      kind
      name
      ofType { kind name }
    }
  }
}
""".strip(),
)


V7_PARSED_SUBTYPE_SHAPE_SENTINEL = GraphQLOperation(
    name="V7ParsedSubtypeShapeSentinel",
    version="1.0.0",
    purpose="Resolve shallow parsed evidence subtype shapes before detail selection.",
    response_model="StratzParsedSubtypeShapeSentinel",
    document="""
query V7ParsedSubtypeShapeSentinel {
  laneReport: __type(name: "MatchStatsLaneReportType") { ...Shape }
  towerDeath: __type(name: "MatchStatsTowerDeathType") { ...Shape }
  pickBan: __type(name: "MatchStatsPickBanType") { ...Shape }
  farmDistribution: __type(name: "MatchPlayerStatsFarmDistributionReportType") { ...Shape }
  locationReport: __type(name: "MatchPlayerStatsLocationReportType") { ...Shape }
  actionReport: __type(name: "MatchPlayerStatsActionReportType") { ...Shape }
  heroDamageReport: __type(name: "MatchPlayerStatsHeroDamageReportType") { ...Shape }
  abilityCastReport: __type(name: "MatchPlayerStatsAbilityCastReportType") { ...Shape }
  inventoryReport: __type(name: "MatchPlayerInventoryType") { ...Shape }
  killEvent: __type(name: "MatchPlayerStatsKillEventType") { ...Shape }
  deathEvent: __type(name: "MatchPlayerStatsDeathEventType") { ...Shape }
  assistEvent: __type(name: "MatchPlayerStatsAssistEventType") { ...Shape }
  wardEvent: __type(name: "MatchPlayerStatsWardEventType") { ...Shape }
  wardDestruction: __type(name: "MatchPlayerWardDestuctionObjectType") { ...Shape }
  itemPurchase: __type(name: "MatchPlayerItemPurchaseEventType") { ...Shape }
  itemUsed: __type(name: "MatchPlayerStatsItemUsedEventType") { ...Shape }
  buffEvent: __type(name: "MatchPlayerStatsBuffEventType") { ...Shape }
  courierKill: __type(name: "MatchPlayerStatsCourierKillEventType") { ...Shape }
  runeEvent: __type(name: "MatchPlayerStatsRuneEventType") { ...Shape }
  eLane: __type(name: "MatchLaneType") { ...EnumShape }
  ePosition: __type(name: "MatchPlayerPositionType") { ...EnumShape }
  eRole: __type(name: "MatchPlayerRoleType") { ...EnumShape }
  eLaneOut: __type(name: "LaneOutcomeEnums") { ...EnumShape }
  eLeaver: __type(name: "LeaverStatusEnum") { ...EnumShape }
  eLobby: __type(name: "LobbyTypeEnum") { ...EnumShape }
  eMode: __type(name: "GameModeEnumType") { ...EnumShape }
  eRune: __type(name: "RuneTypeEnum") { ...EnumShape }
}

fragment Shape on __Type {
  name
  kind
  fields(includeDeprecated: true) {
    name
    isDeprecated
    type { kind name ofType { kind name ofType { kind name } } }
  }
}

fragment EnumShape on __Type {
  name
  kind
  enumValues(includeDeprecated: true) { name }
}
""".strip(),
)


PROBE_PARSED_EVIDENCE_BATCH = GraphQLOperation(
    name="ProbeParsedEvidenceBatch",
    version="1.0.0",
    purpose="Measure the bounded parsed evidence selection at 4, 8, and 16 matches.",
    response_model="StratzParsedEvidenceBatch",
    document="""
query ProbeParsedEvidenceBatch($accountId: Long!, $matchIds: [Long!]!) {
  player(steamAccountId: $accountId) {
    matches(request: { matchIds: $matchIds }) {
      id
      durationSeconds
      startDateTime
      endDateTime
      didRadiantWin
      gameMode
      lobbyType
      gameVersionId
      parsedDateTime
      players(steamAccountId: $accountId) {
        steamAccountId
        playerSlot
        isRadiant
        isVictory
        heroId
        position
        role
        lane
        kills
        deaths
        assists
        stats {
          networthPerMinute
          goldPerMinute
          experiencePerMinute
          lastHitsPerMinute
          deniesPerMinute
          heroDamagePerMinute
          heroDamageReceivedPerMinute
          actionsPerMinute
          tripsFountainPerMinute
          killEvents { time }
          deathEvents { time }
          assistEvents { time }
          itemPurchases { time itemId }
          wards { time type positionX positionY }
          runes { time rune }
        }
      }
    }
  }
}
""".strip(),
)


PROBE_PARSED_CORE_BATCH_FALLBACK = GraphQLOperation(
    name="ProbeParsedCoreBatchFallback",
    version="1.0.0",
    purpose="Measure a reduced parsed core selection after a full selection complexity failure.",
    response_model="StratzParsedCoreBatch",
    document="""
query ProbeParsedCoreBatchFallback($accountId: Long!, $matchIds: [Long!]!) {
  player(steamAccountId: $accountId) {
    matches(request: { matchIds: $matchIds }) {
      id
      durationSeconds
      startDateTime
      gameVersionId
      parsedDateTime
      players(steamAccountId: $accountId) {
        heroId
        position
        role
        lane
        stats {
          networthPerMinute
          experiencePerMinute
          killEvents { time }
          deathEvents { time }
          assistEvents { time }
          itemPurchases { time itemId }
        }
      }
    }
  }
}
""".strip(),
)


FIND_SHORT_PARSED_TRAJECTORY = GraphQLOperation(
    name="FindShortParsedTrajectory",
    version="1.0.0",
    purpose="Find a short parsed match to distinguish level-array length semantics.",
    response_model="StratzShortParsedTrajectoryIndex",
    document="""
query FindShortParsedTrajectory(
  $accountId: Long!
  $startDateTime: Long!
  $endDateTime: Long!
) {
  player(steamAccountId: $accountId) {
    matches(request: {
      startDateTime: $startDateTime
      endDateTime: $endDateTime
      isParsed: true
      take: 100
      skip: 0
    }) {
      id
      durationSeconds
      parsedDateTime
      players(steamAccountId: $accountId) {
        heroId
        position
        role
        lane
        level
      }
    }
  }
}
""".strip(),
)


GET_SHORT_PARSED_TRAJECTORY = GraphQLOperation(
    name="GetShortParsedTrajectory",
    version="1.0.0",
    purpose="Read one selected short parsed trajectory for semantic contrast only.",
    response_model="StratzShortParsedTrajectory",
    document="""
query GetShortParsedTrajectory($accountId: Long!, $matchId: Long!) {
  match(id: $matchId) {
    id
    durationSeconds
    parsedDateTime
    gameVersionId
    players(steamAccountId: $accountId) {
      heroId
      position
      role
      lane
      level
      stats {
        networthPerMinute
        experiencePerMinute
        level
      }
    }
  }
}
""".strip(),
)


PROBE_PARSED_AVAILABILITY = GraphQLOperation(
    name="ProbeParsedAvailability",
    version="1.0.0",
    purpose="Spot-check parsed versus unfiltered ranked and Turbo first-page availability.",
    response_model="StratzParsedAvailability",
    document="""
query ProbeParsedAvailability(
  $accountId: Long!
  $startDateTime: Long!
  $endDateTime: Long!
) {
  player(steamAccountId: $accountId) {
    allRanked: matches(request: {
      startDateTime: $startDateTime
      endDateTime: $endDateTime
      gameModeIds: [22]
      take: 100
      skip: 0
    }) { id parsedDateTime }
    parsedRanked: matches(request: {
      startDateTime: $startDateTime
      endDateTime: $endDateTime
      gameModeIds: [22]
      isParsed: true
      take: 100
      skip: 0
    }) { id parsedDateTime }
    allTurbo: matches(request: {
      startDateTime: $startDateTime
      endDateTime: $endDateTime
      gameModeIds: [23]
      take: 100
      skip: 0
    }) { id parsedDateTime }
    parsedTurbo: matches(request: {
      startDateTime: $startDateTime
      endDateTime: $endDateTime
      gameModeIds: [23]
      isParsed: true
      take: 100
      skip: 0
    }) { id parsedDateTime }
  }
}
""".strip(),
)


STRATZ_OPERATIONS = {
    operation.name: operation
    for operation in (
        GET_PLAYER_PROFILE,
        GET_PLAYER_HISTORY_PAGE,
        GET_MATCH_CORE,
        GET_PARSED_MATCH_CORE,
        GET_PARSED_MATCHES_BATCH,
        V7_SCHEMA_SENTINEL,
        V7_PARSED_SUBTYPE_SHAPE_SENTINEL,
        PROBE_PARSED_EVIDENCE_BATCH,
        PROBE_PARSED_CORE_BATCH_FALLBACK,
        FIND_SHORT_PARSED_TRAJECTORY,
        GET_SHORT_PARSED_TRAJECTORY,
        PROBE_PARSED_AVAILABILITY,
    )
}


def get_operation(name: str) -> GraphQLOperation:
    try:
        return STRATZ_OPERATIONS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown STRATZ operation: {name}") from exc


__all__ = [
    "GET_MATCH_CORE",
    "GET_PARSED_MATCH_CORE",
    "GET_PARSED_MATCHES_BATCH",
    "GET_PLAYER_HISTORY_PAGE",
    "GET_PLAYER_PROFILE",
    "FIND_SHORT_PARSED_TRAJECTORY",
    "GET_SHORT_PARSED_TRAJECTORY",
    "PROBE_PARSED_AVAILABILITY",
    "PROBE_PARSED_CORE_BATCH_FALLBACK",
    "PROBE_PARSED_EVIDENCE_BATCH",
    "V7_PARSED_SUBTYPE_SHAPE_SENTINEL",
    "V7_SCHEMA_SENTINEL",
    "GraphQLOperation",
    "STRATZ_OPERATIONS",
    "get_operation",
]
