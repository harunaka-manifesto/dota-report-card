#!/usr/bin/env python3
"""Serve the private v6 reviewer packet through a loopback-only survey UI."""

from __future__ import annotations

import argparse
import copy
import json
import sys
import threading
import webbrowser
from collections.abc import Mapping
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.player_analysis_v6.calibration_evaluation import (  # noqa: E402
    REVIEW_PACKET_VERSION,
    atomic_json,
)

UI_PATH = Path(__file__).with_name("v6_calibration_review.html")
EDITABLE_TOP_LEVEL = (
    "dota_reviewer_approved",
    "dota_reviewer_reference",
    "statistical_review_approved",
    "statistical_reviewer_reference",
    "data_basis_approved",
    "data_basis_approver_reference",
)
class ReviewInputError(ValueError):
    """Raised when browser-submitted review state is incomplete or malformed."""


def _load_packet(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != REVIEW_PACKET_VERSION:
        raise ReviewInputError("unsupported private review packet version")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ReviewInputError("review packet needs non-empty items")
    identifiers = [item.get("review_item_id") for item in items if isinstance(item, Mapping)]
    if len(identifiers) != len(items) or any(not isinstance(item, str) or not item for item in identifiers):
        raise ReviewInputError("every review item needs a review_item_id")
    if len(set(identifiers)) != len(identifiers):
        raise ReviewInputError("review_item_id values must be unique")
    return payload


def _optional_bool(value: Any, field: str) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise ReviewInputError(f"{field} must be true, false, or null")


def _optional_text(value: Any, field: str, *, limit: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ReviewInputError(f"{field} must be text or null")
    text = value.strip()
    if len(text) > limit:
        raise ReviewInputError(f"{field} exceeds {limit} characters")
    return text or None


def merge_review_state(
    original: Mapping[str, Any],
    submitted: Mapping[str, Any],
    *,
    finalize: bool,
) -> dict[str, Any]:
    """Copy only reviewer-controlled fields into the immutable source packet."""

    if submitted.get("version") != REVIEW_PACKET_VERSION:
        raise ReviewInputError("submitted packet version does not match")
    original_items = original.get("items")
    submitted_items = submitted.get("items")
    if not isinstance(original_items, list) or not isinstance(submitted_items, list):
        raise ReviewInputError("review items must be a list")
    expected_ids = [item.get("review_item_id") for item in original_items]
    received_ids = [item.get("review_item_id") for item in submitted_items if isinstance(item, Mapping)]
    if received_ids != expected_ids:
        raise ReviewInputError("review items cannot be added, removed, or reordered")

    result = copy.deepcopy(dict(original))
    result_items = result["items"]
    for index, raw in enumerate(submitted_items):
        if not isinstance(raw, Mapping):
            raise ReviewInputError("each review item must be an object")
        supported = _optional_bool(raw.get("supported"), "supported")
        believable = _optional_bool(raw.get("believable"), "believable")
        result_items[index]["supported"] = supported
        result_items[index]["believable"] = believable
        result_items[index]["notes"] = _optional_text(raw.get("notes"), "notes", limit=2_000)
        if finalize and (supported is None or believable is None):
            raise ReviewInputError(f"{expected_ids[index]} still needs both votes")
        if finalize and (supported is False or believable is False) and result_items[index]["notes"] is None:
            raise ReviewInputError(f"{expected_ids[index]} needs a note explaining the problem")

    for field in EDITABLE_TOP_LEVEL:
        if field.endswith("_approved"):
            result[field] = _optional_bool(submitted.get(field), field)
        else:
            result[field] = _optional_text(submitted.get(field), field, limit=500)
    if finalize:
        if result["dota_reviewer_approved"] is None:
            raise ReviewInputError("dota_reviewer_approved must be answered before finalizing")
        if result["dota_reviewer_reference"] is None:
            raise ReviewInputError("dota_reviewer_reference is required before finalizing")
        for approval, reference in (
            ("statistical_review_approved", "statistical_reviewer_reference"),
            ("data_basis_approved", "data_basis_approver_reference"),
        ):
            if result[approval] is not None and result[reference] is None:
                raise ReviewInputError(f"{reference} is required when {approval} is answered")
        result["completed_at"] = str(submitted.get("completed_at") or datetime.now(UTC).isoformat())
    else:
        result.pop("completed_at", None)
    result["finalized"] = finalize
    return result


class ReviewState:
    def __init__(self, packet_path: Path, output_path: Path) -> None:
        self.packet_path = packet_path
        self.output_path = output_path
        self.original = _load_packet(packet_path)
        self.lock = threading.Lock()
        self.current = self._load_current()

    def _load_current(self) -> dict[str, Any]:
        if not self.output_path.exists():
            return copy.deepcopy(self.original)
        submitted = json.loads(self.output_path.read_text(encoding="utf-8"))
        if not isinstance(submitted, Mapping):
            raise ReviewInputError("saved review output must be an object")
        return merge_review_state(
            self.original,
            submitted,
            finalize=submitted.get("finalized") is True,
        )

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return copy.deepcopy(self.current)

    def save(self, submitted: Mapping[str, Any], *, finalize: bool) -> dict[str, Any]:
        with self.lock:
            merged = merge_review_state(self.original, submitted, finalize=finalize)
            atomic_json(self.output_path, merged)
            self.current = merged
            return copy.deepcopy(merged)


def _handler(state: ReviewState, html: bytes) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "V6CalibrationReview/1.0"

        def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: HTTPStatus, payload: Mapping[str, Any]) -> None:
            self._send(
                status,
                (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8"),
                "application/json; charset=utf-8",
            )

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/":
                self._send(HTTPStatus.OK, html, "text/html; charset=utf-8")
            elif self.path == "/api/packet":
                self._json(HTTPStatus.OK, state.snapshot())
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path not in {"/api/save", "/api/finalize"}:
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 2_000_000:
                    raise ReviewInputError("request body must be between 1 byte and 2 MB")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, Mapping):
                    raise ReviewInputError("request body must be a JSON object")
                saved = state.save(payload, finalize=self.path == "/api/finalize")
            except (ReviewInputError, json.JSONDecodeError, ValueError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            self._json(
                HTTPStatus.OK,
                {
                    "finalized": saved.get("finalized") is True,
                    "output": str(state.output_path),
                },
            )

        def log_message(self, format: str, *args: object) -> None:
            print(f"review-ui: {format % args}", file=sys.stderr)

    return Handler


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if not 0 <= args.port <= 65_535:
        raise ReviewInputError("--port must be between 0 and 65535")
    output = args.output or args.packet.with_name(f"{args.packet.stem}-completed.json")
    state = ReviewState(args.packet.resolve(), output.resolve())
    html = UI_PATH.read_bytes()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), _handler(state, html))
    port = int(server.server_address[1])
    url = f"http://127.0.0.1:{port}/"
    print(f"V6 review page: {url}", flush=True)
    print(f"Completed packet: {state.output_path}", flush=True)
    if not args.no_browser:
        threading.Timer(0.25, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
