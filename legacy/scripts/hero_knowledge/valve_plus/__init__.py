"""Optional, non-blocking Valve Dota Plus fixture provider."""

from .fetch import fetch_valve_plus_snapshot
from .normalize import normalize_valve_plus_snapshot

__all__ = ["fetch_valve_plus_snapshot", "normalize_valve_plus_snapshot"]
