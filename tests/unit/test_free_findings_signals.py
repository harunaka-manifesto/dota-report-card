from __future__ import annotations

import math

from app.findings.signals import derive_signals
from free_finding_helpers import make_context


def test_signal_derivation_is_finite_and_uses_the_shared_eligible_population() -> None:
    context = make_context()
    signals = derive_signals(context)

    assert context.eligible_matches == len(context.dna.matches)
    assert context.eligible_matches == len(context.summary_features.matches)
    assert signals
    for signal in signals.values():
        if isinstance(signal.value, (int, float)):
            assert math.isfinite(float(signal.value))
        assert signal.coverage > 0
        assert not any(str(match_id) in signal.public_receipt for match_id in signal.source_match_ids)


def test_signal_receipts_do_not_expose_private_hero_ids() -> None:
    signals = derive_signals(make_context())

    for signal in signals.values():
        assert "hero_id" not in signal.public_receipt
        assert "match_id" not in signal.public_receipt
