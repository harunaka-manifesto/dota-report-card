"""Matches list: play sessions, placeholder names and keyword search (matches/SSOT.md).

A play session is a run of Standard and Turbo matches where each match starts less than three
hours after the previous one ended. Sessions, names and search are presentation only: nothing
here feeds baselines, mastery, claims or any progression state, and no row carries a
per-metric state or a composite verdict (matches/SSOT.md §2).
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final, Literal
from zoneinfo import ZoneInfo

from app.tracker import hero_references

CONTRACT: Final[Literal["matches-list-v1"]] = "matches-list-v1"
SESSION_GAP = timedelta(hours=3)  # owner decision 2026-09-29: end of one match to start of the next
NAME_MAX = 40
QUERY_MAX = 100
ROLE_LABELS = {"CARRY": "Carry", "MID": "Mid", "OFFLANE": "Offlane", "SUPPORT": "Support"}
ROLE_WORDS = {
    "carry": "CARRY", "safelane": "CARRY", "pos1": "CARRY",
    "mid": "MID", "middle": "MID", "pos2": "MID",
    "offlane": "OFFLANE", "offlaner": "OFFLANE", "pos3": "OFFLANE",
    "support": "SUPPORT", "supp": "SUPPORT", "sup": "SUPPORT", "pos4": "SUPPORT", "pos5": "SUPPORT",
}
MODE_WORDS = {"turbo": "TURBO", "standard": "STANDARD"}
RESULT_WORDS = {"win": True, "won": True, "victory": True, "loss": False, "lost": False, "lose": False,
                "defeat": False}
RESERVED = frozenset({*ROLE_WORDS, *MODE_WORDS, *RESULT_WORDS})


@dataclass(frozen=True)
class Fact:
    """One visible Standard or Turbo match, in chronology-key terms."""
    ref: str
    started_at: datetime
    source_id: int
    duration_seconds: int | None
    hero_id: int
    role: str | None
    mode: str
    won: bool | None

    @property
    def chronology(self) -> tuple[datetime, int]:
        return self.started_at, self.source_id

    @property
    def ended_at(self) -> datetime:
        # A match still waiting for its duration counts as ending when it started.
        return self.started_at + timedelta(seconds=self.duration_seconds or 0)


def sessions(facts: Iterable[Fact]) -> list[list[Fact]]:
    """Chronological sessions; a gap of exactly SESSION_GAP starts a new one."""
    grouped: list[list[Fact]] = []
    for fact in sorted(facts, key=lambda item: item.chronology):
        if grouped and fact.started_at - grouped[-1][-1].ended_at < SESSION_GAP:
            grouped[-1].append(fact)
        else:
            grouped.append([fact])
    return grouped


def day_part(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "late-night"


def _dominant(values: Sequence[tuple[object, datetime]], total: int) -> object | None:
    """The value covering at least half the session; ties go to the latest played, then the smallest."""
    counts = Counter(value for value, _ in values if value is not None)
    latest: dict[object, datetime] = {}
    for value, at in values:
        if value is not None:
            latest[value] = max(latest.get(value, at), at)
    ranked = sorted(counts, key=lambda value: (-counts[value], -latest[value].timestamp(), str(value)))
    return ranked[0] if ranked and counts[ranked[0]] * 2 >= total else None


def placeholder_name(members: Sequence[Fact], zone: ZoneInfo) -> str:
    """'{Weekday} {day part} {focus}', e.g. 'Tuesday evening Axe run' (owner decision 2026-09-29)."""
    local = members[0].started_at.astimezone(zone)
    prefix = f"{local.strftime('%A')} {day_part(local.hour)}"
    hero = _dominant([(hero_references.name(fact.hero_id), fact.started_at) for fact in members], len(members))
    if len(members) == 1:
        return f"{prefix} {hero} game" if hero else f"{prefix} game"
    if hero:
        return f"{prefix} {hero} run"
    role = _dominant([(fact.role, fact.started_at) for fact in members], len(members))
    if role:
        return f"{prefix} {ROLE_LABELS[str(role)]} grind"
    if all(fact.mode == "TURBO" for fact in members):
        return f"{prefix} Turbo session"
    return f"{prefix} session"


def header(members: Sequence[Fact]) -> dict[str, object]:
    """Whole-session facts: result counts (unknown results left out) and the played span."""
    return {
        "started_at": members[0].started_at,
        "ended_at": max(fact.ended_at for fact in members),
        "wins": sum(1 for fact in members if fact.won is True),
        "losses": sum(1 for fact in members if fact.won is False),
        "match_count": len(members),
    }


@dataclass(frozen=True)
class Term:
    text: str
    heroes: frozenset[int]
    role: str | None
    mode: str | None
    result: bool | None

    def matches(self, fact: Fact, session_name: str) -> bool:
        return (fact.hero_id in self.heroes or (self.role is not None and fact.role == self.role)
                or (self.mode is not None and fact.mode == self.mode)
                or (self.result is not None and fact.won is self.result)
                or self.text in hero_references.normalize(session_name))


def parse_query(query: str | None) -> list[Term]:
    """Whitespace-separated terms, all of which must match a row (hero, role, mode, result or session name)."""
    words = hero_references.normalize(query or "").split()
    return [Term(text=word, heroes=hero_references.match_heroes(word, prefix=word not in RESERVED),
                 role=ROLE_WORDS.get(word),
                 mode=MODE_WORDS.get(word), result=RESULT_WORDS.get(word)) for word in words]


def matches_query(terms: Sequence[Term], fact: Fact, session_name: str) -> bool:
    return all(term.matches(fact, session_name) for term in terms)
