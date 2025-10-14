"""Data acquisition utilities for the Piano di Sorrento municipal website."""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
import os
from pathlib import Path
import re
import time
from typing import List, Optional
from urllib.error import URLError
from urllib.request import urlopen
import xml.etree.ElementTree as ET


_FEED_URL = "https://www.comune.pianodisorrento.na.it/feed/"
_CACHE_FILE = "piano_di_sorrento_cache.json"
_CACHE_MAX_AGE_HOURS = 6


@dataclasses.dataclass
class Article:
    """Structured representation of a municipal news article."""

    title: str
    link: str
    published: Optional[dt.datetime]
    content: str
    summary: str

    def short_snippet(self, length: int = 400) -> str:
        """Return a trimmed preview of the article content."""

        snippet = self.content.strip().replace("\n", " ")
        snippet = re.sub(r"\s+", " ", snippet)
        if len(snippet) <= length:
            return snippet
        return snippet[: length - 1].rstrip() + "…"


def _parse_date(value: Optional[str]) -> Optional[dt.datetime]:
    if not value:
        return None
    for fmt in [
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
    ]:
        try:
            return dt.datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _read_url(url: str, timeout: float = 10.0) -> str:
    with urlopen(url, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        raw = response.read()
    return raw.decode(charset, errors="replace")


def parse_rss_feed(xml_data: str) -> List[Article]:
    """Parse the RSS feed and return the contained articles."""

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as exc:
        raise ValueError("Impossibile analizzare il feed RSS") from exc

    channel = root.find("channel")
    if channel is None:
        return []

    articles: List[Article] = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "Senza titolo").strip()
        link = (item.findtext("link") or "").strip()
        published = _parse_date(item.findtext("pubDate"))

        # WordPress exposes the full HTML inside the content:encoded field.
        content_node = item.find("{http://purl.org/rss/1.0/modules/content/}encoded")
        description = item.findtext("description") or ""
        raw_content = content_node.text if content_node is not None else description
        clean_content = _clean_html(raw_content)
        summary = _clean_html(description)

        articles.append(
            Article(
                title=title,
                link=link,
                published=published,
                content=clean_content,
                summary=summary or clean_content,
            )
        )
    return articles


def _clean_html(html: str) -> str:
    """Remove HTML tags and keep a human readable representation."""

    if not html:
        return ""

    # Strip script and style blocks.
    html = re.sub(r"<\s*(script|style)[^>]*>.*?<\s*/\s*\1\s*>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    # Replace breaks and paragraphs with spaces.
    html = re.sub(r"<\s*/?\s*(p|br|div|li|ul|ol)[^>]*>", " \n", html, flags=re.IGNORECASE)
    # Remove residual tags.
    html = re.sub(r"<[^>]+>", " ", html)
    html = html.replace("&nbsp;", " ")
    html = re.sub(r"&([a-zA-Z]+);", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def fetch_articles(feed_url: str = _FEED_URL, timeout: float = 10.0) -> List[Article]:
    """Download the RSS feed and parse the contained articles."""

    xml_data = _read_url(feed_url, timeout=timeout)
    return parse_rss_feed(xml_data)


def load_articles(
    cache_dir: Optional[os.PathLike[str]] = None,
    *,
    feed_url: str = _FEED_URL,
    max_age_hours: int = _CACHE_MAX_AGE_HOURS,
    timeout: float = 10.0,
) -> List[Article]:
    """Load articles from cache or fetch them if needed."""

    cache_dir_path = Path(cache_dir) if cache_dir else Path.home()
    cache_dir_path.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir_path / _CACHE_FILE

    if cache_path.exists():
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_hours <= max_age_hours:
            try:
                with cache_path.open("r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                return [Article(**item) for item in payload]
            except (json.JSONDecodeError, TypeError, ValueError):
                cache_path.unlink(missing_ok=True)

    try:
        articles = fetch_articles(feed_url=feed_url, timeout=timeout)
    except URLError as exc:
        if cache_path.exists():
            with cache_path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
            return [Article(**item) for item in payload]
        raise ConnectionError(
            "Impossibile contattare il sito del Comune di Piano di Sorrento"
        ) from exc

    with cache_path.open("w", encoding="utf-8") as fh:
        json.dump([dataclasses.asdict(article) for article in articles], fh, ensure_ascii=False, indent=2)

    return articles


__all__ = ["Article", "fetch_articles", "load_articles", "parse_rss_feed"]
