from __future__ import annotations

import logging
from typing import Any

from app.core.security import redact


class SecretRedactionFilter(logging.Filter):
    def __init__(self, secrets: tuple[str | None, ...] = ()) -> None:
        super().__init__()
        self.secrets = secrets

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.msg, self.secrets)
        if record.args:
            record.args = redact(record.args, self.secrets)
        return True


def configure_logging(level: str, secrets: tuple[str | None, ...] = ()) -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
    root = logging.getLogger()
    if not any(isinstance(item, SecretRedactionFilter) for item in root.filters):
        redaction = SecretRedactionFilter(secrets)
        root.addFilter(redaction)
        for handler in root.handlers:
            handler.addFilter(redaction)


def log_fields(**fields: Any) -> dict[str, Any]:
    return redact(fields)
