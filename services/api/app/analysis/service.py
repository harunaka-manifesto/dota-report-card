from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from app.analysis.budget import CostPolicy, DataCostLedger
from app.analysis.deep_scan import (
    acquire_selected_matches,
    evaluate_deep_hypotheses,
    plan_deep_scan,
    plan_diagnostic_deep_scan,
)
from app.analysis.source import AnalysisSource
from app.api.report_schemas import validate_free_dna_report
from app.cohorts.selector import CohortSelection, select_narrowest_cohort
from app.core.config import FREE_HISTORY_WINDOW_DAYS, RECENCY_HALF_LIFE_DAYS, Settings, get_settings
from app.core.errors import (
    AppError,
    DeepEntitlementRequired,
    InsufficientMatchHistory,
    ProfileUnavailable,
    SteamIdentityUnavailable,
)
from app.core.metrics import record_metric
from app.core.security import PlayerIdentifier, parse_player_identifier
from app.dna.pipeline import analyze_dna
from app.dna.sessions import SessionPolicy, infer_sessions
from app.features.calculators import calculate_match_features
from app.features.models import MatchFeature
from app.features.summary_calculators import calculate_summary_features
from app.features.summary_models import SummaryFeatureSet
from app.identity.steam import SteamVanityResolver
from app.ingestion.coverage import coverage_for_match
from app.ingestion.eligibility import assess_match
from app.ingestion.normalize import NormalizedMatch
from app.ingestion.summary_history_contract import (
    SUMMARY_HISTORY_PROJECTION,
    SUMMARY_HISTORY_PROVIDER_LIMIT,
    SUMMARY_HISTORY_WINDOW_DAYS,
    CanonicalSummaryHistory,
    canonical_summary_history_cache_key,
    normalize_canonical_summary_history,
    request_manifest,
)
from app.ingestion.summary_normalize import (
    filter_history_window,
    normalize_summary_rows,
    previous_year_window,
)
from app.insights.evaluator import InsightContext, evaluate_insights
from app.opendota.cache import payload_hash
from app.patterns.detector import detect_patterns
from app.player_analysis_v6.artifacts import ArtifactValidationError, load_context_baseline_artifact
from app.player_analysis_v6.calibration import load_threshold_artifact
from app.player_analysis_v6.hero_portfolio import load_v6_hero_taxonomy
from app.player_analysis_v61.artifacts import (
    load_context_baseline_artifact_v61,
    load_threshold_artifact_v61,
    load_v61_artifact_bundle,
    load_v61_production_beta_authorization,
)
from app.player_analysis_v61.versions import MODEL_VERSION as V61_MODEL_VERSION
from app.reports.assembly import assemble_player_dna_report, assemble_report
from app.reports.dna_assembly import assemble_free_dna_report_v4
from app.reports.dna_assembly_v6 import assemble_free_dna_report_v6
from app.reports.dna_assembly_v61 import assemble_free_dna_report_v61
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
        identity_resolver: SteamVanityResolver | None = None,
        parse_transport: Any | None = None,
    ) -> None:
        self.source = source
        self.repository = repository or InMemoryRepository()
        self.settings = settings or get_settings()
        self.cohort_population = tuple(cohort_population)
        self.identity_resolver = identity_resolver
        self.parse_transport = parse_transport
        self.v6_baseline_resolver = None
        self.v6_thresholds = None
        self.v6_taxonomy_by_hero = None
        self.v61_baseline_resolver = None
        self.v61_thresholds = None
        self.v61_taxonomy_by_hero = None
        self.v61_artifact_checksums: dict[str, str] = {}
        self.v61_supporting_artifacts: dict[str, Any] = {}
        if self.settings.free_dna_v6_enabled and self.settings.free_dna_v61_enabled:
            raise ArtifactValidationError("V6.0 and V6.1 generation flags are mutually exclusive")
        if self.settings.free_dna_v61_enabled:
            (
                self.v61_baseline_resolver,
                self.v61_thresholds,
                self.v61_artifact_checksums,
                self.v61_supporting_artifacts,
            ) = self._load_v61_artifacts()
            self.v61_taxonomy_by_hero = load_v6_hero_taxonomy()
        if self.settings.free_dna_v6_enabled:
            self.v6_baseline_resolver, self.v6_thresholds = self._load_v6_artifacts()
            self.v6_taxonomy_by_hero = load_v6_hero_taxonomy()
        self._tasks: set[asyncio.Task[None]] = set()
        self._scheduled_job_ids: set[str] = set()
        self._semaphore: asyncio.Semaphore | None = None

    def _load_v6_artifacts(self) -> tuple[Any, Any]:
        """Load validated artifacts before the v6 flag can serve traffic."""

        if self.settings.free_dna_v6_model_version != "free-dna-model-6.0.0":
            raise ArtifactValidationError(
                "FREE_DNA_V6_MODEL_VERSION must match the approved v6 runtime model"
            )
        baseline_path = self.settings.free_dna_v6_baseline_artifact_path
        threshold_path = self.settings.free_dna_v6_threshold_artifact_path
        if baseline_path is None or threshold_path is None:
            raise ArtifactValidationError(
                "FREE_DNA_V6_ENABLED requires explicit validated baseline and threshold artifact paths"
            )
        try:
            baseline_artifact = load_context_baseline_artifact(baseline_path)
            threshold_artifact = load_threshold_artifact(threshold_path)
        except ArtifactValidationError:
            # Configuration errors must stop startup; no v5 fallback is safe
            # when the caller explicitly enabled v6.
            raise
        return baseline_artifact.resolver(), threshold_artifact.metrics

    def _load_v61_artifacts(self) -> tuple[Any, Any, dict[str, str], dict[str, Any]]:
        if self.settings.free_dna_v61_model_version != V61_MODEL_VERSION:
            raise ArtifactValidationError(
                "FREE_DNA_V61_MODEL_VERSION must match the approved V6.1 runtime model"
            )
        baseline_path = self.settings.free_dna_v61_baseline_artifact_path
        threshold_path = self.settings.free_dna_v61_threshold_artifact_path
        artifact_dir = self.settings.free_dna_v61_artifact_dir
        # The checked-in fixture pair is retained for unit/integration tests
        # only.  Real V6.1 paths must use the complete frozen directory below;
        # this explicit suffix prevents an incomplete production bundle from
        # silently falling back to fixture constants.
        if (
            self.settings.app_env != "production"
            and
            artifact_dir is None
            and baseline_path is not None
            and threshold_path is not None
            and baseline_path.name.endswith(".fixture.json")
            and threshold_path.name.endswith(".fixture.json")
        ):
            baseline = load_context_baseline_artifact_v61(baseline_path)
            thresholds = load_threshold_artifact_v61(threshold_path)
            return (
                baseline.resolver(),
                thresholds.metrics,
                {
                    "context_baseline": hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
                    "thresholds": hashlib.sha256(threshold_path.read_bytes()).hexdigest(),
                },
                {},
            )
        if artifact_dir is None and baseline_path is not None:
            artifact_dir = baseline_path.parent
        if baseline_path is None or threshold_path is None or artifact_dir is None:
            raise ArtifactValidationError(
                "FREE_DNA_V61_ENABLED requires a complete frozen V6.1 artifact bundle"
            )
        if baseline_path != artifact_dir / "context-baseline-3.0.0.json" or threshold_path != artifact_dir / "metric-thresholds-6.1.0.json":
            raise ArtifactValidationError("V6.1 baseline/threshold paths must point into the frozen artifact directory")
        bundle = load_v61_artifact_bundle(artifact_dir)
        bundle_checksums = dict(bundle.checksums)
        checksums = dict(bundle_checksums)
        checksums.update({"context_baseline": checksums["context-baseline-3.0.0.json"], "thresholds": checksums["metric-thresholds-6.1.0.json"]})
        release_authorization_path = (
            self.settings.free_dna_v61_release_authorization_path
            or artifact_dir / "production-beta-authorization-6.1.0.json"
        )
        expected_revision = self.settings.release_commit_sha
        expected_dirty = self.settings.release_worktree_dirty
        if self.settings.app_env == "production":
            if not expected_revision or expected_dirty is not False:
                raise ArtifactValidationError(
                    "production V6.1 requires RELEASE_COMMIT_SHA and RELEASE_WORKTREE_DIRTY=false"
                )
        release_authorization = load_v61_production_beta_authorization(
            release_authorization_path,
            artifact_checksums=bundle_checksums,
            expected_source_revision=expected_revision,
            expected_dirty_worktree=expected_dirty,
        )
        return (
            bundle.baseline.resolver(),
            bundle.thresholds.metrics,
            checksums,
            {
                "summary_prior": bundle.summary_prior,
                "distance_calibration": bundle.distance_calibration,
                "session_reliability": bundle.session_reliability,
                "semantic_calibration": bundle.semantic_calibration,
                "manifest": bundle.manifest,
                "production_beta_authorization": release_authorization,
            },
        )

    async def create_analysis(
        self,
        player: str,
        *,
        refresh: bool = False,
        enqueue: bool = True,
        mode: str | None = None,
    ) -> tuple[AnalysisJob, bool]:
        if mode not in (None, "free"):
            raise ValueError("The generic analysis path only creates Free reports")
        identifier = await self._resolve_identifier(player)
        analysis_mode = "free"
        compatibility_version = self._compatibility_model_version(analysis_mode)
        if not refresh:
            raw_history_hash = None
            identity_fingerprint = None
            if analysis_mode == "free" and hasattr(self.repository, "get_cached_raw_payload"):
                cached_profile = self.repository.get_cached_raw_payload(
                    f"/players/{identifier.account_id}", str(identifier.account_id)
                )
                if isinstance(cached_profile, dict):
                    identity_fingerprint = _identity_fingerprint(cached_profile)
                cached = self.repository.get_cached_raw_payload(
                    canonical_summary_history_cache_key(identifier.account_id)
                    if self.settings.free_dna_v61_enabled
                    else f"/players/{identifier.account_id}/matches",
                    str(identifier.account_id),
                    max_age_seconds=self.settings.effective_summary_history_cache_ttl_seconds,
                )
                if isinstance(cached, list):
                    raw_history_hash = payload_hash(cached)
            # Free reports may only reuse a completed snapshot after the
            # bounded history identity is known. Otherwise a retained report
            # could outlive its upstream history cache and be reused blindly.
            if analysis_mode != "free" or (
                raw_history_hash is not None and identity_fingerprint is not None
            ):
                existing = self.repository.find_compatible_completed(
                    identifier.account_id,
                    compatibility_version,
                    analysis_mode=analysis_mode,
                    max_age_seconds=self.settings.compatible_analysis_ttl_seconds,
                    raw_history_hash=raw_history_hash,
                    identity_fingerprint=identity_fingerprint,
                )
                if existing is not None:
                    return existing, True
        job, reused = self.repository.get_or_create_inflight_job(
            identifier.account_id,
            identifier.canonical_url,
            compatibility_version,
            analysis_mode,
        )
        if enqueue:
            self._enqueue(job, identifier)
        return job, reused

    def _compatibility_model_version(self, analysis_mode: str) -> str:
        if analysis_mode == "free":
            if self.settings.free_dna_v61_enabled:
                from app.player_analysis_v61.versions import default_versions_v61

                versions = {
                    **default_versions_v61(),
                    "eligibility": "summary-eligibility-1.0.0",
                    "model": self.settings.free_dna_v61_model_version,
                    "template": self.settings.template_version,
                    "artifacts": self.v61_artifact_checksums,
                }
                digest = hashlib.sha256(json.dumps(versions, sort_keys=True).encode()).hexdigest()
                return f"free-analysis-v61-{digest[:44]}"
            if self.settings.free_dna_v6_enabled:
                from app.player_analysis_v6.models import default_versions

                versions = {
                    **default_versions(),
                    "eligibility": "summary-eligibility-1.0.0",
                    "model": self.settings.free_dna_v6_model_version,
                    "template": self.settings.template_version,
                }
                digest = hashlib.sha256(json.dumps(versions, sort_keys=True).encode()).hexdigest()
                return f"free-analysis-v6-{digest[:45]}"
            from app.behavior.context_baseline import CONTEXT_BASELINE_VERSION
            from app.behavior.elements.registry import ELEMENT_REGISTRY_VERSION
            from app.behavior.outcomes import SEMANTIC_OUTCOME_VERSION
            from app.behavior.patterns.registry import PATTERN_REGISTRY_VERSION
            from app.behavior.service import BEHAVIOR_MODEL_VERSION
            from app.content.catalog import copy_version, semantic_copy_version
            from app.dna.features.models import FEATURE_VERSION
            from app.dna.performance import PERFORMANCE_PROXY_VERSION
            from app.dna.pipeline import DNA_SCORING_VERSION
            from app.dna.recency import RECENCY_WEIGHTING_VERSION
            from app.dna.sessions import SESSION_VERSION
            from app.hero_portfolio.config import PORTFOLIO_CONFIG_VERSION
            from app.hero_portfolio.version import (
                HERO_EXPRESSIONS_VERSION,
                HERO_MATCHUPS_VERSION,
                HERO_MIRROR_VERSION,
                HERO_PORTFOLIO_VERSION,
                HERO_RELATIONSHIPS_VERSION,
                HERO_RELIABILITY_VERSION,
                HERO_SITUATIONS_VERSION,
                HERO_SYNERGIES_VERSION,
                PATTERN_ACTIONS_VERSION,
            )
            from app.heroes.knowledge import (
                HERO_KNOWLEDGE_SCHEMA_VERSION,
                HERO_SEMANTICS_VERSION,
                HeroKnowledgeRepository,
            )
            from app.heroes.recommendations import SEMANTIC_RECOMMENDATION_VERSION
            from app.heroes.taxonomy import TAXONOMY_VERSION
            from app.reports.dna_assembly import REPORT_SCHEMA_VERSION, REPORT_STORY_VERSION
            from app.share.service import RENDERER_VERSION

            versions = {
                "eligibility": "summary-eligibility-1.0.0",
                "sessions": SESSION_VERSION,
                "features": FEATURE_VERSION,
                "dna_scoring": DNA_SCORING_VERSION,
                "hero_taxonomy": TAXONOMY_VERSION,
                "hero_knowledge": HeroKnowledgeRepository().version()
                or "hero-knowledge-unavailable",
                "hero_knowledge_schema": HERO_KNOWLEDGE_SCHEMA_VERSION,
                "hero_semantics": HERO_SEMANTICS_VERSION,
                "hero_portfolio": f"{HERO_PORTFOLIO_VERSION}+{PORTFOLIO_CONFIG_VERSION}",
                "hero_mirror": HERO_MIRROR_VERSION,
                "hero_relationships": HERO_RELATIONSHIPS_VERSION,
                "hero_expressions": HERO_EXPRESSIONS_VERSION,
                "hero_reliability": HERO_RELIABILITY_VERSION,
                "hero_matchups": HERO_MATCHUPS_VERSION,
                "hero_synergies": HERO_SYNERGIES_VERSION,
                "hero_situations": HERO_SITUATIONS_VERSION,
                "story": REPORT_STORY_VERSION,
                "copy": copy_version(),
                "semantic_copy": semantic_copy_version(),
                "semantic_outcomes": SEMANTIC_OUTCOME_VERSION,
                "semantic_recommendations": SEMANTIC_RECOMMENDATION_VERSION,
                "report_schema": REPORT_SCHEMA_VERSION,
                "model": self.settings.model_version,
                "template": self.settings.template_version,
                "share_renderer": RENDERER_VERSION,
                "behavior_model": BEHAVIOR_MODEL_VERSION,
                "element_registry": ELEMENT_REGISTRY_VERSION,
                "pattern_registry": PATTERN_REGISTRY_VERSION,
                "context_baseline": CONTEXT_BASELINE_VERSION,
                "pattern_actions": PATTERN_ACTIONS_VERSION,
                "performance_proxy": PERFORMANCE_PROXY_VERSION,
                "recency_weighting": RECENCY_WEIGHTING_VERSION,
            }
            digest = hashlib.sha256(json.dumps(versions, sort_keys=True).encode()).hexdigest()
            return f"free-analysis-{digest[:48]}"
        return self.settings.model_version

    async def _resolve_identifier(self, player: str) -> PlayerIdentifier:
        identifier = parse_player_identifier(player)
        if not identifier.vanity:
            return identifier
        if self.identity_resolver is None:
            raise SteamIdentityUnavailable(
                "Steam vanity URL resolution is not configured",
                detail="Set STEAM_API_KEY or provide an identity resolver.",
            )
        account_id = await self.identity_resolver.resolve(identifier.vanity)
        return PlayerIdentifier(
            account_id,
            f"https://www.opendota.com/players/{account_id}",
        )

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

    def enqueue_existing_job(self, job: AnalysisJob) -> None:
        """Dispatch a repository-created continuation job through the normal worker seam."""

        self._enqueue(job, PlayerIdentifier(job.account_id, job.canonical_player))

    def enqueue_deep_continuation(
        self,
        job: AnalysisJob,
        *,
        parent_report_id: str,
        diagnostic_question_id: str,
        interaction_session_id: str | None = None,
    ) -> None:
        """Dispatch a v6 diagnostic while retaining its audited parent choice."""

        del interaction_session_id  # State access was authorized by the route.
        job.parent_report_id = parent_report_id
        job.diagnostic_question_id = diagnostic_question_id
        self.enqueue_existing_job(job)

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
            if job.analysis_mode == "deep_scan":
                self._validate_deep_authorization(job)
            await self._run(job, identifier)
            record_metric(
                "analysis.completed",
                tags={
                    "mode": job.analysis_mode,
                    "history_tier": "limited" if 30 <= job.eligible_matches < 60 else "normal",
                    "model": job.model_version,
                },
            )
        except asyncio.CancelledError:
            self.repository.fail_job(job, "ANALYSIS_CANCELLED", "The analysis was cancelled")
            record_metric(
                "analysis.failed", tags={"code": "ANALYSIS_CANCELLED", "mode": job.analysis_mode}
            )
            raise
        except AppError as exc:
            self.repository.fail_job(job, exc.code, exc.message)
            record_metric("analysis.failed", tags={"code": exc.code, "mode": job.analysis_mode})
        except Exception:
            logger.exception("analysis_failed job_id=%s account_id=%s", job.job_id, job.account_id)
            self.repository.fail_job(job, "ANALYSIS_FAILED", "Unexpected analysis failure")
            record_metric(
                "analysis.failed", tags={"code": "ANALYSIS_FAILED", "mode": job.analysis_mode}
            )

    def _validate_deep_authorization(self, job: AnalysisJob) -> None:
        decision = job.entitlement_decision
        if not isinstance(decision, dict) or decision.get("allowed") is not True:
            raise DeepEntitlementRequired("Deep Analysis capability is missing or denied")
        if not str(decision.get("grant_id") or "").strip():
            raise DeepEntitlementRequired("Deep Analysis capability is malformed")
        if decision.get("report_id") != job.parent_report_id:
            raise DeepEntitlementRequired("Deep Analysis capability is bound to another report")
        if decision.get("diagnostic_question_id") != job.diagnostic_question_id:
            raise DeepEntitlementRequired("Deep Analysis capability is bound to another question")
        account_value = decision.get("account_id")
        account_id = int(account_value) if isinstance(account_value, (int, str)) else -1
        if (
            account_id != job.account_id
            or decision.get("revoked") is True
            or decision.get("replay_detected") is True
        ):
            raise DeepEntitlementRequired("Deep Analysis capability is invalid")
        expiry = decision.get("expires_at")
        if isinstance(expiry, (int, float)):
            expires_at = float(expiry)
        elif isinstance(expiry, str):
            try:
                expires_at = datetime.fromisoformat(expiry.replace("Z", "+00:00")).timestamp()
            except ValueError:
                expires_at = 0.0
        else:
            expires_at = 0.0
        if expires_at <= datetime.now(UTC).timestamp():
            raise DeepEntitlementRequired("Deep Analysis capability has expired")

    async def _run(self, job: AnalysisJob, identifier: PlayerIdentifier) -> None:
        self.repository.update_job(
            job,
            status="running",
            stage="resolving_player",
            message="Resolving the public player profile",
        )
        cached_profile = (
            self.repository.get_cached_raw_payload(
                f"/players/{identifier.account_id}", str(identifier.account_id)
            )
            if hasattr(self.repository, "get_cached_raw_payload")
            else None
        )
        profile = (
            cached_profile
            if isinstance(cached_profile, dict)
            else await self.source.get_player(identifier.account_id)
        )
        if not profile or not _profile_account_id(profile, identifier.account_id):
            raise ProfileUnavailable("Public profile is unavailable")
        self.repository.persist_raw_payload(
            f"/players/{identifier.account_id}",
            str(identifier.account_id),
            profile,
            {"adapter_version": "opendota-player-1.0.0"},
        )
        self.repository.update_job(
            job, stage="player_found", message="Public player profile resolved"
        )

        self.repository.update_job(
            job, stage="fetching_history", message="Fetching latest match history"
        )
        history_limit = self.settings.effective_free_history_limit
        cost_ledger = DataCostLedger()
        cost_policy = CostPolicy()
        canonical_history: CanonicalSummaryHistory | None = None
        v61_history_key = canonical_summary_history_cache_key(identifier.account_id)
        history_cache_key = (
            v61_history_key
            if job.analysis_mode == "free" and self.settings.free_dna_v61_enabled
            else f"/players/{identifier.account_id}/matches"
        )
        cached_history = (
            self.repository.get_cached_raw_payload(
                history_cache_key,
                str(identifier.account_id),
                max_age_seconds=self.settings.effective_summary_history_cache_ttl_seconds,
            )
            if hasattr(self.repository, "get_cached_raw_payload")
            else None
        )
        if isinstance(cached_history, list):
            history = list(cached_history)
            cost_ledger.record("history", policy=cost_policy, cache_hit=True, units=0.0)
            if job.analysis_mode == "free" and self.settings.free_dna_v61_enabled:
                canonical_history = normalize_canonical_summary_history(
                    history,
                    identifier.account_id,
                    request_count=1,
                    provider_limit=SUMMARY_HISTORY_PROVIDER_LIMIT,
                )
        else:
            if job.analysis_mode == "free" and self.settings.free_dna_v61_enabled:
                history = await self._get_v61_summary_history(identifier.account_id)
                canonical_history = normalize_canonical_summary_history(
                    history,
                    identifier.account_id,
                    request_count=1,
                    provider_limit=SUMMARY_HISTORY_PROVIDER_LIMIT,
                )
            else:
                history = await self._get_summary_history(
                    identifier.account_id,
                    limit=history_limit,
                )
            history = list(history)
            cost_ledger.record("history", policy=cost_policy)
        self.repository.persist_raw_payload(
            history_cache_key,
            str(identifier.account_id),
            history,
            {
                "requested_limit": history_limit,
                "window_days": FREE_HISTORY_WINDOW_DAYS,
                "actual_count": len(history),
                "projection": (
                    list(SUMMARY_HISTORY_PROJECTION)
                    if canonical_history is not None
                    else None
                ),
                "adapter_version": (
                    "opendota-summary-2.0.0"
                    if canonical_history is not None
                    else "opendota-summary-1.0.0"
                ),
                **(
                    {
                        "request_manifest": request_manifest(),
                        "history_audit": canonical_history.audit.as_dict(),
                    }
                    if canonical_history is not None
                    else {}
                ),
            },
        )
        if not history:
            raise InsufficientMatchHistory("No match history was returned")
        job.processed_matches = len(history)

        if job.analysis_mode == "free":
            await self._save_player_dna(
                job,
                identifier,
                profile,
                history=history,
                history_limit=history_limit,
                cost_ledger=cost_ledger,
                canonical_history=canonical_history,
            )
            return

        self.repository.update_job(
            job, stage="filtering_matches", message="Applying match eligibility rules"
        )
        summary_candidates: list[dict[str, Any]] = []
        exclusion_ledger: list[dict[str, Any]] = []
        candidate_history = history if history_limit is None else history[:history_limit]
        for summary in candidate_history:
            result = assess_match(summary, account_id=identifier.account_id)
            if result.eligible:
                summary_candidates.append(summary)
            else:
                exclusion_ledger.append(result.as_dict())
        job.eligible_matches = len(summary_candidates)
        summary_feature_set = calculate_summary_features(
            summary_candidates,
            account_id=identifier.account_id,
            session_gap_minutes=self.settings.effective_session_gap_minutes,
        )
        if not summary_feature_set.matches:
            raise InsufficientMatchHistory("No eligible summary matches were returned")
        job.eligible_matches = len(summary_feature_set.matches)
        self.repository.record_event(
            job, f"{len(exclusion_ledger)} history rows excluded before summary analysis"
        )

        self.repository.update_job(
            job,
            stage="detecting_patterns",
            message="Detecting broad Player DNA patterns without match hydration",
        )
        patterns = detect_patterns(summary_feature_set)
        available_families = _available_families(
            self.repository,
            summary_feature_set,
            identifier.account_id,
        )
        diagnostic_question = _job_diagnostic_question(job, self.repository)
        if diagnostic_question is not None:
            hypotheses, selection_plan = plan_diagnostic_deep_scan(
                diagnostic_question,
                summary_feature_set,
                max_deep_matches=self.settings.effective_max_deep_matches,
                max_parse_requests=self.settings.effective_max_parse_requests,
                max_data_cost=max(
                    0.0,
                    self.settings.effective_max_data_cost_per_report
                    - cost_policy.units_for("history"),
                ),
                min_marginal_information_gain=(
                    self.settings.effective_min_marginal_information_gain
                ),
                parse_min_marginal_information_gain=(
                    self.settings.effective_min_parse_information_gain
                ),
                available_families_by_match=available_families,
            )
            job.selection_plan = selection_plan.as_dict()
            job.stopping_reason = selection_plan.stopping_reason
        else:
            hypotheses, selection_plan = plan_deep_scan(
                patterns,
                summary_feature_set,
                max_primary_hypotheses=self.settings.effective_max_primary_hypotheses,
                max_deep_matches=self.settings.effective_max_deep_matches,
                max_parse_requests=self.settings.effective_max_parse_requests,
                max_data_cost=max(
                    0.0,
                    self.settings.effective_max_data_cost_per_report
                    - cost_policy.units_for("history"),
                ),
                min_marginal_information_gain=(
                    self.settings.effective_min_marginal_information_gain
                ),
                available_families_by_match=available_families,
            )

        deep_history_limit = history_limit if history_limit is not None else len(history)
        await self._run_deep_scan(
            job=job,
            identifier=identifier,
            profile=profile,
            summary_feature_set=summary_feature_set,
            patterns=patterns,
            hypotheses=hypotheses,
            selection_plan=selection_plan,
            cost_ledger=cost_ledger,
            cost_policy=cost_policy,
            exclusion_ledger=exclusion_ledger,
            history_limit=deep_history_limit,
        )

    async def _save_player_dna(
        self,
        job: AnalysisJob,
        identifier: PlayerIdentifier,
        profile: dict[str, Any],
        *,
        history: list[dict[str, Any]],
        history_limit: int | None,
        cost_ledger: DataCostLedger,
        canonical_history: CanonicalSummaryHistory | None = None,
    ) -> None:
        self.repository.update_job(
            job,
            stage="normalizing_history",
            message="Sorting the matches we can read",
        )
        normalized = (
            canonical_history.normalization
            if canonical_history is not None
            else normalize_summary_rows(history, identifier.account_id)
        )
        self.repository.record_event(
            job,
            f"Normalized {len(normalized.matches)} unique summary rows",
        )
        window_end = int(datetime.now(UTC).timestamp())
        window_start, window_end = previous_year_window(
            window_end=window_end,
            days=FREE_HISTORY_WINDOW_DAYS,
        )
        windowed_matches = filter_history_window(
            normalized.eligible_matches,
            window_start=window_start,
            window_end=window_end,
        )
        job.eligible_matches = len(windowed_matches)
        if job.eligible_matches < 30:
            raise InsufficientMatchHistory(
                "At least 30 common eligible matches are required to build Free Dota DNA"
            )
        history_tier = "limited" if job.eligible_matches < 60 else "normal"

        if self.settings.free_dna_v61_enabled:
            if canonical_history is None:
                raise RuntimeError("V6.1 generation requires canonical history audit metadata")
            if self.v61_thresholds is None or self.v61_baseline_resolver is None:
                raise RuntimeError("V6.1 generation requires loaded analytical artifacts")
            session_result = infer_sessions(
                windowed_matches,
                SessionPolicy(gap_minutes=self.settings.effective_session_gap_minutes),
                window_start=window_start,
                window_end=window_end,
            )
            completed_sessions = {
                session.session_id: session in session_result.completed_sessions
                for session in session_result.sessions
            }
            self.repository.update_job(
                job,
                stage="rendering_report",
                message="Building your V6.1 identity, findings, and story report",
            )
            protected_cohorts: dict[str, Any] = {}
            report = assemble_free_dna_report_v61(
                account_id=identifier.account_id,
                profile=_profile_for_report(profile, identifier.account_id),
                matches=tuple(session_result.matches),
                canonical_history=canonical_history,
                processed_matches=job.processed_matches,
                eligible_matches=job.eligible_matches,
                model_version=self.settings.free_dna_v61_model_version,
                template_version=self.settings.template_version,
                cost_ledger=cost_ledger,
                analysis_version_fingerprint=job.model_version,
                baseline_resolver=self.v61_baseline_resolver,
                thresholds=self.v61_thresholds,
                taxonomy_by_hero=self.v61_taxonomy_by_hero,
                completed_sessions=completed_sessions,
                artifact_checksums=self.v61_artifact_checksums,
                supporting_artifacts=self.v61_supporting_artifacts,
                shadow_enabled=self.settings.free_dna_v61_shadow_enabled,
                experimental_evolution_enabled=self.settings.free_dna_v61_experimental_evolution_enabled,
                experimental_loops_enabled=self.settings.free_dna_v61_experimental_loops_enabled,
                protected_cohorts_out=protected_cohorts,
            )
            report = validate_free_dna_report(report)
            persist_report = getattr(self.repository, "save_report_with_protected_cohorts", None)
            if persist_report is None:
                raise RuntimeError("V6.1 generation requires atomic protected Deep cohort persistence")
            report_id = persist_report(
                account_id=identifier.account_id,
                data_cutoff=max((item.start_time or 0 for item in windowed_matches), default=None),
                model_version=job.model_version,
                template_version=self.settings.template_version,
                report=report,
                evidence=[],
                protected_cohorts=protected_cohorts,
            )
            self.repository.complete_job(job, report_id)
            return

        if self.settings.free_dna_v6_enabled:
            # v6 consumes the normalized summary window directly.  The v5
            # behavior model is intentionally not constructed on this path.
            session_result = infer_sessions(
                windowed_matches,
                SessionPolicy(gap_minutes=self.settings.effective_session_gap_minutes),
                window_start=window_start,
                window_end=window_end,
            )
            v6_matches = session_result.matches
            completed_sessions = {
                session.session_id: session in session_result.completed_sessions
                for session in session_result.sessions
            }
            self.repository.update_job(
                job,
                stage="rendering_report",
                message="Building your v6 identity, findings, and story report",
            )
            report = assemble_free_dna_report_v6(
                account_id=identifier.account_id,
                profile=_profile_for_report(profile, identifier.account_id),
                analysis=tuple(v6_matches),
                processed_matches=job.processed_matches,
                eligible_matches=job.eligible_matches,
                raw_payload_hash=payload_hash(history),
                history_limit=history_limit,
                model_version=self.settings.free_dna_v6_model_version,
                template_version=self.settings.template_version,
                cost_ledger=cost_ledger,
                analysis_version_fingerprint=job.model_version,
                baseline_resolver=self.v6_baseline_resolver,
                thresholds=self.v6_thresholds,
                taxonomy_by_hero=self.v6_taxonomy_by_hero,
                completed_sessions=completed_sessions,
            )
            report = validate_free_dna_report(report)
            report_id = self.repository.save_report(
                account_id=identifier.account_id,
                data_cutoff=max((item.start_time or 0 for item in windowed_matches), default=None),
                model_version=job.model_version,
                template_version=self.settings.template_version,
                report=report,
                evidence=[],
            )
            self.repository.complete_job(job, report_id)
            return

        # Free DNA and finding synthesis must share one eligible population.
        # Ineligible rows remain available only to the private exclusion ledger.
        dna_analysis = analyze_dna(
            windowed_matches,
            session_gap_minutes=self.settings.effective_session_gap_minutes,
            history_tier=history_tier,
            report_seed=payload_hash(history),
            window_start=window_start,
            window_end=window_end,
            recency_half_life_days=RECENCY_HALF_LIFE_DAYS,
            on_stage=lambda stage, message: self.repository.update_job(
                job, stage=stage, message=message
            ),
        )

        behavior = dna_analysis.behavior
        if behavior is None:
            raise InsufficientMatchHistory("Behavior model did not produce a result")
        self.repository.update_job(
            job,
            stage="rendering_report",
            message=(
                "Building your v6 identity, findings, and story report"
                if self.settings.free_dna_v6_enabled
                else "Building your Elements, Patterns, and Hero Portfolio report"
            ),
        )
        assembler = (
            assemble_free_dna_report_v6
            if self.settings.free_dna_v6_enabled
            else assemble_free_dna_report_v4
        )
        report = assembler(
            account_id=identifier.account_id,
            profile=_profile_for_report(profile, identifier.account_id),
            analysis=dna_analysis,
            processed_matches=job.processed_matches,
            eligible_matches=job.eligible_matches,
            raw_payload_hash=payload_hash(history),
            history_limit=history_limit,
            model_version=self.settings.model_version,
            template_version=self.settings.template_version,
            cost_ledger=cost_ledger,
            analysis_version_fingerprint=job.model_version,
        )
        report = validate_free_dna_report(report)
        report_id = self.repository.save_report(
            account_id=identifier.account_id,
            data_cutoff=max((item.start_time or 0 for item in dna_analysis.matches), default=None),
            model_version=job.model_version,
            template_version=self.settings.template_version,
            report=report,
            evidence=[],
        )
        self.repository.complete_job(job, report_id)

    async def _get_summary_history(
        self,
        account_id: int,
        *,
        limit: int | None,
    ) -> list[dict[str, Any]]:
        """Call the year-windowed source while tolerating older test adapters."""

        try:
            return list(
                await self.source.get_matches(
                    account_id,
                    limit=limit,
                    days=FREE_HISTORY_WINDOW_DAYS,
                )
            )
        except TypeError as exc:
            # External adapters written against the pre-window protocol may
            # not accept ``days`` yet.  Keep this compatibility path narrow so
            # real source failures are not swallowed.
            if "days" not in str(exc):
                raise
            return list(await self.source.get_matches(account_id, limit=limit))

    async def _get_v61_summary_history(self, account_id: int) -> list[dict[str, Any]]:
        """Read the V6.1 canonical payload without entering pagination."""

        method = getattr(self.source, "get_summary_history_once", None)
        if method is None:
            raise TypeError(
                "FREE_DNA_V61_ENABLED requires a source with get_summary_history_once"
            )
        return list(
            await method(
                account_id,
                days=SUMMARY_HISTORY_WINDOW_DAYS,
                project=SUMMARY_HISTORY_PROJECTION,
                provider_limit=SUMMARY_HISTORY_PROVIDER_LIMIT,
            )
        )

    async def _run_deep_scan(
        self,
        *,
        job: AnalysisJob,
        identifier: PlayerIdentifier,
        profile: dict[str, Any],
        summary_feature_set: SummaryFeatureSet,
        patterns: list[Any],
        hypotheses: list[Any],
        selection_plan: Any,
        cost_ledger: DataCostLedger,
        cost_policy: CostPolicy,
        exclusion_ledger: list[dict[str, Any]],
        history_limit: int,
    ) -> None:
        self.repository.update_job(
            job,
            stage="hydrating_selected_matches",
            message=f"Hydrating {len(selection_plan.selected)} globally selected matches",
        )
        normalized = await acquire_selected_matches(
            selection_plan,
            source=self.source,
            parse_transport=self.parse_transport,
            repository=self.repository,
            account_id=identifier.account_id,
            ledger=cost_ledger,
            policy=cost_policy,
            parse_min_marginal_information_gain=self.settings.effective_min_parse_information_gain,
            max_detail_requests=self.settings.effective_max_deep_matches,
            max_parse_requests=self.settings.effective_max_parse_requests,
            max_data_cost=self.settings.effective_max_data_cost_per_report,
        )
        selected_summary_features = [
            selected.candidate.feature
            for selected in selection_plan.selected
            if selected.candidate.already_available
        ]
        if not normalized:
            self.repository.add_warning(
                job,
                "No selected deep matches were available; returning the summary findings.",
            )
            report, evidence = assemble_player_dna_report(
                account_id=identifier.account_id,
                profile=_profile_for_report(profile, identifier.account_id),
                feature_set=summary_feature_set,
                patterns=patterns,
                hypotheses=hypotheses,
                selection_plan=selection_plan,
                cost_ledger=cost_ledger,
                processed_matches=job.processed_matches,
                eligible_matches=job.eligible_matches,
                history_limit=history_limit,
                model_version=self.settings.model_version,
                template_version=self.settings.template_version,
            )
            report["report_variant"] = "deep_scan"
            report["evidence_scope"]["exclusion_reasons"] = _reason_counts(exclusion_ledger)
            deep_findings = evaluate_deep_hypotheses(
                hypotheses,
                selection_plan,
                selected_summary_features,
            )
            report["deep_scan"] = {
                "patterns": [item.as_dict() for item in patterns],
                "hypotheses": [item.as_dict() for item in hypotheses],
                "selection": selection_plan.as_dict(),
                "findings": [item.as_dict() for item in deep_findings],
            }
            report["cost"] = cost_ledger.as_dict()
            report["telemetry"] = {
                "summary_matches_considered": job.processed_matches,
                "eligible_summary_matches": job.eligible_matches,
                "patterns_detected": len(patterns),
                "hypotheses_investigated": len(hypotheses),
                "hypotheses_resolved": sum(item.status == "resolved" for item in deep_findings),
                "candidate_matches": len(selection_plan.candidates),
                "deep_matches_selected": len(selection_plan.selected),
                "detail_requests": cost_ledger.detail_requests,
                "parse_requests": cost_ledger.parse_requests,
                "estimated_data_cost_units": cost_ledger.estimated_cost_units,
                "stopping_reason": selection_plan.stopping_reason,
            }
            report_id = self.repository.save_report(
                account_id=identifier.account_id,
                data_cutoff=max(
                    (item.start_time or 0 for item in summary_feature_set.matches), default=None
                ),
                model_version=self.settings.model_version,
                template_version=self.settings.template_version,
                report=report,
                evidence=evidence,
            )
            self.repository.complete_job(job, report_id)
            return

        self.repository.update_job(
            job,
            stage="computing_features",
            message="Computing reusable features for selected deep matches",
        )
        features = calculate_match_features(normalized)
        for feature in features:
            self.repository.save_derived_feature(feature.match_id, feature.as_dict())
        hydrated_ids = {item.match_id for item in features}
        deep_findings = evaluate_deep_hypotheses(
            hypotheses,
            selection_plan,
            [*features, *(item for item in selected_summary_features if item.match_id not in hydrated_ids)],
        )

        self.repository.update_job(
            job,
            stage="building_cohorts",
            message="Selecting the narrowest supported cohort",
        )
        cohort = _select_cohort(features, self.cohort_population)
        if cohort is None or not cohort.valid:
            self.repository.add_warning(job, "No valid internal comparison cohort was available")

        self.repository.update_job(
            job,
            stage="evaluating_insights",
            message="Evaluating registered insight families",
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
            job,
            stage="rendering_report",
            message="Rendering deterministic Deep Scan report",
        )
        report = assemble_report(
            context=context,
            evidence=evidence,
            exclusion_ledger=exclusion_ledger,
            processed_matches=job.processed_matches,
            eligible_matches=job.eligible_matches,
        )
        report["report_variant"] = "deep_scan"
        report["deep_scan"] = {
            "patterns": [item.as_dict() for item in patterns],
            "hypotheses": [item.as_dict() for item in hypotheses],
            "selection": selection_plan.as_dict(),
            "findings": [item.as_dict() for item in deep_findings],
        }
        report["cost"] = cost_ledger.as_dict()
        report["telemetry"] = {
            "summary_matches_considered": job.processed_matches,
            "eligible_summary_matches": job.eligible_matches,
            "patterns_detected": len(patterns),
            "deep_scan_patterns": sum(item.unexplained for item in patterns),
            "hypotheses_investigated": len(hypotheses),
            "hypotheses_resolved": sum(item.status == "resolved" for item in deep_findings),
            "candidate_matches": len(selection_plan.candidates),
            "deep_matches_selected": len(selection_plan.selected),
            "detail_requests": cost_ledger.detail_requests,
            "parse_requests": cost_ledger.parse_requests,
            "estimated_data_cost_units": cost_ledger.estimated_cost_units,
            "stopping_reason": selection_plan.stopping_reason,
        }
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
    name = str(nested.get("personaname") or "").strip()
    if not name or name.isdigit() or name.startswith(("http://", "https://")):
        name = "Anonymous player"
    avatar = nested.get("avatarfull")
    if not isinstance(avatar, str):
        avatar = None
    else:
        parsed = urlparse(avatar)
        if (
            parsed.scheme != "https"
            or parsed.hostname
            not in {
                "steamcdn-a.akamaihd.net",
                "avatars.akamai.steamstatic.com",
            }
            or parsed.query
            or parsed.fragment
        ):
            avatar = None
    return {
        "account_id": account_id,
        "personaname": name,
        "avatarfull": avatar,
        "rank_tier": nested.get("rank_tier"),
        "profile_url": f"https://www.opendota.com/players/{account_id}",
    }


def _identity_fingerprint(profile: dict[str, Any]) -> str:
    """Hash only the public identity projection used by a Free report."""

    nested = profile.get("profile")
    if not isinstance(nested, dict):
        nested = profile
    public = {
        "display_name": str(
            nested.get("personaname") or nested.get("display_name") or "Anonymous player"
        ),
        "avatar_url": nested.get("avatarfull") or nested.get("avatar_url"),
        "rank_tier": nested.get("rank_tier"),
    }
    return hashlib.sha256(
        json.dumps(public, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _analysis_mode(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"free", "deep_scan"}:
        raise ValueError("Analysis mode must be 'free' or 'deep_scan'")
    return normalized


def _job_diagnostic_question(job: AnalysisJob, repository: Any) -> dict[str, Any] | None:
    """Resolve the server-offered question for a v6 continuation job."""

    if not job.parent_report_id or not job.diagnostic_question_id:
        return None
    report = repository.get_report(job.parent_report_id)
    if not isinstance(report, dict):
        return None
    for question in report.get("diagnostic_questions") or []:
        if not isinstance(question, dict):
            continue
        identifier = (
            question.get("diagnostic_question_id")
            or question.get("question_id")
            or question.get("id")
        )
        if identifier == job.diagnostic_question_id:
            reference = question.get("protected_cohort_reference")
            if reference is not None:
                if not isinstance(job.entitlement_decision, dict) or job.entitlement_decision.get("allowed") is not True:
                    raise RuntimeError("protected V6.1 cohort resolution requires authorization")
                resolver = getattr(repository, "resolve_protected_cohort", None)
                if resolver is None:
                    raise RuntimeError("protected V6.1 cohort resolver is unavailable")
                protected = resolver(job.parent_report_id, str(reference))
                if not isinstance(protected, dict) or not isinstance(protected.get("question"), dict):
                    raise RuntimeError("protected V6.1 cohort reference could not be resolved")
                return deepcopy(protected["question"])
            return question
    return None


def _available_families(
    repository: Any,
    feature_set: SummaryFeatureSet,
    account_id: int,
) -> dict[int, frozenset[str]]:
    getter = getattr(repository, "get_cached_raw_payload", None)
    if getter is None:
        return {}
    available: dict[int, frozenset[str]] = {}
    for feature in feature_set.matches:
        detail = getter(f"/matches/{feature.match_id}", str(feature.match_id))
        parsed = getter(f"/matches/{feature.match_id}/parse", str(feature.match_id))
        if not isinstance(detail, dict) and not isinstance(parsed, dict):
            continue
        combined = dict(detail) if isinstance(detail, dict) else {}
        if isinstance(parsed, dict):
            nested = parsed.get("match")
            combined.update(dict(nested) if isinstance(nested, dict) else parsed)
        target = next(
            (
                row
                for row in combined.get("players") or []
                if isinstance(row, dict) and _as_int(row.get("account_id")) == account_id
            ),
            None,
        )
        coverage = coverage_for_match(combined, target)
        families = frozenset(family for family, value in coverage.by_family.items() if value >= 1.0)
        if families:
            available[feature.match_id] = families
    return available


def _reason_counts(ledger: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in ledger:
        for reason in entry.get("reasons", []):
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


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
