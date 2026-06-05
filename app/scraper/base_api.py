import abc
import logging
import random
import time
from datetime import date, datetime, timedelta
from typing import Optional

import requests

from scraper.output import save_articles
from scraper.utils import any_phrase_matches, parse_date

logger = logging.getLogger(__name__)

HARD_OFFSET_CAP = 500  # max 500 articles per run per phrase


class BaseApiScraper(abc.ABC):
    SOURCE_SLUG: str = ""
    BATCH_SIZE: int = 10
    DELAY_MIN: float = 0.5
    DELAY_MAX: float = 1.5
    REQUEST_TIMEOUT: int = 20
    HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; prensa_chile_py/1.0)"}

    def run(
        self,
        queries: Optional[list[str]] = None,
        since: Optional[date] = None,
        until: Optional[date] = None,
    ) -> list[dict]:
        since = since or (date.today() - timedelta(days=7))
        until = until or date.today()
        queries = [q for q in (queries or []) if q and q.strip()]

        logger.info(
            f"[{self.SOURCE_SLUG}] since={since} until={until} queries={queries!r}",
            extra={"tag": "INIT"},
        )

        phrases = queries or [""]
        seen_urls: set[str] = set()
        articles: list[dict] = []

        for phrase in phrases:
            phrase_articles = self._collect_for_phrase(phrase, since, until)
            for article in phrase_articles:
                url = article.get("url") or ""
                if url and url in seen_urls:
                    continue
                if queries and not any_phrase_matches(
                    (article.get("titulo") or "") + " " + (article.get("cuerpo") or ""), queries
                ):
                    continue
                seen_urls.add(url)
                articles.append(article)

        query_label = ", ".join(queries)
        for a in articles:
            a["query"] = query_label

        logger.info(f"[{self.SOURCE_SLUG}] {len(articles)} articles collected")
        save_articles(articles, self.SOURCE_SLUG, queries=queries)
        return articles

    def _collect_for_phrase(self, phrase: str, since: date, until: date) -> list[dict]:
        results: list[dict] = []
        offset = 0
        while offset < HARD_OFFSET_CAP:
            raw_batch = self._fetch_page(phrase, offset)
            if not raw_batch:
                break

            batch_past_window = 0
            for raw in raw_batch:
                article = self._map_article(raw)
                if article is None:
                    continue
                d = parse_date(article.get("fecha"))
                if d and d < since:
                    batch_past_window += 1
                    continue
                if d and d > until:
                    continue
                results.append(article)

            if batch_past_window == len(raw_batch):
                logger.info(
                    f"[{self.SOURCE_SLUG}] phrase={phrase!r}: batch entirely before since={since}, stopping"
                )
                break

            offset += self.BATCH_SIZE
            self._polite_delay()
        return results

    @abc.abstractmethod
    def _fetch_page(self, query: str, offset: int) -> list[dict]:
        """Return a list of raw article dicts from the API for this offset."""
        ...

    @abc.abstractmethod
    def _map_article(self, raw: dict) -> Optional[dict]:
        """Map raw API fields to the standard schema dict."""
        ...

    def _get(self, url: str, params: dict, headers: Optional[dict] = None) -> Optional[dict]:
        try:
            resp = requests.get(
                url,
                params=params,
                headers=headers or self.HEADERS,
                timeout=self.REQUEST_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.warning(f"[{self.SOURCE_SLUG}] HTTP {resp.status_code}")
                return None
            return resp.json()
        except Exception as e:
            logger.warning(f"[{self.SOURCE_SLUG}] API error: {e}")
            return None

    def _polite_delay(self):
        time.sleep(random.uniform(self.DELAY_MIN, self.DELAY_MAX))
