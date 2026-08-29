import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from app.analysis.service import AnalysisService
from app.core.config import MATCH_HISTORY_LIMIT, Settings
from app.features.calculators import calculate_match_feature
from app.ingestion.normalize import normalize_match
from app.opendota.cache import MemoryCache
from app.storage.repository import InMemoryRepository


class EmptySource:
    def __init__(self) -> None:
        self.history_limits: list[int] = []

    async def get_player(self, account_id: int) -> dict[str, object]:
        return {"profile": {"account_id": account_id}}

    async def get_matches(self, account_id: int, *, limit: int = MATCH_HISTORY_LIMIT) -> list[dict[str, object]]:
        self.history_limits.append(limit)
        return []

    async def get_match(self, match_id: int) -> dict[str, object]:
        return {"match_id": match_id}


def test_analysis_history_limit_uses_configured_summary_cap() -> None:
    source = EmptySource()
    service = AnalysisService(source, settings=Settings(history_limit=200))
    job, _ = asyncio.run(service.create_analysis("193875165", enqueue=False))
    asyncio.run(service.run_job(job))
    assert source.history_limits == [200]


def test_inflight_jobs_are_atomically_reused() -> None:
    repository = InMemoryRepository()
    first, reused = repository.get_or_create_inflight_job(1, "player", "model")
    second, reused_again = repository.get_or_create_inflight_job(1, "player", "model")
    assert not reused
    assert reused_again
    assert second.job_id == first.job_id


def test_free_compatibility_fingerprint_includes_v4_versions(monkeypatch) -> None:
    service = AnalysisService(EmptySource(), settings=Settings())
    baseline = service._compatibility_model_version("free")
    version_targets = (
        "app.dna.sessions.SESSION_VERSION",
        "app.dna.features.models.FEATURE_VERSION",
        "app.dna.pipeline.DNA_SCORING_VERSION",
        "app.heroes.taxonomy.TAXONOMY_VERSION",
        "app.reports.dna_assembly.REPORT_SCHEMA_VERSION",
        "app.reports.dna_assembly.REPORT_STORY_VERSION",
        "app.hero_portfolio.version.HERO_PORTFOLIO_VERSION",
        "app.hero_portfolio.version.HERO_MIRROR_VERSION",
        "app.hero_portfolio.version.HERO_RELATIONSHIPS_VERSION",
        "app.hero_portfolio.version.HERO_EXPRESSIONS_VERSION",
        "app.hero_portfolio.version.HERO_RELIABILITY_VERSION",
        "app.hero_portfolio.version.HERO_MATCHUPS_VERSION",
        "app.hero_portfolio.version.HERO_SYNERGIES_VERSION",
        "app.hero_portfolio.version.HERO_SITUATIONS_VERSION",
        "app.hero_portfolio.version.PATTERN_ACTIONS_VERSION",
        "app.hero_portfolio.config.PORTFOLIO_CONFIG_VERSION",
        "app.share.service.RENDERER_VERSION",
    )
    for target in version_targets:
        with monkeypatch.context() as context:
            module_path, attribute = target.rsplit(".", 1)
            context.setattr(f"{module_path}.{attribute}", "qa-mutated-version")
            assert service._compatibility_model_version("free") != baseline


def test_v61_story_versions_invalidate_compatibility_fingerprint(monkeypatch) -> None:
    """Every story extension surface participates in cache compatibility."""

    from app.player_analysis_v61 import versions as versions_module

    # V6.1 construction requires release artifacts, but the compatibility
    # calculation itself only needs the settings and artifact checksum map.
    service = AnalysisService.__new__(AnalysisService)
    service.settings = Settings(free_dna_v61_enabled=True)
    service.v61_artifact_checksums = {}

    expected = {
        "story_payload": versions_module.STORY_PAYLOAD_VERSION,
        "story_rules": versions_module.STORY_RULES_VERSION,
        "story_copy": versions_module.STORY_COPY_VERSION,
        "game_mode_map": versions_module.STORY_MODE_MAP_VERSION,
        "hero_taxonomy": versions_module.STORY_HERO_TAXONOMY_VERSION,
        "hero_metadata": versions_module.STORY_HERO_METADATA_VERSION,
        "archetype_contract": versions_module.STORY_ARCHETYPE_CONTRACT_VERSION,
    }
    defaults = versions_module.default_versions_v61()
    assert {key: defaults[key] for key in expected} == expected

    baseline = service._compatibility_model_version("free")
    for key in expected:
        with monkeypatch.context() as context:
            surfaces = tuple(
                replace(surface, version="qa-mutated-story-version")
                if surface.key == key
                else surface
                for surface in versions_module.VERSION_SURFACES
            )
            context.setattr(versions_module, "VERSION_SURFACES", surfaces)
            assert service._compatibility_model_version("free") != baseline


def test_cache_ttl_expires_even_when_marked_immutable() -> None:
    now = [datetime(2026, 1, 1, tzinfo=UTC)]
    cache = MemoryCache(clock=lambda: now[0])
    cache.set("hero_stats", [1], ttl_seconds=60, immutable=True)
    assert cache.get("hero_stats") == [1]
    now[0] += timedelta(seconds=61)
    assert cache.get("hero_stats") is None


def test_death_events_drive_early_death_feature() -> None:
    detail = {
        "match_id": 1,
        "duration": 1800,
        "radiant_win": True,
        "game_mode": 1,
        "lobby_type": 7,
        "players": [{
            "account_id": 42,
            "player_slot": 0,
            "hero_id": 1,
            "lane_role": 2,
            "rank_tier": 45,
            "deaths": 2,
            "death_log": [{"time": 500}, {"time": 700}],
        }],
    }
    normalized = normalize_match(detail, account_id=42)
    events = [event for event in normalized.target_participant.events if event.event_type == "death"]
    feature = calculate_match_feature(normalized)
    assert [event.time_seconds for event in events] == [500, 700]
    assert feature.derived["death_events"] == 2
    assert feature.derived["early_death"] == 1
