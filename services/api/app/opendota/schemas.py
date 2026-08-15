from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RawPayload:
    endpoint: str
    source_id: str
    payload_hash: str
    payload: Any
    fetched_at: str


@dataclass(frozen=True, slots=True)
class PlayerProfile:
    account_id: int
    personaname: str | None = None
    avatarfull: str | None = None
    rank_tier: int | None = None
    profile_url: str | None = None
    is_private: bool = False
    raw: dict[str, Any] = field(default_factory=dict)
