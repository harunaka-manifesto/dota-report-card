"""Acquisition and persistence seam for the frozen V7 runtime."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.heroes.taxonomy import load_default_taxonomy
from app.player_analysis_v7.acquisition_policy import FULL_DEPTH_MATCHES, MATCHES_PER_REQUEST, plan
from app.player_analysis_v7.context_projection import load_context_projection
from app.player_analysis_v7.lifecycle import V7ReportLifecycle
from app.player_analysis_v7.population import load_population_parameters
from app.player_analysis_v7.research.tables import is_product_context
from app.player_analysis_v7.runtime import RUNTIME_VERSION, analyze_v7
from app.stratz.queries import GET_DEEP_MATCH_BATCH

DEEP_CACHE_ENDPOINT = "/v7/stratz/deep-matches"


def _hero_metadata() -> dict[int, dict[str, object]]:
    return {
        hero_id: {"display_name": hero.name}
        for hero_id, hero in load_default_taxonomy().heroes.items()
    }


def runtime_versions() -> dict[str, str]:
    projection = load_context_projection()
    population = load_population_parameters()
    return {
        "analytical_lineage": population.analytical_lineage_id,
        "context_projection": projection.artifact_sha256,
        "population_parameters": population.artifact_sha256,
        "analytical_runtime": RUNTIME_VERSION,
        "deep_operation": f"{GET_DEEP_MATCH_BATCH.name}:{GET_DEEP_MATCH_BATCH.version}",
    }


class V7RuntimeService:
    """Fetch canonical evidence once, apply frozen analytics, and persist."""

    def __init__(
        self,
        provider: Any,
        repository: Any,
        *,
        hero_metadata: Mapping[int, Mapping[str, object]] | None = None,
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.hero_metadata = _hero_metadata() if hero_metadata is None else hero_metadata
        self.lifecycle = V7ReportLifecycle(repository, versions=runtime_versions())

    async def generate(
        self,
        account_id: int,
        canonical_player: str,
        *,
        generated_at: str | None = None,
    ) -> tuple[Any, bool]:
        job, reused = self.lifecycle.locate_or_start(account_id, canonical_player)
        if reused:
            return job, True
        try:
            self.repository.update_job(
                job, stage="acquiring_history", status="running", message="Acquiring V7 history"
            )
            history = await self.provider.fetch_history(account_id)
            candidate_ids = [
                match.match_id
                for match in sorted(
                    history.matches, key=lambda item: item.started_at or 0, reverse=True
                )
                if match.is_parsed
                and is_product_context(
                    {
                        "game_mode_native": match.game_mode_native,
                        "lobby_type_native": match.lobby_native,
                        "leaver_status_native": match.leaver_status_native,
                    }
                )
            ]
            cached = self.repository.get_cached_raw_payload(
                DEEP_CACHE_ENDPOINT, str(account_id)
            )
            existing = {
                int(row["match_id"]): dict(row)
                for row in cached or []
                if isinstance(row, Mapping) and row.get("match_id") is not None
            }
            acquisition = plan(str(account_id), candidate_ids, existing)
            for offset in range(0, len(acquisition.match_ids_to_fetch), MATCHES_PER_REQUEST):
                batch = acquisition.match_ids_to_fetch[offset : offset + MATCHES_PER_REQUEST]
                for row in await self.provider.fetch_deep_matches(account_id, batch):
                    existing[int(row["match_id"])] = row
            considered = candidate_ids[:FULL_DEPTH_MATCHES]
            deep_rows = [existing[match_id] for match_id in considered if match_id in existing]
            self.repository.persist_raw_payload(
                DEEP_CACHE_ENDPOINT,
                str(account_id),
                list(existing.values()),
                metadata={
                    "operation": GET_DEEP_MATCH_BATCH.name,
                    "operation_version": GET_DEEP_MATCH_BATCH.version,
                    "provider": self.provider.provider,
                },
            )
            self.repository.update_job(
                job,
                stage="analysing",
                message=f"Applying frozen V7 lineage to {len(deep_rows)} deep matches",
            )
            job.processed_matches = len(history.matches)
            job.eligible_matches = len(considered)
            payload = analyze_v7(
                history=history,
                deep_rows=deep_rows,
                hero_metadata=self.hero_metadata,
                generated_at=generated_at or datetime.now(UTC).isoformat(),
            )
            self.lifecycle.complete(job, payload)
            return job, False
        except Exception as exc:
            self.repository.fail_job(job, type(exc).__name__, str(exc))
            raise


__all__ = ["DEEP_CACHE_ENDPOINT", "V7RuntimeService", "runtime_versions"]
