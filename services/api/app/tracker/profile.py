"""Profile projection published at coherent checkpoints (profile SSOT §4–§6A).

A Profile read returns the last published projection for a bucket; it never
recomputes from in-flight history, so imports cannot rewrite it per match.
Checkpoints are published after a live READY match, a settled bootstrap mode,
a role correction, or a rebuild. Only values the SSOT fixes numerically are
derived here: counts, the "so far" identity fallback, role shares and tiers
(with ±3 pp hysteresis) and most-played heroes. Role Shape, Hero Shape and the
other claims, hero tags and Right now depend on provisional parameters the SSOT
names without values (§12); they stay withheld with an explicit reason until an
approved parameter set exists. No provider call is reachable from this module.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from datetime import timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import Connection, func, select
from sqlalchemy.dialects.postgresql import insert

from .evidence import canonical_json
from .schema import (
    account_matches,
    bootstrap,
    coverage,
    dota_accounts,
    events,
    ingest_jobs,
    match_players,
    profile_states,
    profiles,
)
from .scope import entitled

PROFILE_VERSION = "profile-projection-1"
ROLES = ("CARRY", "MID", "OFFLANE", "SUPPORT")
MODES = ("STANDARD", "TURBO")
IDENTITY_WINDOW = 200
ROLE_WINDOW = 100
WINDOW_MONTHS = 24
TIER_HYSTERESIS = 0.03
CAUSES = frozenset({"PLAY", "ROLE_CORRECTION", "IMPORT", "ENTITLEMENT", "METHODOLOGY"})
# Parameters the SSOT names without values (§12). None means withheld.
CLAIM_PARAMETERS: dict[str, Any] | None = None


def _entitled(profile: Any) -> Any:
    return entitled(profile, account_matches)


def _tier(share: float, top: bool, previous: str | None) -> str:
    """Anchor (top, ≥50%) · Regular (≥20%) · Occasional (5–20%) · Rare (<5%).

    A published tier holds until the share leaves its band by more than 3 pp.
    """
    def raw(value: float) -> str:
        if top and value >= 0.5:
            return "ANCHOR"
        return "REGULAR" if value >= 0.2 else "OCCASIONAL" if value >= 0.05 else "RARE"

    bands = {"ANCHOR": (0.5, 1.01), "REGULAR": (0.2, 1.01), "OCCASIONAL": (0.05, 0.2), "RARE": (0.0, 0.05)}
    if previous in bands and (previous != "ANCHOR" or top):
        low, high = bands[previous]
        if low - TIER_HYSTERESIS <= share < high + TIER_HYSTERESIS:
            return previous
    return raw(share)


def build_projection(connection: Connection, *, profile: Any, mode: str,
                     previous: dict[str, Any] | None) -> dict[str, Any]:
    now = connection.execute(select(func.clock_timestamp())).scalar_one()
    horizon = now - timedelta(days=30 * WINDOW_MONTHS)
    visible = _entitled(profile)
    tracked = connection.execute(select(
        func.count(), func.min(account_matches.c.provider_started_at),
        func.max(account_matches.c.provider_started_at),
    ).where(account_matches.c.profile_id == profile["id"], account_matches.c.mode == mode,
            account_matches.c.lifecycle == "READY", visible)).one()
    eligible_rows = connection.execute(select(
        account_matches.c.match_id, account_matches.c.effective_role, account_matches.c.provider_started_at,
        match_players.c.hero_id,
    ).join(match_players, (match_players.c.match_id == account_matches.c.match_id)
           & (match_players.c.player_slot == account_matches.c.player_slot)).where(
        account_matches.c.profile_id == profile["id"], account_matches.c.mode == mode,
        account_matches.c.lifecycle == "READY", account_matches.c.progression == mode,
        account_matches.c.provider_started_at >= horizon, visible,
    ).order_by(account_matches.c.provider_started_at.desc(),
               account_matches.c.provider_source_match_id.desc()).limit(IDENTITY_WINDOW)).mappings().all()
    unassigned = connection.scalar(select(func.count()).where(
        account_matches.c.profile_id == profile["id"], account_matches.c.mode == mode,
        account_matches.c.effective_role.is_(None), account_matches.c.provider_started_at >= horizon,
        account_matches.c.lifecycle.in_(("READY", "UNAVAILABLE")), visible,
    )) or 0
    n = len(eligible_rows)
    counts = Counter(row["effective_role"] for row in eligible_rows)
    ordered_roles = sorted(ROLES, key=lambda role: (-counts[role], ROLES.index(role)))
    top = ordered_roles[0] if n else None
    previous_tiers = {row["role"]: row.get("tier") for row in (previous or {}).get("role_map", [])}
    role_map = []
    for role in ROLES:
        share = counts[role] / n if n else 0.0
        mature = n >= 30
        role_map.append({
            "role": role, "count": counts[role],
            "share": round(share, 4) if mature else None,
            "tier": _tier(share, role == top, previous_tiers.get(role)) if mature else None,
        })
    identity_window_total = n + unassigned
    withheld = identity_window_total > 0 and unassigned / identity_window_total > 0.2
    if n < 10:
        identity = None
    elif top is not None and counts[top] / n >= 0.5:
        identity = {"template_id": "MOSTLY_ROLE_SO_FAR", "slots": {"role": top}, "confirmed": False}
    else:
        identity = {"template_id": "BIT_OF_EVERYTHING", "slots": {}, "confirmed": False}

    heroes = []
    for role in ROLES:
        role_rows = [row for row in eligible_rows if row["effective_role"] == role][:ROLE_WINDOW]
        if not role_rows:
            continue
        played = Counter(row["hero_id"] for row in role_rows)
        most = sorted(played.items(), key=lambda item: (-item[1], item[0]))[:3]
        heroes.append({
            "role": role, "role_matches": len(role_rows),
            "most_played": [{"hero_id": hero_id, "count": count} for hero_id, count in most],
            "tags_state": "INSUFFICIENT_MATCHES" if len(role_rows) < 10 else "CALIBRATION_PENDING",
        })

    recent = [row for row in eligible_rows if row["provider_started_at"] >= now - timedelta(days=90)]
    other = connection.scalar(select(func.count()).where(
        account_matches.c.profile_id == profile["id"], account_matches.c.mode != mode,
        account_matches.c.mode.in_(MODES), account_matches.c.lifecycle == "READY",
        account_matches.c.progression == account_matches.c.mode,
        account_matches.c.provider_started_at >= now - timedelta(days=90), visible,
    )) or 0
    share_recent = len(recent) / (len(recent) + other) if recent or other else None
    earliest_known = connection.scalar(select(func.min(coverage.c.start_at)).where(
        coverage.c.profile_id == profile["id"], coverage.c.mode == mode,
        coverage.c.evidence_class == "SUMMARY", coverage.c.state == "KNOWN",
    ))
    return {
        "version": PROFILE_VERSION, "mode": mode,
        "header": {
            "tracked_count": tracked[0], "eligible_count": n,
            "first_match_at": tracked[1].isoformat() if tracked[1] else None,
            "last_played_at": tracked[2].isoformat() if tracked[2] else None,
            "getting_to_know": n < 10,
            "mostly_this_mode": share_recent is not None and share_recent >= 0.7,
            "recent_eligible_count": len(recent),
        },
        "identity": identity,
        "role_shape_withheld": "UNASSIGNED_ROLES" if withheld else None,
        "role_map": role_map, "unassigned_count": unassigned,
        "heroes": heroes,
        "claims_state": "CALIBRATION_PENDING" if CLAIM_PARAMETERS is None else "EVALUATED",
        "claims": [],
        "right_now_state": "CALIBRATION_PENDING",
        "coverage": {"earliest_known_at": earliest_known.isoformat() if earliest_known else None},
    }


def _import_running(connection: Connection, profile_id: str, mode: str) -> bool:
    settled = connection.scalar(select(bootstrap.c.completed_at).where(
        bootstrap.c.profile_id == profile_id, bootstrap.c.mode == mode,
    ))
    has_bootstrap = connection.scalar(select(bootstrap.c.profile_id).where(
        bootstrap.c.profile_id == profile_id, bootstrap.c.mode == mode,
    )) is not None
    return has_bootstrap and settled is None


def publish_profile_checkpoint(connection: Connection, *, profile_id: str, cause: str,
                               modes: tuple[str, ...] = MODES) -> list[str]:
    """Publish the current coherent projection for each settled bucket.

    The caller owns the transaction (it already holds the profile lock or is
    the publication transaction of a finalization/rebuild). A bucket whose
    bootstrap is still importing keeps its previous checkpoint. A changed
    confirmed identity writes one in-app change event; the first publication
    and unconfirmed fallbacks write none.
    """
    if cause not in CAUSES:
        raise ValueError("Unsupported Profile change cause")
    profile = connection.execute(select(profiles).where(
        profiles.c.id == profile_id, profiles.c.active.is_(True),
    )).mappings().one_or_none()
    if profile is None:
        return []
    published: list[str] = []
    for mode in modes:
        if _import_running(connection, profile_id, mode):
            continue
        prior = connection.execute(select(profile_states).where(
            profile_states.c.profile_id == profile_id, profile_states.c.mode == mode,
        ).with_for_update()).mappings().one_or_none()
        state = build_projection(connection, profile=profile, mode=mode,
                                 previous=prior["state"] if prior else None)
        digest = hashlib.sha256(canonical_json(state)).hexdigest()
        if prior is not None and prior["digest"] == digest and prior["revision"] == profile["active_revision"]:
            continue
        seq = (prior["checkpoint_seq"] + 1) if prior else 1
        values = dict(revision=profile["active_revision"], checkpoint_seq=seq, cause=cause, state=state,
                      digest=digest, published_at=func.clock_timestamp())
        connection.execute(insert(profile_states).values(profile_id=profile_id, mode=mode, **values)
                           .on_conflict_do_update(index_elements=[profile_states.c.profile_id,
                                                                  profile_states.c.mode], set_=values))
        before = _confirmed(prior["state"]) if prior else None
        after = _confirmed(state)
        if prior is not None and before != after:
            connection.execute(insert(events).values(
                id=str(uuid4()), profile_id=profile_id, kind="PROFILE_CHANGE",
                dedup_key=f"profile-change:{profile_id}:{mode}:{seq}",
                payload={"mode": mode, "cause": cause, "before": before, "after": after,
                         "checkpoint_seq": seq},
                created_at=func.clock_timestamp(),
            ).on_conflict_do_nothing())
        published.append(mode)
    return published


def _confirmed(state: dict[str, Any]) -> dict[str, Any]:
    identity = state.get("identity")
    return {"identity": identity if identity and identity.get("confirmed") else None,
            "claims": [claim for claim in state.get("claims", []) if claim.get("state") in {"CONFIRMED", "FADING"}]}


def data_access_blocked(connection: Connection, account_id: int) -> bool:
    return connection.scalar(select(dota_accounts.c.visibility).where(
        dota_accounts.c.account_id == account_id,
    )) == "BLOCKED"


def more_arriving(connection: Connection, profile_id: str, mode: str) -> bool:
    if _import_running(connection, profile_id, mode):
        return True
    pending = connection.scalar(select(coverage.c.id).where(
        coverage.c.profile_id == profile_id, coverage.c.mode == mode, coverage.c.state == "PENDING",
    ).limit(1))
    backfill = connection.scalar(select(ingest_jobs.c.id).where(
        ingest_jobs.c.profile_id == profile_id, ingest_jobs.c.job_type == "PRO_BACKFILL",
        ingest_jobs.c.state.in_(("PENDING", "RUNNING")),
    ).limit(1))
    return pending is not None or backfill is not None
