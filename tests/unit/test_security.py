import pytest
from app.core.errors import InvalidPlayerIdentifier
from app.core.security import RateLimiter, parse_player_identifier, redact


def test_url_and_raw_id_resolve_to_same_account() -> None:
    raw = parse_player_identifier("193875165")
    url = parse_player_identifier("https://www.opendota.com/players/193875165/")
    assert raw == url
    assert raw.canonical_url == "https://www.opendota.com/players/193875165"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "193875165?api_key=secret",
        "https://example.com/players/193875165",
        "https://www.opendota.com/players/not-an-id",
        "https://www.opendota.com/players/193875165?api_key=secret",
        "4294967296",
    ],
)
def test_invalid_identifiers_are_rejected(value: str) -> None:
    with pytest.raises(InvalidPlayerIdentifier):
        parse_player_identifier(value)


def test_redaction_removes_credentials_from_nested_values() -> None:
    value = redact(
        {"Authorization": "Bearer super-secret", "url": "/matches/1?api_key=super-secret"},
        ("super-secret",),
    )
    assert "super-secret" not in str(value)
    assert value["Authorization"] == "[REDACTED]"


def test_unresolved_vanity_inputs_use_separate_rate_limit_buckets() -> None:
    limiter = RateLimiter(max_per_ip=10, max_per_account=1)

    assert limiter.allow("127.0.0.1", 0, unresolved_key="first_player")
    assert limiter.allow("127.0.0.1", 0, unresolved_key="second_player")
    assert not limiter.allow("127.0.0.1", 0, unresolved_key="first_player")
