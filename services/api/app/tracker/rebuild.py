"""Deterministic rebuilds of current truth from retained evidence.

Entitlement scope changes, methodology/version bumps and context parameter-set
changes all replay the same path used at finalization: stored snapshots and
feature projections in, analyses and current index rows out. No provider call
is reachable from here. Each rebuild publishes in one transaction under the
user → profile lock order, so a consumer sees either the previous coherent
state or the complete new one, never a mixed timeline (app_foundation §14.3).

Append-only events are never created, retracted or replayed by a rebuild,
except the single in-app scope-change summary allowed by settings §5.1.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Connection, Engine, func, or_, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert

from .backfill import historical_work_pending
from .finalization import (
    ANALYSIS_VERSION,
    FEATURE_VERSION,
    build_analysis,
    publish_analysis,
    recompute_indexes,
)
from .history import BASELINE_VERSION
from .jobs import StaleJob, authorized_job, enqueue, finish, reschedule
from .materialization import materialize_snapshot
from .population_parameters import current_context_parameters
from .schema import (
    account_matches,
    analyses,
    analysis_inputs,
    derived_features,
    events,
    history_operations,
    matches,
    profiles,
    snapshots,
    subscriptions,
)
from .scope import entitled

MODES = ("STANDARD", "TURBO")


class RebuildUnavailable(ValueError):
    """Retained evidence cannot reproduce part of the closure; keep prior state."""


def _visible(profile: Any) -> Any:
    return entitled(profile, account_matches)


def rebuild_inputs(connection: Connection, link: dict[str, Any]) -> dict[str, Any]:
    """Resolve the one retained source of a READY link at the current feature version.

    A projection missing for a newer feature version is re-materialized from the
    stored snapshot (no provider I/O). A source without an inline payload cannot
    be replayed and fails the whole closure.
    """
    source_ids = connection.scalars(select(analysis_inputs.c.snapshot_id).where(
        analysis_inputs.c.analysis_id == link["active_analysis_id"],
    ).order_by(analysis_inputs.c.snapshot_id)).all()
    if len(source_ids) != 1:
        raise RebuildUnavailable("Analysis source lineage is unavailable")
    source_id = source_ids[0]
    snapshot = connection.execute(select(snapshots.c.payload).where(snapshots.c.id == source_id)).first()
    if snapshot is None or snapshot.payload is None:
        raise RebuildUnavailable("Retained source payload is unavailable")

    def projection() -> list[Any]:
        return list(connection.execute(select(derived_features).where(
            derived_features.c.match_id == link["match_id"],
            derived_features.c.feature_version == FEATURE_VERSION,
            derived_features.c.provenance["snapshot_id"].astext == source_id,
        ).order_by(derived_features.c.player_slot, derived_features.c.created_at)).mappings())

    rows = projection()
    if not rows:
        materialize_snapshot(connection, snapshot_id=source_id, match_id=link["match_id"])
        rows = projection()
    digests = {row["inputs_digest"] for row in rows}
    if len(digests) != 1 or [row["player_slot"] for row in rows] != list(range(10)):
        raise RebuildUnavailable("Retained feature projection is incomplete")
    match = dict(connection.execute(select(matches).where(matches.c.match_id == link["match_id"])).mappings().one())
    return {"features": [row["features"] for row in rows], "feature_digest": digests.pop(),
            "snapshot_ids": [source_id], "match": match}


def replay_closure(connection: Connection, *, profile: Any, modes: tuple[str, ...],
                   start: dict[str, tuple[Any, int] | None] | None = None, inclusive: bool = True) -> int:
    """Recompute READY links visible under the profile's in-transaction scope.

    `start` limits each mode to links at or after a chronology key (strictly
    after when not `inclusive`): that is the smallest closure, since only later
    observations read an earlier value.
    """
    rebuilt = 0
    for mode in modes:
        query = select(account_matches).where(
            account_matches.c.profile_id == profile["id"], account_matches.c.mode == mode,
            account_matches.c.lifecycle == "READY", account_matches.c.active_analysis_id.is_not(None),
            _visible(profile),
        )
        boundary = (start or {}).get(mode)
        if start is not None and boundary is None:
            continue
        if boundary is not None:
            key = tuple_(account_matches.c.provider_started_at, account_matches.c.provider_source_match_id)
            query = query.where(key >= boundary if inclusive else key > boundary)
        links = [dict(row) for row in connection.execute(query.order_by(
            account_matches.c.provider_started_at, account_matches.c.provider_source_match_id,
        ).with_for_update()).mappings()]
        sources = {link["match_id"]: rebuild_inputs(connection, link) for link in links}
        for link in links:
            inputs = sources[link["match_id"]]
            built = build_analysis(connection, profile_id=profile["id"], link=link, match=inputs["match"],
                                   features=inputs["features"], snapshot_ids=inputs["snapshot_ids"],
                                   feature_digest=inputs["feature_digest"])
            publish_analysis(connection, profile_id=profile["id"], link=link, match=inputs["match"],
                             built=built, snapshot_ids=inputs["snapshot_ids"],
                             feature_digest=inputs["feature_digest"])
            rebuilt += 1
        recompute_indexes(connection, profile_id=profile["id"], revision=profile["active_revision"], mode=mode)
    return rebuilt


# -- entitlement scope -------------------------------------------------------------

def enqueue_scope_rebuild(connection: Connection, *, profile_id: str, operation_id: str) -> str:
    return enqueue(connection, dedup_key=f"scope-rebuild:{operation_id}", job_type="SCOPE_REBUILD",
                   priority=3, profile_id=profile_id, payload={"operation_id": operation_id})


def _desired_scope(connection: Connection, user_id: str, now: datetime | None) -> str:
    if now is None:
        now = connection.execute(select(func.clock_timestamp())).scalar_one()
    live = connection.execute(select(subscriptions.c.original_transaction_id).where(
        subscriptions.c.user_id == user_id, subscriptions.c.expires_at > now,
        or_(subscriptions.c.revoked_at.is_(None), subscriptions.c.revoked_at > now),
    ).limit(1)).first()
    return "PRO" if live else "FREE"


def run_scope_rebuild(connection: Connection, *, profile_id: str, operation_id: str,
                      now: datetime | None = None) -> str:
    """Replay retained history under the target scope and publish it atomically.

    Must run inside a transaction already holding the user and profile locks.
    The cutoff is every READY link at this instant: the profile lock stops new
    finalizations until commit, and later ones finalize under the new scope.
    """
    operation = connection.execute(select(history_operations).where(
        history_operations.c.id == operation_id, history_operations.c.profile_id == profile_id,
    ).with_for_update()).mappings().one_or_none()
    profile = connection.execute(select(profiles).where(
        profiles.c.id == profile_id, profiles.c.active.is_(True),
    ).with_for_update()).mappings().one_or_none()
    if operation is None or profile is None or operation["state"] not in {"PENDING", "RUNNING"}:
        return "STALE"
    if operation["target_scope"] != _desired_scope(connection, profile["user_id"], now):
        connection.execute(update(history_operations).where(history_operations.c.id == operation_id)
                           .values(state="CANCELLED", completed_at=func.clock_timestamp()))
        return "CANCELLED"
    if operation["target_scope"] == "PRO" and historical_work_pending(connection, profile_id):
        # Keep the coherent Free state active until Pro acquisition catches up.
        connection.execute(update(history_operations).where(history_operations.c.id == operation_id)
                           .values(state="RUNNING"))
        return "WAITING_FOR_HISTORY"
    target_revision = profile["active_revision"] + 1
    connection.execute(update(profiles).where(profiles.c.id == profile_id).values(
        active_scope=operation["target_scope"], active_revision=target_revision,
    ))
    staged = {**dict(profile), "active_scope": operation["target_scope"], "active_revision": target_revision}
    count = replay_closure(connection, profile=staged, modes=MODES)
    cutoff = connection.execute(select(account_matches.c.provider_started_at, account_matches.c.match_id).where(
        account_matches.c.profile_id == profile_id, account_matches.c.lifecycle == "READY",
    ).order_by(account_matches.c.provider_started_at.desc(), account_matches.c.match_id.desc()).limit(1)).first()
    connection.execute(update(history_operations).where(history_operations.c.id == operation_id).values(
        state="COMPLETE", completed_at=func.clock_timestamp(), target_revision=target_revision,
        cutoff_started_at=cutoff.provider_started_at if cutoff else None,
        cutoff_match_id=cutoff.match_id if cutoff else None,
        cursor={"rebuilt_links": count},
    ))
    # One in-app summary that historical scope changed; never per match, never a push.
    connection.execute(insert(events).values(
        id=str(uuid4()), profile_id=profile_id, kind="SCOPE_CHANGED",
        dedup_key=f"scope:{operation_id}",
        payload={"scope": operation["target_scope"], "revision": target_revision},
        created_at=func.clock_timestamp(),
    ).on_conflict_do_nothing())
    from .profile import publish_profile_checkpoint

    publish_profile_checkpoint(connection, profile_id=profile_id, cause="ENTITLEMENT")
    return "COMPLETE"


def complete_scope_rebuild_job(database: Engine, *, job_id: str, lease_token: str) -> str:
    with authorized_job(database, job_id, lease_token) as (connection, job):
        if job["job_type"] != "SCOPE_REBUILD" or job["profile_id"] is None:
            raise ValueError("Expected scope rebuild work")
        try:
            # A savepoint discards a partial replay; the previous coherent scope stays.
            with connection.begin_nested():
                outcome = run_scope_rebuild(connection, profile_id=job["profile_id"],
                                            operation_id=job["payload"]["operation_id"])
        except RebuildUnavailable:
            outcome = "UNAVAILABLE"
        if outcome == "WAITING_FOR_HISTORY":
            reschedule(connection, job, delay_seconds=60, error="AWAITING_HISTORY", failure=False)
            return outcome
        if outcome == "UNAVAILABLE":
            connection.execute(update(history_operations).where(
                history_operations.c.id == job["payload"]["operation_id"],
            ).values(state="FAILED", completed_at=func.clock_timestamp()))
        finish(connection, job)
        return outcome


# -- methodology and parameter-set replay --------------------------------------------

def stale_boundaries(connection: Connection, profile_id: str) -> dict[str, tuple[Any, int] | None]:
    parameters = current_context_parameters(connection)
    version = parameters.version if parameters is not None else None
    boundaries: dict[str, tuple[Any, int] | None] = {}
    stamped = analyses.c.result["parameter_set_version"].astext
    for mode in MODES:
        row = connection.execute(select(
            account_matches.c.provider_started_at, account_matches.c.provider_source_match_id,
        ).join(analyses, analyses.c.id == account_matches.c.active_analysis_id).where(
            account_matches.c.profile_id == profile_id, account_matches.c.mode == mode,
            account_matches.c.lifecycle == "READY",
            or_(analyses.c.analysis_version != ANALYSIS_VERSION,
                analyses.c.baseline_version != BASELINE_VERSION,
                analyses.c.feature_version != FEATURE_VERSION,
                stamped.is_distinct_from(version)),
        ).order_by(account_matches.c.provider_started_at, account_matches.c.provider_source_match_id)
            .limit(1)).first()
        boundaries[mode] = (row.provider_started_at, row.provider_source_match_id) if row else None
    return boundaries


def run_methodology_rebuild(connection: Connection, *, profile_id: str) -> int:
    """Bring every stale active analysis under the one current methodology.

    Must run holding the user and profile locks. Each bucket replays forward
    from its earliest stale chronology point; an unaffected bucket is untouched.
    Running it again finds nothing stale and changes nothing.
    """
    profile = connection.execute(select(profiles).where(
        profiles.c.id == profile_id, profiles.c.active.is_(True),
    ).with_for_update()).mappings().one_or_none()
    if profile is None:
        return 0
    boundaries = stale_boundaries(connection, profile_id)
    if not any(boundaries.values()):
        return 0
    count = replay_closure(connection, profile=dict(profile), modes=MODES, start=boundaries)
    connection.execute(insert(history_operations).values(
        id=str(uuid4()), profile_id=profile_id, kind="METHODOLOGY_REBUILD", state="COMPLETE",
        target_scope=profile["active_scope"], target_revision=profile["active_revision"],
        cursor={"rebuilt_links": count}, dependency_scope={
            mode: None if boundary is None else [boundary[0].isoformat(), boundary[1]]
            for mode, boundary in boundaries.items()},
        created_at=func.clock_timestamp(), completed_at=func.clock_timestamp(),
        dedup_key=f"methodology:{profile_id}:{uuid4()}",
    ))
    from .profile import publish_profile_checkpoint

    publish_profile_checkpoint(connection, profile_id=profile_id, cause="METHODOLOGY")
    return count


def enqueue_methodology_rebuilds(connection: Connection) -> int:
    """Queue one P3 rebuild per active profile whose analyses are stale."""
    parameters = current_context_parameters(connection)
    version = parameters.version if parameters is not None else None
    stamped = analyses.c.result["parameter_set_version"].astext
    profile_ids = connection.scalars(select(account_matches.c.profile_id).distinct().join(
        analyses, analyses.c.id == account_matches.c.active_analysis_id,
    ).join(profiles, profiles.c.id == account_matches.c.profile_id).where(
        profiles.c.active.is_(True), account_matches.c.lifecycle == "READY",
        or_(analyses.c.analysis_version != ANALYSIS_VERSION,
            analyses.c.baseline_version != BASELINE_VERSION,
            analyses.c.feature_version != FEATURE_VERSION,
            stamped.is_distinct_from(version)),
    )).all()
    key = f"{ANALYSIS_VERSION}:{BASELINE_VERSION}:{FEATURE_VERSION}:{version}"
    queued = 0
    for profile_id in profile_ids:
        try:
            enqueue(connection, dedup_key=f"methodology:{profile_id}:{key}", job_type="METHODOLOGY_REBUILD",
                    priority=3, profile_id=profile_id, payload={"methodology": key})
            queued += 1
        except StaleJob:
            continue
    return queued


def complete_methodology_job(database: Engine, *, job_id: str, lease_token: str) -> str:
    with authorized_job(database, job_id, lease_token) as (connection, job):
        if job["job_type"] != "METHODOLOGY_REBUILD" or job["profile_id"] is None:
            raise ValueError("Expected methodology rebuild work")
        # RebuildUnavailable propagates: the whole transaction rolls back, the
        # previous coherent state stays published and the worker retries/fails.
        run_methodology_rebuild(connection, profile_id=job["profile_id"])
        finish(connection, job)
        return "COMPLETE"


# -- late replay recovery ---------------------------------------------------------------

def enqueue_readmissions(connection: Connection, match_id: int) -> list[str]:
    """REPLAY_UNAVAILABLE → REPLAY_READY happened through historical re-admission.

    Each profile holding a READY link gets its own fenced P3 job; the shared
    batch transaction never takes another account's locks.
    """
    queued = []
    for profile_id in connection.scalars(select(account_matches.c.profile_id).join(
        profiles, profiles.c.id == account_matches.c.profile_id,
    ).where(account_matches.c.match_id == match_id, account_matches.c.lifecycle == "READY",
            profiles.c.active.is_(True))):
        try:
            queued.append(enqueue(connection, dedup_key=f"readmit:{profile_id}:{match_id}", job_type="READMIT",
                                  priority=3, profile_id=profile_id, match_id=match_id, payload={}))
        except StaleJob:
            continue
    return queued


def readmit(connection: Connection, *, profile_id: str, match_id: int) -> str:
    """Re-analyse one finalized match from newly retained replay evidence.

    Foundation §14.2: newly available history may change current PBs and later
    comparisons at its true chronology position; it never celebrates, never
    notifies, and the finalized role is kept (refinement is pre-READY only).
    Every later link in the bucket is replayed so no comparison keeps reading
    the pre-replay value.
    """
    from .finalization import _selected_features

    link = connection.execute(select(account_matches).where(
        account_matches.c.profile_id == profile_id, account_matches.c.match_id == match_id,
    ).with_for_update()).mappings().one_or_none()
    match = connection.execute(select(matches).where(matches.c.match_id == match_id)).mappings().one()
    if link is None or link["lifecycle"] != "READY" or match["evidence_state"] != "REPLAY_READY":
        return "NOT_APPLICABLE"
    features, snapshot_ids, feature_digest = _selected_features(connection, dict(match))
    built = build_analysis(connection, profile_id=profile_id, link=dict(link), match=dict(match),
                           features=features, snapshot_ids=snapshot_ids, feature_digest=feature_digest)
    publish_analysis(connection, profile_id=profile_id, link=dict(link), match=dict(match), built=built,
                     snapshot_ids=snapshot_ids, feature_digest=feature_digest)
    progression = built["eligibility"].progression
    if progression != "NONE":
        revision = connection.scalar(select(profiles.c.active_revision).where(profiles.c.id == profile_id))
        recompute_indexes(connection, profile_id=profile_id, revision=int(revision or 0), mode=progression,
                          roles={link["effective_role"]})
    profile = connection.execute(select(profiles).where(profiles.c.id == profile_id).with_for_update()).mappings().one()
    replay_closure(connection, profile=dict(profile), modes=(link["mode"],), inclusive=False,
                   start={link["mode"]: (link["provider_started_at"], link["provider_source_match_id"])})
    return "READMITTED"


def complete_readmit_job(database: Engine, *, job_id: str, lease_token: str) -> str:
    with authorized_job(database, job_id, lease_token) as (connection, job):
        if job["job_type"] != "READMIT" or job["profile_id"] is None or job["match_id"] is None:
            raise ValueError("Expected readmission work")
        outcome = readmit(connection, profile_id=job["profile_id"], match_id=job["match_id"])
        finish(connection, job)
        return outcome
