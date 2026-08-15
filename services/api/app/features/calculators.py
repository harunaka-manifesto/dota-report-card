from __future__ import annotations

from dataclasses import replace

from app.features.models import MatchFeature
from app.features.roles import infer_role
from app.ingestion.normalize import NormalizedMatch


def calculate_match_feature(match: NormalizedMatch) -> MatchFeature:
    role_inference = infer_role(match.participants, match.account_id)
    participant = match.target_participant
    feature = MatchFeature(
        match_id=match.match_id,
        account_id=match.account_id,
        start_time=match.start_time,
        hero_id=participant.hero_id,
        role=role_inference.role,
        role_probability=role_inference.probability,
        role_method=role_inference.method,
        role_signals=role_inference.signals,
        rank_tier=participant.rank_tier or match.rank_tier,
        patch=match.patch,
        side="radiant" if match.radiant else "dire",
        won=match.won,
        duration_seconds=match.duration_seconds,
        kills=participant.kills,
        deaths=participant.deaths,
        assists=participant.assists,
        last_hits=participant.last_hits,
        denies=participant.denies,
        gold_per_min=participant.gold_per_min,
        xp_per_min=participant.xp_per_min,
        net_worth=participant.net_worth,
        gold_spent=participant.gold_spent,
        hero_damage=participant.hero_damage,
        tower_damage=participant.tower_damage,
        hero_healing=participant.hero_healing,
        obs_placed=participant.obs_placed,
        sen_placed=participant.sen_placed,
        party_size=participant.party_size,
        item_ids=participant.item_ids,
        item_timings=participant.item_timings,
        time_series=match.time_series,
        objective_count=len(match.objectives),
        teamfight_count=len(match.teamfights),
        parsed_coverage=match.coverage.replay_coverage,
        coverage=match.coverage,
        source_match_ids=(match.match_id,),
    )
    derived = {
        "kda": (participant.kills + participant.assists) / max(participant.deaths, 1),
        "economy_impact_efficiency": feature.impact_score / max(participant.gold_per_min, 1),
        "tower_share_proxy": participant.tower_damage
        / max(participant.hero_damage + participant.tower_damage, 1),
        "ward_events": float(participant.obs_placed + participant.sen_placed),
        "kill_events": float(
            sum(1 for event in participant.events if event.event_type == "kill")
        ),
        "early_death": 1.0
        if any(
            event.event_type == "death" and (event.time_seconds or 9999) <= 600
            for event in participant.events
        )
        else 0.0,
    }
    if participant.death_events_available:
        derived["death_events"] = float(
            sum(1 for event in participant.events if event.event_type == "death")
        )
    return replace(feature, derived=derived)


def calculate_match_features(matches: list[NormalizedMatch]) -> list[MatchFeature]:
    return [calculate_match_feature(match) for match in matches]
