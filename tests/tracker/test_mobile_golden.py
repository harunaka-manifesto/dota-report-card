"""Golden mobile fixtures from the fixture-backed seed, plus contract scans.

Fixtures under tests/fixtures/tracker/mobile-v1 are versioned and never
overwritten: a contract change adds a new directory. To create a missing file
deliberately, run with TRACKER_WRITE_MISSING_GOLDEN=1 and review it.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pytest
from app.core.config import Settings
from app.tracker.mobile_api import create_mobile_app
from fastapi.testclient import TestClient
from sqlalchemy import select

from scripts.tracker_seed_demo import seed_demo

GOLDEN = Path(__file__).parents[1] / "fixtures/tracker/mobile-v1"
OPENAPI = Path(__file__).parents[2] / "docs/tracker/api/mobile-openapi-v1.json"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Goal §6.11: no provider or pipeline vocabulary in product payloads.
FORBIDDEN = re.compile(r"opendota|stratz|valve|\bparse[rd]?\b|parsing|\bqueue|\bjobs?\b|quota|rate.?limit|"
                       r"position_[1-5]|position [45]|\bpos [1-5]\b|replay_url|celery|redis|worker",
                       re.IGNORECASE)


class Normalizer:
    def __init__(self) -> None:
        self.refs: dict[str, str] = {}

    def __call__(self, value: Any, key: str | None = None) -> Any:
        if isinstance(value, dict):
            return {k: self(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [self(item) for item in value]
        if isinstance(value, str):
            if UUID.match(value):
                return self.refs.setdefault(value, f"<ref:{len(self.refs) + 1}>")
            if DATETIME.match(value):
                return "<datetime>"
            if DATE.match(value):
                return "<date>"
            if key in {"request_id", "next_cursor", "cursor"}:
                return f"<{key}>"
        if isinstance(value, float):
            return round(value, 9)
        return value


ENDPOINTS = [
    "/account", "/bootstrap", "/readiness", "/subscription", "/history-operation", "/recovery",
    "/settings", "/account/steam-switch/preflight",
    "/home?mode=STANDARD&time_zone=UTC", "/history?mode=STANDARD", "/history?mode=TURBO",
    "/coverage?mode=STANDARD", "/profile?mode=STANDARD", "/profile?mode=TURBO",
    "/progress?mode=STANDARD&role=SUPPORT&metric_id=support.camps_stacked.v1",
]


def capture(client: TestClient, token: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    normalize = Normalizer()
    responses: dict[str, Any] = {}
    refs: list[str] = []
    for path in ENDPOINTS:
        response = client.get(path, headers=headers)
        body = response.json()
        responses[path] = normalize({"status": response.status_code, "body": body})
        if path.startswith("/history?") and response.status_code == 200:
            refs.extend(match["ref"] for match in body["matches"])
    for ref in refs:
        response = client.get(f"/matches/{ref}", headers=headers)
        responses[f"/matches/{normalize(ref)}"] = normalize({"status": response.status_code, "body": response.json()})
    return responses


@pytest.fixture
def seeded(database):
    return database, seed_demo(database)


def test_seed_covers_required_states_and_matches_versioned_golden_fixtures(seeded):
    database, personas = seeded
    client = TestClient(create_mobile_app(Settings(), database=database))
    GOLDEN.mkdir(parents=True, exist_ok=True)
    written = []
    for name, persona in personas.items():
        observed = capture(client, persona["access_token"])
        text = json.dumps(observed, indent=2, sort_keys=True) + "\n"
        assert not FORBIDDEN.search(text), (name, FORBIDDEN.search(text))
        path = GOLDEN / f"{name}.json"
        if not path.exists():
            if os.getenv("TRACKER_WRITE_MISSING_GOLDEN") != "1":
                pytest.fail(f"missing golden fixture {path.name}; set TRACKER_WRITE_MISSING_GOLDEN=1 to create it")
            path.write_text(text)
            written.append(path.name)
            continue
        assert json.loads(path.read_text()) == observed, f"{name} drifted from its versioned golden fixture"
    assert not written, f"wrote new golden fixtures, review and commit: {written}"

    # State coverage the goal requires, checked on the captured contract itself.
    ready = capture(client, personas["ready_common"]["access_token"])
    matches = [value["body"] for key, value in ready.items() if key.startswith("/matches/")]
    assert any(match["role_source"] == "USER_CONFIRMED" for match in matches)
    assert any(match["insights"]["cards"] == [] for match in matches)
    assert ready["/profile?mode=STANDARD"]["body"]["identity"]["template_id"] == "MOSTLY_ROLE_SO_FAR"
    states = capture(client, personas["match_states"]["access_token"])
    lifecycles = {value["body"]["lifecycle"] for key, value in states.items() if key.startswith("/matches/")}
    assert lifecycles >= {"READY", "UNAVAILABLE", "WAITING_FOR_DATA", "WAITING_FOR_PRIOR_MATCH", "ACTION_REQUIRED"}
    replay_na = [value["body"] for key, value in states.items() if key.startswith("/matches/")
                 and value["body"]["lifecycle"] == "READY" and value["body"]["progression"] == "STANDARD"]
    assert any(metric["state"] == "NOT_AVAILABLE" and metric["unavailable_reason"]
               for match in replay_na for metric in match["metrics"])
    assert any(metric["state"] == "MEASURED" and metric["raw_value"] == 0
               for match in replay_na for metric in match["metrics"])
    outcomes = set()
    for persona in personas.values():
        response = client.get("/bootstrap", headers={"Authorization": f"Bearer {persona['access_token']}"})
        if response.status_code == 200:
            outcomes |= {mode["outcome"] for mode in response.json()["modes"]}
    assert outcomes >= {"NO_STEAM_LINKED", "DATA_ACCESS_BLOCKED", "NO_MATCHES_FOUND", "NO_ELIGIBLE_MATCHES",
                        "READY", "READY_WITH_GAPS"}
    denied = client.get("/account", headers={"Authorization": f"Bearer {personas['deletion_pending']['access_token']}"})
    assert denied.status_code == 401
    from app.tracker.schema import provider_calls

    with database.connect() as connection:
        assert connection.execute(select(provider_calls.c.id)).first() is None


def test_mobile_openapi_is_checked_in_closed_and_free_of_pipeline_vocabulary(database):
    schema = create_mobile_app(Settings(), database=database).openapi()
    text = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    assert not FORBIDDEN.search(text), FORBIDDEN.search(text)
    assert OPENAPI.exists(), "export with: python -m scripts.tracker_export_openapi"
    assert json.loads(OPENAPI.read_text()) == json.loads(text), "mobile OpenAPI changed; re-export and review"
    for path in ("/app-store/notifications", "/summary"):
        assert path not in schema["paths"]
    problems = lint_openapi(schema)
    assert problems == [], problems


def lint_openapi(schema: dict[str, Any]) -> list[str]:
    """Structural checks standing in for an external validator (none installed)."""
    problems: list[str] = []
    components = schema.get("components", {}).get("schemas", {})
    operation_ids: set[str] = set()

    def walk(node: Any, where: str) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.split("/")[-1] not in components:
                problems.append(f"{where}: unresolved {ref}")
            if node.get("type") == "object" and node.get("additionalProperties") is True and "properties" not in node:
                problems.append(f"{where}: untyped object")
            for key, value in node.items():
                walk(value, f"{where}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{where}[{index}]")

    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            operation_id = operation.get("operationId")
            if operation_id in operation_ids:
                problems.append(f"duplicate operationId {operation_id}")
            operation_ids.add(operation_id)
            if "200" in operation.get("responses", {}) and method == "get" and path != "/shares/{share_ref}/image.svg":
                content = operation["responses"]["200"].get("content", {}).get("application/json", {})
                if "$ref" not in content.get("schema", {}):
                    problems.append(f"{method} {path}: response is not a named model")
    walk(schema, "#")
    return problems
