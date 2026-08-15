from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from dataclasses import asdict
from typing import Any

from app.analysis.source import AnalysisSource
from app.cohorts.selector import CohortSelection, select_narrowest_cohort
from app.core.config import Settings, get_settings
from app.core.errors import AppError, InsufficientMatchHistory, ProfileUnavailable
from app.core.security import PlayerIdentifier, parse_player_identifier
from app.features.calculators import calculate_match_features
from app.features.models import MatchFeature
from app.ingestion.eligibility import assess_match
from app.ingestion.normalize import NormalizedMatch, normalize_match
from app.insights.evaluator import InsightContext, evaluate_insights
from app.reports.assembly import assemble_report
from app.storage.repository import AnalysisJob, InMemoryRepository

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(
        self,
        source: AnalysisSource,
        *,
        repository: Any | None = None,
        settings: Settings | None = None,
        cohort_population: Iterable[MatchFeature] = (),
    ) -> None:
        self.source = source
        self.repository = repository or InMemoryRepository()
        self.settings = settings or get_settings()
        self.cohort_population = tuple(cohort_population)
        self._tasks: set[asyncio.Task[None]] = set()
        self._scheduled_job_ids: set[str] = set()
        self._semaphore: asyncio.Semaphore | None = None

    async def create_analysis(
        self,
        player: str,
        *,
        refresh: bool = False,
        enqueue: bool = True,
    ) -> tuple[AnalysisJob, bool]:
        identifier = parse_player_identifier(player)
        if not refresh:
            existing = self.repository.find_compatible_completed(
                identifier.account_id,
                self.settings.model_version,
                max_age_seconds=self.settings.compatible_analysis_ttl_seconds,
            )
            if existing is not None:
                return existing, True
        job, reused = self.repository.get_or_create_inflight_job(
            identifier.account_id,
            identifier.canonical_url,
            self.settings.model_version,
        )
        if enqueue:
            self._enqueue(job, identifier)
        return job, reused

    def _enqueue(self, job: AnalysisJob, identifier: PlayerIdentifier) -> None:
        if job.job_id in self._scheduled_job_ids or job.status != "queued":
            return
        self._scheduled_job_ids.add(job.job_id)
        if self.settings.effective_analysis_execution_backend == "celery":
            try:
                from app.workers.tasks import celery_app

                celery_app.send_task(
                    "dota_report_card.run_analysis",
                    args=[job.job_id, identifier.account_id, identifier.canonical_url],
                )
            except Exception:
                self._scheduled_job_ids.discard(job.job_id)
                raise
            return
        task = asyncio.create_task(self._run_bounded(job, identifier))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run_bounded(self, job: AnalysisJob, identifier: PlayerIdentifier) -> None:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(max(1, self.settings.analysis_max_concurrency))
        try:
            async with self._semaphore:
                await self.run_job(job, identifier)
        finally:
            self._scheduled_job_ids.discard(job.job_id)

    async def shutdown(self) -> None:
        """Cancel tracked in-process jobs so shutdown never leaves detached work behind."""

        tasks = list(self._tasks)
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        self._scheduled_job_ids.clear()

    async def run_job(self, job: AnalysisJob, identifier: PlayerIdentifier | None = None) -> None:
        identifier = identifier or PlayerIdentifier(job.account_id, job.canonical_player)
        try:
            await self._run(job, identifier)
        except asyncio.CancelledError:
            self.repository.fail_job(job, "ANALYSIS_CANCELLED", "The analysis was cancelled")
            raise
        except AppError as exc:
            self.repository.fail_job(job, exc.code, exc.message)
        except Exception:
            logger.exception("analysis_failed job_id=%s account_id=%s", job.job_id, job.account_id)
            self.repository.fail_job(job, "ANALYSIS_FAILED", "Unexpected analysis failure")

    async def _run(self, job: AnalysisJob, identifier: PlayerIdentifier) -> None:
        self.repository.update_job(
            job, status="running", stage="validating_player", message="Identifier accepted"
        )
        profile = await self.source.get_player(identifier.account_id)
        if not profile or not _profile_account_id(profile, identifier.account_id):
            raise ProfileUnavailable("Public profile is unavailable")
        self.repository.persist_raw_payload(
            f"/players/{identifier.account_id}",
            str(identifier.account_id),
            profile,
        )

        self.repository.update_job(
            job, stage="fetching_history", message="Fetching latest match history"
        )
        history_limit = self.settings.effective_history_limit
        history = await self.source.get_matches(identifier.account_id, limit=history_limit)
        history = list(history[:history_limit])
        self.repository.persist_raw_payload(
            f"/players/{identifier.account_id}/matches",
            str(identifier.account_id),
            history,
        )
        if not history:
            raise InsufficientMatchHistory("No match history was returned")
        job.processed_matches = len(history)

        self.repository.update_job(
            job, stage="filtering_matches", message="Applying match eligibility rules"
        )
        candidates: list[dict[str, Any]] = []
        exclusion_ledger: list[dict[str, Any]] = []
        for summary in history[:history_limit]:
            result = assess_match(summary, account_id=identifier.account_id)
            if result.eligible:
                candidates.append(summary)
            else:
                exclusion_ledger.append(result.as_dict())
        job.eligible_matches = len(candidates)
        self.repository.record_event(
            job, f"{len(exclusion_ledger)} history rows excluded before hydration"
        )

        self.repository.update_job(
            job, stage="hydrating_matches", message="Hydrating eligible match details"
        )
        normalized: list[NormalizedMatch] = []
        for summary in candidates:
            match_id = int(summary["match_id"])
            detail = await self.source.get_match(match_id)
            self.repository.persist_raw_payload(f"/matches/{match_id}", str(match_id), detail)
            result = assess_match(summary, detail=detail, account_id=identifier.account_id)
            if not result.eligible:
                exclusion_ledger.append(result.as_dict())
                job.eligible_matches -= 1
                continue
            normalized_match = normalize_match(
                detail, account_id=identifier.account_id, eligibility=result
            )
            normalized.append(normalized_match)
            self.repository.save_normalized_match(match_id, _normalized_record(normalized_match))

        if not normalized:
            raise InsufficientMatchHistory("No eligible, identifiable matches were hydrated")
        self.repository.update_job(
            job, stage="normalizing", message="Normalized facts and parse coverage recorded"
        )

        self.repository.update_job(
            job, stage="computing_features", message="Computing reusable match features"
        )
        features = calculate_match_features(normalized)
        for feature in features:
            self.repository.save_derived_feature(feature.match_id, feature.as_dict())

        self.repository.update_job(
            job, stage="building_cohorts", message="Selecting the narrowest supported cohort"
        )
        cohort = _select_cohort(features, self.cohort_population)
        if cohort is None or not cohort.valid:
            self.repository.add_warning(job, "No valid internal comparison cohort was available")

        self.repository.update_job(
            job, stage="evaluating_insights", message="Evaluating registered insight families"
        )
        context = InsightContext(
            account_id=identifier.account_id,
            features=tuple(features),
            cohort=cohort,
            profile=_profile_for_report(profile, identifier.account_id),
            data_cutoff=max((feature.start_time or 0 for feature in features), default=None),
            model_version=self.settings.model_version,
            template_version=self.settings.template_version,
            role_confidence_threshold=self.settings.role_confidence_threshold,
            replay_coverage_threshold=self.settings.replay_coverage_threshold,
            summary_coverage_threshold=self.settings.summary_coverage_threshold,
            history_limit=history_limit,
        )
        evidence = evaluate_insights(context)

        self.repository.update_job(
            job, stage="rendering_report", message="Rendering deterministic report"
        )
        report = assemble_report(
            context=context,
            evidence=evidence,
            exclusion_ledger=exclusion_ledger,
            processed_matches=job.processed_matches,
            eligible_matches=job.eligible_matches,
        )
        report_id = self.repository.save_report(
            account_id=identifier.account_id,
            data_cutoff=context.data_cutoff,
            model_version=self.settings.model_version,
            template_version=self.settings.template_version,
            report=report,
            evidence=evidence,
        )
        self.repository.complete_job(job, report_id)


def _select_cohort(
    features: list[MatchFeature],
    population: tuple[MatchFeature, ...],
) -> CohortSelection | None:
    if not features or not population:
        return None
    latest = max(
        features,
        key=_feature_recency_key,
    )
    return select_narrowest_cohort(latest, population)


def _feature_recency_key(feature: MatchFeature | dict[str, Any]) -> tuple[bool, int, int]:
    if isinstance(feature, dict):
        start_time = feature.get("start_time")
        match_id = feature.get("match_id") or 0
    else:
        start_time = feature.start_time
        match_id = feature.match_id
    return (start_time is not None, int(start_time or 0), int(match_id))


def _profile_account_id(profile: dict[str, Any], account_id: int) -> bool:
    nested = profile.get("profile")
    if not isinstance(nested, dict) or nested.get("account_id") is None:
        return False
    try:
        return int(nested["account_id"]) == account_id
    except (TypeError, ValueError):
        return False


def _profile_for_report(profile: dict[str, Any], account_id: int) -> dict[str, Any]:
    nested = profile.get("profile")
    if not isinstance(nested, dict):
        nested = {}
    return {
        "account_id": account_id,
        "personaname": nested.get("personaname") or "Anonymous player",
        "avatarfull": nested.get("avatarfull"),
        "rank_tier": nested.get("rank_tier"),
        "profile_url": f"https://www.opendota.com/players/{account_id}",
    }


def _normalized_record(match: NormalizedMatch) -> dict[str, Any]:
    return {
        "match_id": match.match_id,
        "account_id": match.account_id,
        "start_time": match.start_time,
        "duration_seconds": match.duration_seconds,
        "radiant": match.radiant,
        "won": match.won,
        "game_mode": match.game_mode,
        "lobby_type": match.lobby_type,
        "patch": match.patch,
        "rank_tier": match.rank_tier,
        "coverage": match.coverage.as_dict(),
        "participants": [
            {
                "account_id": participant.account_id,
                "player_slot": participant.player_slot,
                "hero_id": participant.hero_id,
                "lane_role": participant.lane_role,
                "won": participant.won,
                "kills": participant.kills,
                "deaths": participant.deaths,
                "assists": participant.assists,
                "last_hits": participant.last_hits,
                "gold_per_min": participant.gold_per_min,
                "tower_damage": participant.tower_damage,
                "role": participant.role,
                "role_probability": participant.role_probability,
                "death_events_available": participant.death_events_available,
                "events": [asdict(event) for event in participant.events],
            }
            for participant in match.participants
        ],
        "objectives": [asdict(event) for event in match.objectives],
    }
