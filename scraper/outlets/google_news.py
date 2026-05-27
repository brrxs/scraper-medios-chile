"""Google News — supplementary catch-all source (GNews library backend).

Uses GNews (ranahaani/GNews) which wraps the official Google News RSS endpoint
with Chile/Spanish targeting, automatic URL resolution, and optional proxy support.

503 mitigation: per-day fetch with exponential backoff (3 attempts, 5/15/30s).
Proxy: set GNEWS_PROXY env var to route requests through a proxy.
"""
import logging
import os
import random
import time
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Optional

from bs4 import BeautifulSoup
from gnews import GNews

from scraper.base_api import BaseApiScraper

logger = logging.getLogger(__name__)

_MAX_PER_DAY = 100
_RETRY_DELAYS = (5, 15, 30)


class GoogleNewsScraper(BaseApiScraper):
    SOURCE_SLUG = "google_news"

    def _collect_for_phrase(self, phrase: str, since: date, until: date) -> list[dict]:
        proxy = os.getenv("GNEWS_PROXY")
        results: list[dict] = []
        seen: set[str] = set()
        day = since
        while day <= until:
            for article in self._fetch_day(phrase, day, proxy):
                url = article.get("url") or ""
                if url and url not in seen:
                    seen.add(url)
                    results.append(article)
            time.sleep(random.uniform(1.0, 2.5))
            day += timedelta(days=1)
        return results

    def _fetch_day(self, phrase: str, day: date, proxy: Optional[str]) -> list[dict]:
        next_day = day + timedelta(days=1)
        client = GNews(
            language="es",
            country="CL",
            max_results=_MAX_PER_DAY,
            start_date=(day.year, day.month, day.day),
            end_date=(next_day.year, next_day.month, next_day.day),
        )
        if proxy:
            client.proxy = {"http": proxy, "https": proxy}

        for attempt in range(len(_RETRY_DELAYS) + 1):
            try:
                raw_list = client.get_news(phrase)
                n = len(raw_list)
                logger.info(f"[{self.SOURCE_SLUG}] {day} query={phrase!r} -> {n} results")
                if n >= _MAX_PER_DAY:
                    logger.warning(
                        f"[{self.SOURCE_SLUG}] 100-result cap hit on {day} for query={phrase!r} — "
                        f"add more --query phrases for broader coverage"
                    )
                return [a for a in (_gnews_to_article(r, self.SOURCE_SLUG) for r in raw_list) if a]
            except Exception as e:
                if attempt < len(_RETRY_DELAYS):
                    delay = _RETRY_DELAYS[attempt] + random.uniform(-2, 2)
                    logger.warning(
                        f"[{self.SOURCE_SLUG}] attempt {attempt + 1} failed ({e}), "
                        f"retrying in {delay:.0f}s"
                    )
                    time.sleep(delay)
                else:
                    logger.warning(f"[{self.SOURCE_SLUG}] all retries exhausted on {day}: {e}")
        return []

    def _fetch_page(self, query: str, offset: int) -> list[dict]:
        """Used only by run.py `check` command — returns raw GNews dicts for today."""
        if offset > 0:
            return []
        client = GNews(language="es", country="CL", max_results=10)
        try:
            return client.get_news(query or "chile")
        except Exception as e:
            logger.warning(f"[{self.SOURCE_SLUG}] check fetch failed: {e}")
            return []

    def _map_article(self, raw: dict) -> Optional[dict]:
        return _gnews_to_article(raw, self.SOURCE_SLUG)


def _gnews_to_article(raw: dict, slug: str) -> Optional[dict]:
    titulo = (raw.get("title") or "").strip()
    if not titulo or len(titulo) < 20:
        return None
    url = raw.get("url") or ""
    if not url:
        return None

    publisher = raw.get("publisher") or {}
    source_name = (publisher.get("title") or "").strip() or slug

    raw_desc = raw.get("description") or ""
    description = BeautifulSoup(raw_desc, "lxml").get_text(" ", strip=True) if raw_desc else ""
    if description and source_name != slug:
        bajada: Optional[str] = f"[{source_name}] {description}"[:500]
    else:
        bajada = description[:500] if description else None
    cuerpo = bajada or titulo

    fecha = _parse_gnews_date(raw.get("published date") or "")

    return {
        "titulo": titulo,
        "cuerpo": cuerpo,
        "bajada": bajada,
        "fecha": fecha,
        "fuente": source_name,
        "url": url,
        "fecha_scraping": datetime.now().isoformat(timespec="seconds"),
        "query": "",
    }


def _parse_gnews_date(date_str: str) -> Optional[str]:
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str).date().isoformat()
    except Exception:
        return None
