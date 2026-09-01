from __future__ import annotations

from pathlib import Path

import pytest
from app.analysis.source import FixtureOpenDotaSource
from app.core.config import Settings, validate_runtime_configuration
from app.main import create_app
from app.providers import build_v7_provider, provider_cache_key
from app.stratz import (
    GET_PARSED_MATCH_CORE,
    GET_PARSED_MATCHES_BATCH,
    GET_PLAYER_HISTORY_PAGE,
    StratzProvider,
    stratz_cache_key,
)


def test_default_provider_and_v6_lineage_remain_opendota() -> None:
    settings = Settings()
    validate_runtime_configuration(settings)
    assert settings.data_provider == "opendota"
    assert build_v7_provider(settings) is None


def test_stratz_configuration_is_loaded_without_defaulting_production_to_stratz(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATA_PROVIDER", "stratz")
    monkeypatch.setenv("STRATZ_API_TOKEN", "fixture-secret")
    monkeypatch.setenv("STRATZ_TIMEOUT_SECONDS", "12")
    settings = Settings.from_env()

    assert settings.data_provider == "stratz"
    assert settings.stratz_api_token == "fixture-secret"
    assert settings.stratz_timeout_seconds == 12
    assert Settings().data_provider == "opendota"


def test_stratz_provider_is_explicit_and_does_not_replace_legacy_analysis_source() -> None:
    settings = Settings(data_provider="stratz")
    provider = build_v7_provider(settings)
    assert isinstance(provider, StratzProvider)

    app = create_app(settings, source=FixtureOpenDotaSource("tests/fixtures/opendota"))
    assert app.state.data_provider == "stratz"
    assert isinstance(app.state.v7_provider, StratzProvider)
    assert app.state.analysis_service.source.__class__ is FixtureOpenDotaSource


def test_stratz_selection_cannot_run_v6_or_v61_flags() -> None:
    with pytest.raises(ValueError, match="V7-only"):
        validate_runtime_configuration(Settings(data_provider="stratz", free_dna_v6_enabled=True))
    with pytest.raises(ValueError, match="V7-only"):
        validate_runtime_configuration(Settings(data_provider="stratz", free_dna_v61_enabled=True))
    with pytest.raises(ValueError, match="STRATZ_USER_AGENT"):
        validate_runtime_configuration(Settings(data_provider="stratz", stratz_user_agent="custom"))


def test_cache_identity_is_provider_and_operation_specific() -> None:
    assert stratz_cache_key("player", 123) == "stratz:player:123"
    assert stratz_cache_key("history", 123, "window", GET_PLAYER_HISTORY_PAGE.version) != (
        provider_cache_key("opendota", "history", 123, "window", GET_PLAYER_HISTORY_PAGE.version)
    )
    assert stratz_cache_key("match", 456, GET_PARSED_MATCH_CORE.name, GET_PARSED_MATCH_CORE.version) != stratz_cache_key(
        "match", 456, GET_PARSED_MATCHES_BATCH.name, GET_PARSED_MATCHES_BATCH.version
    )


def test_queries_are_named_and_do_not_use_legacy_role_fields() -> None:
    assert GET_PLAYER_HISTORY_PAGE.name == "GetPlayerHistoryPage"
    assert "roleBasic" not in GET_PLAYER_HISTORY_PAGE.document
    assert "lane_role" not in GET_PLAYER_HISTORY_PAGE.document
    assert "roleBasic" not in GET_PARSED_MATCH_CORE.document
    assert "roleBasic" not in GET_PARSED_MATCHES_BATCH.document


def test_secrets_are_local_only_and_env_example_has_empty_token() -> None:
    env_example = Path(".env.example").read_text()
    assert "STRATZ_API_TOKEN=" in env_example
    assert "STRATZ_API_TOKEN=<" not in env_example
    assert ".env" in Path(".gitignore").read_text()
