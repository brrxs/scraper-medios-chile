import logging
import re
from datetime import date
from typing import Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from scraper.base import HARD_PAGE_CAP
from scraper.base_playwright import BasePlaywrightScraper

logger = logging.getLogger(__name__)

_RE_WS = re.compile(r"\s+")


class ChvNoticiasScraper(BasePlaywrightScraper):
    SOURCE_SLUG = "chvnoticias"
    INDEX_URL_TEMPLATE = "https://www.chilevision.cl/noticias/nacional/"
    # Sentinel — search is handled by _collect_urls_search override.
    SEARCH_URL_TEMPLATE = "https://www.chilevision.cl/search/"

    @property
    def link_selector(self): return "a[href*='/noticias/']"

    @property
    def title_selector(self): return "h1"

    @property
    def date_selector(self): return "time"

    @property
    def body_selector(self): return "div[class*=content] p"

    def _encode_query(self, phrase: str) -> str:
        return quote(phrase, safe="")  # slug-style path needs %20, not +

    def _collect_urls_search(self, phrase: str, since: date, until: date) -> list[str]:
        q = self._encode_query(phrase)
        urls: list[str] = []
        for pg in range(1, HARD_PAGE_CAP + 1):
            # Page 1: /search/{query}/  — Page 2+: /search/{query}/page/{n}/
            if pg == 1:
                page_url = f"https://www.chilevision.cl/search/{q}/"
            else:
                page_url = f"https://www.chilevision.cl/search/{q}/page/{pg}/"
            soup = self._fetch(page_url)
            if soup is None:
                break
            links = self._extract_links(soup)
            if not links:
                if pg == 1:
                    logger.warning(
                        f"[{self.SOURCE_SLUG}] search page 1 returned 0 links for {phrase!r}"
                    )
                break
            urls.extend(links)
            self._polite_delay()
        return list(dict.fromkeys(urls))

    def _collect_urls_feed(self, since: date, until: date) -> list[str]:
        soup = self._fetch(self.INDEX_URL_TEMPLATE)
        if soup is None:
            return []
        return self._extract_links(soup)

    def _date_text(self, soup: BeautifulSoup) -> Optional[str]:
        # CHV's datetime attribute is unreliable (wrong dates); use visible text instead.
        # The text contains newlines ("20/\n  05/\n  2026...") so collapse whitespace first.
        el = soup.select_one(self.date_selector)
        if el is None:
            return None
        return _RE_WS.sub("", el.get_text())

    def _extract_links(self, soup: BeautifulSoup) -> list[str]:
        base = "https://www.chilevision.cl"
        links = []
        for a in soup.select(self.link_selector):
            href = a.get("href", "")
            if not href:
                continue
            full = href if href.startswith("http") else base + href
            path = full.replace(base, "").rstrip("/")
            # Require at least /noticias/{section}/{slug} — drop bare category paths
            parts = [p for p in path.split("/") if p]
            if len(parts) < 3:
                continue
            links.append(full)
        return list(dict.fromkeys(links))
