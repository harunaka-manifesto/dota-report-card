from __future__ import annotations

import asyncio
import json
import stat
from pathlib import Path

import pytest

from scripts import prepare_v61_replacement_holdout as precommit
from scripts import scan_v61_replacement_holdout as scanner

RELEASE_SHA = "a" * 40
SALT = b"scan-test-salt-012345678901234567890"


def _write_json(path: Path, payload: object, *, private: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if private:
        path.chmod(0o600)
        path.parent.chmod(0o700)


def _write_inputs(tmp_path: Path, account_ids: list[int]) -> dict[str, Path]:
    precommit_path = tmp_path / "inputs" / "precommit.json"
    salt_path = tmp_path / "inputs" / "salt.bin"
    contract = scanner._expected_collection_contract()
    contract["planned_summary_requests"] = len(account_ids)
    _write_json(
        precommit_path,
        {
            "schema_version": precommit.SCHEMA_VERSION,
            "release_sha": RELEASE_SHA,
            "candidate_count": len(account_ids),
            "candidate_order_digest_format": precommit.ORDER_DIGEST_FORMAT,
            "candidate_order_sha256": scanner._order_digest(account_ids),
            "candidate_account_ids": account_ids,
            "exclusions": {"current_population_overlap_count": 0},
            "collection_contract": contract,
        },
    )
    salt_path.write_bytes(SALT)
    salt_path.chmod(0o600)
    salt_path.parent.chmod(0o700)
    return {"precommit": precommit_path, "salt": salt_path}


class _Source:
    def __init__(self, *, failures: set[int] | None = None) -> None:
        self.failures = failures or set()
        self.calls: list[int] = []

    async def get_summary_history_once(
        self,
        account_id: int,
        *,
        days: int,
        project: tuple[str, ...],
        provider_limit: int,
    ) -> list[dict[str, object]]:
        self.calls.append(account_id)
        assert days == 365
        assert project == tuple(scanner.request_manifest()["projection"])
        assert provider_limit == 10_000
        if account_id in self.failures:
            raise RuntimeError(f"account {account_id} failed")
        return [
            {
                "match_id": account_id * 100,
                "player_slot": 0,
                "radiant_win": True,
                "duration": 1_800,
                "game_mode": 1,
                "lobby_type": 0,
                "hero_id": 1,
                "start_time": 1_780_000_000,
                "kills": 3,
                "deaths": 2,
                "assists": 8,
                "leaver_status": 0,
            }
        ]


class _CrashSource(_Source):
    async def get_summary_history_once(
        self,
        account_id: int,
        *,
        days: int,
        project: tuple[str, ...],
        provider_limit: int,
    ) -> list[dict[str, object]]:
        self.calls.append(account_id)
        raise KeyboardInterrupt


def _run(
    paths: dict[str, Path],
    tmp_path: Path,
    source: _Source,
    *,
    account_ids: list[int],
    release_sha: str = RELEASE_SHA,
    now: int = 1_800_000_000,
    progress: bool = False,
) -> dict[str, object]:
    return asyncio.run(
        scanner.run_scan(
            precommit_manifest=paths["precommit"],
            salt=paths["salt"],
            raw_archive_dir=tmp_path / "raw",
            state_dir=tmp_path / "state",
            output=tmp_path / "scan.json",
            release_sha=release_sha,
            client=source,
            acknowledge_network_collection=True,
            expected_candidate_count=len(account_ids),
            now=now,
            progress=progress,
        )
    )


def test_clean_run_freezes_one_window_and_resume_reuses_it(tmp_path: Path) -> None:
    account_ids = [42, 2, 17]
    paths = _write_inputs(tmp_path, account_ids)
    first_source = _Source()
    first = _run(paths, tmp_path, first_source, account_ids=account_ids)

    assert first["window"] == {
        "days": 365,
        "start_time": 1_768_464_000,
        "end_time": 1_800_000_000,
    }
    assert first_source.calls == account_ids

    second_source = _Source(failures=set(account_ids))
    second = _run(
        paths,
        tmp_path,
        second_source,
        account_ids=account_ids,
        now=1_900_000_000,
    )
    assert second["window"] == first["window"]
    assert second["success_count"] == 3
    assert second_source.calls == []


def test_success_is_never_requested_twice(tmp_path: Path) -> None:
    account_ids = [3, 1]
    paths = _write_inputs(tmp_path, account_ids)
    source = _Source()
    _run(paths, tmp_path, source, account_ids=account_ids)
    again = _Source(failures=set(account_ids))

    _run(paths, tmp_path, again, account_ids=account_ids)

    assert source.calls == account_ids
    assert again.calls == []


def test_failed_candidate_is_terminal_and_does_not_retry(tmp_path: Path) -> None:
    account_ids = [8, 4, 6]
    paths = _write_inputs(tmp_path, account_ids)
    first_source = _Source(failures={4})
    first = _run(paths, tmp_path, first_source, account_ids=account_ids)

    assert first["failure_count"] == 1
    failure_state = tmp_path / "state" / "candidates" / (
        f"{precommit._pseudonym(4, SALT)}.json"
    )
    failure_payload = json.loads(failure_state.read_text(encoding="utf-8"))
    assert failure_payload["exception_type"] == "RuntimeError"
    assert "account 4" not in json.dumps(failure_payload)

    second_source = _Source(failures=set(account_ids))
    second = _run(paths, tmp_path, second_source, account_ids=account_ids)
    assert second["failure_count"] == 1
    assert second_source.calls == []


def test_archive_existing_result_missing_recovers_without_network(tmp_path: Path) -> None:
    account_ids = [12, 5]
    paths = _write_inputs(tmp_path, account_ids)
    source = _Source()
    _run(paths, tmp_path, source, account_ids=account_ids)
    result_path = tmp_path / "state" / "results" / f"{precommit._pseudonym(12, SALT)}.json"
    result_path.unlink()

    no_network = _Source(failures=set(account_ids))
    payload = _run(paths, tmp_path, no_network, account_ids=account_ids)

    assert payload["success_count"] == 2
    assert no_network.calls == []
    assert result_path.exists()


def test_attempt_started_without_archive_becomes_indeterminate(tmp_path: Path) -> None:
    account_ids = [7, 1, 9]
    paths = _write_inputs(tmp_path, account_ids)
    with pytest.raises(KeyboardInterrupt):
        _run(paths, tmp_path, _CrashSource(), account_ids=account_ids)

    source = _Source()
    payload = _run(paths, tmp_path, source, account_ids=account_ids)

    assert payload["indeterminate_count"] == 1
    assert source.calls == account_ids[1:]
    marker = tmp_path / "state" / "candidates" / f"{precommit._pseudonym(7, SALT)}.json"
    assert json.loads(marker.read_text(encoding="utf-8"))["status"] == "indeterminate"


def test_one_failure_does_not_abort_later_candidates(tmp_path: Path) -> None:
    account_ids = [11, 13, 15]
    paths = _write_inputs(tmp_path, account_ids)
    source = _Source(failures={11})

    payload = _run(paths, tmp_path, source, account_ids=account_ids)

    assert source.calls == account_ids
    assert payload["failure_count"] == 1
    assert payload["success_count"] == 2


def test_candidate_order_is_precommit_order_not_numeric_order(tmp_path: Path) -> None:
    account_ids = [91, 3, 44]
    paths = _write_inputs(tmp_path, account_ids)
    source = _Source()

    payload = _run(paths, tmp_path, source, account_ids=account_ids)

    assert source.calls == account_ids
    assert [
        item["candidate_index"] for item in payload["candidate_statuses"]
    ] == [0, 1, 2]
    assert payload["candidate_order_sha256"] == scanner._order_digest(account_ids)


def test_precommit_manifest_sha_mismatch_blocks_resume(tmp_path: Path) -> None:
    account_ids = [20, 21]
    paths = _write_inputs(tmp_path, account_ids)
    _run(paths, tmp_path, _Source(), account_ids=account_ids)
    manifest = json.loads(paths["precommit"].read_text(encoding="utf-8"))
    manifest["unrelated_metadata"] = "changed"
    _write_json(paths["precommit"], manifest)
    no_network = _Source()

    with pytest.raises(ValueError, match="immutable scan manifest"):
        _run(paths, tmp_path, no_network, account_ids=account_ids)
    assert no_network.calls == []


def test_release_sha_mismatch_blocks_resume(tmp_path: Path) -> None:
    account_ids = [30, 31]
    paths = _write_inputs(tmp_path, account_ids)
    _run(paths, tmp_path, _Source(), account_ids=account_ids)
    no_network = _Source()

    with pytest.raises(ValueError, match="release SHA"):
        _run(
            paths,
            tmp_path,
            no_network,
            account_ids=account_ids,
            release_sha="b" * 40,
        )
    assert no_network.calls == []


def test_candidate_order_digest_mismatch_blocks_resume(tmp_path: Path) -> None:
    account_ids = [50, 52]
    paths = _write_inputs(tmp_path, account_ids)
    _run(paths, tmp_path, _Source(), account_ids=account_ids)
    scan_manifest = tmp_path / "state" / "scan-manifest.json"
    payload = json.loads(scan_manifest.read_text(encoding="utf-8"))
    payload["candidate_order_sha256"] = "0" * 64
    _write_json(scan_manifest, payload)
    no_network = _Source()

    with pytest.raises(ValueError, match="immutable scan manifest"):
        _run(paths, tmp_path, no_network, account_ids=account_ids)
    assert no_network.calls == []


def test_retry_limit_is_zero_and_request_accounting_has_no_detail_or_parse(
    tmp_path: Path,
) -> None:
    account_ids = [60, 61]
    paths = _write_inputs(tmp_path, account_ids)
    payload = _run(paths, tmp_path, _Source(), account_ids=account_ids)

    scan_manifest = json.loads(
        (tmp_path / "state" / "scan-manifest.json").read_text(encoding="utf-8")
    )
    assert scan_manifest["retry_limit"] == 0
    assert payload["request_accounting"]["retry_limit"] == 0
    assert payload["request_accounting"]["attempted_summary_requests"] == 2
    assert payload["detail_requests"] == 0
    assert payload["parse_requests"] == 0


def test_private_modes_and_progress_do_not_leak_identifiers(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    account_ids = [70, 71]
    paths = _write_inputs(tmp_path, account_ids)
    _run(paths, tmp_path, _Source(), account_ids=account_ids, progress=True)
    stdout = capsys.readouterr().out

    assert "match_id" not in stdout
    assert "processed 2/2 success 2 failed 0 indeterminate 0" in stdout
    for path in [
        tmp_path / "state",
        tmp_path / "state" / "candidates",
        tmp_path / "state" / "results",
        tmp_path / "raw",
        tmp_path / "scan.json",
    ]:
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == (0o700 if path.is_dir() else 0o600)


def test_normal_unit_path_requires_acknowledgement_without_network(tmp_path: Path) -> None:
    account_ids = [80]
    paths = _write_inputs(tmp_path, account_ids)

    with pytest.raises(RuntimeError, match="acknowledgement"):
        asyncio.run(
            scanner.run_scan(
                precommit_manifest=paths["precommit"],
                salt=paths["salt"],
                raw_archive_dir=tmp_path / "raw",
                state_dir=tmp_path / "state",
                output=tmp_path / "scan.json",
                release_sha=RELEASE_SHA,
            )
        )
    assert not (tmp_path / "state").exists()
