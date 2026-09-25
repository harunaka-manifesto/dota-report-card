from datetime import UTC, datetime

import pytest

from legacy.scripts.stratz_v7_corpus_supervisor import seconds_until


def test_seconds_until_handles_future_past_and_requires_timezone() -> None:
    now = datetime(2026, 9, 2, 6, 0, tzinfo=UTC)
    assert seconds_until("2026-09-02T07:00:00+00:00", now=now) == 3600
    assert seconds_until("2026-09-02T05:00:00+00:00", now=now) == 0
    with pytest.raises(ValueError, match="timezone"):
        seconds_until("2026-09-02T07:00:00", now=now)
