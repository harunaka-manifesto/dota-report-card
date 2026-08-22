"""Privacy-safe deterministic share-card rendering for Free DNA reports."""

from __future__ import annotations

import hashlib
import html
import json
from typing import Any
from urllib.parse import urlparse

from app.content.renderer import resolve_evolution_copy

RENDERER_VERSION = "share-svg-4.1.0"
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
    cache_key = share_cache_key(
        report,
        card_type=card_type,
        show_name=show_name,
        show_avatar=show_avatar,
    )
    title = html.escape(str(content.get("title") or "Your Dota DNA"))
    subtitle = html.escape(str(content.get("subtitle") or ""))
    avatar_markup = ""
    avatar_url = content.get("avatar_url")
    if isinstance(avatar_url, str) and avatar_url:
        avatar_markup = (
            f'<image href="{html.escape(avatar_url, quote=True)}" x="870" y="90" '
            'width="120" height="120" preserveAspectRatio="xMidYMid slice" '
            'clip-path="circle(60px at 60px 60px)"/>'
        )
    section_markup = _section_markup(content.get("sections", []))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350" role="img" aria-labelledby="title subtitle">
  <title id="title">{title}</title><desc id="subtitle">{subtitle}</desc>
  <rect width="1080" height="1350" fill="#f7f2e8"/><rect x="48" y="48" width="984" height="1254" rx="24" fill="none" stroke="#c8c0b1" stroke-width="3"/>
  <text x="90" y="130" class="eyebrow">DOTA DNA</text><text x="90" y="260" class="title">{title}</text><text x="90" y="330" class="subtitle">{subtitle}</text>
  <line x1="90" y1="410" x2="990" y2="410" stroke="#c8c0b1" stroke-width="2"/>{section_markup}
  {avatar_markup}<text x="90" y="1240" class="footer">Summary history · deterministic snapshot</text>
  <style>.eyebrow{{font:700 24px Arial;letter-spacing:5px;fill:#9b3d22}}.title{{font:700 72px Arial;fill:#20231f}}.subtitle{{font:400 28px Arial;fill:#6e685d}}.section-heading{{font:700 18px Arial;letter-spacing:3px;fill:#9b3d22}}.section-line{{font:700 27px Arial;fill:#20231f}}.footer{{font:400 20px Arial;fill:#7e776b}}</style>
</svg>'''
    return svg, cache_key


def _section_markup(sections: Any) -> str:
    if not isinstance(sections, list):
        return ""
    markup: list[str] = []
    y = 470
    for section in sections:
        if not isinstance(section, dict):
            continue
        heading = html.escape(str(section.get("heading") or ""))
        lines = section.get("lines")
        if not heading or not isinstance(lines, list):
            continue
        markup.append(f'<text x="90" y="{y}" class="section-heading">{heading}</text>')
        y += 38
        for line in lines[:3]:
            markup.append(f'<text x="90" y="{y}" class="section-line">{html.escape(str(line))}</text>')
            y += 38
        y += 30
    return "".join(markup)


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
        f"{item.get('label')} · {item.get('zone')}"
        for item in card.get("strongest_elements", [])
        if isinstance(item, dict) and item.get("label") and item.get("zone")
    ]
    patterns = [
        str(item.get("label"))
        for item in card.get("strongest_patterns", [])
        if isinstance(item, dict) and item.get("label")
    ]
    common_thread = portfolio.get("common_thread") or "No clear Common Thread yet."
    exception = portfolio.get("exception_hero")
    exception_line = f"Exception · {exception}" if exception else "No clear Exception yet."
    evolution = _human_evolution_copy(portfolio.get("pool_direction"))
    mirror = card.get("hero_mirror") or {}
    mirror_line = str(mirror.get("hero_name")) if mirror.get("hero_name") else "No clear Mirror yet."
    sections = [
        {"heading": "TOP SIGNALS", "lines": elements or ["No highlighted Element cleared the display gate yet."]},
        {"heading": "PATTERNS", "lines": [" · ".join(patterns)] if patterns else ["No Pattern highlight cleared the display gate yet."]},
        {"heading": "HERO PORTFOLIO", "lines": [str(common_thread), exception_line, evolution or "Pool Evolution is unavailable yet."]},
        {"heading": "HERO MIRROR", "lines": [mirror_line]},
    ]
    facts = [line for section in sections for line in section["lines"]]
    return {
        "title": identity.get("display_name") if show_name else "Your Dota DNA",
        "subtitle": " · ".join(facts[:2]) or "A bounded snapshot of observable Dota patterns.",
        "facts": facts,
        "sections": sections,
        "show_avatar": show_avatar,
        "show_name": show_name,
        "avatar_url": _safe_avatar_url(identity.get("avatar_url")) if show_avatar else None,
    }


def _human_evolution_copy(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    if value in {
        "new_heroes_new_toolkit",
        "new_heroes_same_toolkit",
        "stable_core_new_branch",
        "broadly_stable",
    }:
        copy = resolve_evolution_copy(value)
        return f"{copy['heading']} {copy['body']}"
    return value


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
