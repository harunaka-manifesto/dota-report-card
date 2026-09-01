from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from app.core.config import FREE_HISTORY_LIMIT, FREE_HISTORY_WINDOW_DAYS
from app.core.errors import ProfileUnavailable


class OpenDotaAnalysisSource(Protocol):
    async def get_player(self, account_id: int) -> dict[str, Any]: ...

    async def get_matches(
        self,
        account_id: int,
        *,
        limit: int | None = FREE_HISTORY_LIMIT,
        days: int = FREE_HISTORY_WINDOW_DAYS,
        project: str | Sequence[str] | None = None,
    ) -> list[dict[str, Any]]: ...

    async def get_summary_history_once(
        self,
        account_id: int,
        *,
        days: int,
        project: Sequence[str],
        provider_limit: int,
    ) -> list[dict[str, Any]]: ...

    async def get_match(self, match_id: int) -> dict[str, Any]: ...


# Compatibility alias for integrations that imported the old internal name.
# V7 uses app.providers.HistoryProvider instead.
AnalysisSource = OpenDotaAnalysisSource


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
        self,
        account_id: int,
        *,
        limit: int | None = FREE_HISTORY_LIMIT,
        days: int = FREE_HISTORY_WINDOW_DAYS,
        project: str | Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        self.requests.append(("matches", account_id))
        value = self._read_first(
            f"matches_{account_id}.json", f"history_{account_id}.json", fallback=[]
        )
        rows = list(value or [])
        return rows if limit is None else rows[:limit]

    async def get_summary_history_once(
        self,
        account_id: int,
        *,
        days: int,
        project: Sequence[str],
        provider_limit: int,
    ) -> list[dict[str, Any]]:
        del days
        rows = await self.get_matches(account_id, limit=None, project=project)
        return [{key: row.get(key) for key in project if key in row} for row in rows][
            :provider_limit
        ]

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
        self,
        account_id: int,
        *,
        limit: int | None = FREE_HISTORY_LIMIT,
        days: int = FREE_HISTORY_WINDOW_DAYS,
        project: str | Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        self.requests.append(("matches", account_id))
        return list(self.matches) if limit is None else self.matches[:limit]

    async def get_summary_history_once(
        self,
        account_id: int,
        *,
        days: int,
        project: Sequence[str],
        provider_limit: int,
    ) -> list[dict[str, Any]]:
        del days
        self.requests.append(("summary_history_once", account_id))
        return [
            {key: row.get(key) for key in project if key in row}
            for row in self.matches[:provider_limit]
        ]

    async def get_match(self, match_id: int) -> dict[str, Any]:
        self.requests.append(("match", match_id))
        return self.details[match_id]
