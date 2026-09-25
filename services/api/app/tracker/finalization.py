"""One ordered, fenced publication point for a tracker account match."""
from __future__ import annotations

import hashlib
from statistics import median
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import Connection, Engine, and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert

from .context import ContextInput, evaluate
from .eligibility import classify
from .evidence import canonical_json
from .history import BASELINE_VERSION, Observation, baseline, load_prior_observations, personal_best
from .insights import CONTRACT_VERSION as INSIGHT_CONTRACT_VERSION
from .insights import evaluate as evaluate_insights
from .insights import from_provider_snapshot
from .jobs import StaleJob, authorized_job, enqueue, finish, reschedule
from .materialization import FEATURE_VERSION, _match_payload
from .metrics import measure, metric_ids
from .roles import ROLES
from .schema import (
    account_matches,
    acquisitions,
    analyses,
    analysis_inputs,
    baselines,
    bootstrap,
    derived_features,
    events,
    insight_results,
    matches,
    metric_observations,
    personal_bests,
    positions,
    profiles,
    role_assertions,
    snapshots,
    users,
)

ANALYSIS_VERSION = "tracker-analysis-1"


def enqueue_finalization(connection: Connection, *, profile_id: str, match_id: int) -> str:
    """A generation-scoped job may be requested by either link or evidence terminality."""
    profile = connection.execute(select(profiles.c.generation).where(profiles.c.id == profile_id)).mappings().one()
    link = connection.execute(select(account_matches.c.origin).where(
        account_matches.c.profile_id == profile_id, account_matches.c.match_id == match_id,
    )).mappings().one()
    return enqueue(
        connection,
        dedup_key=f"finalize:{profile_id}:{profile['generation']}:{match_id}",
        job_type="FINALIZE", priority=0 if link["origin"] == "LIVE" else 3,
        profile_id=profile_id, match_id=match_id, payload={},
    )


def enqueue_terminal_finalizations(connection: Connection, match_id: int) -> None:
    owners = connection.scalars(select(account_matches.c.profile_id).join(
        profiles, profiles.c.id == account_matches.c.profile_id,
    ).join(users, users.c.id == profiles.c.user_id).where(
        account_matches.c.match_id == match_id, account_matches.c.finalized_at.is_(None),
        profiles.c.active.is_(True), users.c.state == "ACTIVE",
    ))
    for profile_id in owners:
        try:
            enqueue_finalization(connection, profile_id=profile_id, match_id=match_id)
        except StaleJob:
            continue


def _selected_features(connection: Connection, match: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], str]:
    source = connection.scalar(select(acquisitions.c.snapshot_id).where(
        acquisitions.c.match_id == match["match_id"], acquisitions.c.state == "REPLAY_READY",
        acquisitions.c.snapshot_id.is_not(None),
    ).order_by(acquisitions.c.provider, acquisitions.c.operation).limit(1)) if match["evidence_state"] == "REPLAY_READY" else None
    query = select(derived_features.c.inputs_digest).where(
        derived_features.c.match_id == match["match_id"], derived_features.c.player_slot == 0,
        derived_features.c.feature_version == FEATURE_VERSION,
    )
    if source is not None:
        query = query.where(derived_features.c.provenance["snapshot_id"].astext == source)
    digest = connection.scalar(query.order_by(
        derived_features.c.created_at.desc() if match["evidence_state"] == "REPLAY_READY" else derived_features.c.created_at,
        derived_features.c.inputs_digest,
    ).limit(1))
    if not isinstance(digest, str):
        raise ValueError("Terminal match has no retained feature projection")
    rows = connection.execute(select(derived_features).where(
        derived_features.c.match_id == match["match_id"],
        derived_features.c.inputs_digest == digest,
        derived_features.c.feature_version == FEATURE_VERSION,
    ).order_by(derived_features.c.player_slot)).mappings().all()
    if len(rows) != 10 or [row["player_slot"] for row in rows] != list(range(10)):
        raise ValueError("Terminal match has an incomplete feature projection")
    snapshot_ids = sorted({row["provenance"]["snapshot_id"] for row in rows})
    if len(snapshot_ids) != 1:
        raise ValueError("A projection cannot mix source snapshots")
    return [row["features"] for row in rows], snapshot_ids, digest


def _positions(connection: Connection, link: dict[str, Any]) -> dict[int, int | None]:
    assignment = link["role_assignment"]
    if not isinstance(assignment, dict):
        return {}
    rows = connection.execute(select(positions.c.player_slot, positions.c.position).where(
        positions.c.match_id == link["match_id"],
        positions.c.evidence_profile == assignment.get("evidence_profile"),
        positions.c.version == assignment.get("version"),
        positions.c.inputs_digest == assignment.get("inputs_digest"),
    )).all()
    return {slot: position for slot, position in rows}


def _metric_conflict(metric_id: str, slot: int, quarantined: list[str]) -> bool:
    """Suppress only source fields consumed by this metric; unknown conflict paths fail closed."""
    if not quarantined:
        return False
    fields: tuple[str, ...]
    if metric_id.endswith("hero_damage_share.v1"):
        fields = ("hero_damage",)
    elif metric_id.endswith("tower_damage_share.v1"):
        fields = ("tower_damage",)
    elif metric_id.endswith("healing.v1"):
        fields = ("hero_healing",)
    elif metric_id.endswith("fight_presence.v1"):
        fields = ("kills", "assists")
    elif "net_worth" in metric_id:
        fields = ("net_worth",)
    elif "last_hits" in metric_id or "cs_10_to_20" in metric_id:
        fields = ("last_hits",)
    elif "camps_stacked" in metric_id:
        fields = ("camps_stacked",)
    else:
        fields = ("events",)
    summary_team = metric_id.endswith(("damage_share.v1", "fight_presence.v1"))
    checkpoint = metric_id in {
        "carry.last_hits_at_10.v1", "mid.lane_net_worth_advantage_at_10.v1",
        "offlane.lane_net_worth_advantage_at_10.v1", "offlane.net_worth_at_10.v1",
    }
    needed_seconds = {600, 1200} if "cs_10_to_20" in metric_id else {600 if checkpoint else 1200}
    for path in quarantined:
        if not isinstance(path, str):
            return True
        if path in {"duration_seconds", "started_at", "mode"}:
            return True
        parts = path.split(".")
        if len(parts) < 4 or parts[0] != "players" or not parts[1].isdigit():
            continue
        conflict_slot = int(parts[1])
        if not (summary_team and conflict_slot // 5 == slot // 5 or conflict_slot == slot or
                "lane_net_worth_advantage" in metric_id and conflict_slot // 5 != slot // 5):
            continue
        if parts[2] == "series" and parts[3] in fields:
            if len(parts) == 5 and parts[4].isdigit() and int(parts[4]) in needed_seconds:
                return True
        elif parts[2] == "values" and parts[3] in fields:
            return True
        elif parts[2] == "events" and "events" in fields:
            return True
    return False


def _prior_pending(connection: Connection, link: dict[str, Any]) -> bool:
    prior = account_matches.alias("prior")
    return connection.scalar(select(prior.c.match_id).where(
        prior.c.profile_id == link["profile_id"], prior.c.mode == link["mode"],
        or_(prior.c.progression.is_(None), prior.c.progression != "NONE"),
        prior.c.lifecycle.not_in(("READY", "UNAVAILABLE")),
        or_(prior.c.provider_started_at < link["provider_started_at"],
            and_(prior.c.provider_started_at == link["provider_started_at"],
                 prior.c.provider_source_match_id < link["provider_source_match_id"])),
    ).limit(1)) is not None


def _insight_result(connection: Connection, *, link: dict[str, Any], match: dict[str, Any],
                    snapshot_id: str, position_map: dict[int, int | str | None]) -> dict[str, Any]:
    snapshot = connection.execute(select(snapshots).where(snapshots.c.id == snapshot_id)).mappings().one()
    try:
        raw = _match_payload(dict(snapshot), match["match_id"])
        neutral = from_provider_snapshot(dict(raw), snapshot["provider"], position_map)
    except (KeyError, TypeError, ValueError):
        return {"status": "NOT_ELIGIBLE(SOURCE_EVIDENCE)",
                "contract_version": INSIGHT_CONTRACT_VERSION, "cards": []}
    viewer = {"team": "RADIANT" if link["player_slot"] < 5 else "DIRE",
              "won": match["radiant_win"] == (link["player_slot"] < 5),
              "player_slot": link["player_slot"], "effective_role": link["effective_role"]}
    return evaluate_insights(neutral, viewer)


def build_analysis(connection: Connection, *, profile_id: str, link: dict[str, Any],
                   match: dict[str, Any], features: list[dict[str, Any]],
                   snapshot_ids: list[str], feature_digest: str) -> dict[str, Any]:
    """Calculate one match's analytical output from retained inputs, without writes.

    This is the reusable boundary for finalization and future retained-data rebuilds.
    The caller owns the transaction and publication side effects.
    """
    player = features[link["player_slot"]]
    position_map = _positions(connection, link)
    integrity = player.get("integrity", {}).get("verdict")
    quarantined = match["quarantined_fields"] or []
    if any(path in {"duration_seconds", "mode", "game_mode", "lobby_type"} or
           (isinstance(path, str) and path.endswith(".leaver_status")) for path in quarantined):
        integrity = "UNKNOWN"
    eligibility = classify(
        mode=link["mode"], duration_seconds=match["duration_seconds"],
        effective_role=link["effective_role"],
        leaver_status=player["summary"].get("leaver_status"), integrity=integrity,
    )
    if eligibility.progression == "NONE" or quarantined:
        # ponytail: withhold all cards on source disagreement until each card has a verified field dependency map.
        insight: dict[str, Any] = {"status": "NOT_ELIGIBLE(PROGRESSION)" if eligibility.progression == "NONE"
                   else "NOT_ELIGIBLE(SOURCE_DISAGREEMENT)",
                   "contract_version": INSIGHT_CONTRACT_VERSION, "cards": []}
    else:
        insight = _insight_result(connection, link=link, match=match,
                                  snapshot_id=snapshot_ids[0],
                                  position_map=cast(dict[int, int | str | None], position_map))
    metric_rows: list[dict[str, Any]] = []
    pb_rows: list[dict[str, Any]] = []
    for metric_id in metric_ids(link["effective_role"]):
        measured = measure(
            metric_id, players=features, player_slot=link["player_slot"],
            duration_seconds=match["duration_seconds"],
            replay_ready=match["evidence_state"] == "REPLAY_READY", positions=position_map,
        )
        if _metric_conflict(metric_id, link["player_slot"], quarantined):
            measured = type(measured)(metric_id, None, None, reason="SOURCE_DISAGREEMENT")
        current = Observation(
            match["match_id"], link["provider_started_at"],
            link["mode"] if link["mode"] in {"STANDARD", "TURBO"} else "STANDARD",
            link["effective_role"], metric_id, measured.comparison_value,
            eligibility.progression != "NONE",
        )
        priors = load_prior_observations(
            connection, profile_id=profile_id, current=current,
            analysis_version=ANALYSIS_VERSION, baseline_version=BASELINE_VERSION,
        ) if eligibility.progression != "NONE" else []
        reference = baseline(current, priors)
        pb = personal_best(current, priors, celebrate=link["origin"] == "LIVE")
        context = evaluate(ContextInput(
            metric_id=metric_id, role=link["effective_role"], mode=current.mode,
            hero_id=player["summary"].get("hero_id"), position=position_map.get(link["player_slot"]),
            lane=None, is_radiant=link["player_slot"] < 5, players=(),
            comparison_value=measured.comparison_value,
            baseline=reference["value"] if isinstance(reference["value"], (int, float)) else None,
            prior_count=cast(int, reference["prior_count"]),
        ), None)
        metric_rows.append({
            "metric_id": metric_id, "metric_version": metric_id.rsplit(".", 1)[-1],
            "raw_value": measured.raw_value, "comparison_value": measured.comparison_value,
            "unavailable_reason": measured.reason, "baseline_snapshot": reference,
            "context_h": context.delta_hero, "context_e": context.delta_lane,
            "performance_state": context.performance_state,
        })
        if eligibility.progression != "NONE" and measured.comparison_value is not None:
            pb_rows.append({"metric_id": metric_id, "current": current, "priors": priors, "pb": pb})
    inputs_digest = hashlib.sha256(canonical_json({
        "analysis_version": ANALYSIS_VERSION, "baseline_version": BASELINE_VERSION,
        "feature_version": FEATURE_VERSION, "feature_digest": feature_digest,
        "profile_id": profile_id, "match_id": link["match_id"],
        "role": link["effective_role"], "role_revision": link["role_revision"],
        "progression": eligibility.progression, "metric_rows": metric_rows,
        "insight_result": insight,
        "quarantined_fields": quarantined,
    })).hexdigest()
    return {"eligibility": eligibility, "insight": insight, "metric_rows": metric_rows,
            "pb_rows": pb_rows, "inputs_digest": inputs_digest,
            "quarantined_fields": quarantined}


def complete_finalization_job(database: Engine, *, job_id: str, lease_token: str) -> str:
    """Publish metrics/history once after terminal evidence, in bucket chronology order."""
    with authorized_job(database, job_id, lease_token) as (connection, job):
        if job["job_type"] != "FINALIZE" or job["profile_id"] is None or job["match_id"] is None:
            raise ValueError("Expected private finalization work")
        link = dict(connection.execute(select(account_matches).where(
            account_matches.c.profile_id == job["profile_id"],
            account_matches.c.match_id == job["match_id"],
        ).with_for_update()).mappings().one())
        if link["lifecycle"] == "READY":
            finish(connection, job)
            return "ALREADY_READY"
        match = dict(connection.execute(select(matches).where(matches.c.match_id == job["match_id"])).mappings().one())
        if match["evidence_state"] not in {"REPLAY_READY", "REPLAY_UNAVAILABLE"}:
            connection.execute(account_matches.update().where(
                account_matches.c.profile_id == job["profile_id"], account_matches.c.match_id == job["match_id"],
            ).values(lifecycle="WAITING_FOR_PROVIDER"))
            reschedule(connection, job, delay_seconds=30, error="AWAITING_TERMINAL_EVIDENCE", failure=False)
            return "WAITING_FOR_PROVIDER"
        if link["lifecycle"] == "WAITING_FOR_PROVIDER":
            connection.execute(account_matches.update().where(
                account_matches.c.profile_id == job["profile_id"], account_matches.c.match_id == job["match_id"],
            ).values(lifecycle="ANALYZING"))
        assignment = match["replay_role_assignment"]
        if isinstance(assignment, dict):
            asserted = connection.execute(select(role_assertions.c.role, role_assertions.c.revision).where(
                role_assertions.c.profile_id == job["profile_id"],
                role_assertions.c.match_id == job["match_id"],
            ).order_by(role_assertions.c.revision.desc()).limit(1)).first()
            refined = connection.scalar(select(positions.c.position).where(
                positions.c.match_id == job["match_id"], positions.c.player_slot == link["player_slot"],
                positions.c.evidence_profile == "REPLAY", positions.c.version == assignment.get("version"),
                positions.c.inputs_digest == assignment.get("inputs_digest"),
            ))
            role = asserted.role if asserted is not None else ROLES.get(refined) if isinstance(refined, int) else None
            if role is not None:
                link["effective_role"] = role
                link["role_assignment"] = assignment
                if asserted is not None:
                    link["role_revision"] = asserted.revision
                connection.execute(account_matches.update().where(
                    account_matches.c.profile_id == job["profile_id"], account_matches.c.match_id == job["match_id"],
                ).values(effective_role=link["effective_role"], role_assignment=assignment,
                         role_revision=link["role_revision"], lifecycle="ANALYZING"))
        if link["effective_role"] is None:
            connection.execute(account_matches.update().where(
                account_matches.c.profile_id == job["profile_id"], account_matches.c.match_id == job["match_id"],
            ).values(lifecycle="UNAVAILABLE", retrying=False, failure_stage="ROLE_CLASSIFICATION", failure_reason="ROLE_UNAVAILABLE"))
            from .coverage import record_match_coverage

            record_match_coverage(connection, profile_id=job["profile_id"], match_id=job["match_id"])
            if link["origin"] == "BOOTSTRAP":
                from .bootstrap import settle_bootstrap

                settle_bootstrap(connection, job["profile_id"])
            finish(connection, job)
            return "UNAVAILABLE"
        if link["origin"] == "LIVE" and link["mode"] in {"STANDARD", "TURBO"}:
            settled = connection.scalar(select(bootstrap.c.completed_at).where(
                bootstrap.c.profile_id == job["profile_id"], bootstrap.c.mode == link["mode"],
            ))
            has_bootstrap = connection.scalar(select(bootstrap.c.profile_id).where(
                bootstrap.c.profile_id == job["profile_id"], bootstrap.c.mode == link["mode"],
            )) is not None
            if has_bootstrap and settled is None:
                connection.execute(account_matches.update().where(
                    account_matches.c.profile_id == job["profile_id"], account_matches.c.match_id == job["match_id"],
                ).values(lifecycle="WAITING_FOR_PRIOR_MATCH"))
                reschedule(connection, job, delay_seconds=30, error="AWAITING_MODE_BOOTSTRAP", failure=False)
                return "WAITING_FOR_PRIOR_MATCH"
        if link["mode"] in {"STANDARD", "TURBO"} and _prior_pending(connection, link):
            connection.execute(account_matches.update().where(
                account_matches.c.profile_id == job["profile_id"], account_matches.c.match_id == job["match_id"],
            ).values(lifecycle="WAITING_FOR_PRIOR_MATCH"))
            reschedule(connection, job, delay_seconds=30, error="AWAITING_PRIOR_MATCH", failure=False)
            return "WAITING_FOR_PRIOR_MATCH"
        features, snapshot_ids, feature_digest = _selected_features(connection, match)
        built = build_analysis(connection, profile_id=job["profile_id"], link=link, match=match,
                               features=features, snapshot_ids=snapshot_ids,
                               feature_digest=feature_digest)
        eligibility = built["eligibility"]
        insight = built["insight"]
        metric_rows = built["metric_rows"]
        pb_rows = built["pb_rows"]
        inputs_digest = built["inputs_digest"]
        quarantined = built["quarantined_fields"]
        analysis_id = str(uuid4())
        connection.execute(analyses.insert().values(
            id=analysis_id, profile_id=job["profile_id"], match_id=job["match_id"],
            feature_version=FEATURE_VERSION, analysis_version=ANALYSIS_VERSION,
            baseline_version=BASELINE_VERSION, inputs_digest=inputs_digest,
            result={"progression": eligibility.progression, "reason": eligibility.reason,
                    "insight_status": insight["status"],
                    "insight_contract_version": insight["contract_version"]},
            provenance={"source_snapshot_ids": snapshot_ids, "feature_digest": feature_digest,
                        "quarantined_fields": quarantined}, created_at=func.clock_timestamp(),
        ))
        for snapshot_id in snapshot_ids:
            connection.execute(analysis_inputs.insert().values(analysis_id=analysis_id, snapshot_id=snapshot_id))
        for row in metric_rows:
            connection.execute(metric_observations.insert().values(analysis_id=analysis_id, **row))
        connection.execute(insight_results.insert().values(
            analysis_id=analysis_id, contract_version=insight["contract_version"],
            inputs_digest=inputs_digest, cards=insight["cards"],
            created_at=func.clock_timestamp(),
        ))
        revision = connection.scalar(select(profiles.c.active_revision).where(profiles.c.id == job["profile_id"]))
        if revision is None:
            raise ValueError("Profile revision unavailable")
        for item in pb_rows:
            current, priors, pb = item["current"], item["priors"], item["pb"]
            observed = sorted([*priors, current], key=lambda row: row.chronology)[-20:]
            rolling = {"version": BASELINE_VERSION, "state": "BASELINE_READY" if len(observed) >= 5 else "BASELINE_BUILDING",
                       "prior_count": len(observed), "value": median(row.comparison_value for row in observed) if len(observed) >= 5 else None,
                       "source_match_ids": [row.match_id for row in observed]}
            key = dict(profile_id=job["profile_id"], revision=revision, mode=current.mode,
                       role=current.role, metric_id=current.metric_id, metric_version=current.metric_id.rsplit(".", 1)[-1])
            connection.execute(insert(baselines).values(**key, baseline_version=BASELINE_VERSION, snapshot=rolling)
                               .on_conflict_do_update(index_elements=list(key), set_={"snapshot": rolling}))
            if pb["source_match_id"] == current.match_id:
                connection.execute(insert(personal_bests).values(
                    **key, analysis_id=analysis_id, comparison_value=current.comparison_value,
                ).on_conflict_do_update(index_elements=list(key), set_={
                    "analysis_id": analysis_id, "comparison_value": current.comparison_value,
                }))
                if pb["new_pb"]:
                    connection.execute(insert(events).values(
                        id=str(uuid4()), profile_id=job["profile_id"], kind="NEW_PB",
                        dedup_key=f"pb:{job['profile_id']}:{job['match_id']}:{current.metric_id}:{ANALYSIS_VERSION}",
                        payload={"metric_id": current.metric_id, "match_id": current.match_id},
                        created_at=func.clock_timestamp(),
                    ).on_conflict_do_nothing())
        connection.execute(account_matches.update().where(
            account_matches.c.profile_id == job["profile_id"], account_matches.c.match_id == job["match_id"],
        ).values(lifecycle="READY", retrying=False, progression=eligibility.progression,
                 progression_reason=eligibility.reason, active_analysis_id=analysis_id,
                 finalized_at=func.clock_timestamp(), failure_stage=None, failure_reason=None))
        from .coverage import record_match_coverage

        record_match_coverage(connection, profile_id=job["profile_id"], match_id=job["match_id"])
        from .notifications import record_ready

        record_ready(connection, profile_id=job["profile_id"], match_id=job["match_id"],
                     origin=link["origin"])
        if link["origin"] == "BOOTSTRAP":
            from .bootstrap import settle_bootstrap

            settle_bootstrap(connection, job["profile_id"])
        finish(connection, job)
        return "READY"
