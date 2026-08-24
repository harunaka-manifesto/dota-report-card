from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.analysis.budget import CostPolicy, DataCostLedger
from app.analysis.deep_scan import acquire_selected_matches, evaluate_deep_hypotheses
from app.analysis.service import AnalysisService
from app.core.config import Settings
from app.features.summary_calculators import calculate_summary_features
from app.hypotheses.models import Hypothesis, MatchPredicate
from app.selection.models import CandidateMatch, SelectedMatch, SelectionPlan
from app.storage.repository import InMemoryRepository


class TrackingSource:
    def __init__(self, history: list[dict[str, Any]], details: dict[int, dict[str, Any]]) -> None:
        self.history = history
        self.details = details
        self.requests: list[tuple[str, int]] = []

    async def get_player(self, account_id: int) -> dict[str, Any]:
        self.requests.append(("player", account_id))
        return {"profile": {"account_id": account_id, "personaname": "Tracked player"}}

    async def get_matches(self, account_id: int, *, limit: int = 200) -> list[dict[str, Any]]:
        self.requests.append(("matches", account_id))
        return self.history[:limit]

    async def get_match(self, match_id: int) -> dict[str, Any]:
        self.requests.append(("match", match_id))
        return self.details[match_id]


class ParseTrackingSource(TrackingSource):
    def __init__(self, history: list[dict[str, Any]], details: dict[int, dict[str, Any]]) -> None:
        super().__init__(history, details)
        self.parse_requests: list[int] = []
        self.parse_status_requests: list[str] = []

    async def request_parse(self, match_id: int) -> dict[str, Any]:
        self.parse_requests.append(match_id)
        return {"job": "parse-job-1", "match": {"objectives": [{"type": "tower"}]}}

    async def get_parse_request(self, job_id: str) -> dict[str, Any]:
        self.parse_status_requests.append(job_id)
        return {"job": job_id, "status": "done"}


def _summary(match_id: int, hero_id: int, won: bool) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "start_time": 1_700_000_000 + match_id * 3_600,
        "duration": 1_800,
        "game_mode": 1,
        "lobby_type": 7,
        "radiant_win": won,
        "player_slot": 0,
        "hero_id": hero_id,
        "lane_role": 3,
        "rank_tier": 45,
        "leaver_status": 0,
    }


def _detail(summary: dict[str, Any], account_id: int = 42) -> dict[str, Any]:
    return {
        **summary,
        "players": [
            {
                "account_id": account_id,
                "player_slot": summary["player_slot"],
                "hero_id": summary["hero_id"],
                "lane_role": summary["lane_role"],
                "rank_tier": 45,
                "kills": 8 if summary["radiant_win"] else 2,
                "deaths": 2 if summary["radiant_win"] else 8,
                "assists": 12,
                "last_hits": 200,
                "denies": 10,
                "gold_per_min": 500,
                "xp_per_min": 600,
                "net_worth": 15000,
                "gold_spent": 14000,
                "hero_damage": 20000,
                "tower_damage": 1500,
                "hero_healing": 0,
                "obs_placed": 0,
                "sen_placed": 0,
                "party_size": 1,
                "item_0": 1,
                "item_1": 0,
                "item_2": 0,
                "item_3": 0,
                "item_4": 0,
                "item_5": 0,
                "leaver_status": 0,
            }
        ],
    }


async def test_deep_scan_hydrates_only_global_selection() -> None:
    history = [_summary(index, 1 if index <= 10 else 2, index <= 9) for index in range(1, 21)]
    details = {item["match_id"]: _detail(item) for item in history}
    source = TrackingSource(history, details)
    service = AnalysisService(
        source,
        settings=Settings(max_deep_matches=5, max_data_cost_per_report=5),
    )
    job = service.repository.create_job(
        42,
        "https://www.opendota.com/players/42",
        service._compatibility_model_version("deep_scan"),
        "deep_scan",
        parent_report_id="test-parent",
        diagnostic_question_id="test-question",
        entitlement_decision={
            "allowed": True,
            "grant_id": "test-grant",
            "report_id": "test-parent",
            "account_id": 42,
            "diagnostic_question_id": "test-question",
            "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
        },
    )
    await service.run_job(job)

    deep_reads = [request for request in source.requests if request[0] == "match"]
    report = service.repository.get_report(job.report_id or "")
    assert job.status == "completed"
    assert 0 < len(deep_reads) <= 5
    assert report is not None
    assert report["cost"]["detail_requests"] == len(deep_reads)
    assert report["telemetry"]["candidate_matches"] >= len(deep_reads)


def _parse_plan(*, parse_marginal_gain: float) -> SelectionPlan:
    summary = _summary(1, 1, True)
    feature = calculate_summary_features([summary], account_id=42).matches[0]
    candidate = CandidateMatch(
        match_id=1,
        feature=feature,
        hypothesis_ids=("hypothesis-1",),
        evidence_roles={"hypothesis-1": "positive"},
        relevance=1.0,
        contrast_value=1.0,
        comparability=1.0,
        extremeness=1.0,
        available_families=feature.summary_families,
        metadata={
            "parse_required_families": ["events"],
            "parse_marginal_gain": parse_marginal_gain,
        },
    )
    selected = SelectedMatch(
        candidate=candidate,
        selection_order=1,
        score=parse_marginal_gain,
        marginal_gain=parse_marginal_gain,
        newly_supported_needs=(("hypothesis-1", "positive"),),
        reason="requires replay evidence",
        parse_required=True,
    )
    return SelectionPlan(
        candidates=(candidate,),
        selected=(selected,),
        needs=(),
        stopping_reason="test_fixture",
    )


async def test_deep_scan_requests_parse_only_after_detail_clears_gain_gate() -> None:
    summary = _summary(1, 1, True)
    source = ParseTrackingSource([summary], {1: _detail(summary)})
    repository = InMemoryRepository()
    ledger = DataCostLedger()

    normalized = await acquire_selected_matches(
        _parse_plan(parse_marginal_gain=0.20),
        source=source,
        repository=repository,
        account_id=42,
        ledger=ledger,
        policy=CostPolicy(),
    )

    assert len(normalized) == 1
    assert source.parse_requests == [1]
    assert source.parse_status_requests == ["parse-job-1"]
    assert ledger.parse_requests == 1
    assert ledger.parse_status_requests == 1


async def test_deep_scan_skips_parse_below_marginal_gain_floor() -> None:
    summary = _summary(1, 1, True)
    source = ParseTrackingSource([summary], {1: _detail(summary)})
    repository = InMemoryRepository()
    ledger = DataCostLedger()

    normalized = await acquire_selected_matches(
        _parse_plan(parse_marginal_gain=0.05),
        source=source,
        repository=repository,
        account_id=42,
        ledger=ledger,
        policy=CostPolicy(),
    )

    assert len(normalized) == 1
    assert source.parse_requests == []
    assert ledger.parse_requests == 0
    assert any(event["operation"] == "parse_skipped" for event in ledger.events)


async def test_cached_parsed_evidence_prevents_detail_and_parse_calls() -> None:
    summary = _summary(1, 1, True)
    source = ParseTrackingSource([summary], {1: _detail(summary)})
    repository = InMemoryRepository()
    repository.persist_raw_payload("/matches/1", "1", _detail(summary))
    repository.persist_raw_payload(
        "/matches/1/parse",
        "1",
        {"match": {"objectives": [{"type": "tower"}]}},
    )
    ledger = DataCostLedger()

    normalized = await acquire_selected_matches(
        _parse_plan(parse_marginal_gain=0.20),
        source=source,
        repository=repository,
        account_id=42,
        ledger=ledger,
        policy=CostPolicy(),
    )

    assert len(normalized) == 1
    assert source.requests == []
    assert source.parse_requests == []
    assert ledger.detail_requests == 0
    assert ledger.parse_requests == 0


def test_summary_only_selected_evidence_is_evaluated_without_hydration() -> None:
    summaries = [_summary(index, index, index == 1) for index in range(1, 4)]
    features = calculate_summary_features(summaries, account_id=42).matches
    hypothesis = Hypothesis(
        hypothesis_id="summary-only",
        source_pattern_id="summary-only",
        statement="Summary evidence can resolve this diagnostic.",
        explanation_type="outcome_difference",
        priority=1.0,
        pattern_strength=1.0,
        actionability=1.0,
        required_data_families=("summary",),
        positive_definition=MatchPredicate("match_id_set", {"match_ids": [1]}),
        negative_definition=MatchPredicate("match_id_set", {"match_ids": [2]}),
        control_definition=MatchPredicate("match_id_set", {"match_ids": [3]}),
        min_positive=1,
        min_negative=1,
        min_control=1,
        target_positive=1,
        target_negative=1,
        target_control=1,
        confounders_to_control=(),
    )
    roles = ("positive", "negative", "control")
    candidates = tuple(
        CandidateMatch(
            match_id=feature.match_id,
            feature=feature,
            hypothesis_ids=(hypothesis.hypothesis_id,),
            evidence_roles={hypothesis.hypothesis_id: role},
            relevance=1.0,
            contrast_value=1.0,
            comparability=1.0,
            extremeness=1.0,
            available_families=feature.summary_families,
            already_available=True,
            estimated_detail_cost=0.0,
        )
        for feature, role in zip(features, roles, strict=True)
    )
    plan = SelectionPlan(
        candidates=candidates,
        selected=tuple(
            SelectedMatch(candidate, index, 1.0, 1.0, ((hypothesis.hypothesis_id, role),), "cached")
            for index, (candidate, role) in enumerate(zip(candidates, roles, strict=True), start=1)
        ),
        needs=(),
        stopping_reason="requirements_satisfied",
    )

    finding = evaluate_deep_hypotheses((hypothesis,), plan, features)[0]

    assert finding.status == "moderate"
    assert finding.evidence["data_quality"] == 1.0
    assert finding.abstention_reason is None
