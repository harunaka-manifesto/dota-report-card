"""Typed data contract for the V7 report.

This module defines **structure only**. It says exactly what each of the nine
V7 report sections needs to carry, so that later work (feature derivation,
corpus reads, the Finding-ranking and improvement-recommendation
computations) has an unambiguous target to fill in. It deliberately does not:

- compute anything over the corpus,
- derive any feature or statistic,
- read or write `.local/`, Pass-1/Pass-2 scripts, or any provider data,
- touch the existing V6.1 report, its schemas, or the frontend.

Sources of truth for the shapes defined here:

- ``docs/evidence/v7-report-narrative-and-data-requirements-2026-09-04.md``
  (section-by-section spec, section numbers referenced in docstrings below),
- ``docs/evidence/v7-finding-ranking-model-2026-09-05.md`` (what a Finding
  carries: z, reliability, score, direction, interval),
- ``docs/evidence/v7-improvement-recommendation-model-2026-09-05.md`` (what
  the single section-5 recommendation carries).

Conventions are matched to the existing V6.1 payload style in
``report_card.api.story_payload_schemas_v61``: frozen, extra-forbidding Pydantic
models (``PublicV7Model`` mirrors ``PublicV6Model``'s
``ConfigDict(extra="forbid", frozen=True, populate_by_name=True)``),
``Literal`` unions for closed vocabularies, ``Field(ge=..., le=...)`` for
numeric ranges, and ``@model_validator(mode="after")`` methods that enforce
cross-field invariants and raise ``ValueError`` on violation (which is how
Pydantic supplies the "validate()" contract required here — construction
itself is the validation call).

No account id, steam id, or match id appears anywhere in this tree. Only
pseudonymous, aggregate, or player-facing descriptive data is represented.
Rank is the one exception the owner explicitly allowed (owner decision 5.1 in
the narrative doc): it is display-only, lives in exactly one place
(``HistorySection.rank``), and is fenced by a comment on that field and on
``RankDisplay`` stating it must never be read by analysis code. It is not an
identifier — no field here stores an account id, MMR value, or anything that
resolves to a specific Steam account.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from report_card.player_analysis_v7.research.recommendation import MIN_PER_ARM

# ---------------------------------------------------------------------------
# Base model and shared vocabularies
# ---------------------------------------------------------------------------


class PublicV7Model(BaseModel):
    """Frozen, extra-forbidding base model, matching ``PublicV6Model``."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    @model_validator(mode="after")
    def numeric_values_are_finite(self) -> PublicV7Model:
        _assert_finite_numbers(self.model_dump(mode="python"), self.__class__.__name__)
        return self


Direction = Literal["positive", "negative", "zero"]
"""Sign of a z-score or a within-player gap (`v7-finding-ranking-model`
section 2.1, `sign(z_pf)`). ``"zero"`` covers the exact-tie edge case; real
Findings and recommendations are expected to land on positive or negative."""

# There is no ``StrengthBand``. Owner decision D2 (2026-09-06) dropped the
# slight / moderate / pronounced bands entirely, on measurement rather than
# taste: over 4,983 player-Findings, the best cut points that keep all three
# bands populated leave 65.2% of Findings with a 95% interval straddling a band
# boundary. A typical interval on ``|z| * reliability`` is about 0.6 wide while
# three populated bands need cuts about 0.5 apart, so the interval is wider than
# the band. Collecting more players cannot fix that -- the interval is dominated
# by within-player measurement error -- so the adjective was dropped rather than
# calibrated. A Finding carries its ``direction``, its ``score`` and its
# ``estimate`` (a shrunk point estimate with an interval), which say everything
# a band would have said and say it at the precision the data supports.
# See docs/evidence/v7-cut-point-calibration-dry-run-2026-09-06.md.

ReportSectionKey = Literal[
    "history",
    "what_is_good",
    "what_is_costing_you",
    "response_to_a_loss",
    "what_to_improve",
    "archetype",
    "share_card",
    "paid_bridge",
    "closing",
]
"""The nine report sections, in narrative order (sections 1-9)."""

FindingSectionKey = Literal["what_is_good", "what_is_costing_you", "response_to_a_loss"]
"""Sections that actually carry ranked Findings. Section 5 ("what to
improve") uses a different computation entirely (recommendation model
section 1) and is deliberately excluded from this union — a Finding can
never claim to belong to it."""

HeroRole = Literal["core", "support"]
TempoAxis = Literal["early", "mid", "late"]
FightStyleAxis = Literal["frontliner", "opportunist", "ghost"]
ArchetypeModifier = Literal["metronome", "streaky"]

_TOLERANCE = 1e-6


def _assert_finite_numbers(value: object, path: str = "model") -> None:
    """Reject non-finite numeric values at the typed report boundary."""

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must be finite, got {value!r}")
    elif isinstance(value, Mapping):
        for key, nested in value.items():
            _assert_finite_numbers(nested, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _assert_finite_numbers(nested, f"{path}[{index}]")


# ---------------------------------------------------------------------------
# No-identifiers guard
# ---------------------------------------------------------------------------

_FORBIDDEN_IDENTIFIER_KEYS = frozenset(
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
        "username",
        "user_name",
        "personaname",
        "persona_name",
        "mmr",
        "mmr_bucket",
        "average_rank",
        "rank_tier",
    }
)
_PRIVATE_IDENTIFIER_TOKENS = frozenset(
    re.sub(r"[^a-z0-9]", "", key) for key in _FORBIDDEN_IDENTIFIER_KEYS
)


def _assert_no_identifiers(value: object, path: str = "report") -> None:
    """Walk a ``model_dump``-shaped tree and reject any identifier key.

    Mirrors ``validate_story_privacy`` in ``story_payload_schemas_v61`` but is
    scoped to the identifier tokens that matter for this contract (rank is
    allowed, display-only, elsewhere; see ``RankDisplay``).
    """

    if isinstance(value, Mapping):
        for key, nested in value.items():
            folded = str(key).casefold()
            normalized = re.sub(r"[^a-z0-9]", "", folded)
            if folded in _FORBIDDEN_IDENTIFIER_KEYS or normalized in _PRIVATE_IDENTIFIER_TOKENS:
                raise ValueError(f"report payload contains an identifier key at {path}.{key}")
            _assert_no_identifiers(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _assert_no_identifiers(nested, f"{path}[{index}]")


# ---------------------------------------------------------------------------
# Shared small structures
# ---------------------------------------------------------------------------


class WinLossValue(PublicV7Model):
    """A dimension's value in the player's own wins versus their own losses.

    This is the shape of every "contrast" the narrative doc calls for
    (section 1.1: "a number is not an insight; a contrast is"). Both values
    are computed on the *same* hero/position/role slice; nothing here is a
    population comparison.
    """

    win_value: float
    loss_value: float


class PointEstimateWithInterval(PublicV7Model):
    """A shrunk point estimate with its interval (ranking model section 5.2:
    "report the interval, not just the point")."""

    point: float
    interval_low: float
    interval_high: float

    @model_validator(mode="after")
    def interval_contains_point(self) -> PointEstimateWithInterval:
        if not (self.interval_low - _TOLERANCE <= self.point <= self.interval_high + _TOLERANCE):
            raise ValueError("interval must contain the point estimate")
        if self.interval_low > self.interval_high + _TOLERANCE:
            raise ValueError("interval_low cannot exceed interval_high")
        return self


# ---------------------------------------------------------------------------
# Finding (ranking-model output, ranking-model doc sections 2 and 5)
# ---------------------------------------------------------------------------


class Finding(PublicV7Model):
    """One ranked Finding, as produced by the per-player ranking model.

    Field-for-field mapping to `v7-finding-ranking-model-2026-09-05.md`:

    - ``dimension_key``: the family/dimension being measured (section 3's
      table, e.g. ``"post_loss_hero_switch"``).
    - ``section``: which report section this Finding is presented under
      (section 6, "Section coverage" — stratified selection fills each
      section's top slot first).
    - ``direction``: ``sign(z_pf)`` (section 2.1 / section 5.3).
    - ``z``: ``z_pf``, the player's position in population standard
      deviations (section 2.1).
    - ``reliability``: ``r_pf``, the dependence-corrected shrinkage weight in
      ``[0, 1]`` (section 2.2).
    - ``score``: ``score_pf = |z_pf| * r_pf`` (section 2.3).
    - ``estimate``: the shrunk point estimate with interval (section 5.2).
    - ``sample_size``: how many of the player's matches support this
      estimand.
    - ``player_facing_question``: the copy hook this Finding answers, e.g.
      "when do your games actually get decided?" — never the raw dimension
      key, which is an internal name.
    """

    dimension_key: str = Field(min_length=1)
    section: FindingSectionKey
    direction: Direction
    own_contrast_direction: Direction | None = Field(
        default=None,
        description=(
            "Sign of the player's within-player treated-minus-control estimate. "
            "Present for contrast dimensions; unlike direction, this is not sign(z)."
        ),
    )
    z: float
    reliability: float = Field(ge=0, le=1)
    score: float = Field(ge=0)
    estimate: PointEstimateWithInterval
    sample_size: int = Field(ge=1)
    player_facing_question: str = Field(min_length=1)

    @model_validator(mode="after")
    def score_is_the_shrunk_position(self) -> Finding:
        """``score = |z| * reliability`` - the ranking model's own definition.

        This is the invariant worth enforcing. It is arithmetic, it holds
        whatever cut points calibration eventually picks, and it catches the
        error that actually matters: a Finding ranked by something other than
        the model. It is now the only cross-field rule a Finding carries: the
        band check went with the bands (owner decision D2).
        """

        expected = abs(self.z) * self.reliability
        if abs(self.score - expected) > _TOLERANCE:
            raise ValueError(
                f"score {self.score!r} is not |z| * reliability "
                f"({abs(self.z)!r} * {self.reliability!r} = {expected!r})"
            )
        return self


# ---------------------------------------------------------------------------
# Recommendation (improvement-recommendation model)
# ---------------------------------------------------------------------------


class RecommendationObservation(PublicV7Model):
    """The player's own win value, loss value, and gap for one dimension.

    ``gap`` follows the estimand in the recommendation model, section 2:
    ``gap_pd = E[d | p, loss] - E[d | p, win]``.
    """

    win_value: float
    loss_value: float
    gap: float

    @model_validator(mode="after")
    def gap_matches_values(self) -> RecommendationObservation:
        expected = self.loss_value - self.win_value
        if abs(self.gap - expected) > 1e-6:
            raise ValueError("gap must equal loss_value minus win_value")
        return self


class Recommendation(PublicV7Model):
    """One candidate improvement, per `v7-improvement-recommendation-model`.

    Used both for the single selected recommendation and for the two
    retained runners-up (section 6 of that document) — the shape is
    identical, only the ranking position differs.
    """

    dimension_key: str = Field(min_length=1)
    upstream_of_result: Literal[True] = Field(
        default=True,
        description=(
            "Attests the eligibility rule in recommendation-model section 3: "
            "only a behaviour the player emits, never a result they receive, "
            "may be recommended. Fixed True; a dimension that fails this rule "
            "must not be represented as a Recommendation at all."
        ),
    )
    outcome_contaminated: Literal[False] = Field(
        default=False,
        description=(
            "Attests the recommendation registry's independent modal-sign rule. "
            "A contaminated gap cannot be represented as a Recommendation."
        ),
    )
    observation: RecommendationObservation
    direction: Direction
    recommendation_text: str = Field(
        min_length=1, description="One sentence, imperative, doable in the next game."
    )
    verification: str = Field(
        min_length=1,
        description="The exact measurement, from fields already collected, that will "
        "confirm or refute this next time (recommendation-model section 4).",
    )
    sample_wins: int = Field(ge=MIN_PER_ARM)
    sample_losses: int = Field(ge=MIN_PER_ARM)
    reliability: float = Field(ge=0, le=1)
    actionability_weight: float = Field(ge=0, le=1)
    priority_score: float = Field(ge=0, description="priority_pd = |g_pd| * r_pd * A_d")

    @model_validator(mode="after")
    def direction_matches_gap(self) -> Recommendation:
        expected = (
            "positive"
            if self.observation.gap > 0
            else "negative"
            if self.observation.gap < 0
            else "zero"
        )
        if self.direction != expected:
            raise ValueError(
                f"recommendation direction {self.direction!r} must match "
                f"the gap sign {expected!r}"
            )
        return self


# ---------------------------------------------------------------------------
# Section 1 — History
# ---------------------------------------------------------------------------


class TopHeroHistoryRow(PublicV7Model):
    rank: int = Field(ge=1, le=5)
    hero_id: int = Field(ge=1)
    hero_name: str = Field(min_length=1)
    games: int = Field(ge=1)
    win_rate: float = Field(ge=0, le=1)


class MostPurchasedItem(PublicV7Model):
    """The most-purchased *real* item (consumables and starters excluded),
    with the player's average purchase timing for it."""

    item_id: int = Field(ge=1)
    item_name: str = Field(min_length=1)
    purchase_count: int = Field(ge=1)
    average_purchase_minute: float = Field(ge=0)


class LongestWinStreak(PublicV7Model):
    length: int = Field(ge=0)
    start_date: str | None = Field(
        default=None, description="Absent when length is 0 (the player has no win streak yet)."
    )
    end_date: str | None = Field(
        default=None, description="Absent when length is 0 (the player has no win streak yet)."
    )

    @model_validator(mode="after")
    def dates_match_length(self) -> LongestWinStreak:
        has_dates = self.start_date is not None or self.end_date is not None
        if self.length == 0 and has_dates:
            raise ValueError("a zero-length win streak cannot carry dates")
        if self.length > 0 and (self.start_date is None or self.end_date is None):
            raise ValueError("a positive-length win streak requires both dates")
        return self


class PatchSpread(PublicV7Model):
    patches_played: list[str] = Field(min_length=1)
    primary_patch: str = Field(min_length=1)

    @model_validator(mode="after")
    def primary_patch_is_played(self) -> PatchSpread:
        if self.primary_patch not in self.patches_played:
            raise ValueError("primary_patch must be one of patches_played")
        return self


class RankDisplay(PublicV7Model):
    """Rank movement across the reporting window, for History display only.

    Owner decision 5.1 in the narrative doc: rank is collected and shown in
    section 1 as history, and it is **never** an analytical input. This
    struct must never be read by any Finding, recommendation, archetype, or
    context/cohort computation — those all live outside
    ``HistorySection.rank`` in this contract, and none of them may import or
    reference ``RankDisplay``. Values are display labels (e.g. "Legend 3"),
    not raw MMR, and are absent whenever rank display is disabled or was not
    collected for the account.
    """

    start_rank_label: str = Field(min_length=1)
    end_rank_label: str = Field(min_length=1)
    direction: Direction


class HistorySection(PublicV7Model):
    """Section 1 — receipts, not Findings (narrative doc section "Section 1")."""

    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    hours_played: float = Field(ge=0)
    distinct_heroes: int = Field(ge=0)
    top_heroes: list[TopHeroHistoryRow] = Field(default_factory=list, max_length=5)
    most_purchased_item: MostPurchasedItem | None = Field(
        default=None,
        description="Absent when the item vocabulary yields no non-consumable, "
        "non-starter purchase for this player.",
    )
    longest_win_streak: LongestWinStreak
    active_days: int = Field(ge=0)
    first_match_date: str
    last_match_date: str
    patch_spread: PatchSpread
    rank: RankDisplay | None = Field(
        default=None,
        description="Absent when rank display was not collected for this account, or the "
        "owner-level rank-display toggle is off. DISPLAY-ONLY — see RankDisplay docstring; "
        "must never be used as an analytical input anywhere else in this tree.",
    )

    @model_validator(mode="after")
    def counts_are_consistent(self) -> HistorySection:
        ranks = [row.rank for row in self.top_heroes]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("top_heroes rows must have consecutive ranks starting at 1")
        total_games = self.wins + self.losses
        if sum(row.games for row in self.top_heroes) > total_games:
            raise ValueError("top_heroes games cannot exceed total wins plus losses")
        if total_games > 0 and self.active_days == 0:
            raise ValueError("a player with matches must have at least one active day")
        if self.first_match_date > self.last_match_date:
            raise ValueError("first_match_date cannot be after last_match_date")
        return self


# ---------------------------------------------------------------------------
# Section 2 — What is good
# ---------------------------------------------------------------------------


class CoreHeroGoodContrast(PublicV7Model):
    """Win-vs-loss contrast for a core hero (narrative doc, "If the hero is a core")."""

    last_hits_at_10: WinLossValue
    denies_at_10: WinLossValue
    lane_outcome_win_rate: WinLossValue = Field(description="Share of games the player's own "
        "lane was won, contrasted between their wins and their losses.")
    net_worth_at_10: WinLossValue
    net_worth_at_15: WinLossValue
    net_worth_at_20: WinLossValue
    net_worth_at_25: WinLossValue
    key_item_name: str = Field(min_length=1)
    key_item_timing_minutes: WinLossValue
    tower_damage_per_minute: WinLossValue
    fight_presence_rate: WinLossValue = Field(
        description="Share of the team's kills/assists this player was part of."
    )


class SupportHeroGoodContrast(PublicV7Model):
    """Win-vs-loss contrast for a support hero (narrative doc, "If the hero is a support")."""

    first_ward_time_minutes: WinLossValue
    wards_per_game: WinLossValue
    ward_spread_variance: WinLossValue = Field(
        description="Variance of ward position; low variance means the same spots every game."
    )
    camp_stacks_per_game: WinLossValue
    heal_per_minute: WinLossValue
    save_item_name: str = Field(min_length=1)
    save_item_timing_minutes: WinLossValue
    deaths_avoided_while_participating_rate: WinLossValue
    rune_control_rate: WinLossValue = Field(
        description="Share of early runes/bounty runs this player secured."
    )


class TopHeroGoodEntry(PublicV7Model):
    hero_id: int = Field(ge=1)
    hero_name: str = Field(min_length=1)
    role: HeroRole
    games: int = Field(ge=1)
    core_contrast: CoreHeroGoodContrast | None = Field(
        default=None, description="Present only when role is 'core'."
    )
    support_contrast: SupportHeroGoodContrast | None = Field(
        default=None, description="Present only when role is 'support'."
    )

    @model_validator(mode="after")
    def contrast_matches_role(self) -> TopHeroGoodEntry:
        if self.role == "core":
            if self.core_contrast is None or self.support_contrast is not None:
                raise ValueError("a core hero entry requires core_contrast and no support_contrast")
        else:
            if self.support_contrast is None or self.core_contrast is not None:
                raise ValueError("a support hero entry requires support_contrast and no core_contrast")
        return self


class TeamInWinsProjection(PublicV7Model):
    """What the team does in the player's wins (narrative doc, "What your
    team does in your wins"). Slim, scalar-only per the ten-player projection
    constraint (`v7-report-narrative...` section 3.3)."""

    core_farm_share: float = Field(ge=0, le=1, description="Share of team farm going to cores.")
    kill_concentration: Literal["spread", "concentrated"]
    lanes_won_of_three: int = Field(ge=0, le=3)


class TellingSignMinute(PublicV7Model):
    """The minute at which the player's own net-worth/experience lead starts
    predicting their result (narrative doc, "the telling sign")."""

    minute: int = Field(ge=0)
    win_rate_when_ahead_at_minute: float = Field(ge=0, le=1)
    win_rate_before_minute: float = Field(
        ge=0, le=1, description="Baseline win rate when position at this minute is not yet decisive."
    )
    sample_size: int = Field(ge=1)


class WhatIsGoodSection(PublicV7Model):
    """Section 2."""

    top_heroes: list[TopHeroGoodEntry] = Field(min_length=1, max_length=5)
    team_in_wins: TeamInWinsProjection
    telling_sign: TellingSignMinute
    findings: list[Finding] = Field(default_factory=list)

    @model_validator(mode="after")
    def findings_belong_here(self) -> WhatIsGoodSection:
        for finding in self.findings:
            if finding.section != "what_is_good":
                raise ValueError("a what_is_good Finding must have section == 'what_is_good'")
        return self


# ---------------------------------------------------------------------------
# Section 3 — What is costing you
# ---------------------------------------------------------------------------


class TopHeroCostingEntry(PublicV7Model):
    """The same per-hero contrast as section 2, framed as what is costing the
    player rather than what is going right; the underlying measurement is
    identical, only the narrative framing differs (narrative doc: "Same
    contrast inverted")."""

    hero_id: int = Field(ge=1)
    hero_name: str = Field(min_length=1)
    role: HeroRole
    games: int = Field(ge=1)
    core_contrast: CoreHeroGoodContrast | None = Field(
        default=None, description="Present only when role is 'core'."
    )
    support_contrast: SupportHeroGoodContrast | None = Field(
        default=None, description="Present only when role is 'support'."
    )

    @model_validator(mode="after")
    def contrast_matches_role(self) -> TopHeroCostingEntry:
        if self.role == "core":
            if self.core_contrast is None or self.support_contrast is not None:
                raise ValueError("a core hero entry requires core_contrast and no support_contrast")
        else:
            if self.support_contrast is None or self.core_contrast is not None:
                raise ValueError("a support hero entry requires support_contrast and no core_contrast")
        return self


class DeathTimingBand(PublicV7Model):
    minute_band_start: int = Field(ge=0)
    minute_band_end: int = Field(gt=0)
    death_count: int = Field(ge=0)
    share_of_deaths: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def band_is_ordered(self) -> DeathTimingBand:
        if self.minute_band_end <= self.minute_band_start:
            raise ValueError("minute_band_end must be after minute_band_start")
        return self


class DeathGameState(PublicV7Model):
    """Deaths cross-referenced against the player's own net-worth lead curve
    (narrative doc: "dying while ahead is a different disease from dying
    while behind")."""

    ahead_death_share: float = Field(ge=0, le=1)
    behind_death_share: float = Field(ge=0, le=1)
    even_death_share: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def shares_sum_to_one(self) -> DeathGameState:
        total = self.ahead_death_share + self.behind_death_share + self.even_death_share
        if abs(total - 1.0) > 1e-6:
            raise ValueError("death game-state shares must sum to 1")
        return self


class DeathAloneSplit(PublicV7Model):
    """Alone-versus-in-fight split (narrative doc: "the strongest single
    insight available")."""

    alone_share: float = Field(ge=0, le=1)
    in_fight_share: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def shares_sum_to_one(self) -> DeathAloneSplit:
        if abs((self.alone_share + self.in_fight_share) - 1.0) > 1e-6:
            raise ValueError("alone/in-fight death shares must sum to 1")
        return self


class DeathProfile(PublicV7Model):
    total_deaths: int = Field(ge=0)
    timing_bands: list[DeathTimingBand] = Field(default_factory=list)
    game_state: DeathGameState
    alone_split: DeathAloneSplit

    @model_validator(mode="after")
    def bands_are_consistent(self) -> DeathProfile:
        if self.timing_bands:
            band_total = sum(band.death_count for band in self.timing_bands)
            if band_total > self.total_deaths:
                raise ValueError("death timing bands cannot account for more than total_deaths")
            share_total = sum(band.share_of_deaths for band in self.timing_bands)
            if share_total > 1.0 + 1e-6:
                raise ValueError("death timing band shares cannot sum past 1")
        return self


class WhatIsCostingYouSection(PublicV7Model):
    """Section 3."""

    top_heroes: list[TopHeroCostingEntry] = Field(min_length=1, max_length=5)
    death_profile: DeathProfile
    findings: list[Finding] = Field(default_factory=list)

    @model_validator(mode="after")
    def findings_belong_here(self) -> WhatIsCostingYouSection:
        for finding in self.findings:
            if finding.section != "what_is_costing_you":
                raise ValueError(
                    "a what_is_costing_you Finding must have section == 'what_is_costing_you'"
                )
        return self


# ---------------------------------------------------------------------------
# Section 4 — Response to a loss
# ---------------------------------------------------------------------------


class BetweenMatchResponse(PublicV7Model):
    """Between-match behaviours after a loss (narrative doc section 4, the
    "most reliable material in the corpus")."""

    continues_playing_rate: float = Field(ge=0, le=1)
    switches_hero_rate: float = Field(ge=0, le=1)
    requeue_latency_minutes: float = Field(ge=0)
    sample_size: int = Field(ge=1)


class InGameResponse(PublicV7Model):
    """In-game behaviours after a loss — does the first ten minutes get
    worse (narrative doc section 4, "the second pass adds")."""

    last_hits_at_10_after_loss: float = Field(ge=0)
    last_hits_at_10_baseline: float = Field(ge=0)
    first_death_minute_after_loss: float = Field(ge=0)
    first_death_minute_baseline: float = Field(ge=0)
    turbo_switch_rate_after_loss: float = Field(ge=0, le=1)
    sample_size: int = Field(ge=1)


class ResponseToALossSection(PublicV7Model):
    """Section 4."""

    between_match: BetweenMatchResponse
    in_game: InGameResponse
    findings: list[Finding] = Field(default_factory=list)

    @model_validator(mode="after")
    def findings_belong_here(self) -> ResponseToALossSection:
        for finding in self.findings:
            if finding.section != "response_to_a_loss":
                raise ValueError(
                    "a response_to_a_loss Finding must have section == 'response_to_a_loss'"
                )
        return self


# ---------------------------------------------------------------------------
# Section 5 — What to improve
# ---------------------------------------------------------------------------


class WhatToImproveSection(PublicV7Model):
    """Section 5. Exactly one recommendation ships (recommendation-model
    section 6); ``runners_up`` retains exactly the two next-highest-priority
    eligible dimensions for the paid tier (section 6: "Two runners-up are
    computed and retained for the paid tier")."""

    recommendation: Recommendation
    runners_up: list[Recommendation] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def exactly_one_recommendation_and_distinct_runners_up(self) -> WhatToImproveSection:
        # `recommendation` is a single required field, so "exactly one
        # recommendation" is structurally guaranteed; this also checks that
        # the runners-up do not silently duplicate it or each other.
        all_keys = [self.recommendation.dimension_key] + [r.dimension_key for r in self.runners_up]
        if len(set(all_keys)) != len(all_keys):
            raise ValueError(
                "the selected recommendation and its runners-up must be distinct dimensions"
            )
        return self


# ---------------------------------------------------------------------------
# Section 6 — Archetype
# ---------------------------------------------------------------------------


class ArchetypeSection(PublicV7Model):
    """Section 6. Tempo x fight-style x modifier = 18 combinations (enforced
    structurally by the three ``Literal`` axes), plus two rare specials that
    bypass the grid (narrative doc: "plus two rare specials for genuine
    outliers = 20")."""

    tempo: TempoAxis
    fight_style: FightStyleAxis
    modifier: ArchetypeModifier
    label: str = Field(min_length=1)
    is_special: bool = False
    special_label: str | None = Field(
        default=None,
        description="Set only when is_special is True; one of the two rare special "
        "archetypes that bypass the normal 18-combination grid.",
    )

    @model_validator(mode="after")
    def special_label_matches_flag(self) -> ArchetypeSection:
        if self.is_special and not self.special_label:
            raise ValueError("a special archetype requires special_label")
        if not self.is_special and self.special_label is not None:
            raise ValueError("special_label may only be set when is_special is True")
        return self


# ---------------------------------------------------------------------------
# Section 7 — Share card
# ---------------------------------------------------------------------------


class HeadlineNumber(PublicV7Model):
    label: str = Field(min_length=1)
    value: float
    unit: str | None = None


class ShareCardContrastStat(PublicV7Model):
    label: str = Field(min_length=1)
    win_value: float
    loss_value: float


class ShareCardSection(PublicV7Model):
    """Section 7: one headline number, the archetype, one contrast stat.

    "A share card must be true and must not be an insult" (narrative doc) is
    a copy-review constraint, not something a type can enforce; it is
    recorded here as documentation for whoever authors share-card copy.
    """

    headline_number: HeadlineNumber
    archetype_label: str = Field(min_length=1)
    contrast_stat: ShareCardContrastStat


# ---------------------------------------------------------------------------
# Section 8 — Paid bridge
# ---------------------------------------------------------------------------


class PaidBridgeSection(PublicV7Model):
    """Section 8: what the free report deliberately cannot do."""

    free_report_limits: list[str] = Field(min_length=1)
    paid_capabilities: list[str] = Field(min_length=1)


# ---------------------------------------------------------------------------
# Section 9 — Closing
# ---------------------------------------------------------------------------


class ClosingSection(PublicV7Model):
    """Section 9: recap and the single improvement. ``improvement_dimension_key``
    must match the dimension selected in ``WhatToImproveSection.recommendation``
    (checked at the ``ReportPayload`` level, since that is the only place both
    sections are in scope together)."""

    recap_summary: str = Field(min_length=1)
    improvement_dimension_key: str = Field(min_length=1)
    improvement_recap_text: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Provenance and top-level payload
# ---------------------------------------------------------------------------


class ReportProvenance(PublicV7Model):
    corpus_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    feature_version: str = Field(min_length=1)
    ranking_model_version: str = Field(min_length=1)
    generated_at: str = Field(min_length=1, description="ISO 8601 timestamp.")


class ReportPayload(PublicV7Model):
    """The complete V7 report: all nine sections plus provenance."""

    history: HistorySection
    what_is_good: WhatIsGoodSection
    what_is_costing_you: WhatIsCostingYouSection
    response_to_a_loss: ResponseToALossSection
    what_to_improve: WhatToImproveSection
    archetype: ArchetypeSection
    share_card: ShareCardSection
    paid_bridge: PaidBridgeSection
    closing: ClosingSection
    provenance: ReportProvenance

    @model_validator(mode="after")
    def validate_report(self) -> ReportPayload:
        if (
            self.closing.improvement_dimension_key
            != self.what_to_improve.recommendation.dimension_key
        ):
            raise ValueError(
                "closing.improvement_dimension_key must match "
                "what_to_improve.recommendation.dimension_key"
            )
        _assert_no_identifiers(self.model_dump(mode="json", by_alias=True))
        return self


__all__ = [
    "ArchetypeModifier",
    "ArchetypeSection",
    "BetweenMatchResponse",
    "ClosingSection",
    "CoreHeroGoodContrast",
    "DeathAloneSplit",
    "DeathGameState",
    "DeathProfile",
    "DeathTimingBand",
    "Direction",
    "Finding",
    "FightStyleAxis",
    "FindingSectionKey",
    "HeadlineNumber",
    "HeroRole",
    "HistorySection",
    "InGameResponse",
    "LongestWinStreak",
    "MostPurchasedItem",
    "PaidBridgeSection",
    "PatchSpread",
    "PointEstimateWithInterval",
    "PublicV7Model",
    "RankDisplay",
    "Recommendation",
    "RecommendationObservation",
    "ReportPayload",
    "ReportProvenance",
    "ReportSectionKey",
    "ResponseToALossSection",
    "ShareCardContrastStat",
    "ShareCardSection",
    "SupportHeroGoodContrast",
    "TeamInWinsProjection",
    "TellingSignMinute",
    "TempoAxis",
    "TopHeroCostingEntry",
    "TopHeroGoodEntry",
    "TopHeroHistoryRow",
    "WhatIsCostingYouSection",
    "WhatIsGoodSection",
    "WhatToImproveSection",
    "WinLossValue",
]
