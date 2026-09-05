from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from app.player_analysis_v7.report_contract import (
    ArchetypeSection,
    BetweenMatchResponse,
    ClosingSection,
    CoreHeroGoodContrast,
    DeathAloneSplit,
    DeathGameState,
    DeathProfile,
    DeathTimingBand,
    Finding,
    HeadlineNumber,
    HistorySection,
    InGameResponse,
    LongestWinStreak,
    MostPurchasedItem,
    PaidBridgeSection,
    PatchSpread,
    PointEstimateWithInterval,
    RankDisplay,
    Recommendation,
    RecommendationObservation,
    ReportPayload,
    ReportProvenance,
    ResponseToALossSection,
    ShareCardContrastStat,
    ShareCardSection,
    SupportHeroGoodContrast,
    TeamInWinsProjection,
    TellingSignMinute,
    TopHeroCostingEntry,
    TopHeroGoodEntry,
    TopHeroHistoryRow,
    WhatIsCostingYouSection,
    WhatIsGoodSection,
    WhatToImproveSection,
    WinLossValue,
)
from pydantic import ValidationError


def _core_contrast() -> CoreHeroGoodContrast:
    return CoreHeroGoodContrast(
        last_hits_at_10=WinLossValue(win_value=61, loss_value=39),
        denies_at_10=WinLossValue(win_value=8, loss_value=4),
        lane_outcome_win_rate=WinLossValue(win_value=0.7, loss_value=0.4),
        net_worth_at_10=WinLossValue(win_value=4200, loss_value=3100),
        net_worth_at_15=WinLossValue(win_value=7200, loss_value=5100),
        net_worth_at_20=WinLossValue(win_value=10200, loss_value=7100),
        net_worth_at_25=WinLossValue(win_value=13200, loss_value=9100),
        key_item_name="Black King Bar",
        key_item_timing_minutes=WinLossValue(win_value=24, loss_value=31),
        tower_damage_per_minute=WinLossValue(win_value=120, loss_value=80),
        fight_presence_rate=WinLossValue(win_value=0.8, loss_value=0.6),
    )


def _support_contrast() -> SupportHeroGoodContrast:
    return SupportHeroGoodContrast(
        first_ward_time_minutes=WinLossValue(win_value=1.5, loss_value=4.0),
        wards_per_game=WinLossValue(win_value=12, loss_value=7),
        ward_spread_variance=WinLossValue(win_value=0.6, loss_value=0.2),
        camp_stacks_per_game=WinLossValue(win_value=5, loss_value=2),
        heal_per_minute=WinLossValue(win_value=180, loss_value=110),
        save_item_name="Glimmer Cape",
        save_item_timing_minutes=WinLossValue(win_value=13, loss_value=19),
        deaths_avoided_while_participating_rate=WinLossValue(win_value=0.7, loss_value=0.4),
        rune_control_rate=WinLossValue(win_value=0.6, loss_value=0.3),
    )


def _finding(section: str, dimension_key: str = "post_loss_hero_switch") -> Finding:
    return Finding(
        dimension_key=dimension_key,
        section=section,  # type: ignore[arg-type]
        direction="positive",
        z=1.8,
        reliability=0.9,
        score=1.62,
        strength_band="pronounced",
        estimate=PointEstimateWithInterval(point=0.4, interval_low=0.2, interval_high=0.6),
        sample_size=120,
        player_facing_question="How do you respond after a loss?",
    )


def _recommendation(dimension_key: str = "last_hits_at_10") -> Recommendation:
    return Recommendation(
        dimension_key=dimension_key,
        observation=RecommendationObservation(win_value=61, loss_value=39, gap=-22),
        direction="negative",
        recommendation_text="For five games, care about nothing but last hits until minute 10.",
        verification="last_hits_per_minute cumulated to minute 10",
        sample_wins=80,
        sample_losses=60,
        reliability=0.85,
        actionability_weight=0.9,
        priority_score=1.4,
    )


def _valid_payload_kwargs() -> dict[str, Any]:
    history = HistorySection(
        wins=120,
        losses=90,
        hours_played=310.5,
        distinct_heroes=42,
        top_heroes=[
            TopHeroHistoryRow(rank=i, hero_id=i, hero_name=f"Hero {i}", games=20 - i, win_rate=0.55)
            for i in range(1, 6)
        ],
        most_purchased_item=MostPurchasedItem(
            item_id=43, item_name="Black King Bar", purchase_count=140, average_purchase_minute=26.4
        ),
        longest_win_streak=LongestWinStreak(length=6, start_date="2026-01-01", end_date="2026-01-05"),
        active_days=180,
        first_match_date="2025-09-01",
        last_match_date="2026-08-30",
        patch_spread=PatchSpread(patches_played=["7.36c", "7.37"], primary_patch="7.36c"),
        rank=RankDisplay(start_rank_label="Legend 1", end_rank_label="Legend 4", direction="positive"),
    )

    what_is_good = WhatIsGoodSection(
        top_heroes=[
            TopHeroGoodEntry(
                hero_id=1, hero_name="Juggernaut", role="core", games=40, core_contrast=_core_contrast()
            ),
            TopHeroGoodEntry(
                hero_id=2,
                hero_name="Lion",
                role="support",
                games=30,
                support_contrast=_support_contrast(),
            ),
        ],
        team_in_wins=TeamInWinsProjection(
            core_farm_share=0.62, kill_concentration="spread", lanes_won_of_three=2
        ),
        telling_sign=TellingSignMinute(
            minute=18, win_rate_when_ahead_at_minute=0.79, win_rate_before_minute=0.5, sample_size=200
        ),
        findings=[_finding("what_is_good", "duration_tempo")],
    )

    what_is_costing_you = WhatIsCostingYouSection(
        top_heroes=[
            TopHeroCostingEntry(
                hero_id=1, hero_name="Juggernaut", role="core", games=40, core_contrast=_core_contrast()
            )
        ],
        death_profile=DeathProfile(
            total_deaths=400,
            timing_bands=[
                DeathTimingBand(minute_band_start=0, minute_band_end=10, death_count=40, share_of_deaths=0.1),
                DeathTimingBand(minute_band_start=10, minute_band_end=20, death_count=160, share_of_deaths=0.4),
            ],
            game_state=DeathGameState(ahead_death_share=0.2, behind_death_share=0.5, even_death_share=0.3),
            alone_split=DeathAloneSplit(alone_share=0.61, in_fight_share=0.39),
        ),
        findings=[_finding("what_is_costing_you", "lane_recovery_participation")],
    )

    response_to_a_loss = ResponseToALossSection(
        between_match=BetweenMatchResponse(
            continues_playing_rate=0.7, switches_hero_rate=0.3, requeue_latency_minutes=4.2, sample_size=90
        ),
        in_game=InGameResponse(
            last_hits_at_10_after_loss=35,
            last_hits_at_10_baseline=45,
            first_death_minute_after_loss=6.0,
            first_death_minute_baseline=9.0,
            turbo_switch_rate_after_loss=0.1,
            sample_size=90,
        ),
        findings=[_finding("response_to_a_loss", "post_loss_requeue_latency")],
    )

    what_to_improve = WhatToImproveSection(
        recommendation=_recommendation("last_hits_at_10"),
        runners_up=[_recommendation("first_ward_time"), _recommendation("bkb_timing")],
    )

    archetype = ArchetypeSection(
        tempo="mid", fight_style="frontliner", modifier="streaky", label="Mid Frontliner (Streaky)"
    )

    share_card = ShareCardSection(
        headline_number=HeadlineNumber(label="Hours played", value=310.5, unit="hours"),
        archetype_label="Mid Frontliner (Streaky)",
        contrast_stat=ShareCardContrastStat(label="Last hits at 10", win_value=61, loss_value=39),
    )

    paid_bridge = PaidBridgeSection(
        free_report_limits=["No per-match review", "No opponent-aware analysis"],
        paid_capabilities=["Per-match review", "Matchup-specific reads", "Recommendation tracking"],
    )

    closing = ClosingSection(
        recap_summary="You are a mid-tempo frontliner who wins the fights you show up for.",
        improvement_dimension_key="last_hits_at_10",
        improvement_recap_text="For five games, care about nothing but last hits until minute 10.",
    )

    provenance = ReportProvenance(
        corpus_digest="a" * 64,
        feature_version="v7-features-1.0.0",
        ranking_model_version="v7-ranking-1.0.0",
        generated_at="2026-09-05T00:00:00Z",
    )

    return dict(
        history=history,
        what_is_good=what_is_good,
        what_is_costing_you=what_is_costing_you,
        response_to_a_loss=response_to_a_loss,
        what_to_improve=what_to_improve,
        archetype=archetype,
        share_card=share_card,
        paid_bridge=paid_bridge,
        closing=closing,
        provenance=provenance,
    )


def _valid_payload() -> ReportPayload:
    return ReportPayload(**_valid_payload_kwargs())


def test_fully_populated_payload_is_valid() -> None:
    payload = _valid_payload()
    assert payload.history.wins == 120
    assert payload.what_to_improve.recommendation.dimension_key == "last_hits_at_10"
    assert len(payload.what_to_improve.runners_up) == 2


# ---------------------------------------------------------------------------
# Finding invariants
# ---------------------------------------------------------------------------


def test_finding_rejects_a_score_that_is_not_the_shrunk_position() -> None:
    """``score = |z| * reliability`` is the ranking model's own definition.

    This is the invariant worth enforcing: it is arithmetic, it survives any
    cut points calibration eventually chooses, and it catches a Finding ranked
    by something other than the model.
    """

    with pytest.raises(ValidationError):
        Finding(
            dimension_key="duration_tempo",
            section="what_is_good",
            direction="positive",
            z=1.8,
            reliability=0.9,
            score=0.5,  # should be 1.8 * 0.9 = 1.62
            strength_band="moderate",
            estimate=PointEstimateWithInterval(point=0.4, interval_low=0.2, interval_high=0.6),
            sample_size=120,
            player_facing_question="q",
        )


def test_a_negative_z_still_produces_a_positive_score() -> None:
    """Direction is carried separately; the score is a magnitude."""

    finding = Finding(
        dimension_key="duration_tempo",
        section="what_is_good",
        direction="negative",
        z=-1.8,
        reliability=0.9,
        score=1.62,
        strength_band="pronounced",
        estimate=PointEstimateWithInterval(point=-0.4, interval_low=-0.6, interval_high=-0.2),
        sample_size=120,
        player_facing_question="q",
    )
    assert finding.score > 0


def test_any_strength_band_is_accepted_for_a_given_score() -> None:
    """The contract must not pin itself to provisional cut points.

    Calibration chooses the real ones against the reserved split. A contract
    that hard-coded today's guess would reject every payload built with
    tomorrow's bands.
    """

    for band in ("slight", "moderate", "pronounced"):
        Finding(
            dimension_key="duration_tempo",
            section="what_is_good",
            direction="positive",
            z=1.8,
            reliability=0.9,
            score=1.62,
            strength_band=band,  # type: ignore[arg-type]
            estimate=PointEstimateWithInterval(point=0.4, interval_low=0.2, interval_high=0.6),
            sample_size=120,
            player_facing_question="q",
        )


def test_finding_rejects_reliability_out_of_range() -> None:
    with pytest.raises(ValidationError):
        Finding(
            dimension_key="duration_tempo",
            section="what_is_good",
            direction="positive",
            z=1.8,
            reliability=1.4,
            score=1.62,
            strength_band="pronounced",
            estimate=PointEstimateWithInterval(point=0.4, interval_low=0.2, interval_high=0.6),
            sample_size=120,
            player_facing_question="q",
        )


def test_finding_in_wrong_section_is_rejected() -> None:
    kwargs = _valid_payload_kwargs()
    bad_finding = _finding("what_is_costing_you", "wrong_section_finding")
    kwargs["what_is_good"] = kwargs["what_is_good"].model_copy(
        update={"findings": [*kwargs["what_is_good"].findings, bad_finding]}
    )
    with pytest.raises(ValidationError):
        ReportPayload(**kwargs)


def test_point_estimate_interval_must_contain_point() -> None:
    with pytest.raises(ValidationError):
        PointEstimateWithInterval(point=5.0, interval_low=0.0, interval_high=1.0)


# ---------------------------------------------------------------------------
# What-to-improve invariants
# ---------------------------------------------------------------------------


def test_recommendation_requires_two_runners_up() -> None:
    with pytest.raises(ValidationError):
        WhatToImproveSection(
            recommendation=_recommendation("last_hits_at_10"),
            runners_up=[_recommendation("first_ward_time")],
        )


def test_recommendation_and_runners_up_must_be_distinct() -> None:
    with pytest.raises(ValidationError):
        WhatToImproveSection(
            recommendation=_recommendation("last_hits_at_10"),
            runners_up=[_recommendation("last_hits_at_10"), _recommendation("bkb_timing")],
        )


def test_recommendation_gap_must_match_observation() -> None:
    with pytest.raises(ValidationError):
        RecommendationObservation(win_value=61, loss_value=39, gap=5)


def test_closing_must_reference_the_selected_recommendation() -> None:
    kwargs = _valid_payload_kwargs()
    kwargs["closing"] = kwargs["closing"].model_copy(
        update={"improvement_dimension_key": "some_other_dimension"}
    )
    with pytest.raises(ValidationError):
        ReportPayload(**kwargs)


# ---------------------------------------------------------------------------
# Other section invariants
# ---------------------------------------------------------------------------


def test_hero_entry_role_must_match_contrast_present() -> None:
    with pytest.raises(ValidationError):
        TopHeroGoodEntry(
            hero_id=1,
            hero_name="Juggernaut",
            role="core",
            games=10,
            core_contrast=None,
            support_contrast=_support_contrast(),
        )


def test_death_game_state_shares_must_sum_to_one() -> None:
    with pytest.raises(ValidationError):
        DeathGameState(ahead_death_share=0.5, behind_death_share=0.5, even_death_share=0.5)


def test_death_alone_split_shares_must_sum_to_one() -> None:
    with pytest.raises(ValidationError):
        DeathAloneSplit(alone_share=0.7, in_fight_share=0.7)


def test_archetype_special_label_required_when_special() -> None:
    with pytest.raises(ValidationError):
        ArchetypeSection(
            tempo="mid", fight_style="frontliner", modifier="streaky", label="x", is_special=True
        )


def test_archetype_special_label_forbidden_when_not_special() -> None:
    with pytest.raises(ValidationError):
        ArchetypeSection(
            tempo="mid",
            fight_style="frontliner",
            modifier="streaky",
            label="x",
            is_special=False,
            special_label="Rare One",
        )


def test_history_win_streak_requires_dates_when_positive() -> None:
    with pytest.raises(ValidationError):
        LongestWinStreak(length=3, start_date=None, end_date=None)


def test_history_top_heroes_ranks_must_be_consecutive() -> None:
    kwargs = _valid_payload_kwargs()
    bad_rows = [
        TopHeroHistoryRow(rank=1, hero_id=1, hero_name="A", games=5, win_rate=0.5),
        TopHeroHistoryRow(rank=3, hero_id=2, hero_name="B", games=5, win_rate=0.5),
    ]
    kwargs["history"] = kwargs["history"].model_copy(update={"top_heroes": bad_rows})
    with pytest.raises(ValidationError):
        ReportPayload(**kwargs)


# ---------------------------------------------------------------------------
# No identifiers anywhere in the tree
# ---------------------------------------------------------------------------


def _forbidden_field_names() -> set[str]:
    return {
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


def test_no_model_declares_an_identifier_field() -> None:
    from app.player_analysis_v7 import report_contract as module

    forbidden = _forbidden_field_names()
    checked_any = False
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and issubclass(obj, module.PublicV7Model):
            checked_any = True
            for field_name in obj.model_fields:
                assert field_name not in forbidden, f"{obj.__name__}.{field_name} is an identifier field"
    assert checked_any


def test_serialized_payload_contains_no_identifier_keys() -> None:
    payload = _valid_payload()
    dumped = payload.model_dump(mode="json", by_alias=True)

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                assert key not in _forbidden_field_names()
                walk(nested)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(dumped)


def test_payload_round_trips_through_deepcopy() -> None:
    payload = _valid_payload()
    kwargs = deepcopy(_valid_payload_kwargs())
    ReportPayload(**kwargs)
    assert payload.provenance.corpus_digest == "a" * 64


def test_payload_rejects_bands_that_are_not_monotone_in_score() -> None:
    """A higher-scoring Finding may never carry a weaker band.

    This is the calibration-independent replacement for the old per-Finding
    band check: it constrains the relationship between bands and scores without
    asserting where the cut points fall.
    """

    kwargs = _valid_payload_kwargs()
    strong = _finding("what_is_good", dimension_key="duration_tempo").model_copy(
        update={"z": 2.0, "reliability": 0.9, "score": 1.8, "strength_band": "slight"}
    )
    weak = _finding("what_is_good", dimension_key="hero_novelty").model_copy(
        update={"z": 0.5, "reliability": 0.8, "score": 0.4, "strength_band": "pronounced"}
    )
    kwargs["what_is_good"] = kwargs["what_is_good"].model_copy(
        update={"findings": [strong, weak]}
    )
    with pytest.raises(ValidationError, match="monotone"):
        ReportPayload(**kwargs)


def test_payload_accepts_bands_that_are_monotone_in_score() -> None:
    kwargs = _valid_payload_kwargs()
    strong = _finding("what_is_good", dimension_key="duration_tempo").model_copy(
        update={"z": 2.0, "reliability": 0.9, "score": 1.8, "strength_band": "pronounced"}
    )
    weak = _finding("what_is_good", dimension_key="hero_novelty").model_copy(
        update={"z": 0.5, "reliability": 0.8, "score": 0.4, "strength_band": "slight"}
    )
    kwargs["what_is_good"] = kwargs["what_is_good"].model_copy(
        update={"findings": [strong, weak]}
    )
    assert ReportPayload(**kwargs) is not None


def test_equal_scores_may_carry_different_bands() -> None:
    """Monotonicity constrains ordering, not ties.

    Two Findings with the same score sitting either side of a cut point is a
    presentation choice, not a contract violation.
    """

    kwargs = _valid_payload_kwargs()
    first = _finding("what_is_good", dimension_key="duration_tempo").model_copy(
        update={"z": 1.0, "reliability": 0.5, "score": 0.5, "strength_band": "moderate"}
    )
    second = _finding("what_is_good", dimension_key="hero_novelty").model_copy(
        update={"z": 1.0, "reliability": 0.5, "score": 0.5, "strength_band": "slight"}
    )
    kwargs["what_is_good"] = kwargs["what_is_good"].model_copy(
        update={"findings": [first, second]}
    )
    assert ReportPayload(**kwargs) is not None
