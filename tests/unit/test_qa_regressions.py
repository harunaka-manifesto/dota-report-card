import asyncio
from datetime import UTC, datetime, timedelta

from app.analysis.service import AnalysisService, _select_cohort
from app.core.config import MATCH_HISTORY_LIMIT, Settings
from app.dna.archetypes.classifier import classify
from app.dna.dimensions.adaptability import score as score_adaptability
from app.dna.dimensions.models import DimensionResult
from app.dna.features.extractor import extract_dna_features
from app.dna.sessions import infer_sessions
from app.features.calculators import calculate_match_feature
from app.ingestion.normalize import normalize_match
from app.ingestion.summary_normalize import normalize_summary_rows
from app.insights.evaluator import REPLAY_CALCULATORS
from app.insights.gates import apply_publication_gates
from app.insights.models import MetricObservation
from app.insights.registry import INSIGHT_REGISTRY
from app.opendota.cache import MemoryCache
from app.storage.repository import InMemoryRepository


class EmptySource:
    def __init__(self) -> None:
        self.history_limits: list[int] = []

    async def get_player(self, account_id: int) -> dict[str, object]:
        return {"profile": {"account_id": account_id}}

    async def get_matches(
        self, account_id: int, *, limit: int = MATCH_HISTORY_LIMIT
    ) -> list[dict[str, object]]:
        self.history_limits.append(limit)
        return []

    async def get_match(self, match_id: int) -> dict[str, object]:
        return {"match_id": match_id}


def _observation(effect: float | None, cohort_value: float | None = None) -> MetricObservation:
    return MetricObservation(
        player_value=0.5,
        cohort_value=cohort_value,
        unit="rate",
        effect=effect,
        interval=None,
        numerator=5,
        denominator=10,
        situation_count=10,
        relevant_matches=10,
        parsed_matches=10,
        source_match_ids=(1,),
        direction="positive" if effect else None,
        evidence_facts=(),
        confounders=(),
        action_behavior="review",
        measurable_target="review",
    )


def test_missing_effect_and_cohort_fail_closed() -> None:
    definition = INSIGHT_REGISTRY["adjusted_role_fit"]
    result = apply_publication_gates(
        definition,
        _observation(None),
        role_confidence=0.9,
        role_confidence_threshold=0.8,
        parse_coverage=1.0,
        holdout_survives=True,
    )
    assert not result.passed
    assert "EFFECT_UNAVAILABLE" in result.reasons
    assert "COHORT_UNAVAILABLE" in result.reasons


def test_configured_coverage_threshold_is_used_by_publication_gate() -> None:
    definition = INSIGHT_REGISTRY["specialization_hero_pool_entropy"]
    result = apply_publication_gates(
        definition,
        _observation(0.1),
        role_confidence=0.9,
        parse_coverage=0.59,
        minimum_parse_coverage=0.60,
        holdout_survives=True,
    )
    assert not result.passed
    assert "INSUFFICIENT_PARSE_COVERAGE" in result.reasons


def test_analysis_history_limit_uses_broad_summary_cap() -> None:
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


def test_free_compatibility_fingerprint_changes_with_analytical_versions(
    monkeypatch,
) -> None:
    service = AnalysisService(EmptySource(), settings=Settings())
    baseline = service._compatibility_model_version("free")
    version_targets = (
        "app.dna.sessions.SESSION_VERSION",
        "app.dna.features.models.FEATURE_VERSION",
        "app.dna.pipeline.DNA_SCORING_VERSION",
        "app.dna.baselines.BASELINE_VERSION",
        "app.dna.archetypes.classifier.CLASSIFIER_VERSION",
        "app.heroes.identity.HERO_IDENTITY_VERSION",
        "app.heroes.taxonomy.TAXONOMY_VERSION",
        "app.reports.dna_assembly.REPORT_SCHEMA_VERSION",
        "app.share.service.RENDERER_VERSION",
    )

    for target in version_targets:
        with monkeypatch.context() as context:
            context.setattr(target, "qa-mutated-version")
            assert service._compatibility_model_version("free") != baseline

    changed_settings = AnalysisService(
        EmptySource(), settings=Settings(model_version="model-v2", template_version="template-v2")
    )
    assert changed_settings._compatibility_model_version("free") != baseline


def test_cohort_uses_latest_match_by_start_time() -> None:
    features = [
        {"account_id": 1, "hero_id": 1, "role": 1, "rank_tier": 45, "patch": "old", "start_time": 10},
        {"account_id": 1, "hero_id": 2, "role": 2, "rank_tier": 45, "patch": "new", "start_time": 20},
    ]
    population = [
        {
            "account_id": index + 2,
            "hero_id": 2,
            "role": 2,
            "rank_tier": 45,
            "patch": "new",
            "won": True,
            "gold_per_min": 500,
            "xp_per_min": 500,
            "last_hits": 100,
            "tower_damage": 1000,
            "duration_seconds": 1800,
        }
        for index in range(20)
    ]
    cohort = _select_cohort(features, tuple(population))  # type: ignore[arg-type]
    assert cohort is not None
    assert cohort.valid
    assert cohort.dimensions["patch"] == "new"


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
        "players": [
            {
                "account_id": 42,
                "player_slot": 0,
                "hero_id": 1,
                "lane_role": 2,
                "rank_tier": 45,
                "deaths": 2,
                "death_log": [{"time": 500}, {"time": 700}],
            }
        ],
    }
    normalized = normalize_match(detail, account_id=42)
    events = [event for event in normalized.target_participant.events if event.event_type == "death"]
    feature = calculate_match_feature(normalized)
    assert [event.time_seconds for event in events] == [500, 700]
    assert feature.derived["death_events"] == 2
    assert feature.derived["early_death"] == 1


def test_every_replay_definition_has_an_explicit_calculator() -> None:
    replay_ids = {
        definition.id
        for definition in INSIGHT_REGISTRY.values()
        if definition.evidence_class == "replay"
    }
    assert replay_ids == set(REPLAY_CALCULATORS)


def test_adaptability_keeps_hero_outcome_evidence_when_timestamps_are_missing() -> None:
    rows = []
    for match_id in range(1, 81):
        rows.append(
            {
                "match_id": match_id,
                "start_time": None,
                "duration": 1800,
                "hero_id": 1 if match_id <= 56 else 2,
                "player_slot": 0,
                "radiant_win": match_id % 2 == 0,
                "game_mode": 1,
                "lobby_type": 7,
                "kills": 6,
                "deaths": 4,
                "assists": 10,
            }
        )
    normalized = normalize_summary_rows(rows, account_id=42)
    sessions = infer_sessions(normalized.matches)
    features = extract_dna_features(sessions.matches, sessions)

    result = score_adaptability(features)

    assert result.status in {"available", "limited"}
    assert result.sample_size >= 40
    assert any(item.key == "evaluation_method" for item in result.evidence)


def test_missing_performance_rows_do_not_create_resilience_transitions() -> None:
    rows = [
        {
            "match_id": 1,
            "start_time": 1_700_000_000,
            "duration": 1800,
            "hero_id": 1,
            "player_slot": 0,
            "radiant_win": False,
            "game_mode": 1,
            "lobby_type": 7,
        },
        {
            "match_id": 2,
            "start_time": 1_700_001_900,
            "duration": 300,
            "hero_id": 1,
            "player_slot": 0,
            "radiant_win": True,
            "game_mode": 1,
            "lobby_type": 7,
        },
        {
            "match_id": 3,
            "start_time": 1_700_003_800,
            "duration": 1800,
            "hero_id": 1,
            "player_slot": 0,
            "radiant_win": True,
            "game_mode": 1,
            "lobby_type": 7,
        },
    ]
    normalized = normalize_summary_rows(rows, account_id=42)
    sessions = infer_sessions(normalized.matches)
    features = extract_dna_features(sessions.matches, sessions, include_sensitivity=False)

    assert features.transitions_after_win == ()
    assert features.transitions_after_loss == ()


def test_archetype_prototypes_require_their_declared_evidence_groups() -> None:
    def dimension(key: str, score: float) -> DimensionResult:
        return DimensionResult(
            key=key,  # type: ignore[arg-type]
            status="available",
            score=score,
            centered_score=score * 2 - 1,
            label=None,
            confidence="high",
            confidence_score=1.0,
            sample_size=20,
            effective_sample_size=20.0,
            coverage=1.0,
        )

    dimensions = [
        dimension("breadth", 0.8),
        dimension("role", 0.8),
        dimension("activity", 0.8),
        dimension("resilience", 0.8),
    ]
    prototypes = [
        {
            "key": "partial",
            "label": "Partial",
            "expected": {"activity": 0.8},
            "weights": {"activity": 1.0},
            "groups": ["hero_identity", "combat_expression"],
        },
        {
            "key": "complete",
            "label": "Complete",
            "expected": {"breadth": 0.8, "activity": 0.8},
            "weights": {"breadth": 1.0, "activity": 1.0},
            "groups": ["hero_identity", "combat_expression"],
        },
    ]

    result = classify(dimensions, prototypes=prototypes)

    assert result.key == "complete"
