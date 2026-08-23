"""Frozen non-MMR context baselines and the v6 fallback hierarchy."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .constants import BASELINE_VERSION
from .models import _freeze, _plain


@dataclass(frozen=True, slots=True)
class BaselineContext:
    patch: str | None = None
    hero_id: int | str | None = None
    hero_function: str | None = None
    lane_context: str | None = None

    @property
    def lane(self) -> str | None:
        return self.lane_context


@dataclass(frozen=True, slots=True)
class BaselineCell:
    """One baseline cell, frozen at generation time.

    ``metrics`` may hold several metric-specific means/medians.  The resolver
    never synthesises a missing metric from another metric.
    """

    level: str
    patch: str | None = None
    hero_id: int | str | None = None
    hero_function: str | None = None
    lane_context: str | None = None
    metrics: Mapping[str, float] = field(default_factory=dict)
    match_count: int = 0
    distinct_players: int = 0
    source_version: str = BASELINE_VERSION
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.match_count < 0 or self.distinct_players < 0:
            raise ValueError("baseline cell counts must be non-negative")
        object.__setattr__(self, "metrics", _freeze({key: float(value) for key, value in self.metrics.items()}))
        object.__setattr__(self, "limitations", tuple(str(item) for item in self.limitations))

    @property
    def eligible(self) -> bool:
        return self.match_count >= 200 and self.distinct_players >= 50

    def metric(self, key: str) -> float | None:
        value = self.metrics.get(key)
        return float(value) if value is not None else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "patch": self.patch,
            "hero_id": self.hero_id,
            "hero_function": self.hero_function,
            "lane_context": self.lane_context,
            "metrics": _plain(self.metrics),
            "match_count": self.match_count,
            "distinct_players": self.distinct_players,
            "eligible": self.eligible,
            "source_version": self.source_version,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class BaselineResolution:
    metric: str
    value: float | None
    level: str | None
    cell: BaselineCell | None
    available: bool
    attempted_levels: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    version: str = BASELINE_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "value": self.value,
            "level": self.level,
            "cell": self.cell.as_dict() if self.cell else None,
            "available": self.available,
            "attempted_levels": list(self.attempted_levels),
            "limitations": list(self.limitations),
            "version": self.version,
        }


BASELINE_HIERARCHY = (
    "patch+hero+lane",
    "patch+hero_function+lane",
    "patch+hero",
    "patch+lane",
    "patch",
    "overall",
)

_LEVEL_ALIASES = {
    "patch_hero_lane": "patch+hero+lane",
    "patch_hero_function_lane": "patch+hero_function+lane",
    "patch_hero": "patch+hero",
    "patch_lane": "patch+lane",
    "overall_patch": "patch",
    "global": "overall",
}


def _level_dimensions(level: str) -> tuple[str, ...]:
    return {
        "patch+hero+lane": ("patch", "hero_id", "lane_context"),
        "patch+hero_function+lane": ("patch", "hero_function", "lane_context"),
        "patch+hero": ("patch", "hero_id"),
        "patch+lane": ("patch", "lane_context"),
        "patch": ("patch",),
        "overall": (),
    }.get(level, ())


def _coerce_cell(level: str, raw: BaselineCell | Mapping[str, Any]) -> BaselineCell:
    if isinstance(raw, BaselineCell):
        # A caller may provide a cell under a different mapping key.  The
        # explicit cell level remains authoritative for auditability.
        return raw
    normalised_level = _LEVEL_ALIASES.get(str(raw.get("level", level)), str(raw.get("level", level)))
    return BaselineCell(
        level=normalised_level,
        patch=raw.get("patch"),
        hero_id=raw.get("hero_id"),
        hero_function=raw.get("hero_function"),
        lane_context=raw.get("lane_context", raw.get("lane")),
        metrics=raw.get("metrics", raw.get("values", {})),
        match_count=int(raw.get("match_count", raw.get("matches", 0)) or 0),
        distinct_players=int(raw.get("distinct_players", raw.get("players", 0)) or 0),
        source_version=str(raw.get("source_version", BASELINE_VERSION)),
        limitations=tuple(raw.get("limitations", ())),
    )


def _normalise_cells(cells: Mapping[Any, Any] | Iterable[BaselineCell | Mapping[str, Any]]) -> tuple[BaselineCell, ...]:
    if isinstance(cells, Mapping):
        result: list[BaselineCell] = []
        for key, raw in cells.items():
            if isinstance(raw, BaselineCell):
                result.append(raw)
                continue
            raw_map = dict(raw) if isinstance(raw, Mapping) else {}
            level = str(raw_map.get("level", ""))
            if not level:
                if isinstance(key, str) and key in BASELINE_HIERARCHY:
                    level = key
                elif isinstance(key, tuple):
                    # Tuple keys use the natural hierarchy dimensions.
                    level = {
                        3: "patch+hero+lane",
                        2: "patch+hero",
                        1: "patch",
                        0: "overall",
                    }.get(len(key), "overall")
                    if len(key) == 3:
                        raw_map.setdefault("patch", key[0])
                        raw_map.setdefault("hero_id", key[1])
                        raw_map.setdefault("lane_context", key[2])
                    elif len(key) == 2 and level == "patch+hero":
                        raw_map.setdefault("patch", key[0])
                        raw_map.setdefault("hero_id", key[1])
                    elif len(key) == 1:
                        raw_map.setdefault("patch", key[0])
            result.append(_coerce_cell(level or "overall", raw_map))
        return tuple(result)
    return tuple(item if isinstance(item, BaselineCell) else _coerce_cell(str(item.get("level", "overall")), item) for item in cells)


def _cell_matches(cell: BaselineCell, context: BaselineContext, level: str) -> bool:
    for dimension in _level_dimensions(level):
        left = getattr(cell, dimension)
        right = getattr(context, dimension)
        if right is None or left != right:
            return False
    # Avoid accidentally treating a general cell as a more specific one.
    return cell.level == level or cell.level in {"", "overall"}


class BaselineResolver:
    """Resolve metric baselines using the frozen, non-MMR fallback order."""

    def __init__(
        self,
        cells: Mapping[Any, Any] | Iterable[BaselineCell | Mapping[str, Any]],
        *,
        min_matches: int = 200,
        min_players: int = 50,
        version: str = BASELINE_VERSION,
    ) -> None:
        self.cells = _normalise_cells(cells)
        self.min_matches = max(1, int(min_matches))
        self.min_players = max(1, int(min_players))
        self.version = version

    def resolve(self, context: BaselineContext, metric: str, *, default: float | None = None) -> BaselineResolution:
        attempted: list[str] = []
        ineligible_reasons: list[str] = []
        for level in BASELINE_HIERARCHY:
            attempted.append(level)
            matching = [
                cell
                for cell in self.cells
                if _cell_matches(cell, context, level)
                and cell.match_count >= self.min_matches
                and cell.distinct_players >= self.min_players
                and cell.metric(metric) is not None
            ]
            if matching:
                # A generation pipeline should create one cell per key.  If a
                # malformed snapshot contains duplicates, deterministic tie
                # breaking chooses the largest evidence cell then source name.
                chosen = sorted(
                    matching,
                    key=lambda cell: (-cell.match_count, -cell.distinct_players, cell.source_version, repr(cell.metrics)),
                )[0]
                limitations = tuple(dict.fromkeys((*chosen.limitations, *ineligible_reasons)))
                return BaselineResolution(
                    metric,
                    chosen.metric(metric),
                    level,
                    chosen,
                    True,
                    tuple(attempted),
                    limitations,
                    self.version,
                )
            # Keep useful diagnostics while falling back.  Do not expose the
            # cell's raw identity in the report.
            for cell in self.cells:
                if _cell_matches(cell, context, level):
                    if cell.match_count < self.min_matches:
                        ineligible_reasons.append(f"{level}: fewer than {self.min_matches} matches")
                    if cell.distinct_players < self.min_players:
                        ineligible_reasons.append(f"{level}: fewer than {self.min_players} players")
        limitations = tuple(dict.fromkeys((*ineligible_reasons, "no eligible context baseline cell")))
        return BaselineResolution(
            metric,
            default,
            None,
            None,
            default is not None,
            tuple(attempted),
            limitations,
            self.version,
        )


ContextBaselineResolver = BaselineResolver


def resolve_baseline(
    context: BaselineContext | Mapping[str, Any],
    metric: str,
    cells: Mapping[Any, Any] | Iterable[BaselineCell | Mapping[str, Any]],
    *,
    default: float | None = None,
    min_matches: int = 200,
    min_players: int = 50,
) -> BaselineResolution:
    if not isinstance(context, BaselineContext):
        context = BaselineContext(
            patch=context.get("patch"),
            hero_id=context.get("hero_id"),
            hero_function=context.get("hero_function"),
            lane_context=context.get("lane_context", context.get("lane")),
        )
    return BaselineResolver(cells, min_matches=min_matches, min_players=min_players).resolve(context, metric, default=default)


__all__ = [
    "BaselineContext",
    "BaselineCell",
    "BaselineResolution",
    "BASELINE_HIERARCHY",
    "BaselineResolver",
    "ContextBaselineResolver",
    "resolve_baseline",
]
