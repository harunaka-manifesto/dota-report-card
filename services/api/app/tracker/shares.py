"""Immutable, privacy-safe share snapshots (profile SSOT §4.8, foundation §12.3).

A share is a timestamped copy of a whitelisted projection. Later corrections,
rebuilds or entitlement changes never alter it. It carries no account, Steam,
match or profile identifiers. The SVG renderer is deterministic and uses the
foundation registry's display names only.
"""
from __future__ import annotations

import html
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Connection, func, select

from .schema import (
    account_matches,
    analyses,
    match_players,
    personal_bests,
    profile_states,
    profiles,
    shares,
)

SNAPSHOT_VERSION = "tracker-share-1"
METRIC_LABELS = {
    "carry.last_hits_at_10.v1": "CS at 10:00",
    "carry.cs_10_to_20.v1": "CS gained 10:00–20:00",
    "carry.net_worth_at_20.v1": "Net Worth at 20:00",
    "carry.dead_time.v1": "Time Spent Dead",
    "carry.hero_damage_share.v1": "Hero Damage Share",
    "carry.tower_damage_share.v1": "Tower Damage Share",
    "mid.lane_net_worth_advantage_at_10.v1": "Mid Lane NW Advantage",
    "mid.level_6_time.v1": "Time Reaching Level 6",
    "mid.early_fight_presence.v1": "Early Fight Presence (to 15:00)",
    "mid.net_worth_at_20.v1": "Mid Net Worth at 20:00",
    "mid.tower_damage_share.v1": "Tower Damage Share",
    "offlane.lane_net_worth_advantage_at_10.v1": "Offlane Lane Pressure",
    "offlane.net_worth_at_10.v1": "Offlane Economy",
    "offlane.fight_presence.v1": "Fight Presence (whole match)",
    "offlane.objective_involvement.v1": "Objective Involvement",
    "support.fight_presence.v1": "Fight Presence",
    "support.observer_wards_placed.v1": "Wards Placed",
    "support.vision_denial.v1": "Vision Denial",
    "support.camps_stacked.v1": "Camps Stacked",
    "support.healing.v1": "Healing",
}


class ShareUnavailable(ValueError):
    pass


def create_share(connection: Connection, *, profile_id: str, kind: str, mode: str,
                 metric_id: str | None = None) -> dict[str, Any]:
    profile = connection.execute(select(profiles).where(profiles.c.id == profile_id)).mappings().one()
    now: datetime = connection.execute(select(func.clock_timestamp())).scalar_one()
    if kind == "PROFILE":
        state = connection.scalar(select(profile_states.c.state).where(
            profile_states.c.profile_id == profile_id, profile_states.c.mode == mode))
        identity = (state or {}).get("identity")
        if not identity or not identity.get("confirmed"):
            # Profile §4.8: unavailable without a confirmed identity line.
            raise ShareUnavailable("IDENTITY_UNCONFIRMED")
        assert state is not None
        projection: dict[str, Any] = {"kind": "PROFILE", "mode": mode, "identity": identity,
                                      "heroes": state.get("heroes", [])}
    elif kind == "PERSONAL_BEST":
        if metric_id not in METRIC_LABELS:
            raise ShareUnavailable("METRIC_INVALID")
        row = connection.execute(select(personal_bests.c.comparison_value, personal_bests.c.role,
                                        analyses.c.match_id).join(
            analyses, analyses.c.id == personal_bests.c.analysis_id).where(
            personal_bests.c.profile_id == profile_id, personal_bests.c.revision == profile["active_revision"],
            personal_bests.c.mode == mode, personal_bests.c.metric_id == metric_id,
        )).first()
        if row is None:
            raise ShareUnavailable("PERSONAL_BEST_UNAVAILABLE")
        source = connection.execute(select(account_matches.c.provider_started_at, match_players.c.hero_id).join(
            match_players, (match_players.c.match_id == account_matches.c.match_id)
            & (match_players.c.player_slot == account_matches.c.player_slot)).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == row.match_id)).one()
        projection = {"kind": "PERSONAL_BEST", "mode": mode, "role": row.role, "metric_id": metric_id,
                      "label": METRIC_LABELS[metric_id], "value": row.comparison_value,
                      "hero_id": source.hero_id, "achieved_on": source.provider_started_at.date().isoformat(),
                      "scope": profile["active_scope"], "revision": profile["active_revision"]}
    else:
        raise ShareUnavailable("KIND_INVALID")
    projection["generated_at"] = now.isoformat()
    share_id = str(uuid4())
    connection.execute(shares.insert().values(id=share_id, profile_id=profile_id, snapshot_version=SNAPSHOT_VERSION,
                                              projection=projection, created_at=now))
    return {"ref": share_id, **projection}


def render_svg(projection: dict[str, Any]) -> str:
    """Deterministic card from the stored projection alone."""
    def text(y: int, value: str, size: int, colour: str = "#F7F4EC") -> str:
        return (f'<text x="48" y="{y}" font-family="Inter, sans-serif" font-size="{size}" '
                f'fill="{colour}">{html.escape(value)}</text>')

    if projection["kind"] == "PERSONAL_BEST":
        value = projection["value"]
        shown = f"{value:g}" if isinstance(value, (int, float)) else "—"
        lines = [text(96, "Personal Best", 28, "#A3A59D"), text(170, projection["label"], 40),
                 text(260, shown, 88), text(330, f"{projection['role'].title()} · {projection['mode'].title()}", 28, "#A3A59D"),
                 text(380, projection["achieved_on"], 24, "#A3A59D")]
    else:
        lines = [text(96, "Profile", 28, "#A3A59D"), text(170, projection["identity"]["template_id"], 36)]
    body = "".join(lines)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="800" height="440" viewBox="0 0 800 440">'
            f'<rect width="800" height="440" rx="24" fill="#141513"/>{body}</svg>')
