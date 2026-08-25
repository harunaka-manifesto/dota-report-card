from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.ingestion.summary_history_contract import (
    normalize_canonical_summary_history,
    request_manifest,
)
from app.player_analysis_v61.calibration_corpus import (
    CANONICAL_SCHEMA_VERSION,
    CanonicalCorpusError,
    canonical_history,
    validate_canonical_corpus,
)
from app.player_analysis_v61.calibration_evaluation import validate_runtime_parity
from app.player_analysis_v61.corpus_reuse import audit_reuse
from app.player_analysis_v61.versions import MODEL_VERSION, REPORT_VERSION

from scripts.collect_v61_calibration_histories import collect_profile
from scripts.evaluate_v61_calibration import _runtime_parity
from scripts.v61_calibration_builder import (
    build_summary_prior,
    profile_digest,
    split_from_manifest,
)

WINDOW_START = 1_700_000_000
WINDOW_END = WINDOW_START + 365 * 24 * 60 * 60
PROFILE_ID = "a" * 64


def _source_row(index: int, *, leaver_status: int | None = 0) -> dict[str, object]:
    row: dict[str, object] = {
        "match_id": 10_000 + index,
        "player_slot": 0,
        "radiant_win": True,
        "duration": 1_800,
        "game_mode": 1,
        "lobby_type": 0,
        "hero_id": 1 + index % 4,
        "start_time": WINDOW_START + index * 1_800,
        "version": "7.39",
        "kills": index % 8,
        "deaths": 1 + index % 4,
        "assists": 4 + index % 7,
        "party_size": 1,
        "lane_role": 1,
    }
    if leaver_status is not None:
        row["leaver_status"] = leaver_status
    return row


def _canonical_payload() -> dict[str, object]:
    raw = [_source_row(index) for index in range(30)]
    audit = normalize_canonical_summary_history(raw, account_id=1).audit.as_dict()
    analytical = [
        {
            "match_id": row["match_id"],
            "start_time": row["start_time"],
            "duration_seconds": row["duration"],
            "won": True,
            "hero_id": row["hero_id"],
            "kills": row["kills"],
            "deaths": row["deaths"],
            "assists": row["assists"],
            "leaver_status": row["leaver_status"],
            "game_mode": row["game_mode"],
            "lobby_type": row["lobby_type"],
            "player_slot": row["player_slot"],
            "radiant_win": row["radiant_win"],
            "source_version": row["version"],
            "lane_role": row["lane_role"],
        }
        for row in raw
    ]
    history = canonical_history(
        analytical,
        account_id=1,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
    )
    for row, match in zip(analytical, history.normalization.matches, strict=True):
        row.update(
            {
                "session_id": match.session_id,
                "session_index": match.session_index,
                "session_corrupt": match.session_corrupt,
            }
        )
    return {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "generated_at": "2000-01-01T00:00:00+00:00",
        "request_manifest": request_manifest(),
        "source": {
            "endpoint": "/players/{account_id}/matches",
            "request_count_per_profile": 1,
            "detail_requests": 0,
            "parse_requests": 0,
            "rank_or_mmr_used": False,
            "retry_limit": 0,
        },
        "window": {"days": 365, "start_time": WINDOW_START, "end_time": WINDOW_END},
        "profile_count": 1,
        "summary": {"profile_count": 1, "eligible_profile_count": 1, "eligible_match_count": 30},
        "raw_identifiers_present": False,
        "profiles": [
            {
                "profile_id": PROFILE_ID,
                "status": "eligible",
                "eligible_match_count": 30,
                "session_count": 1,
                "completed_session_count": 1,
                "history_audit": audit,
                "eligibility_audit": {
                    "excluded_match_count": 0,
                    "exclusion_reasons": {},
                    "duplicate_conflict_count": 0,
                    "minimum_usable_matches": 30,
                },
                "matches": analytical,
            }
        ],
    }


def test_canonical_validator_accepts_valid_synthetic_corpus() -> None:
    corpus = validate_canonical_corpus(_canonical_payload(), checksum="synthetic")

    assert corpus.profile_ids == (PROFILE_ID,)
    assert corpus.matches[0]["match_id"] == 10_000
    assert corpus.aggregate_diagnostics()["raw_identifiers_present"] is False


@pytest.mark.parametrize("leaver_status", [None, 99])
def test_missing_or_invalid_leaver_status_is_excluded_not_zero(leaver_status: int | None) -> None:
    rows = [_source_row(index) for index in range(31)]
    rows[0].pop("leaver_status", None) if leaver_status is None else rows[0].update(leaver_status=leaver_status)

    class Source:
        calls = 0

        async def get_summary_history_once(self, account_id: int, **kwargs: object) -> list[dict[str, object]]:
            self.calls += 1
            return rows

    source = Source()
    profile = asyncio.run(
        collect_profile(
            source,
            42,
            salt=b"x" * 32,
            window_start=WINDOW_START,
            window_end=WINDOW_END,
        )
    )

    assert source.calls == 1
    assert len(profile["matches"]) == 30
    assert all(row["leaver_status"] in {0, 1} for row in profile["matches"])
    assert profile["eligibility_audit"]["exclusion_reasons"][
        "missing_leaver_status" if leaver_status is None else "invalid_leaver_status"
    ] == 1


def test_canonical_validator_rejects_old_compact_schema() -> None:
    old = {"schema_version": "v6-calibration-corpus-1.0.0", "matches": []}
    with pytest.raises(CanonicalCorpusError, match="canonical corpus schema"):
        validate_canonical_corpus(old)


def test_canonical_validator_rejects_missing_required_evidence() -> None:
    payload = _canonical_payload()
    del payload["profiles"][0]["matches"][0]["leaver_status"]

    with pytest.raises(CanonicalCorpusError, match="leaver_status"):
        validate_canonical_corpus(payload)


def test_materialized_corpus_has_match_ids_but_no_account_ids() -> None:
    payload = _canonical_payload()
    encoded = json.dumps(payload["profiles"])
    assert "account_id" not in encoded
    assert "match_id" in encoded
    assert "leaver_status" in encoded


def test_split_binding_uses_actual_corpus_checksum_and_exact_population() -> None:
    rows = [{"profile_id": f"profile-{index}"} for index in range(1_130)]
    train = [row["profile_id"] for row in rows[:791]]
    holdout = [row["profile_id"] for row in rows[791:]]
    manifest = {
        "seed": 6000,
        "corpus_sha256": "actual-corpus",
        "train_profile_ids": train,
        "holdout_profile_ids": holdout,
        "train_digest": profile_digest(train),
        "holdout_digest": profile_digest(holdout),
    }

    assert split_from_manifest(rows, manifest, corpus_sha256="actual-corpus") == (
        set(train),
        set(holdout),
    )
    with pytest.raises(ValueError, match="actual canonical corpus checksum"):
        split_from_manifest(rows, manifest, corpus_sha256="different-corpus")
    with pytest.raises(ValueError, match="player-exclusive"):
        split_from_manifest(rows[:-1], manifest, corpus_sha256="actual-corpus")


def test_canonical_audit_uses_actual_checksum_and_reports_leaver_counts(tmp_path: Path) -> None:
    corpus_path = tmp_path / "canonical.json"
    corpus_path.write_text(json.dumps(_canonical_payload()), encoding="utf-8")
    corpus_sha = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    split_path = tmp_path / "split.json"
    split_path.write_text(
        json.dumps(
            {
                "seed": 6000,
                "corpus_sha256": corpus_sha,
                "train_profile_ids": [PROFILE_ID],
                "holdout_profile_ids": [],
                "train_digest": profile_digest([PROFILE_ID]),
                "holdout_digest": profile_digest([]),
            }
        ),
        encoding="utf-8",
    )

    audit = audit_reuse(corpus_path, split_path, authorization_reference="synthetic")

    assert audit["corpus_sha256"] == corpus_sha
    assert "expected_corpus_sha256" not in audit
    assert audit["leaver_status"]["included_valid_count"] == 30
    assert audit["aggregate_identifier_free"] is True
    assert audit["core_passed"] is False


def test_builders_filter_holdout_rows_before_fitting_prior() -> None:
    rows = [
        {"profile_id": "train", "kills": 2, "assists": 2},
        {"profile_id": "holdout", "kills": 200, "assists": 200},
    ]

    prior = build_summary_prior(rows, {"train"}, corpus_sha256="corpus")

    assert prior["finishing_beta_binomial"]["training_observations"] == 4
    assert prior["finishing_beta_binomial"]["training_successes"] == 2


def _valid_runtime_parity() -> dict[str, object]:
    return {
        "passed": True,
        "source": {"repository_commit": "release", "dirty_worktree": False},
        "corpus": {
            "schema_version": CANONICAL_SCHEMA_VERSION,
            "sha256": "corpus",
            "split_manifest_checksum": "split",
        },
        "artifact_checksums": {"artifact": "sha"},
        "versions": {
            "model": MODEL_VERSION,
            "model_version": MODEL_VERSION,
            "report_schema_version": REPORT_VERSION,
        },
        "assertions": {
            "canonical_one_request": True,
            "fixture_components_in_production": False,
            "full_recomputation": True,
            "family_branch_evidence_complete": True,
            "report_assembly_completed": True,
        },
    }


@pytest.mark.parametrize(
    ("expected", "kwargs"),
    [
        ("artifact checksum mismatch", {"artifact_checksums": {"artifact": "different"}}),
        ("corpus mismatch", {"corpus_sha256": "different"}),
        ("split manifest mismatch", {"split_manifest_checksum": "different"}),
        ("source revision mismatch", {"source_revision": "different"}),
        ("worktree state mismatch", {"dirty_worktree": True}),
    ],
)
def test_runtime_parity_fails_closed_on_binding_mismatch(
    expected: str, kwargs: dict[str, object]
) -> None:
    with pytest.raises(ValueError, match=expected):
        validate_runtime_parity(_valid_runtime_parity(), **kwargs)


def test_runtime_parity_consumes_canonical_corpus_directly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    corpus_path = tmp_path / "canonical.json"
    corpus_path.write_text(json.dumps(_canonical_payload()), encoding="utf-8")
    corpus_sha = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    split_path = tmp_path / "split.json"
    split_path.write_text(
        json.dumps(
            {
                "seed": 6000,
                "corpus_sha256": corpus_sha,
                "train_profile_ids": [PROFILE_ID],
                "holdout_profile_ids": [],
                "train_digest": profile_digest([PROFILE_ID]),
                "holdout_digest": profile_digest([]),
            }
        ),
        encoding="utf-8",
    )
    bundle = SimpleNamespace(
        manifest={"code_fingerprint": "fingerprint"},
        baseline=SimpleNamespace(resolver=lambda: object()),
        thresholds=SimpleNamespace(metrics={}),
        checksums={"artifact": "sha"},
        summary_prior={},
        distance_calibration={},
        session_reliability={},
        semantic_calibration={},
    )

    def load_bundle(_path: Path, *, expected_corpus_sha256: str, expected_split_checksum: str) -> object:
        assert expected_corpus_sha256 == corpus_sha
        assert expected_split_checksum
        return bundle

    monkeypatch.setattr("scripts.evaluate_v61_calibration.load_v61_artifact_bundle", load_bundle)
    monkeypatch.setattr(
        "scripts.evaluate_v61_calibration.assemble_free_dna_report_v61",
        lambda **_kwargs: {
            "schema_version": "free-dna-report-6.1.0",
            "versions": {"model": MODEL_VERSION},
            "selection_audit": {"complete": True},
        },
    )
    monkeypatch.setattr("scripts.evaluate_v61_calibration._revision", lambda: ("release", False))
    output = tmp_path / "runtime-parity.json"

    _runtime_parity(
        SimpleNamespace(
            input=corpus_path,
            split_manifest=split_path,
            artifact_dir=tmp_path,
            output=output,
        )
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["corpus"]["schema_version"] == CANONICAL_SCHEMA_VERSION
    assert result["assertions"]["canonical_one_request"] is True
    assert result["assertions"]["fixture_components_in_production"] is False
