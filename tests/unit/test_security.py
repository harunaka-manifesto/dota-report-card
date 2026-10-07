from app.core.security import redact, safe_endpoint


def test_redaction_removes_credentials_from_nested_values() -> None:
    value = redact(
        {"Authorization": "Bearer super-secret", "url": "/matches/1?api_key=super-secret"},
        ("super-secret",),
    )
    assert "super-secret" not in str(value)
    assert value["Authorization"] == "[REDACTED]"


def test_safe_endpoint_drops_query_strings() -> None:
    assert safe_endpoint("https://api.opendota.com/api/matches/1?api_key=secret") == "/api/matches/1"
