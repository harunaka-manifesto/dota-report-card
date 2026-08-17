"""Privacy-safe deterministic share-card rendering for the v4 report."""

from __future__ import annotations

import hashlib
import html
import json
from typing import Any
from urllib.parse import urlparse

RENDERER_VERSION = "share-svg-4.0.0"
CARD_TYPES = frozenset({"final"})


def share_cache_key(
    report: dict[str, Any],
    *,
    card_type: str,
    show_name: bool = True,
    show_avatar: bool = True,
    aspect_ratio: str = "4:5",
) -> str:
    content = _card_content(report, card_type, show_name=show_name, show_avatar=show_avatar)
    value = {
        "report_id": report.get("report_id"),
        "report_schema": report.get("schema_version"),
        "card_type": card_type,
        "aspect_ratio": aspect_ratio,
        "show_name": show_name,
        "show_avatar": show_avatar,
        "renderer": RENDERER_VERSION,
        "content": content,
    }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_share_svg(
    report: dict[str, Any],
    *,
    card_type: str,
    show_name: bool = True,
    show_avatar: bool = True,
) -> tuple[str, str]:
    if card_type not in CARD_TYPES:
        raise ValueError("Unsupported share card")
    content = _card_content(report, card_type, show_name=show_name, show_avatar=show_avatar)
    cache_key = share_cache_key(
        report,
        card_type=card_type,
        show_name=show_name,
        show_avatar=show_avatar,
    )
    title = html.escape(str(content.get("title") or "Your Dota DNA"))
    subtitle = html.escape(str(content.get("subtitle") or ""))
    facts = [html.escape(str(value)) for value in content.get("facts", [])]
    avatar_markup = ""
    avatar_url = content.get("avatar_url")
    if isinstance(avatar_url, str) and avatar_url:
        avatar_markup = (
            f'<image href="{html.escape(avatar_url, quote=True)}" x="870" y="90" '
            'width="120" height="120" preserveAspectRatio="xMidYMid slice" '
            'clip-path="circle(60px at 60px 60px)"/>'
        )
    fact_markup = "".join(
        f'<text x="90" y="{500 + index * 58}" class="fact">{fact}</text>'
        for index, fact in enumerate(facts[:5])
    )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350" role="img" aria-labelledby="title subtitle">
  <title id="title">{title}</title><desc id="subtitle">{subtitle}</desc>
  <rect width="1080" height="1350" fill="#f7f2e8"/><rect x="48" y="48" width="984" height="1254" rx="24" fill="none" stroke="#c8c0b1" stroke-width="3"/>
  <text x="90" y="130" class="eyebrow">DOTA DNA</text><text x="90" y="260" class="title">{title}</text><text x="90" y="330" class="subtitle">{subtitle}</text>
  <line x1="90" y1="410" x2="990" y2="410" stroke="#c8c0b1" stroke-width="2"/>{fact_markup}
  {avatar_markup}<text x="90" y="1190" class="footer">Summary history · deterministic snapshot</text>
  <style>.eyebrow{{font:700 24px Arial;letter-spacing:5px;fill:#9b3d22}}.title{{font:700 72px Arial;fill:#20231f}}.subtitle{{font:400 28px Arial;fill:#6e685d}}.fact{{font:700 31px Arial;fill:#20231f}}.footer{{font:400 20px Arial;fill:#7e776b}}</style>
</svg>'''
    return svg, cache_key


def _card_content(
    report: dict[str, Any],
    card_type: str,
    *,
    show_name: bool,
    show_avatar: bool,
) -> dict[str, Any]:
    if card_type not in CARD_TYPES:
        raise ValueError("Unsupported share card")
    shares = report.get("shares") or {}
    card = shares.get("final") or {}
    identity = report.get("identity") or {}
    portfolio = card.get("hero_portfolio") or {}
    elements = [
        item.get("label")
        for item in card.get("strongest_elements", [])
        if isinstance(item, dict) and item.get("label")
    ]
    patterns = [
        item.get("label")
        for item in card.get("strongest_patterns", [])
        if isinstance(item, dict) and item.get("label")
    ]
    facts = [*elements, *patterns]
    common_thread = portfolio.get("common_thread")
    if common_thread:
        facts.append(f"Common thread: {common_thread}")
    mirror = card.get("hero_mirror") or {}
    if mirror.get("hero_name"):
        facts.append(f"Hero Mirror: {mirror['hero_name']}")
    return {
        "title": identity.get("display_name") if show_name else "Your Dota DNA",
        "subtitle": " · ".join(str(value) for value in facts[:2])
        or "A bounded snapshot of observable Dota patterns.",
        "facts": facts,
        "show_avatar": show_avatar,
        "show_name": show_name,
        "avatar_url": _safe_avatar_url(identity.get("avatar_url")) if show_avatar else None,
    }


def _safe_avatar_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in {
        "steamcdn-a.akamaihd.net",
        "avatars.akamai.steamstatic.com",
    }:
        return None
    if parsed.query or parsed.fragment:
        return None
    return value


__all__ = ["CARD_TYPES", "RENDERER_VERSION", "build_share_svg", "share_cache_key"]
