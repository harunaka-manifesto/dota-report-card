"""Static and runtime proofs of the tracker's architectural boundaries (goal §16.11, §16.14)."""
from __future__ import annotations

import ast
from pathlib import Path

import httpx
import pytest
from app.core.config import Settings
from app.tracker.mobile_api import create_mobile_app
from fastapi.testclient import TestClient

from scripts.tracker_seed_demo import seed_demo

TRACKER = Path(__file__).parents[2] / "services/api/app/tracker"
LLM_SDKS = ("anthropic", "openai", "langchain", "google.generativeai", "google.genai", "cohere",
            "mistralai", "ollama", "transformers", "litellm")
PROVIDER_PACKAGES = ("app.opendota", "report_card.stratz", "report_card.providers")
# The acquisition and derivation layers, which ADR 0004 places below entitlement.
BELOW_ENTITLEMENT = ("acquisition.py", "replay_acquisition.py", "historical.py", "historical_summary.py",
                     "sync.py", "linking.py", "materialization.py", "normalization.py", "replay.py",
                     "evidence.py", "provider_control.py", "provider_transport.py", "roles.py",
                     "role_evidence.py", "events.py", "integrity.py", "metrics.py", "context.py",
                     "eligibility.py", "insights.py", "jobs.py")
# Read-path modules: they may not import provider clients at all.
READ_PATH = ("profile.py", "shares.py", "operations.py", "history.py", "trend.py", "coverage.py")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            base = node.module
            if node.level:
                base = "app.tracker." + base
            names.add(base)
    return names


def test_tracker_static_import_closure_never_reaches_report_card_or_app_main():
    """The relocation goal's closure rule: report_card (the deprecated-but-live
    Free DNA / legacy package) and app.main (the deploy composition root) must
    never be pulled in by the tracker's own static import graph. If either
    were reachable, app.tracker would no longer be safely deployable without
    the legacy package.
    """
    repo_root = Path(__file__).parents[2]
    app_dir = repo_root / "services/api/app"

    def module_name_for(path: Path) -> str:
        rel = path.relative_to(repo_root / "services/api")
        parts = list(rel.parts)
        parts[-1] = parts[-1][: -len(".py")] if parts[-1] != "__init__.py" else None
        parts = [p for p in parts if p is not None and p != "__init__.py"]
        return ".".join(parts) if parts else "app"

    def module_imports(path: Path, mod: str) -> set[str]:
        tree = ast.parse(path.read_text())
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    # All tracker modules are flat (app.tracker.<name>), so a
                    # single-level relative import resolves within the package.
                    base = "app.tracker"
                    if node.module:
                        base += "." + node.module
                    found.add(base)
                elif node.module:
                    found.add(node.module)
        return found

    all_modules: dict[str, Path] = {}
    for path in app_dir.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        all_modules[module_name_for(path)] = path

    graph: dict[str, set[str]] = {
        mod: module_imports(path, mod) for mod, path in all_modules.items()
    }

    visited: set[str] = set()
    frontier = [mod for mod in all_modules if mod == "app.tracker" or mod.startswith("app.tracker.")]
    visited.update(frontier)
    while frontier:
        current = frontier.pop()
        for imported in graph.get(current, ()):  # noqa: B905
            candidate = imported
            while candidate and candidate not in all_modules and "." in candidate:
                candidate = candidate.rsplit(".", 1)[0]
            if candidate in all_modules and candidate not in visited:
                visited.add(candidate)
                frontier.append(candidate)

    assert "app.main" not in visited
    assert not any(m.startswith("report_card") for m in visited)
    for mod in visited:
        assert not mod.startswith("report_card"), mod


def test_no_runtime_llm_sdk_is_imported_anywhere_in_the_tracker():
    for path in TRACKER.glob("*.py"):
        for name in _imports(path):
            assert not name.startswith(LLM_SDKS), (path.name, name)
    for sdk in LLM_SDKS:
        with pytest.raises(ImportError):
            __import__(sdk)


def test_acquisition_and_analysis_layers_never_read_entitlement():
    for name in BELOW_ENTITLEMENT:
        source = (TRACKER / name).read_text()
        for token in ("active_scope", "subscriptions", "entitlement", "PRO_BACKFILL", '"PRO"'):
            assert token not in source, (name, token)


def test_read_path_modules_cannot_reach_provider_clients():
    for name in READ_PATH:
        for imported in _imports(TRACKER / name):
            assert not imported.startswith(PROVIDER_PACKAGES), (name, imported)
            assert imported not in {"app.tracker.provider_transport", "app.tracker.provider_control", "httpx"}, (
                name, imported)
    mobile = _imports(TRACKER / "mobile_api.py")
    assert not {name for name in mobile if name.startswith(PROVIDER_PACKAGES)}
    # The mobile boundary may only enqueue sync work, never execute a provider page.
    tree = ast.parse((TRACKER / "mobile_api.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "app.tracker.sync":
            assert {alias.name for alias in node.names} == {"request_account_sync"}


def test_free_and_pro_share_one_fresh_path():
    """No fresh-path module branches on scope; the finalizer reads scope only to
    select entitled prior history above persisted analysis."""
    finalization = (TRACKER / "finalization.py").read_text()
    assert "active_scope" not in finalization.split("def recompute_indexes")[0].split("def build_analysis")[0]


def test_every_mobile_read_is_provider_free(database, monkeypatch):
    from app.tracker.schema import ingest_jobs
    from sqlalchemy import func, select

    personas = seed_demo(database)
    with database.connect() as connection:
        jobs_before = connection.scalar(select(func.count()).select_from(ingest_jobs))

    def refuse(*_args, **_kwargs):
        raise AssertionError("a product read attempted network I/O")

    # Real network transports only; the in-process test client has its own.
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", refuse)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", refuse)
    app = create_mobile_app(Settings(), database=database)
    client = TestClient(app)
    reads = [route.path for route in app.routes
             if "GET" in getattr(route, "methods", set()) and "{" not in route.path
             and route.path not in {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}]
    params = {"mode": "STANDARD", "time_zone": "UTC", "role": "SUPPORT", "metric_id": "support.camps_stacked.v1"}
    for persona in personas.values():
        headers = {"Authorization": f"Bearer {persona['access_token']}"}
        for path in reads:
            response = client.get(path, params=params, headers=headers)
            assert response.status_code in {200, 401, 409}, (path, response.text)
        history = client.get("/history", params=params, headers=headers)
        if history.status_code == 200:
            for match in history.json()["matches"]:
                assert client.get(f"/matches/{match['ref']}", headers=headers).status_code == 200
    with database.connect() as connection:
        # Reads never queue acquisition, backfill or rebuild work either.
        assert connection.scalar(select(func.count()).select_from(ingest_jobs)) == jobs_before
