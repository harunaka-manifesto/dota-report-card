"""Strict, additive schema for the Free DNA V6.1 story payload.

The legacy V6.1 report is deliberately left in ``report_schemas_v61``.  This
module only describes the optional descriptive projection.  A missing
``story_payload`` therefore remains a valid historical report.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import Field, model_validator

from app.api.report_schemas_v6 import PublicV6Model
from app.player_analysis_v61.story_selector import MODE_MAP_SHA256
from app.player_analysis_v61.versions import (
    STORY_ARCHETYPE_CONTRACT_VERSION,
    STORY_COPY_VERSION,
    STORY_HERO_METADATA_VERSION,
    STORY_HERO_TAXONOMY_VERSION,
    STORY_MODE_MAP_VERSION,
    STORY_PAYLOAD_VERSION,
    STORY_RULES_VERSION,
    StoryArchetypeContractVersion,
    StoryCopyVersion,
    StoryHeroMetadataVersion,
    StoryHeroTaxonomyVersion,
    StoryModeMapVersion,
    StoryPayloadVersion,
    StoryRulesVersion,
)

StoryState = Literal["available", "degraded", "omitted", "not_ready"]
StoryOutcome = Literal["win", "loss"]
StoryFindingFamily = Literal["post_loss_response", "transfer"]
StoryModuleKey = Literal[
    "hello",
    "match_count",
    "hours_in_matches",
    "rank_points",
    "busiest_week",
    "busiest_day",
    "longest_match",
    "wins_bridge",
    "win_summary",
    "winning_streak",
    "top_win_heroes",
    "losing_streak",
    "top_loss_heroes",
    "hero_pool",
    "hero_eras",
    "hero_era_payoff",
    "kills",
    "assists",
    "deaths",
    "element_distinctiveness",
    "archetype",
    "card_collage",
    "final_identity_card",
    "deep",
]
StoryCardModuleKey = Literal[
    "hello",
    "match_count",
    "hours_in_matches",
    "rank_points",
    "busiest_week",
    "busiest_day",
    "longest_match",
    "wins_bridge",
    "win_summary",
    "winning_streak",
    "top_win_heroes",
    "losing_streak",
    "top_loss_heroes",
    "hero_pool",
    "hero_eras",
    "hero_era_payoff",
    "kills",
    "assists",
    "deaths",
    "element_distinctiveness",
    "archetype",
    "card_collage",
    "final_identity_card",
    "deep",
    "post_loss",
    "transfer",
]

STORY_RANK_POINTS_VERSION = "rank-points-story-1.0.0"
STORY_CARD_VERSION = "free-story-cards-1.0.0"

STORY_MODULE_KEYS = (
    "hello",
    "match_count",
    "hours_in_matches",
    "rank_points",
    "busiest_week",
    "busiest_day",
    "longest_match",
    "wins_bridge",
    "win_summary",
    "winning_streak",
    "top_win_heroes",
    "losing_streak",
    "top_loss_heroes",
    "hero_pool",
    "hero_eras",
    "hero_era_payoff",
    "kills",
    "assists",
    "deaths",
    "element_distinctiveness",
    "archetype",
    "card_collage",
    "final_identity_card",
    "deep",
)

# The module/page relationship is intentionally descriptive.  A few reviewed
# page numbers are bridges owned by the frontend, so the schema only maps
# pages whose module ownership is fixed by the backend contract.
STORY_MODULE_PAGES: dict[str, int] = {
    "hello": 1,
    "match_count": 2,
    "hours_in_matches": 3,
    "rank_points": 4,
    "busiest_week": 5,
    "busiest_day": 6,
    "longest_match": 7,
    "wins_bridge": 8,
    "win_summary": 9,
    "winning_streak": 10,
    "top_win_heroes": 11,
    "losing_streak": 12,
    "top_loss_heroes": 13,
    "hero_pool": 17,
    "hero_eras": 18,
    "hero_era_payoff": 19,
    "kills": 22,
    "assists": 23,
    "deaths": 24,
    "element_distinctiveness": 28,
    "archetype": 29,
    "card_collage": 32,
    "final_identity_card": 33,
    "deep": 34,
    "post_loss": 15,
    "transfer": 21,
}

_FORBIDDEN_STORY_KEYS = frozenset(
    {
        "account_id",
        "player_id",
        "steam_id",
        "steamid",
        "steam_id64",
        "match_id",
        "match_ids",
        "session_id",
        "session_ids",
        "cohort_reference",
        "protected_cohort_reference",
        "raw_cohort_reference",
        "rank_tier",
        "average_rank",
        "mmr",
        "mmr_bucket",
        "username",
        "user_name",
        "personaname",
        "persona_name",
        "deep_handoff",
    }
)
_PAGE_25_RE = re.compile(r"(?:^|[^a-z])page[-_ ]?25(?:$|[^0-9])", re.IGNORECASE)
_DEATH_CONTEXT_RE = re.compile(r"death[-_ ]context", re.IGNORECASE)
_PRIVATE_STORY_KEY_TOKENS = frozenset(
    re.sub(r"[^a-z0-9]", "", key) for key in _FORBIDDEN_STORY_KEYS
)


def validate_story_privacy(value: Any) -> None:
    """Reject private identifiers and the explicitly removed Death Context.

    The existing V6.1 privacy validator remains the owner of the legacy
    report surface.  This stricter walker is scoped to the additive story
    projection, where opaque cohort references are not part of the contract.
    """

    def walk(item: Any, path: str = "story_payload") -> None:
        if isinstance(item, Mapping):
            for key, nested in item.items():
                folded = str(key).casefold()
                normalized = re.sub(r"[^a-z0-9]", "", folded)
                if folded in _FORBIDDEN_STORY_KEYS or normalized in _PRIVATE_STORY_KEY_TOKENS:
                    raise ValueError(f"story payload contains a private key at {path}.{key}")
                if _DEATH_CONTEXT_RE.search(folded):
                    raise ValueError(f"story payload cannot contain Death Context at {path}.{key}")
                if folded in {"page_25", "page-25", "page25"} or _PAGE_25_RE.search(folded):
                    raise ValueError(f"story payload cannot contain Page 25 at {path}.{key}")
                walk(nested, f"{path}.{key}")
        elif isinstance(item, list):
            for index, nested in enumerate(item):
                walk(nested, f"{path}[{index}]")
        elif isinstance(item, str):
            if _DEATH_CONTEXT_RE.search(item):
                raise ValueError(f"story payload cannot contain Death Context at {path}")
            if _PAGE_25_RE.search(item):
                raise ValueError(f"story payload cannot contain Page 25 at {path}")

    walk(value)


class StoryAvailabilityV61Schema(PublicV6Model):
    state: Literal["available", "degraded"]
    reason: str | None = None

    @model_validator(mode="after")
    def reason_matches_state(self) -> StoryAvailabilityV61Schema:
        if self.state == "available" and self.reason is not None:
            raise ValueError("available story payloads cannot carry an omission reason")
        if self.state == "degraded" and not self.reason:
            raise ValueError("degraded story payloads require a reason")
        return self


class StoryProvenanceV61Schema(PublicV6Model):
    provider: Literal["opendota_summary"]
    physical_history_requests: Literal[1]
    detail_requests: Literal[0]
    parse_requests: Literal[0]
    mode_map_version: StoryModeMapVersion
    mode_map_checksum: str
    hero_taxonomy_version: StoryHeroTaxonomyVersion
    hero_taxonomy_factual_checksum: str
    hero_taxonomy_editorial_checksum: str
    hero_metadata_version: StoryHeroMetadataVersion
    story_input_sha256: str

    @model_validator(mode="after")
    def checksums_are_source_bound(self) -> StoryProvenanceV61Schema:
        if self.mode_map_checksum != MODE_MAP_SHA256:
            raise ValueError("story mode map checksum does not match the pinned artifact")
        digests = {
            "story input": self.story_input_sha256,
            "hero taxonomy factual": self.hero_taxonomy_factual_checksum,
            "hero taxonomy editorial": self.hero_taxonomy_editorial_checksum,
        }
        for label, digest in digests.items():
            if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise ValueError(f"{label} must be a lowercase 64-character SHA-256 digest")
        return self


class StoryModeCountsV61Schema(PublicV6Model):
    unranked_all_pick: int = Field(ge=0)
    ranked_all_pick: int = Field(ge=0)
    unranked_captains_mode: int = Field(ge=0)
    ranked_captains_mode: int = Field(ge=0)


class StoryUniverseV61Schema(PublicV6Model):
    key: Literal["public_ap_cm_story_v1"]
    requested_window_days: Literal[365]
    window_start: str
    window_end: str
    observed_from: str
    observed_to: str
    observed_days: int = Field(ge=0)
    history_materially_short: bool
    match_count: int = Field(ge=30)
    volume_tier: Literal["limited", "normal"]
    mode_counts: StoryModeCountsV61Schema
    excluded_or_unknown_count: int = Field(ge=0)
    duration_candidate_count: int = Field(ge=0)
    duration_known_count: int = Field(ge=0)
    duration_coverage: float = Field(ge=0, le=1)
    history_completeness: Literal["complete", "possibly_truncated", "unknown"]

    @model_validator(mode="after")
    def counts_are_consistent(self) -> StoryUniverseV61Schema:
        supported = sum(self.mode_counts.model_dump().values())
        if supported != self.match_count:
            raise ValueError("story mode counts must sum to the story match count")
        if self.duration_known_count > self.duration_candidate_count:
            raise ValueError("known durations cannot exceed duration candidates")
        if self.duration_candidate_count > self.match_count:
            raise ValueError("duration candidates cannot exceed story matches")
        expected_coverage = (
            self.duration_known_count / self.duration_candidate_count
            if self.duration_candidate_count
            else 0.0
        )
        if abs(self.duration_coverage - expected_coverage) > 1e-9:
            raise ValueError("story duration coverage does not match its numerator and denominator")
        return self


class StoryIdentityV61Schema(PublicV6Model):
    display_name: str | None = None


class StoryModuleV61Schema(PublicV6Model):
    state: StoryState
    reason: str | None = None
    copy_variant: str | None = None
    data: Any | None = None

    @model_validator(mode="after")
    def state_matches_data(self) -> StoryModuleV61Schema:
        if self.state in {"available", "degraded"} and self.data is None:
            raise ValueError(f"{self.state} story modules require data")
        if self.state == "omitted" and self.data is not None:
            raise ValueError("omitted story modules must have null data")
        if self.state in {"omitted", "not_ready"} and not self.reason:
            raise ValueError(f"{self.state} story modules require a reason")
        if self.state == "available" and self.reason is not None:
            raise ValueError("available story modules cannot carry an omission reason")
        if self.state == "degraded" and not self.reason:
            raise ValueError("degraded story modules require a reason")
        return self


class StoryHelloDataV61Schema(PublicV6Model):
    display_name: str | None = None
    requested_window_days: Literal[365]
    window_start: str
    window_end: str
    observed_from: str
    observed_to: str
    history_materially_short: bool


class StoryMatchCountDataV61Schema(PublicV6Model):
    match_count: int = Field(ge=30)
    volume_variant: Literal["limited", "normal"]


class StoryHoursDataV61Schema(PublicV6Model):
    total_duration_seconds: int | None = Field(default=None, ge=0)
    display_value: float | None = Field(default=None, ge=0)
    display_unit: Literal["minutes", "hours"] | None = None
    hours_available: bool
    coverage_numerator: int = Field(ge=0)
    coverage_denominator: int = Field(ge=0)
    coverage_ratio: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_coverage(self) -> StoryHoursDataV61Schema:
        if self.coverage_numerator > self.coverage_denominator:
            raise ValueError("hours coverage numerator cannot exceed denominator")
        expected = self.coverage_numerator / self.coverage_denominator if self.coverage_denominator else 0.0
        if abs(self.coverage_ratio - expected) > 1e-9:
            raise ValueError("hours coverage does not match its numerator and denominator")
        if (self.display_value is None) != (self.display_unit is None):
            raise ValueError("hours display value and unit must be supplied together")
        if not self.hours_available and self.display_value is not None:
            raise ValueError("unavailable hours cannot carry a display value")
        return self


class StoryRankPointsDataV61Schema(PublicV6Model):
    points_absolute: int = Field(ge=0)
    direction: Literal["positive", "negative", "zero"]
    ranked_matches: int = Field(ge=0)
    ranked_wins: int = Field(ge=0)
    ranked_losses: int = Field(ge=0)
    points_per_match: Literal[25]
    classification_reliable: Literal[True]
    formula_version: Literal["rank-points-story-1.0.0"]

    @model_validator(mode="after")
    def formula_is_consistent(self) -> StoryRankPointsDataV61Schema:
        if self.ranked_matches != self.ranked_wins + self.ranked_losses:
            raise ValueError("ranked match count must equal ranked wins plus ranked losses")
        expected = abs((self.ranked_wins - self.ranked_losses) * self.points_per_match)
        if self.points_absolute != expected:
            raise ValueError("rank points do not match the frozen wins/losses formula")
        direction = "positive" if self.ranked_wins > self.ranked_losses else (
            "negative" if self.ranked_wins < self.ranked_losses else "zero"
        )
        if self.direction != direction:
            raise ValueError("rank points direction does not match wins and losses")
        if self.ranked_matches < 10:
            raise ValueError("rank points require at least ten ranked matches")
        return self


class StoryPeriodDurationDataV61Schema(PublicV6Model):
    total_duration_seconds: int | None = Field(default=None, ge=0)
    display_value: float | None = Field(default=None, ge=0)
    display_unit: Literal["minutes", "hours"] | None = None
    hours_available: bool

    @model_validator(mode="after")
    def validate_display(self) -> StoryPeriodDurationDataV61Schema:
        if (self.display_value is None) != (self.display_unit is None):
            raise ValueError("period duration display value and unit must be supplied together")
        if not self.hours_available and self.display_value is not None:
            raise ValueError("unavailable period hours cannot carry a display value")
        return self


class StoryBusiestWeekDataV61Schema(StoryPeriodDurationDataV61Schema):
    period_kind: Literal["iso_calendar_week"]
    date_start: str
    date_end: str
    match_count: int = Field(ge=1)


class StoryBusiestDayDataV61Schema(StoryPeriodDurationDataV61Schema):
    date: str
    match_count: int = Field(ge=3)
    inside_busiest_week: bool
    also_longest_match_day: bool


class StoryLongestMatchDataV61Schema(PublicV6Model):
    duration_seconds: int = Field(ge=0)
    formatted_duration: str = Field(min_length=1)
    hero_id: int = Field(ge=1)
    hero_name: str = Field(min_length=1)
    date: str
    outcome: StoryOutcome
    kills: int | None = Field(default=None, ge=0)
    deaths: int | None = Field(default=None, ge=0)
    assists: int | None = Field(default=None, ge=0)
    refused_to_end: bool
    on_busiest_day: bool


class StoryWinsBridgeDataV61Schema(PublicV6Model):
    wins: int = Field(ge=0)


class StoryWinningestDayV61Schema(PublicV6Model):
    date: str
    daily_wins: int = Field(ge=1)


class StoryWinSummaryDataV61Schema(PublicV6Model):
    wins: int = Field(ge=0)
    winningest_day: StoryWinningestDayV61Schema | None = None


class StoryWinningStreakDataV61Schema(PublicV6Model):
    length: int = Field(ge=1)
    start_date: str
    end_date: str


class StoryWinHeroRowV61Schema(PublicV6Model):
    rank: int = Field(ge=1, le=3)
    hero_id: int = Field(ge=1)
    hero_name: str = Field(min_length=1)
    wins: int = Field(ge=0)
    matches: int = Field(ge=1)


class StoryTopWinHeroesDataV61Schema(PublicV6Model):
    rows: list[StoryWinHeroRowV61Schema] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def rows_are_ranked(self) -> StoryTopWinHeroesDataV61Schema:
        ranks = [row.rank for row in self.rows]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("top win hero rows must have consecutive ranks")
        return self


class StoryBreakerV61Schema(PublicV6Model):
    hero_id: int = Field(ge=1)
    hero_name: str = Field(min_length=1)
    date: str
    outcome: StoryOutcome
    kills: int | None = Field(default=None, ge=0)
    deaths: int | None = Field(default=None, ge=0)
    assists: int | None = Field(default=None, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)


class StoryLosingStreakDataV61Schema(PublicV6Model):
    length: int = Field(ge=1)
    start_date: str
    end_date: str
    terminal_state: Literal["broken_by_win", "observation_ended", "history_boundary"]
    breaker: StoryBreakerV61Schema | None = None

    @model_validator(mode="after")
    def breaker_matches_terminal_state(self) -> StoryLosingStreakDataV61Schema:
        if self.terminal_state == "broken_by_win" and self.breaker is None:
            raise ValueError("a streak broken by a win requires its breaker")
        if self.terminal_state != "broken_by_win" and self.breaker is not None:
            raise ValueError("only a win-broken streak may carry a breaker")
        return self


class StoryLossHeroRowV61Schema(PublicV6Model):
    rank: int = Field(ge=1, le=3)
    hero_id: int = Field(ge=1)
    hero_name: str = Field(min_length=1)
    losses: int = Field(ge=0)
    matches: int = Field(ge=1)


class StoryRoughestDayV61Schema(PublicV6Model):
    date: str
    daily_losses: int = Field(ge=1)


class StoryTopLossHeroesDataV61Schema(PublicV6Model):
    breaker_exists: bool
    rows: list[StoryLossHeroRowV61Schema] = Field(default_factory=list, max_length=3)
    roughest_day: StoryRoughestDayV61Schema | None = None

    @model_validator(mode="after")
    def rows_are_ranked(self) -> StoryTopLossHeroesDataV61Schema:
        ranks = [row.rank for row in self.rows]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("top loss hero rows must have consecutive ranks")
        return self


class StoryPoolHeroRowV61Schema(PublicV6Model):
    rank: int = Field(ge=1, le=5)
    hero_id: int = Field(ge=1)
    hero_name: str = Field(min_length=1)
    matches: int = Field(ge=1)
    share: float = Field(ge=0, le=1)


class StoryHeroPoolDataV61Schema(PublicV6Model):
    heroes: list[StoryPoolHeroRowV61Schema] = Field(default_factory=list, max_length=5)
    total_matches: int = Field(ge=0)
    top_five_share: float = Field(ge=0, le=1)
    concentration_band: Literal["concentrated", "broad"] | None = None

    @model_validator(mode="after")
    def rows_are_ranked(self) -> StoryHeroPoolDataV61Schema:
        ranks = [row.rank for row in self.heroes]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("hero pool rows must have consecutive ranks")
        if not self.heroes and (self.top_five_share != 0 or self.total_matches != 0):
            raise ValueError("an empty hero pool must have zero top-five share")
        if self.heroes and self.total_matches < sum(row.matches for row in self.heroes):
            raise ValueError("hero pool total cannot be less than its displayed rows")
        return self


class StoryEraHeroCountV61Schema(PublicV6Model):
    rank: int = Field(ge=1, le=5)
    hero_id: int = Field(ge=1)
    hero_name: str = Field(min_length=1)
    matches: int = Field(ge=1)


class StoryHeroEraV61Schema(PublicV6Model):
    id: str = Field(min_length=1)
    period_kind: Literal["calendar_month", "third"]
    date_start: str
    date_end: str
    match_count: int = Field(ge=0)
    empty: bool
    sparse: bool
    top_heroes: list[StoryEraHeroCountV61Schema] = Field(max_length=5)

    @model_validator(mode="after")
    def empty_period_has_no_rankings(self) -> StoryHeroEraV61Schema:
        ranks = [row.rank for row in self.top_heroes]
        if self.empty and (self.match_count != 0 or self.top_heroes):
            raise ValueError("empty hero eras cannot carry matches or rankings")
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("hero era rankings must have consecutive ranks")
        return self


class StoryHeroErasDataV61Schema(PublicV6Model):
    periods: list[StoryHeroEraV61Schema] = Field(default_factory=list)
    sparse_fallback: bool
    period_kind: Literal["calendar_month", "third"]


class StoryHeroReferenceV61Schema(PublicV6Model):
    hero_id: int = Field(ge=1)
    hero_name: str = Field(min_length=1)


class StoryEraPersistenceV61Schema(PublicV6Model):
    hero: StoryHeroReferenceV61Schema
    top_five_periods: int = Field(ge=1)


class StoryEraTakeoverV61Schema(PublicV6Model):
    hero: StoryHeroReferenceV61Schema
    period: str = Field(min_length=1)


class StoryHeroEraPayoffDataV61Schema(PublicV6Model):
    persistence: StoryEraPersistenceV61Schema | None = None
    takeover: StoryEraTakeoverV61Schema | None = None
    steady_pool: bool


class StoryCombatLeadingHeroV61Schema(PublicV6Model):
    hero_id: int = Field(ge=1)
    hero_name: str = Field(min_length=1)
    total: int = Field(ge=0)


class StoryCombatRowV61Schema(PublicV6Model):
    rank: int = Field(ge=1, le=3)
    hero_id: int | None = Field(default=None, ge=1)
    hero_name: str | None = None
    date: str | None = None
    outcome: StoryOutcome | None = None
    kills: int | None = Field(default=None, ge=0)
    deaths: int | None = Field(default=None, ge=0)
    assists: int | None = Field(default=None, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)
    stat_value: int | None = Field(default=None, ge=0)


class StoryCombatDataV61Schema(PublicV6Model):
    total: int = Field(ge=0)
    leading_hero: StoryCombatLeadingHeroV61Schema | None = None
    individuals: list[StoryCombatRowV61Schema] = Field(max_length=3)

    @model_validator(mode="after")
    def rows_are_ranked(self) -> StoryCombatDataV61Schema:
        ranks = [row.rank for row in self.individuals]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("combat rows must have consecutive ranks")
        if self.total == 0 and self.leading_hero is not None:
            raise ValueError("zero combat totals cannot have a leading hero")
        return self


class StoryDistinctivenessRowV61Schema(PublicV6Model):
    element_key: str = Field(min_length=1)
    percentile: float = Field(ge=0, le=1)
    extremity_rank: int = Field(ge=1)
    direction: Literal["positive", "negative", "zero"]


class StoryElementDistinctivenessDataV61Schema(PublicV6Model):
    rows: list[StoryDistinctivenessRowV61Schema]
    nothing_meaningfully_stands_out: bool


class StoryArchetypeDataV61Schema(PublicV6Model):
    production_ready: Literal[False]
    name: None = None
    description: None = None
    evidence_anchors: list[None] = Field(default_factory=list, max_length=3)
    recap_available: Literal[False] = False
    share_card_available: Literal[False] = False


class StoryFinalIdentityDataV61Schema(PublicV6Model):
    display_name: str | None = None
    archetype: None = None
    story_match_count: int = Field(ge=30)
    lookback_days: Literal[365]
    window_start: str
    window_end: str
    share_card_available: Literal[False] = False


class StoryDeepDataV61Schema(PublicV6Model):
    available: bool


class StoryCardV61Schema(PublicV6Model):
    id: str = Field(min_length=1)
    module: StoryCardModuleKey
    page: int | None = Field(default=None, ge=1, le=34)

    @model_validator(mode="after")
    def no_removed_page(self) -> StoryCardV61Schema:
        if self.page == 25:
            raise ValueError("story cards cannot reference Page 25")
        if self.module in STORY_MODULE_PAGES and self.page is not None:
            expected_page = STORY_MODULE_PAGES[self.module]
            if self.page != expected_page:
                raise ValueError("story card page must match its module")
        return self


class StoryCardCollageDataV61Schema(PublicV6Model):
    version: Literal["free-story-cards-1.0.0"]
    cards: list[StoryCardV61Schema] = Field(default_factory=list)


class StoryFindingClaimContractV61Schema(PublicV6Model):
    """Public claim projection without the protected Deep handoff."""

    claim: str | None = None
    evidence: str | None = None
    interpretation: str | None = None
    recommendation: dict[str, Any] | None = None
    alternatives: list[str] = Field(default_factory=list)
    verification: dict[str, Any] | None = None
    interaction: str | None = None
    copy_version: str | None = None


class StoryFindingContentV61Schema(PublicV6Model):
    family: StoryFindingFamily
    claim: str | None = None
    interpretation: str | None = None
    claim_contract: StoryFindingClaimContractV61Schema | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: Literal["unavailable", "descriptive", "moderate", "high"] = "unavailable"
    semantic_outcome_key: str | None = None
    comparable_opportunities: int | None = Field(default=None, ge=0)
    cross_session_transitions: Literal[False] = False


class StoryFindingSlotV61Schema(PublicV6Model):
    available: bool
    family: StoryFindingFamily
    content: StoryFindingContentV61Schema | None = None

    @model_validator(mode="after")
    def content_matches_availability(self) -> StoryFindingSlotV61Schema:
        if self.available:
            if self.content is None:
                raise ValueError("available story finding slots require content")
            if self.content.family != self.family:
                raise ValueError("story finding content must match its slot family")
            if (
                not self.content.claim
                or not self.content.interpretation
                or self.content.claim_contract is None
            ):
                raise ValueError(
                    "available story findings require claim, interpretation, and claim contract"
                )
            if self.family == "post_loss_response" and self.content.comparable_opportunities is None:
                raise ValueError("Post-Loss story content requires comparable opportunities")
        elif self.content is not None:
            raise ValueError("unavailable story finding slots must have null content")
        return self


class StoryFindingSlotsV61Schema(PublicV6Model):
    post_loss: StoryFindingSlotV61Schema
    transfer: StoryFindingSlotV61Schema

    @model_validator(mode="after")
    def slot_families_are_fixed(self) -> StoryFindingSlotsV61Schema:
        if self.post_loss.family != "post_loss_response":
            raise ValueError("post_loss slot must use post_loss_response")
        if self.transfer.family != "transfer":
            raise ValueError("transfer slot must use transfer")
        return self


class StoryHelloModuleV61Schema(StoryModuleV61Schema):
    data: StoryHelloDataV61Schema | None = None


class StoryMatchCountModuleV61Schema(StoryModuleV61Schema):
    data: StoryMatchCountDataV61Schema | None = None


class StoryHoursModuleV61Schema(StoryModuleV61Schema):
    data: StoryHoursDataV61Schema | None = None


class StoryRankPointsModuleV61Schema(StoryModuleV61Schema):
    data: StoryRankPointsDataV61Schema | None = None


class StoryBusiestWeekModuleV61Schema(StoryModuleV61Schema):
    data: StoryBusiestWeekDataV61Schema | None = None


class StoryBusiestDayModuleV61Schema(StoryModuleV61Schema):
    data: StoryBusiestDayDataV61Schema | None = None


class StoryLongestMatchModuleV61Schema(StoryModuleV61Schema):
    data: StoryLongestMatchDataV61Schema | None = None


class StoryWinsBridgeModuleV61Schema(StoryModuleV61Schema):
    data: StoryWinsBridgeDataV61Schema | None = None


class StoryWinSummaryModuleV61Schema(StoryModuleV61Schema):
    data: StoryWinSummaryDataV61Schema | None = None


class StoryWinningStreakModuleV61Schema(StoryModuleV61Schema):
    data: StoryWinningStreakDataV61Schema | None = None


class StoryTopWinHeroesModuleV61Schema(StoryModuleV61Schema):
    data: StoryTopWinHeroesDataV61Schema | None = None


class StoryLosingStreakModuleV61Schema(StoryModuleV61Schema):
    data: StoryLosingStreakDataV61Schema | None = None


class StoryTopLossHeroesModuleV61Schema(StoryModuleV61Schema):
    data: StoryTopLossHeroesDataV61Schema | None = None


class StoryHeroPoolModuleV61Schema(StoryModuleV61Schema):
    data: StoryHeroPoolDataV61Schema | None = None


class StoryHeroErasModuleV61Schema(StoryModuleV61Schema):
    data: StoryHeroErasDataV61Schema | None = None


class StoryHeroEraPayoffModuleV61Schema(StoryModuleV61Schema):
    data: StoryHeroEraPayoffDataV61Schema | None = None


class StoryKillsModuleV61Schema(StoryModuleV61Schema):
    data: StoryCombatDataV61Schema | None = None


class StoryAssistsModuleV61Schema(StoryModuleV61Schema):
    data: StoryCombatDataV61Schema | None = None


class StoryDeathsModuleV61Schema(StoryModuleV61Schema):
    data: StoryCombatDataV61Schema | None = None


class StoryElementDistinctivenessModuleV61Schema(StoryModuleV61Schema):
    data: StoryElementDistinctivenessDataV61Schema | None = None

    @model_validator(mode="after")
    def remains_unavailable(self) -> StoryElementDistinctivenessModuleV61Schema:
        if self.state != "not_ready":
            raise ValueError("Element distinctiveness remains not_ready in this release")
        return self


class StoryArchetypeModuleV61Schema(StoryModuleV61Schema):
    data: StoryArchetypeDataV61Schema | None = None

    @model_validator(mode="after")
    def remains_unavailable(self) -> StoryArchetypeModuleV61Schema:
        if self.state != "not_ready":
            raise ValueError("archetype remains not_ready in this release")
        return self


class StoryCardCollageModuleV61Schema(StoryModuleV61Schema):
    data: StoryCardCollageDataV61Schema | None = None


class StoryFinalIdentityCardModuleV61Schema(StoryModuleV61Schema):
    data: StoryFinalIdentityDataV61Schema | None = None

    @model_validator(mode="after")
    def remains_unavailable(self) -> StoryFinalIdentityCardModuleV61Schema:
        if self.state != "not_ready":
            raise ValueError("final identity card remains not_ready in this release")
        return self


class StoryDeepModuleV61Schema(StoryModuleV61Schema):
    data: StoryDeepDataV61Schema | None = None


class StoryPageManifestEntryV61Schema(PublicV6Model):
    id: str | None = None
    page: int | None = Field(default=None, ge=1, le=34)
    module: StoryCardModuleKey | None = None

    @model_validator(mode="after")
    def has_page_identity(self) -> StoryPageManifestEntryV61Schema:
        if self.id is None and self.page is None and self.module is None:
            raise ValueError("page manifest entries need an id, page, or module")
        if self.page == 25:
            raise ValueError("story page manifest cannot contain Page 25")
        return self


STORY_PAGE_MANIFEST_ITEM = StoryPageManifestEntryV61Schema | int | str
STORY_CARD_MANIFEST_ITEM = str | StoryCardV61Schema


class StoryModulesV61Schema(PublicV6Model):
    hello: StoryHelloModuleV61Schema
    match_count: StoryMatchCountModuleV61Schema
    hours_in_matches: StoryHoursModuleV61Schema
    rank_points: StoryRankPointsModuleV61Schema
    busiest_week: StoryBusiestWeekModuleV61Schema
    busiest_day: StoryBusiestDayModuleV61Schema
    longest_match: StoryLongestMatchModuleV61Schema
    wins_bridge: StoryWinsBridgeModuleV61Schema
    win_summary: StoryWinSummaryModuleV61Schema
    winning_streak: StoryWinningStreakModuleV61Schema
    top_win_heroes: StoryTopWinHeroesModuleV61Schema
    losing_streak: StoryLosingStreakModuleV61Schema
    top_loss_heroes: StoryTopLossHeroesModuleV61Schema
    hero_pool: StoryHeroPoolModuleV61Schema
    hero_eras: StoryHeroErasModuleV61Schema
    hero_era_payoff: StoryHeroEraPayoffModuleV61Schema
    kills: StoryKillsModuleV61Schema
    assists: StoryAssistsModuleV61Schema
    deaths: StoryDeathsModuleV61Schema
    element_distinctiveness: StoryElementDistinctivenessModuleV61Schema
    archetype: StoryArchetypeModuleV61Schema
    card_collage: StoryCardCollageModuleV61Schema
    final_identity_card: StoryFinalIdentityCardModuleV61Schema
    deep: StoryDeepModuleV61Schema


class StoryPayloadV61Schema(PublicV6Model):
    version: StoryPayloadVersion
    availability: StoryAvailabilityV61Schema
    provenance: StoryProvenanceV61Schema
    universe: StoryUniverseV61Schema
    identity: StoryIdentityV61Schema
    modules: StoryModulesV61Schema
    finding_slots: StoryFindingSlotsV61Schema
    page_manifest: list[STORY_PAGE_MANIFEST_ITEM] = Field(default_factory=list)
    card_manifest: list[STORY_CARD_MANIFEST_ITEM] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_story_contract(self) -> StoryPayloadV61Schema:
        if self.universe.match_count < 30:
            raise ValueError("story payload requires at least thirty story matches")

        # These pages are mandatory facts for every active story.  All other
        # modules are allowed to omit themselves according to their state.
        for key in ("hello", "match_count", "busiest_week", "wins_bridge", "win_summary"):
            if getattr(self.modules, key).state != "available":
                raise ValueError(f"story module {key} is always available")

        if self.modules.match_count.data is not None:
            match_count = getattr(self.modules.match_count.data, "match_count", None)
            if match_count != self.universe.match_count:
                raise ValueError("match_count module must match the story universe")

        rank_points = self.modules.rank_points
        if rank_points.state in {"available", "degraded"} and rank_points.data is not None:
            if getattr(rank_points.data, "ranked_matches", 0) < 10:
                raise ValueError("rank points cannot ship below the ten-match threshold")

        archetype = self.modules.archetype
        if archetype.state != "not_ready":
            raise ValueError("archetype remains not_ready until its analytical release")
        if archetype.data is not None and getattr(archetype.data, "production_ready", False):
            raise ValueError("archetype cannot be production-ready in this release")

        distinctiveness = self.modules.element_distinctiveness
        if distinctiveness.state != "not_ready":
            raise ValueError("Element distinctiveness remains not_ready in this release")

        final_identity = self.modules.final_identity_card
        if final_identity.state != "not_ready":
            raise ValueError("final identity card is unavailable before archetype readiness")

        deep = self.modules.deep
        if deep.state in {"available", "degraded"} and deep.data is not None:
            available = getattr(deep.data, "available", False)
            if deep.state == "available" and available is not True:
                raise ValueError("available Deep modules must advertise availability")
            if deep.state == "degraded" and available is not False:
                raise ValueError("degraded Deep modules must advertise unavailable")
        elif deep.state != "omitted":
            raise ValueError("unavailable Deep must be omitted or explicitly false")

        self._validate_page_manifest()
        self._validate_card_manifest()
        public = self.model_dump(mode="json", by_alias=True)
        validate_story_privacy(public)
        return self

    def _validate_page_manifest(self) -> None:
        entries: list[tuple[int | None, str | None]] = []
        for item in self.page_manifest:
            page, module = _manifest_page_and_module(item)
            if page is not None and not 1 <= page <= 34:
                raise ValueError("story page manifest page must be between 1 and 34")
            if page == 25:
                raise ValueError("story page manifest cannot contain Page 25")
            if page in {29, 30, 31}:
                raise ValueError("archetype pages remain unavailable in this release")
            if module == "death_context":
                raise ValueError("Death Context is not a story module")
            if module is not None and module in STORY_MODULE_KEYS:
                state = getattr(self.modules, module).state
                if state not in {"available", "degraded"}:
                    raise ValueError("page manifest can only ship available or degraded modules")
            elif module == "post_loss":
                if not self.finding_slots.post_loss.available:
                    raise ValueError("page manifest cannot ship an unavailable Post-Loss slot")
            elif module == "transfer" and not self.finding_slots.transfer.available:
                raise ValueError("page manifest cannot ship an unavailable Transfer slot")
            entries.append((page, module))
        pages = [page for page, _module in entries if page is not None]
        if len(pages) != len(set(pages)):
            raise ValueError("story page manifest cannot repeat a page")
        expected: list[tuple[int, str | None]] = [
            (STORY_MODULE_PAGES[key], key)
            for key in STORY_MODULE_KEYS
            if self._module_is_shippable(key)
        ]
        if self.finding_slots.transfer.available:
            expected.append((STORY_MODULE_PAGES["transfer"], "transfer"))
        if self.finding_slots.post_loss.available:
            expected.append((STORY_MODULE_PAGES["post_loss"], "post_loss"))
        if self._module_is_shippable("deaths"):
            expected.append((26, None))
        expected.sort(key=lambda item: item[0])
        if (
            self._module_is_shippable("deaths")
            and (24, "deaths") in entries
            and (
                (26, None) not in entries
                or entries.index((26, None)) != entries.index((24, "deaths")) + 1
            )
        ):
            raise ValueError("Page 24 must connect directly to Page 26")
        if entries != expected:
            raise ValueError("story page manifest must exactly match shipped modules in reviewed order")

    def _validate_card_manifest(self) -> None:
        cards_data = self.modules.card_collage.data
        cards = list(getattr(cards_data, "cards", ())) if cards_data is not None else []
        manifest_ids = [_card_id(item) for item in self.card_manifest]
        card_ids = [card.id for card in cards]
        if len(card_ids) != len(set(card_ids)) or len(manifest_ids) != len(set(manifest_ids)):
            raise ValueError("story cards and card manifest must have unique IDs")
        if manifest_ids != card_ids:
            raise ValueError("card manifest must exactly mirror card-collage cards")
        expected_modules = [
            key
            for key in STORY_MODULE_KEYS
            if key != "card_collage" and self._module_is_shippable(key)
        ]
        if self.finding_slots.transfer.available:
            expected_modules.append("transfer")
        if self.finding_slots.post_loss.available:
            expected_modules.append("post_loss")
        expected_modules.sort(key=lambda key: STORY_MODULE_PAGES[key])
        if [card.module for card in cards] != expected_modules:
            raise ValueError("story cards must exactly match eligible shipped modules")
        for card in cards:
            if card.module in STORY_MODULE_KEYS:
                state = getattr(self.modules, card.module).state
                if state not in {"available", "degraded"}:
                    raise ValueError("cards can only reference available or degraded modules")
            elif card.module == "post_loss":
                if not self.finding_slots.post_loss.available:
                    raise ValueError("cards cannot reference an unavailable Post-Loss slot")
            elif card.module == "transfer" and not self.finding_slots.transfer.available:
                raise ValueError("cards cannot reference an unavailable Transfer slot")
            if card.page != STORY_MODULE_PAGES[card.module]:
                raise ValueError("story card page must match its shipped module")

    def _module_is_shippable(self, key: str) -> bool:
        module = getattr(self.modules, key)
        if module.state not in {"available", "degraded"}:
            return False
        if key != "deep":
            return True
        return module.data is not None and module.data.available is True


def _manifest_page_and_module(item: STORY_PAGE_MANIFEST_ITEM) -> tuple[int | None, str | None]:
    if isinstance(item, int):
        return item, next((key for key, page in STORY_MODULE_PAGES.items() if page == item), None)
    if isinstance(item, str):
        if item in STORY_MODULE_PAGES:
            return STORY_MODULE_PAGES[item], item
        match = re.search(r"(?:page|p)[-_ ]?(\d+)", item, re.IGNORECASE)
        return (int(match.group(1)), None) if match else (None, item)
    page = item.page
    module: str | None = item.module
    if module is None and item.id is not None:
        if item.id in STORY_MODULE_PAGES:
            module = item.id
        else:
            match = re.fullmatch(r"(?:page|p)[-_ ]?(\d+)", item.id, re.IGNORECASE)
            if match:
                page = int(match.group(1))
            else:
                module = item.id
    if page is None and module is not None:
        page = STORY_MODULE_PAGES.get(module)
    if module is None and page is not None:
        module = next((key for key, value in STORY_MODULE_PAGES.items() if value == page), None)
    if module in STORY_MODULE_PAGES and page is not None and STORY_MODULE_PAGES[module] != page:
        raise ValueError("story page manifest page must match its module")
    return page, module


def _card_id(item: STORY_CARD_MANIFEST_ITEM) -> str:
    return item if isinstance(item, str) else item.id


__all__ = [
    "STORY_ARCHETYPE_CONTRACT_VERSION",
    "STORY_CARD_VERSION",
    "STORY_COPY_VERSION",
    "STORY_HERO_METADATA_VERSION",
    "STORY_HERO_TAXONOMY_VERSION",
    "STORY_MODE_MAP_VERSION",
    "STORY_MODULE_KEYS",
    "STORY_MODULE_PAGES",
    "STORY_PAYLOAD_VERSION",
    "STORY_RANK_POINTS_VERSION",
    "STORY_RULES_VERSION",
    "StoryArchetypeContractVersion",
    "StoryCopyVersion",
    "StoryHeroMetadataVersion",
    "StoryHeroTaxonomyVersion",
    "StoryModeMapVersion",
    "StoryPayloadVersion",
    "StoryRulesVersion",
    "StoryArchetypeDataV61Schema",
    "StoryArchetypeModuleV61Schema",
    "StoryAvailabilityV61Schema",
    "StoryBusiestDayDataV61Schema",
    "StoryBusiestDayModuleV61Schema",
    "StoryBusiestWeekDataV61Schema",
    "StoryBusiestWeekModuleV61Schema",
    "StoryCardCollageDataV61Schema",
    "StoryCardCollageModuleV61Schema",
    "StoryCardV61Schema",
    "StoryCombatDataV61Schema",
    "StoryCombatLeadingHeroV61Schema",
    "StoryCombatRowV61Schema",
    "StoryDeepDataV61Schema",
    "StoryDeepModuleV61Schema",
    "StoryDistinctivenessRowV61Schema",
    "StoryElementDistinctivenessDataV61Schema",
    "StoryEraHeroCountV61Schema",
    "StoryEraPersistenceV61Schema",
    "StoryEraTakeoverV61Schema",
    "StoryFindingContentV61Schema",
    "StoryFindingClaimContractV61Schema",
    "StoryFindingFamily",
    "StoryFindingSlotV61Schema",
    "StoryFindingSlotsV61Schema",
    "StoryFinalIdentityDataV61Schema",
    "StoryFinalIdentityCardModuleV61Schema",
    "StoryHelloDataV61Schema",
    "StoryHelloModuleV61Schema",
    "StoryHeroEraPayoffDataV61Schema",
    "StoryHeroReferenceV61Schema",
    "StoryHeroEraV61Schema",
    "StoryHeroErasDataV61Schema",
    "StoryHeroPoolDataV61Schema",
    "StoryHoursDataV61Schema",
    "StoryHoursModuleV61Schema",
    "StoryIdentityV61Schema",
    "StoryLongestMatchDataV61Schema",
    "StoryLongestMatchModuleV61Schema",
    "StoryMatchCountDataV61Schema",
    "StoryMatchCountModuleV61Schema",
    "StoryModeCountsV61Schema",
    "StoryModuleV61Schema",
    "StoryModuleKey",
    "StoryCardModuleKey",
    "StoryModulesV61Schema",
    "StoryPageManifestEntryV61Schema",
    "StoryPayloadV61Schema",
    "StoryPeriodDurationDataV61Schema",
    "StoryPoolHeroRowV61Schema",
    "StoryProvenanceV61Schema",
    "StoryRankPointsDataV61Schema",
    "StoryRankPointsModuleV61Schema",
    "StoryRoughestDayV61Schema",
    "StoryTopLossHeroesDataV61Schema",
    "StoryTopLossHeroesModuleV61Schema",
    "StoryTopWinHeroesDataV61Schema",
    "StoryTopWinHeroesModuleV61Schema",
    "StoryUniverseV61Schema",
    "StoryWinHeroRowV61Schema",
    "StoryWinSummaryDataV61Schema",
    "StoryWinsBridgeDataV61Schema",
    "StoryWinsBridgeModuleV61Schema",
    "StoryWinningStreakDataV61Schema",
    "StoryWinningStreakModuleV61Schema",
    "StoryWinningestDayV61Schema",
    "StoryLosingStreakDataV61Schema",
    "StoryLosingStreakModuleV61Schema",
    "StoryBreakerV61Schema",
    "StoryLossHeroRowV61Schema",
    "StoryHeroPoolModuleV61Schema",
    "StoryHeroErasModuleV61Schema",
    "StoryHeroEraPayoffModuleV61Schema",
    "StoryKillsModuleV61Schema",
    "StoryAssistsModuleV61Schema",
    "StoryDeathsModuleV61Schema",
    "StoryElementDistinctivenessModuleV61Schema",
    "StoryWinSummaryModuleV61Schema",
    "StoryOutcome",
    "StoryState",
    "StoryFinalIdentityCardModuleV61Schema",
    "validate_story_privacy",
]
