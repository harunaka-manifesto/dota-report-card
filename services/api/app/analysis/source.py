from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from app.core.config import FREE_HISTORY_LIMIT
from app.core.errors import ProfileUnavailable


class AnalysisSource(Protocol):
    async def get_player(self, account_id: int) -> dict[str, Any]: ...

    async def get_matches(
        self, account_id: int, *, limit: int = FREE_HISTORY_LIMIT, project: str | None = None
    ) -> list[dict[str, Any]]: ...

    async def get_match(self, match_id: int) -> dict[str, Any]: ...


class FixtureOpenDotaSource:
    """Recorded source adapter used by tests and the local demo."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.requests: list[tuple[str, int]] = []

    async def get_player(self, account_id: int) -> dict[str, Any]:
        self.requests.append(("player", account_id))
        return self._read_first(
            f"player_{account_id}.json",
            f"profile_{account_id}.json",
            fallback={"profile": {"account_id": account_id, "personaname": "Recorded player"}},
        )

    async def get_matches(
        self, account_id: int, *, limit: int = FREE_HISTORY_LIMIT, project: str | None = None
    ) -> list[dict[str, Any]]:
        self.requests.append(("matches", account_id))
        value = self._read_first(
            f"matches_{account_id}.json", f"history_{account_id}.json", fallback=[]
        )
        return list(value or [])[: min(limit, FREE_HISTORY_LIMIT)]

    async def get_match(self, match_id: int) -> dict[str, Any]:
        self.requests.append(("match", match_id))
        return self._read_first(f"match_{match_id}.json", fallback={"match_id": match_id})

    def _read_first(self, *names: str, fallback: Any) -> Any:
        for name in names:
            path = self.directory / name
            if path.exists():
                with path.open(encoding="utf-8") as handle:
                    return json.load(handle)
        if fallback is not None:
            return fallback
        raise ProfileUnavailable("Recorded profile is unavailable")


class MappingSource:
    """Tiny injected source for unit and contract tests."""

    def __init__(
        self,
        *,
        player: dict[str, Any],
        matches: list[dict[str, Any]],
        details: dict[int, dict[str, Any]],
    ) -> None:
        self.player = player
        self.matches = matches
        self.details = details
        self.requests: list[tuple[str, int]] = []

    async def get_player(self, account_id: int) -> dict[str, Any]:
        self.requests.append(("player", account_id))
        if not self.player:
            raise ProfileUnavailable("Profile is unavailable")
        return self.player

    async def get_matches(
        self, account_id: int, *, limit: int = FREE_HISTORY_LIMIT, project: str | None = None
    ) -> list[dict[str, Any]]:
        self.requests.append(("matches", account_id))
        return self.matches[: min(limit, FREE_HISTORY_LIMIT)]

    async def get_match(self, match_id: int) -> dict[str, Any]:
        self.requests.append(("match", match_id))
        return self.details[match_id]
