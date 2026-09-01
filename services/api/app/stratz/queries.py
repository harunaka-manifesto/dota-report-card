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


STRATZ_OPERATIONS = {
    operation.name: operation
    for operation in (
        GET_PLAYER_PROFILE,
        GET_PLAYER_HISTORY_PAGE,
        GET_MATCH_CORE,
        GET_PARSED_MATCH_CORE,
        GET_PARSED_MATCHES_BATCH,
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
    "GraphQLOperation",
    "STRATZ_OPERATIONS",
    "get_operation",
]
