from __future__ import annotations

from app.dna.pipeline import analyze_dna
from app.findings.context import build_free_finding_context, summary_features_for_free
from app.ingestion.summary_normalize import normalize_summary_rows
from app.patterns.detector import detect_patterns


def summary_row(match_id: int, index: int) -> dict[str, int | bool]:
    return {
        "match_id": match_id,
        "start_time": 1_700_000_000 + index * 7_200,
        "duration": 1_800 + (index % 4) * 600,
        "hero_id": 25 + index % 5,
        "player_slot": 0,
        "radiant_win": index % 2 == 0,
        "game_mode": 1,
        "lobby_type": 0,
        "kills": 8 + index % 4,
        "deaths": 4,
        "assists": 10,
        "lane_role": 2 if index % 2 else 1,
    }


def make_context(count: int = 35):
    rows = [summary_row(920_000_000 + index, index) for index in range(count)]
    normalized = normalize_summary_rows(rows, account_id=42)
    eligible = normalized.eligible_matches
    dna = analyze_dna(
        eligible,
        session_gap_minutes=90,
        history_tier="limited" if count < 60 else "normal",
    )
    summary_features = summary_features_for_free(eligible, session_gap_minutes=90)
    return build_free_finding_context(
        dna=dna,
        summary_features=summary_features,
        patterns=detect_patterns(summary_features),
        processed_matches=len(rows),
        eligible_matches=len(eligible),
        history_limit=60,
    )

