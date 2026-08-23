#!/usr/bin/env python3
"""
Dota 2 News -> Markdown scraper

Discovers Dota 2 news article URLs from the rendered news archive and optional
sitemap(s), then saves one Markdown file per article.

Usage:
  python dota2_news_scraper.py
  python dota2_news_scraper.py --headful --limit 10
  python dota2_news_scraper.py --output ./dota2-news --delay 1.5

Install:
  python3 -m venv .venv
  source .venv/bin/activate
  pip install playwright beautifulsoup4 python-slugify trafilatura lxml_html_clean
  playwright install chromium
"""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import random
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

try:
    import trafilatura
except ImportError:
    trafilatura = None
from bs4 import BeautifulSoup
from playwright.async_api import Browser, Page, async_playwright
from slugify import slugify

BASE = "https://www.dota2.com"
NEWS_URL = f"{BASE}/news"
DEFAULT_ARCHIVES = [NEWS_URL, f"{NEWS_URL}/updates"]
SITEMAP_CANDIDATES = [f"{BASE}/sitemap.xml", f"{BASE}/sitemap_index.xml"]
ARTICLE_RE = re.compile(r"^https?://(?:www\.)?dota2\.com/newsentry/(\d+)(?:[/?#].*)?$", re.I)
DATE_RE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2},\s+\d{4}\b",
    re.I,
)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/151.0 Safari/537.36 DotaNewsResearchScraper/1.0"
)


@dataclass
class ArticleResult:
    article_id: str
    url: str
    title: str
    date: str | None
    filename: str | None
    status: str
    error: str | None = None


def clean_url(url: str, language: str = "english") -> str:
    """Normalize Dota URLs and force a stable language query parameter."""
    absolute = urljoin(BASE, url)
    p = urlparse(absolute)
    if p.netloc.lower() not in {"dota2.com", "www.dota2.com"}:
        return absolute
    query = dict(parse_qsl(p.query, keep_blank_values=True))
    query["l"] = language
    return urlunparse(("https", "www.dota2.com", p.path, "", urlencode(query), ""))


def canonical_article_url(url: str, language: str = "english") -> str | None:
    absolute = urljoin(BASE, url)
    p = urlparse(absolute)
    candidate = urlunparse(("https", "www.dota2.com", p.path.rstrip("/"), "", "", ""))
    m = ARTICLE_RE.match(candidate)
    if not m:
        return None
    return clean_url(candidate, language)


def article_id_from_url(url: str) -> str:
    m = re.search(r"/newsentry/(\d+)", url)
    return m.group(1) if m else "unknown"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Dota 2 news articles into separate Markdown files.")
    parser.add_argument("--output", default="dota2-news-md", help="Output directory (default: dota2-news-md)")
    parser.add_argument("--language", default="english", help="Dota site language query value (default: english)")
    parser.add_argument("--delay", type=float, default=1.0, help="Base delay between article requests in seconds")
    parser.add_argument("--limit", type=int, default=0, help="Only scrape N articles; 0 = all discovered")
    parser.add_argument("--max-scrolls", type=int, default=500, help="Max archive scroll rounds per page")
    parser.add_argument("--stable-rounds", type=int, default=10, help="Stop archive scrolling after N rounds with no new URLs")
    parser.add_argument("--headful", action="store_true", help="Show Chromium while scraping")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing Markdown files")
    parser.add_argument("--no-sitemap", action="store_true", help="Skip sitemap discovery")
    parser.add_argument("--archive", action="append", default=[], help="Additional archive URL to scan; repeatable")
    parser.add_argument("--timeout", type=int, default=45, help="Page timeout in seconds")
    return parser.parse_args()


def robots_allows(url: str) -> bool:
    """Best-effort robots.txt check. If robots cannot be fetched, warn and continue."""
    robots_url = f"{BASE}/robots.txt"
    try:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        allowed = rp.can_fetch(USER_AGENT, url)
        if not allowed:
            print(f"[robots] Disallowed: {url}", file=sys.stderr)
        return allowed
    except Exception as exc:
        print(f"[robots] Could not read robots.txt ({exc}); continuing cautiously.", file=sys.stderr)
        return True


def fetch_sitemap_urls(language: str) -> set[str]:
    """Best-effort recursive sitemap discovery for /newsentry/ URLs."""
    found: set[str] = set()
    visited: set[str] = set()
    queue = list(SITEMAP_CANDIDATES)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/xml,text/xml,*/*"}

    while queue and len(visited) < 50:
        sitemap_url = queue.pop(0)
        if sitemap_url in visited:
            continue
        visited.add(sitemap_url)
        try:
            req = Request(sitemap_url, headers=headers)
            with urlopen(req, timeout=20) as response:
                content = response.read()
            if not content.strip():
                continue
            root = ET.fromstring(content)
        except Exception:
            continue

        # Namespace-agnostic <loc> extraction.
        locs = [el.text.strip() for el in root.iter() if el.tag.endswith("loc") and el.text]
        for loc in locs:
            art = canonical_article_url(loc, language)
            if art:
                found.add(art)
            elif "sitemap" in loc.lower() and loc not in visited:
                queue.append(loc)

    return found


async def dismiss_common_overlays(page: Page) -> None:
    """Best-effort close/accept common overlays without depending on exact site copy."""
    candidates = [
        "button:has-text('Accept')",
        "button:has-text('Agree')",
        "button:has-text('OK')",
        "button[aria-label='Close']",
        "[role='dialog'] button:has-text('Close')",
    ]
    for selector in candidates:
        try:
            loc = page.locator(selector).first
            if await loc.is_visible(timeout=500):
                await loc.click(timeout=1000)
        except Exception:
            pass


async def collect_links_from_page(page: Page, language: str) -> set[str]:
    hrefs = await page.locator("a[href]").evaluate_all("els => els.map(a => a.href)")
    out: set[str] = set()
    for href in hrefs:
        art = canonical_article_url(href, language)
        if art:
            out.add(art)
    return out


async def click_load_more_if_present(page: Page) -> bool:
    """Click likely load-more controls if one is visible."""
    selectors = [
        "button:has-text('Load More')",
        "button:has-text('Show More')",
        "button:has-text('More')",
        "a:has-text('Load More')",
        "a:has-text('Show More')",
    ]
    for selector in selectors:
        try:
            loc = page.locator(selector).last
            if await loc.is_visible(timeout=300):
                await loc.click(timeout=1500)
                await page.wait_for_timeout(1200)
                return True
        except Exception:
            continue
    return False


async def discover_from_archive(
    page: Page,
    archive_url: str,
    language: str,
    max_scrolls: int,
    stable_rounds: int,
    timeout_ms: int,
) -> set[str]:
    url = clean_url(archive_url, language)
    print(f"[discover] {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    await page.wait_for_timeout(1800)
    await dismiss_common_overlays(page)

    discovered: set[str] = set()
    stable = 0
    last_height = 0

    for round_no in range(1, max_scrolls + 1):
        before = len(discovered)
        discovered |= await collect_links_from_page(page, language)

        # Try both native infinite scroll and explicit load-more UI.
        clicked = await click_load_more_if_present(page)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(900)

        try:
            height = await page.evaluate("document.body.scrollHeight")
        except Exception:
            height = last_height

        discovered |= await collect_links_from_page(page, language)
        after = len(discovered)
        gained = after - before

        if gained > 0:
            stable = 0
            print(f"  round {round_no:>3}: +{gained}, total={after}")
        else:
            if height == last_height and not clicked:
                stable += 1
            else:
                stable += 1

        last_height = height
        if stable >= stable_rounds:
            break

    print(f"[discover] Found {len(discovered)} article URLs from {archive_url}")
    return discovered


def clean_markdown(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def get_meta(soup: BeautifulSoup, *keys: tuple[str, str]) -> str | None:
    for attr, value in keys:
        tag = soup.find("meta", attrs={attr: value})
        if tag and tag.get("content"):
            return html.unescape(tag["content"].strip())
    return None


def extract_title(soup: BeautifulSoup, extracted_meta: object | None = None) -> str:
    title = get_meta(
        soup,
        ("property", "og:title"),
        ("name", "twitter:title"),
    )
    if not title and extracted_meta is not None:
        title = getattr(extracted_meta, "title", None)
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(" ", strip=True) if h1 else None
    if not title and soup.title:
        title = soup.title.get_text(" ", strip=True)
    title = title or "Untitled Dota 2 News Article"
    title = re.sub(r"\s*[|–—-]\s*Dota\s*2\s*$", "", title, flags=re.I).strip()
    return title


def normalize_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    # ISO-like dates first.
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.date().isoformat()
    except Exception:
        pass
    # Common English site date.
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except Exception:
            pass
    m = DATE_RE.search(raw)
    if m:
        for fmt in ("%B %d, %Y", "%b %d, %Y"):
            try:
                return datetime.strptime(m.group(0), fmt).date().isoformat()
            except Exception:
                pass
    return raw


def extract_date(soup: BeautifulSoup, extracted_meta: object | None = None) -> str | None:
    candidates: list[str] = []
    meta_date = get_meta(
        soup,
        ("property", "article:published_time"),
        ("name", "date"),
        ("itemprop", "datePublished"),
    )
    if meta_date:
        candidates.append(meta_date)
    if extracted_meta is not None:
        for attr in ("date", "publish_date"):
            value = getattr(extracted_meta, attr, None)
            if value:
                candidates.append(str(value))
    for t in soup.find_all("time"):
        if t.get("datetime"):
            candidates.append(t["datetime"])
        txt = t.get_text(" ", strip=True)
        if txt:
            candidates.append(txt)
    # Last-resort visible-text scan near top of document.
    visible = soup.get_text(" ", strip=True)[:5000]
    m = DATE_RE.search(visible)
    if m:
        candidates.append(m.group(0))

    for candidate in candidates:
        normalized = normalize_date(candidate)
        if normalized:
            return normalized
    return None


def extract_markdown_from_html(page_html: str, url: str) -> tuple[str, str, str | None]:
    soup = BeautifulSoup(page_html, "html.parser")

    # Trafilatura is optional. If it is unavailable (for example because a
    # transitive lxml/justext dependency is broken), the scraper still works
    # using the BeautifulSoup fallback below.
    if trafilatura is not None:
        try:
            meta = trafilatura.extract_metadata(page_html, default_url=url)
        except Exception:
            meta = None
    else:
        meta = None

    title = extract_title(soup, meta)
    date = extract_date(soup, meta)

    md = None
    if trafilatura is not None:
        try:
            md = trafilatura.extract(
                page_html,
                url=url,
                output_format="markdown",
                include_links=True,
                include_images=False,
                include_tables=True,
                include_formatting=True,
                include_comments=False,
                deduplicate=True,
                favor_precision=False,
            )
        except Exception:
            md = None

    if not md or len(md.strip()) < 50:
        # Readability-ish fallback: prefer semantic article/main containers.
        for bad in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "button"]):
            bad.decompose()
        candidate = soup.find("article") or soup.find("main") or soup.body
        if candidate:
            # Simple text fallback; keeps the scraper usable even if extraction libraries miss.
            chunks: list[str] = []
            for el in candidate.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote"]):
                txt = el.get_text(" ", strip=True)
                if not txt:
                    continue
                if el.name == "h1":
                    chunks.append(f"# {txt}")
                elif el.name == "h2":
                    chunks.append(f"## {txt}")
                elif el.name == "h3":
                    chunks.append(f"### {txt}")
                elif el.name == "h4":
                    chunks.append(f"#### {txt}")
                elif el.name == "li":
                    chunks.append(f"- {txt}")
                elif el.name == "blockquote":
                    chunks.append(f"> {txt}")
                else:
                    chunks.append(txt)
            md = "\n\n".join(chunks)

    md = clean_markdown(md or "")

    # Avoid duplicating a leading title already represented in frontmatter / H1.
    escaped_title = re.escape(title)
    md = re.sub(rf"^#\s+{escaped_title}\s*\n+", "", md, count=1, flags=re.I)

    return title, md, date


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def output_filename(title: str, date: str | None, article_id: str) -> str:
    prefix = date if date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) else "undated"
    slug = slugify(title, lowercase=True, max_length=100) or "article"
    return f"{prefix}__{slug}__{article_id}.md"


def write_article_file(
    out_dir: Path,
    url: str,
    article_id: str,
    title: str,
    date: str | None,
    markdown_body: str,
    overwrite: bool,
) -> tuple[str, str]:
    filename = output_filename(title, date, article_id)
    path = out_dir / filename
    if path.exists() and not overwrite:
        return filename, "skipped"

    frontmatter = [
        "---",
        f"title: {yaml_quote(title)}",
        f"date: {yaml_quote(date or '')}",
        f"url: {yaml_quote(url)}",
        f"article_id: {yaml_quote(article_id)}",
        "source: \"Dota 2 News\"",
        "---",
        "",
        f"# {title}",
        "",
    ]
    path.write_text("\n".join(frontmatter) + markdown_body.strip() + "\n", encoding="utf-8")
    return filename, "saved"


async def scrape_article(
    page: Page,
    url: str,
    out_dir: Path,
    overwrite: bool,
    timeout_ms: int,
) -> ArticleResult:
    article_id = article_id_from_url(url)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        await page.wait_for_timeout(1000)
        await dismiss_common_overlays(page)
        html_text = await page.content()
        title, body, date = extract_markdown_from_html(html_text, url)
        if len(body.strip()) < 20:
            raise RuntimeError("Article body extraction returned too little text")
        filename, status = write_article_file(
            out_dir, url, article_id, title, date, body, overwrite
        )
        return ArticleResult(article_id, url, title, date, filename, status)
    except Exception as exc:
        return ArticleResult(article_id, url, "", None, None, "error", str(exc))


async def make_browser(playwright, headful: bool) -> Browser:
    return await playwright.chromium.launch(
        headless=not headful,
        args=["--disable-blink-features=AutomationControlled"],
    )


async def main_async(args: argparse.Namespace) -> int:
    out_dir = Path(args.output).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "errors").mkdir(exist_ok=True)

    if not robots_allows(NEWS_URL):
        print("Aborting because robots.txt disallows the news archive for this user agent.", file=sys.stderr)
        return 2

    timeout_ms = args.timeout * 1000
    article_urls: set[str] = set()

    if not args.no_sitemap:
        sitemap_urls = fetch_sitemap_urls(args.language)
        if sitemap_urls:
            print(f"[sitemap] Found {len(sitemap_urls)} article URLs")
            article_urls |= sitemap_urls
        else:
            print("[sitemap] No usable newsentry URLs found; using rendered archive discovery.")

    async with async_playwright() as p:
        browser = await make_browser(p, args.headful)
        context = await browser.new_context(
            user_agent=USER_AGENT,
            locale="en-US",
            viewport={"width": 1440, "height": 1200},
        )
        page = await context.new_page()
        page.set_default_timeout(timeout_ms)

        archives = DEFAULT_ARCHIVES + args.archive
        seen_archives: set[str] = set()
        for archive in archives:
            normalized = clean_url(archive, args.language)
            if normalized in seen_archives:
                continue
            seen_archives.add(normalized)
            try:
                article_urls |= await discover_from_archive(
                    page,
                    archive,
                    args.language,
                    args.max_scrolls,
                    args.stable_rounds,
                    timeout_ms,
                )
            except Exception as exc:
                print(f"[discover:error] {archive}: {exc}", file=sys.stderr)

        # Persist URL inventory before scraping so a failed run can be inspected/resumed.
        inventory = sorted(article_urls, key=lambda u: int(article_id_from_url(u)), reverse=True)
        (out_dir / "article_urls.txt").write_text("\n".join(inventory) + "\n", encoding="utf-8")
        print(f"[total] {len(inventory)} unique article URLs discovered")

        if args.limit > 0:
            inventory = inventory[: args.limit]
            print(f"[limit] Scraping first {len(inventory)} URLs")

        results: list[ArticleResult] = []
        for i, url in enumerate(inventory, start=1):
            print(f"[{i}/{len(inventory)}] {url}")
            result = await scrape_article(page, url, out_dir, args.overwrite, timeout_ms)
            results.append(result)
            if result.status == "error":
                print(f"  ERROR: {result.error}", file=sys.stderr)
                err_path = out_dir / "errors" / f"{result.article_id}.txt"
                err_path.write_text(f"URL: {url}\nERROR: {result.error}\n", encoding="utf-8")
            else:
                print(f"  {result.status}: {result.filename}")

            # Polite jitter reduces burstiness.
            if i < len(inventory):
                await asyncio.sleep(max(0.0, args.delay + random.uniform(0.0, 0.45)))

        await context.close()
        await browser.close()

    # Machine-readable manifest.
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Human-readable index.
    ok = [r for r in results if r.status in {"saved", "skipped"}]
    errors = [r for r in results if r.status == "error"]
    lines = [
        "# Dota 2 News Archive",
        "",
        f"- Discovered: {len(article_urls)}",
        f"- Processed this run: {len(results)}",
        f"- Saved/skipped successfully: {len(ok)}",
        f"- Errors: {len(errors)}",
        "",
        "## Articles",
        "",
    ]
    for r in sorted(ok, key=lambda x: (x.date or "", x.article_id), reverse=True):
        display_date = r.date or "undated"
        lines.append(f"- {display_date} — [{r.title}]({r.filename}) — [source]({r.url})")
    if errors:
        lines += ["", "## Errors", ""]
        for r in errors:
            lines.append(f"- `{r.article_id}` — {r.url} — {r.error}")
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\nDone.")
    print(f"Output: {out_dir}")
    print(f"Manifest: {manifest_path}")
    print(f"Index: {out_dir / 'README.md'}")
    return 0 if not errors else 1


def main() -> None:
    args = parse_args()
    try:
        raise SystemExit(asyncio.run(main_async(args)))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
