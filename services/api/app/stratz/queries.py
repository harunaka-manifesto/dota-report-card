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


GET_PARSED_ACQUISITION_BATCH = GraphQLOperation(
    name="GetParsedAcquisitionBatch",
    version="1.0.0",
    purpose=(
        "Acquire the minimum parsed evidence for candidate-test work and the "
        "research-only item-signature candidate."
    ),
    response_model="StratzParsedAcquisitionBatch",
    document="""
query GetParsedAcquisitionBatch($steamAccountId: Long!, $matchIds: [Long!]!) {
  player(steamAccountId: $steamAccountId) {
    matches(request: { matchIds: $matchIds }) {
      id
      durationSeconds
      startDateTime
      endDateTime
      didRadiantWin
      gameVersionId
      parsedDateTime
      radiantKills
      direKills
      radiantNetworthLeads
      bottomLaneOutcome
      midLaneOutcome
      topLaneOutcome
      players(steamAccountId: $steamAccountId) {
        steamAccountId
        isRadiant
        isVictory
        heroId
        position
        role
        lane
        stats {
          killEvents { time }
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



# ---------------------------------------------------------------------------
# V7 pass-2 operations.
#
# Pass 1 acquired kill/assist/item timings and the match-level net-worth lead.
# Pass 2 adds what the report narrative actually needs: death timings, the
# per-minute trajectories, wards, runes, and a scalars-only projection of the
# other nine players.
#
# Deliberately absent, and they must stay absent: imp, award, behavior,
# intentionalFeeding, streakPrediction, actualRank, averageRank, averageImp,
# rank, bracket, analysisOutcome, predictedOutcomeWeight, winRates,
# predictedWinRates, chatEvents, allTalks, chatWheels, playbackData at either
# level, and the steamAccount identity block for players other than the
# sampled one. A field that is not requested cannot leak.
# ---------------------------------------------------------------------------


GET_DEEP_MATCH_BATCH = GraphQLOperation(
    name="GetDeepMatchBatch",
    version="3.4.0",
    purpose=(
        "Pass-2 production acquisition: own-player full parsed detail, match "
        "context, and a scalars-only projection of all ten players. Finalised "
        "against the first- and second-level shapes measured by the 2026-09-04 "
        "sizing probes."
    ),
    response_model="StratzDeepMatchBatch",
    document="""
query GetDeepMatchBatch($steamAccountId: Long!, $matchIds: [Long!]!) {
  player(steamAccountId: $steamAccountId) {
    matches(request: { matchIds: $matchIds }) {
      id
      didRadiantWin
      durationSeconds
      startDateTime
      endDateTime
      gameMode
      lobbyType
      gameVersionId
      regionId
      parsedDateTime
      statsDateTime
      isStats
      numHumanPlayers
      firstBloodTime
      towerStatusRadiant
      towerStatusDire
      barracksStatusRadiant
      barracksStatusDire
      radiantKills
      direKills
      radiantNetworthLeads
      radiantExperienceLeads
      bottomLaneOutcome
      midLaneOutcome
      topLaneOutcome
      towerDeaths {
        time
        isRadiant
        npcId
        attacker
      }
      pickBans {
        isPick
        isRadiant
        heroId
        bannedHeroId
        order
        playerIndex
        isCaptain
        wasBannedSuccessfully
      }
      allPlayers: players {
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
        numLastHits
        numDenies
        goldPerMinute
        experiencePerMinute
        networth
        heroDamage
        towerDamage
        heroHealing
      }
      players(steamAccountId: $steamAccountId) {
        steamAccountId
        playerSlot
        isRadiant
        isVictory
        heroId
        variant
        position
        role
        lane
        leaverStatus
        isRandom
        partyId
        invisibleSeconds
        kills
        deaths
        assists
        numLastHits
        numDenies
        goldPerMinute
        experiencePerMinute
        networth
        level
        gold
        goldSpent
        heroDamage
        towerDamage
        heroHealing
        item0Id
        item1Id
        item2Id
        item3Id
        item4Id
        item5Id
        backpack0Id
        backpack1Id
        backpack2Id
        neutral0Id
        abilities {
          abilityId
          level
          time
          isTalent
        }
        stats {
          networthPerMinute
          goldPerMinute
          experiencePerMinute
          lastHitsPerMinute
          deniesPerMinute
          heroDamagePerMinute
          heroDamageReceivedPerMinute
          towerDamagePerMinute
          healPerMinute
          campStack
          level
          actionsPerMinute
          tripsFountainPerMinute
          itemUsed {
            itemId
            count
          }
          wardDestruction {
            time
            isWard
            gold
            experience
          }
          matchPlayerBuffEvent {
            time
            itemId
            abilityId
            stackCount
          }
          farmDistributionReport {
            buyBackGold
            abandonGold
            creepLocation {
              id
              count
              gold
              xp
            }
            neutralLocation {
              id
              count
              gold
              xp
            }
          }
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


GET_ROLE_METRIC_MATCH_BATCH = GraphQLOperation(
    name="GetRoleMetricMatchBatch",
    version="1.0.0",
    purpose=(
        "Progression-only acquisition: player healing, camp-stack trajectory, "
        "credited team kill timestamps, and specific player tower damage. This "
        "is separate from the frozen V7 report-card query."
    ),
    response_model="StratzRoleMetricMatchBatch",
    document="""
query GetRoleMetricMatchBatch($steamAccountId: Long!, $matchIds: [Long!]!) {
  player(steamAccountId: $steamAccountId) {
    matches(request: { matchIds: $matchIds }) {
      id
      durationSeconds
      startDateTime
      endDateTime
      gameMode
      lobbyType
      towerDeaths {
        time
        isRadiant
        npcId
      }
      allPlayers: players {
        playerSlot
        isRadiant
        kills
        assists
        stats {
          killEvents { time }
        }
      }
      players(steamAccountId: $steamAccountId) {
        playerSlot
        isRadiant
        position
        role
        lane
        leaverStatus
        kills
        assists
        heroHealing
        stats {
          campStack
          killEvents { time }
          assistEvents { time }
          towerDamageReport {
            npcId
            damage
          }
        }
      }
    }
  }
}
""".strip(),
)


PROBE_LOCATION_REPORT = GraphQLOperation(
    name="ProbeLocationReport",
    version="1.0.0",
    purpose=(
        "Establish the shape and complexity cost of stats.locationReport, the "
        "only route to a map-position answer that does not touch playback."
    ),
    response_model="StratzLocationReportProbe",
    document="""
query ProbeLocationReport($steamAccountId: Long!, $matchIds: [Long!]!) {
  player(steamAccountId: $steamAccountId) {
    matches(request: { matchIds: $matchIds }) {
      id
      durationSeconds
      players(steamAccountId: $steamAccountId) {
        heroId
        position
        stats {
          locationReport
        }
      }
    }
  }
}
""".strip(),
)


PROBE_ITEM_VOCABULARY = GraphQLOperation(
    name="ProbeItemVocabulary",
    version="1.0.0",
    purpose=(
        "Static reference data: item id to name and cost, so an item-timing "
        "Finding can tell a consumable from a real item."
    ),
    response_model="StratzItemVocabulary",
    document="""
query ProbeItemVocabulary {
  constants {
    items {
      id
      displayName
      shortName
      stat {
        cost
        isSideShop
      }
    }
  }
}
""".strip(),
)


GET_PLAYER_RANK_HISTORY = GraphQLOperation(
    name="GetPlayerRankHistory",
    version="1.0.0",
    purpose=(
        "DISPLAY ONLY. Rank progression for the history section of the report. "
        "This operation's output must never reach a canonical research table, a "
        "derived feature, a context projection, or a cohort filter; it is stored "
        "in a separate display-only table that the research reader cannot return."
    ),
    response_model="StratzPlayerRankHistory",
    document="""
query GetPlayerRankHistory($steamAccountId: Long!) {
  player(steamAccountId: $steamAccountId) {
    steamAccountId
    ranks {
      seasonRankId
      asOfDateTime
      isCore
      rank
    }
  }
}
""".strip(),
)



V7_PASS2_TYPE_SENTINEL = GraphQLOperation(
    name="V7Pass2TypeSentinel",
    version="1.0.0",
    purpose=(
        "Learn the field shape of the object and list types the pass-2 query "
        "cannot yet select from. A GraphQL selection set cannot be written "
        "against an unknown type, and guessing one costs a failed collection."
    ),
    response_model="StratzPass2TypeSentinel",
    document="""
query V7Pass2TypeSentinel {
  towerDeath: __type(name: "MatchStatsTowerDeathType") { ...Shape }
  pickBan: __type(name: "MatchStatsPickBanType") { ...Shape }
  laneReport: __type(name: "MatchStatsLaneReportType") { ...Shape }
  towerStatus: __type(name: "MatchStatsTowerReportType") { ...Shape }
  playerAbility: __type(name: "PlayerAbilityType") { ...Shape }
  itemUsed: __type(name: "MatchPlayerStatsItemUsedEventType") { ...Shape }
  wardDestruction: __type(name: "MatchPlayerWardDestuctionObjectType") { ...Shape }
  farmDistribution: __type(name: "MatchPlayerStatsFarmDistributionReportType") { ...Shape }
  heroDamageReport: __type(name: "MatchPlayerStatsHeroDamageReportType") { ...Shape }
  towerDamageReport: __type(name: "MatchPlayerStatsTowerDamageReportType") { ...Shape }
  inventoryReport: __type(name: "MatchPlayerInventoryType") { ...Shape }
  actionReport: __type(name: "MatchPlayerStatsActionReportType") { ...Shape }
  abilityCastReport: __type(name: "MatchPlayerStatsAbilityCastReportType") { ...Shape }
  locationReport: __type(name: "MatchPlayerStatsLocationReportType") { ...Shape }
  buffEvent: __type(name: "MatchPlayerStatsBuffEventType") { ...Shape }
  courierKill: __type(name: "MatchPlayerStatsCourierKillEventType") { ...Shape }
}

fragment Shape on __Type {
  kind
  name
  fields(includeDeprecated: true) {
    name
    isDeprecated
    type { kind name ofType { kind name ofType { kind name } } }
  }
}
""".strip(),
)



V7_PASS2_NESTED_TYPE_SENTINEL = GraphQLOperation(
    name="V7Pass2NestedTypeSentinel",
    version="1.0.0",
    purpose=(
        "Resolve the second-level object types the first sentinel left "
        "unresolved. These are the only remaining fields that could force a "
        "second deep collection, so they are settled before the first one runs."
    ),
    response_model="StratzPass2NestedTypeSentinel",
    document="""
query V7Pass2NestedTypeSentinel {
  farmDistributionObject: __type(name: "MatchPlayerStatsFarmDistributionObjectType") { ...Shape }
  laneReportFaction: __type(name: "MatchStatsLaneReportFactionObjectType") { ...Shape }
  inventoryObject: __type(name: "MatchPlayerInventoryObjectType") { ...Shape }
  towerReportObject: __type(name: "MatchStatsTowerReportObjectType") { ...Shape }
  outpostReportObject: __type(name: "MatchStatsOutpostReportObjectType") { ...Shape }
  abilityCastObject: __type(name: "MatchPlayerStatsAbilityCastObjectType") { ...Shape }
  damageSourceAbility: __type(name: "MatchPlayerHeroDamageSourceAbilityReportObjectType") { ...Shape }
  damageSourceItem: __type(name: "MatchPlayerHeroDamageSourceItemReportObjectType") { ...Shape }
  damageTargets: __type(name: "MatchPlayerHeroDamageTargetReportObjectType") { ...Shape }
  damageTotal: __type(name: "MatchPlayerHeroDamageTotalReportObjectType") { ...Shape }
  damageTotalReceived: __type(name: "MatchPlayerHeroDamageTotalRecievedReportObjectType") { ...Shape }
}

fragment Shape on __Type {
  kind
  name
  fields(includeDeprecated: true) {
    name
    isDeprecated
    type { kind name ofType { kind name ofType { kind name } } }
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
        GET_PARSED_ACQUISITION_BATCH,
        V7_SCHEMA_SENTINEL,
        V7_PARSED_SUBTYPE_SHAPE_SENTINEL,
        PROBE_PARSED_EVIDENCE_BATCH,
        PROBE_PARSED_CORE_BATCH_FALLBACK,
        FIND_SHORT_PARSED_TRAJECTORY,
        GET_SHORT_PARSED_TRAJECTORY,
        PROBE_PARSED_AVAILABILITY,
        GET_DEEP_MATCH_BATCH,
        GET_ROLE_METRIC_MATCH_BATCH,
        PROBE_LOCATION_REPORT,
        PROBE_ITEM_VOCABULARY,
        GET_PLAYER_RANK_HISTORY,
        V7_PASS2_TYPE_SENTINEL,
        V7_PASS2_NESTED_TYPE_SENTINEL,
    )
}


def get_operation(name: str) -> GraphQLOperation:
    try:
        return STRATZ_OPERATIONS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown STRATZ operation: {name}") from exc


__all__ = [
    "GET_DEEP_MATCH_BATCH",
    "GET_ROLE_METRIC_MATCH_BATCH",
    "GET_MATCH_CORE",
    "GET_PARSED_MATCH_CORE",
    "GET_PARSED_ACQUISITION_BATCH",
    "GET_PARSED_MATCHES_BATCH",
    "GET_PLAYER_HISTORY_PAGE",
    "GET_PLAYER_PROFILE",
    "FIND_SHORT_PARSED_TRAJECTORY",
    "GET_SHORT_PARSED_TRAJECTORY",
    "PROBE_PARSED_AVAILABILITY",
    "PROBE_PARSED_CORE_BATCH_FALLBACK",
    "GET_PLAYER_RANK_HISTORY",
    "PROBE_ITEM_VOCABULARY",
    "PROBE_LOCATION_REPORT",
    "PROBE_PARSED_EVIDENCE_BATCH",
    "V7_PARSED_SUBTYPE_SHAPE_SENTINEL",
    "V7_PASS2_NESTED_TYPE_SENTINEL",
    "V7_PASS2_TYPE_SENTINEL",
    "V7_SCHEMA_SENTINEL",
    "GraphQLOperation",
    "STRATZ_OPERATIONS",
    "get_operation",
]
