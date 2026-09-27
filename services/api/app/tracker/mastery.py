"""Award-time Role Mastery facts. Analytical replays never rewrite this ledger."""
from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import Connection, exists, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert

from .history import Observation, load_prior_observations, personal_best
from .metrics import metric_ids
from .population_parameters import current_context_parameters
from .rebuild import stale_analysis
from .schema import (
    account_matches,
    analyses,
    bootstrap,
    events,
    mastery_ledger,
    metric_observations,
    profiles,
)
from .scope import entitled

# v2: bonus evidence comes only from the four canonical metrics of each role.
# v1 rows (which could cite retired metrics) stay as audit history and never count.
RULE_VERSION = "role-mastery-v2"
CURVE_VERSION = "role-mastery-curve-v1"
ROLES = ("CARRY", "MID", "OFFLANE", "SUPPORT")
MODES = ("STANDARD", "TURBO")
CURRENT_RULE = mastery_ledger.c.rule_version == RULE_VERSION


def mastery_state(connection: Connection, profile: Any) -> Literal["AVAILABLE", "BACKFILLING", "CALIBRATION_PENDING"]:
    if current_context_parameters(connection) is None:
        return "CALIBRATION_PENDING"
    importing = connection.scalar(select(bootstrap.c.mode).where(
        bootstrap.c.profile_id == profile["id"], bootstrap.c.completed_at.is_(None),
    ).limit(1))
    awarded = exists(select(mastery_ledger.c.id).where(
        mastery_ledger.c.profile_id == account_matches.c.profile_id,
        mastery_ledger.c.match_id == account_matches.c.match_id,
        mastery_ledger.c.kind == "AWARD", CURRENT_RULE,
    ))
    missing = connection.scalar(select(account_matches.c.match_id).where(
        account_matches.c.profile_id == profile["id"], account_matches.c.lifecycle == "READY",
        account_matches.c.progression.in_(MODES), entitled(profile, account_matches),
        ~awarded,
    ).limit(1))
    return "BACKFILLING" if importing is not None or missing is not None else "AVAILABLE"


def level_for_xp(xp: int) -> tuple[int | None, int, int | None]:
    """Earned level, XP within it, and XP needed for the next level."""
    if xp <= 0:
        return None, 0, None
    remaining = xp
    for level in range(1, 99):
        needed = 2_000 + 300 * ((level - 1) // 5)
        if remaining < needed:
            return level, remaining, needed
        remaining -= needed
    return 99, remaining, None


def award_xp(mode: str, above: list[str], pbs: list[str]) -> int:
    if mode not in MODES:
        raise ValueError("Unsupported mastery mode")
    standard = 100 + 10 * min(len(set(above)), 2) + 20 * min(len(set(pbs)), 2)
    return standard if mode == "STANDARD" else standard // 2


def role_total(connection: Connection, profile_id: str, role: str) -> int:
    return int(connection.scalar(select(func.coalesce(func.sum(mastery_ledger.c.xp), 0)).where(
        mastery_ledger.c.profile_id == profile_id, mastery_ledger.c.role == role, CURRENT_RULE,
    )) or 0)


def _facts_from_built(built: dict[str, Any], role: str) -> tuple[list[str], list[str]]:
    canonical = set(metric_ids(role))
    above = sorted(row["metric_id"] for row in built["metric_rows"]
                   if row["metric_id"] in canonical and row["performance_state"] == "ABOVE")
    pbs = sorted(row["metric_id"] for row in built["pb_rows"]
                 if row["metric_id"] in canonical and row["pb"]["state"] == "READY"
                 and row["pb"]["source_match_id"] == row["current"].match_id)
    return above[:2], pbs[:2]


def _facts_from_stored(connection: Connection, link: dict[str, Any], analysis: dict[str, Any]) -> tuple[list[str], list[str]]:
    # ponytail: per-metric prior reads; use one chronological scan if large backfills become slow.
    rows = connection.execute(select(metric_observations).where(
        metric_observations.c.analysis_id == analysis["id"],
        metric_observations.c.metric_id.in_(metric_ids(link["effective_role"])),
    ).order_by(metric_observations.c.metric_id)).mappings().all()
    above = [row["metric_id"] for row in rows if row["performance_state"] == "ABOVE"][:2]
    pbs: list[str] = []
    for row in rows:
        if row["comparison_value"] is None:
            continue
        current = Observation(link["match_id"], link["provider_started_at"], link["mode"],
                              link["effective_role"], row["metric_id"], row["comparison_value"], True)
        priors = load_prior_observations(connection, profile_id=link["profile_id"], current=current,
                                         analysis_version=analysis["analysis_version"],
                                         baseline_version=analysis["baseline_version"])
        pb = personal_best(current, priors)
        if pb["state"] == "READY" and pb["source_match_id"] == link["match_id"]:
            pbs.append(row["metric_id"])
    return above, pbs[:2]


def _source(analysis: dict[str, Any], above: list[str], pbs: list[str], *, reason: str) -> dict[str, Any]:
    return {"reason": reason, "base_standard_xp": 100, "above_metric_ids": above,
            "pb_metric_ids": pbs, "analysis_version": analysis["analysis_version"],
            "baseline_version": analysis["baseline_version"],
            "parameter_set_version": analysis["result"].get("parameter_set_version")}


def _insert(connection: Connection, *, link: dict[str, Any], kind: str, xp: int,
            source_analysis_id: str, source: dict[str, Any], key: str, role: str | None = None) -> bool:
    if xp == 0:
        return False
    inserted = connection.execute(insert(mastery_ledger).values(
        id=str(uuid4()), profile_id=link["profile_id"], match_id=link["match_id"],
        mode=link["mode"], role=role or link["effective_role"], kind=kind, xp=xp,
        source_analysis_id=source_analysis_id, rule_version=RULE_VERSION, source=source,
        dedup_key=key, created_at=func.clock_timestamp(),
    ).on_conflict_do_nothing(index_elements=[mastery_ledger.c.dedup_key])
        .returning(mastery_ledger.c.id)).scalar_one_or_none()
    return inserted is not None


def _methodology_pending(connection: Connection, link: dict[str, Any]) -> bool:
    """A visible same-mode match at or before this one still awaits a methodology rebuild.

    Its facts (and this match's priors) are not yet current truth, so the award waits
    for the rebuild's quiet backfill instead of snapshotting a transitional analysis.
    """
    profile = connection.execute(select(profiles).where(profiles.c.id == link["profile_id"])).mappings().one()
    key = tuple_(account_matches.c.provider_started_at, account_matches.c.provider_source_match_id)
    return connection.scalar(select(account_matches.c.match_id).join(
        analyses, analyses.c.id == account_matches.c.active_analysis_id,
    ).where(
        account_matches.c.profile_id == link["profile_id"], account_matches.c.mode == link["mode"],
        account_matches.c.lifecycle == "READY", entitled(profile, account_matches),
        key <= (link["provider_started_at"], link["provider_source_match_id"]),
        stale_analysis(connection),
    ).limit(1)) is not None


def award_match(connection: Connection, *, profile_id: str, match_id: int,
                reason: str, built: dict[str, Any] | None = None, live: bool = False) -> bool:
    """Append one award only after a coherent READY publication and approved calibration."""
    if current_context_parameters(connection) is None:
        return False
    link = connection.execute(select(account_matches).where(
        account_matches.c.profile_id == profile_id, account_matches.c.match_id == match_id,
    )).mappings().one()
    if (link["lifecycle"] != "READY" or link["progression"] not in MODES
            or link["effective_role"] not in ROLES):
        return False
    analysis = connection.execute(select(analyses).where(
        analyses.c.id == link["active_analysis_id"],
    )).mappings().one()
    if analysis["result"].get("parameter_set_version") is None or _methodology_pending(connection, dict(link)):
        return False
    above, pbs = (_facts_from_built(built, link["effective_role"]) if built is not None
                  else _facts_from_stored(connection, dict(link), dict(analysis)))
    previous = role_total(connection, profile_id, link["effective_role"]) if live else 0
    inserted = _insert(connection, link=dict(link), kind="AWARD", xp=award_xp(link["mode"], above, pbs),
                       source_analysis_id=analysis["id"], source=_source(dict(analysis), above, pbs, reason=reason),
                       key=f"mastery:award:{RULE_VERSION}:{profile_id}:{match_id}")
    if inserted and live:
        before = level_for_xp(previous)[0] or 0
        after = level_for_xp(role_total(connection, profile_id, link["effective_role"]))[0] or 0
        scope = connection.scalar(select(profiles.c.active_scope).where(profiles.c.id == profile_id))
        for level in range(before + 1, after + 1):
            if scope == "PRO" or level <= 5:
                connection.execute(insert(events).values(
                    id=str(uuid4()), profile_id=profile_id, kind="MASTERY_LEVEL",
                    dedup_key=f"mastery:level:{profile_id}:{link['effective_role']}:{level}",
                    payload={"role": link["effective_role"], "level": level,
                             "curve_version": CURVE_VERSION, "match_id": match_id},
                    created_at=func.clock_timestamp(),
                ).on_conflict_do_nothing())
    return inserted


def award_retained(connection: Connection, *, profile_id: str,
                   origins: set[str] | None = None, reason: str = "HISTORICAL_IMPORT") -> int:
    """Backfill stored finalized matches in match chronology, without celebrations."""
    if current_context_parameters(connection) is None:
        return 0
    query = select(account_matches.c.match_id).where(
        account_matches.c.profile_id == profile_id, account_matches.c.lifecycle == "READY",
        account_matches.c.progression.in_(MODES),
    )
    if origins is not None:
        query = query.where(account_matches.c.origin.in_(origins))
    ids = connection.scalars(query.order_by(
        account_matches.c.provider_started_at, account_matches.c.provider_source_match_id,
    )).all()
    return sum(award_match(connection, profile_id=profile_id, match_id=match_id,
                           reason=reason) for match_id in ids)


def add_late_bonus(connection: Connection, *, profile_id: str, match_id: int,
                   built: dict[str, Any]) -> bool:
    """Add only newly available evidence, never retract old award-time bonuses."""
    link = connection.execute(select(account_matches).where(
        account_matches.c.profile_id == profile_id, account_matches.c.match_id == match_id,
    )).mappings().one()
    positive = connection.execute(select(mastery_ledger).where(
        mastery_ledger.c.profile_id == profile_id, mastery_ledger.c.match_id == match_id,
        mastery_ledger.c.role == link["effective_role"], mastery_ledger.c.xp > 0, CURRENT_RULE,
    )).mappings().all()
    if not positive or built["parameter_set_version"] is None:
        return False
    credited_above = {metric for row in positive for metric in row["source"].get("above_metric_ids", [])}
    credited_pbs = {metric for row in positive for metric in row["source"].get("pb_metric_ids", [])}
    above, pbs = _facts_from_built(built, link["effective_role"])
    new_above = [metric for metric in above if metric not in credited_above][:max(0, 2 - len(credited_above))]
    new_pbs = [metric for metric in pbs if metric not in credited_pbs][:max(0, 2 - len(credited_pbs))]
    standard_bonus = 10 * len(new_above) + 20 * len(new_pbs)
    if not standard_bonus:
        return False
    analysis = connection.execute(select(analyses).where(
        analyses.c.id == link["active_analysis_id"],
    )).mappings().one()
    source = _source(dict(analysis), new_above, new_pbs, reason="LATE_REPLAY")
    source["base_standard_xp"] = 0
    return _insert(connection, link=dict(link), kind="LATE_BONUS",
                   xp=standard_bonus if link["mode"] == "STANDARD" else standard_bonus // 2,
                   source_analysis_id=analysis["id"], source=source,
                   key=f"mastery:replay:{RULE_VERSION}:{profile_id}:{match_id}:{analysis['id']}")


def move_corrected_match(connection: Connection, *, profile_id: str, match_id: int,
                         previous_role: str, revision: int) -> None:
    """Move only the corrected match's net XP; later awards remain snapshots."""
    rows = connection.execute(select(mastery_ledger).where(
        mastery_ledger.c.profile_id == profile_id, mastery_ledger.c.match_id == match_id,
        mastery_ledger.c.role == previous_role, CURRENT_RULE,
    )).mappings().all()
    net = sum(row["xp"] for row in rows)
    if net <= 0:
        return
    link = dict(connection.execute(select(account_matches).where(
        account_matches.c.profile_id == profile_id, account_matches.c.match_id == match_id,
    )).mappings().one())
    positive = [row for row in rows if row["xp"] > 0]
    source = {**positive[0]["source"], "reason": "ROLE_CORRECTION", "from_role": previous_role}
    source["above_metric_ids"] = sorted({metric for row in positive
                                         for metric in row["source"].get("above_metric_ids", [])})
    source["pb_metric_ids"] = sorted({metric for row in positive
                                      for metric in row["source"].get("pb_metric_ids", [])})
    _insert(connection, link=link, kind="REVERSAL", xp=-net, role=previous_role,
            source_analysis_id=positive[0]["source_analysis_id"], source=source,
            key=f"mastery:correction:{RULE_VERSION}:{profile_id}:{match_id}:{revision}:reverse")
    _insert(connection, link=link, kind="CORRECTION", xp=net,
            source_analysis_id=positive[0]["source_analysis_id"], source=source,
            key=f"mastery:correction:{RULE_VERSION}:{profile_id}:{match_id}:{revision}:award")
