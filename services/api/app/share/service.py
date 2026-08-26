"""Privacy-safe deterministic share-card rendering for Free DNA reports."""

from __future__ import annotations

import hashlib
import html
import json
from typing import Any
from urllib.parse import urlparse

from app.content.renderer import resolve_evolution_copy
from app.player_analysis_v6.copy import forbidden_copy_violations

RENDERER_VERSION = "share-svg-5.0.0"
V6_RENDERER_VERSION = "share-svg-6.0.0"
V61_RENDERER_VERSION = "share-svg-6.1.0"
CARD_TYPES = frozenset({"final"})
V6_CARD_TYPES = frozenset({"final", "identity", "strongest-finding", "hero-mirror"})

_VOID = "#0B0C0B"
_SURFACE = "#141513"
_RAISED = "#1C1E1B"
_LINE = "#30332E"
_PAPER = "#F2EFE7"
_TEXT = "#F7F4EC"
_MUTED = "#A3A59D"
_CORAL = "#F26B5E"
_SAFFRON = "#F3B744"
_LILAC = "#B7A4FF"
_CYAN = "#64D9E7"
_MAGENTA = "#F065B7"
_CHARTREUSE = "#C8EE62"


def share_cache_key(
    report: dict[str, Any],
    *,
    card_type: str,
    show_name: bool = True,
    show_avatar: bool = True,
    aspect_ratio: str = "4:5",
) -> str:
    schema_version = report.get("schema_version")
    is_v6 = schema_version in {"free-dna-report-6.0.0", "free-dna-report-6.1.0"}
    if is_v6:
        content = _v6_card_content(report, card_type, show_name=show_name)
    else:
        content = _card_content(report, card_type, show_name=show_name, show_avatar=show_avatar)
    value = {
        "report_id": report.get("report_id"),
        "report_schema": report.get("schema_version"),
        "card_type": card_type,
        "aspect_ratio": aspect_ratio,
        "show_name": show_name,
        "show_avatar": show_avatar,
        "renderer": (
            V61_RENDERER_VERSION
            if schema_version == "free-dna-report-6.1.0"
            else V6_RENDERER_VERSION if is_v6 else RENDERER_VERSION
        ),
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
    if report.get("schema_version") in {"free-dna-report-6.0.0", "free-dna-report-6.1.0"}:
        return _build_v6_share_svg(report, card_type=card_type, show_name=show_name)
    if card_type not in CARD_TYPES:
        raise ValueError("Unsupported share card")
    content = _card_content(report, card_type, show_name=show_name, show_avatar=show_avatar)
    cache_key = share_cache_key(
        report,
        card_type=card_type,
        show_name=show_name,
        show_avatar=show_avatar,
    )
    title = html.escape(_compact_title(str(content.get("title") or "Your Dota DNA")))
    subtitle = html.escape(str(content.get("subtitle") or ""))
    identity_headline = str(content.get("identity_headline") or "Your Dota keeps a shape of its own.")
    avatar_markup = ""
    avatar_url = content.get("avatar_url")
    if isinstance(avatar_url, str) and avatar_url:
        avatar_markup = (
            f'<circle cx="922" cy="142" r="64" fill="{_RAISED}" stroke="{_PAPER}" '
            f'stroke-width="2"/><image href="{html.escape(avatar_url, quote=True)}" x="858" y="78" '
            'width="128" height="128" preserveAspectRatio="xMidYMid slice" '
            'clip-path="circle(64px at 64px 64px)"/>'
        )
    section_markup = _section_markup(content.get("sections", []))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350" role="img" aria-labelledby="title subtitle">
  <title id="title">{title}</title><desc id="subtitle">{subtitle}</desc>
  <defs>
    <linearGradient id="aurora" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{_CORAL}"/><stop offset="0.46" stop-color="{_SAFFRON}"/><stop offset="1" stop-color="{_LILAC}"/>
    </linearGradient>
    <radialGradient id="aurora-glow" cx="25%" cy="20%" r="85%">
      <stop offset="0" stop-color="{_CYAN}" stop-opacity="0.9"/><stop offset="0.48" stop-color="{_MAGENTA}" stop-opacity="0.62"/><stop offset="1" stop-color="{_VOID}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="grain" width="12" height="12" patternUnits="userSpaceOnUse">
      <path d="M0 2h1M6 8h1M10 4h1M3 11h1" stroke="{_PAPER}" stroke-opacity="0.1" stroke-width="1"/>
    </pattern>
    <clipPath id="identity-cell"><rect x="72" y="246" width="936" height="300"/></clipPath>
  </defs>
  <rect width="1080" height="1350" fill="{_VOID}"/>
  <rect x="36" y="36" width="1008" height="1278" fill="none" stroke="{_LINE}" stroke-width="2"/>
  <rect x="72" y="246" width="936" height="300" fill="{_RAISED}"/>
  <g clip-path="url(#identity-cell)">
    <rect x="72" y="246" width="936" height="300" fill="url(#aurora)" opacity="0.55"/>
    <rect x="72" y="246" width="936" height="300" fill="url(#aurora-glow)" opacity="0.78"/>
    <rect x="72" y="246" width="936" height="300" fill="url(#grain)"/>
    <path d="M72 510C260 410 390 570 560 430S870 280 1008 370V546H72Z" fill="{_VOID}" opacity="0.62"/>
  </g>
  <text x="72" y="104" class="eyebrow">DOTA DNA / FREE</text>
  <text x="72" y="178" class="title">{title}</text>
  <text x="72" y="220" class="subtitle">{subtitle}</text>
  <text x="104" y="318" class="identity-kicker">YOUR PLAYING SHAPE</text>
  {_text_lines(identity_headline, x=104, y=390, class_name="identity", max_chars=28, line_height=62)}
  {avatar_markup}
  {section_markup}
  <line x1="72" y1="1260" x2="1008" y2="1260" stroke="{_LINE}" stroke-width="2"/>
  <text x="72" y="1294" class="footer">PRIVATE BY DEFAULT · NO PLAYER ID · NO RAW MATCH DATA</text>
  <text x="1008" y="1294" text-anchor="end" class="footer">FREE DNA / {RENDERER_VERSION.upper()}</text>
  <style>
    .eyebrow{{font:700 20px 'Plus Jakarta Sans',Arial,sans-serif;letter-spacing:4px;fill:{_SAFFRON}}}
    .title{{font:800 64px 'Plus Jakarta Sans',Arial,sans-serif;letter-spacing:-2px;fill:{_TEXT}}}
    .subtitle{{font:500 20px 'Plus Jakarta Sans',Arial,sans-serif;fill:{_MUTED}}}
    .identity-kicker,.section-heading{{font:700 16px 'Plus Jakarta Sans',Arial,sans-serif;letter-spacing:3px;fill:{_VOID}}}
    .identity{{font:800 48px 'Plus Jakarta Sans',Arial,sans-serif;letter-spacing:-1.5px;fill:{_VOID}}}
    .section-heading-dark{{font:700 16px 'Plus Jakarta Sans',Arial,sans-serif;letter-spacing:3px;fill:{_SAFFRON}}}
    .section-line{{font:650 24px 'Plus Jakarta Sans',Arial,sans-serif;fill:{_TEXT}}}
    .section-note{{font:500 18px 'Plus Jakarta Sans',Arial,sans-serif;fill:{_MUTED}}}
    .footer{{font:600 13px 'Plus Jakarta Sans',Arial,sans-serif;letter-spacing:1.4px;fill:{_MUTED}}}
  </style>
</svg>'''
    return svg, cache_key


def _build_v6_share_svg(
    report: dict[str, Any],
    *,
    card_type: str,
    show_name: bool,
) -> tuple[str, str]:
    content = _v6_card_content(report, card_type, show_name=show_name)
    cache_key = share_cache_key(report, card_type=card_type, show_name=show_name, show_avatar=False)
    renderer_version = (
        V61_RENDERER_VERSION
        if report.get("schema_version") == "free-dna-report-6.1.0"
        else V6_RENDERER_VERSION
    )
    title = html.escape(str(content["title"]))
    subtitle = html.escape(str(content["subtitle"]))
    sections = _section_markup(content["sections"])
    identity = html.escape(str(content["identity_headline"]))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350" role="img" aria-labelledby="v6-title v6-subtitle">
  <title id="v6-title">{title}</title><desc id="v6-subtitle">{subtitle}</desc>
  <rect width="1080" height="1350" fill="{_VOID}"/>
  <rect x="36" y="36" width="1008" height="1278" fill="none" stroke="{_LINE}" stroke-width="2"/>
  <text x="72" y="104" class="eyebrow">DOTA DNA / FREE V6</text>
  <text x="72" y="178" class="title">{title}</text>
  <text x="72" y="220" class="subtitle">{subtitle}</text>
  <rect x="72" y="246" width="936" height="190" fill="{_RAISED}" stroke="{_LINE}" stroke-width="2"/>
  <text x="104" y="302" class="identity-kicker">OBSERVED SUMMARY SHAPE</text>
  {_text_lines(identity, x=104, y=366, class_name="identity", max_chars=31, line_height=54)}
  {sections}
  <line x1="72" y1="1260" x2="1008" y2="1260" stroke="{_LINE}" stroke-width="2"/>
  <text x="72" y="1294" class="footer">PRIVATE BY DEFAULT · NO PLAYER ID · NO RAW MATCH DATA</text>
  <text x="1008" y="1294" text-anchor="end" class="footer">FREE DNA / {renderer_version.upper()}</text>
  <style>
    .eyebrow{{font:700 20px 'Plus Jakarta Sans',Arial,sans-serif;letter-spacing:4px;fill:{_SAFFRON}}}
    .title{{font:800 64px 'Plus Jakarta Sans',Arial,sans-serif;letter-spacing:-2px;fill:{_TEXT}}}
    .subtitle{{font:500 20px 'Plus Jakarta Sans',Arial,sans-serif;fill:{_MUTED}}}
    .identity-kicker,.section-heading{{font:700 16px 'Plus Jakarta Sans',Arial,sans-serif;letter-spacing:3px;fill:{_SAFFRON}}}
    .identity{{font:800 42px 'Plus Jakarta Sans',Arial,sans-serif;letter-spacing:-1px;fill:{_TEXT}}}
    .section-heading-dark{{font:700 16px 'Plus Jakarta Sans',Arial,sans-serif;letter-spacing:3px;fill:{_SAFFRON}}}
    .section-line{{font:650 24px 'Plus Jakarta Sans',Arial,sans-serif;fill:{_TEXT}}}
    .footer{{font:600 13px 'Plus Jakarta Sans',Arial,sans-serif;letter-spacing:1.4px;fill:{_MUTED}}}
  </style>
</svg>'''
    return svg, cache_key


def _v6_card_content(report: dict[str, Any], card_type: str, *, show_name: bool) -> dict[str, Any]:
    if card_type not in V6_CARD_TYPES:
        raise ValueError("Unsupported v6 share card")
    candidates = [
        item for item in report.get("share_candidates", [])
        if isinstance(item, dict) and item.get("eligible") is True
    ]
    if card_type != "final":
        wanted = {
            "identity": {"identity", "dynamic_identity"},
            "strongest-finding": {"strongest-finding", "strongest_finding", "finding"},
            "hero-mirror": {"hero-mirror", "hero_mirror"},
        }[card_type]
        candidates = [
            item for item in candidates
            if str(item.get("id") or item.get("candidate_id") or item.get("kind")) in wanted
        ]
    if not candidates:
        raise ValueError("The requested v6 share card is not eligible")

    identity_summary_value = report.get("identity_summary")
    identity_summary: dict[str, Any] = dict(identity_summary_value) if isinstance(identity_summary_value, dict) else {}
    headline = str(identity_summary.get("headline") or "Your observed summary shape")
    sections: list[dict[str, Any]] = []
    for candidate in candidates[:4]:
        payload_value = candidate.get("payload")
        payload: dict[str, Any] = dict(payload_value) if isinstance(payload_value, dict) else {}
        heading = str(payload.get("title") or candidate.get("title") or candidate.get("kind") or "Observed signal")
        lines = [
            str(value)
            for value in (
                payload.get("body") or payload.get("reason") or candidate.get("reason"),
                payload.get("evidence_label"),
                payload.get("limitation_label"),
            )
            if value
        ]
        sections.append(
            {
                "heading": heading.upper()[:48],
                "lines": list(dict.fromkeys(lines)) or ["Eligible server-authored evidence"],
            }
        )
    identity_value = report.get("identity")
    identity: dict[str, Any] = dict(identity_value) if isinstance(identity_value, dict) else {}
    title = str(identity.get("display_name") or "Your Dota DNA") if show_name else "Your Dota DNA"
    subtitle = " · ".join(str(section["lines"][0]) for section in sections[:2])
    text_payload = {"title": title, "subtitle": subtitle, "identity_headline": headline, "sections": sections}
    violations = forbidden_copy_violations(text_payload)
    if violations:
        raise ValueError("v6 share copy contains forbidden summary inference: " + ", ".join(violations))
    return text_payload


def _section_markup(sections: Any) -> str:
    if not isinstance(sections, list):
        return ""
    markup: list[str] = []
    positions = (
        (72, 598, 456, 236),
        (552, 598, 456, 236),
        (72, 882, 456, 300),
        (552, 882, 456, 300),
    )
    for index, section in enumerate(sections[:4]):
        if not isinstance(section, dict):
            continue
        heading = html.escape(str(section.get("heading") or ""))
        lines = section.get("lines")
        if not heading or not isinstance(lines, list):
            continue
        x, y, width, height = positions[index]
        markup.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{_SURFACE}" stroke="{_LINE}" stroke-width="2"/>'
        )
        markup.append(f'<text x="{x + 24}" y="{y + 38}" class="section-heading-dark">{heading}</text>')
        line_y = y + 82
        for line in lines[:3]:
            rendered = _text_lines(str(line), x=x + 24, y=line_y, class_name="section-line", max_chars=30, line_height=31)
            markup.append(rendered)
            line_y += 62
    return "".join(markup)


def _text_lines(
    value: str,
    *,
    x: int,
    y: int,
    class_name: str,
    max_chars: int,
    line_height: int,
) -> str:
    """Render deterministic, escaped text lines without relying on SVG wrapping."""

    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_chars:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if not lines:
        return ""
    return "".join(
        f'<text x="{x}" y="{y + index * line_height}" class="{class_name}">{html.escape(line)}</text>'
        for index, line in enumerate(lines[:3])
    )


def _compact_title(value: str, *, max_chars: int = 24) -> str:
    """Keep a user-provided display name inside the fixed share-card grid."""

    value = " ".join(value.split())
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 1].rstrip() + "…"


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
    common_thread = portfolio.get("common_thread") or "Your pool is still writing its common thread."
    exception = portfolio.get("exception_hero")
    exception_line = f"Exception · {exception}" if exception else "No exception has stepped forward yet."
    evolution = _human_evolution_copy(portfolio.get("pool_direction"))
    mirror = card.get("hero_mirror") or {}
    mirror_line = str(mirror.get("hero_name")) if mirror.get("hero_name") else "Your mirror is still offstage."
    strongest_pattern = patterns[0] if patterns else None
    strongest_element = elements[0] if elements else None
    identity_headline = (
        f"Your Dota keeps returning to {strongest_pattern}."
        if strongest_pattern
        else f"Your Dota keeps showing {strongest_element or 'a shape of its own'}."
    )
    sections = [
        {"heading": "ELEMENTS", "lines": elements or ["No Element is taking the spotlight yet."]},
        {"heading": "PATTERNS", "lines": patterns or ["No Pattern has stepped forward yet."]},
        {"heading": "HERO PORTFOLIO", "lines": [str(common_thread), exception_line, evolution or "Your pool is holding its cards for now."]},
        {"heading": "HERO MIRROR", "lines": [mirror_line]},
    ]
    facts = [line for section in sections for line in section["lines"]]
    return {
        "title": identity.get("display_name") if show_name else "Your Dota DNA",
        "subtitle": " · ".join(facts[:2]) or "A personal snapshot of the way you play.",
        "identity_headline": identity_headline,
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


__all__ = [
    "CARD_TYPES",
    "RENDERER_VERSION",
    "V6_RENDERER_VERSION",
    "V61_RENDERER_VERSION",
    "build_share_svg",
    "share_cache_key",
]
