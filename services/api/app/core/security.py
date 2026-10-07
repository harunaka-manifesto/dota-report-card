from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


def redact(value: Any, secrets: tuple[str | None, ...] = ()) -> Any:
    """Recursively remove known credentials from logs and exception payloads."""

    known = {secret for secret in secrets if secret}
    if isinstance(value, str):
        result = value
        for secret in known:
            result = result.replace(secret, "[REDACTED]")
        result = re.sub(r"(?i)(authorization\s*[:=]\s*)([^,\s]+)", r"\1[REDACTED]", result)
        result = re.sub(r"(?i)(api_key\s*=\s*)([^&\s]+)", r"\1[REDACTED]", result)
        return result
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if str(key).lower() in {"authorization", "api_key"}
            else redact(item, secrets)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item, secrets) for item in value)
    return value


def safe_endpoint(endpoint: str) -> str:
    """Only log an API path, never a query string that could contain credentials."""

    parsed = urlparse(endpoint)
    return parsed.path or endpoint.split("?", 1)[0]
