"""Privacy-safe deterministic share-card rendering.

The production renderer can swap this SVG template for a pinned Chromium
renderer without changing the report contract or cache key.  SVG keeps the
local/test path dependency-free and is directly usable by browser share and
download fallbacks.
"""

from __future__ import annotations

import hashlib
import html
import json
from typing import Any
from urllib.parse import urlparse

RENDERER_VERSION = "share-svg-2.1.0"
CARD_TYPES = frozenset({
    "identity", "exposed", "strength", "strongest", "pattern", "archetypes",
    "dna", "heroes", "final",
})


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
        "asset_manifest_hash": _asset_manifest_hash(report),
        "content": content,
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


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
    cache_key = share_cache_key(report, card_type=card_type, show_name=show_name, show_avatar=show_avatar)
    title = html.escape(str(content.get("title") or "Dota DNA"))
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
    hero_markup = ""
    hero_url = content.get("hero_url")
    if isinstance(hero_url, str) and hero_url:
        hero_markup = (
            f'<image href="{html.escape(hero_url, quote=True)}" x="770" y="80" '
            'width="220" height="220" preserveAspectRatio="xMidYMid slice"/>'
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
  {avatar_markup}{hero_markup}<text x="90" y="1190" class="footer">Summary history · deterministic snapshot</text>
  <style>.eyebrow{{font:700 24px Arial;letter-spacing:5px;fill:#9b3d22}}.title{{font:700 72px Arial;fill:#20231f}}.subtitle{{font:400 28px Arial;fill:#6e685d}}.fact{{font:700 31px Arial;fill:#20231f}}.footer{{font:400 20px Arial;fill:#7e776b}}</style>
</svg>'''
    return svg, cache_key


def _card_content(report: dict[str, Any], card_type: str, *, show_name: bool, show_avatar: bool) -> dict[str, Any]:
    shares = report.get("shares") or {}
    raw_card = shares.get(card_type)
    card = dict(raw_card) if isinstance(raw_card, dict) else {}
    identity = report.get("identity") or {}
    facts: list[Any] = []
    if card_type in {"identity", "exposed", "strength", "strongest", "pattern"}:
        title = card.get("headline") or "Your Dota pattern"
        facts = [value for value in card.get("receipts", []) if isinstance(value, str)]
        groups = card.get("archetype_groups") or []
        subtitle = card.get("archetype") or (" · ".join(groups) if groups else "A finding from the patterns in your recent matches.")
    elif card_type == "archetypes":
        archetypes = [item for item in (shares.get("archetypes") or []) if isinstance(item, dict)]
        first = archetypes[0] if archetypes else {}
        title = first.get("label") or "Your context archetypes"
        facts = [item.get("label") for item in archetypes[1:4] if item.get("label")]
        subtitle = first.get("group_label") or "Three context views from the same summary history."
    elif card_type == "dna":
        title = card.get("archetype") or "Your Dota DNA"
        descriptors = [item.get("label") for item in card.get("descriptors", []) if isinstance(item, dict)]
        facts = descriptors + ([f"{card.get('match_count')} eligible matches"] if card.get("match_count") is not None else [])
        subtitle = card.get("archetype") or "A snapshot of the patterns in your recent matches."
    elif card_type == "heroes":
        signature = card.get("signature") or {}
        title = signature.get("name") or "Your hero identity"
        pattern = card.get("pattern") or {}
        recommendation = (card.get("recommendations") or [{}])[0]
        recommendation_name = recommendation.get("name") if isinstance(recommendation, dict) else None
        facts = ["Signature hero", pattern.get("label") if isinstance(pattern, dict) else pattern]
        if recommendation_name:
            facts.append(f"Try next: {recommendation_name}")
        subtitle = card.get("archetype") or "A snapshot of the heroes in your recent matches."
    else:
        title = identity.get("display_name") if show_name else card.get("archetype") or "Your Dota DNA"
        facts = [card.get("archetype"), card.get("signature"), card.get("pattern"), card.get("rhythm")]
        subtitle = card.get("archetype") or "A snapshot of the patterns in your recent matches."
    hero_url = None
    if card_type == "heroes":
        signature = card.get("signature") or {}
        hero_url = _safe_hero_url(signature.get("portrait_url")) if isinstance(signature, dict) else None
    return {
        "title": title,
        "subtitle": subtitle,
        "facts": [value for value in facts if value],
        "show_avatar": show_avatar,
        "show_name": show_name,
        "avatar_url": _safe_avatar_url(identity.get("avatar_url") or identity.get("avatarfull")) if show_avatar else None,
        "hero_url": hero_url,
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


def _safe_hero_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname != "cdn.cloudflare.steamstatic.com":
        return None
    if parsed.query or parsed.fragment:
        return None
    return value


def _asset_manifest_hash(report: dict[str, Any]) -> str:
    heroes = report.get("heroes") or {}
    cards = [
        heroes.get("signature"),
        *(heroes.get("comfort_picks") or []),
        *(heroes.get("recommendations") or []),
    ]
    versions = sorted(
        str(card.get("portrait_asset_version"))
        for card in cards
        if isinstance(card, dict) and card.get("portrait_asset_version")
    )
    value = {
        "taxonomy_version": heroes.get("taxonomy_version"),
        "portrait_versions": versions,
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
