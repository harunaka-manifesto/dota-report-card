"""V6.1 calibration projection/parity seam."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.ingestion.summary_history_contract import (
    SUMMARY_HISTORY_PROVIDER_LIMIT,
    normalize_canonical_summary_history,
)


def normalize_calibration_history(
    rows: Sequence[Mapping[str, Any]], account_id: int
) -> dict[str, Any]:
    canonical = normalize_canonical_summary_history(
        rows,
        account_id,
        request_count=1,
        provider_limit=SUMMARY_HISTORY_PROVIDER_LIMIT,
    )
    return {
        "normalized_payload_sha256": canonical.audit.normalized_payload_sha256,
        "eligibility_audit": {
            "raw_count": canonical.audit.raw_count,
            "normalized_count": canonical.audit.normalized_count,
            "eligible_count": canonical.audit.eligible_count,
            "deduplicated_count": canonical.audit.deduplicated_count,
        },
        "coverage": {
            "required": dict(canonical.audit.required_field_coverage),
            "optional": dict(canonical.audit.optional_field_coverage),
        },
        "matches": canonical.normalization.matches,
    }


__all__ = ["normalize_calibration_history"]
