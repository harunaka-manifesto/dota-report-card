from __future__ import annotations

import json
import stat
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from scripts.serve_v6_calibration_review import (
    ReviewInputError,
    ReviewState,
    _handler,
    merge_review_state,
)


def _packet() -> dict:
    return {
        "version": "v6-private-review-packet-1.0.0",
        "seed": 6000,
        "dota_reviewer_approved": None,
        "dota_reviewer_reference": None,
        "statistical_review_approved": None,
        "statistical_reviewer_reference": None,
        "data_basis_approved": None,
        "data_basis_approver_reference": None,
        "items": [
            {
                "review_item_id": "review-0001",
                "family": "transfer",
                "claim": "Original immutable claim",
                "literal_evidence": "Observed evidence",
                "supported": None,
                "believable": None,
                "notes": None,
            }
        ],
    }


def _completed_submission() -> dict:
    payload = _packet()
    payload["items"][0].update(
        {
            "claim": "Browser tried to replace the claim",
            "supported": True,
            "believable": True,
            "notes": "Reviewed literally.",
        }
    )
    payload.update(
        {
            "dota_reviewer_approved": True,
            "dota_reviewer_reference": "dota-reviewer",
            "statistical_review_approved": True,
            "statistical_reviewer_reference": "statistics-reviewer",
            "data_basis_approved": True,
            "data_basis_approver_reference": "data-approver",
        }
    )
    return payload


def test_review_merge_preserves_evidence_and_requires_complete_signoffs() -> None:
    original = _packet()
    submitted = _completed_submission()
    merged = merge_review_state(original, submitted, finalize=True)

    assert merged["items"][0]["claim"] == "Original immutable claim"
    assert merged["items"][0]["supported"] is True
    assert merged["finalized"] is True
    assert merged["completed_at"]

    submitted["dota_reviewer_reference"] = None
    with pytest.raises(ReviewInputError, match="dota_reviewer_reference"):
        merge_review_state(original, submitted, finalize=True)

    dota_only = _completed_submission()
    dota_only["statistical_review_approved"] = None
    dota_only["statistical_reviewer_reference"] = None
    dota_only["data_basis_approved"] = None
    dota_only["data_basis_approver_reference"] = None
    assert merge_review_state(original, dota_only, finalize=True)["finalized"] is True


def test_loopback_server_saves_owner_only_completed_packet(tmp_path: Path) -> None:
    packet_path = tmp_path / "packet.json"
    output_path = tmp_path / "completed.json"
    packet_path.write_text(json.dumps(_packet()), encoding="utf-8")
    state = ReviewState(packet_path, output_path)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        _handler(state, b"<!doctype html><title>Review</title>"),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urllib.request.urlopen(f"{url}/api/packet") as response:  # noqa: S310 - fixed loopback test URL
            assert json.load(response)["items"][0]["supported"] is None

        request = urllib.request.Request(
            f"{url}/api/finalize",
            data=json.dumps(_completed_submission()).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:  # noqa: S310 - fixed loopback test URL
            assert json.load(response)["finalized"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["items"][0]["claim"] == "Original immutable claim"
    assert stat.S_IMODE(output_path.stat().st_mode) == 0o600


def test_loopback_server_rejects_incomplete_finalization(tmp_path: Path) -> None:
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(_packet()), encoding="utf-8")
    state = ReviewState(packet_path, tmp_path / "completed.json")
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(state, b"review"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    request = urllib.request.Request(
        f"http://127.0.0.1:{server.server_address[1]}/api/finalize",
        data=json.dumps(_packet()).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request)  # noqa: S310 - fixed loopback test URL
        assert error.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
