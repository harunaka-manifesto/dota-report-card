"""Atomic role correction from immutable tracker evidence."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import Connection, func, select, tuple_, update

from .finalization import (
    ANALYSIS_VERSION,
    FEATURE_VERSION,
    build_analysis,
    publish_analysis,
    recompute_indexes,
)
from .history import BASELINE_VERSION
from .metrics import metric_ids
from .schema import (
    account_matches,
    analyses,
    analysis_inputs,
    derived_features,
    matches,
    metric_observations,
    profiles,
    role_assertions,
    snapshots,
    users,
)

ROLES = frozenset({"CARRY", "MID", "OFFLANE", "SUPPORT"})


class RoleCorrectionConflict(ValueError):
    """The caller's role revision is stale or its profile is no longer active."""


class RoleCorrectionUnavailable(ValueError):
    """The retained source cannot reproduce the affected analytical history."""


def _retained_inputs(connection: Connection, link: dict[str, Any]) -> dict[str, Any]:
    analysis = connection.execute(select(analyses).where(
        analyses.c.id == link["active_analysis_id"], analyses.c.profile_id == link["profile_id"],
        analyses.c.match_id == link["match_id"],
    )).mappings().one_or_none()
    if analysis is None or analysis["analysis_version"] != ANALYSIS_VERSION or analysis["baseline_version"] != BASELINE_VERSION:
        raise RoleCorrectionUnavailable("Original analysis version is unavailable")
    if analysis["feature_version"] != FEATURE_VERSION:
        raise RoleCorrectionUnavailable("Original feature version is unavailable")
    provenance = analysis["provenance"]
    if not isinstance(provenance, dict):
        raise RoleCorrectionUnavailable("Original analysis provenance is unavailable")
    digest = provenance.get("feature_digest")
    source_ids = connection.scalars(select(analysis_inputs.c.snapshot_id).where(
        analysis_inputs.c.analysis_id == analysis["id"],
    ).order_by(analysis_inputs.c.snapshot_id)).all()
    declared_sources = provenance.get("source_snapshot_ids")
    if (not isinstance(digest, str) or len(source_ids) != 1
            or declared_sources != source_ids):
        raise RoleCorrectionUnavailable("Original source lineage is unavailable")
    source_id = source_ids[0]
    snapshot = connection.execute(select(snapshots).where(snapshots.c.id == source_id)).mappings().one_or_none()
    if snapshot is None or snapshot["payload"] is None:
        raise RoleCorrectionUnavailable("Original insight source is unavailable")
    feature_rows = connection.execute(select(derived_features).where(
        derived_features.c.match_id == link["match_id"],
        derived_features.c.feature_version == analysis["feature_version"],
        derived_features.c.inputs_digest == digest,
    ).order_by(derived_features.c.player_slot)).mappings().all()
    if len(feature_rows) != 10 or [row["player_slot"] for row in feature_rows] != list(range(10)):
        raise RoleCorrectionUnavailable("Original metric source is unavailable")
    if (any(not isinstance(row["provenance"], dict) for row in feature_rows)
            or {row["provenance"].get("snapshot_id") for row in feature_rows} != {source_id}):
        raise RoleCorrectionUnavailable("Original source lineage is inconsistent")
    versions = connection.execute(select(metric_observations.c.metric_version).where(
        metric_observations.c.analysis_id == analysis["id"],
    )).scalars().all()
    if not versions or any(version != "v1" for version in versions):
        raise RoleCorrectionUnavailable("Original metric versions are unavailable")
    return {"analysis": dict(analysis), "features": [row["features"] for row in feature_rows],
            "feature_digest": digest, "snapshot_ids": [source_id], "match": dict(connection.execute(
                select(matches).where(matches.c.match_id == link["match_id"])).mappings().one())}


def _publish_analysis(connection: Connection, *, profile_id: str, link: dict[str, Any],
                      match: dict[str, Any], inputs: dict[str, Any]) -> str:
    built = build_analysis(connection, profile_id=profile_id, link=link, match=match,
                           features=inputs["features"], snapshot_ids=inputs["snapshot_ids"],
                           feature_digest=inputs["feature_digest"])
    return publish_analysis(connection, profile_id=profile_id, link=link, match=match, built=built,
                            snapshot_ids=inputs["snapshot_ids"], feature_digest=inputs["feature_digest"])


def _affected_links(connection: Connection, *, profile_id: str, link: dict[str, Any],
                    roles: set[str], lock: bool = False) -> list[dict[str, Any]]:
    query = select(account_matches).where(
        account_matches.c.profile_id == profile_id, account_matches.c.mode == link["mode"],
        account_matches.c.lifecycle == "READY", account_matches.c.progression == link["mode"],
        account_matches.c.effective_role.in_(roles),
        tuple_(account_matches.c.provider_started_at,
               account_matches.c.provider_source_match_id) >=
        (link["provider_started_at"], link["provider_source_match_id"]),
    ).order_by(account_matches.c.provider_started_at, account_matches.c.provider_source_match_id)
    if lock:
        query = query.with_for_update()
    return [dict(row) for row in connection.execute(query).mappings().all()]


def _preflight(connection: Connection, *, affected: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    if not affected:
        raise RoleCorrectionUnavailable("Match is outside the rebuildable progression history")
    sources = {row["match_id"]: _retained_inputs(connection, row) for row in affected}
    for row in affected:
        expected_metrics = set(metric_ids(row["effective_role"]))
        stored_metrics = set(connection.scalars(select(metric_observations.c.metric_id).where(
            metric_observations.c.analysis_id == row["active_analysis_id"],
        )).all())
        if stored_metrics != expected_metrics:
            raise RoleCorrectionUnavailable("Affected analysis metric set is unsupported")
    return sources


def correction_available(connection: Connection, *, profile_id: str, match_id: int,
                         role: str | None = None) -> bool:
    """Read-only provider-free check; without `role`, any valid edit enables the action."""
    link = connection.execute(select(account_matches).where(
        account_matches.c.profile_id == profile_id, account_matches.c.match_id == match_id,
    )).mappings().one_or_none()
    if (link is None or link["lifecycle"] != "READY" or link["active_analysis_id"] is None
            or link["effective_role"] not in ROLES):
        return False
    candidates = {role.upper()} if isinstance(role, str) else ROLES - {link["effective_role"]}
    if not candidates or not candidates <= ROLES:
        return False
    for candidate in candidates:
        if candidate == link["effective_role"]:
            return True
        try:
            if link["progression"] == link["mode"] and link["mode"] in {"STANDARD", "TURBO"}:
                affected = _affected_links(connection, profile_id=profile_id, link=dict(link),
                                           roles={link["effective_role"], candidate})
            else:
                affected = [dict(link)]
            if any(metric.rsplit(".", 1)[-1] != "v1" for metric in metric_ids(candidate)):
                continue
            _preflight(connection, affected=affected)
        except RoleCorrectionUnavailable:
            continue
        return True
    return False


def correct_role(connection: Connection, *, profile_id: str, match_id: int, role: str,
                 expected_role_revision: int) -> dict[str, Any]:
    """Append a user assertion and atomically replay its same-mode role closure.

    The caller must include this function in the authenticated request transaction.
    `expected_role_revision` is the account-match revision returned by the read API.
    """
    role = role.upper() if isinstance(role, str) else ""
    if role not in ROLES:
        raise ValueError("Invalid role")
    owner = connection.scalar(select(profiles.c.user_id).where(profiles.c.id == profile_id))
    if owner is None:
        raise RoleCorrectionConflict("Profile is unavailable")
    user = connection.execute(select(users).where(users.c.id == owner).with_for_update()).mappings().one()
    if user["state"] != "ACTIVE":
        raise RoleCorrectionConflict("Profile is unavailable")
    profile = connection.execute(select(profiles).where(
        profiles.c.id == profile_id, profiles.c.active.is_(True),
    ).with_for_update()).mappings().one_or_none()
    if profile is None:
        raise RoleCorrectionConflict("Profile is unavailable")
    link_row = connection.execute(select(account_matches).where(
        account_matches.c.profile_id == profile_id, account_matches.c.match_id == match_id,
    ).with_for_update()).mappings().one_or_none()
    if link_row is None or link_row["lifecycle"] != "READY" or link_row["active_analysis_id"] is None:
        raise RoleCorrectionUnavailable("Match is not finalized")
    link = dict(link_row)
    if link["role_revision"] != expected_role_revision:
        raise RoleCorrectionConflict("Role revision is stale")
    previous_role = link["effective_role"]
    latest_assertion = connection.execute(select(role_assertions.c.revision, role_assertions.c.role).where(
        role_assertions.c.profile_id == profile_id, role_assertions.c.match_id == match_id,
    ).order_by(role_assertions.c.revision.desc()).limit(1)).first()
    if latest_assertion is not None and latest_assertion.revision != expected_role_revision:
        raise RoleCorrectionConflict("Role assertion revision is stale")
    if latest_assertion is not None and latest_assertion.role != previous_role:
        raise RoleCorrectionConflict("Effective role does not match the latest assertion")
    if previous_role not in ROLES or link["mode"] not in {"STANDARD", "TURBO", "UNSUPPORTED"}:
        raise RoleCorrectionUnavailable("Match role cannot be rebuilt")
    new_revision = link["role_revision"] + 1
    if role == previous_role:
        if latest_assertion is not None and latest_assertion.role == role:
            return {"effective_role": role, "role_revision": link["role_revision"], "rebuilt": False}
        connection.execute(role_assertions.insert().values(
            id=str(uuid4()), profile_id=profile_id, match_id=match_id,
            revision=new_revision, role=role, asserted_at=func.clock_timestamp(),
            provenance={"source": "user_confirmation"},
            dedup_key=f"role-assertion:{profile_id}:{match_id}:{new_revision}",
        ))
        connection.execute(update(account_matches).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == match_id,
        ).values(role_revision=new_revision))
        return {"effective_role": role, "role_revision": new_revision, "rebuilt": False}

    if link["progression"] == link["mode"] and link["mode"] in {"STANDARD", "TURBO"}:
        affected = _affected_links(connection, profile_id=profile_id, link=link,
                                    roles={previous_role, role}, lock=True)
    else:
        affected = [link]
    if any(metric.rsplit(".", 1)[-1] != "v1" for metric in metric_ids(role)):
        raise RoleCorrectionUnavailable("Corrected metric version is unsupported")
    sources = _preflight(connection, affected=affected)

    connection.execute(role_assertions.insert().values(
        id=str(uuid4()), profile_id=profile_id, match_id=match_id,
        revision=new_revision, role=role, asserted_at=func.clock_timestamp(),
        provenance={"source": "user_role_edit", "previous_role": previous_role},
        dedup_key=f"role-assertion:{profile_id}:{match_id}:{new_revision}",
    ))
    connection.execute(update(account_matches).where(
        account_matches.c.profile_id == profile_id, account_matches.c.match_id == match_id,
    ).values(effective_role=role, role_revision=new_revision))
    for original in affected:
        mutable_link = dict(original)
        if mutable_link["match_id"] == match_id:
            mutable_link["effective_role"] = role
            mutable_link["role_revision"] = new_revision
        _publish_analysis(connection, profile_id=profile_id, link=mutable_link,
                          match=sources[mutable_link["match_id"]]["match"],
                          inputs=sources[mutable_link["match_id"]])

    if link["progression"] == link["mode"] and link["mode"] in {"STANDARD", "TURBO"}:
        recompute_indexes(connection, profile_id=profile_id, revision=profile["active_revision"],
                          mode=link["mode"], roles={previous_role, role})
        from .profile import publish_profile_checkpoint

        publish_profile_checkpoint(connection, profile_id=profile_id, cause="ROLE_CORRECTION",
                                   modes=(link["mode"],))
    return {"effective_role": role, "role_revision": new_revision, "rebuilt": True,
            "rebuilt_match_count": len(affected)}
