"""Parity check: the legacy V7 corpus re-export of ``forbidden_fields_in`` must
stay identical to the shared ``app.stratz.field_policy`` implementation the
fresh STRATZ path (``app.stratz.deep``) enforces independently.
"""
from __future__ import annotations

from app.stratz.field_policy import FORBIDDEN_FIELD_TOKENS, forbidden_fields_in
from report_card.player_analysis_v7.research.corpus import (
    FORBIDDEN_FIELD_TOKENS as CORPUS_FORBIDDEN_FIELD_TOKENS,
)
from report_card.player_analysis_v7.research.corpus import (
    forbidden_fields_in as corpus_forbidden_fields_in,
)


def test_corpus_reexport_is_the_same_object():
    assert corpus_forbidden_fields_in is forbidden_fields_in
    assert CORPUS_FORBIDDEN_FIELD_TOKENS is FORBIDDEN_FIELD_TOKENS


def test_corpus_reexport_matches_behavior_on_sample_inputs():
    samples = [
        {"rank_tier": 70, "matchId": 1},
        {"nested": {"predictedWinner": True, "safe_field": 1}},
        [{"mmrEstimate": 4000}, {"heroId": 1}],
        {"no_forbidden_fields_here": 1},
        {},
    ]
    for sample in samples:
        assert corpus_forbidden_fields_in(sample) == forbidden_fields_in(sample)
