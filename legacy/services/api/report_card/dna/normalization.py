"""Public Free DNA normalization contract.

The implementation lives beside the ingestion adapters so the legacy summary
feature calculator can remain compatible. This module is the stable import
surface for DNA callers and tests.
"""

from app.ingestion.summary_normalize import (
    EligibilityFlag,
    EligibilityKey,
    NormalizationResult,
    NormalizedSummaryMatch,
    normalize_summary_rows,
)

__all__ = [
    "EligibilityFlag",
    "EligibilityKey",
    "NormalizationResult",
    "NormalizedSummaryMatch",
    "normalize_summary_rows",
]
