"""Luna C grades for the twelve frozen V7 candidates.

The grades are judgements, not computed values, so they live here as data with
their reasons attached and are joined to the measured numbers by
``scripts/v7_statistical_tournament.py summarise``. Every claim in
``justification`` is checkable against the DISCOVERY and CANDIDATE_TEST
artefacts.

Grade meanings, from the task packet:

``A``  strong owner-selectable finalist
``B``  viable but has a material tradeoff
``C``  interesting research, not suitable for the final-five target
``D``  reject
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

VERDICT_VERSION = "v7-luna-c-verdicts-1.0.0"

#: The chronological split-half of the planted negative control landed at
#: -0.073 on DISCOVERY (527 players) and +0.218 on CANDIDATE_TEST (269). A
#: family whose chronological agreement sits inside that band has not
#: demonstrated stability, whatever its point estimate says.
CONTROL_CHRONOLOGICAL_BAND = (-0.073, 0.218)


@dataclass(frozen=True)
class Verdict:
    family: str
    grade: str
    concept: str
    inherited_or_novel: str
    unit_of_observation: str
    estimand: str
    main_confounders: str
    null_model_viability: str
    expected_publication_reach: str
    report_time_cost: str
    narrative_quality: str
    distinctiveness: str
    primary_failure_risk: str
    justification: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


VERDICTS: tuple[Verdict, ...] = (
    Verdict(
        family="post_loss_session_continuation",
        grade="A",
        concept="Does a loss make you keep playing, or stop for the day?",
        inherited_or_novel="inherited (Post-Loss), recast from outcome to behaviour",
        unit_of_observation="one in-session match with a known successor state",
        estimand=(
            "per-player difference in context-adjusted probability that another match "
            "follows inside the session, after a loss versus after a win"
        ),
        main_confounders="time of day, real-life schedule, accumulated session length, right-censoring",
        null_model_viability=(
            "STRONG. Within-player circular shift of the arm labels preserves the real "
            "serial dependence exactly and measures 0.0508/0.0099 on DISCOVERY and "
            "0.0525/0.0104 on CANDIDATE_TEST against nominal 0.05/0.01"
        ),
        expected_publication_reach=(
            "roughly a quarter of information-eligible users at the provisional bar; "
            "structurally near-universal"
        ),
        report_time_cost="history only; one linear pass per player, milliseconds",
        narrative_quality="high - immediately recognisable, non-judgemental, no good/bad reading",
        distinctiveness="high, but rho -0.58 with post_loss_requeue_latency",
        primary_failure_risk="right-censoring at the observation edge and the session-gap convention",
        justification=(
            "Calibrated null on both splits, the highest structural reach in the set, real "
            "heterogeneity that is not an artefact of shrinkage, chronological stability far "
            "above the control band, and per-player estimates that survive every declared probe "
            "at rho >= +0.92"
        ),
    ),
    Verdict(
        family="post_loss_hero_switch",
        grade="A",
        concept="After a loss, do you change hero or run it back?",
        inherited_or_novel="inherited (Post-Loss), recast from outcome to behaviour",
        unit_of_observation="one in-session match transition",
        estimand=(
            "per-player difference in context-adjusted probability the next hero differs, "
            "after a loss versus after a win"
        ),
        main_confounders="hero pool size, mode, party role assignment, non-chosen draft modes",
        null_model_viability=(
            "STRONG. Circular-shift null measures 0.0500/0.0091 on DISCOVERY and "
            "0.0480/0.0087 on CANDIDATE_TEST"
        ),
        expected_publication_reach=(
            "roughly a fifth of information-eligible users at the provisional bar; "
            "structurally near-universal"
        ),
        report_time_cost="history only; one linear pass per player, milliseconds",
        narrative_quality="high - a concrete, visible act the player will recognise",
        distinctiveness="high; no |rho| above 0.30 with any other frozen candidate",
        primary_failure_risk="hero-pool size is a lurking third variable that is not in the projection",
        justification=(
            "The strongest heterogeneity-to-noise ratio among the calibrated families "
            "(tau 0.107, I2 0.845), chronological stability +0.78/+0.74, and the "
            "single-draft/random-draft contamination discovery worried about moves the "
            "per-player estimate by rho +0.993 - that is, not at all"
        ),
    ),
    Verdict(
        family="post_loss_requeue_latency",
        grade="B",
        concept="When you lose, do you jump straight back in or take a breath?",
        inherited_or_novel="inherited (Post-Loss), recast from outcome to behaviour",
        unit_of_observation="one in-session match transition",
        estimand="per-player difference in context-adjusted log gap to the next match, loss versus win",
        main_confounders="queue times, party regrouping, time of day, post-game screen length",
        null_model_viability="STRONG. 0.0488/0.0100 on DISCOVERY and 0.0481/0.0085 on CANDIDATE_TEST",
        expected_publication_reach=(
            "roughly a fifth of information-eligible users at the provisional bar; "
            "structurally near-universal"
        ),
        report_time_cost="history only; one linear pass per player, milliseconds",
        distinctiveness="moderate: rho -0.58 with post_loss_session_continuation",
        narrative_quality="high - 'you are a chaser' is a strong, legible line",
        primary_failure_risk="portfolio redundancy with session continuation, plus definitional sensitivity",
        justification=(
            "Statistically it is as sound as the two A candidates. It is graded B for two "
            "material tradeoffs: it is the most session-gap-sensitive family in the set "
            "(rho +0.913 and tau 0.219 -> 0.263 at a 6 h gap) and it overlaps session "
            "continuation at rho -0.58, so a portfolio should carry one of the two, or one "
            "family with two facets"
        ),
    ),
    Verdict(
        family="transfer_risk",
        grade="B",
        concept="Do you die more when you step off your comfort heroes?",
        inherited_or_novel="inherited (Transfer), recast from outcome to a within-player behavioural contrast",
        unit_of_observation="one product-context match after a 50-match comfort-pool warm-up",
        estimand=(
            "per-player difference in context-adjusted deaths per ten minutes, "
            "stretch heroes versus comfort-pool heroes"
        ),
        main_confounders="hero difficulty, position, pool size; death rate is strongly hero-linked",
        null_model_viability=(
            "STRONG but slightly conservative. 0.0488/0.0082 on DISCOVERY, "
            "0.0447/0.0086 on CANDIDATE_TEST"
        ),
        expected_publication_reach="likely low - about 8% of information-eligible users at the provisional bar",
        report_time_cost="history only; one linear pass per player, milliseconds",
        narrative_quality="high - the idea is vivid and the direction is meaningful",
        distinctiveness="good; rho -0.36 with transfer_activity, its own rejected sibling",
        primary_failure_risk=(
            "the context projection contains hero, which is close to the treatment itself; "
            "removing it raises tau by 55% and chronological stability from +0.47 to +0.61, "
            "so the estimand is not yet pinned down"
        ),
        justification=(
            "The only Transfer form that survives confirmation: chronological stability "
            "+0.467 on DISCOVERY and +0.552 on CANDIDATE_TEST, both clear of the control "
            "band. Its tradeoff is real - only 39/495 and 20/257 players clear the "
            "provisional bar, and the hero-in-projection question must be settled before "
            "the estimand can be called final"
        ),
    ),
    Verdict(
        family="purchase_tempo",
        grade="B",
        concept="How far into a game are you when your build comes together?",
        inherited_or_novel="novel (STRATZ-native item timing)",
        unit_of_observation="one parsed product-context match with at least eight purchases",
        estimand="per-player mean context-adjusted normalised game progress at the eighth item purchase",
        main_confounders="consumables inflate early counts, unverified item vocabulary, position, game length",
        null_model_viability=(
            "WEAK. Calibrated under an i.i.d. null (0.0559/0.0110 and 0.0485/0.0100) but "
            "anticonservative once dependence is planted (0.083/0.020 at range 100, "
            "0.199/0.079 at range 200), and its measured dependence ratio is 4.65 at b=100"
        ),
        expected_publication_reach=(
            "likely high among parsed-eligible research accounts (44/68 and 27/60 clear the "
            "provisional bar) but only 11% of sampled accounts, which is a corpus artefact "
            "rather than a candidate property"
        ),
        report_time_cost="parsed detail required; moderate - one sort of the purchase list per match",
        narrative_quality="high and unusually concrete",
        distinctiveness="moderate: rho +0.47 with fight_timing_centroid",
        primary_failure_risk=(
            "item semantics are unverified in the capability atlas, so the eighth purchase "
            "may be counting consumables; and the level-family standard error cannot be "
            "certified at any block length this corpus supports"
        ),
        justification=(
            "The strongest heterogeneity in the set (I2 0.969, chronological stability +0.94 "
            "and +0.87) and the highest qualified share of any candidate. It is B rather than "
            "A because it is a level family whose p-value is not certifiable, because it "
            "rests on an unverified item vocabulary, and because parsed dependence caps its "
            "research reach"
        ),
    ),
    Verdict(
        family="hero_novelty",
        grade="C",
        concept="How often do you reach for a hero you have not touched in a month?",
        inherited_or_novel="novel",
        unit_of_observation="one product-context match after a 30-match warm-up",
        estimand="per-player mean context-adjusted rate of playing a hero unseen in the previous 30 days",
        main_confounders="match volume above all; hero pool size; patch-driven pool churn",
        null_model_viability=(
            "BROKEN. Anticonservative under every null tested, including the i.i.d. one "
            "(0.0757/0.0194 on DISCOVERY, 0.0655/0.0137 on CANDIDATE_TEST), and it carries "
            "the largest measured dependence in the set at 5.25"
        ),
        expected_publication_reach="moderate, but on an uncertified p-value",
        report_time_cost="history only; one linear pass per player",
        narrative_quality="high",
        distinctiveness="high",
        primary_failure_risk="it is substantially a measure of how much you play",
        justification=(
            "Discovery's own worry is confirmed and is not fixable by the adjustment it "
            "proposed: the per-player estimate correlates -0.526 with log match volume, and "
            "capping exposure at 500 matches only moves that to -0.349. Its test is not "
            "calibrated under any null tested. Interesting, not shippable as it stands"
        ),
    ),
    Verdict(
        family="duration_tempo",
        grade="C",
        concept="Do your games run long or end early?",
        inherited_or_novel="novel (level family)",
        unit_of_observation="one product-context match",
        estimand="per-player mean context-adjusted log match duration",
        main_confounders="game mode (41% of raw variance), lobby type (34%), and nine other players",
        null_model_viability=(
            "BROKEN. Calibrated under an i.i.d. null only; 0.115/0.039 at dependence range 25 "
            "on DISCOVERY and 0.171/0.076 on CANDIDATE_TEST, rising to 0.30/0.15 at range 200"
        ),
        expected_publication_reach="high on the point estimate, but on an uncertified p-value",
        report_time_cost="history only; trivial",
        narrative_quality="moderate - risks a good/bad reading",
        distinctiveness="high",
        primary_failure_risk="it is a ten-player outcome attributed to one player, and half of it is mode mix",
        justification=(
            "Discovery flagged this as its weakest justification and the flag was right. A "
            "player's Turbo-only and standard-only estimates agree at only rho +0.495 across "
            "168 players, against a within-mode reliability near +0.99 - so the pooled number "
            "is substantially a mode-mix statistic, not one personal tempo. Its test is also "
            "the most anticonservative in the set on the confirmation split"
        ),
    ),
    Verdict(
        family="position_flexibility",
        grade="C",
        concept="Are you a one-position player or a fill player?",
        inherited_or_novel="novel",
        unit_of_observation="one pair of consecutive in-session parsed matches",
        estimand="per-player mean context-adjusted probability the position changes between them",
        main_confounders="hero is nearly collinear with position; party role assignment; doubled parsed selection",
        null_model_viability="MIXED. Calibrated to dependence range 25, anticonservative beyond it",
        expected_publication_reach=(
            "likely low: 37 of 116 parsed-eligible DISCOVERY accounts and 32 of 119 on "
            "CANDIDATE_TEST reach information eligibility"
        ),
        report_time_cost="parsed detail required for two consecutive matches; trivial compute",
        narrative_quality="high - one of the most legible ideas in the set",
        distinctiveness="high",
        primary_failure_risk="requiring two consecutive parsed matches compounds parsed selection and destroys reach",
        justification=(
            "Statistically healthy where it applies - I2 0.933, chronological stability +0.80 "
            "and +0.83 - but honest block geometry leaves it reaching 32% and 27% of "
            "parsed-eligible accounts. A good idea that this corpus cannot support"
        ),
    ),
    Verdict(
        family="fight_timing_centroid",
        grade="C",
        concept="Is your game an early game or a late game?",
        inherited_or_novel="novel (STRATZ-native event timing)",
        unit_of_observation="one parsed product-context match with at least three own fight events",
        estimand="per-player mean context-adjusted normalised-progress centroid of own kill and assist times",
        main_confounders="hero, position and role; assist events are timing-only by atlas rule",
        null_model_viability=(
            "WEAK and worse on confirmation: 0.0489/0.0114 at range 25 on DISCOVERY but "
            "0.0946/0.0260 on CANDIDATE_TEST"
        ),
        expected_publication_reach="moderate among parsed-eligible accounts, 11% of sampled",
        report_time_cost="parsed detail required; trivial compute",
        narrative_quality="moderate",
        distinctiveness="moderate: rho +0.47 with purchase_tempo",
        primary_failure_risk="the effect is tiny in player-facing units",
        justification=(
            "Real and stable, but the per-player spread runs from -0.015 to +0.014 of game "
            "progress - about half a minute either side of the population centroid in a "
            "40-minute game. That is too small to narrate honestly, and the null degraded "
            "between the two splits"
        ),
    ),
    Verdict(
        family="transfer_activity",
        grade="D",
        concept="Do you play more quietly on unfamiliar heroes?",
        inherited_or_novel="inherited (Transfer)",
        unit_of_observation="one product-context match after a 50-match comfort-pool warm-up",
        estimand=(
            "per-player difference in context-adjusted kills-plus-assists per ten minutes, "
            "stretch versus comfort"
        ),
        main_confounders="hero difficulty, position, pool size",
        null_model_viability="STRONG - the test is fine; the signal is not",
        expected_publication_reach="likely low and not credible",
        report_time_cost="history only; trivial",
        narrative_quality="moderate",
        distinctiveness="low: rho -0.36 with transfer_risk, which says the same thing better",
        primary_failure_risk="chronological stability fails on the confirmation split",
        justification=(
            "Chronological split-half falls from +0.390 on DISCOVERY to +0.176 on "
            "CANDIDATE_TEST, which is inside the planted negative control's own chronological "
            "band of -0.073 to +0.218. Only 6-7% of players clear the provisional bar. This "
            "is a confirmation failure, and tuning it would be exactly the rescue the phase "
            "forbids"
        ),
    ),
    Verdict(
        family="lead_retention",
        grade="D",
        concept="When your team is decided ahead or behind at the midpoint, does the game convert?",
        inherited_or_novel="novel (STRATZ-native net-worth trajectory)",
        unit_of_observation="one parsed match whose midpoint net-worth lead exceeds 5,000 gold",
        estimand="per-player difference in context-adjusted win indicator, decided-ahead versus decided-behind",
        main_confounders="the arm explains 27.9% of raw variance; four teammates share the trajectory",
        null_model_viability="ADEQUATE but the observed rejection rate barely exceeds it",
        expected_publication_reach="likely negligible",
        report_time_cost="parsed detail required; trivial",
        narrative_quality="moderate",
        distinctiveness="low - it correlates diffusely with several unrelated families, a noise signature",
        primary_failure_risk="the response is a match outcome and the estimand is team-level by construction",
        justification=(
            "5 of 109 and 5 of 112 players clear the provisional bar against a measured "
            "Type-I of 1.4% and 1.0% - that is at most a couple of players' worth of signal. "
            "Chronological stability +0.366 and +0.305 sits at the control band's edge. It is "
            "the outcome form of a family whose outcome form discovery already killed"
        ),
    ),
    Verdict(
        family="lane_recovery_participation",
        grade="D",
        concept="After a lost lane, does your late-game involvement hold up?",
        inherited_or_novel="inherited (Lane Recovery)",
        unit_of_observation="one parsed match with a resolvable own-lane verdict",
        estimand=(
            "per-player difference in context-adjusted own fight events per ten minutes of the "
            "second half of game progress, lost lane versus won lane"
        ),
        main_confounders="lane outcome is a team verdict, not a player verdict; hero and position",
        null_model_viability="STRONG - 0.0507/0.0102 and 0.0498/0.0100; the test is not the problem",
        expected_publication_reach="likely negligible",
        report_time_cost="parsed detail required; trivial",
        narrative_quality="moderate",
        distinctiveness="high but irrelevant at this signal level",
        primary_failure_risk="there is no between-player signal to find",
        justification=(
            "4 of 113 on DISCOVERY and 2 of 113 on CANDIDATE_TEST clear the provisional bar "
            "against a measured Type-I of exactly 1.0% - the confirmation is indistinguishable "
            "from the null. I2 is 0.236 despite a large tau, because the response scale is "
            "large, not because players differ. The rejection is now on the record with a "
            "proper test, which is what discovery asked for"
        ),
    ),
)

VERDICT_BY_FAMILY = {verdict.family: verdict for verdict in VERDICTS}

GRADE_ORDER = ("A", "B", "C", "D")


__all__ = [
    "CONTROL_CHRONOLOGICAL_BAND",
    "GRADE_ORDER",
    "VERDICTS",
    "VERDICT_BY_FAMILY",
    "VERDICT_VERSION",
    "Verdict",
]
